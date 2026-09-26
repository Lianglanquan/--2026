from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import cadquery as cq
import trimesh

from .input_audit import MANIFEST, ORIGINAL_SOURCE
from .parameters import DesignParameters, JointFrame, REPO_ROOT
from .reference_solids import import_ha8_horn_reference, make_ha8_reference


@dataclass(frozen=True)
class _HornHole:
    x_mm: float
    y_mm: float
    diameter_mm: float


PASSIVE_INSERT_GEOMETRY = {
    "cavity_radius_mm": 6.2,
    "cavity_start_z_mm": 2.9,
    "cavity_depth_mm": 3.2,
    "clearance_radius_mm": 6.25,
    "clearance_start_z_mm": 2.8,
    "clearance_depth_mm": 3.4,
    "seat_outer_radius_mm": 7.0,
    "seat_start_z_mm": 2.5,
    "seat_height_mm": 3.0,
    "seat_fillet_radius_mm": 0.5,
    "passive_insert_outer_diameter_mm": None,
    "passive_insert_length_mm": None,
}


def _axis_record(face: cq.Face) -> dict[str, Any]:
    axis = face._geomAdaptor().Axis()
    location = axis.Location()
    direction = axis.Direction()
    return {
        "origin": (location.X(), location.Y(), location.Z()),
        "direction": (direction.X(), direction.Y(), direction.Z()),
    }


def _manifest() -> dict[str, Any]:
    return json.loads((REPO_ROOT / MANIFEST).read_text(encoding="utf-8"))


def _horn_holes() -> tuple[_HornHole, ...]:
    reference = import_ha8_horn_reference()
    horn = reference.objects["REF_HA8_OFFICIAL_25T_HORN"].obj
    candidates = []
    for face in horn.faces().vals():
        if face.geomType() != "CYLINDER":
            continue
        radius = float(face._geomAdaptor().Radius())
        if not math.isclose(radius, 0.9, abs_tol=1e-6):
            continue
        center = face._geomAdaptor().Axis().Location()
        candidates.append((round(center.X(), 7), round(center.Y(), 7), radius))
    unique = sorted(set(candidates))
    if len(unique) != 8:
        raise ValueError(f"official 25T horn must expose eight holes; got {len(unique)}")
    holes = tuple(_HornHole(x, y, 2.0 * radius) for x, y, radius in unique)
    if {round(math.hypot(hole.x_mm, hole.y_mm), 5) for hole in holes} != {8.0}:
        raise ValueError("official horn hole topology is not an 16 mm BCD")
    return holes


def _interface_reference(joint_id: int) -> dict[str, Any]:
    relative = (ORIGINAL_SOURCE / "01_原版STL" / f"舵机接口{joint_id}.stl").as_posix()
    record = next(item for item in _manifest()["files"] if item["relative_path"] == relative)
    source_path = REPO_ROOT / relative
    if not source_path.is_file():
        raise FileNotFoundError(f"audited STL interface reference is missing: {relative}")
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_sha256 != record["sha256"]:
        raise ValueError(f"audited STL hash changed: {relative}")
    geometry = _manifest()["original_stl_geometry"][relative]
    mesh = trimesh.load(source_path, file_type="stl", force="mesh", process=False)
    section_z = 0.0
    section = mesh.section(plane_origin=(0.0, 0.0, section_z), plane_normal=(0.0, 0.0, 1.0))
    if section is None or len(section.vertices) == 0:
        raise ValueError(f"unable to recover measured STL section: {relative}")
    section_xy = section.vertices[:, :2]
    section_loops = []
    for entity in section.entities:
        loop = section.vertices[entity.points, :2]
        if len(loop) < 4 or not math.isclose(float(math.dist(loop[0], loop[-1])), 0.0, abs_tol=1e-8):
            raise ValueError(f"STL section loop is not closed: {relative}")
        section_loops.append(tuple((float(x), float(y)) for x, y in loop[:-1]))
    if len(section_loops) < 2:
        raise ValueError(f"STL section must expose outer and inner loops: {relative}")
    measured_profile = {
        "section_z_mm": section_z,
        "width_mm": float(section_xy[:, 0].max() - section_xy[:, 0].min()),
        "depth_mm": float(section_xy[:, 1].max() - section_xy[:, 1].min()),
        "vertex_count": int(len(section.vertices)),
        "vertices_xy": tuple(section_loops),
    }
    bounds = geometry["bounding_box_mm"]
    minimum = tuple(float(value) for value in bounds["minimum"])
    maximum = tuple(float(value) for value in bounds["maximum"])
    extents = tuple(float(value) for value in bounds["extents"])
    outer_loop, *inner_loops = section_loops
    mating_profile = cq.Workplane("XY").polyline(outer_loop).close().extrude(extents[2], both=True)
    for inner_loop in inner_loops:
        mating_profile = mating_profile.cut(
            cq.Workplane("XY").polyline(inner_loop).close().extrude(extents[2] + 2.0, both=True)
        )
    return {
        "source_path": relative,
        "source_sha256": source_sha256,
        "face_count": int(geometry["face_count"]),
        "watertight": bool(geometry["watertight"]),
        "bounds_mm": {"minimum": minimum, "maximum": maximum, "extents": extents},
        "center_mm": tuple((low + high) / 2.0 for low, high in zip(minimum, maximum)),
        "measured_section": measured_profile,
        "solid": mating_profile.val(),
        "status": "measured_section_contour_extrusion",
        "unresolved_detail": "STL triangle-level surface texture and non-section relief are not uniquely recoverable as CAD faces",
    }


