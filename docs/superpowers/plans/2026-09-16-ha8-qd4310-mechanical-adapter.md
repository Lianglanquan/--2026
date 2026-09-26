# HA8 与 QD4310 机械适配实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为灯哥小型轮足机器人生成可追溯的 HA8-U25H-M 四关节接口和 QD4310 双轮直驱接口，并交付参数化源文件、STEP、STL、装配校验、BOM 与设计说明。

**Architecture:** 使用 Python 3.12、CadQuery/OpenCascade 建立参数化实体，使用 Trimesh 检查原始 STL 和导出 STL。输入尺寸、坐标变换、HA8 零件、QD4310 零件、装配检查和导出各自独立；所有制造件从同一组参数生成，左右件通过变换镜像，不手工维护两套尺寸。

**Tech Stack:** Python 3.12、CadQuery、OpenCascade、Trimesh、Manifold3D、NumPy、pytest、MeshLabServer、Markdown。

**Spec:** `docs/superpowers/specs/2026-09-16-ha8-qd4310-mechanical-adapter-design.md`

## Global Constraints

- 原始模型目录 `机械资料/01_灯哥小型轮足/01_原版STL/` 只读，任何任务不得覆盖或修改其中的 29 个 STL。
- HA8 官方 STEP/DWG/PDF 和 QD4310 手册只作为输入依据，不转换后冒充官方原件。
- 腿部关节使用 `HA8-U25H-M ×4`，输出侧使用官方金属 25T 主舵盘，背面 M3 提供被动支撑。
- 轮端使用 `QD4310 ×2`，定子固定在腿部，外转子通过 `8 × M3` 驱动车轮。
- 保持原关节中心、轮轴中心、腿长和约 `Ø66 × 30 mm` 车轮外包络；数字中心偏差上限 `0.20 mm`。
- 不打印 HA8 花键，不为 QD4310 添加减速器，不修改电控或运动学。
- 未在官方图纸中唯一确定的尺寸必须作为命名参数和“实物待复测项”，不得静默猜测。
- 每个新增制造件必须同时导出 STEP 和 STL；STL 必须非空、封闭、流形且法向正确。
- 所有 Git 提交只包含当前任务文件，不暂存或回退工作区中既有用户改动。

## File Structure

```text
机械资料/03_适配模型/
├── 01_参数化源文件/
│   ├── requirements.txt
│   ├── wheelbot_adapter/
│   │   ├── __init__.py
│   │   ├── parameters.py
│   │   ├── input_audit.py
│   │   ├── reference_frames.py
│   │   ├── reference_solids.py
│   │   ├── ha8_adapters.py
│   │   ├── qd4310_adapters.py
│   │   ├── assembly_check.py
│   │   ├── export_models.py
│   │   └── validate_exports.py
│   └── build_all.py
├── 02_STEP装配与零件/
├── 03_STL打印件/
├── 04_装配检查/
│   ├── input_manifest.json
│   ├── geometry_report.json
│   ├── collision_report.json
│   ├── export_validation.json
│   └── SHA256SUMS.txt
└── 05_设计说明/
    ├── README_适配模型.md
    ├── BOM.csv
    └── 实物待复测项.md

tests/mechanical_adapter/
├── conftest.py
├── geometry_assertions.py
├── test_input_audit.py
├── test_parameters.py
├── test_ha8_adapters.py
├── test_qd4310_adapters.py
├── test_assembly_check.py
└── test_export_validation.py
```

`parameters.py` 是尺寸的唯一来源；建模模块不得散落魔法数字。`reference_solids.py` 只生成不可制造的碰撞参考体。`export_models.py` 只接收已生成实体，不包含设计逻辑。

---

