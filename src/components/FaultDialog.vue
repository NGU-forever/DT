<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm pointer-events-auto">
    <div class="w-full max-w-xl glass-panel rounded-2xl p-6 border border-amber-500/40 shadow-2xl relative">
      <!-- 头部 -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-700/60 mb-4">
        <div class="flex items-center space-x-2.5">
          <div class="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-300">
            <AlertTriangle class="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 class="text-base font-bold text-white font-tech">变电站应急预案与故障仿真注入</h3>
            <div class="text-xs text-slate-400">模拟典型电力一次设备突发事故并联动数字孪生处置流程</div>
          </div>
        </div>
        <button
          @click="$emit('close')"
          class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-all"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- 预设演练故障列表 -->
      <div class="space-y-3 mb-6">
        <!-- 故障 1: 主变过热 -->
        <div
          @click="selectFault('trans_overheat')"
          class="p-3.5 rounded-xl border transition-all cursor-pointer flex items-start space-x-3.5"
          :class="state.interaction.activeFaultType === 'trans_overheat'
            ? 'bg-rose-950/60 border-rose-500 shadow-danger-glow'
            : 'bg-slate-900/60 border-slate-800 hover:border-amber-500/50 hover:bg-slate-800/60'"
        >
          <div class="p-2 rounded-lg bg-rose-500/20 text-rose-400 mt-0.5">
            <Flame class="w-4 h-4" />
          </div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <h4 class="text-xs font-bold text-slate-100">演练事故一：1# 主变绕组严重过热</h4>
              <span class="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                I级紧急缺陷
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">
              变压器顶层油温骤升至 91.5℃，自动联动红外热像视野高亮，主变脚底产生红色告警光环，触发风冷系统事故强排。
            </p>
          </div>
        </div>

        <!-- 故障 2: GIS SF6 气体泄漏 -->
        <div
          @click="selectFault('sf6_leak')"
          class="p-3.5 rounded-xl border transition-all cursor-pointer flex items-start space-x-3.5"
          :class="state.interaction.activeFaultType === 'sf6_leak'
            ? 'bg-amber-950/60 border-amber-500 shadow-warning-glow'
            : 'bg-slate-900/60 border-slate-800 hover:border-amber-500/50 hover:bg-slate-800/60'"
        >
          <div class="p-2 rounded-lg bg-amber-500/20 text-amber-400 mt-0.5">
            <Gauge class="w-4 h-4" />
          </div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <h4 class="text-xs font-bold text-slate-100">演练事故二：220kV GIS 201 气室 SF6 绝缘泄漏</h4>
              <span class="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                II级严重缺陷
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">
              气室压力骤降至 0.42MPa，触发断路器跳闸闭锁指示，三维镜头自动飞向 GIS 设备区并发出橙色预警光柱。
            </p>
          </div>
        </div>

        <!-- 故障 3: 线路过载跳闸 -->
        <div
          @click="selectFault('overload_trip')"
          class="p-3.5 rounded-xl border transition-all cursor-pointer flex items-start space-x-3.5"
          :class="state.interaction.activeFaultType === 'overload_trip'
            ? 'bg-purple-950/60 border-purple-500 shadow-cyber-glow'
            : 'bg-slate-900/60 border-slate-800 hover:border-amber-500/50 hover:bg-slate-800/60'"
        >
          <div class="p-2 rounded-lg bg-purple-500/20 text-purple-400 mt-0.5">
            <ZapOff class="w-4 h-4" />
          </div>
          <div class="flex-1">
            <div class="flex items-center justify-between">
              <h4 class="text-xs font-bold text-slate-100">演练事故三：110kV 出线短路过流速断保护跳闸</h4>
              <span class="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                保护动作跳闸
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-1">
              出线断路器自动变位为分闸，出线侧电流归零，架空导线电流粒子流停止流动，生成事故跳闸分析报告。
            </p>
          </div>
        </div>
      </div>

      <!-- 底部控制按键 -->
      <div class="flex items-center justify-between pt-3 border-t border-slate-800">
        <button
          @click="resetFault"
          class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center space-x-1.5 transition-all"
        >
          <RotateCcw class="w-3.5 h-3.5" />
          <span>全站状态一键复归</span>
        </button>

        <button
          @click="$emit('close')"
          class="px-5 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-bold transition-all shadow-cyber-glow"
        >
          进入演练场景
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { AlertTriangle, X, Flame, Gauge, ZapOff, RotateCcw } from 'lucide-vue-next'
import { substationState, substationStore } from '../store/substationStore.js'

const emit = defineEmits(['close', 'triggerFault', 'resetFault'])

const state = substationState
const store = substationStore

function selectFault(type) {
  store.injectFault(type)
  emit('triggerFault', type)
}

function resetFault() {
  store.clearFault()
  emit('resetFault')
}
</script>
