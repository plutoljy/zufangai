from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import main  # noqa: E402


def load_preferences_module():
    module_path = SRC_DIR / "api" / "preferences.py"
    spec = importlib.util.spec_from_file_location("api.preferences", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preferences_router_module_imports_cleanly():
    module = load_preferences_module()

    assert module.router.prefix == "/api/preferences"


def test_preferences_router_delegates_to_main_handlers():
    module = load_preferences_module()
    route_map = {
        (route.path, next(iter(route.methods - {"HEAD", "OPTIONS"}))): route.endpoint
        for route in module.router.routes
        if getattr(route, "path", None)
    }

    assert route_map[("/api/preferences/{user_id}", "GET")] is main.get_user_preferences
    assert route_map[("/api/preferences/{user_id}", "POST")] is main.create_or_update_preferences
    assert route_map[("/api/preferences/{user_id}", "DELETE")] is main.delete_user_preferences
    assert route_map[("/api/preferences/{user_id}/reset", "POST")] is main.reset_user_preferences