### Task 1: 建立可复现 CAD 环境并审计输入文件

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/requirements.txt`
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/__init__.py`
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/input_audit.py`
- Create: `tests/mechanical_adapter/conftest.py`
- Create: `tests/mechanical_adapter/geometry_assertions.py`
- Create: `tests/mechanical_adapter/test_input_audit.py`
- Create: `机械资料/03_适配模型/04_装配检查/input_manifest.json`

**Interfaces:**
- Consumes: 29 个原始 STL、HA8 官方 STEP 文件、QD4310 手册。
- Produces: `audit_inputs(repo_root: Path) -> dict[str, object]`，后续任务使用的不可变输入清单和 SHA256 基线；测试模块共用的几何断言函数。

- [ ] **Step 1: 创建隔离环境并记录依赖**

Run:

```bash
python3 -m venv .venv-mechanical
.venv-mechanical/bin/python -m pip install --upgrade pip
.venv-mechanical/bin/pip install cadquery trimesh manifold3d numpy pytest
.venv-mechanical/bin/pip freeze > /tmp/mechanical-requirements.txt
```

将 `/tmp/mechanical-requirements.txt` 中 CadQuery、Trimesh、Manifold3D、NumPy 和 pytest 的实际解析版本写入 `requirements.txt`。不得使用未锁定的 `>=` 范围。

- [ ] **Step 2: 建立测试夹具和几何断言接口**

`conftest.py` 负责把 `01_参数化源文件` 加入测试导入路径，并提供 `repo_root`、`params` 和 `adapter_assembly` 夹具。`geometry_assertions.py` 集中实现以下测试接口，后续任务不得重复定义：

```python
assembly_bounding_box(assembly) -> BoundingBox
assembly_solid_count(assembly) -> int
solid_count(shape) -> int
axis_offset_mm(shape_or_assembly, expected_axis) -> float
minimum_wall_mm(shape) -> float
mirrored_shape_equivalent(left, right, tolerance_mm=0.05) -> bool
clearance_mm(a, b) -> float
circular_pattern_bcd(shape, hole_count) -> float
circular_pattern_hole_count(shape) -> int
through_hole_diameter(shape, fastener_name) -> float
radial_diameter_mm(box) -> float
axial_width_mm(box) -> float
```

孔位、工具路径、线束出口和径向定位使用命名面/轴标签检查：

```python
all_mounting_holes_clear(shape, diameter_mm) -> bool
fastener_tool_path_is_open(shape) -> bool
cable_exit_is_open(shape) -> bool
has_clearance_for_m3_fastener(shape) -> bool
all_holes_accept_m3_fastener(shape) -> bool
radial_register_is_present(shape) -> bool
```

如果 CadQuery 实体无法保留标签，则 builder 同时返回 `PartModel(shape, features)`，其中 `features` 保存命名轴、孔和工具包络；不得依赖文件名猜测特征。

- [ ] **Step 3: 写输入审计失败测试**

```python
def test_input_audit_finds_all_original_stls(repo_root):
    report = audit_inputs(repo_root)
    assert report["original_stl_count"] == 29
    assert report["empty_files"] == []
    assert "舵机接口1.stl" in report["original_stls"]
    assert "轮毂X2.stl" in report["original_stls"]


def test_input_audit_finds_authoritative_cad(repo_root):
    report = audit_inputs(repo_root)
    assert report["ha8_body_step"].endswith("ha8-hp8-hx8-series-3D.STEP")
    assert report["ha8_horn_step"].endswith("main-horn-25T-8holes-3D.STEP")
    assert report["qd4310_manual"].endswith("QD4310使用手册.pdf")
```

- [ ] **Step 4: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_input_audit.py -v`

Expected: FAIL，提示 `wheelbot_adapter.input_audit` 或 `audit_inputs` 尚不存在。

- [ ] **Step 5: 实现输入审计**

`audit_inputs()` 必须：

- 只递归读取输入目录；
- 对每个文件记录相对路径、字节数、扩展名和 SHA256；
- 对 29 个原始 STL 使用 Trimesh 读取面数、包围盒和 watertight 状态；
- 对 HA8 STEP 使用 CadQuery 导入并记录实体数量和包围盒；
- 拒绝空文件、重复相对路径和无法解析的必需输入；
- 将稳定排序后的 JSON 写入 `04_装配检查/input_manifest.json`。

- [ ] **Step 6: 运行审计测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_input_audit.py -v`

Expected: PASS，报告原始 STL 数量为 29，必需官方输入均存在。

- [ ] **Step 7: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件' \
        '机械资料/03_适配模型/04_装配检查/input_manifest.json' \
        tests/mechanical_adapter/conftest.py \
        tests/mechanical_adapter/geometry_assertions.py \
        tests/mechanical_adapter/test_input_audit.py
git commit -m "build: add mechanical CAD toolchain and input audit"
```

---

