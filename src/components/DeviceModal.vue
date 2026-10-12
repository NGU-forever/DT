<template>
  <div
    v-if="device"
    class="fixed top-20 right-6 w-96 glass-panel rounded-2xl p-5 z-30 shadow-2xl border border-cyan-500/40 pointer-events-auto transition-all animate-fadeIn"
  >
    <!-- 标题与关闭按钮 -->
    <div class="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-3">
      <div class="flex items-center space-x-2">
        <div class="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300">
          <Cpu class="w-4 h-4" />
        </div>
        <div>
          <h3 class="text-sm font-bold text-white font-tech">{{ device.name }}</h3>
          <div class="text-[11px] text-slate-400">型号: {{ device.model }}</div>
        </div>
      </div>
      <button
        @click="close"
        class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
      >
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- 设备运行健康度与状态标签 -->
    <div class="flex items-center justify-between mb-4 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
      <div class="flex items-center space-x-2">
        <span
          class="w-2.5 h-2.5 rounded-full"
          :class="device.status === 'danger' ? 'bg-rose-500 animate-ping' : (device.status === 'warning' ? 'bg-amber-400' : 'bg-emerald-400')"
        ></span>
        <span class="text-xs font-semibold" :class="device.status === 'danger' ? 'text-rose-400' : 'text-slate-200'">
          {{ device.status === 'danger' ? '异常报警状态' : (device.status === 'warning' ? '关注预警状态' : '正常投运受控') }}
        </span>
      </div>
      <div class="text-xs font-tech">
        健康度综合分:
        <span class="font-bold" :class="device.healthScore < 80 ? 'text-rose-400' : 'text-cyan-300'">
          {{ device.healthScore }} 分
        </span>
      </div>
    </div>

    <!-- 遥测遥信详细测点列表 -->
    <div class="space-y-2 text-xs mb-4">
      <div v-if="device.oilTemp !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">顶层油温</span>
        <span class="font-tech font-bold" :class="device.oilTemp > 85 ? 'text-rose-400' : 'text-cyan-300'">
          {{ device.oilTemp }} ℃
        </span>
      </div>

      <div v-if="device.windingTemp !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">绕组热点温度</span>
        <span class="font-tech font-bold" :class="device.windingTemp > 95 ? 'text-rose-400' : 'text-amber-300'">
          {{ device.windingTemp }} ℃
        </span>
      </div>

      <div v-if="device.voltage !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">运行线电压</span>
        <span class="font-tech font-bold text-slate-200">{{ device.voltage }} kV</span>
      </div>

      <div v-if="device.current !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">运行相电流</span>
        <span class="font-tech font-bold text-cyan-300">{{ device.current }} A</span>
      </div>

      <div v-if="device.sf6Pressure > 0" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">SF6 气体绝缘压力</span>
        <span class="font-tech font-bold" :class="device.sf6Pressure < 0.5 ? 'text-rose-400' : 'text-emerald-400'">
          {{ device.sf6Pressure }} MPa
        </span>
      </div>

      <div v-if="device.sf6Moisture !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">SF6 微水含量</span>
        <span class="font-tech font-bold text-slate-200">{{ device.sf6Moisture }} ppm</span>
      </div>

      <div v-if="device.loadRate !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">当前负载率</span>
        <span class="font-tech font-bold" :class="device.loadRate > 100 ? 'text-rose-400' : device.loadRate > 90 ? 'text-amber-300' : 'text-emerald-400'">
          {{ device.loadRate }} %
        </span>
      </div>

      <div v-if="device.coolerRatio !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">冷却器可用率</span>
        <span class="font-tech font-bold" :class="device.coolerRatio < 0.9 ? 'text-amber-300' : 'text-slate-200'">
          {{ (device.coolerRatio * 100).toFixed(0) }} %
        </span>
      </div>

      <div v-if="device.pdLevel !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">特高频局放 (UHF PD)</span>
        <span class="font-tech font-bold text-emerald-400">{{ device.pdLevel }} pC</span>
      </div>

      <div v-if="device.vibration !== undefined" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">油箱振动烈度</span>
        <span class="font-tech font-bold text-slate-200">{{ device.vibration }} mm/s</span>
      </div>

      <div v-if="device.coolerStatus" class="flex justify-between p-2 rounded bg-slate-950/40 border border-slate-800/80">
        <span class="text-slate-400">强迫油循环风冷</span>
        <span class="font-tech text-cyan-300">{{ device.coolerStatus }}</span>
      </div>
    </div>

    <!-- 底部操作联动快捷按钮 -->
    <div class="flex items-center space-x-2 pt-2 border-t border-slate-800">
      <button
        @click="focusDevice"
        class="flex-1 py-2 rounded-lg bg-cyber-accent/20 hover:bg-cyber-accent/30 text-cyber-accent border border-cyber-accent/40 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
      >
        <Crosshair class="w-3.5 h-3.5" />
        <span>特写运镜</span>
      </button>

      <button
        v-if="device.id.startsWith('trans')"
        @click="store.toggleExploded()"
        class="flex-1 py-2 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/40 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
      >
        <Box class="w-3.5 h-3.5" />
        <span>{{ state.interaction.isExplodedView ? '还原部件' : '爆炸拆解' }}</span>
      </button>

      <button
        v-if="device.breakerState !== undefined"
        @click="store.toggleBreaker(device.id)"
        class="flex-1 py-2 rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all"
        :class="device.breakerState
          ? 'bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40'
          : 'bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40'"
      >
        <Power class="w-3.5 h-3.5" />
        <span>{{ device.breakerState ? '倒闸分闸' : '倒闸合闸' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Cpu, X, Crosshair, Box, Power } from 'lucide-vue-next'
import { substationState, substationStore } from '../store/substationStore.js'

const emit = defineEmits(['close', 'focusDevice'])

const state = substationState
const store = substationStore

const device = computed(() => {
  const id = state.interaction.selectedDeviceId
  return id ? state.devices[id] : null
})

function close() {
  store.selectDevice(null)
  emit('close')
}

function focusDevice() {
  if (device.value) {
    emit('focusDevice', device.value.id)
  }
}
</script>