def _original_part_reference(file_name: str) -> dict[str, Any]:
    relative = (ORIGINAL_SOURCE / "01_原版STL" / file_name).as_posix()
    record = next(item for item in _manifest()["files"] if item["relative_path"] == relative)
    source_path = REPO_ROOT / relative
    actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if actual_sha256 != record["sha256"]:
        raise ValueError(f"audited STL hash changed: {relative}")
    geometry = _manifest()["original_stl_geometry"][relative]
    return {
        "source_path": relative,
        "source_sha256": actual_sha256,
        "bounds_mm": geometry["bounding_box_mm"],
        "face_count": int(geometry["face_count"]),
        "watertight": bool(geometry["watertight"]),
    }


def _ha8_mount_hole_centers(params: DesignParameters) -> tuple[tuple[float, float], ...]:
    # The official body STEP is the authority for ear-hole positions.  Radius
    # 2.15 mm is the documented 4.3 mm mounting hole, and duplicate split
    # faces are collapsed by their axes.
    assembly = make_ha8_reference(params.ha8)
    body = assembly.objects["REF_HA8_OFFICIAL_BODY"].obj
    centers: set[tuple[float, float]] = set()
    for face in body.faces().vals():
        if face.geomType() != "CYLINDER":
            continue
        radius = float(face._geomAdaptor().Radius())
        if not math.isclose(radius, 2.15, abs_tol=1e-5):
            continue
        location = face._geomAdaptor().Axis().Location()
        centers.add((round(location.X(), 6), round(location.Y(), 6)))
    if len(centers) != 4:
        raise ValueError(f"official HA8 body must expose four 4.3 mm ear holes; got {len(centers)}")
    center_x = sum(point[0] for point in centers) / len(centers)
    center_y = sum(point[1] for point in centers) / len(centers)
    return tuple(sorted((x - center_x, y - center_y) for x, y in centers))


def _solid_faces(workplane: cq.Workplane) -> tuple[cq.Face, ...]:
    return tuple(workplane.val().Faces())


def _cylinders(workplane: cq.Workplane) -> list[cq.Face]:
    faces = []
    for face in _solid_faces(workplane):
        if face.geomType() != "CYLINDER":
            continue
        try:
            face._geomAdaptor().Radius()
        except AttributeError:
            continue
        faces.append(face)
    return faces


def _faces_at_radius(workplane: cq.Workplane, radius: float) -> list[cq.Face]:
    faces = []
    seen: set[tuple[float, float, float, float]] = set()
    for face in _cylinders(workplane):
        if not math.isclose(float(face._geomAdaptor().Radius()), radius, abs_tol=1e-5):
            continue
        center = face._geomAdaptor().Axis().Location()
        key = (round(center.X(), 5), round(center.Y(), 5), round(center.Z(), 5), round(radius, 5))
        if key not in seen:
            seen.add(key)
            faces.append(face)
    return faces