### Task 2: 建立尺寸参数和统一参考坐标系

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/parameters.py`
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/reference_frames.py`
- Create: `tests/mechanical_adapter/test_parameters.py`
- Create: `机械资料/03_适配模型/04_装配检查/geometry_report.json`

**Interfaces:**
- Consumes: Task 1 的输入清单与原始 STL 包围盒。
- Produces: `DesignParameters`、`JointFrame`、`WheelFrame`、`load_parameters() -> DesignParameters`、`build_reference_frames(params) -> dict[str, cq.Location]`、`expected_joint_axis(joint_id)`、`expected_wheel_axis(side)`。

- [ ] **Step 1: 写参数与参考系失败测试**

```python
def test_authoritative_dimensions_are_recorded():
    p = load_parameters()
    assert p.ha8.body_xyz_mm == (40.0, 20.0, 40.0)
    assert p.ha8.output_spline_teeth == 25
    assert p.ha8.passive_thread == "M3"
    assert p.qd4310.outer_diameter_mm == 49.0
    assert p.qd4310.total_width_mm == 26.7
    assert p.qd4310.stator_bcd_mm == 38.5
    assert p.qd4310.stator_hole_count == 4
    assert p.qd4310.rotor_hole_count == 8


def test_print_rules_match_spec():
    p = load_parameters()
    assert p.print_rules.moving_clearance_per_side_mm == 0.20
    assert 0.10 <= p.print_rules.locating_clearance_per_side_mm <= 0.15
    assert p.print_rules.minimum_load_wall_mm == 3.0


def test_wheel_reference_envelope_matches_original():
    p = load_parameters()
    assert abs(p.original.wheel_outer_diameter_mm - 66.0) <= 0.2
    assert abs(p.original.wheel_width_mm - 29.9) <= 0.2
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_parameters.py -v`

Expected: FAIL，提示参数类型或加载函数尚不存在。

- [ ] **Step 3: 实现强类型参数**

使用冻结的 `dataclass` 定义：

```python
@dataclass(frozen=True)
class Ha8Dimensions:
    body_xyz_mm: tuple[float, float, float]
    ear_total_height_mm: float
    mounting_hole_diameter_mm: float
    output_spline_teeth: int
    passive_thread: str


@dataclass(frozen=True)
class QD4310Dimensions:
    outer_diameter_mm: float
    total_width_mm: float
    stator_bcd_mm: float
    stator_hole_count: int
    stator_thread: str
    rotor_hole_count: int
    rotor_thread: str
```

同时定义 `PrintRules`、`OriginalEnvelope` 和汇总类型 `DesignParameters`。每个字段旁记录来源文件和图纸页码；待实测字段使用名称明确的 `MeasuredFitAllowance`，不得填入伪造的官方尺寸。

- [ ] **Step 4: 实现关节与轮端参考系**

统一约定：

- `X` 为机器人前方；
- `Y` 为机器人左方；
- `Z` 为机器人上方；
- 每个关节局部 `+Z` 为旋转轴正方向；
- 左右镜像只通过 `mirror_y(location)` 完成；
- 四个关节编号映射和两个车轮编号映射集中在 `reference_frames.py`。

生成 `geometry_report.json`，记录原零件包围盒、原中心基准、四个关节变换和两个轮轴变换。

- [ ] **Step 5: 运行参数测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_parameters.py -v`

Expected: PASS，官方尺寸、打印规则、轮外包络和参考系均可重复加载。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/parameters.py' \
        '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/reference_frames.py' \
        '机械资料/03_适配模型/04_装配检查/geometry_report.json' \
        tests/mechanical_adapter/test_parameters.py
git commit -m "feat: define mechanical dimensions and reference frames"
```

---

### Task 3: 生成 HA8、舵盘和 QD4310 的装配参考体

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/reference_solids.py`
- Modify: `tests/mechanical_adapter/test_parameters.py`

**Interfaces:**
- Consumes: `DesignParameters` 和官方 HA8 STEP。
- Produces: `make_ha8_reference()`、`import_ha8_horn_reference()`、`make_qd4310_reference()`；返回带稳定标签的 `cq.Assembly`，仅用于装配和碰撞，不导出为制造件。

- [ ] **Step 1: 写参考体失败测试**

```python
def test_qd4310_reference_has_expected_envelope(params):
    motor = make_qd4310_reference(params.qd4310)
    box = assembly_bounding_box(motor)
    assert box.xlen == pytest.approx(49.0, abs=0.05)
    assert box.ylen == pytest.approx(49.0, abs=0.05)
    assert box.zlen == pytest.approx(26.7, abs=0.05)


