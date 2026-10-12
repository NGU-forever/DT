"""孪生引擎集成测试：验证遥测是"算出来的"而不是"填上去的"。

这些用例就是面试时可以直接展示的"物理一致性证据"：
分闸一定改变电流与温度，失电一定零流，故障一定由模型演化出后果。
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.simulation.engine import (  # noqa: E402
    FAULT_OVERLOAD_TRIP,
    FAULT_SF6_LEAK,
    FAULT_TRANS_OVERHEAT,
    TwinEngine,
)

SQRT3 = math.sqrt(3.0)


def advance(engine, steps=1):
    snapshot = None
    for _ in range(steps):
        snapshot = engine.step()
    return snapshot


def collect_alarms(engine):
    return [ev["alarm"] for ev in engine.drain_events() if ev.get("kind") == "ALARM"]


class TestInitialState(unittest.TestCase):
    def setUp(self):
        self.engine = TwinEngine()
        self.snapshot = self.engine.snapshot()

    def test_power_is_self_consistent(self):
        flow = self.engine.last_flow
        self.assertFalse(flow.de_energized)
        self.assertAlmostEqual(sum(flow.transformer_mva.values()), flow.served_mva, places=3)
        telemetry = self.snapshot["telemetry"]
        self.assertAlmostEqual(telemetry["apparent_power"], flow.served_mva, places=1)
        self.assertAlmostEqual(
            telemetry["current_a"], flow.served_mva / (SQRT3 * telemetry["voltage_a"]) * 1000.0, delta=1.0
        )

    def test_every_device_has_measurements_and_health(self):
        self.assertEqual(len(self.snapshot["devices"]), 5)
        for device in self.snapshot["devices"].values():
            self.assertIsInstance(device["health_score"], int)
            self.assertIn(device["status"], ("normal", "warning", "danger"))
            self.assertIsNotNone(device["current"])

    def test_initial_conditions_are_stable(self):
        # 配置的初始工况本身就在稳态，不应出现"开机即越限"
        self.assertTrue(self.snapshot["model"]["converged"])
        self.assertEqual(self.snapshot["model"]["active_faults"], [])

    def test_health_score_is_derived_not_hardcoded(self):
        # 健康分由模型量（局放/振动/磨损/动作次数）算出，两台同型号主变分数应不同
        devices = self.snapshot["devices"]
        self.assertNotEqual(devices["trans-1"]["health_score"], devices["trans-2"]["health_score"])
        for device in devices.values():
            self.assertGreaterEqual(device["health_score"], 0)
            self.assertLessEqual(device["health_score"], 100)


class TestBreakerOperations(unittest.TestCase):
    def setUp(self):
        self.engine = TwinEngine()

    def test_opening_bus_tie_transfers_load_and_zeroes_far_branch(self):
        self.engine.set_breaker("gis-202", closed=False)
        snapshot = advance(self.engine)
        self.assertEqual(snapshot["model"]["in_service_transformers"], ["trans-1"])
        self.assertEqual(snapshot["devices"]["trans-2"]["current"], 0.0)
        self.assertEqual(snapshot["devices"]["gis-202"]["current"], 0.0)
        self.assertGreater(snapshot["devices"]["trans-1"]["load_rate"], 140.0)
        # 负荷转移后总供电功率仍维持，这才是"转移"而不是"甩掉"
        self.assertAlmostEqual(snapshot["telemetry"]["apparent_power"], 365.3, delta=5.0)

    def test_opening_incoming_line_blackouts_station(self):
        self.engine.set_breaker("gis-201", closed=False)
        snapshot = advance(self.engine)
        self.assertTrue(snapshot["model"]["de_energized"])
        self.assertEqual(snapshot["telemetry"]["total_power"], 0.0)
        self.assertEqual(snapshot["telemetry"]["current_a"], 0.0)
        for device in snapshot["devices"].values():
            self.assertEqual(device["current"], 0.0)

    def test_operation_is_rejected_on_non_switch_device(self):
        with self.assertRaises(ValueError):
            self.engine.set_breaker("trans-1", closed=False)

    def test_repeated_operation_is_a_noop(self):
        self.engine.set_breaker("gis-202", closed=False)
        result = self.engine.set_breaker("gis-202", closed=False)
        self.assertFalse(result["changed"])

    def test_operation_log_event_emitted(self):
        self.engine.drain_events()
        self.engine.set_breaker("gis-202", closed=False)
        events = self.engine.drain_events()
        self.assertTrue(any(e.get("log_type") == "遥控指令" for e in events))

    def test_contact_wear_accumulates_on_operation(self):
        before = self.engine.values["gis-202"]["contact_wear"]
        self.engine.set_breaker("gis-202", closed=False)
        self.assertGreater(self.engine.values["gis-202"]["contact_wear"], before)


class TestFaultScenarios(unittest.TestCase):
    def test_transformer_overheat_is_evolved_by_thermal_model(self):
        engine = TwinEngine()
        engine.drain_events()
        engine.inject_fault(FAULT_TRANS_OVERHEAT)

        oil_trace = []
        alarms = []
        for _ in range(150):
            snapshot = engine.step()
            oil_trace.append(snapshot["devices"]["trans-1"]["oil_temp"])
            alarms.extend(collect_alarms(engine))

        # 温度应逐步爬升而不是瞬间跳变。
        # 负荷需求本身有 ±2.4MVA 的随机波动，稳态附近允许极小幅回摆，故用容差判定。
        for prev, curr in zip(oil_trace, oil_trace[1:]):
            self.assertGreaterEqual(curr, prev - 0.2, "油温不应出现明显回退")
        self.assertGreater(oil_trace[40], oil_trace[0] + 3.0, "前 60 秒应出现明确温升")
        self.assertLess(oil_trace[0], 62.0, "第一步不应立刻跳到故障温度")
        self.assertGreater(oil_trace[-1], 85.0, "最终应越过油温危险阈值")
        self.assertAlmostEqual(oil_trace[-1], 91.3, delta=2.0)

        levels = [a["level"] for a in alarms]
        self.assertIn("danger", levels)
        self.assertTrue(any("顶层油温" in a["text"] for a in alarms), "应产生油温越限告警")
        # 边沿触发：不应每步刷屏
        self.assertLess(len(alarms), 10, f"告警条数过多，疑似逐帧刷屏: {len(alarms)}")

        # 健康度应随模型量下降
        self.assertLess(engine.snapshot()["devices"]["trans-1"]["health_score"], 95)

    def test_sf6_leak_alarms_and_blocks_closing(self):
        engine = TwinEngine()
        engine.inject_fault(FAULT_SF6_LEAK)
        engine.set_breaker("gis-201", closed=False)  # 先分开，才能验证"重新合闸被闭锁"
        engine.drain_events()

        alarms = []
        for _ in range(25):
            engine.step()
            alarms.extend(collect_alarms(engine))

        pressure = engine.snapshot()["devices"]["gis-201"]["sf6_pressure"]
        self.assertLess(pressure, 0.45)
        self.assertTrue(any(a["level"] == "danger" and "SF6" in a["text"] for a in alarms))

        with self.assertRaises(PermissionError) as ctx:
            engine.set_breaker("gis-201", closed=True)
        self.assertIn("闭锁", str(ctx.exception))

    def test_outgoing_overload_trips_only_the_faulted_feeder(self):
        engine = TwinEngine()
        engine.drain_events()
        engine.inject_fault(FAULT_OVERLOAD_TRIP)

        snapshot = advance(engine, 1)
        self.assertGreater(snapshot["devices"]["gis-101"]["current"], 1000.0)

        logs = []
        for _ in range(10):
            snapshot = engine.step()
            logs.extend(engine.drain_events())

        self.assertFalse(snapshot["devices"]["gis-101"]["breaker_state"], "出线应被保护跳闸")
        self.assertTrue(snapshot["devices"]["gis-201"]["breaker_state"], "进线不应误动")
        self.assertEqual(snapshot["devices"]["gis-101"]["current"], 0.0)
        # 跳闸后负荷被甩掉，主变负载率回落
        self.assertLess(snapshot["devices"]["trans-1"]["load_rate"], 76.1)
        self.assertGreater(snapshot["telemetry"]["shed_mva"], 100.0)
        self.assertTrue(any(ev.get("log_type") == "保护动作" for ev in logs))

    def test_unknown_fault_type_rejected(self):
        with self.assertRaises(ValueError):
            TwinEngine().inject_fault("meltdown")


class TestFaultReset(unittest.TestCase):
    def test_reset_restores_initial_operating_point(self):
        engine = TwinEngine()
        engine.inject_fault(FAULT_TRANS_OVERHEAT)
        engine.set_breaker("gis-202", closed=False)
        advance(engine, 40)
        self.assertTrue(engine.snapshot()["model"]["active_faults"])

        engine.clear_fault()
        snapshot = engine.snapshot()
        self.assertEqual(snapshot["model"]["active_faults"], [])
        self.assertEqual(snapshot["model"]["in_service_transformers"], ["trans-1", "trans-2"])
        self.assertTrue(snapshot["devices"]["gis-202"]["breaker_state"])
        self.assertAlmostEqual(snapshot["devices"]["trans-1"]["oil_temp"], 58.2, delta=0.5)
        self.assertAlmostEqual(snapshot["telemetry"]["apparent_power"], 365.3, delta=1.0)


if __name__ == "__main__":
    unittest.main()