def _face_at_radius(workplane: cq.Workplane, radius: float, *, center: bool = False) -> cq.Face:
    faces = _faces_at_radius(workplane, radius)
    if center:
        box = workplane.val().BoundingBox()
        center_x = (box.xmin + box.xmax) / 2.0
        center_y = (box.ymin + box.ymax) / 2.0
        faces = sorted(
            faces,
            key=lambda face: math.hypot(
                face.Center().x - center_x, face.Center().y - center_y
            ),
        )[:1]
    if not faces:
        raise ValueError(f"unable to find owned cylindrical face at radius {radius}")
    return max(faces, key=lambda face: face.Area())


def _boundary_faces(workplane: cq.Workplane) -> list[cq.Face]:
    excluded = (1.6, 1.7, 5.5, 7.0)
    candidates = []
    for face in _solid_faces(workplane):
        if face.geomType() == "TORUS":
            candidates.append(face)
        elif face.geomType() == "CYLINDER":
            try:
                radius = float(face._geomAdaptor().Radius())
            except AttributeError:
                continue
            if not any(math.isclose(radius, item, abs_tol=1e-5) for item in excluded):
                candidates.append(face)
    if not candidates:
        raise ValueError("part has no local cylindrical boundary faces")
    return candidates


def _hole_feature(face: cq.Face) -> dict[str, Any]:
    return {"axis": _axis_record(face), "face": face}


def _axis_feature(workplane: cq.Workplane) -> dict[str, Any]:
    face = _face_at_radius(workplane, 1.7, center=True)
    return {"axis": _axis_record(face), "face": face}


def _frame_map(params: DesignParameters) -> dict[int, JointFrame]:
    frames = {frame.joint_id: frame for frame in params.joint_frames}
    if set(frames) != {1, 2, 3, 4}:
        raise ValueError("params must contain four approved joint frames")
    return frames


def _should_mirror(frame: JointFrame, frames: dict[int, JointFrame]) -> bool:
    partner = frames[frame.mirror_partner]
    if partner.mirror_partner != frame.joint_id:
        raise ValueError("joint frame mirror partners must be reciprocal")
    return frame.side == "right" and partner.side == "left" and frame.variant == partner.variant


def _fillet_faces(workplane: cq.Workplane, radius: float) -> list[cq.Face]:
    result = []
    for face in _solid_faces(workplane):
        if face.geomType() == "TORUS" and math.isclose(float(face._geomAdaptor().MinorRadius()), radius, abs_tol=1e-5):
            result.append(face)
    return result


def _make_interface_plate(holes: tuple[_HornHole, ...], reference: dict[str, Any]) -> cq.Workplane:
    extents = reference["bounds_mm"]["extents"]
    base = (
        cq.Workplane("XY")
        .box(extents[0], extents[1], 4.0, centered=(True, True, True))
        .edges("|Z")
        .fillet(2.0)
    )
    hole_cuts = cq.Workplane("XY").pushPoints([(hole.x_mm, hole.y_mm) for hole in holes]).circle(1.6).extrude(8.0, both=True)
    center_cut = cq.Workplane("XY").circle(1.7).extrude(8.0, both=True)
    register = cq.Workplane("XY").circle(5.5).circle(1.7).extrude(1.0).translate((0.0, 0.0, 2.0)).edges(">Z").fillet(0.5)
    mating_profile = cq.Workplane("XY").newObject([reference["solid"]]).translate((0.0, 0.0, 0.0)).cut(
        cq.Workplane("XY").circle(6.0).extrude(10.0, both=True)
    )
    return base.union(register).union(mating_profile).cut(hole_cuts).cut(center_cut)


def _make_support(holes: tuple[_HornHole, ...]) -> cq.Workplane:
    base = cq.Workplane("XY").circle(13.5).extrude(6.0).edges(">Z").fillet(1.0)
    hole_cuts = cq.Workplane("XY").pushPoints([(hole.x_mm, hole.y_mm) for hole in holes]).circle(1.6).extrude(8.0, both=True)
    center_cut = cq.Workplane("XY").circle(1.7).extrude(8.0, both=True)
    g = PASSIVE_INSERT_GEOMETRY
    cavity = cq.Workplane("XY").circle(g["cavity_radius_mm"]).extrude(g["cavity_depth_mm"]).translate((0.0, 0.0, g["cavity_start_z_mm"]))
    clearance = cq.Workplane("XY").circle(g["clearance_radius_mm"]).extrude(g["clearance_depth_mm"]).translate((0.0, 0.0, g["clearance_start_z_mm"]))
    seat_register_groove = (
        cq.Workplane("XY")
        .circle(g["seat_outer_radius_mm"] + 0.3)
        .circle(g["seat_outer_radius_mm"])
        .extrude(0.4)
        .translate((0.0, 0.0, g["clearance_start_z_mm"]))
    )
    return base.cut(hole_cuts).cut(center_cut).cut(cavity).cut(clearance).cut(seat_register_groove)