def test_ha8_reference_imports_official_body_and_horn(params):
    servo = make_ha8_reference(params.ha8)
    horn = import_ha8_horn_reference(params.paths.ha8_horn_step)
    assert assembly_solid_count(servo) >= 1
    assert solid_count(horn) >= 1
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_parameters.py -v`

Expected: FAIL，提示参考体函数尚不存在。

- [ ] **Step 3: 实现参考体**

HA8 本体优先导入官方 STEP；代码生成的包络体只用于扫掠和间隙检查。QD4310 因缺少官方 STEP，依据手册明确尺寸生成分离的定子包络、转子扫掠体、后侧孔系轴线和前侧孔系轴线。所有参考体使用醒目标签 `REF_*`，禁止进入制造件导出清单。

- [ ] **Step 4: 运行参考体测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_parameters.py -v`

Expected: PASS，参考体包络和实体数量正确。

- [ ] **Step 5: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/reference_solids.py' \
        tests/mechanical_adapter/test_parameters.py
git commit -m "feat: add actuator reference solids"
```

---

### Task 4: 建模 HA8 输出侧适配盘与被动支撑

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/ha8_adapters.py`
- Create: `tests/mechanical_adapter/test_ha8_adapters.py`

**Interfaces:**
- Consumes: `DesignParameters`、四个 `JointFrame`、官方 25T 舵盘孔系。
- Produces: `make_ha8_output_adapter(joint_id: int, params) -> cq.Workplane`、`make_ha8_passive_support(joint_id: int, params) -> cq.Workplane`、`make_ha8_spacer(joint_id: int, params) -> cq.Workplane`。

- [ ] **Step 1: 写 HA8 连接件失败测试**

```python
@pytest.mark.parametrize("joint_id", [1, 2, 3, 4])
def test_output_adapter_preserves_joint_axis(joint_id, params):
    part = make_ha8_output_adapter(joint_id, params)
    assert axis_offset_mm(part, expected_joint_axis(joint_id)) <= 0.20
    assert minimum_wall_mm(part) >= 3.0


@pytest.mark.parametrize("joint_id", [1, 2, 3, 4])
def test_passive_support_is_coaxial(joint_id, params):
    support = make_ha8_passive_support(joint_id, params)
    assert axis_offset_mm(support, expected_joint_axis(joint_id)) <= 0.20
    assert has_clearance_for_m3_fastener(support)


def test_mirrored_pairs_share_dimensions(params):
    assert mirrored_shape_equivalent(
        make_ha8_output_adapter(1, params),
        make_ha8_output_adapter(2, params),
    )
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_ha8_adapters.py -v`

Expected: FAIL，提示 HA8 建模函数尚不存在。

- [ ] **Step 3: 建模输出侧适配盘**

从官方舵盘 STEP/DWG 提取中心孔和周向安装孔，不建立打印花键。适配盘包含：金属舵盘贴合面、周向紧固孔、原腿部接口、中心螺钉工具通道、最小 3 mm 承力壁和避免应力尖角的圆角。四个编号件从同一 builder 加镜像/方向参数生成。

- [ ] **Step 4: 建模被动支撑与隔套**

围绕 HA8 背面 M3 轴线建立可拆换隔套接口。打印件只定位金属隔套、法兰轴承或耐磨衬套，不让普通打印孔直接承担旋转摩擦。未知采购件配合尺寸集中为 `passive_insert_outer_diameter_mm` 和 `passive_insert_length_mm`，同时写入待复测清单。

- [ ] **Step 5: 运行 HA8 连接件测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_ha8_adapters.py -v`

Expected: PASS，四个编号件轴线误差、壁厚、M3 工具空间和镜像一致性合格。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/ha8_adapters.py' \
        tests/mechanical_adapter/test_ha8_adapters.py
git commit -m "feat: model HA8 output and passive adapters"
```

---

### Task 5: 建模 HA8 外固定与盖板适配件

