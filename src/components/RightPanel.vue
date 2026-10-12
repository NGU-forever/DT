<template>
  <aside class="w-84 lg:w-96 flex flex-col space-y-3 pointer-events-auto select-none">
    <!-- 1. 倒闸仿真与断路器遥控控制台 -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-2">
        <div class="flex items-center space-x-2">
          <Sliders class="w-4 h-4 text-cyan-400" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">倒闸操作仿真控制台</h2>
        </div>
        <span class="text-[10px] text-amber-300 bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-500/30">
          远程遥控模式
        </span>
      </div>

      <!-- 断路器遥控卡片列表 -->
      <div class="space-y-2.5">
        <!-- 220kV GIS 201 -->
        <div class="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
              <span>{{ state.devices['gis-201'].name }}</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-2 font-tech">
              <span>SF6: {{ state.devices['gis-201'].sf6Pressure }} MPa</span>
              <span>I: {{ state.devices['gis-201'].current }} A</span>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <span
              class="px-2 py-0.5 rounded text-[11px] font-bold font-tech"
              :class="state.devices['gis-201'].breakerState ? 'bg-red-500/20 text-red-400 border border-red-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'"
            >
              {{ state.devices['gis-201'].breakerState ? '合闸 (通)' : '分闸 (断)' }}
            </span>
            <button
              @click="store.toggleBreaker('gis-201')"
              class="px-2.5 py-1 text-xs rounded font-medium transition-all"
              :class="state.devices['gis-201'].breakerState
                ? 'bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40'
                : 'bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 border border-emerald-500/40'"
            >
              {{ state.devices['gis-201'].breakerState ? '遥控分闸' : '遥控合闸' }}
            </button>
          </div>
        </div>

        <!-- 110kV GIS 101 -->
        <div class="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div class="text-xs font-bold text-slate-200 flex items-center space-x-1.5">
              <span>{{ state.devices['gis-101'].name }}</span>
            </div>
            <div class="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-2 font-tech">
              <span>SF6: {{ state.devices['gis-101'].sf6Pressure }} MPa</span>
              <span>I: {{ state.devices['gis-101'].current }} A</span>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <span
              class="px-2 py-0.5 rounded text-[11px] font-bold font-tech"
              :class="state.devices['gis-101'].breakerState ? 'bg-red-500/20 text-red-400 border border-red-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'"
            >
              {{ state.devices['gis-101'].breakerState ? '合闸 (通)' : '分闸 (断)' }}
            </span>
            <button
              @click="store.toggleBreaker('gis-101')"
              class="px-2.5 py-1 text-xs rounded font-medium transition-all"
              :class="state.devices['gis-101'].breakerState
                ? 'bg-rose-600/30 hover:bg-rose-600/50 text-rose-200 border border-rose-500/40'
                : 'bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 border border-emerald-500/40'"
            >
              {{ state.devices['gis-101'].breakerState ? '遥控分闸' : '遥控合闸' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. 实时预警与事故告警流水列表 -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner flex-1 flex flex-col min-h-0">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-2">
        <div class="flex items-center space-x-2">
          <BellRing class="w-4 h-4 text-rose-400 animate-bounce" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">站内实时预警与告警</h2>
        </div>
        <span class="text-[10px] text-rose-300 bg-rose-500/20 px-1.5 py-0.5 rounded border border-rose-500/30">
          未处理: {{ unhandledCount }} 条
        </span>
      </div>

      <!-- 告警条目列表 (带滚动) -->
      <div class="space-y-2 overflow-y-auto max-h-48 pr-1 flex-1">
        <div
          v-for="alm in state.alarms"
          :key="alm.id"
          @click="locateAlarmDevice(alm.deviceId)"
          class="p-2 rounded-lg cursor-pointer transition-all border"
          :class="getAlarmClass(alm.level)"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs font-bold flex items-center space-x-1">
              <span class="w-2 h-2 rounded-full" :class="alm.level === 'danger' ? 'bg-red-500 animate-ping' : (alm.level === 'warning' ? 'bg-amber-400' : 'bg-cyan-400')"></span>
              <span>{{ alm.deviceName }}</span>
            </span>
            <span class="text-[10px] font-tech text-slate-400">{{ alm.time }}</span>
          </div>
          <div class="text-[11px] leading-relaxed text-slate-300">
            {{ alm.text }}
          </div>
          <div class="mt-1 flex items-center justify-between text-[10px] text-cyan-400/80">
            <span>点击在三维场景中聚焦定位 »</span>
            <span v-if="alm.handled" class="text-emerald-400">已响应</span>
            <span v-else class="text-rose-400">待处置</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. 操作记录与巡检审计日志 -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-1.5">
        <div class="flex items-center space-x-2">
          <FileText class="w-4 h-4 text-slate-300" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">变电运维操作记录流水</h2>
        </div>
      </div>
      <div class="space-y-1.5 overflow-y-auto max-h-28 pr-1 text-xs">
        <div
          v-for="log in state.operationLogs"
          :key="log.id"
          class="text-slate-400 text-[11px] leading-snug flex items-start space-x-2 py-0.5 border-b border-slate-800/40"
        >
          <span class="font-tech text-cyan-400">{{ log.time }}</span>
          <span class="px-1 py-0.2 rounded bg-slate-800 text-[10px] text-slate-300">{{ log.type }}</span>
          <span class="text-slate-300 flex-1 truncate">{{ log.content }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Sliders, BellRing, FileText } from 'lucide-vue-next'
import { substationState, substationStore } from '../store/substationStore.js'

const emit = defineEmits(['locateDevice'])

const state = substationState
const store = substationStore

const unhandledCount = computed(() => {
  return state.alarms.filter(a => !a.handled).length
})

function getAlarmClass(level) {
  if (level === 'danger') {
    return 'bg-rose-950/40 border-rose-500/40 hover:bg-rose-900/50'
  } else if (level === 'warning') {
    return 'bg-amber-950/30 border-amber-500/40 hover:bg-amber-900/40'
  }
  return 'bg-slate-900/60 border-slate-800 hover:bg-slate-800/60'
}

function locateAlarmDevice(deviceId) {
  store.selectDevice(deviceId)
  emit('locateDevice', deviceId)
}
</script>