def _make_spacer() -> cq.Workplane:
    g = PASSIVE_INSERT_GEOMETRY
    base = cq.Workplane("XY").circle(g["seat_outer_radius_mm"]).extrude(g["seat_height_mm"])
    cavity = cq.Workplane("XY").circle(g["cavity_radius_mm"]).extrude(g["cavity_depth_mm"]).translate((0.0, 0.0, g["cavity_start_z_mm"]))
    return base.cut(cavity).cut(cq.Workplane("XY").circle(1.7).extrude(4.0))


def _attach_features(workplane: cq.Workplane, *, kind: str, params: DesignParameters, joint_id: int, holes: tuple[_HornHole, ...], reference: dict[str, Any], location: cq.Location) -> cq.Workplane:
    axis_feature = _axis_feature(workplane)
    axis = axis_feature["axis"]
    axis_face = axis_feature["face"]
    mounting_faces = [] if kind == "spacer" else _faces_at_radius(workplane, 1.6)
    if kind != "spacer" and len(mounting_faces) != 8:
        raise ValueError(f"part must retain eight mounting-hole faces; got {len(mounting_faces)}")
    mounting_faces.sort(key=lambda face: math.atan2(face.Center().y, face.Center().x))
    mounting_holes = [_hole_feature(face) for face in mounting_faces]
    register_face = _face_at_radius(workplane, 5.5, center=True) if kind == "output_adapter" else _face_at_radius(workplane, 7.0)
    boundary_faces = _boundary_faces(workplane)
    if kind == "output_adapter":
        boundary_faces = [
            face for face in boundary_faces
            if face.geomType() == "CYLINDER"
            and math.isclose(float(face._geomAdaptor().Radius()), 2.0, abs_tol=1e-5)
        ]
    def nearest_boundary(face: cq.Face) -> cq.Face:
        candidates = [candidate for candidate in boundary_faces if face.distance(candidate) > 1e-6]
        return min(candidates, key=lambda candidate: face.distance(candidate))

    local_hole = mounting_faces[0] if mounting_faces else axis_face
    probes = [
        {"name": "outer_to_center", "faces": [axis_face, nearest_boundary(axis_face)], "pair_type": "axis_to_nearest_boundary"},
        {"name": "mounting_hole_local_wall", "faces": [local_hole, nearest_boundary(local_hole)], "pair_type": "hole_to_nearest_boundary"},
        {"name": "register_local_wall", "faces": [register_face, nearest_boundary(register_face)], "pair_type": "register_to_nearest_boundary"},
    ]
    clearance = cq.Solid.makeCylinder(1.5, 14.0, (0.0, 0.0, -7.0), (0.0, 0.0, 1.0)).located(location)
    tool_envelope = cq.Solid.makeCylinder(1.5, 14.0, (0.0, 0.0, -7.0), (0.0, 0.0, 1.0)).located(location)
    outer_fillet_radius = 2.0 if kind == "output_adapter" else 1.0
    inner_fillet_radius = PASSIVE_INSERT_GEOMETRY["seat_fillet_radius_mm"]
    fillet_faces = _fillet_faces(workplane, outer_fillet_radius)
    fillet_faces.extend(_fillet_faces(workplane, inner_fillet_radius))
    fillet_faces = list({id(face): face for face in fillet_faces}.values())
    features: dict[str, Any] = {
        "axis": axis,
        "joint_axis": axis,
        "mounting_holes": mounting_holes,
        "circular_pattern": {"axis": axis, "holes": mounting_holes or [{"axis": axis, "face": register_face}]},
        "radial_register": {"axis": axis, "faces": [register_face]},
        "wall_check_probes": probes,
        "fastener_tool_envelopes": [tool_envelope],
        "m3_fastener_envelope": clearance,
        "source_horn_holes": tuple({"center_mm": (hole.x_mm, hole.y_mm), "diameter_mm": hole.diameter_mm} for hole in holes),
        "minimum_load_wall_mm": params.print_rules.minimum_load_wall_mm,
        "adapter_kind": kind,
        "official_horn_reference": "main-horn-25T-8holes-3D.STEP",
        "spline_geometry": "not_printed",
        "joint_frame": {
            "joint_id": joint_id,
            "side": _frame_map(params)[joint_id].side,
            "mirror_partner": _frame_map(params)[joint_id].mirror_partner,
            "orientation": _frame_map(params)[joint_id].orientation,
            "variant": _frame_map(params)[joint_id].variant,
            "translation_mm": _frame_map(params)[joint_id].translation_mm,
            "rotation_extrinsic_xyz_deg": _frame_map(params)[joint_id].rotation_extrinsic_xyz_deg,
        },
        "stress_relief_fillets": {
            "outer_radius_mm": 2.0 if kind == "output_adapter" else 1.0,
            "inner_radius_mm": inner_fillet_radius,
            "faces": fillet_faces,
            "face_radii_mm": tuple(
                float(face._geomAdaptor().MinorRadius()) if face.geomType() == "TORUS" else float(face._geomAdaptor().Radius())
                for face in fillet_faces
            ),
        },
    }
    if kind == "output_adapter":
        features.update({
            "leg_interface_envelope": reference,
            "mating_interface": {"source": reference["source_path"], "solid": reference["solid"], "status": reference["status"]},
        })
    else:
        g = PASSIVE_INSERT_GEOMETRY
        cavity = cq.Solid.makeCylinder(g["cavity_radius_mm"], g["cavity_depth_mm"], (0.0, 0.0, g["cavity_start_z_mm"]), (0.0, 0.0, 1.0)).located(location)
        seat = cq.Solid.makeCylinder(g["seat_outer_radius_mm"], 0.4, (0.0, 0.0, g["clearance_start_z_mm"]), (0.0, 0.0, 1.0)).cut(
            cq.Solid.makeCylinder(g["clearance_radius_mm"], 0.4, (0.0, 0.0, g["clearance_start_z_mm"]), (0.0, 0.0, 1.0))
        ).located(location)
        features.update({
            "insert_cavity": {"solid": cavity, "design_envelope_diameter_mm": 2.0 * g["cavity_radius_mm"], "printed_bearing_surface": False, "status": "provisional_until_insert_selected"},
            "insert_seat": {"solid": seat, "seat_outer_diameter_mm": 2.0 * g["seat_outer_radius_mm"], "status": "provisional_until_insert_selected"},
            "insert_clearance_envelope": cq.Solid.makeCylinder(g["clearance_radius_mm"], g["clearance_depth_mm"], (0.0, 0.0, g["clearance_start_z_mm"]), (0.0, 0.0, 1.0)).located(location),
            "passive_insert_outer_diameter_mm": g["passive_insert_outer_diameter_mm"],
            "passive_insert_length_mm": g["passive_insert_length_mm"],
            "unresolved_measurements": {
                "passive_insert_outer_diameter_mm": "requires_first_article_measurement",
                "passive_insert_length_mm": "requires_first_article_measurement",
            },
        })
    workplane.features = features
    return workplane