**Files:**
- Modify: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/ha8_adapters.py`
- Modify: `tests/mechanical_adapter/test_ha8_adapters.py`

**Interfaces:**
- Consumes: Task 4 的输出/被动连接件、HA8 本体包络和原 `外固定1~4`、`盖板1~4` 参考包络。
- Produces: `make_ha8_outer_mount(joint_id: int, params) -> cq.Workplane`、`make_ha8_cover(joint_id: int, params) -> cq.Workplane`。

- [ ] **Step 1: 写外固定与盖板失败测试**

```python
@pytest.mark.parametrize("joint_id", [1, 2, 3, 4])
def test_outer_mount_has_servo_ear_and_tool_clearance(joint_id, params):
    mount = make_ha8_outer_mount(joint_id, params)
    assert all_mounting_holes_clear(mount, diameter_mm=4.3)
    assert fastener_tool_path_is_open(mount)
    assert minimum_wall_mm(mount) >= 3.0


@pytest.mark.parametrize("joint_id", [1, 2, 3, 4])
def test_cover_clears_ha8_and_cable_bend(joint_id, params):
    cover = make_ha8_cover(joint_id, params)
    assert clearance_mm(cover, ha8_body_sweep(joint_id)) >= 0.20
    assert cable_exit_is_open(cover)
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_ha8_adapters.py -v`

Expected: FAIL，提示外固定和盖板 builder 尚不存在。

- [ ] **Step 3: 建模外固定件**

保留原结构与大腿/小臂的连接面和关节中心，只重建 HA8 安装耳、被动支撑座、螺钉沉台及必要加强筋。为四个 Ø4.3 安装孔提供明确的螺钉装入方向，不使用封闭螺母腔。

- [ ] **Step 4: 建模盖板件**

盖板仅围绕 HA8 新包络和线束出口局部改变，保持原外边界与固定点。线束出口倒圆，避免锐边；插头可在不拆腿部主体的情况下拔出。

- [ ] **Step 5: 运行 HA8 全套测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_ha8_adapters.py -v`

Expected: PASS，四组外固定和盖板满足孔位、壁厚、工具路径及线束空间要求。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/ha8_adapters.py' \
        tests/mechanical_adapter/test_ha8_adapters.py
git commit -m "feat: model HA8 mounts and covers"
```

---

### Task 6: 建模 QD4310 定子支架

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/qd4310_adapters.py`
- Create: `tests/mechanical_adapter/test_qd4310_adapters.py`

**Interfaces:**
- Consumes: `DesignParameters`、左右 `WheelFrame`、QD4310 定子孔系和原轮轴中心。
- Produces: `make_qd4310_stator_mount(side: Literal["left", "right"], params) -> cq.Workplane`。

- [ ] **Step 1: 写定子支架失败测试**

```python
@pytest.mark.parametrize("side", ["left", "right"])
def test_stator_mount_preserves_wheel_axis(side, params):
    mount = make_qd4310_stator_mount(side, params)
    assert axis_offset_mm(mount, expected_wheel_axis(side)) <= 0.20
    assert circular_pattern_bcd(mount, hole_count=4) == pytest.approx(38.5, abs=0.05)
    assert through_hole_diameter(mount, "M2.5") >= 2.7


def test_stator_mounts_are_mirrored(params):
    assert mirrored_shape_equivalent(
        make_qd4310_stator_mount("left", params),
        make_qd4310_stator_mount("right", params),
    )
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_qd4310_adapters.py -v`

Expected: FAIL，提示 QD4310 支架 builder 尚不存在。

- [ ] **Step 3: 建模左右定子支架**

支架包含 `Ø38.5 mm` 的 `4 × M2.5` 通孔系、定子端面定位台阶、原腿部连接界面、线束出口和加强筋。线束出口必须完全位于外转子扫掠体之外；M2.5 螺钉工具轴线不得被轮毂遮挡。

- [ ] **Step 4: 运行定子支架测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_qd4310_adapters.py -v`

Expected: PASS，左右镜像、轮轴中心、孔系和工具空间均合格。

- [ ] **Step 5: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/qd4310_adapters.py' \
        tests/mechanical_adapter/test_qd4310_adapters.py
git commit -m "feat: model QD4310 stator mounts"
```

---

### Task 7: 建模 QD4310 直驱轮毂和轮固定件

