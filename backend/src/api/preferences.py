"""
Compatibility router for user preference endpoints.

This module intentionally reuses the canonical handlers defined in main.py so
we do not maintain a second copy of the same business logic.
"""

from __future__ import annotations

import os
import sys

from fastapi import APIRouter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (  # noqa: E402
    create_or_update_preferences,
    delete_user_preferences,
    get_user_preferences,
    reset_user_preferences,
)
from models.user_preferences import UserPreferences  # noqa: E402


router = APIRouter(prefix="/api/preferences", tags=["preferences"])

# Compatibility-only router: keep endpoint objects pointing at the canonical
# implementations in main.py so future behavior changes only happen in one place.
router.add_api_route(
    "/{user_id}",
    get_user_preferences,
    methods=["GET"],
    response_model=UserPreferences,
)
router.add_api_route(
    "/{user_id}",
    create_or_update_preferences,
    methods=["POST"],
    response_model=UserPreferences,
)
router.add_api_route(
    "/{user_id}",
    delete_user_preferences,
    methods=["DELETE"],
)
router.add_api_route(
    "/{user_id}/reset",
    reset_user_preferences,
    methods=["POST"],
    response_model=UserPreferences,
)