def _frame_transform(
    part: cq.Workplane, frame: JointFrame, frames: dict[int, JointFrame]
) -> tuple[cq.Workplane, cq.Location, bool]:
    mirrored = _should_mirror(frame, frames)
    if mirrored:
        part = part.mirror("XZ")
    location = cq.Location(frame.translation_mm, frame.rotation_extrinsic_xyz_deg)
    return cq.Workplane(obj=part.val().located(location)), location, mirrored


def _transform_shape(shape: cq.Shape, location: cq.Location, mirrored: bool) -> cq.Shape:
    if mirrored:
        shape = shape.mirror("XZ")
    return shape.located(location)


def _make_outer_mount_local(
    params: DesignParameters,
) -> tuple[cq.Workplane, tuple[tuple[float, float], ...]]:
    holes = _ha8_mount_hole_centers(params)
    hole_radius = params.ha8.mounting_hole_diameter_mm / 2.0
    wall = params.print_rules.minimum_load_wall_mm + 0.2
    x_values = [point[0] for point in holes]
    y_values = [point[1] for point in holes]
    outer_x = max(
        params.ha8.body_xyz_mm[0] + 2.0 * (wall + params.print_rules.moving_clearance_per_side_mm),
        max(x_values) - min(x_values) + 2.0 * (hole_radius + wall),
    )
    outer_y = max(y_values) - min(y_values) + 2.0 * (hole_radius + wall)
    thickness = 5.0
    mount = (
        cq.Workplane("XY")
        .box(outer_x, outer_y, thickness, centered=(True, True, True))
        .edges("|Z")
        .fillet(2.0)
    )
    body_opening = (
        cq.Workplane("XY")
        .box(
            params.ha8.body_xyz_mm[0]
            + 2.0 * params.print_rules.moving_clearance_per_side_mm,
            params.ha8.body_xyz_mm[1]
            + 2.0 * params.print_rules.moving_clearance_per_side_mm,
            thickness + 2.0,
            centered=(True, True, True),
        )
    )
    hole_cut = (
        cq.Workplane("XY")
        .pushPoints(holes)
        .circle(hole_radius)
        .extrude(thickness + 2.0, both=True)
    )
    return mount.cut(body_opening).cut(hole_cut), holes


