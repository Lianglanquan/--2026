from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cadquery as cq

from .input_audit import HA8_BODY_STEP, HA8_HORN_STEP, MANIFEST
from .parameters import Ha8Dimensions, QD4310Dimensions, REPO_ROOT


REFERENCE_EXPORT_METADATA = {
    "reference_only": True,
    "manufacturing_export": False,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reference_metadata(**values: Any) -> dict[str, Any]:
    return {**REFERENCE_EXPORT_METADATA, **values}


def _axis_tuple(direction: Any) -> tuple[float, float, float]:
    if hasattr(direction, "toTuple"):
        values = tuple(float(value) for value in direction.toTuple())
    else:
        values = (float(direction.X()), float(direction.Y()), float(direction.Z()))
    return tuple(0.0 if abs(value) < 1e-12 else value for value in values)


def _largest_cylindrical_face_axis(
    geometry: cq.Workplane,
) -> tuple[cq.Vector, float, cq.Face, int]:
    cylindrical_faces = [
        (index, face)
        for index, face in enumerate(geometry.faces().vals())
        if face.geomType() == "CYLINDER"
    ]
    if not cylindrical_faces:
        raise ValueError("official STEP has no cylindrical face for axis verification")
    face_index, largest = max(
        cylindrical_faces,
        key=lambda item: item[1]._geomAdaptor().Radius(),
    )
    surface = largest._geomAdaptor()
    direction = surface.Axis().Direction()
    return (
        cq.Vector(direction.X(), direction.Y(), direction.Z()),
        surface.Radius(),
        largest,
        face_index,
    )


def _signed_output_axis(
    geometry: cq.Workplane,
    *,
    datum_role: str,
) -> tuple[cq.Vector, float, dict[str, Any]]:
    """Resolve cylinder polarity from the actual output-side mating topology."""

    unsigned_axis, radius_mm, cylinder_face, cylinder_face_index = (
        _largest_cylindrical_face_axis(geometry)
    )
    faces = geometry.faces().vals()
    cylinder_center = cylinder_face.Center()
    planar_neighbors = []
    cylinder_edges = cylinder_face.Edges()
    for index, face in enumerate(faces):
        if face.geomType() != "PLANE":
            continue
        shared_edges = sum(
            1
            for edge in cylinder_edges
            if any(edge.isSame(neighbor) for neighbor in face.Edges())
        )
        if shared_edges:
            datum_center = face.Center()
            delta = datum_center - cylinder_center
            projected = delta.dot(unsigned_axis)
            planar_neighbors.append(
                (projected, index, face, datum_center, shared_edges)
            )
    if not planar_neighbors:
        raise ValueError(
            "official STEP output cylinder has no planar mating datum neighbor"
        )

    # The output-side shoulder is the adjacent planar face behind the cylinder
    # along the unsigned axis. This uses shared topology, not a source-axis name.
    projected, datum_face_index, datum_face, datum_center, shared_edges = min(
        planar_neighbors, key=lambda item: item[0]
    )
    if abs(projected) < 1e-9:
        raise ValueError("output-side mating datum does not establish polarity")
    signed_axis = unsigned_axis if projected < 0.0 else -unsigned_axis

    cylinder_axis = cylinder_face._geomAdaptor().Axis()
    axis_location = cylinder_axis.Location()
    evidence = {
        "method": "output_datum_to_cylindrical_feature",
        "polarity_contract": "official_output_side_datum_shared_by_body_horn_pair",
        "datum_role": datum_role,
        "datum_face_index": datum_face_index,
        "datum_face_topology_verified": True,
        "datum_face_shared_edge_count": shared_edges,
        "datum_face_center_mm": _axis_tuple(datum_center),
        "datum_face_axis_coordinate_mm": datum_center.dot(unsigned_axis),
        "cylinder_face_index": cylinder_face_index,
        "cylinder_face_center_mm": _axis_tuple(cylinder_center),
        "cylinder_axis_location_mm": (
            axis_location.X(), axis_location.Y(), axis_location.Z()
        ),
        "source_radius_mm": radius_mm,
        "source_unsigned_cylinder_direction": _axis_tuple(unsigned_axis),
        "source_signed_direction": _axis_tuple(signed_axis),
        "datum_to_cylinder_projection_mm": projected,
    }
    return signed_axis, radius_mm, evidence


def _canonicalize_positive_axis(
    source_geometry: cq.Workplane,
    *,
    datum_role: str,
) -> tuple[cq.Workplane, dict[str, Any]]:
    source_axis, source_radius_mm, evidence = _signed_output_axis(
        source_geometry, datum_role=datum_role
    )
    target_axis = cq.Vector(0.0, 0.0, 1.0)
    dot = max(-1.0, min(1.0, source_axis.dot(target_axis)))
    angle_degrees = math.degrees(math.acos(dot))
    rotation_axis = source_axis.cross(target_axis)
    if rotation_axis.Length < 1e-12:
        rotation_axis = cq.Vector(1.0, 0.0, 0.0)
    canonical_geometry = source_geometry.rotate(
        (0.0, 0.0, 0.0),
        rotation_axis.toTuple(),
        angle_degrees,
    )
    canonical_axis, canonical_radius_mm, _, _ = _largest_cylindrical_face_axis(
        canonical_geometry
    )
    if abs(canonical_radius_mm - source_radius_mm) > 1e-9:
        raise ValueError("axis verification face changed during canonical transform")
    canonical_direction = _axis_tuple(canonical_axis)
    if any(
        abs(actual - expected) > 1e-9
        for actual, expected in zip(canonical_direction, (0.0, 0.0, 1.0))
    ):
        raise ValueError("official STEP output axis did not map to canonical +Z")
    return canonical_geometry, {
        **evidence,
        "canonical_direction": canonical_direction,
        "status": "verified_from_geometry",
    }


def _audited_step(relative_path: Path) -> tuple[Path, str]:
    manifest_path = REPO_ROOT / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {
        record["relative_path"]: record
        for record in manifest["files"]
        if isinstance(record, dict) and "relative_path" in record
    }
    relative = relative_path.as_posix()
    if relative not in records:
        raise ValueError(f"STEP is absent from the audited input manifest: {relative}")

    absolute_path = REPO_ROOT / relative_path
    actual_sha256 = _sha256(absolute_path)
    expected_sha256 = str(records[relative]["sha256"])
    if actual_sha256 != expected_sha256:
        raise ValueError(f"audited STEP hash changed: {relative}")
    return absolute_path, actual_sha256


def _canonical_step_reference(
    relative_path: Path,
    *,
    assembly_name: str,
    object_name: str,
) -> cq.Assembly:
    absolute_path, sha256 = _audited_step(relative_path)
    source_geometry = cq.importers.importStep(str(absolute_path))
    datum_role = (
        "body_output_boss_shoulder"
        if relative_path == HA8_BODY_STEP
        else "horn_output_mating_face"
    )
    canonical_geometry, axis_geometry_evidence = _canonicalize_positive_axis(
        source_geometry,
        datum_role=datum_role,
    )
    source_metadata = _reference_metadata(
        source_kind="official_step",
        source_path=relative_path.as_posix(),
        source_sha256=sha256,
        canonical_positive_axis="+Z",
        axis_geometry_evidence=axis_geometry_evidence,
    )
    assembly = cq.Assembly(name=assembly_name, metadata=dict(source_metadata))
    assembly.add(
        canonical_geometry,
        name=object_name,
        metadata=dict(source_metadata),
    )
    return assembly


def make_ha8_reference(dimensions: Ha8Dimensions) -> cq.Assembly:
    """Import the audited HA8 body as canonical +Z reference geometry."""

    if dimensions.output_spline_teeth != 25:
        raise ValueError("HA8 reference requires the approved 25T output spline")
    return _canonical_step_reference(
        HA8_BODY_STEP,
        assembly_name="REF_HA8_ASSEMBLY",
        object_name="REF_HA8_OFFICIAL_BODY",
    )


def import_ha8_horn_reference(path: Path | str | None = None) -> cq.Assembly:
    """Import the audited official 25T horn without modifying its source file."""

    relative_path = HA8_HORN_STEP
    if path is not None:
        candidate = Path(path)
        absolute_candidate = (
            candidate if candidate.is_absolute() else REPO_ROOT / candidate
        )
        if absolute_candidate.resolve() != (REPO_ROOT / HA8_HORN_STEP).resolve():
            raise ValueError("HA8 horn reference must use the audited official STEP")
    return _canonical_step_reference(
        relative_path,
        assembly_name="REF_HA8_HORN_ASSEMBLY",
        object_name="REF_HA8_OFFICIAL_25T_HORN",
    )


def _qd4310_stator_axes(
    dimensions: QD4310Dimensions,
) -> tuple[dict[str, Any], ...]:
    radius = dimensions.stator_bcd_mm / 2.0
    axes = []
    for index in range(dimensions.stator_hole_count):
        angle = 2.0 * math.pi * index / dimensions.stator_hole_count
        axes.append(
            {
                "name": f"REF_QD4310_STATOR_HOLE_AXIS_{index + 1}",
                "origin": (radius * math.cos(angle), radius * math.sin(angle), 0.0),
                "direction": (0.0, 0.0, 1.0),
            }
        )
    return tuple(axes)


def _nominal_metric_thread_radius_mm(thread: str) -> float:
    try:
        diameter = float(thread.removeprefix("M").split("x", 1)[0])
    except ValueError as error:
        raise ValueError(f"unsupported metric thread specification: {thread}") from error
    return diameter / 2.0


def make_qd4310_reference(dimensions: QD4310Dimensions) -> cq.Assembly:
    """Build non-manufacturing QD4310 references with explicit evidence status."""

    radius = dimensions.outer_diameter_mm / 2.0
    half_width = dimensions.total_width_mm / 2.0
    nominal_stator_thread_radius = _nominal_metric_thread_radius_mm(
        dimensions.stator_thread
    )
    stator_envelope_radius = (
        dimensions.stator_bcd_mm / 2.0 + nominal_stator_thread_radius
    )
    if stator_envelope_radius >= radius:
        raise ValueError("QD4310 stator envelope must fit inside the outer diameter")

    stator = (
        cq.Workplane("XY", origin=(0.0, 0.0, -half_width))
        .circle(stator_envelope_radius)
        .extrude(dimensions.total_width_mm)
    )
    rotor_sweep = (
        cq.Workplane("XY", origin=(0.0, 0.0, -half_width))
        .circle(radius)
        .circle(stator_envelope_radius)
        .extrude(dimensions.total_width_mm)
    )
    stator_axes = _qd4310_stator_axes(dimensions)
    rotor_front_axis_result = {
        "status": "unresolved",
        "expected_count": dimensions.rotor_hole_count,
        "thread": dimensions.rotor_thread,
        "bcd_mm": None,
        "axes": (),
        "reason": "approved handbook does not uniquely state rotor hole BCD",
    }
    unresolved_rotor_pattern = {
        "count": dimensions.rotor_hole_count,
        "thread": dimensions.rotor_thread,
        "bcd_mm": None,
        "axes": (),
        "status": "unresolved",
    }
    unresolved_measurements = {
        "rotor_hole_bcd_mm": {
            "value_mm": None,
            "status": "unresolved",
            "measurement_method": (
                "obtain a dimensioned manufacturer drawing or measure the motor"
            ),
            "reason": (
                "the approved handbook dimensions specify eight M3 rotor holes "
                "but do not uniquely state their pitch-circle diameter"
            ),
        },
        "stator_envelope_radius_mm": {
            "value_mm": stator_envelope_radius,
            "status": "provisional",
            "verified": False,
            "derivation": "stator_bcd_radius_plus_nominal_m2_5_radius",
            "reason": (
                "the handbook verifies the stator hole BCD and thread but not "
                "the stator body radius or rotor/stator ownership boundary"
            ),
        },
    }
    assembly_metadata = _reference_metadata(
        source_kind="handbook_dimensions_with_provisional_internal_split",
        canonical_positive_axis="+Z",
        axis={"origin": (0.0, 0.0, 0.0), "direction": (0.0, 0.0, 1.0)},
        collision_envelope_result={
            "status": "provisional",
            "verified": False,
            "reason": (
                "outer diameter and total width are verified, but the internal "
                "stator/rotor split radius is provisional"
            ),
        },
        stator_hole_pattern={
            "count": dimensions.stator_hole_count,
            "thread": dimensions.stator_thread,
            "bcd_mm": dimensions.stator_bcd_mm,
            "axes": stator_axes,
        },
        rotor_hole_pattern=unresolved_rotor_pattern,
        rotor_front_axis_result=rotor_front_axis_result,
        unresolved_measurements=unresolved_measurements,
    )
    assembly = cq.Assembly(
        name="REF_QD4310_ASSEMBLY",
        metadata=assembly_metadata,
    )
    assembly.add(
        stator,
        name="REF_QD4310_STATOR_ENVELOPE",
        metadata=_reference_metadata(
            source_kind="provisional_stator_interface_envelope",
            canonical_positive_axis="+Z",
            geometry_status="provisional",
            collision_envelope_verified=False,
            radius_mm=stator_envelope_radius,
        ),
    )
    assembly.add(
        rotor_sweep,
        name="REF_QD4310_ROTOR_SWEEP",
        metadata=_reference_metadata(
            source_kind="provisional_rotor_sweep_envelope",
            canonical_positive_axis="+Z",
            geometry_status="provisional",
            collision_envelope_verified=False,
        ),
    )
    for axis in stator_axes:
        x, y, _ = axis["origin"]
        assembly.add(
            cq.Edge.makeLine(
                cq.Vector(x, y, -half_width),
                cq.Vector(x, y, half_width),
            ),
            name=axis["name"],
            metadata=_reference_metadata(
                source_kind="verified_stator_hole_axis",
                axis=axis,
            ),
        )
    return assembly


__all__ = [
    "import_ha8_horn_reference",
    "make_ha8_reference",
    "make_qd4310_reference",
]