**Files:**
- Modify: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/qd4310_adapters.py`
- Modify: `tests/mechanical_adapter/test_qd4310_adapters.py`

**Interfaces:**
- Consumes: QD4310 转子 `8 × M3` 孔系、原轮胎包络、Task 6 定子支架。
- Produces: `make_qd4310_rotor_hub(side, params) -> cq.Workplane`、`make_qd4310_wheel_retainer(side, params) -> cq.Workplane`、`make_wheel_subassembly(side, params) -> cq.Assembly`。

- [ ] **Step 1: 写轮毂失败测试**

```python
@pytest.mark.parametrize("side", ["left", "right"])
def test_rotor_hub_matches_qd4310_pattern(side, params):
    hub = make_qd4310_rotor_hub(side, params)
    assert circular_pattern_hole_count(hub) == 8
    assert all_holes_accept_m3_fastener(hub)
    assert radial_register_is_present(hub)


@pytest.mark.parametrize("side", ["left", "right"])
def test_wheel_assembly_stays_in_original_envelope(side, params):
    assembly = make_wheel_subassembly(side, params)
    box = assembly_bounding_box(assembly)
    assert radial_diameter_mm(box) <= 66.2
    assert axial_width_mm(box) <= 30.1
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_qd4310_adapters.py -v`

Expected: FAIL，提示轮毂、轮固定或轮端分总成函数尚不存在。

- [ ] **Step 3: 建模转子轮毂**

轮毂通过官方手册标注的 `8 × M3` 孔连接外转子，增加同心定位台阶，避免仅靠螺钉间隙定位。螺钉头和安装工具位于车轮内腔，不突出到轮胎外圆或静止支架扫掠区。

- [ ] **Step 4: 建模轮固定件**

重用原轮胎安装界面和轮胎中心平面。将原 `轮固定X1/X2` 的功能合并或保留为独立件，由数字装配后的可拆卸性决定；无论采用哪种形式，导出清单仍明确给出左右轮毂和左右轮固定功能对应关系。

- [ ] **Step 5: 运行轮端测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_qd4310_adapters.py -v`

Expected: PASS，8 孔连接、径向定位、左右镜像和 `Ø66.2 × 30.1 mm` 最大包络均合格。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/qd4310_adapters.py' \
        tests/mechanical_adapter/test_qd4310_adapters.py
git commit -m "feat: model QD4310 direct-drive wheel hubs"
```

---

### Task 8: 建立数字装配、碰撞和拆装路径检查

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/assembly_check.py`
- Create: `tests/mechanical_adapter/test_assembly_check.py`
- Create: `机械资料/03_适配模型/04_装配检查/collision_report.json`

**Interfaces:**
- Consumes: Tasks 3-7 的参考体和制造实体。
- Produces: `build_robot_adapter_assembly(params) -> cq.Assembly`、`run_collision_checks(assembly) -> CollisionReport`、`check_fastener_paths(assembly) -> list[CheckResult]`、`check_actuator_removal_paths(assembly) -> CheckReport`、`joint_center_error_mm(assembly, joint_id) -> float`、`wheel_axis_error_mm(assembly, side) -> float`。

- [ ] **Step 1: 写装配检查失败测试**

```python
def test_all_joint_centers_are_preserved(adapter_assembly, params):
    for joint_id in (1, 2, 3, 4):
        assert joint_center_error_mm(adapter_assembly, joint_id) <= 0.20


def test_all_wheel_axes_are_preserved(adapter_assembly, params):
    for side in ("left", "right"):
        assert wheel_axis_error_mm(adapter_assembly, side) <= 0.20


def test_no_moving_reference_intersects_fixed_parts(adapter_assembly):
    report = run_collision_checks(adapter_assembly)
    assert report.hard_collisions == []
    assert report.minimum_clearance_mm >= 0.20


def test_every_actuator_has_removal_path(adapter_assembly):
    assert check_actuator_removal_paths(adapter_assembly).failures == []
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_assembly_check.py -v`

Expected: FAIL，提示装配和碰撞检查接口尚不存在。

- [ ] **Step 3: 构建关节与轮端分总成**

装入 HA8 官方本体、官方舵盘、四组关节适配件、QD4310 参考体、左右定子支架和轮毂。原始 STL 以只读参考 mesh 加入检查，但不参与制造实体导出。

- [ ] **Step 4: 实现扫掠与拆装检查**

至少检查：HA8 本体及线束包络的关节扫掠、QD4310 转子/轮毂/轮胎的 360° 扫掠、M2.5/M3 螺钉工具圆柱、插头拔出包络和电机/舵机直线移除路径。将每项状态、最小间隙和冲突零件名称写入 `collision_report.json`。

