"""站内简化潮流模型测试：验证"电流由功率导出、失电即零流、负荷可转移"三条硬约束。"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain.point_model import load_point_model  # noqa: E402
from app.simulation.powerflow import StationPowerFlow  # noqa: E402

SQRT3 = math.sqrt(3.0)


class PowerFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.pm = load_point_model()
        self.demand = float(self.pm.station["demand"]["base_mva"])
        self.mv_share = float(self.pm.station["demand"]["mv_share"])
        self.u_hv = float(self.pm.station["voltage_hv_kv"])
        self.u_mv = float(self.pm.station["voltage_mv_kv"])

    def solve(self, **overrides):
        state = {d.id: bool(d.initial_breaker_state()) for d in self.pm.switches()}
        state.update(overrides)
        return StationPowerFlow(self.pm, state).solve(self.demand)


class TestPowerConservation(PowerFlowTestCase):
    def test_transformer_loads_sum_to_served_power(self):
        flow = self.solve()
        self.assertAlmostEqual(sum(flow.transformer_mva.values()), flow.served_mva, places=3)

    def test_total_power_is_derived_from_apparent_power(self):
        flow = self.solve()
        pf = float(self.pm.station["power_factor"])
        self.assertAlmostEqual(flow.total_power_mw, flow.served_mva * pf, places=2)

    def test_initial_operating_point(self):
        flow = self.solve()
        self.assertFalse(flow.de_energized)
        self.assertEqual(flow.in_service_transformers, ["trans-1", "trans-2"])
        self.assertAlmostEqual(flow.station_load_rate, 76.1, delta=0.5)
        # 两台 240MVA 主变各承担一半
        for mva in flow.transformer_mva.values():
            self.assertAlmostEqual(mva, self.demand / 2, places=2)


class TestCurrentDerivedFromPower(PowerFlowTestCase):
    def test_branch_currents_follow_ohms_law(self):
        flow = self.solve()
        for device_id in ("trans-1", "trans-2"):
            expected = flow.transformer_mva[device_id] / (SQRT3 * self.u_hv) * 1000.0
            self.assertAlmostEqual(flow.current_of(device_id), expected, delta=0.1)

    def test_incoming_current_carries_whole_station(self):
        flow = self.solve()
        expected = flow.served_mva / (SQRT3 * self.u_hv) * 1000.0
        self.assertAlmostEqual(flow.current_of("gis-201"), expected, delta=0.1)
        # 单电源终端站：进线电流 = 两台主变电流之和
        self.assertAlmostEqual(
            flow.current_of("gis-201"),
            flow.current_of("trans-1") + flow.current_of("trans-2"),
            delta=0.2,
        )

    def test_outgoing_current_uses_medium_voltage_level(self):
        flow = self.solve()
        expected = flow.served_mva * self.mv_share / (SQRT3 * self.u_mv) * 1000.0
        self.assertAlmostEqual(flow.current_of("gis-101"), expected, delta=0.1)

    def test_bus_tie_carries_only_far_side_load(self):
        flow = self.solve()
        # 电源在 220kV-I，母联只输送 II 段母线上主变所需的功率
        self.assertAlmostEqual(flow.current_of("gis-202"), flow.current_of("trans-2"), delta=0.2)


class TestTopologyChanges(PowerFlowTestCase):
    def test_opening_bus_tie_transfers_load_and_overloads_remaining_transformer(self):
        flow = self.solve(**{"gis-202": False})
        self.assertFalse(flow.de_energized)
        self.assertEqual(flow.in_service_transformers, ["trans-1"])
        self.assertEqual(flow.current_of("trans-2"), 0.0)
        self.assertEqual(flow.current_of("gis-202"), 0.0)
        # 单台主变承担全站负荷 -> 负载率超过 140%
        self.assertGreater(flow.station_load_rate, 140.0)
        self.assertAlmostEqual(sum(flow.transformer_mva.values()), flow.served_mva, places=3)

    def test_opening_incoming_line_de_energizes_station_and_zeroes_all_currents(self):
        flow = self.solve(**{"gis-201": False})
        self.assertTrue(flow.de_energized)
        self.assertEqual(flow.served_mva, 0.0)
        self.assertEqual(flow.total_power_mw, 0.0)
        for spec in self.pm.switches():
            self.assertEqual(flow.current_of(spec.id), 0.0, f"{spec.id} 失电后电流应为 0")
        for mva in flow.transformer_mva.values():
            self.assertEqual(mva, 0.0)

    def test_opening_outgoing_feeder_sheds_only_its_share(self):
        flow = self.solve(**{"gis-101": False})
        self.assertFalse(flow.de_energized)
        self.assertAlmostEqual(flow.served_mva, self.demand * (1 - self.mv_share), places=2)
        self.assertAlmostEqual(flow.shed_mva, self.demand * self.mv_share, places=2)
        self.assertEqual(flow.current_of("gis-101"), 0.0)
        # 主变负荷随之下降
        self.assertLess(flow.station_load_rate, 76.1)

    def test_outgoing_overload_multiplier_raises_current_and_total_load(self):
        normal = self.solve()
        surge = StationPowerFlow(
            self.pm, {d.id: bool(d.initial_breaker_state()) for d in self.pm.switches()}
        ).solve(self.demand, mv_demand_multiplier=2.2)
        self.assertGreater(surge.current_of("gis-101"), normal.current_of("gis-101"))
        self.assertGreater(surge.served_mva, normal.served_mva)
        # 出线过载会把整站负荷一起抬上去（这才是真实的物理因果）
        self.assertGreater(surge.station_load_rate, 100.0)

    def test_energized_bus_set_reflects_switch_positions(self):
        self.assertEqual(self.solve().energized_buses, ["110kV", "220kV-I", "220kV-II"])
        self.assertNotIn("220kV-II", self.solve(**{"gis-202": False}).energized_buses)
        self.assertEqual(self.solve(**{"gis-201": False}).energized_buses, [])


if __name__ == "__main__":
    unittest.main()
