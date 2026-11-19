"""Exercise the NXG adapter with the actual pinned API dependency."""
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "nxg_under_test", ROOT / "custom_components/froeling_connect/nxg_readonly.py"
)
nxg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(nxg)


def fixture(name):
    return json.loads((ROOT / "tests/fixtures" / f"{name}.json").read_text())


class FakeSession:
    user_id = 9001

    def __init__(self):
        self.calls = []
        self.detail = fixture("boiler")

    async def request(self, method, url):
        self.calls.append((method, url))
        if url.endswith("component-list"):
            return [
                {"componentId": 101, "type": "Boiler", "valueItems": {
                    "componentName": {"value": "", "defaultValue": "Test boiler"}}},
                {"componentId": 104, "type": "MaterialFeed"},
            ]
        return self.detail


class ParserTests(unittest.TestCase):
    def parse(self, name):
        return nxg.parse_parameters(fixture(name), None, 9002)

    def test_nested_values_and_deduplication(self):
        params = self.parse("boiler")
        self.assertEqual(params["temp"].value, 75.5)
        self.assertEqual(len([p for p in params.values() if p.name == "tempBoiler"]), 1)
        self.assertNotIn("schedule", params)

    def test_enums_and_empty_labels(self):
        p = self.parse("boiler")["state"]
        self.assertEqual(p.string_list_key_values["65"], "Scheitholzbetrieb")
        self.assertEqual(p.string_list_key_values["0"], "Wert 0")

    def test_binary_values_match_existing_binary_sensor_platform(self):
        params = self.parse("boiler")
        self.assertEqual(params["fire"].value, "1")
        self.assertEqual(params["pellet"].value, "0")
        self.assertEqual((params["fire"].min_val, params["fire"].max_val, params["fire"].unit), ("0", "1", ""))

    def test_invalid_numeric_value_is_unavailable(self):
        self.assertIsNone(self.parse("boiler")["bad"].value)

    def test_all_parameters_are_read_only(self):
        for name in ("boiler", "buffer", "heating_circuit"):
            for p in self.parse(name).values():
                self.assertFalse(p.editable)
                with self.assertRaises(NotImplementedError):
                    asyncio.run(p.set_value(1))

    def test_two_buffer_temperatures_and_loading_direction(self):
        params = self.parse("buffer")
        self.assertEqual(params["buffer1SensorBarSlotA"].value, 70.0)
        self.assertEqual(params["buffer2SensorBarSlotJ"].value, 25.0)
        self.assertEqual(params["soc"].value, 40)
        self.assertEqual(params["loading"].string_list_key_values["3"], "Be - und Entladen")

    def test_heating_values_and_additional_view(self):
        params = self.parse("heating_circuit")
        self.assertEqual(params["room"].value, 21.0)
        self.assertEqual(params["outside"].value, 5.0)
        self.assertEqual(params["pump"].value, "1")
        self.assertIn("info", params)
        self.assertNotIn("time", params)


class RequestTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session = FakeSession()
        self.facility = SimpleNamespace(facility_id=9002, session=self.session)

    async def test_numeric_component_ids_and_get_only(self):
        components = await nxg.get_nxg_components(self.facility)
        self.assertEqual(len(components), 1)
        c = components[0]
        self.assertEqual(c.component_id, "101")
        self.assertEqual(c.display_name, "Test boiler")
        await c.update()
        self.session.detail["topView"][0]["valueItems"][1]["value"] = 76.0
        self.session.detail["listView"][0]["valueItems"][0]["value"] = 76.0
        await c.update()
        self.assertEqual(c.parameters["temp"].value, 76.0)
        self.assertEqual(self.session.calls[0], ("get", "https://connect-api.froeling.com/fcs/v1.0/resources/user/9001/nxg/facility/9002/web/component-list"))
        self.assertTrue(self.session.calls[1][1].endswith("/component/101"))
        self.assertTrue(all(method == "get" for method, _ in self.session.calls))

    async def test_mismatched_detail_is_rejected(self):
        c = (await nxg.get_nxg_components(self.facility))[0]
        self.session.detail["id"] = 999
        with self.assertRaises(ValueError):
            await c.update()

    async def test_disappearing_parameter_rejects_update(self):
        c = (await nxg.get_nxg_components(self.facility))[0]
        await c.update()
        self.session.detail["topView"][0]["valueItems"] = []
        with self.assertRaises(ValueError):
            await c.update()


if __name__ == "__main__":
    unittest.main()
