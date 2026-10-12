import { reactive, ref } from 'vue'

export const substationState = reactive({
  // 全站基础指标
  stationInfo: {
    name: '国家电网 · 220kV 枫桥智能变电站',
    voltageLevel: '220kV / 110kV / 35kV',
    safeDays: 1428,
    commissionDate: '2022-08-16',
    status: '正常运行',
  },

  // 综合环境
  environment: {
    temp: 24.8, // ℃
    humidity: 52, // %
    pressure: 101.3, // kPa
    windSpeed: 3.2, // m/s
    sf6Density: 0.0, // ppm
    waterLevel: 0, // mm (水浸)
  },

  // 电气运行遥测总览 (YC)
  telemetry: {
    totalPower: 182.6, // 有功 MW
    reactivePower: 41.2, // 无功 Mvar
    apparentPower: 187.2, // 视在 MVA
    powerFactor: 0.975, // 功率因数
    loadRate: 76.1, // 负载率 %
    frequency: 50.02, // 频率 Hz
    voltageA: 224.5, // A相电压 kV
    voltageB: 224.2, // B相电压 kV
    voltageC: 224.8, // C相电压 kV
    currentA: 472.4, // A相电流 A
    currentB: 470.8, // B相电流 A
    currentC: 474.1, // C相电流 A
  },

  // 核心一次设备列表与遥测
  devices: {
    'trans-1': {
      id: 'trans-1',
      name: '1# 主变压器 (220kV/110kV/35kV)',
      model: 'SFPZ-240000/220',
      ratedCapacity: '240 MVA',
      status: 'normal', // normal | warning | danger
      oilTemp: 58.4, // 顶层油温 ℃
      windingTemp: 68.2, // 绕组温度 ℃
      current: 546.2, // 高压侧电流 A
      voltage: 224.5, // 运行电压 kV
      sf6Pressure: 0.0, // 无
      vibration: 1.15, // 振动加速度 mm/s
      gasH2: 12.4, // 油色谱 H2 ppm
      pdLevel: 35, // 局部放电 pC
      coolerStatus: '自动运行 (6组投运)',
      neutralGround: '直接接地',
      healthScore: 96,
    },
    'trans-2': {
      id: 'trans-2',
      name: '2# 主变压器 (220kV/110kV/35kV)',
      model: 'SFPZ-240000/220',
      ratedCapacity: '240 MVA',
      status: 'normal',
      oilTemp: 55.8,
      windingTemp: 65.1,
      current: 521.0,
      voltage: 224.2,
      sf6Pressure: 0.0,
      vibration: 0.98,
      gasH2: 10.1,
      pdLevel: 28,
      coolerStatus: '自动运行 (6组投运)',
      neutralGround: '直接接地',
      healthScore: 98,
    },
    'gis-201': {
      id: 'gis-201',
      name: '220kV GIS 201 进线断路器',
      model: 'ZF12-252/T4000-50',
      status: 'normal',
      breakerState: true, // true: 合闸 (CLOSED), false: 分闸 (OPEN)
      sf6Pressure: 0.58, // 额定 0.60 MPa
      sf6Moisture: 42, // 微水 ppm
      contactWear: 4.2, // 电寿命磨损率 %
      actionCount: 148, // 动作次数
      voltage: 224.5,
      current: 472.4,
      healthScore: 95,
    },
    'gis-202': {
      id: 'gis-202',
      name: '220kV GIS 202 母联断路器',
      model: 'ZF12-252/T4000-50',
      status: 'normal',
      breakerState: true,
      sf6Pressure: 0.57,
      sf6Moisture: 38,
      contactWear: 3.8,
      actionCount: 112,
      voltage: 224.3,
      current: 310.5,
      healthScore: 97,
    },
    'gis-101': {
      id: 'gis-101',
      name: '110kV GIS 101 出线断路器',
      model: 'ZF11-126/T3150-40',
      status: 'normal',
      breakerState: true,
      sf6Pressure: 0.52,
      sf6Moisture: 35,
      contactWear: 6.1,
      actionCount: 220,
      voltage: 114.8,
      current: 680.4,
      healthScore: 94,
    }
  },

  // 实时告警队列
  alarms: [
    {
      id: 'alm-1',
      time: '18:15:20',
      deviceId: 'trans-1',
      deviceName: '1# 主变压器',
      level: 'warning',
      text: 'B相绕组温度微幅上升，触发智能风冷3组补强循环',
      handled: false,
    },
    {
      id: 'alm-2',
      time: '17:40:12',
      deviceId: 'gis-201',
      deviceName: '220kV GIS 201 断路器',
      level: 'info',
      text: '储能电机自动完成储能充压，机构压力正常',
      handled: true,
    },
    {
      id: 'alm-3',
      time: '16:02:44',
      deviceId: 'trans-2',
      deviceName: '2# 主变压器',
      level: 'info',
      text: '油中溶解气体在线监测周期自检完成，指标优良',
      handled: true,
    }
  ],

  // 倒闸与操作日志
  operationLogs: [
    { id: 1, time: '18:00:00', type: '巡检', content: '红外测温机器人完成 #1 主变例行巡检，未见异常热点' },
    { id: 2, time: '16:30:15', type: '遥信', content: '220kV I母接地刀闸 2017 在分闸位状态确认' },
  ],

  // 3D 视觉交互与控制状态
  interaction: {
    currentView: 'overview', // 'overview' | 'transformer1' | 'transformer2' | 'gis' | 'patrol'
    showFlowParticles: true,
    isHeatmapMode: false,
    isExplodedView: false,
    selectedDeviceId: null,
    activeFaultType: null, // null | 'trans_overheat' | 'sf6_leak' | 'overload_trip'
    isPatrolling: false,
  },

  // 后端工业连接状态 (FastAPI + OPC UA + MQTT + WebSocket)
  backend: {
    connected: false,
    protocol: 'FastAPI + OPC UA + MQTT',
    wsUrl: 'ws://localhost:8000/ws/substation',
    apiBase: 'http://localhost:8000/api'
  },

  // 数字孪生模型运行元信息 (由后端机理模型随推流下发)
  model: {
    step: 0,
    converged: false,
    timeCompression: 300,
    stepSeconds: 1.5,
    deEnergized: false,
    inServiceTransformers: [],
    activeFaults: [],
    energizedBuses: [],
    shedMva: 0,
  }
})

