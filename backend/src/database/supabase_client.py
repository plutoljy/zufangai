"""
Supabase client helpers for user preferences and auth-bound lookups.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models.user_preferences import UserPreferences


class SupabaseClient:
    """Supabase client wrapper used by the FastAPI backend."""

    def __init__(self):
        self.client = None
        self.enabled = False
        supabase_access_key = settings.supabase_service_role_key or settings.supabase_key

        if settings.supabase_url and supabase_access_key:
            try:
                from supabase import create_client

                self.client = create_client(settings.supabase_url, supabase_access_key)
                self.enabled = True
                print("[OK] Supabase client initialized")
            except ImportError:
                print("[WARN] supabase-py not installed, user preferences disabled")
            except Exception as exc:
                print(f"[WARN] Failed to initialize Supabase client: {exc}")
        else:
            print("[INFO] Supabase not configured, user preferences disabled")

    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Fetch a user's saved preferences."""
        if not self.enabled or not self.client:
            return None

        try:
            response = (
                self.client.table("user_preferences").select("*").eq("user_id", user_id).execute()
            )

            if response.data and len(response.data) > 0:
                data = response.data[0]
                return UserPreferences(**data)

            return None
        except Exception as exc:
            print(f"[ERROR] Failed to get user preferences: {exc}")
            return None

    def get_user_id_from_access_token(self, access_token: str) -> Optional[str]:
        """Validate a Supabase access token and return the authenticated user id."""
        if not self.enabled or not self.client or not access_token:
            return None

        try:
            response = self.client.auth.get_user(access_token)
            user = getattr(response, "user", None)
            return getattr(user, "id", None) if user else None
        except Exception as exc:
            print(f"[ERROR] Failed to validate Supabase access token: {exc}")
            return None

    def save_user_preferences(self, preferences: UserPreferences) -> bool:
        """Persist user preferences to Supabase."""
        if not self.enabled or not self.client:
            return False

        try:
            data = preferences.model_dump()
            data["updated_at"] = datetime.utcnow().isoformat()

            existing = self.get_user_preferences(preferences.user_id)

            if existing:
                self.client.table("user_preferences").update(data).eq(
                    "user_id", preferences.user_id
                ).execute()
            else:
                data["created_at"] = datetime.utcnow().isoformat()
                self.client.table("user_preferences").insert(data).execute()

            print(f"[OK] User preferences saved for user_id: {preferences.user_id}")
            return True
        except Exception as exc:
            print(f"[ERROR] Failed to save user preferences: {exc}")
            return False

    def delete_user_preferences(self, user_id: str) -> bool:
        """Delete a user's saved preferences."""
        if not self.enabled or not self.client:
            return False

        try:
            self.client.table("user_preferences").delete().eq("user_id", user_id).execute()
            print(f"[OK] User preferences deleted for user_id: {user_id}")
            return True
        except Exception as exc:
            print(f"[ERROR] Failed to delete user preferences: {exc}")
            return False


supabase_client = SupabaseClient()
