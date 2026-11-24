"""Distribution artifacts must describe the same public contract as the code."""

import ast
import json
import re
import tomllib
from pathlib import Path

from PIL import Image

from custom_components.daikin_home_hub.const import MIN_HA_VERSION
from custom_components.daikin_home_hub.models import MODELS
from custom_components.daikin_home_hub.registers import (
    AIR_TO_AIR_REGISTERS,
    ALTHERMA_REGISTERS,
)

from .reference import AIR_TO_AIR, HOLDING, INPUT

ROOT = Path(__file__).parents[1]
COMPONENT = ROOT / "custom_components/daikin_home_hub"


def test_distribution_metadata_and_translations():
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert manifest["version"] == project["version"] == "0.1.0"
    assert manifest["requirements"] == []
    assert manifest["dependencies"] == ["modbus"]
    assert hacs["homeassistant"] == MIN_HA_VERSION
    strings = json.loads((COMPONENT / "strings.json").read_text())
    assert (
        manifest["name"] == hacs["name"] == strings["title"] == "Daikin HomeHub Modbus"
    )
    assert strings == json.loads((COMPONENT / "translations/en.json").read_text())
    assert set(strings["selector"]["model"]["options"]) == set(MODELS)
    for register in [*ALTHERMA_REGISTERS.values(), *AIR_TO_AIR_REGISTERS.values()]:
        entry = strings["entity"][register.platform][register.key]
        assert entry["name"]
        if register.options:
            assert set(entry["state"]) == set(register.options.values())


def test_documented_inventory_contains_every_published_offset_and_key():
    doc = (ROOT / "docs/register-map.md").read_text()
    rows = re.findall(r"^\| (\d+) \| (\d+) \| [^\n]*?<br>`([^`]+)`", doc, re.MULTILINE)
    assert len(rows) == 61
    actual = {(int(offset), int(address), key) for offset, address, key in rows}
    # The independent specification fixture is the reference for docs too.
    for table in (HOLDING, INPUT, AIR_TO_AIR):
        for offset, (key, _, _) in table.items():
            assert (offset, offset - 1, key) in actual


def test_icon_keys_and_states_match_the_entity_contract():
    icons = json.loads((COMPONENT / "icons.json").read_text())["entity"]
    entities = json.loads((COMPONENT / "strings.json").read_text())["entity"]
    for platform, entries in icons.items():
        for key, entry in entries.items():
            entity = entities[platform][key]
            states = entry.get("state", {})
            allowed_states = (
                {"on", "off"}
                if platform in ("binary_sensor", "switch")
                else set(entity.get("state", {}))
            )
            assert set(states) <= allowed_states
            assert entry["default"].startswith("mdi:")
            assert all(icon.startswith("mdi:") for icon in states.values())
            assert entry["default"] not in states.values()


def test_protocol_modules_have_no_home_assistant_imports():
    for filename in ("protocol.py", "registers.py", "models.py", "installation.py"):
        tree = ast.parse((COMPONENT / filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    not name.name.startswith("homeassistant") for name in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("homeassistant")


def test_brand_assets_are_valid_pngs_at_standard_resolutions():
    for filename in ("icon.png", "icon@2x.png", "logo.png", "logo@2x.png"):
        with Image.open(COMPONENT / "brand" / filename) as image:
            assert image.format == "PNG"
            size = 512 if "@2x" in filename else 256
            assert image.height == size
            if filename.startswith("icon"):
                assert image.width == size
            else:
                # Official wordmarks are wide; preserve the upstream images.
                assert image.width > size
            image.verify()