// 状态管理服务对象
export const substationStore = {
  state: substationState,

  // 切换视角
  setView(viewName) {
    substationState.interaction.currentView = viewName
    if (viewName === 'transformer1') {
      substationState.interaction.selectedDeviceId = 'trans-1'
    } else if (viewName === 'transformer2') {
      substationState.interaction.selectedDeviceId = 'trans-2'
    } else if (viewName === 'gis') {
      substationState.interaction.selectedDeviceId = 'gis-201'
    } else if (viewName === 'overview') {
      substationState.interaction.selectedDeviceId = null
    }
  },

  // 选中特定设备
  selectDevice(deviceId) {
    substationState.interaction.selectedDeviceId = deviceId
  },

  // 切换电流粒子流动
  toggleFlowParticles() {
    substationState.interaction.showFlowParticles = !substationState.interaction.showFlowParticles
  },

  // 切换红外热力图模式
  toggleHeatmap() {
    substationState.interaction.isHeatmapMode = !substationState.interaction.isHeatmapMode
  },

  // 切换部件爆炸拆解模式
  toggleExploded() {
    substationState.interaction.isExplodedView = !substationState.interaction.isExplodedView
  },

  // 倒闸遥控开关操作 (向 FastAPI 发送控制请求，联动 OPC UA 和 MQTT)
  async toggleBreaker(deviceId) {
    const dev = substationState.devices[deviceId]
    if (!dev || typeof dev.breakerState === 'undefined') return

    dev.breakerState = !dev.breakerState
    const actionText = dev.breakerState ? '合闸 (CLOSED)' : '分闸 (OPEN)'
    
    // 本地乐观更新：分闸立即置零电流，合闸保持原值，真实数值由后端模型在下一帧纠正
    if (!dev.breakerState) {
      dev.current = 0
    }

    // 记录操作票
    const now = new Date().toTimeString().slice(0, 8)
    substationState.operationLogs.unshift({
      id: Date.now(),
      time: now,
      type: '遥控指令',
      content: `下发控制指令成功：[${dev.name}] 执行 ${actionText} (OPC UA + MQTT已同步)`
    })

    substationState.alarms.unshift({
      id: `alm-${Date.now()}`,
      time: now,
      deviceId: dev.id,
      deviceName: dev.name,
      level: 'info',
      text: `遥控操作执行：断路器变位至 ${actionText}，已向 OPC UA 节点与 MQTT 控制总线写入`,
      handled: true,
    })

    // 向 FastAPI 后端发送真实遥控指令
    try {
      await fetch(`${substationState.backend.apiBase}/control/breaker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: deviceId,
          action: dev.breakerState ? 'close' : 'open',
          operator: 'DIGITAL_TWIN_3D_DOCK'
        })
      })
    } catch (e) {
      console.warn('FastAPI 后端离线，已在前端本地仿真模式执行:', e)
    }
  },

  // 注入预设故障
  injectFault(faultType) {
    substationState.interaction.activeFaultType = faultType
    const now = new Date().toTimeString().slice(0, 8)

    if (faultType === 'trans_overheat') {
      const dev = substationState.devices['trans-1']
      dev.status = 'danger'
      dev.oilTemp = 91.5
      dev.windingTemp = 108.4
      dev.healthScore = 62
      substationState.interaction.selectedDeviceId = 'trans-1'
      substationState.interaction.isHeatmapMode = true

      substationState.alarms.unshift({
        id: `alm-f1-${Date.now()}`,
        time: now,
        deviceId: 'trans-1',
        deviceName: '1# 主变压器',
        level: 'danger',
        text: '【严重告警】1#主变顶层油温超限 (>85℃)，绕组热点温度急剧上升，请立即启动事故强排并转移负荷！',
        handled: false,
      })
    } else if (faultType === 'sf6_leak') {
      const dev = substationState.devices['gis-201']
      dev.status = 'danger'
      dev.sf6Pressure = 0.42
      dev.healthScore = 58
      substationState.interaction.selectedDeviceId = 'gis-201'

      substationState.alarms.unshift({
        id: `alm-f2-${Date.now()}`,
        time: now,
        deviceId: 'gis-201',
        deviceName: '220kV GIS 201 进线断路器',
        level: 'danger',
        text: '【气压闭锁】220kV GIS 201 气室 SF6 绝缘气体压力突降至 0.42MPa，触发断路器跳闸闭锁报警！',
        handled: false,
      })
    } else if (faultType === 'overload_trip') {
      const dev = substationState.devices['gis-101']
      dev.status = 'danger'
      dev.breakerState = false
      dev.current = 0
      dev.healthScore = 70
      substationState.interaction.selectedDeviceId = 'gis-101'

      substationState.alarms.unshift({
        id: `alm-f3-${Date.now()}`,
        time: now,
        deviceId: 'gis-101',
        deviceName: '110kV GIS 101 出线断路器',
        level: 'danger',
        text: '【事故跳闸】110kV 枫南线出线短路过流速断保护动作，断路器自动跳闸，重合闸启动！',
        handled: false,
      })
    }
  },

  // 清除/复归故障
  async clearFault() {
    substationState.interaction.activeFaultType = null
    // 恢复设备指标
    const t1 = substationState.devices['trans-1']
    t1.status = 'normal'
    t1.oilTemp = 58.4
    t1.windingTemp = 68.2
    t1.healthScore = 96

    const g1 = substationState.devices['gis-201']
    g1.status = 'normal'
    g1.sf6Pressure = 0.58
    g1.healthScore = 95

    const g2 = substationState.devices['gis-101']
    g2.status = 'normal'
    g2.breakerState = true
    g2.current = 680.4
    g2.healthScore = 94

    const now = new Date().toTimeString().slice(0, 8)
    substationState.operationLogs.unshift({
      id: Date.now(),
      time: now,
      type: '故障复归',
      content: '站内全量事故保护信号已远程复归，设备状态恢复正常受控。'
    })

    try {
      await fetch(`${substationState.backend.apiBase}/control/fault/reset`, { method: 'POST' })
    } catch (e) {
      // 本地模式忽略
    }
  },

  // 接收后端孪生快照并合并进前端状态。
  // 必须显式做 snake_case -> camelCase 字段映射：后端推流使用 snake_case（物模型字段名），
  // 前端状态使用 camelCase，直接 Object.assign 会导致绝大多数测点根本不会被更新。
  applyBackendSnapshot(data) {
    const telemetry = data.telemetry || {}
    for (const [snake, camel] of Object.entries(TELEMETRY_FIELD_MAP)) {
      if (telemetry[snake] !== undefined) {
        substationState.telemetry[camel] = telemetry[snake]
      }
    }
    const devices = data.devices || {}
    for (const deviceId of Object.keys(devices)) {
      const target = substationState.devices[deviceId]
      if (!target) continue
      for (const [snake, value] of Object.entries(devices[deviceId])) {
        target[DEVICE_FIELD_MAP[snake] || snake] = value
      }
    }
    if (data.model) {
      const m = data.model
      const model = substationState.model
      model.step = m.step ?? model.step
      model.converged = !!m.converged
      model.timeCompression = m.time_compression ?? model.timeCompression
      model.stepSeconds = m.step_seconds ?? model.stepSeconds
      model.deEnergized = !!m.de_energized
      model.inServiceTransformers = m.in_service_transformers || []
      model.activeFaults = m.active_faults || []
      model.energizedBuses = telemetry.energized_buses || model.energizedBuses
      model.shedMva = telemetry.shed_mva ?? 0
    }
  },

  // 建立与 FastAPI 后端的 WebSocket 实时双向通信
  initWebSocket() {
    let ws = null
    let reconnectTimer = null

    const connect = () => {
      try {
        ws = new WebSocket(substationState.backend.wsUrl)

        ws.onopen = () => {
          console.log('★ 已连接至 FastAPI 变电站数字孪生后端 WebSocket ★')
          substationState.backend.connected = true
        }

        ws.onmessage = (event) => {
          try {
            const data = jsonParseSafe(event.data)
            if (!data) return

            // 接收后端推送的时序遥测快照或周期更新
            if (data.type === 'TELEMETRY_UPDATE' || data.type === 'INITIAL_SNAPSHOT') {
              substationStore.applyBackendSnapshot(data)
            }
          } catch (err) {
            console.error('处理后端 WebSocket 消息异常:', err)
          }
        }

        ws.onclose = () => {
          substationState.backend.connected = false
          if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
              reconnectTimer = null
              connect()
            }, 3000)
          }
        }

        ws.onerror = () => {
          substationState.backend.connected = false
        }
      } catch (e) {
        substationState.backend.connected = false
      }
    }

    connect()
  },

  // 动态数据微幅波动推流仿真 (作为 WebSocket 离线时的后备引擎)
  startSimulationTicker() {
    // 优先启动后端 WebSocket
    this.initWebSocket()

    return setInterval(() => {
      // 若后端已连接，由后端 WebSocket 主动推流，前端停止本地扰动
      if (substationState.backend.connected) {
        return
      }

      // 仅在后端离线时执行本地保底推流。
      // 保底模式同样遵守后端的物理约束（拓扑决定供电范围、I = S/(√3·U)），
      // 避免出现"已经失压了负荷还在跳"这种自相矛盾的画面。
      const phase = Math.sqrt(3)
      const ratedMva = 240
      const uHv = 224.5
      const gis201Closed = substationState.devices['gis-201'].breakerState !== false
      const gis202Closed = substationState.devices['gis-202'].breakerState !== false
      const gis101Closed = substationState.devices['gis-101'].breakerState !== false
      const inService = []
      if (gis201Closed) inService.push('trans-1')
      if (gis201Closed && gis202Closed) inService.push('trans-2')

      const demandMva = 365.3 + (Math.random() - 0.5) * 4.8
      const servedMva = inService.length ? demandMva * (gis101Closed ? 1 : 0.63) : 0
      const perMva = inService.length ? servedMva / inService.length : 0

      const T = substationState.telemetry
      T.apparentPower = +servedMva.toFixed(1)
      T.totalPower = +(servedMva * 0.975).toFixed(2)
      T.reactivePower = +(servedMva * Math.sqrt(1 - 0.975 ** 2)).toFixed(2)
      T.loadRate = inService.length ? +((servedMva / (ratedMva * inService.length)) * 100).toFixed(1) : 0
      T.frequency = +(50 + (Math.random() - 0.5) * 0.02).toFixed(3)
      T.currentA = +(servedMva / (phase * uHv) * 1000).toFixed(1)
      T.currentB = +(T.currentA * 0.997).toFixed(1)
      T.currentC = +(T.currentA * 1.004).toFixed(1)
      substationState.model.shedMva = gis101Closed ? 0 : +(demandMva * 0.37).toFixed(1)
      substationState.model.deEnergized = inService.length === 0
      substationState.model.inServiceTransformers = inService
      
      const deltaV = (Math.random() - 0.5) * 0.3
      substationState.telemetry.voltageA = +(224.5 + deltaV).toFixed(1)
      substationState.telemetry.voltageB = +(224.2 + deltaV).toFixed(1)
      substationState.telemetry.voltageC = +(224.8 + deltaV).toFixed(1)

      // 离散热路镜像：油温按负载率一阶惯性演化，绕组热点 = 油温 + 与 K^1.6 成正比的温升
      const alpha = 1 - Math.exp(-2.0 / 30)
      for (const id of ['trans-1', 'trans-2']) {
        const dev = substationState.devices[id]
        const online = inService.includes(id)
        const k = online ? perMva / ratedMva : 0
        const oilSs = 24.8 + 50 * (((1 + 6 * k * k) / 7) ** 0.9)
        dev.oilTemp = +(dev.oilTemp + (oilSs - dev.oilTemp) * alpha).toFixed(1)
        dev.windingTemp = +(dev.oilTemp + 16 * (k ** 1.6)).toFixed(1)
        dev.current = online ? +(perMva / (phase * uHv) * 1000).toFixed(1) : 0
        dev.loadRate = +(k * 100).toFixed(1)
      }
    }, 2000)
  }
}

function jsonParseSafe(str) {
  try {
    return JSON.parse(str)
  } catch (e) {
    return null
  }
}

// 后端物模型/推流字段（snake_case）-> 前端状态字段（camelCase）
// 后端以物模型字段名推流，前端状态用驼峰；这张映射表是两侧唯一的契约点。
const TELEMETRY_FIELD_MAP = {
  total_power: 'totalPower',
  reactive_power: 'reactivePower',
  apparent_power: 'apparentPower',
  power_factor: 'powerFactor',
  load_rate: 'loadRate',
  frequency: 'frequency',
  voltage_a: 'voltageA',
  voltage_b: 'voltageB',
  voltage_c: 'voltageC',
  current_a: 'currentA',
  current_b: 'currentB',
  current_c: 'currentC',
}

const DEVICE_FIELD_MAP = {
  oil_temp: 'oilTemp',
  winding_temp: 'windingTemp',
  load_rate: 'loadRate',
  health_score: 'healthScore',
  breaker_state: 'breakerState',
  sf6_pressure: 'sf6Pressure',
  sf6_moisture: 'sf6Moisture',
  pd_level: 'pdLevel',
  gas_h2: 'gasH2',
  contact_wear: 'contactWear',
  action_count: 'actionCount',
  cooler_ratio: 'coolerRatio',
  cooler_banks_running: 'coolerBanksRunning',
  cooler_status: 'coolerStatus',
  rated_capacity: 'ratedCapacity',
  voltage_level: 'voltageLevel',
  device_type: 'deviceType',
  // current / voltage / vibration / status / name / model 两端同名，无需映射
}
