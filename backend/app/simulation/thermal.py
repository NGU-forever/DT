"""变压器热路模型：IEC 60076-7《电力变压器负载导则》的一阶形式。

为什么要有这一层：原 Demo 的油温/绕组温度是写死的数字，故障注入直接把温度"赋值"到
91.5℃。那种做法经不起追问——温度不是算出来的，是填上去的。

本模块把温度变成**负载率与冷却能力的函数**：

- 顶层油温稳态温升：Δθ_oil = Δθ_oil,rated · ((1 + R·K²) / (1 + R))^x
- 绕组热点对油温升：Δθ_hs   = Δθ_hs,rated · K^y
- 热点温度：        θ_hs     = θ_ambient + Δθ_oil + Δθ_hs
- 暂态过程：一阶惯性 dθ/dt = (θ_∞ - θ) / τ

其中 K 为负载率，R 为额定负载损耗与空载损耗之比，x/y 为油指数与绕组指数。
于是"冷却器全停"不再是一个赋值，而是把冷却可用率下调，让模型自己把温度推上去。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class ThermalState:
    """变压器热状态。"""

    oil_temp: float  # 顶层油温 ℃
    hot_spot_grad: float  # 绕组热点对顶层油的温升 K

    @property
    def hot_spot_temp(self) -> float:
        """绕组热点温度 ℃（工程上即"绕组温度"）。"""
        return self.oil_temp + self.hot_spot_grad


class TransformerThermalModel:
    """单台变压器的热路模型（参数来自物模型 physics 段）。"""

    def __init__(self, physics: Dict[str, Any], ambient_temp_c: float, time_compression: float = 1.0):
        self.loss_ratio_r = float(physics.get("loss_ratio_r", 6.0))
        self.oil_exponent_x = float(physics.get("oil_exponent_x", 0.9))
        self.winding_exponent_y = float(physics.get("winding_exponent_y", 1.6))
        self.top_oil_rise_rated_k = float(physics.get("top_oil_rise_rated_k", 50.0))
        self.hot_spot_gradient_rated_k = float(physics.get("hot_spot_gradient_rated_k", 16.0))
        self.ambient_temp_c = float(ambient_temp_c)

        # 真实时间常数按声明倍数压缩到 Demo 可观察的尺度（并显式记录，避免"魔法加速"）
        compression = max(float(time_compression), 1.0)
        self.tau_oil_s = float(physics.get("tau_oil_real_s", 9000.0)) / compression
        self.tau_winding_s = float(physics.get("tau_winding_real_s", 600.0)) / compression

    # ---- 解析稳态 ----
    def steady_state(self, load_factor: float, cooling_ratio: float = 1.0) -> Tuple[float, float]:
        """返回 (顶层油温稳态值 ℃, 热点温升稳态值 K)。

        cooling_ratio 为冷却能力可用率：1.0 表示冷却器全部投运，
        0.5 表示冷却能力只剩一半（等价于冷却器全停事故工况）。
        """
        k = max(float(load_factor), 0.0)
        cool = max(float(cooling_ratio), 0.05)  # 防止除零，保留 5% 自然散热
        # 冷却能力下降 -> 额定温升等效抬高，油温进入过热区间
        top_oil_rise_rated_eff = self.top_oil_rise_rated_k / cool
        oil_rise = top_oil_rise_rated_eff * ((1.0 + self.loss_ratio_r * k * k) / (1.0 + self.loss_ratio_r)) ** self.oil_exponent_x
        hot_spot_grad = self.hot_spot_gradient_rated_k * (k ** self.winding_exponent_y)
        return self.ambient_temp_c + oil_rise, hot_spot_grad

    # ---- 暂态步进 ----
    def step(
        self,
        state: ThermalState,
        load_factor: float,
        cooling_ratio: float,
        dt_seconds: float,
    ) -> ThermalState:
        """一阶惯性步进。

        采用指数积分的解析解而非显式欧拉，任意步长下都稳定、无过冲，
        不允许出现数值振荡导致的"温度乱跳"。
        """
        oil_ss, grad_ss = self.steady_state(load_factor, cooling_ratio)
        alpha_oil = 1.0 - math.exp(-dt_seconds / self.tau_oil_s)
        alpha_grad = 1.0 - math.exp(-dt_seconds / self.tau_winding_s)
        return ThermalState(
            oil_temp=state.oil_temp + (oil_ss - state.oil_temp) * alpha_oil,
            hot_spot_grad=state.hot_spot_grad + (grad_ss - state.hot_spot_grad) * alpha_grad,
        )

    def initial_state(self, oil_temp: float, hot_spot_temp: float) -> ThermalState:
        return ThermalState(oil_temp=float(oil_temp), hot_spot_grad=float(hot_spot_temp) - float(oil_temp))

    def describe(self) -> Dict[str, Any]:
        return {
            "model": "iec60076-7-first-order",
            "loss_ratio_r": self.loss_ratio_r,
            "oil_exponent_x": self.oil_exponent_x,
            "winding_exponent_y": self.winding_exponent_y,
            "top_oil_rise_rated_k": self.top_oil_rise_rated_k,
            "hot_spot_gradient_rated_k": self.hot_spot_gradient_rated_k,
            "tau_oil_s": round(self.tau_oil_s, 3),
            "tau_winding_s": round(self.tau_winding_s, 3),
            "ambient_temp_c": self.ambient_temp_c,
        }
