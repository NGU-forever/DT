"""物模型（Thing Model）配置层测试。

运行方式（无需安装 pytest，仅用标准库 unittest）：
    backend/venv/bin/python -m unittest discover -s backend/tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.domain.point_model import Measurement, load_point_model, reload_point_model  # noqa: E402


class TestPointModelLoading(unittest.TestCase):
    def setUp(self):
        self.pm = reload_point_model()

    def test_devices_and_types_loaded_from_config(self):
        self.assertEqual(len(self.pm.devices), 5)
        self.assertEqual(
            sorted(self.pm.devices.keys()),
            ["gis-101", "gis-201", "gis-202", "trans-1", "trans-2"],
        )
        self.assertEqual(set(self.pm.device_types.keys()), {"transformer", "breaker"})

    def test_measurement_templates_are_type_scoped(self):
        transformer_keys = set(self.pm.measurements_for("trans-1").keys())
        breaker_keys = set(self.pm.measurements_for("gis-201").keys())

        # 变压器有油温/绕组热点，断路器有 SF6 气压 —— 两类设备的测点集合必须不同
        self.assertIn("oil_temp", transformer_keys)
        self.assertIn("winding_temp", transformer_keys)
        self.assertNotIn("sf6_pressure", transformer_keys)
        self.assertIn("sf6_pressure", breaker_keys)
        self.assertNotIn("oil_temp", breaker_keys)

    def test_device_level_physics_overrides_type_default(self):
        # trans-2 在配置里覆盖了类型模板的额定温升，两台主变不应完全相同
        trans1 = self.pm.device("trans-1")
        trans2 = self.pm.device("trans-2")
        self.assertEqual(trans1.physics["top_oil_rise_rated_k"], 50.0)
        self.assertEqual(trans2.physics["top_oil_rise_rated_k"], 46.0)
        # 未覆盖的项仍继承类型模板
        self.assertEqual(trans1.physics["loss_ratio_r"], trans2.physics["loss_ratio_r"])

    def test_grid_source_declared_in_config(self):
        self.assertEqual(self.pm.grid_sources(), ["gis-201"])

    def test_simulation_parameters(self):
        self.assertEqual(self.pm.step_seconds, 1.5)
        self.assertEqual(self.pm.db_persist_every_steps, 10)
        # 时间压缩：真实 9000s 的油温时间常数应被压缩到 Demo 可观察尺度
        self.assertAlmostEqual(self.pm.real_seconds_to_model(9000.0), 30.0, places=3)


class TestAlarmEvaluation(unittest.TestCase):
    def test_high_direction_thresholds(self):
        m = Measurement("oil_temp", "顶层油温", "℃", 1, {"warning": 75, "danger": 85})
        self.assertEqual(m.evaluate(58.2), "normal")
        self.assertEqual(m.evaluate(75.0), "warning")
        self.assertEqual(m.evaluate(80.0), "warning")
        self.assertEqual(m.evaluate(85.0), "danger")
        self.assertEqual(m.evaluate(91.5), "danger")

    def test_low_direction_thresholds(self):
        # SF6 气压是"越低越危险"
        m = Measurement("sf6_pressure", "SF6 气压", "MPa", 3, {"warning": 0.50, "danger": 0.45, "direction": "low"})
        self.assertEqual(m.evaluate(0.58), "normal")
        self.assertEqual(m.evaluate(0.50), "warning")
        self.assertEqual(m.evaluate(0.47), "warning")
        self.assertEqual(m.evaluate(0.45), "danger")
        self.assertEqual(m.evaluate(0.26), "danger")

    def test_missing_and_boolean_values_are_ignored(self):
        m = Measurement("oil_temp", "顶层油温", "℃", 1, {"danger": 85})
        self.assertEqual(m.evaluate(None), "normal")
        self.assertEqual(m.evaluate(True), "normal")

    def test_device_report_picks_worst_level_and_lists_items(self):
        pm = load_point_model()
        report = pm.evaluate_device(
            "trans-1",
            {"oil_temp": 88.0, "winding_temp": 70.0, "load_rate": 80.0, "pd_level": 90.0},
        )
        self.assertEqual(report["level"], "danger")
        offending = {item["key"] for item in report["items"]}
        self.assertIn("oil_temp", offending)   # 超过 85 danger
        self.assertIn("pd_level", offending)   # 超过 80 warning
        self.assertNotIn("winding_temp", offending)


class TestOPCUALayout(unittest.TestCase):
    def setUp(self):
        self.pm = reload_point_model()
        self.layout = self.pm.opcua_layout()

    def test_layout_generated_from_config(self):
        # 变压器类 4 个节点 × 2 台 + 断路器类 3 个节点 × 3 台 = 17
        self.assertEqual(len(self.layout), 17)
        for item in self.layout:
            for key in ("device_id", "folder", "node", "variant", "writable"):
                self.assertIn(key, item)

    def test_breaker_position_is_writable(self):
        writable = {(i["device_id"], i["node"]) for i in self.layout if i["writable"]}
        self.assertEqual(
            writable,
            {("gis-201", "BreakerPosition"), ("gis-202", "BreakerPosition"), ("gis-101", "BreakerPosition")},
        )

    def test_initial_values_are_typed_correctly(self):
        by_key = {(i["device_id"], i["measurement_key"]): i for i in self.layout}
        self.assertIsInstance(by_key[("gis-201", "breaker_state")]["initial"], bool)
        self.assertIsInstance(by_key[("trans-1", "oil_temp")]["initial"], float)

    def test_opcua_folder_naming_convention(self):
        folders = {i["device_id"]: i["folder"] for i in self.layout}
        self.assertEqual(folders["trans-1"], "Transformer_1")
        self.assertEqual(folders["gis-201"], "GIS_Breaker_201")

    def test_thing_model_is_self_describing(self):
        doc = self.pm.to_dict()
        self.assertIn("station", doc)
        self.assertIn("device_types", doc)
        self.assertEqual(len(doc["devices"]), 5)
        # 每台设备都要带上自己的测点清单，前端据此即可动态渲染
        for device in doc["devices"]:
            self.assertTrue(device["measurements"])


if __name__ == "__main__":
    unittest.main()
