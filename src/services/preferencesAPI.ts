/**
 * Frontend preferences service backed by the FastAPI backend.
 */

import { DEFAULT_PREFERENCE_UPDATE, DEFAULT_RISK_TOLERANCE } from '../types/preferences';
import type { PreferenceUpdate, UserPreferences } from '../types/preferences';
import { buildAuthenticatedHeaders } from './authHeaders';
import { resolveApiBaseUrl } from './apiConfig';
import { normalizeApiError } from './apiError';
import { buildApiUrl } from './apiUrl';

const API_BASE_URL = resolveApiBaseUrl();

function buildDefaultPreferences(userId: string): UserPreferences {
  return {
    user_id: userId,
    risk_tolerance: DEFAULT_RISK_TOLERANCE,
    focused_risks: DEFAULT_PREFERENCE_UPDATE.focused_risks!,
    user_role: DEFAULT_PREFERENCE_UPDATE.user_role!,
    experience_level: DEFAULT_PREFERENCE_UPDATE.experience_level!,
    region: DEFAULT_PREFERENCE_UPDATE.region,
    custom_thresholds: DEFAULT_PREFERENCE_UPDATE.custom_thresholds ?? {},
  };
}

function normalizeRiskTolerance(update?: PreferenceUpdate['risk_tolerance']) {
  return {
    ...DEFAULT_RISK_TOLERANCE,
    ...(update ?? {}),
  };
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T;
  }

  let errorMessage = '请求失败';
  try {
    const error = await response.json();
    errorMessage = error.detail || errorMessage;
  } catch {
    errorMessage = response.statusText || errorMessage;
  }

  throw new Error(errorMessage);
}

export class PreferencesAPI {
  static async getUserPreferences(userId: string): Promise<UserPreferences | null> {
    try {
      const response = await fetch(buildApiUrl(API_BASE_URL, `/preferences/${userId}`), {
        headers: await buildAuthenticatedHeaders(),
      });

      const data = await parseJsonResponse<UserPreferences>(response);
      return data ?? buildDefaultPreferences(userId);
    } catch (error) {
      throw normalizeApiError(error);
    }
  }

  static async saveUserPreferences(
    userId: string,
    preferences: PreferenceUpdate
  ): Promise<UserPreferences> {
    try {
      const payload = {
        risk_tolerance: normalizeRiskTolerance(preferences.risk_tolerance),
        focused_risks: preferences.focused_risks ?? DEFAULT_PREFERENCE_UPDATE.focused_risks,
        user_role: preferences.user_role ?? DEFAULT_PREFERENCE_UPDATE.user_role,
        experience_level:
          preferences.experience_level ?? DEFAULT_PREFERENCE_UPDATE.experience_level,
        region: preferences.region ?? null,
        custom_thresholds: preferences.custom_thresholds ?? {},
      };

      const response = await fetch(buildApiUrl(API_BASE_URL, `/preferences/${userId}`), {
        method: 'POST',
        headers: await buildAuthenticatedHeaders({
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify(payload),
      });

      return await parseJsonResponse<UserPreferences>(response);
    } catch (error) {
      throw normalizeApiError(error);
    }
  }

  static async deleteUserPreferences(userId: string): Promise<void> {
    try {
      const response = await fetch(buildApiUrl(API_BASE_URL, `/preferences/${userId}`), {
        method: 'DELETE',
        headers: await buildAuthenticatedHeaders(),
      });

      await parseJsonResponse<{ message: string }>(response);
    } catch (error) {
      throw normalizeApiError(error);
    }
  }

  static async resetUserPreferences(userId: string): Promise<UserPreferences> {
    try {
      const response = await fetch(
        buildApiUrl(API_BASE_URL, `/preferences/${userId}/reset`),
        {
          method: 'POST',
          headers: await buildAuthenticatedHeaders(),
        }
      );

      return await parseJsonResponse<UserPreferences>(response);
    } catch (error) {
      throw normalizeApiError(error);
    }
  }
}
