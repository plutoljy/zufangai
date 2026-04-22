/**
 * User preference types used by the frontend.
 */

export interface RiskTolerance {
  deposit_tolerance: number;
  penalty_tolerance: number;
  utility_markup_tolerance: number;
  notice_period_tolerance: number;
}

export interface UserPreferences {
  user_id: string;
  risk_tolerance: RiskTolerance;
  focused_risks: string[];
  user_role: 'tenant' | 'landlord' | 'agent';
  experience_level: 'beginner' | 'intermediate' | 'expert';
  region?: string;
  custom_thresholds: Record<string, number>;
  created_at?: string;
  updated_at?: string;
}

export interface PreferenceUpdate {
  risk_tolerance?: Partial<RiskTolerance>;
  focused_risks?: string[];
  user_role?: 'tenant' | 'landlord' | 'agent';
  experience_level?: 'beginner' | 'intermediate' | 'expert';
  region?: string;
  custom_thresholds?: Record<string, number>;
}

export const DEFAULT_RISK_TOLERANCE: RiskTolerance = {
  deposit_tolerance: 1.0,
  penalty_tolerance: 0.3,
  utility_markup_tolerance: 0.2,
  notice_period_tolerance: 30,
};

export const DEFAULT_PREFERENCE_UPDATE: PreferenceUpdate = {
  risk_tolerance: DEFAULT_RISK_TOLERANCE,
  focused_risks: ['deposit_limit', 'penalty_excessive', 'utility_markup'],
  user_role: 'tenant',
  experience_level: 'beginner',
  region: '',
  custom_thresholds: {},
};

export const RISK_TYPES = [
  { value: 'deposit_limit', label: '押金超限' },
  { value: 'penalty_excessive', label: '违约金过高' },
  { value: 'utility_markup', label: '水电费加价' },
  { value: 'notice_period', label: '提前退租通知期' },
  { value: 'sublease_restriction', label: '转租限制' },
  { value: 'maintenance_unclear', label: '维修责任不明' },
  { value: 'auto_renewal', label: '自动续租' },
] as const;

export const EXPERIENCE_LEVELS = [
  { value: 'beginner', label: '新手', description: '第一次租房或经验较少' },
  { value: 'intermediate', label: '中级', description: '有一定租房经验' },
  { value: 'expert', label: '专家', description: '资深租房者或房产从业者' },
] as const;

export const USER_ROLES = [
  { value: 'tenant', label: '租客' },
  { value: 'landlord', label: '房东' },
  { value: 'agent', label: '中介' },
] as const;
