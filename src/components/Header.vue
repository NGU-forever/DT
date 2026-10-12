<template>
  <header class="w-full h-16 px-6 flex items-center justify-between select-none pointer-events-auto relative z-20">
    <!-- 背景流光与科技边框 -->
    <div class="absolute inset-0 bg-gradient-to-b from-[#081326]/95 via-[#060e1d]/85 to-transparent border-b border-cyber-accent/30 backdrop-blur-md"></div>
    <div class="absolute bottom-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-cyber-accent to-transparent"></div>

    <!-- 左侧：系统标题与变电站等级 -->
    <div class="relative flex items-center space-x-3">
      <div class="w-10 h-10 rounded-lg bg-cyber-accent/15 border border-cyber-accent/40 flex items-center justify-center shadow-cyber-glow">
        <Zap class="w-6 h-6 text-cyber-accent animate-pulse" />
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="text-xl font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-cyan-300 font-tech">
            {{ state.stationInfo.name }}
          </h1>
          <span class="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
            220kV 枢纽站
          </span>
          <span
            class="px-2 py-0.5 text-[11px] font-semibold rounded border flex items-center space-x-1 transition-all"
            :class="state.backend.connected ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-cyber-glow' : 'bg-amber-500/20 text-amber-300 border-amber-500/40'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="state.backend.connected ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'"></span>
            <span>{{ state.backend.connected ? 'FastAPI + OPC UA + MQTT: 实时联动' : '本地离线模式' }}</span>
          </span>
          <!-- 孪生机理模型运行状态（IEC 60076-7 一阶热路 + 拓扑潮流） -->
          <span
            class="px-2 py-0.5 text-[11px] font-semibold rounded border flex items-center space-x-1 transition-all"
            :class="state.model.deEnergized
              ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
              : state.model.converged
                ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                : 'bg-sky-500/20 text-sky-300 border-sky-500/40'"
            :title="`IEC 60076-7 一阶热路模型 + 拓扑潮流模型 · 时间压缩 ${state.model.timeCompression} 倍`"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="state.model.converged ? 'bg-indigo-400' : 'bg-sky-400 animate-ping'"></span>
            <span v-if="state.model.deEnergized">全站失压 · 甩负荷 {{ state.model.shedMva }} MVA</span>
            <span v-else-if="state.model.shedMva > 0">已甩负荷 {{ state.model.shedMva }} MVA</span>
            <span v-else>{{ state.model.converged ? '模型已收敛' : '模型演化中' }} · step {{ state.model.step }}</span>
          </span>
        </div>
        <div class="text-xs text-slate-400 flex items-center space-x-3 mt-0.5">
          <span>投运时间: {{ state.stationInfo.commissionDate }}</span>
          <span class="text-slate-600">|</span>
          <span class="text-emerald-400 flex items-center">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-ping"></span>
            {{ state.stationInfo.status }}
          </span>
        </div>
      </div>
    </div>

    <!-- 中间：核心关键指标看板 (安全天数、负荷率、环境) -->
    <div class="relative hidden md:flex items-center space-x-8">
      <div class="flex items-center space-x-2">
        <ShieldCheck class="w-4 h-4 text-emerald-400" />
        <div class="text-xs text-slate-400">安全运行</div>
        <div class="text-lg font-bold font-tech text-white">
          {{ state.stationInfo.safeDays }} <span class="text-xs text-slate-400 font-normal">天</span>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <Activity class="w-4 h-4 text-cyber-accent" />
        <div class="text-xs text-slate-400">实时总负荷</div>
        <div class="text-lg font-bold font-tech text-cyan-300">
          {{ state.telemetry.totalPower }} <span class="text-xs text-slate-400 font-normal">MW</span>
        </div>
      </div>

      <div class="flex items-center space-x-2">
        <Gauge class="w-4 h-4 text-amber-400" />
        <div class="text-xs text-slate-400">综合负载率</div>
        <div class="text-lg font-bold font-tech text-amber-300">
          {{ state.telemetry.loadRate }}%
        </div>
      </div>

      <div class="flex items-center space-x-2 text-xs text-slate-300 bg-slate-900/60 px-3 py-1.5 rounded-full border border-slate-700/50">
        <ThermometerSun class="w-3.5 h-3.5 text-orange-400" />
        <span>{{ state.environment.temp }}℃</span>
        <Droplets class="w-3.5 h-3.5 text-blue-400 ml-1.5" />
        <span>{{ state.environment.humidity }}%</span>
        <Wind class="w-3.5 h-3.5 text-cyan-400 ml-1.5" />
        <span>{{ state.environment.windSpeed }}m/s</span>
      </div>
    </div>

    <!-- 右侧：当前时钟、故障注入预案与全屏 -->
    <div class="relative flex items-center space-x-3">
      <div class="text-right hidden sm:block">
        <div class="text-sm font-bold font-tech tracking-wider text-cyan-300">{{ currentTime }}</div>
        <div class="text-[11px] text-slate-400">{{ currentDate }}</div>
      </div>

      <!-- 导入 Blender 模型 -->
      <label class="px-3 py-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 text-xs font-semibold flex items-center space-x-1.5 cursor-pointer transition-all shadow-cyber-glow">
        <UploadCloud class="w-3.5 h-3.5" />
        <span>导入 Blender (.glb)</span>
        <input type="file" accept=".glb,.gltf" class="hidden" @change="handleFileUpload" />
      </label>

      <button
        @click="$emit('openFaultDialog')"
        class="px-3 py-1.5 rounded bg-gradient-to-r from-amber-500/20 to-rose-500/20 hover:from-amber-500/30 hover:to-rose-500/30 border border-amber-500/40 text-amber-300 text-xs font-semibold flex items-center space-x-1.5 transition-all shadow-warning-glow"
      >
        <AlertTriangle class="w-3.5 h-3.5" />
        <span>故障预案演练</span>
      </button>

      <button
        @click="toggleFullscreen"
        class="p-2 rounded bg-slate-800/60 hover:bg-slate-700/70 border border-slate-700 text-slate-300 hover:text-white transition-all"
        title="全屏切换"
      >
        <Maximize2 class="w-4 h-4" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import {
  Zap,
  Activity,
  ShieldCheck,
  Gauge,
  ThermometerSun,
  Droplets,
  Wind,
  AlertTriangle,
  Maximize2,
  UploadCloud
} from 'lucide-vue-next'
import { substationState } from '../store/substationStore.js'

const emit = defineEmits(['openFaultDialog', 'importModel'])

const state = substationState
const currentTime = ref('')
const currentDate = ref('')

function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    emit('importModel', e.target.result)
  }
  reader.readAsArrayBuffer(file)
}

let timer = null

function updateClock() {
  const now = new Date()
  currentTime.value = now.toTimeString().slice(0, 8)
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'short'
  })
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
    }
  }
}

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
