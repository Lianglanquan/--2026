from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

import cadquery as cq
from OCP.gp import gp_Trsf

from .parameters import DesignParameters, JointFrame, WheelFrame


@dataclass(frozen=True)
class ReferenceAxis:
    frame: str
    origin_mm: tuple[float, float, float]
    direction: tuple[float, float, float]


def _location(
    translation_mm: tuple[float, float, float],
    rotation_extrinsic_xyz_deg: tuple[float, float, float],
) -> cq.Location:
    return cq.Location(translation_mm, rotation_extrinsic_xyz_deg)


def mirror_y(location: cq.Location) -> cq.Location:
    """Mirror a right-handed location across the robot XZ plane."""

    source = location.wrapped.Transformation()
    reflection = (1.0, -1.0, 1.0)
    values: list[float] = []
    for row in range(1, 4):
        for column in range(1, 4):
            values.append(
                reflection[row - 1]
                * source.Value(row, column)
                * reflection[column - 1]
            )
        values.append(reflection[row - 1] * source.Value(row, 4))
    mirrored = gp_Trsf()
    mirrored.SetValues(*values)
    return cq.Location(mirrored)


def _joint_map(params: DesignParameters) -> dict[int, JointFrame]:
    mapping = {frame.joint_id: frame for frame in params.joint_frames}
    if set(mapping) != {1, 2, 3, 4}:
        raise ValueError("joint frame map must contain joint_id values 1 through 4")
    return mapping


def _wheel_map(params: DesignParameters) -> dict[str, WheelFrame]:
    mapping = {frame.side: frame for frame in params.wheel_frames}
    if set(mapping) != {"left", "right"}:
        raise ValueError("wheel frame map must contain left and right")
    return mapping


def build_reference_frames(params: DesignParameters) -> dict[str, cq.Location]:
    """Build local center-preserving locations without inventing assembly centers."""

    frames: dict[str, cq.Location] = {}
    for joint_id, frame in sorted(_joint_map(params).items()):
        frames[f"joint_{joint_id}"] = _location(
            frame.translation_mm, frame.rotation_extrinsic_xyz_deg
        )

    wheels = _wheel_map(params)
    left = wheels["left"]
    frames["wheel_left"] = _location(
        left.translation_mm, left.rotation_extrinsic_xyz_deg
    )
    right = wheels["right"]
    frames["wheel_right"] = _location(
        right.translation_mm, right.rotation_extrinsic_xyz_deg
    )
    if frames["wheel_right"].toTuple() != mirror_y(frames["wheel_left"]).toTuple():
        raise ValueError("wheel frame records must be reciprocal XZ-plane mirrors")
    return frames


def expected_joint_axis(joint_id: int) -> ReferenceAxis:
    if type(joint_id) is not int or joint_id not in {1, 2, 3, 4}:
        raise ValueError("joint_id must be one of 1, 2, 3, or 4")
    return ReferenceAxis(
        frame=f"joint_{joint_id}",
        origin_mm=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
    )


def expected_wheel_axis(side: str) -> ReferenceAxis:
    if side not in {"left", "right"}:
        raise ValueError("side must be 'left' or 'right'")
    return ReferenceAxis(
        frame=f"wheel_{side}",
        origin_mm=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
    )


def _normalized_location(location: cq.Location) -> dict[str, list[float]]:
    translation, rotation = location.toTuple()

    def clean(values: tuple[float, float, float]) -> list[float]:
        return [0.0 if abs(value) < 1e-12 else float(value) for value in values]

    return {
        "translation_mm": clean(translation),
        "rotation_extrinsic_xyz_deg": clean(rotation),
    }


def _frame_report(
    frame: JointFrame | WheelFrame,
    location: cq.Location,
    axis: ReferenceAxis,
) -> dict[str, Any]:
    report = {
        key: value
        for key, value in asdict(frame).items()
        if key not in {"translation_mm", "rotation_extrinsic_xyz_deg"}
    }
    report["transform"] = _normalized_location(location)
    report["expected_axis"] = asdict(axis)
    return report


def build_geometry_report(params: DesignParameters) -> dict[str, Any]:
    frames = build_reference_frames(params)
    unresolved = params.reference_measurement(
        "original_absolute_joint_and_wheel_assembly_placement"
    )
    report = {
        "schema_version": 1,
        "coordinate_convention": {
            "robot_axes": dict(params.reference_convention.robot_axes),
            "joint_local_positive_axis": (
                params.reference_convention.joint_local_positive_axis
            ),
            "wheel_local_positive_axis": (
                params.reference_convention.wheel_local_positive_axis
            ),
            "mirror_rule": "all left/right frame mirroring uses mirror_y(location)",
        },
        "input_manifest": {
            "relative_path": params.input_manifest_relative_path,
            "sha256": params.input_manifest_sha256,
        },
        "original_part_bounding_boxes_mm": [
            asdict(box) for box in params.original.original_part_bounding_boxes
        ],
        "original_center_baseline": {
            "mode": "source_part_local_origin_with_wheel_center_datum",
            "mesh_origin_datum": "preserved_for_joint_frames",
            "wheel_center_datum": "derived_from_source_y_bounds_and_transformed_to_canonical_origin",
            "absolute_assembly_placement": asdict(unresolved),
        },
        "original_wheel_envelope": {
            "outer_diameter_mm": params.original.wheel_outer_diameter_mm,
            "width_mm": params.original.wheel_width_mm,
            "method": params.original.wheel_envelope_method,
            "mesh_bounding_boxes_mm": [
                asdict(box) for box in params.original.wheel_mesh_bounding_boxes
            ],
            "nominal_tolerance_assertions_mm": {
                "outer_diameter": {"nominal": 66.0, "absolute_tolerance": 0.2},
                "width": {"nominal": 29.9, "absolute_tolerance": 0.2},
            },
        },
        "joint_transforms": [
            _frame_report(
                frame,
                frames[frame.frame_name],
                expected_joint_axis(frame.joint_id),
            )
            for frame in params.joint_frames
        ],
        "wheel_transforms": [
            _frame_report(
                frame,
                frames[frame.frame_name],
                expected_wheel_axis(frame.side),
            )
            for frame in params.wheel_frames
        ],
        "measured_fit_allowances": [
            asdict(item) for item in params.measured_fit_allowances
        ],
    }
    return json.loads(json.dumps(report, ensure_ascii=False, sort_keys=True))


def write_geometry_report(params: DesignParameters, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            build_geometry_report(params),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(payload, encoding="utf-8")
    temporary_path.replace(path)
