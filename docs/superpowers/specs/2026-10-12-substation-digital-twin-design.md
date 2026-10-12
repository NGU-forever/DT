# 智能变电站 3D 数字孪生系统 (Smart Substation Digital Twin) 设计方案

## 1. 系统概述 (Overview)
本项目是一个专为电气工程行业（220kV/110kV 智能变电站）打造的 Web 3D 数字孪生大屏展示系统。
系统结合 Three.js WebGL 三维渲染引擎、Vue 3 组合式 API (Composition API)、ECharts 5 工业数据看板与 Tailwind CSS 样式引擎，构建具备高保真设备模型、动态电流粒子流、设备红外热成像模式、部件爆炸拆解、实时遥测数据模拟、倒闸遥控操作及故障预警联动的现代工业级数字孪生平台。

## 2. 技术栈架构 (Tech Stack)
- **前端框架**：Vue 3 (Composition API, `<script setup>`) + Vite 6
- **三维渲染引擎**：Three.js (r160+), OrbitControls, TWEEN.js (缓动动画), EffectComposer (UnrealBloomPass 工业辉光效果)
- **数据可视化**：ECharts 5 (vue-echarts 或 echarts 原生封装，深色工业大屏定制主题)
- **图标与样式**：Lucide-Vue-Next 图标库, Tailwind CSS 3 / CSS3 自定义科技感玻璃拟态与光晕动效
- **语言**：JavaScript (ESNext)。全工程为纯 JS（不含 TypeScript）

## 3. 核心功能与模块规划

### 3.1 3D 变电站数字孪生场景 (Three.js Scene)
1. **站区基础设施**：
   - 变电站工业防滑网格地面、安全巡检通道、安全警示围栏、电缆沟槽、主控室建筑模型。
2. **核心电气一次设备三维程序化建模**：
   - **#1 & #2 主变压器 (Main Transformers)**：
     - 油箱本体、高压/低压绝缘套管 (Bushings)、储油柜（油枕）、大型散热片组（带散热风扇）、瓦斯继电器、铭牌与接地端子。
     - 结构爆炸拆解动画 (Exploded View)：点击拆解可向外延展查看绕组线圈、铁芯与绝缘结构。
   - **GIS 组合电器设备区 (Gas Insulated Switchgear)**：
     - 断路器气室 (SF6 Circuit Breakers)、三工位隔离开关/接地刀闸、高压封闭母线筒、避雷器与精密管阀结构。
   - **高压门型架构与母线走廊 (Gantries & Busbars)**：
     - 220kV/110kV 进出线门型铁塔架构、耐张悬垂绝缘子串、架空母线导线。
   - **开关柜排阵 (Switchgear Row)**：
     - 10kV/35kV 户内/户外中置式高压开关柜。
3. **动态工业视觉特效**：
   - **能量/电流动态粒子流 (Electric Flow Particle Stream)**：
     - 沿高压进线 -> 母线 -> 主变压器 -> 出线开关柜流动发光的粒子流光，动态表征潮流负荷方向与输电强度。
   - **设备红外热成像 / 热力场仿真 (Thermal Heatmap Simulation)**：
     - 一键切换热像仪模式，主变压器与关键接头表面呈现红外温度场色谱（蓝->绿->黄->红），高亮展示油温温升。
   - **告警脉冲光环 (Alarm Pulse Ring)**：
     - 故障状态下，目标设备脚底或周围扩散红/橙色动态光环与频闪告警。
   - **光影与后期发光 (Unreal Bloom)**：
     - 工业深色科技蓝背景，搭配冷白泛光、警报发光及母线光流辉光效果。

### 3.2 交互与控制台功能
1. **多视角漫游与自动巡检**：
   - 全景俯瞰视角 (Overview)
   - 1# 主变特写视角 (Transformer Focus)
   - GIS 设备区视角 (GIS Bay)
   - 360° 自动巡航漫游 (Auto Patrol)
2. **倒闸操作与遥控仿真 (Remote Switch Control)**：
   - 可以在 UI 控制面板中选择 220kV 进线断路器或主变低压侧断路器，下发“分闸”或“合闸”指令。
   - 场景联动：断路器指示灯由红（合闸）变为绿（分闸），对应导线上的电流粒子流停止流动或恢复流动，右侧系统记录生成操作票日志。
3. **故障模拟与应急预案 (Fault Injection & Emergency Response)**：
   - 支持一键触发典型电力故障：
     - 故障 1：1# 主变绕组温度超限（油温 > 85℃，热力图过热，触发冷却器强排）
     - 故障 2：220kV GIS SF6 气体微水压力降低（压力 < 0.45MPa，气压告警）
     - 故障 3：出线侧短路过载保护跳闸（重合闸动作仿真）
   - 联动 3D 相机飞向故障设备并高亮光环，同时在告警面板弹出处置预案指南。

### 3.3 工业级 HUD 大屏数据看板 (UI Layer)
1. **顶部导航状态栏**：
   - 站名：`国家电网 · 220kV 枫桥智能变电站数字孪生系统`
   - 实时时间显示、环境温湿度、气压、阵风级数
   - 安全运行天数（如 1,428 天）、站内当前综合负荷率（如 76.4%）
2. **左侧运行态势看板**：
   - 全站实时负荷潮流曲线 (ECharts 动态推流折线图)
   - 三相电压与频率稳定性监测 (Ua/Ub/Uc 220.4kV, f=50.02Hz)
   - 主变健康度综合评价 (雷达图：绝缘、温升、油色谱、振动、局放)
3. **右侧设备台账与告警中心**：
   - 实时告警信息流水列表（紧急、重要、预警，点击卡片 3D 镜头直接定位）
   - 倒闸仿真控制面板（断路器遥控、隔离开关操作）
   - 当前选中设备属性卡片（遥测、遥信、出厂型号、维护周期）
4. **底部交互控制 Dock**：
   - 视角快捷切换按键
   - 潮流流向 (粒子) 开关
   - 红外热成像模式开关
   - 设备部件拆解动画开关
   - 故障注入控制台入口
   - 全屏切换按钮

## 4. 系统工程目录设计
```
/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── style.css
│   ├── components/
│   │   ├── Header.vue           # 顶部态势与状态栏
│   │   ├── LeftPanel.vue        # 左侧监测看板 (ECharts)
│   │   ├── RightPanel.vue       # 右侧告警与控制看板
│   │   ├── BottomDock.vue       # 底部场景交互与模式切换栏
│   │   ├── DeviceModal.vue      # 设备详情与测点台账弹窗
│   │   └── FaultDialog.vue      # 故障注入与应急预案弹窗
│   ├── three/
│   │   ├── SubstationScene.js   # Three.js 场景管理核心入口 (相机、渲染器、灯光、Bloom)
│   │   ├── models/
│   │   │   ├── Environment.js   # 地面、道路、护栏、控制楼
│   │   │   ├── Transformer.js   # 变压器精细建模及拆解动画
│   │   │   ├── GISBay.js        # GIS 组合电器建模
│   │   │   └── Gantries.js      # 门型架构、母线与绝缘子
│   │   └── effects/
│   │       ├── FlowParticles.js # 高压电流导线粒子流光特效
│   │       ├── HeatmapMaterial.js# 红外热像渐变着色器材质
│   │       └── AlarmRings.js    # 告警发光脉冲扩散环
│   └── store/
│       └── substationStore.js   # 全局状态管理 (遥测数据推流、设备状态、告警队列)
```
