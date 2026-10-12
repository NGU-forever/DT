# 智能变电站 3D 数字孪生系统 (Smart Substation Digital Twin) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 Vue 3 + Three.js + ECharts 的工业级 220kV 智能变电站 3D 数字孪生大屏展示系统 Demo，支持高保真三维设备建模、电流粒子动态流光、设备部件爆炸拆解、红外热成像模式、遥控倒闸仿真及故障应急联动。

**Architecture:** 前端单页系统，Three.js 在底层全屏 Canvas 中渲染变电站三维物理世界及粒子/辉光后处理特效；Vue 3 通过响应式 Store (substationStore) 驱动工业 HUD 数据大屏（ECharts 实时图表、告警事件流、控制台）；通过射线拾取 (Raycaster) 与镜头平滑运镜 (TWEEN.js) 实现 3D 场景与 2D UI 双向联动。

**Tech Stack:** Vue 3, Vite, Three.js (r160+), @tweenjs/tween.js, ECharts 5, Tailwind CSS, Lucide-Vue-Next.

**Spec:** `docs/superpowers/specs/2026-10-12-substation-digital-twin-design.md`

## Global Constraints
- 前端运行环境：Node.js v22+, 纯现代前端 ESM 架构，无后端强依赖（自带高拟真遥测推流与仿真器）
- 界面风格：工业暗黑科技风 (Cyber-Industrial Dark Slate / Deep Blue / Electric Cyan / Amber Warning)，支持高刷新率 WebGL 渲染
- 所有 3D 模型采用 Three.js 程序化几何体与 PBR 材质高精度构建，无需依赖外部大体积 glTF 文件，保证零延迟秒开与离线高可用

---

### Task 1: 项目脚手架与依赖搭建 (Project Scaffolding)

**Files:**
- Create: `package.json`
- Create: `vite.config.js`
- Create: `tailwind.config.js`
- Create: `postcss.config.js`
- Create: `index.html`
- Create: `src/main.js`
- Create: `src/style.css`
- Create: `src/App.vue`

**Interfaces:**
- Produces: 运行良好的 Vue 3 + Tailwind CSS + Three.js 现代化脚手架

- [ ] **Step 1: 创建 package.json 并安装核心依赖**
  依赖项包含：`vue`, `three`, `@tweenjs/tween.js`, `echarts`, `lucide-vue-next`, 以及开发依赖 `vite`, `@vitejs/plugin-vue`, `tailwindcss`, `postcss`, `autoprefixer`。
- [ ] **Step 2: 配置 Vite、Tailwind CSS 与 PostCSS**
- [ ] **Step 3: 创建主入口文件与全局暗黑工业样式**
- [ ] **Step 4: 运行 `npm install` 与 `npm run build` 验证构建通路**

---

### Task 2: 状态管理与实时仿真推流器 (Store & Telemetry Simulator)

**Files:**
- Create: `src/store/substationStore.js`

**Interfaces:**
- Produces: `useSubstationStore()`，提供全站遥测数据（负荷、电压、油温、频率）、开关刀闸状态、告警队列、视角状态、热力图模式开关、电流粒子开关、设备拆解状态，并提供遥控倒闸与故障注入方法。

- [ ] **Step 1: 编写 `substationStore.js` 响应式数据结构与初始状态**
- [ ] **Step 2: 实现实时遥测定时波动仿真逻辑 (Tick 周期推流)**
- [ ] **Step 3: 实现断路器遥控分合闸逻辑与防误操作保护**
- [ ] **Step 4: 实现典型故障注入 (主变高温、SF6泄漏、短路跳闸) 与告警清除逻辑**

---

### Task 3: Three.js 3D 渲染核心引擎与站区环境构建 (Scene & Environment)

**Files:**
- Create: `src/three/SubstationScene.js`
- Create: `src/three/models/Environment.js`

**Interfaces:**
- Consumes: Three.js, @tweenjs/tween.js
- Produces: `SubstationScene` 类，封装 WebGLRenderer、PerspectiveCamera、Scene、DirectionalLight / AmbientLight、OrbitControls、TWEEN 动画循环、Resize 监听与销毁机制。

- [ ] **Step 1: 实现站区三维环境与基础设施模型 `Environment.js`**
  包含地坪网格、巡检环形沥青车道、安全警戒防撞围栏、主控制室大楼及外立面、电缆沟盖板。
- [ ] **Step 2: 实现核心场景控制器 `SubstationScene.js` 初始化生命周期与动画帧渲染**
- [ ] **Step 3: 添加 UnrealBloomPass 辉光合成通道与工业科技感色调调优**

---

### Task 4: 核心电气一次设备程序化三维建模 (Electrical Equipment Models)