def make_ha8_outer_mount(joint_id: int, params: DesignParameters) -> cq.Workplane:
    frames = _frame_map(params)
    if joint_id not in frames:
        raise ValueError("joint_id must be one of 1, 2, 3, or 4")
    frame = frames[joint_id]
    local, hole_centers = _make_outer_mount_local(params)
    part, location, mirrored = _frame_transform(local, frame, frames)
    hole_radius = params.ha8.mounting_hole_diameter_mm / 2.0
    hole_faces = _faces_at_radius(part, hole_radius)
    if len(hole_faces) != 4:
        raise ValueError(f"HA8 outer mount must retain four ear holes; got {len(hole_faces)}")
    hole_faces.sort(key=lambda face: (face.Center().x, face.Center().y))
    holes = [_hole_feature(face) for face in hole_faces]
    boundary_faces = []
    for face in part.val().Faces():
        if any(face.isSame(hole_face) for hole_face in hole_faces):
            continue
        if face.geomType() in {"CYLINDER", "TORUS"}:
            boundary_faces.append(face)
            continue
        if face.geomType() == "PLANE":
            normal = face.normalAt()
            if abs(normal.z) < 0.1:
                boundary_faces.append(face)
    wall_probes = []
    for index, hole_face in enumerate(hole_faces, start=1):
        candidates = [face for face in boundary_faces if face.distance(hole_face) > 1e-6]
        wall_probes.append(
            {
                "name": f"ear_hole_{index}_local_wall",
                "faces": [hole_face, min(candidates, key=lambda face: face.distance(hole_face))],
                "pair_type": "hole_to_nearest_owned_boundary",
            }
        )
    local_tools = [
        cq.Solid.makeCylinder(2.0, 12.0, (x, y, -6.0), (0.0, 0.0, 1.0))
        for x, y in hole_centers
    ]
    tool_envelopes = [
        _transform_shape(envelope, location, mirrored) for envelope in local_tools
    ]
    source = _original_part_reference(f"外固定{joint_id}.stl")
    part.features = {
        "mounting_holes": holes,
        "through_holes": {"HA8_4.3": holes[0]},
        "fastener_tool_envelopes": tool_envelopes,
        "wall_check_probes": wall_probes,
        "minimum_load_wall_mm": params.print_rules.minimum_load_wall_mm,
        "source_original_part": source["source_path"],
        "source_original_sha256": source["source_sha256"],
        "source_original_bounds_mm": source["bounds_mm"],
        "joint_frame": {
            "joint_id": joint_id,
            "side": frame.side,
            "mirror_partner": frame.mirror_partner,
            "translation_mm": frame.translation_mm,
            "rotation_extrinsic_xyz_deg": frame.rotation_extrinsic_xyz_deg,
        },
    }
    return part


def _ha8_body_sweep_local(params: DesignParameters) -> cq.Workplane:
    body_x, body_y, body_z = params.ha8.body_xyz_mm
    body = cq.Workplane("XY").box(body_x, body_y, body_z, centered=True)
    ear = cq.Workplane("XY").box(
        body_x + 10.0, params.ha8.ear_total_height_mm, 4.0, centered=True
    )
    return body.union(ear)


def ha8_body_sweep(joint_id: int, params: DesignParameters) -> cq.Workplane:
    frames = _frame_map(params)
    if joint_id not in frames:
        raise ValueError("joint_id must be one of 1, 2, 3, or 4")
    return _frame_transform(_ha8_body_sweep_local(params), frames[joint_id], frames)[0]


