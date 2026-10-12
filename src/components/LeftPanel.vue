<template>
  <aside class="w-84 lg:w-96 flex flex-col space-y-3 pointer-events-auto select-none">
    <!-- 1. 实时全站负荷潮流趋势 (ECharts 曲线) -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-2">
        <div class="flex items-center space-x-2">
          <Activity class="w-4 h-4 text-cyber-accent" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">全站实时负荷潮流趋势</h2>
        </div>
        <span class="text-[11px] text-cyan-400 font-tech">更新中: 2s/点</span>
      </div>

      <!-- 实时负荷 ECharts 容器 -->
      <div ref="loadChartRef" class="w-full h-36"></div>

      <!-- 负荷关键遥测指标 -->
      <div class="grid grid-cols-3 gap-2 mt-2 pt-2 border-t border-slate-800/80 text-center">
        <div class="bg-slate-900/40 p-1.5 rounded border border-slate-800">
          <div class="text-[10px] text-slate-400">有功功率 P</div>
          <div class="text-xs font-bold font-tech text-cyan-300">{{ state.telemetry.totalPower }} MW</div>
        </div>
        <div class="bg-slate-900/40 p-1.5 rounded border border-slate-800">
          <div class="text-[10px] text-slate-400">无功功率 Q</div>
          <div class="text-xs font-bold font-tech text-amber-300">{{ state.telemetry.reactivePower }} Mvar</div>
        </div>
        <div class="bg-slate-900/40 p-1.5 rounded border border-slate-800">
          <div class="text-[10px] text-slate-400">功率因数 cosφ</div>
          <div class="text-xs font-bold font-tech text-emerald-400">{{ state.telemetry.powerFactor }}</div>
        </div>
      </div>
    </div>

    <!-- 2. 三相电压平衡与母线电能质量 -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-2">
        <div class="flex items-center space-x-2">
          <Zap class="w-4 h-4 text-amber-400" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">220kV 母线三相电能质量</h2>
        </div>
        <span class="text-[11px] text-emerald-400 flex items-center">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1 animate-pulse"></span>
          合格率 100%
        </span>
      </div>

      <div class="space-y-2">
        <div>
          <div class="flex justify-between text-xs text-slate-300 mb-1">
            <span class="text-yellow-400">A相电压 Ua</span>
            <span class="font-tech">{{ state.telemetry.voltageA }} kV ({{ state.telemetry.currentA }} A)</span>
          </div>
          <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-yellow-400 rounded-full" :style="{ width: `${(state.telemetry.voltageA / 240) * 100}%` }"></div>
          </div>
        </div>

        <div>
          <div class="flex justify-between text-xs text-slate-300 mb-1">
            <span class="text-green-400">B相电压 Ub</span>
            <span class="font-tech">{{ state.telemetry.voltageB }} kV ({{ state.telemetry.currentB }} A)</span>
          </div>
          <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-green-400 rounded-full" :style="{ width: `${(state.telemetry.voltageB / 240) * 100}%` }"></div>
          </div>
        </div>

        <div>
          <div class="flex justify-between text-xs text-slate-300 mb-1">
            <span class="text-red-400">C相电压 Uc</span>
            <span class="font-tech">{{ state.telemetry.voltageC }} kV ({{ state.telemetry.currentC }} A)</span>
          </div>
          <div class="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div class="h-full bg-red-400 rounded-full" :style="{ width: `${(state.telemetry.voltageC / 240) * 100}%` }"></div>
          </div>
        </div>
      </div>

      <div class="mt-2.5 pt-2 border-t border-slate-800/80 flex justify-between items-center text-xs">
        <span class="text-slate-400">系统频率:</span>
        <span class="font-tech text-cyan-300 font-bold">{{ state.telemetry.frequency }} Hz</span>
        <span class="text-slate-400 ml-2">电压不平衡度:</span>
        <span class="font-tech text-emerald-400 font-bold">0.18%</span>
      </div>
    </div>

    <!-- 3. 主变压器运行健康度雷达综合评价 (ECharts Radar) -->
    <div class="glass-panel rounded-xl p-3.5 tech-corner">
      <div class="flex items-center justify-between pb-2 border-b border-slate-700/50 mb-2">
        <div class="flex items-center space-x-2">
          <Layers class="w-4 h-4 text-cyan-400" />
          <h2 class="text-sm font-bold tracking-wide text-white font-tech">主变压器多维健康评价</h2>
        </div>
        <div class="text-[11px] font-tech text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded border border-emerald-500/40">
          健康指数: {{ state.devices['trans-1'].healthScore }}
        </div>
      </div>

      <!-- 雷达图容器 -->
      <div ref="radarChartRef" class="w-full h-44"></div>

      <!-- 快速测点卡片 -->
      <div class="grid grid-cols-2 gap-2 text-xs">
        <div class="p-2 rounded bg-slate-900/60 border border-slate-800">
          <div class="text-slate-400 text-[11px]">1#主变顶层油温</div>
          <div class="font-tech text-sm font-bold" :class="state.devices['trans-1'].oilTemp > 85 ? 'text-red-400 animate-pulse' : 'text-cyan-300'">
            {{ state.devices['trans-1'].oilTemp }} ℃
          </div>
        </div>
        <div class="p-2 rounded bg-slate-900/60 border border-slate-800">
          <div class="text-slate-400 text-[11px]">局部放电 (PD)</div>
          <div class="font-tech text-sm font-bold text-emerald-400">
            {{ state.devices['trans-1'].pdLevel }} pC
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { Activity, Zap, Layers } from 'lucide-vue-next'
import { substationState } from '../store/substationStore.js'