- [ ] **Step 5: 运行装配检查测试**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_assembly_check.py -v`

Expected: PASS，中心误差不超过 0.20 mm，无硬碰撞，活动区域间隙不低于 0.20 mm，全部执行器可拆卸。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/assembly_check.py' \
        '机械资料/03_适配模型/04_装配检查/collision_report.json' \
        tests/mechanical_adapter/test_assembly_check.py
git commit -m "test: add mechanical assembly and collision checks"
```

---

### Task 9: 导出 STEP/STL 并验证几何完整性

**Files:**
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/export_models.py`
- Create: `机械资料/03_适配模型/01_参数化源文件/wheelbot_adapter/validate_exports.py`
- Create: `机械资料/03_适配模型/01_参数化源文件/build_all.py`
- Create: `tests/mechanical_adapter/test_export_validation.py`
- Create: `机械资料/03_适配模型/04_装配检查/export_validation.json`
- Create: `机械资料/03_适配模型/04_装配检查/SHA256SUMS.txt`
- Create outputs under: `机械资料/03_适配模型/02_STEP装配与零件/`
- Create outputs under: `机械资料/03_适配模型/03_STL打印件/`

**Interfaces:**
- Consumes: 全部通过装配检查的制造实体。
- Produces: `manufacturing_parts(params) -> dict[str, cq.Workplane]`、`export_all(output_root: Path) -> ExportReport`、`validate_all_exports(output_root: Path) -> ValidationReport`。

- [ ] **Step 1: 写导出失败测试**

```python
def test_every_manufacturing_part_exports_step_and_stl(tmp_path, params):
    report = export_all(tmp_path, params)
    for name in report.part_names:
        assert (tmp_path / "02_STEP装配与零件" / f"{name}.step").is_file()
        assert (tmp_path / "03_STL打印件" / f"{name}.stl").is_file()


def test_exported_stls_are_watertight(tmp_path, params):
    export_all(tmp_path, params)
    validation = validate_all_exports(tmp_path)
    assert validation.empty_files == []
    assert validation.non_watertight_stls == []
    assert validation.non_manifold_stls == []
    assert validation.unit_mismatches == []
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `.venv-mechanical/bin/pytest tests/mechanical_adapter/test_export_validation.py -v`

Expected: FAIL，提示导出和校验函数尚不存在。

- [ ] **Step 3: 实现稳定命名和批量导出**

导出清单至少包括：

- `HA8_舵机接口1~4`；
- `HA8_外固定1~4`；
- `HA8_盖板1~4`；
- HA8 被动支撑和隔套的编号件；
- `QD4310_电机固定X1/X2`；
- `QD4310_轮固定X1/X2`；
- `QD4310_轮毂X1/X2`；
- HA8 关节分总成 STEP、QD4310 轮端分总成 STEP 和全适配总装 STEP。

文件名包含 `v1`，不与原始 STL 同名。STL 使用固定弦高和角度公差，导出设置写入报告。

- [ ] **Step 4: 实现出口验证**

对每个 STEP 和 STL 记录文件大小、SHA256、包围盒和实体/面数。用 CadQuery 重新导入 STEP、Trimesh 重新导入 STL；比较同名 STEP/STL 包围盒，任一轴差异超过 `0.05 mm` 判定失败。使用 MeshLabServer 对 STL 进行第二次非空读取检查，但不得让 MeshLab 自动修复或覆盖模型。

- [ ] **Step 5: 运行全量构建和测试**

Run:

```bash
.venv-mechanical/bin/python '机械资料/03_适配模型/01_参数化源文件/build_all.py'
.venv-mechanical/bin/pytest tests/mechanical_adapter -v
```

Expected: 全部测试 PASS；`export_validation.json` 中空文件、非流形、非封闭、单位错误和包围盒不匹配列表均为空。

- [ ] **Step 6: 提交本任务**

```bash
git add '机械资料/03_适配模型/01_参数化源文件' \
        '机械资料/03_适配模型/02_STEP装配与零件' \
        '机械资料/03_适配模型/03_STL打印件' \
        '机械资料/03_适配模型/04_装配检查/export_validation.json' \
        '机械资料/03_适配模型/04_装配检查/SHA256SUMS.txt' \
        tests/mechanical_adapter/test_export_validation.py
git commit -m "feat: export and validate mechanical adapter models"
```