def _make_cover_local(
    params: DesignParameters,
) -> tuple[cq.Workplane, cq.Solid, float]:
    body_x, body_y, body_z = params.ha8.body_xyz_mm
    clearance = params.print_rules.moving_clearance_per_side_mm + 0.01
    thickness = 2.5
    edge_radius = 1.5
    outer_x = body_x + 8.0
    outer_y = body_y + 8.0
    center_z = body_z / 2.0 + clearance + thickness / 2.0
    cover = (
        cq.Workplane("XY")
        .box(outer_x, outer_y, thickness, centered=(True, True, True))
        .translate((0.0, 0.0, center_z))
        .edges("|Z")
        .fillet(edge_radius)
    )
    cable_envelope = cq.Solid.makeBox(
        8.0,
        12.0,
        thickness + 2.0,
        (-4.0, outer_y / 2.0 - 6.0, center_z - (thickness + 2.0) / 2.0),
    )
    return cover.cut(cq.Workplane(obj=cable_envelope)), cable_envelope, edge_radius


def make_ha8_cover(joint_id: int, params: DesignParameters) -> cq.Workplane:
    frames = _frame_map(params)
    if joint_id not in frames:
        raise ValueError("joint_id must be one of 1, 2, 3, or 4")
    frame = frames[joint_id]
    local, local_cable_envelope, edge_radius = _make_cover_local(params)
    part, location, mirrored = _frame_transform(local, frame, frames)
    cable_envelope = _transform_shape(local_cable_envelope, location, mirrored)
    source = _original_part_reference(f"盖板{joint_id}.stl")
    part.features = {
        "cable_exit_envelope": cable_envelope,
        "cable_exit_edge_radius_mm": edge_radius,
        "source_original_part": source["source_path"],
        "source_original_sha256": source["source_sha256"],
        "source_original_bounds_mm": source["bounds_mm"],
        "joint_frame": {
            "joint_id": joint_id,
            "side": frame.side,
            "mirror_partner": frame.mirror_partner,
            "translation_mm": frame.translation_mm,
            "rotation_extrinsic_xyz_deg": frame.rotation_extrinsic_xyz_deg,
        },
    }
    return part


def _build(kind: str, joint_id: int, params: DesignParameters) -> cq.Workplane:
    frames = _frame_map(params)
    try:
        frame = frames[joint_id]
    except KeyError as exc:
        raise ValueError("joint_id must be one of 1, 2, 3, or 4") from exc
    holes = _horn_holes()
    reference = _interface_reference(joint_id)
    if kind == "output_adapter":
        part = _make_interface_plate(holes, reference)
    elif kind == "passive_support":
        part = _make_support(holes)
    elif kind == "spacer":
        part = _make_spacer()
    else:
        raise ValueError(f"unknown HA8 adapter kind: {kind}")
    mirrored = _should_mirror(frame, frames)
    if mirrored:
        part = part.mirror("XZ")
    location = cq.Location(frame.translation_mm, frame.rotation_extrinsic_xyz_deg)
    final_solid = part.val().located(location)
    reference = dict(reference)
    reference_solid = reference["solid"]
    if mirrored:
        reference_solid = reference_solid.mirror("XZ")
    reference["solid"] = reference_solid.located(location)
    part = _attach_features(
        cq.Workplane(obj=final_solid),
        kind=kind,
        params=params,
        joint_id=joint_id,
        holes=holes,
        reference=reference,
        location=location,
    )
    part.features["joint_frame"]["applied_transform"] = {
        "translation_mm": frame.translation_mm,
        "rotation_extrinsic_xyz_deg": frame.rotation_extrinsic_xyz_deg,
    }
    return part


def make_ha8_output_adapter(joint_id: int, params: DesignParameters) -> cq.Workplane:
    return _build("output_adapter", joint_id, params)


def make_ha8_passive_support(joint_id: int, params: DesignParameters) -> cq.Workplane:
    return _build("passive_support", joint_id, params)


def make_ha8_spacer(joint_id: int, params: DesignParameters) -> cq.Workplane:
    return _build("spacer", joint_id, params)


__all__ = [
    "ha8_body_sweep",
    "make_ha8_cover",
    "make_ha8_outer_mount",
    "make_ha8_output_adapter",
    "make_ha8_passive_support",
    "make_ha8_spacer",
]
