"""R0 — plugin loader + dispatcher tests.

The critical property: a broken plugin (bad JSON, import error, raising
hook) must never crash Ralph. These tests verify failure isolation.
"""
from __future__ import annotations

import json
import textwrap

import pytest

from ralph import plugins, telemetry


def _write_plugin(root, name, manifest, module_src):
    d = root / name
    d.mkdir()
    (d / "plugin.json").write_text(json.dumps(manifest))
    (d / "plugin.py").write_text(textwrap.dedent(module_src))


GOOD_MODULE = """
from ralph.plugins import RalphPlugin
class P(RalphPlugin):
    name = "good"
    version = "0.1"
    def __init__(self): self.calls = []
    def on_start(self, ctx): self.calls.append(("on_start", ctx))
    def on_iteration_end(self, ctx, i, out): self.calls.append(("on_iter_end", i))
plugin = P()
"""

RAISING_MODULE = """
from ralph.plugins import RalphPlugin
class P(RalphPlugin):
    name = "raising"
    def on_start(self, ctx): raise RuntimeError("boom from raising plugin")
plugin = P()
"""

BROKEN_IMPORT_MODULE = """
import some_module_that_does_not_exist  # noqa
from ralph.plugins import RalphPlugin
plugin = RalphPlugin()
"""

NO_PLUGIN_INSTANCE_MODULE = """
# Forgot to assign `plugin = ...`
from ralph.plugins import RalphPlugin
class P(RalphPlugin): pass
"""


@pytest.fixture
def plugins_dir(tmp_path, monkeypatch):
    d = tmp_path / "plugins"
    d.mkdir()
    monkeypatch.setenv("RALPH_PLUGINS_DIR", str(d))
    # Send telemetry somewhere harmless
    monkeypatch.setenv("RALPH_TELEMETRY_PATH", str(tmp_path / "tel.jsonl"))
    return d


def test_discover_loads_good_plugin(plugins_dir):
    _write_plugin(plugins_dir, "good", {"name": "good", "version": "0.1"}, GOOD_MODULE)
    loaded = plugins.discover()
    assert len(loaded) == 1
    assert loaded[0].name == "good"
    assert loaded[0].version == "0.1"


def test_discover_skips_missing_files(plugins_dir):
    # Directory exists but no manifest/module
    (plugins_dir / "empty").mkdir()
    loaded = plugins.discover()
    assert loaded == []


def test_discover_skips_bad_json(plugins_dir):
    d = plugins_dir / "bad"
    d.mkdir()
    (d / "plugin.json").write_text("{this is not json")
    (d / "plugin.py").write_text("from ralph.plugins import RalphPlugin\nplugin = RalphPlugin()")
    loaded = plugins.discover()
    assert loaded == []


def test_discover_skips_import_error(plugins_dir):
    _write_plugin(plugins_dir, "bad_import", {"name": "bad"}, BROKEN_IMPORT_MODULE)
    loaded = plugins.discover()
    assert loaded == []


def test_discover_skips_no_plugin_instance(plugins_dir):
    _write_plugin(plugins_dir, "no_inst", {"name": "no_inst"}, NO_PLUGIN_INSTANCE_MODULE)
    loaded = plugins.discover()
    assert loaded == []


def test_discover_continues_after_one_broken(plugins_dir):
    _write_plugin(plugins_dir, "a_good", {"name": "a"}, GOOD_MODULE)
    _write_plugin(plugins_dir, "b_broken", {"name": "b"}, BROKEN_IMPORT_MODULE)
    _write_plugin(plugins_dir, "c_good", {"name": "c"}, GOOD_MODULE)
    loaded = plugins.discover()
    names = sorted(lp.manifest["name"] for lp in loaded)
    assert names == ["a", "c"]   # b skipped, others loaded


def test_dispatch_calls_hooks(plugins_dir):
    _write_plugin(plugins_dir, "good", {"name": "good"}, GOOD_MODULE)
    loaded = plugins.discover()
    plugins.dispatch(loaded, "on_start", {"k": 1})
    plugins.dispatch(loaded, "on_iteration_end", {}, 7, "result")
    calls = loaded[0].instance.calls
    assert ("on_start", {"k": 1}) in calls
    assert ("on_iter_end", 7) in calls


def test_dispatch_isolates_failures(plugins_dir):
    _write_plugin(plugins_dir, "raising", {"name": "raising"}, RAISING_MODULE)
    _write_plugin(plugins_dir, "good", {"name": "good"}, GOOD_MODULE)
    loaded = plugins.discover()
    # Should NOT raise — bad hook is caught + logged + telemetry-emitted
    plugins.dispatch(loaded, "on_start", {})

    # Verify telemetry recorded the failure
    events = telemetry.read_tail(50)
    failed = [e for e in events if e["event"] == "plugin.on_start_failed"]
    assert any(e.get("plugin") == "raising" for e in failed)


def test_dispatch_skips_missing_hook(plugins_dir):
    _write_plugin(plugins_dir, "good", {"name": "good"}, GOOD_MODULE)
    loaded = plugins.discover()
    # provide_tools is not overridden in GOOD_MODULE; should return [] (base no-op)
    results = plugins.dispatch(loaded, "provide_tools")
    assert results == [[]]      # base class returns []
