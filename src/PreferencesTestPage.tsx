/**
 * 用户偏好设置测试页面
 */
import React, { useState } from 'react';
import { UserPreferencesSettings } from './components/UserPreferencesSettings';
import type { UserPreferences } from './types/preferences';

export const PreferencesTestPage: React.FC = () => {
  const [userId, setUserId] = useState('test_user_001');
  const [showSettings, setShowSettings] = useState(false);
  const [savedPreferences, setSavedPreferences] = useState<UserPreferences | null>(null);

  const handleSave = (preferences: UserPreferences) => {
    setSavedPreferences(preferences);
    console.log('Saved preferences:', preferences);
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>用户偏好设置测试页面</h1>

      <div style={{ marginBottom: '20px' }}>
        <label>
          用户 ID：
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            style={{ marginLeft: '10px', padding: '5px' }}
          />
        </label>
        <button
          onClick={() => setShowSettings(true)}
          style={{
            marginLeft: '10px',
            padding: '8px 16px',
            backgroundColor: '#1976d2',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          打开偏好设置
        </button>
      </div>

      {showSettings && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div style={{ width: '90%', maxWidth: '800px' }}>
            <UserPreferencesSettings
              userId={userId}
              onSave={handleSave}
              onClose={() => setShowSettings(false)}
            />
          </div>
        </div>
      )}

      {savedPreferences && (
        <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
          <h2>已保存的偏好设置</h2>
          <pre style={{ overflow: 'auto' }}>
            {JSON.stringify(savedPreferences, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
