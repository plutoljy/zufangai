/**
 * 用户偏好设置组件
 */
import React, { useState, useEffect } from 'react';
import type { UserPreferences, PreferenceUpdate } from '../types/preferences';
import { RISK_TYPES, EXPERIENCE_LEVELS, USER_ROLES } from '../types/preferences';
import { PreferencesAPI } from '../services/preferencesAPI';

interface Props {
  userId: string;
  onSave?: (preferences: UserPreferences) => void;
  onClose?: () => void;
}

export const UserPreferencesSettings: React.FC<Props> = ({ userId, onSave, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [preferences, setPreferences] = useState<PreferenceUpdate>({
    risk_tolerance: {
      deposit_tolerance: 1.0,
      penalty_tolerance: 0.3,
      utility_markup_tolerance: 0.2,
      notice_period_tolerance: 30,
    },
    focused_risks: ['deposit_limit', 'penalty_excessive', 'utility_markup'],
    user_role: 'tenant',
    experience_level: 'beginner',
    region: '',
  });

  // 加载用户偏好
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const data = await PreferencesAPI.getUserPreferences(userId);
        if (data) {
          setPreferences({
            risk_tolerance: data.risk_tolerance,
            focused_risks: data.focused_risks,
            user_role: data.user_role,
            experience_level: data.experience_level,
            region: data.region || '',
          });
        }
      } catch (error) {
        console.error('Failed to load preferences:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPreferences();
  }, [userId]);

  // 保存偏好
  const handleSave = async () => {
    setSaving(true);
    try {
      const saved = await PreferencesAPI.saveUserPreferences(userId, preferences);
      onSave?.(saved);
      alert('偏好设置已保存');
    } catch (error) {
      alert('保存失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  // 重置偏好
  const handleReset = async () => {
    if (!confirm('确定要重置为默认设置吗？')) return;

    setSaving(true);
    try {
      const reset = await PreferencesAPI.resetUserPreferences(userId);
      setPreferences({
        risk_tolerance: reset.risk_tolerance,
        focused_risks: reset.focused_risks,
        user_role: reset.user_role,
        experience_level: reset.experience_level,
        region: reset.region || '',
      });
      alert('已重置为默认设置');
    } catch (error) {
      alert('重置失败，请重试');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="preferences-loading">加载中...</div>;
  }

  return (
    <div className="preferences-container">
      <div className="preferences-header">
        <h2>用户偏好设置</h2>
        {onClose && (
          <button onClick={onClose} className="close-btn">
            ×
          </button>
        )}
      </div>

      <div className="preferences-content">
        {/* 基本信息 */}
        <section className="preferences-section">
          <h3>基本信息</h3>

          <div className="form-group">
            <label>用户角色</label>
            <select
              value={preferences.user_role}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  user_role: e.target.value as any,
                })
              }
            >
              {USER_ROLES.map((role) => (
                <option key={role.value} value={role.value}>
                  {role.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>经验等级</label>
            <select
              value={preferences.experience_level}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  experience_level: e.target.value as any,
                })
              }
            >
              {EXPERIENCE_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label} - {level.description}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>所在地区（可选）</label>
            <input
              type="text"
              value={preferences.region || ''}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  region: e.target.value,
                })
              }
              placeholder="例如：北京"
            />
          </div>
        </section>

        {/* 风险容忍度 */}
        <section className="preferences-section">
          <h3>风险容忍度</h3>

          <div className="form-group">
            <label>
              押金容忍度：{preferences.risk_tolerance?.deposit_tolerance || 1.0} 倍月租金
            </label>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={preferences.risk_tolerance?.deposit_tolerance || 1.0}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  risk_tolerance: {
                    ...preferences.risk_tolerance!,
                    deposit_tolerance: parseFloat(e.target.value),
                  },
                })
              }
            />
            <small>押金超过此倍数将被标记为高风险</small>
          </div>

          <div className="form-group">
            <label>
              违约金容忍度：{((preferences.risk_tolerance?.penalty_tolerance || 0.3) * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={preferences.risk_tolerance?.penalty_tolerance || 0.3}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  risk_tolerance: {
                    ...preferences.risk_tolerance!,
                    penalty_tolerance: parseFloat(e.target.value),
                  },
                })
              }
            />
            <small>违约金超过此比例将被标记为高风险</small>
          </div>

          <div className="form-group">
            <label>
              水电费加价容忍度：{((preferences.risk_tolerance?.utility_markup_tolerance || 0.2) * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={preferences.risk_tolerance?.utility_markup_tolerance || 0.2}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  risk_tolerance: {
                    ...preferences.risk_tolerance!,
                    utility_markup_tolerance: parseFloat(e.target.value),
                  },
                })
              }
            />
            <small>水电费加价超过此比例将被标记为高风险</small>
          </div>

          <div className="form-group">
            <label>
              提前退租通知期容忍度：{preferences.risk_tolerance?.notice_period_tolerance || 30} 天
            </label>
            <input
              type="range"
              min="7"
              max="90"
              step="1"
              value={preferences.risk_tolerance?.notice_period_tolerance || 30}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  risk_tolerance: {
                    ...preferences.risk_tolerance!,
                    notice_period_tolerance: parseInt(e.target.value),
                  },
                })
              }
            />
            <small>通知期超过此天数将被标记为高风险</small>
          </div>
        </section>

        {/* 关注的风险类型 */}
        <section className="preferences-section">
          <h3>关注的风险类型</h3>
          <p className="section-description">选择您特别关注的风险类型，分析时会重点提示</p>

          <div className="checkbox-group">
            {RISK_TYPES.map((risk) => (
              <label key={risk.value} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={preferences.focused_risks?.includes(risk.value) || false}
                  onChange={(e) => {
                    const current = preferences.focused_risks || [];
                    const updated = e.target.checked
                      ? [...current, risk.value]
                      : current.filter((r) => r !== risk.value);
                    setPreferences({
                      ...preferences,
                      focused_risks: updated,
                    });
                  }}
                />
                {risk.label}
              </label>
            ))}
          </div>
        </section>
      </div>

      {/* 操作按钮 */}
      <div className="preferences-footer">
        <button onClick={handleReset} disabled={saving} className="btn-secondary">
          重置为默认
        </button>
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? '保存中...' : '保存设置'}
        </button>
      </div>

      <style>{`
        .preferences-container {
          max-width: 800px;
          margin: 0 auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .preferences-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          border-bottom: 1px solid #e0e0e0;
        }

        .preferences-header h2 {
          margin: 0;
          font-size: 24px;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 32px;
          cursor: pointer;
          color: #666;
        }

        .close-btn:hover {
          color: #333;
        }

        .preferences-content {
          padding: 20px;
          max-height: 600px;
          overflow-y: auto;
        }

        .preferences-section {
          margin-bottom: 30px;
        }

        .preferences-section h3 {
          margin: 0 0 15px 0;
          font-size: 18px;
          color: #333;
        }

        .section-description {
          margin: 0 0 15px 0;
          color: #666;
          font-size: 14px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
          color: #333;
        }

        .form-group input[type="text"],
        .form-group select {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
        }

        .form-group input[type="range"] {
          width: 100%;
        }

        .form-group small {
          display: block;
          margin-top: 4px;
          color: #666;
          font-size: 12px;
        }

        .checkbox-group {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 10px;
        }

        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
        }

        .checkbox-label input[type="checkbox"] {
          cursor: pointer;
        }

        .preferences-footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 20px;
          border-top: 1px solid #e0e0e0;
        }

        .btn-primary,
        .btn-secondary {
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          font-size: 14px;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .btn-primary {
          background-color: #1976d2;
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          background-color: #1565c0;
        }

        .btn-secondary {
          background-color: #f5f5f5;
          color: #333;
        }

        .btn-secondary:hover:not(:disabled) {
          background-color: #e0e0e0;
        }

        .btn-primary:disabled,
        .btn-secondary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .preferences-loading {
          padding: 40px;
          text-align: center;
          color: #666;
        }
      `}</style>
    </div>
  );
};
