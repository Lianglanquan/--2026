from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

import cadquery as cq

from .input_audit import MANIFEST, ORIGINAL_SOURCE
from .parameters import DesignParameters, REPO_ROOT


Side = Literal["left", "right"]


def _manifest() -> dict[str, Any]:
    return json.loads((REPO_ROOT / MANIFEST).read_text(encoding="utf-8"))


def _source_reference(file_name: str) -> dict[str, Any]:
    relative = (ORIGINAL_SOURCE / "01_原版STL" / file_name).as_posix()
    manifest = _manifest()
    record = next(item for item in manifest["files"] if item["relative_path"] == relative)
    source = REPO_ROOT / relative
    sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    if sha256 != record["sha256"]:
        raise ValueError(f"audited STL hash changed: {relative}")
    return {
        "source_path": relative,
        "source_sha256": sha256,
        "source_bounds_mm": manifest["original_stl_geometry"][relative]["bounding_box_mm"],
    }


def _cylinder_faces(part: cq.Workplane, radius: float) -> list[cq.Face]:
    faces = []
    for face in part.val().Faces():
        if face.geomType() != "CYLINDER":
            continue
        try:
            actual_radius = float(face._geomAdaptor().Radius())
        except AttributeError:
            continue
        if math.isclose(actual_radius, radius, abs_tol=1e-5):
            faces.append(face)
    return faces


def _hole_feature(face: cq.Face) -> dict[str, Any]:
    axis = face._geomAdaptor().Axis()
    origin = axis.Location()
    direction = axis.Direction()
    return {
        "face": face,
        "axis": {
            "origin": (origin.X(), origin.Y(), origin.Z()),
            "direction": (direction.X(), direction.Y(), direction.Z()),
        },
    }


def _build_stator_mount_local(params: DesignParameters) -> cq.Workplane:
    dimensions = params.qd4310
    plate_radius = dimensions.outer_diameter_mm / 2.0 + 2.0
    thickness = 5.0
    register_radius = dimensions.stator_bcd_mm / 2.0 + 0.25
    hole_radius = 1.35
    base = cq.Workplane("XY").circle(plate_radius).extrude(thickness)
    pocket = (
        cq.Workplane("XY")
        .circle(register_radius)
        .extrude(2.0)
        .translate((0.0, 0.0, thickness - 2.0))
    )
    hole_points = []
    for index in range(dimensions.stator_hole_count):
        angle = 2.0 * math.pi * index / dimensions.stator_hole_count
        radius = dimensions.stator_bcd_mm / 2.0
        hole_points.append((radius * math.cos(angle), radius * math.sin(angle)))
    holes = (
        cq.Workplane("XY")
        .pushPoints(hole_points)
        .circle(hole_radius)
        .extrude(thickness + 2.0, both=True)
    )
    # Two opposed slots make the cable route genuinely open and preserve the
    # same geometry for the left/right mirrored variants.
    cable_slot = (
        cq.Workplane("XY")
        .box(4.0, 8.0, thickness + 2.0, centered=(True, True, True))
        .translate((plate_radius - 2.0, 0.0, thickness / 2.0))
    )
    cable_slot = cable_slot.union(
        cq.Workplane("XY")
        .box(4.0, 8.0, thickness + 2.0, centered=(True, True, True))
        .translate((-(plate_radius - 2.0), 0.0, thickness / 2.0))
    )
    return base.cut(pocket).cut(holes).cut(cable_slot)


