"""R0 — Plugin architecture.

Plugins are independent Python modules living at::

    ~/.ralph/plugins/<name>/plugin.py          ← required (defines `plugin` instance)
    ~/.ralph/plugins/<name>/plugin.json        ← required (metadata + activation)

Plugin lifecycle: loader scans the plugins directory at runtime startup,
imports each ``plugin.py`` via ``importlib``, instantiates the ``plugin``
object, then dispatches lifecycle hooks during the Ralph run.

Failure isolation: a plugin that raises during a hook is logged and
skipped; the rest of the loop continues. A plugin that fails to import is
logged and excluded — Ralph still starts.

API (subclass ``RalphPlugin`` to implement)::

    on_start(run_ctx)                  # before iteration 0
    on_iteration_start(run_ctx, i)     # before each iteration
    on_iteration_end(run_ctx, i, out)  # after each iteration
    on_exit_signal(run_ctx, result)    # after the loop terminates
    provide_tools()  -> list[dict]     # tool defs to inject into claude args
    provide_skills() -> list[dict]     # skill descriptors for system prompt

Telemetry: every hook dispatch emits a ``plugin.<hook>`` event so R9
dashboard can show per-plugin activity / failures.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ralph import telemetry

log = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".ralph" / "plugins"


def _plugins_dir() -> Path:
    override = os.environ.get("RALPH_PLUGINS_DIR")
    return Path(override) if override else _DEFAULT_DIR


# ─── Public API ────────────────────────────────────────────────────────


class RalphPlugin:
    """Base class. All hooks are no-ops by default — subclass and override
    only the ones you need."""

    name: str = "unnamed"
    version: str = "0.0.0"

    def on_start(self, run_ctx: dict[str, Any]) -> None:
        pass

    def on_iteration_start(self, run_ctx: dict[str, Any], iteration: int) -> None:
        pass

    def on_iteration_end(self, run_ctx: dict[str, Any], iteration: int, outcome: Any) -> None:
        pass

    def on_exit_signal(self, run_ctx: dict[str, Any], result: Any) -> None:
        pass

    def provide_tools(self) -> list[dict[str, Any]]:
        return []

    def provide_skills(self) -> list[dict[str, Any]]:
        return []


@dataclass
class LoadedPlugin:
    name: str
    version: str
    path: Path
    instance: RalphPlugin
    manifest: dict[str, Any] = field(default_factory=dict)


# ─── Loader ────────────────────────────────────────────────────────────


def discover() -> list[LoadedPlugin]:
    """Scan the plugins directory; return successfully loaded plugins.

    Errors are logged + telemetry-emitted; broken plugins are silently
    skipped (intentionally — Ralph must boot even when some plugin breaks).
    """
    root = _plugins_dir()
    if not root.exists():
        return []

    loaded: list[LoadedPlugin] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        manifest_path = entry / "plugin.json"
        module_path = entry / "plugin.py"
        if not manifest_path.exists() or not module_path.exists():
            log.debug("skipping %s — missing plugin.json or plugin.py", entry)
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.warning("plugin %s: invalid plugin.json — %s", entry.name, e)
            telemetry.emit("plugin.load_failed", plugin=entry.name, reason="invalid_manifest", error=str(e))
            continue

        try:
            spec = importlib.util.spec_from_file_location(f"ralph_plugins.{entry.name}", module_path)
            if spec is None or spec.loader is None:
                raise ImportError("spec_from_file_location returned None")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as e:
            log.warning("plugin %s: import failed — %s", entry.name, e)
            telemetry.emit("plugin.load_failed", plugin=entry.name, reason="import_error", error=str(e))
            continue

        instance = getattr(module, "plugin", None)
        if not isinstance(instance, RalphPlugin):
            log.warning(
                "plugin %s: module has no `plugin` instance of RalphPlugin (got %r)",
                entry.name, type(instance),
            )
            telemetry.emit("plugin.load_failed", plugin=entry.name, reason="no_plugin_instance")
            continue

        loaded.append(LoadedPlugin(
            name=manifest.get("name", entry.name),
            version=manifest.get("version", "0.0.0"),
            path=entry,
            instance=instance,
            manifest=manifest,
        ))
        telemetry.emit("plugin.loaded", plugin=entry.name, version=manifest.get("version", "?"))

    log.info("loaded %d plugins from %s", len(loaded), root)
    return loaded


# ─── Dispatcher ────────────────────────────────────────────────────────


def dispatch(plugins: list[LoadedPlugin], hook: str, *args, **kwargs) -> list[Any]:
    """Call ``hook`` on every plugin. Returns list of results (None for
    plugins that don't implement the hook or that raised).

    Errors are caught + telemetry-emitted; one plugin's failure never
    cancels the rest.
    """
    results = []
    for lp in plugins:
        fn: Callable | None = getattr(lp.instance, hook, None)
        if fn is None:
            results.append(None)
            continue
        try:
            results.append(fn(*args, **kwargs))
            telemetry.emit(f"plugin.{hook}", plugin=lp.name)
        except Exception as e:
            log.warning("plugin %s hook %s failed: %s", lp.name, hook, e)
            telemetry.emit(f"plugin.{hook}_failed", plugin=lp.name, error=str(e))
            results.append(None)
    return results
