# 轮足机器人机械原始资料说明

下载日期：2026-09-13（Asia/Shanghai）

## 使用原则

- 只收录公开官方或官方开源资源。
- 所有 STL、STEP/STP、DWG、PDF、URDF 和配置文件均保持原始内容。
- 未生成、转换、重建或修改任何 CAD/mesh 文件。
- 原始文件名尽量保持不变；同名文件没有静默覆盖。

## 01_灯哥小型轮足

### 01_原版STL

来源为灯哥 StackForce 项目仓库 `模型/` 目录，共 29 个原始 STL。

- GitHub：https://github.com/cy2016-1/bipedal_wheeled_robot
- GitHub 提交：`7ce6507b57d556bcbdf111b0ba7231edf429316d`
- Gitee 官方镜像：https://gitee.com/StackForce/bipedal_wheeled_robot
- Gitee 提交：`89d9724087215508b0678cf6296a85a57779d15a`
- 格式：STL
- 官方性：项目公开仓库原始文件
- 用途：腿长、关节中心、轮轴位置和整体结构参考

### 02_Seeed官方URDF_STL

- 教程：https://wiki.seeedstudio.com/cn/stackforce_mini_wheeled_legged_robot/
- 原始下载：https://files.seeedstudio.com/wiki/robotics/projects/stackfoce/SF_bipedalWheel.zip
- 格式：STL、URDF、CSV
- 内容：7 个 mesh STL、1 个 URDF、1 个 CSV 配置文件
- 官方性：Seeed Studio 官方下载包原始文件
- 原始 ZIP 保存在 `03_来源说明/`，解压文件未修改。

## 02_华馨京_HA8-U25H-M

### 型号依据

官方 HA8-U25H-M 数据手册明确记录：12 V 版本、输入电压 9.0-12.6 V、40×20×40 mm、单轴、Ø6 mm/25T 输出齿。该 PDF 是本目录中唯一明确以 `HA8-U25H-M` 单型号命名的机械/规格文档。

- 产品页：https://fashionstar.com.hk/store/product/uart-servo-ha8-u25h-m/
- Wiki：https://fashionstar.com.hk/wiki/uart-servo/ha8-u25h-m/
- 数据手册：https://fashionstar.com.hk/wiki/servo/uart/datasheet/pdf/Fashion-Star-HA8-U25H-M.pdf

### 华馨京官方系列模型

- `ha8-hp8-hx8-series-3D.STEP`：HA8/HP8/HX8 系列本体 STEP，官方原始文件，适用于 HA8 所属尺寸体系。
- `ha8-hp8-hx8-series-dimension.dwg/.pdf`：同系列尺寸图，官方原始文件。
- `main-horn-25T-8holes-3D.STEP` 与对应 DWG：官方 25T 八孔主舵盘。
- `mounting-spacer-3D.STEP` 与对应 DWG：官方安装隔套/附件，不是完整 U 型支架。
- 原始下载页面：https://fashionstar.com.hk/wiki/servo/uart/cad-files/

这些文件确定来自华馨京官方并覆盖 HA8 系列，但其文件名是系列级，不应表述为仅供 HA8-U25H-M 单型号使用。

### 同尺寸系列参考模型

以下文件来自华馨京官方开源仓库，但仓库没有明确写明 HA8-U25H-M 专用：

- `Single-shaft-Servo-3D.stp`
- `单轴舵机外观CAD尺寸图.dwg`
- `单轴舵机外观CAD尺寸图.pdf`
- `25T主舵盘外观尺寸图.dwg`
- `25T主舵盘外观尺寸图.pdf`

仓库：https://github.com/servodevelop/servo-dimension

提交：`f6700e07b9ae7217e739fc8ee52e7f0957d2f976`

### 官方公开资源中未找到

- 明确以 `HA8-U25H-M` 单型号命名的独立 STEP/STP。
- 明确以 `HA8-U25H-M` 单型号命名的独立 DWG。
- 明确适配 HA8-U25H-M 单轴结构的完整舵机支架模型或图纸。
- 官方系列包提供安装隔套，但没有提供可确认的完整单轴 U 型支架。

## 灯哥原始结构与后续适配

灯哥原始 STL 本次仅作为结构参考，没有修改。机器人计划将腿关节由 DS041MG 改为 HA8-U25H-M，将轮电机由 2208 改为 QD4310。

### 后续需要重新设计的文件

适配 HA8-U25H-M：

- 舵机接口1.stl
- 舵机接口2.stl
- 舵机接口3.stl
- 舵机接口4.stl

适配 QD4310：

- 电机固定X1.stl
- 电机固定X2.stl
- 轮固定X1.stl
- 轮固定X2.stl
- 轮毂X1.stl
- 轮毂X2.stl

原始下载阶段没有修改任何 CAD；后续经用户确认，已在独立目录新增参数化适配模型，原始文件仍保持不变。

## 03_适配模型

`03_适配模型/` 是本项目新设计的 HA8-U25H-M 与 QD4310 适配模型，不是灯哥、Seeed Studio 或 FashionStar 官方原始文件。

- 设计规格：`../docs/superpowers/specs/2026-09-16-ha8-qd4310-mechanical-adapter-design.md`
- 参数化源文件：`03_适配模型/01_参数化源文件/`
- STEP：`03_适配模型/02_STEP装配与零件/`
- STL：`03_适配模型/03_STL打印件/`
- 校验报告：`03_适配模型/04_装配检查/`
- BOM 与装配说明：`03_适配模型/05_设计说明/`

当前状态为“数字装配版 v1”。QD4310 转子侧 8×M3 孔 BCD、HA8 被动侧嵌件规格和原整机绝对装配坐标仍需实物测量；未完成首件验证前不得表述为已实体装车验证。

## 校验文件

- `05_校验/完整文件树.txt`
- `05_校验/文件清单.tsv`
- `05_校验/SHA256SUMS.txt`
- `05_校验/校验报告.txt`