const state = substationState

const loadChartRef = ref(null)
const radarChartRef = ref(null)

let loadChart = null
let radarChart = null
let chartTimer = null

// 历史负荷数据队列
const timeQueue = []
const loadQueue = []

function initCharts() {
  if (loadChartRef.value) {
    loadChart = echarts.init(loadChartRef.value)
    
    // 初始化过去10个数据点
    const now = new Date()
    for (let i = 9; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 2000)
      timeQueue.push(t.toTimeString().slice(0, 8))
      loadQueue.push(+(state.telemetry.totalPower + (Math.random() - 0.5) * 2).toFixed(1))
    }

    const loadOption = {
      grid: { top: 12, bottom: 20, left: 35, right: 10 },
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: timeQueue,
        axisLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } },
        axisLabel: { color: '#64748b', fontSize: 9 }
      },
      yAxis: {
        type: 'value',
        min: 160,
        max: 210,
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
        axisLabel: { color: '#64748b', fontSize: 9 }
      },
      series: [
        {
          name: '负荷 P',
          type: 'line',
          smooth: true,
          showSymbol: false,
          data: loadQueue,
          lineStyle: { color: '#00f0ff', width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 240, 255, 0.35)' },
              { offset: 1, color: 'rgba(0, 240, 255, 0.01)' }
            ])
          }
        }
      ]
    }
    loadChart.setOption(loadOption)
  }

  if (radarChartRef.value) {
    radarChart = echarts.init(radarChartRef.value)
    updateRadarOption()
  }

  window.addEventListener('resize', handleResize)
}

function updateRadarOption() {
  if (!radarChart) return
  const dev = state.devices['trans-1']
  const radarOption = {
    radar: {
      indicator: [
        { name: '绝缘裕度', max: 100 },
        { name: '温升状态', max: 100 },
        { name: '油色谱指标', max: 100 },
        { name: '机械振动', max: 100 },
        { name: '局放抑制', max: 100 },
      ],
      radius: '65%',
      splitNumber: 4,
      axisName: { color: '#94a3b8', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(0, 240, 255, 0.2)' } }
    },
    series: [
      {
        name: '健康指标',
        type: 'radar',
        data: [
          {
            value: [
              dev.healthScore > 80 ? 95 : 60,
              dev.oilTemp > 85 ? 40 : 92,
              94,
              90,
              88
            ],
            name: '1# 主变健康度',
            symbolSize: 4,
            lineStyle: { color: '#00f0ff', width: 2 },
            areaStyle: { color: 'rgba(0, 240, 255, 0.25)' }
          }
        ]
      }
    ]
  }
  radarChart.setOption(radarOption)
}

function handleResize() {
  if (loadChart) loadChart.resize()
  if (radarChart) radarChart.resize()
}

// 监听遥测负荷变化动态喂入图表
watch(
  () => state.telemetry.totalPower,
  (newVal) => {
    if (!loadChart) return
    const now = new Date().toTimeString().slice(0, 8)
    timeQueue.shift()
    timeQueue.push(now)
    loadQueue.shift()
    loadQueue.push(newVal)

    loadChart.setOption({
      xAxis: { data: timeQueue },
      series: [{ data: loadQueue }]
    })
  }
)

watch(
  () => [state.devices['trans-1'].oilTemp, state.devices['trans-1'].healthScore],
  () => {
    updateRadarOption()
  }
)

onMounted(() => {
  initCharts()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (loadChart) loadChart.dispose()
  if (radarChart) radarChart.dispose()
})
</script>