def make_qd4310_stator_mount(side: Side, params: DesignParameters) -> cq.Workplane:
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    part = _build_stator_mount_local(params)
    hole_faces = _cylinder_faces(part, 1.35)
    if len(hole_faces) != params.qd4310.stator_hole_count:
        raise ValueError(
            "QD4310 stator mount must retain four owned M2.5 hole faces; "
            f"got {len(hole_faces)}"
        )
    hole_faces.sort(key=lambda face: math.atan2(face.Center().y, face.Center().x))
    mounting_holes = [_hole_feature(face) for face in hole_faces]
    register_faces = _cylinder_faces(part, params.qd4310.stator_bcd_mm / 2.0 + 0.25)
    if not register_faces:
        raise ValueError("QD4310 stator mount lost its locating pocket face")
    register_face = max(register_faces, key=lambda face: face.Area())
    cable_envelope = cq.Solid.makeBox(
        4.0,
        8.0,
        7.0,
        (params.qd4310.outer_diameter_mm / 2.0, -4.0, -1.0),
    )
    tool_envelopes = []
    for hole in mounting_holes:
        origin = hole["axis"]["origin"]
        tool_envelopes.append(
            cq.Solid.makeCylinder(1.35, 9.0, (origin[0], origin[1], -2.0), (0.0, 0.0, 1.0))
        )
    source = _source_reference("电机固定X1.stl" if side == "left" else "电机固定X2.stl")
    part.features = {
        "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "wheel_axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "mounting_holes": mounting_holes,
        "through_holes": {"M2.5": mounting_holes[0]},
        "circular_pattern": {
            "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
            "holes": mounting_holes,
        },
        "radial_register": {
            "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
            "faces": [register_face],
        },
        "fastener_tool_envelopes": tool_envelopes,
        "cable_exit_envelope": cable_envelope,
        "cable_exit_status": "outside_rotor_sweep",
        "stator_register_diameter_mm": 2.0 * (params.qd4310.stator_bcd_mm / 2.0 + 0.25),
        "stator_bcd_mm": params.qd4310.stator_bcd_mm,
        "stator_hole_count": params.qd4310.stator_hole_count,
        "stator_thread": params.qd4310.stator_thread,
        "rotor_hole_bcd_mm": None,
        "rotor_hole_status": "unresolved",
        "source_original_part": source["source_path"],
        "source_original_sha256": source["source_sha256"],
        "source_original_bounds_mm": source["source_bounds_mm"],
        "side": side,
        "reinforcement": "continuous_outer_ring_behind_stator_mount",
    }
    return part


def _rotor_slot_points(count: int, inner_radius: float, outer_radius: float) -> list[tuple[float, float]]:
    points = []
    radius = (inner_radius + outer_radius) / 2.0
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        points.append((radius * math.cos(angle), radius * math.sin(angle)))
    return points


def make_qd4310_rotor_hub(side: Side, params: DesignParameters) -> cq.Workplane:
    """Build a provisional rotor hub without inventing the unverified rotor BCD."""

    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    wheel_radius = params.original.wheel_outer_diameter_mm / 2.0
    hub_radius = min(wheel_radius - 1.0, 30.0)
    thickness = 4.0
    register_radius = params.qd4310.outer_diameter_mm / 2.0 - 1.0
    hub = cq.Workplane("XY").circle(hub_radius).extrude(thickness)
    register = (
        cq.Workplane("XY")
        .circle(register_radius)
        .extrude(1.2)
        .translate((0.0, 0.0, thickness))
    )
    # The handbook confirms eight M3 rotor holes but not their BCD.  A named
    # provisional pitch circle is used only to keep the digital adapter
    # inspectable; it remains explicitly unresolved in the returned metadata.
    provisional_hole_radius = (register_radius + hub_radius) / 2.0
    provisional_points = [
        (
            provisional_hole_radius * math.cos(2.0 * math.pi * index / params.qd4310.rotor_hole_count),
            provisional_hole_radius * math.sin(2.0 * math.pi * index / params.qd4310.rotor_hole_count),
        )
        for index in range(params.qd4310.rotor_hole_count)
    ]
    slots = (
        cq.Workplane("XY")
        .pushPoints(provisional_points)
        .circle(1.7)
        .extrude(thickness + 2.0, both=True)
    )
    center_bore = cq.Workplane("XY").circle(3.0).extrude(thickness + 2.0, both=True)
    hub = hub.union(register).cut(slots).cut(center_bore)
    hole_faces = []
    for face in hub.val().Faces():
        if face.geomType() != "CYLINDER":
            continue
        try:
            radius = float(face._geomAdaptor().Radius())
        except AttributeError:
            continue
        if math.isclose(radius, 1.7, abs_tol=1e-5):
            hole_faces.append(face)
    if len(hole_faces) != params.qd4310.rotor_hole_count:
        raise ValueError(
            "provisional QD4310 rotor hub must expose eight M3 slot end faces; "
            f"got {len(hole_faces)}"
        )
    hole_faces.sort(key=lambda face: math.atan2(face.Center().y, face.Center().x))
    hole_metadata = [_hole_feature(face) for face in hole_faces]
    register_faces = _cylinder_faces(hub, register_radius)
    register_face = max(register_faces, key=lambda face: face.Area())
    source = _source_reference("轮毂X1.stl" if side == "left" else "轮毂X2.stl")
    hub.features = {
        "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "wheel_axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "mounting_holes": hole_metadata,
        "circular_pattern": {
            "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
            "holes": hole_metadata,
        },
        "radial_register": {
            "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
            "faces": [register_face],
        },
        "rotor_hole_count": params.qd4310.rotor_hole_count,
        "rotor_hole_bcd_mm": None,
        "rotor_hole_status": "unresolved",
        "manufacturing_status": "provisional_until_rotor_bcd_measured",
        "provisional_hole_center_radius_mm": provisional_hole_radius,
        "source_original_part": source["source_path"],
        "source_original_sha256": source["source_sha256"],
        "source_original_bounds_mm": source["source_bounds_mm"],
        "side": side,
    }
    return hub