**Files:**
- Create: `src/three/models/Transformer.js`
- Create: `src/three/models/GISBay.js`
- Create: `src/three/models/Gantries.js`

**Interfaces:**
- Consumes: Three.js
- Produces:
  - `createTransformer(id, position)`: 220kV 主变压器主体、高低压绝缘套管、油枕、波纹散热器组、冷却风机、内部线圈铁芯（支持爆炸拆解动画）。
  - `createGISBay(id, position)`: 220kV GIS 组合电器组（断路器罐体、隔离开关机构箱、母线筒）。
  - `createGantrySystem(position)`: 进出线门型高压架构、母线横梁、悬式瓷绝缘子串。

- [ ] **Step 1: 构建主变压器精细模型及爆炸拆解部件分层 `Transformer.js`**
- [ ] **Step 2: 构建 220kV GIS 组合电器气室及操作机构模型 `GISBay.js`**
- [ ] **Step 3: 构建高压门型架构与悬挂式母线系统 `Gantries.js`**
- [ ] **Step 4: 将设备模型组装至 `SubstationScene` 中并完成材质光照调优**

---

### Task 5: 3D 动态视觉特效：电流粒子、红外热成像与告警光环 (Visual Effects)

**Files:**
- Create: `src/three/effects/FlowParticles.js`
- Create: `src/three/effects/HeatmapMaterial.js`
- Create: `src/three/effects/AlarmRings.js`

**Interfaces:**
- Consumes: Three.js, substationStore
- Produces:
  - `FlowParticles`: 沿母线及变压器套管三维曲线流动发光的粒子流，支持动态开启/停流/变流速。
  - `HeatmapShader`: 红外热像模式着色器，根据温度标量动态给主变压器渲染热力场颜色。
  - `AlarmRingEffect`: 发生告警时在故障设备周围产生向上扩散的红色脉冲光环。

- [ ] **Step 1: 实现高压母线电流流动粒子系统 `FlowParticles.js`**
- [ ] **Step 2: 实现设备红外测温热力图渐变着色材质 `HeatmapMaterial.js`**
- [ ] **Step 3: 实现故障预警扩散光环动效 `AlarmRings.js`**
- [ ] **Step 4: 实现主变压器外壳与内部线圈的平滑展开/合并爆炸拆解动画**

---

### Task 6: 工业科技 HUD 大屏组件开发 (UI Dashboard Layer)

**Files:**
- Create: `src/components/Header.vue`
- Create: `src/components/LeftPanel.vue`
- Create: `src/components/RightPanel.vue`
- Create: `src/components/BottomDock.vue`
- Create: `src/components/DeviceModal.vue`
- Create: `src/components/FaultDialog.vue`

**Interfaces:**
- Consumes: `substationStore.js`, `lucide-vue-next`, ECharts
- Produces: 响应式工业科技深色数据大屏 HUD，覆盖变电站实时指标、动态负荷图、设备控制面板与告警处理。

- [ ] **Step 1: 开发顶部导航与站内态势栏 `Header.vue`**
- [ ] **Step 2: 开发左侧遥测监控看板 `LeftPanel.vue` (ECharts 实时负荷波形、功率因数、变压器健康度雷达图)**
- [ ] **Step 3: 开发右侧告警流与倒闸控制台 `RightPanel.vue` (实时告警、断路器分合闸开关、设备巡检日志)**
- [ ] **Step 4: 开发底部快捷控制坞 `BottomDock.vue` (视角切换、热力图、流光、拆解控制)**
- [ ] **Step 5: 开发设备详情测点抽屉 `DeviceModal.vue` 与故障预案模拟器 `FaultDialog.vue`**

---

### Task 7: 场景-UI双向交互集成与整体联调测试 (Integration & Verification)

**Files:**
- Modify: `src/App.vue`
- Test: 浏览器预览与构建打包测试

**Interfaces:**
- 射线检测点击设备弹出 `DeviceModal` 并自动聚焦镜头
- 倒闸分合闸操作即时影响电流粒子通断与指示灯
- 故障注入触发声光报警、热力图过热及相机自动追踪

- [ ] **Step 1: 在 `App.vue` 中集成 Three.js 场景与全部 UI 组件，挂载鼠标点击射线拾取**
- [ ] **Step 2: 联调倒闸分合闸操作 -> 3D 电流粒子通断与断路器指示灯变色**
- [ ] **Step 3: 联调故障注入 -> 3D 相机平滑运镜、红色告警脉冲光环、热力图升温与应急方案弹窗**
- [ ] **Step 4: 执行生产构建测试 `npm run build`，启动本地服务并在浏览器中验证全流程流畅度**