---

### Task 10: 生成 BOM、实测清单和交付说明

**Files:**
- Create: `机械资料/03_适配模型/05_设计说明/README_适配模型.md`
- Create: `机械资料/03_适配模型/05_设计说明/BOM.csv`
- Create: `机械资料/03_适配模型/05_设计说明/实物待复测项.md`
- Modify: `机械资料/README_机械资料说明.md`

**Interfaces:**
- Consumes: 输入审计、几何报告、碰撞报告和导出校验。
- Produces: 可供打印、采购、首件复测和后续版本调整使用的中文交付文档。

- [ ] **Step 1: 编写 BOM**

`BOM.csv` 至少包含：编号、零件名称、数量、制造/采购、材料建议、紧固件规格、关联 STEP、关联 STL、尺寸来源和备注。官方 HA8 舵盘、M2.5/M3 螺钉、垫片、螺母、被动侧金属隔套/轴承均单独列项；未选定采购型号的被动支撑件标为“首件前选型”，不得伪造料号。

- [ ] **Step 2: 编写实物待复测项**

明确列出并说明测量方法：HA8 实物安装耳厚度和孔径公差、官方舵盘实际孔径/孔距、背面 M3 可用螺纹深度、QD4310 前后端面与孔系实测、线束出线位置、原轮胎内孔/卡槽、打印机孔径补偿、拟采购轴承或隔套尺寸。

- [ ] **Step 3: 编写适配模型 README**

记录坐标系、版本、构建命令、输出目录、每个新零件替代的原件、装配顺序、螺钉方向、零位定义、打印方向建议、材料建议、不得直接打印花键的说明、复测后改参数而非改 STL 的流程。

- [ ] **Step 4: 更新总机械资料说明**

在 `机械资料/README_机械资料说明.md` 中新增“03_适配模型”章节，明确这些文件是新设计的适配模型，不是灯哥或 FashionStar 官方原始文件，并链接设计规格、参数化源文件和校验报告。

- [ ] **Step 5: 运行最终验证**

Run:

```bash
.venv-mechanical/bin/python '机械资料/03_适配模型/01_参数化源文件/build_all.py'
.venv-mechanical/bin/pytest tests/mechanical_adapter -v
find '机械资料/03_适配模型' -type f -size 0 -print
sha256sum -c '机械资料/03_适配模型/04_装配检查/SHA256SUMS.txt'
git diff --check
```

Expected: 构建和测试通过；空文件检查无输出；SHA256 全部 `OK`；`git diff --check` 无错误。

- [ ] **Step 6: 确认原始 STL 未变化**

重新运行 Task 1 的 `audit_inputs()`，与首次 `input_manifest.json` 中 29 个原始 STL 的 SHA256 比较。

Expected: 29 个 SHA256 全部一致，无新增、删除或覆盖。

- [ ] **Step 7: 提交最终文档**

```bash
git add '机械资料/03_适配模型/05_设计说明' \
        '机械资料/README_机械资料说明.md'
git commit -m "docs: add mechanical adapter build and assembly guide"
```

---

## Final Acceptance Run

依次执行并保存摘要：

```bash
.venv-mechanical/bin/python '机械资料/03_适配模型/01_参数化源文件/build_all.py'
.venv-mechanical/bin/pytest tests/mechanical_adapter -v
find '机械资料/03_适配模型/02_STEP装配与零件' -type f | sort
find '机械资料/03_适配模型/03_STL打印件' -type f | sort
find '机械资料/03_适配模型' -type f -size 0 -print
sha256sum -c '机械资料/03_适配模型/04_装配检查/SHA256SUMS.txt'
git status --short
```

最终报告必须说明：

- 生成的 STEP、STL 和装配文件数量；
- 四个 HA8 关节中心和两个 QD4310 轮轴中心的最大偏差；
- 最小活动间隙和车轮最终外包络；
- 碰撞、空文件、流形、封闭性和 SHA256 校验结果；
- 原始 29 个 STL 的 SHA256 是否保持不变；
- 仍需用实物确认的尺寸；
- 未通过实物首件验证前，模型状态标记为“数字装配版 v1”，不得表述为已完成实体装车验证。
