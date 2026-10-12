<template>
  <nav class="h-14 px-5 py-2 glass-panel rounded-2xl flex items-center space-x-3 pointer-events-auto select-none shadow-2xl border border-cyan-500/30">
    <!-- 1. 视角切换按键组 -->
    <div class="flex items-center space-x-1.5 pr-3 border-r border-slate-700/60">
      <button
        v-for="v in viewOptions"
        :key="v.id"
        @click="selectView(v.id)"
        class="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all"
        :class="state.interaction.currentView === v.id
          ? 'bg-cyber-accent text-slate-950 font-bold shadow-cyber-glow'
          : 'bg-slate-800/60 text-slate-300 hover:bg-slate-700/60 hover:text-white'"
      >
        <component :is="v.icon" class="w-3.5 h-3.5" />
        <span>{{ v.label }}</span>
      </button>
    </div>

    <!-- 2. 特效与模式开关组 -->
    <div class="flex items-center space-x-2 pr-3 border-r border-slate-700/60">
      <!-- 潮流粒子开关 -->
      <button
        @click="store.toggleFlowParticles()"
        class="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all border"
        :class="state.interaction.showFlowParticles
          ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 shadow-cyber-glow'
          : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-slate-200'"
      >
        <Waves class="w-3.5 h-3.5" :class="state.interaction.showFlowParticles ? 'animate-pulse' : ''" />
        <span>潮流粒子流</span>
      </button>

      <!-- 红外热成像模式 -->
      <button
        @click="store.toggleHeatmap()"
        class="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all border"
        :class="state.interaction.isHeatmapMode
          ? 'bg-amber-500/25 border-amber-500/60 text-amber-300 shadow-warning-glow'
          : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-slate-200'"
      >
        <Flame class="w-3.5 h-3.5" />
        <span>红外热成像模式</span>
      </button>

      <!-- 设备爆炸拆解 -->
      <button
        @click="store.toggleExploded()"
        class="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center space-x-1.5 transition-all border"
        :class="state.interaction.isExplodedView
          ? 'bg-indigo-500/25 border-indigo-500/60 text-indigo-300'
          : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:text-slate-200'"
      >
        <Box class="w-3.5 h-3.5" />
        <span>主变结构拆解</span>
      </button>
    </div>

    <!-- 3. 故障复归快捷按键 (当有故障时高亮) -->
    <div class="flex items-center">
      <button
        v-if="state.interaction.activeFaultType"
        @click="store.clearFault()"
        class="px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 bg-rose-600 hover:bg-rose-500 text-white shadow-danger-glow animate-pulse transition-all"
      >
        <RotateCcw class="w-3.5 h-3.5" />
        <span>复归故障状态</span>
      </button>
      <div v-else class="text-[11px] text-slate-400 font-tech flex items-center space-x-1.5 px-2">
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
        <span>系统拓扑运行稳定</span>
      </div>
    </div>
  </nav>
</template>

<script setup>
import {
  Globe,
  Radio,
  Sliders,
  Rotate3d,
  Waves,
  Flame,
  Box,
  RotateCcw
} from 'lucide-vue-next'
import { substationState, substationStore } from '../store/substationStore.js'

const emit = defineEmits(['changeView'])

const state = substationState
const store = substationStore

const viewOptions = [
  { id: 'overview', label: '全景鸟瞰', icon: Globe },
  { id: 'transformer1', label: '1# 主变特写', icon: Radio },
  { id: 'transformer2', label: '2# 主变特写', icon: Radio },
  { id: 'gis', label: 'GIS 设备区', icon: Sliders },
  { id: 'patrol', label: '360° 巡航', icon: Rotate3d },
]

function selectView(viewId) {
  store.setView(viewId)
  emit('changeView', viewId)
}
</script>
