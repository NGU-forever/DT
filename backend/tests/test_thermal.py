"""变压器热路模型测试（IEC 60076-7 一阶形式）。"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain.point_model import load_point_model  # noqa: E402
from app.simulation.thermal import ThermalState, TransformerThermalModel  # noqa: E402


class TestThermalSteadyState(unittest.TestCase):
    def setUp(self):
        self.pm = load_point_model()
        self.ambient = float(self.pm.station["ambient_temp_c"])
        self.model = TransformerThermalModel(
            self.pm.device("trans-1").physics, self.ambient, self.pm.time_compression
        )

    def test_steady_state_matches_iec_formula(self):
        k = 0.761
        r, x = self.model.loss_ratio_r, self.model.oil_exponent_x
        expected_oil = self.ambient + self.model.top_oil_rise_rated_k * (
            (1 + r * k * k) / (1 + r)
        ) ** x
        oil, grad = self.model.steady_state(k, 1.0)
        self.assertAlmostEqual(oil, expected_oil, places=6)
        self.assertAlmostEqual(grad, self.model.hot_spot_gradient_rated_k * k ** self.model.winding_exponent_y, places=6)

    def test_steady_state_reproduces_configured_initial_operating_point(self):
        # 76.1% 负载下的稳态值应落在物模型配置的初始工况附近
        oil, grad = self.model.steady_state(0.761, 1.0)
        self.assertAlmostEqual(oil, 58.2, delta=1.0)
        self.assertAlmostEqual(oil + grad, 68.5, delta=1.0)

    def test_hot_spot_always_above_top_oil(self):
        for k in (0.2, 0.5, 0.761, 1.0, 1.5):
            oil, grad = self.model.steady_state(k, 1.0)
            self.assertGreater(grad, 0.0, f"负载率 {k} 时热点温升应为正")
            self.assertGreater(oil + grad, oil)

    def test_higher_load_raises_temperature_monotonically(self):
        oils = [self.model.steady_state(k / 10, 1.0)[0] for k in range(1, 16)]
        self.assertEqual(oils, sorted(oils), "油温稳态值应随负载率单调上升")

    def test_cooling_loss_raises_oil_temperature(self):
        normal, _ = self.model.steady_state(0.761, 1.0)
        failed, _ = self.model.steady_state(0.761, 0.5)
        self.assertGreater(failed, normal)
        # 冷却器全停（冷却能力 50%）时稳态油温应进入 85℃ 以上的危险区间
        self.assertGreater(failed, 85.0)
        self.assertGreater(failed, 91.0)
        self.assertLess(failed, 92.0)


class TestThermalTransient(unittest.TestCase):
    def setUp(self):
        self.pm = load_point_model()
        self.model = TransformerThermalModel(
            self.pm.device("trans-1").physics, float(self.pm.station["ambient_temp_c"]), self.pm.time_compression
        )

    def test_time_constants_are_compressed(self):
        self.assertAlmostEqual(self.model.tau_oil_s, 9000.0 / 300.0, places=3)
        self.assertAlmostEqual(self.model.tau_winding_s, 600.0 / 300.0, places=3)

    def test_step_matches_analytic_first_order_solution(self):
        # 一阶惯性用指数积分解，单步结果应与解析解完全一致
        state = ThermalState(oil_temp=30.0, hot_spot_grad=5.0)
        dt = 7.5
        oil_ss, grad_ss = self.model.steady_state(0.761, 1.0)
        new = self.model.step(state, 0.761, 1.0, dt)
        expected_oil = oil_ss + (30.0 - oil_ss) * math.exp(-dt / self.model.tau_oil_s)
        expected_grad = grad_ss + (5.0 - grad_ss) * math.exp(-dt / self.model.tau_winding_s)
        self.assertAlmostEqual(new.oil_temp, expected_oil, places=9)
        self.assertAlmostEqual(new.hot_spot_grad, expected_grad, places=9)

    def test_step_never_overshoots_steady_state_even_with_huge_dt(self):
        # 显式欧拉在大步长下会振荡甚至发散；指数积分解必须始终夹在初值与稳态值之间
        state = ThermalState(oil_temp=24.8, hot_spot_grad=0.0)
        oil_ss, grad_ss = self.model.steady_state(1.5, 1.0)
        new = self.model.step(state, 1.5, 1.0, dt_seconds=self.model.tau_oil_s * 50)
        self.assertLessEqual(new.oil_temp, oil_ss + 1e-9)
        self.assertGreaterEqual(new.oil_temp, 24.8)
        self.assertLessEqual(new.hot_spot_grad, grad_ss + 1e-9)

    def test_temperature_converges_to_steady_state(self):
        state = ThermalState(oil_temp=24.8, hot_spot_grad=0.0)
        oil_ss, _ = self.model.steady_state(0.761, 1.0)
        for _ in range(300):
            state = self.model.step(state, 0.761, 1.0, 1.5)
        self.assertAlmostEqual(state.oil_temp, oil_ss, places=2)

    def test_initial_state_splits_hot_spot_gradient(self):
        state = self.model.initial_state(oil_temp=58.2, hot_spot_temp=68.5)
        self.assertAlmostEqual(state.oil_temp, 58.2, places=6)
        self.assertAlmostEqual(state.hot_spot_grad, 10.3, places=6)
        self.assertAlmostEqual(state.hot_spot_temp, 68.5, places=6)


if __name__ == "__main__":
    unittest.main()