def make_qd4310_wheel_retainer(side: Side, params: DesignParameters) -> cq.Workplane:
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    outer_radius = params.original.wheel_outer_diameter_mm / 2.0 - 1.0
    inner_radius = outer_radius - 3.0
    retainer = (
        cq.Workplane("XY")
        .circle(outer_radius)
        .circle(inner_radius)
        .extrude(2.0)
    )
    source = _source_reference("轮固定X1.stl" if side == "left" else "轮固定X2.stl")
    retainer.features = {
        "axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "wheel_axis": {"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        "source_original_part": source["source_path"],
        "source_original_sha256": source["source_sha256"],
        "source_original_bounds_mm": source["source_bounds_mm"],
        "side": side,
        "function": "retain_original_tire_inner_interface",
    }
    return retainer


def make_wheel_subassembly(side: Side, params: DesignParameters) -> cq.Assembly:
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    hub = make_qd4310_rotor_hub(side, params)
    retainer = make_qd4310_wheel_retainer(side, params)
    tire = (
        cq.Workplane("XY")
        .circle(params.original.wheel_outer_diameter_mm / 2.0)
        .circle(params.original.wheel_outer_diameter_mm / 2.0 - 5.0)
        .extrude(params.original.wheel_width_mm)
        .translate((0.0, 0.0, -params.original.wheel_width_mm / 2.0))
    )
    assembly = cq.Assembly(name=f"QD4310_WHEEL_SUBASSEMBLY_{side}")
    assembly.add(hub, name=f"QD4310_ROTOR_HUB_{side}")
    assembly.add(retainer, name=f"QD4310_WHEEL_RETAINER_{side}", loc=cq.Location((0.0, 0.0, -2.0)))
    assembly.add(tire, name=f"ORIGINAL_WHEEL_ENVELOPE_{side}")
    assembly.metadata = {
        "side": side,
        "reference_wheel_outer_diameter_mm": params.original.wheel_outer_diameter_mm,
        "reference_wheel_width_mm": params.original.wheel_width_mm,
        "rotor_hole_bcd_mm": None,
        "status": "digital_assembly_provisional_until_rotor_bcd_measured",
    }
    return assembly


__all__ = [
    "make_qd4310_rotor_hub",
    "make_qd4310_stator_mount",
    "make_qd4310_wheel_retainer",
    "make_wheel_subassembly",
]
