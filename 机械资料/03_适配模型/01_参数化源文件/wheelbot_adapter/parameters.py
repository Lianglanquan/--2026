from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar, Mapping

import numpy as np
import trimesh

from .input_audit import MANIFEST as INPUT_MANIFEST


REPO_ROOT = Path(__file__).resolve().parents[4]
DESIGN_SPEC = Path(
    "docs/superpowers/specs/2026-09-16-ha8-qd4310-mechanical-adapter-design.md"
)
HA8_MANUAL = Path(
    "机械资料/02_华馨京_HA8-U25H-M/02_尺寸图_DWG_PDF/"
    "Fashion-Star-HA8-U25H-M.pdf"
)
HA8_DIMENSION_DRAWING = Path(
    "机械资料/02_华馨京_HA8-U25H-M/02_尺寸图_DWG_PDF/"
    "ha8-hp8-hx8-series-dimension.pdf"
)
QD4310_MANUAL = Path("QD4310使用手册.pdf")
LEFT_WHEEL_MESH = Path(
    "机械资料/01_灯哥小型轮足/02_Seeed官方URDF_STL/meshes/LW_link.STL"
)
RIGHT_WHEEL_MESH = Path(
    "机械资料/01_灯哥小型轮足/02_Seeed官方URDF_STL/meshes/RW__link.STL"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SourceReference:
    relative_path: str
    page_or_section: str
    sha256: str
    note: str


def _freeze_provenance(
    owner: object,
    provenance: Mapping[str, SourceReference],
    authoritative_fields: tuple[str, ...],
) -> None:
    missing = set(authoritative_fields) - set(provenance)
    extra = set(provenance) - set(authoritative_fields)
    if missing or extra:
        raise ValueError(
            f"invalid provenance keys; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    object.__setattr__(owner, "provenance", MappingProxyType(dict(provenance)))


def _source_for(
    provenance: Mapping[str, SourceReference], field_name: str
) -> SourceReference:
    try:
        return provenance[field_name]
    except KeyError as exc:
        raise ValueError(f"unknown authoritative field: {field_name}") from exc


@dataclass(frozen=True)
class Ha8Dimensions:
    body_xyz_mm: tuple[float, float, float]
    ear_total_height_mm: float
    mounting_hole_diameter_mm: float
    output_spline_teeth: int
    passive_thread: str
    provenance: Mapping[str, SourceReference]

    authoritative_fields: ClassVar[tuple[str, ...]] = (
        "body_xyz_mm",
        "ear_total_height_mm",
        "mounting_hole_diameter_mm",
        "output_spline_teeth",
        "passive_thread",
    )

    def __post_init__(self) -> None:
        _freeze_provenance(self, self.provenance, self.authoritative_fields)

    def source_for(self, field_name: str) -> SourceReference:
        return _source_for(self.provenance, field_name)


@dataclass(frozen=True)
class QD4310Dimensions:
    outer_diameter_mm: float
    total_width_mm: float
    stator_bcd_mm: float
    stator_hole_count: int
    stator_thread: str
    rotor_hole_count: int
    rotor_thread: str
    provenance: Mapping[str, SourceReference]

    authoritative_fields: ClassVar[tuple[str, ...]] = (
        "outer_diameter_mm",
        "total_width_mm",
        "stator_bcd_mm",
        "stator_hole_count",
        "stator_thread",
        "rotor_hole_count",
        "rotor_thread",
    )

    def __post_init__(self) -> None:
        _freeze_provenance(self, self.provenance, self.authoritative_fields)

    def source_for(self, field_name: str) -> SourceReference:
        return _source_for(self.provenance, field_name)


@dataclass(frozen=True)
class PrintRules:
    moving_clearance_per_side_mm: float
    locating_clearance_per_side_mm: float
    minimum_load_wall_mm: float
    provenance: Mapping[str, SourceReference]

    authoritative_fields: ClassVar[tuple[str, ...]] = (
        "moving_clearance_per_side_mm",
        "locating_clearance_per_side_mm",
        "minimum_load_wall_mm",
    )

    def __post_init__(self) -> None:
        _freeze_provenance(self, self.provenance, self.authoritative_fields)

    def source_for(self, field_name: str) -> SourceReference:
        return _source_for(self.provenance, field_name)


@dataclass(frozen=True)
class PartBoundingBox:
    relative_path: str
    minimum_mm: tuple[float, float, float]
    maximum_mm: tuple[float, float, float]
    extents_mm: tuple[float, float, float]
    sha256: str


@dataclass(frozen=True)
class OriginalEnvelope:
    wheel_outer_diameter_mm: float
    wheel_width_mm: float
    wheel_envelope_method: str
    wheel_meshes: tuple[str, str]
    wheel_mesh_bounding_boxes: tuple[PartBoundingBox, PartBoundingBox]
    original_part_bounding_boxes: tuple[PartBoundingBox, ...]


@dataclass(frozen=True)
class MeasuredFitAllowance:
    name: str
    value_mm: float | None
    status: str
    measurement_method: str
    reason: str


@dataclass(frozen=True)
class ReferenceMeasurement:
    name: str
    value_mm: tuple[float, float, float] | None
    status: str
    measurement_method: str
    reason: str


@dataclass(frozen=True)
class ReferenceConvention:
    robot_axes: Mapping[str, str]
    joint_local_positive_axis: str
    wheel_local_positive_axis: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "robot_axes", MappingProxyType(dict(self.robot_axes))
        )


@dataclass(frozen=True)
class JointFrame:
    joint_id: int
    frame_name: str
    side: str
    mirror_partner: int
    source_part: str
    source_relative_path: str
    translation_mm: tuple[float, float, float]
    rotation_extrinsic_xyz_deg: tuple[float, float, float]
    canonical_rotation_axis: str
    orientation: str
    variant: str
    transform_role: str
    assembly_placement_status: str


@dataclass(frozen=True)
class WheelFrame:
    side: str
    frame_name: str
    source_part: str
    source_relative_path: str
    translation_mm: tuple[float, float, float]
    rotation_extrinsic_xyz_deg: tuple[float, float, float]
    source_bounds_min_mm: tuple[float, float, float]
    source_bounds_max_mm: tuple[float, float, float]
    source_center_plane_mm: float
    source_axis_sign: float
    canonical_rotation_axis: str
    orientation: str
    variant: str
    mirror_partner: str
    transform_role: str
    assembly_placement_status: str


@dataclass(frozen=True)
class DesignParameters:
    ha8: Ha8Dimensions
    qd4310: QD4310Dimensions
    print_rules: PrintRules
    original: OriginalEnvelope
    reference_convention: ReferenceConvention
    joint_frames: tuple[JointFrame, ...]
    wheel_frames: tuple[WheelFrame, ...]
    measured_fit_allowances: tuple[MeasuredFitAllowance, ...]
    reference_measurements: tuple[ReferenceMeasurement, ...]
    input_manifest_relative_path: str
    input_manifest_sha256: str

    def reference_measurement(self, name: str) -> ReferenceMeasurement:
        for item in self.reference_measurements:
            if item.name == name:
                return item
        raise ValueError(f"unknown reference measurement: {name}")


def _load_manifest() -> dict[str, object]:
    manifest_path = REPO_ROOT / INPUT_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported input manifest schema")
    return manifest


def _file_records(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("input manifest has no file records")
    return {
        str(record["relative_path"]): record
        for record in records
        if isinstance(record, dict) and "relative_path" in record
    }


def _manifest_source(
    records: Mapping[str, dict[str, object]],
    path: Path,
    page_or_section: str,
    note: str,
) -> SourceReference:
    relative_path = path.as_posix()
    try:
        record = records[relative_path]
    except KeyError as exc:
        raise ValueError(
            f"source is absent from input manifest: {relative_path}"
        ) from exc
    return SourceReference(
        relative_path=relative_path,
        page_or_section=page_or_section,
        sha256=str(record["sha256"]),
        note=note,
    )


def _repo_source(path: Path, section: str, note: str) -> SourceReference:
    absolute_path = REPO_ROOT / path
    return SourceReference(
        relative_path=path.as_posix(),
        page_or_section=section,
        sha256=_sha256(absolute_path),
        note=note,
    )


def _mesh_bounding_box(
    relative_path: Path,
    records: Mapping[str, dict[str, object]],
) -> PartBoundingBox:
    relative = relative_path.as_posix()
    try:
        expected_sha = str(records[relative]["sha256"])
    except KeyError as exc:
        raise ValueError(
            f"wheel mesh is absent from input manifest: {relative}"
        ) from exc

    absolute_path = REPO_ROOT / relative_path
    actual_sha = _sha256(absolute_path)
    if actual_sha != expected_sha:
        raise ValueError(f"audited wheel mesh hash changed: {relative}")

    mesh = trimesh.load(absolute_path, file_type="stl", force="mesh", process=False)
    if not isinstance(mesh, trimesh.Trimesh) or mesh.bounds is None:
        raise ValueError(f"unable to parse audited wheel mesh: {relative}")
    minimum = np.asarray(mesh.bounds[0], dtype=float)
    maximum = np.asarray(mesh.bounds[1], dtype=float)
    extents = maximum - minimum
    if not np.isfinite(extents).all() or np.any(extents <= 0.0):
        raise ValueError(f"invalid audited wheel mesh bounds: {relative}")
    return PartBoundingBox(
        relative_path=relative,
        minimum_mm=tuple(float(value * 1000.0) for value in minimum),
        maximum_mm=tuple(float(value * 1000.0) for value in maximum),
        extents_mm=tuple(float(value * 1000.0) for value in extents),
        sha256=actual_sha,
    )


def _original_part_boxes(
    manifest: dict[str, object], records: Mapping[str, dict[str, object]]
) -> tuple[PartBoundingBox, ...]:
    geometry = manifest.get("original_stl_geometry")
    if not isinstance(geometry, dict) or len(geometry) != 29:
        raise ValueError("input manifest must contain 29 original STL bounding boxes")

    boxes: list[PartBoundingBox] = []
    for relative_path in sorted(geometry):
        item = geometry[relative_path]
        if not isinstance(item, dict) or not isinstance(
            item.get("bounding_box_mm"), dict
        ):
            raise ValueError(f"invalid original STL geometry: {relative_path}")
        bounding_box = item["bounding_box_mm"]
        boxes.append(
            PartBoundingBox(
                relative_path=relative_path,
                minimum_mm=tuple(float(value) for value in bounding_box["minimum"]),
                maximum_mm=tuple(float(value) for value in bounding_box["maximum"]),
                extents_mm=tuple(float(value) for value in bounding_box["extents"]),
                sha256=str(records[relative_path]["sha256"]),
            )
        )
    return tuple(boxes)


def load_parameters() -> DesignParameters:
    """Load authoritative dimensions and hash-verified geometry references."""

    manifest = _load_manifest()
    records = _file_records(manifest)
    ha8_manual_page_1 = _manifest_source(
        records,
        HA8_MANUAL,
        "product page 1",
        "HA8 basic parameters table",
    )
    ha8_manual_page_3 = _manifest_source(
        records,
        HA8_MANUAL,
        "drawing page 3 (PDF page 6)",
        "HA8 exterior dimension drawing",
    )
    ha8_drawing_page_1 = _manifest_source(
        records,
        HA8_DIMENSION_DRAWING,
        "drawing page 1",
        "HA8 single-shaft exterior dimension drawing",
    )
    qd4310_page_6 = _manifest_source(
        records,
        QD4310_MANUAL,
        "manual page 6",
        "QD4310 product dimension drawing",
    )
    print_rule_source = _repo_source(
        DESIGN_SPEC,
        "section 8",
        "approved first-print manufacturing rules",
    )

    left_wheel = _mesh_bounding_box(LEFT_WHEEL_MESH, records)
    right_wheel = _mesh_bounding_box(RIGHT_WHEEL_MESH, records)
    diameter_values = (
        left_wheel.extents_mm[0],
        left_wheel.extents_mm[2],
        right_wheel.extents_mm[0],
        right_wheel.extents_mm[2],
    )
    width_values = (left_wheel.extents_mm[1], right_wheel.extents_mm[1])
    wheel_outer_diameter_mm = max(diameter_values)
    wheel_width_mm = max(width_values)
    if abs(wheel_outer_diameter_mm - 66.0) > 0.2:
        raise ValueError("audited wheel diameter does not match the approved envelope")
    if abs(wheel_width_mm - 29.9) > 0.2:
        raise ValueError("audited wheel width does not match the approved envelope")

    local_identity = (0.0, 0.0, 0.0)
    joint_frames = tuple(
        JointFrame(
            joint_id=joint_id,
            frame_name=f"joint_{joint_id}",
            side="left" if joint_id in {1, 3} else "right",
            mirror_partner={1: 2, 2: 1, 3: 4, 4: 3}[joint_id],
            source_part=f"舵机接口{joint_id}.stl",
            source_relative_path=(
                "机械资料/01_灯哥小型轮足/01_原版STL/"
                f"舵机接口{joint_id}.stl"
            ),
            translation_mm=local_identity,
            rotation_extrinsic_xyz_deg=local_identity,
            canonical_rotation_axis="+Z",
            orientation="canonical_positive_axis",
            variant="front_mirror_pair" if joint_id in {1, 2} else "rear_mirror_pair",
            transform_role="center_preservation_local_identity_no_assembly_placement",
            assembly_placement_status="unresolved",
        )
        for joint_id in (1, 2, 3, 4)
    )
    wheel_frames = (
        WheelFrame(
            side="left",
            frame_name="wheel_left",
            source_part="LW_link.STL",
            source_relative_path=LEFT_WHEEL_MESH.as_posix(),
            rotation_extrinsic_xyz_deg=(90.0, 0.0, 0.0),
            source_bounds_min_mm=left_wheel.minimum_mm,
            source_bounds_max_mm=left_wheel.maximum_mm,
            source_center_plane_mm=(left_wheel.minimum_mm[1] + left_wheel.maximum_mm[1]) / 2.0,
            source_axis_sign=1.0,
            canonical_rotation_axis="+Z",
            orientation="source_positive_y_to_canonical_positive_z",
            variant="left_source_mesh",
            mirror_partner="right",
            translation_mm=(0.0, 0.0, -(left_wheel.minimum_mm[1] + left_wheel.maximum_mm[1]) / 2.0),
            transform_role="source_y_to_canonical_z_and_center_plane_to_origin",
            assembly_placement_status="unresolved",
        ),
        WheelFrame(
            side="right",
            frame_name="wheel_right",
            source_part="RW__link.STL",
            source_relative_path=RIGHT_WHEEL_MESH.as_posix(),
            translation_mm=(
                0.0,
                0.0,
                (right_wheel.minimum_mm[1] + right_wheel.maximum_mm[1]) / 2.0,
            ),
            rotation_extrinsic_xyz_deg=(-90.0, 0.0, 0.0),
            source_bounds_min_mm=right_wheel.minimum_mm,
            source_bounds_max_mm=right_wheel.maximum_mm,
            source_center_plane_mm=(right_wheel.minimum_mm[1] + right_wheel.maximum_mm[1]) / 2.0,
            source_axis_sign=-1.0,
            canonical_rotation_axis="+Z",
            orientation="mirrored_source_negative_y_to_canonical_positive_z",
            variant="right_mirror_of_left_source_mesh",
            mirror_partner="left",
            transform_role="mirror_y_of_left_axis_and_center_datum",
            assembly_placement_status="unresolved",
        ),
    )

    return DesignParameters(
        ha8=Ha8Dimensions(
            body_xyz_mm=(40.0, 20.0, 40.0),
            ear_total_height_mm=56.0,
            mounting_hole_diameter_mm=4.3,
            output_spline_teeth=25,
            passive_thread="M3",
            provenance={
                "body_xyz_mm": ha8_manual_page_1,
                "ear_total_height_mm": ha8_manual_page_3,
                "mounting_hole_diameter_mm": ha8_manual_page_3,
                "output_spline_teeth": ha8_manual_page_1,
                "passive_thread": ha8_drawing_page_1,
            },
        ),
        qd4310=QD4310Dimensions(
            outer_diameter_mm=49.0,
            total_width_mm=26.7,
            stator_bcd_mm=38.5,
            stator_hole_count=4,
            stator_thread="M2.5x0.45",
            rotor_hole_count=8,
            rotor_thread="M3x0.5",
            provenance={
                field_name: qd4310_page_6
                for field_name in QD4310Dimensions.authoritative_fields
            },
        ),
        print_rules=PrintRules(
            moving_clearance_per_side_mm=0.20,
            locating_clearance_per_side_mm=0.10,
            minimum_load_wall_mm=3.0,
            provenance={
                field_name: print_rule_source
                for field_name in PrintRules.authoritative_fields
            },
        ),
        original=OriginalEnvelope(
            wheel_outer_diameter_mm=wheel_outer_diameter_mm,
            wheel_width_mm=wheel_width_mm,
            wheel_envelope_method="audited_mesh_bounding_box",
            wheel_meshes=(LEFT_WHEEL_MESH.as_posix(), RIGHT_WHEEL_MESH.as_posix()),
            wheel_mesh_bounding_boxes=(left_wheel, right_wheel),
            original_part_bounding_boxes=_original_part_boxes(manifest, records),
        ),
        reference_convention=ReferenceConvention(
            robot_axes={"X": "forward", "Y": "left", "Z": "up"},
            joint_local_positive_axis="+Z",
            wheel_local_positive_axis="+Z",
        ),
        joint_frames=joint_frames,
        wheel_frames=wheel_frames,
        measured_fit_allowances=(
            MeasuredFitAllowance(
                name="passive_insert_outer_diameter",
                value_mm=None,
                status="requires_first_article_measurement",
                measurement_method="measure the selected metal insert or bearing",
                reason="purchase part has not been selected",
            ),
            MeasuredFitAllowance(
                name="passive_insert_length",
                value_mm=None,
                status="requires_first_article_measurement",
                measurement_method=(
                    "measure the selected insert and available HA8 depth"
                ),
                reason=(
                    "purchase part and usable thread depth require physical "
                    "confirmation"
                ),
            ),
            MeasuredFitAllowance(
                name="printer_hole_compensation",
                value_mm=None,
                status="requires_first_article_measurement",
                measurement_method="print and gauge a hole-calibration coupon",
                reason="printer, material, and process are not yet fixed",
            ),
        ),
        reference_measurements=(
            ReferenceMeasurement(
                name="original_absolute_joint_and_wheel_assembly_placement",
                value_mm=None,
                status="unresolved",
                measurement_method=(
                    "capture the original assembly coordinate system or measure "
                    "centers from an assembled reference robot"
                ),
                reason=(
                    "absolute centers cannot be recovered uniquely from isolated STL "
                    "names and per-part bounding boxes"
                ),
            ),
        ),
        input_manifest_relative_path=INPUT_MANIFEST.as_posix(),
        input_manifest_sha256=_sha256(REPO_ROOT / INPUT_MANIFEST),
    )
