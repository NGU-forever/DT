<template>
  <div class="w-screen h-screen relative bg-[#060a14] overflow-hidden select-none text-slate-100">
    <!-- 1. 底层全屏 Three.js 3D WebGL 渲染容器 -->
    <div ref="canvasContainer" class="absolute inset-0 z-0 cursor-grab active:cursor-grabbing"></div>

    <!-- 2. 上层 HUD 数据看板交互界面 (pointer-events-none 让未被UI遮挡的区域可自由旋转缩放3D场景) -->
    <div class="relative z-10 w-full h-full flex flex-col justify-between pointer-events-none p-4 pb-3">
      <!-- 顶部 Header -->
      <Header @openFaultDialog="showFaultDialog = true" @importModel="onImportModel" />

      <!-- 中间左右两侧看板区 -->
      <div class="flex-1 flex justify-between items-start my-3 px-2 min-h-0 overflow-hidden">
        <!-- 左侧运行态势看板 -->
        <LeftPanel />

        <!-- 右侧告警与控制台看板 -->
        <RightPanel @locateDevice="onLocateDevice" />
      </div>

      <!-- 底部控制坞 (Dock) -->
      <div class="flex justify-center pb-2">
        <BottomDock @changeView="onChangeView" />
      </div>
    </div>

    <!-- 3. 设备详情测点抽屉弹窗 -->
    <DeviceModal
      v-if="state.interaction.selectedDeviceId"
      @close="state.interaction.selectedDeviceId = null"
      @focusDevice="onFocusDevice"
    />

    <!-- 4. 故障演练与仿真对话框 -->
    <FaultDialog
      v-if="showFaultDialog"
      @close="showFaultDialog = false"
      @triggerFault="onTriggerFault"
      @resetFault="onResetFault"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import Header from './components/Header.vue'
import LeftPanel from './components/LeftPanel.vue'
import RightPanel from './components/RightPanel.vue'
import BottomDock from './components/BottomDock.vue'
import DeviceModal from './components/DeviceModal.vue'
import FaultDialog from './components/FaultDialog.vue'

import { substationState, substationStore } from './store/substationStore.js'
import { SubstationScene } from './three/SubstationScene.js'

const state = substationState
const store = substationStore

const canvasContainer = ref(null)
const showFaultDialog = ref(false)

let sceneInstance = null
let simulationTicker = null

// 3D 射线拾取回调
function onSelectDevice(deviceId) {
  store.selectDevice(deviceId)
}

// 导入外部 Blender GLB 模型
async function onImportModel(arrayBuffer) {
  if (sceneInstance) {
    try {
      await sceneInstance.loadGLTFModel(arrayBuffer)
      // 切换到全景并调整相机
      sceneInstance.setCameraView('overview')
      alert('Blender 模型已成功导入场景！')
    } catch (e) {
      console.error('加载模型失败:', e)
      alert('模型解析失败，请确保导出为 glTF 2.0 (.glb) 格式')
    }
  }
}

// 视角切换
function onChangeView(viewId) {
  if (sceneInstance) {
    sceneInstance.setCameraView(viewId)
  }
}

// 特写定位到某个设备
function onFocusDevice(deviceId) {
  if (!sceneInstance) return
  if (deviceId === 'trans-1') {
    sceneInstance.setCameraView('transformer1')
  } else if (deviceId === 'trans-2') {
    sceneInstance.setCameraView('transformer2')
  } else if (deviceId.startsWith('gis')) {
    sceneInstance.setCameraView('gis')
  }
}

function onLocateDevice(deviceId) {
  onFocusDevice(deviceId)
}

// 故障演练触发
function onTriggerFault(faultType) {
  if (sceneInstance) {
    sceneInstance.handleFaultTrigger(faultType)
  }
}

// 故障复归
function onResetFault() {
  if (sceneInstance) {
    sceneInstance.clearFault()
  }
}

// 监听状态变化并联动 3D 场景特效
watch(
  () => state.interaction.showFlowParticles,
  (val) => {
    if (sceneInstance && sceneInstance.flowParticles) {
      sceneInstance.flowParticles.setActive(val)
    }
  }
)

watch(
  () => state.interaction.isHeatmapMode,
  (val) => {
    if (sceneInstance) {
      sceneInstance.setHeatmapMode(val, state.interaction.activeFaultType)
    }
  }
)

watch(
  () => state.interaction.isExplodedView,
  (val) => {
    if (sceneInstance) {
      sceneInstance.setExplodedView(val)
    }
  }
)

watch(
  () => state.devices['gis-201'].breakerState,
  (val) => {
    if (sceneInstance) {
      sceneInstance.updateBreakerState('gis-201', val)
    }
  }
)

watch(
  () => state.devices['gis-101'].breakerState,
  (val) => {
    if (sceneInstance) {
      sceneInstance.updateBreakerState('gis-101', val)
    }
  }
)

onMounted(() => {
  if (canvasContainer.value) {
    sceneInstance = new SubstationScene(canvasContainer.value, onSelectDevice)
  }
  // 启动数据周期波动仿真器
  simulationTicker = store.startSimulationTicker()
})

onUnmounted(() => {
  if (simulationTicker) {
    clearInterval(simulationTicker)
  }
  if (sceneInstance) {
    sceneInstance.destroy()
  }
})
</script>
