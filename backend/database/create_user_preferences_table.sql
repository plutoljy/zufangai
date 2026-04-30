-- ============================================
-- 租房避坑局 - 用户偏好表创建脚本
-- ============================================
-- 在 Supabase SQL Editor 中执行此脚本

-- 1. 创建用户偏好表
CREATE TABLE IF NOT EXISTS user_preferences (
    -- 主键：用户ID
    user_id TEXT PRIMARY KEY,

    -- 风险容忍度配置（JSON格式）
    risk_tolerance JSONB NOT NULL DEFAULT '{
        "deposit_tolerance": 1.0,
        "penalty_tolerance": 0.3,
        "utility_markup_tolerance": 0.2,
        "notice_period_tolerance": 30
    }'::jsonb,

    -- 关注的风险类型（数组）
    focused_risks TEXT[] NOT NULL DEFAULT ARRAY[
        'deposit_limit',
        'penalty_excessive',
        'utility_markup'
    ],

    -- 用户角色：tenant(租客) / landlord(房东) / agent(中介)
    user_role TEXT NOT NULL DEFAULT 'tenant',

    -- 经验等级：beginner(新手) / intermediate(中级) / expert(专家)
    experience_level TEXT NOT NULL DEFAULT 'beginner',

    -- 地区偏好（可选）
    region TEXT,

    -- 自定义风险阈值（JSON格式，可选）
    custom_thresholds JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 创建时间
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 更新时间
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_role
    ON user_preferences(user_role);

CREATE INDEX IF NOT EXISTS idx_user_preferences_experience_level
    ON user_preferences(experience_level);

CREATE INDEX IF NOT EXISTS idx_user_preferences_region
    ON user_preferences(region)
    WHERE region IS NOT NULL;

-- 3. 创建自动更新 updated_at 的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 4. 创建触发器
DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences;

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 5. 添加表注释
COMMENT ON TABLE user_preferences IS '用户偏好配置表，用于个性化风险判断';
COMMENT ON COLUMN user_preferences.user_id IS '用户唯一标识';
COMMENT ON COLUMN user_preferences.risk_tolerance IS '风险容忍度配置';
COMMENT ON COLUMN user_preferences.focused_risks IS '用户特别关注的风险类型';
COMMENT ON COLUMN user_preferences.user_role IS '用户角色';
COMMENT ON COLUMN user_preferences.experience_level IS '租房经验等级';
COMMENT ON COLUMN user_preferences.region IS '地区偏好';
COMMENT ON COLUMN user_preferences.custom_thresholds IS '自定义风险阈值';

-- 6. 插入测试数据（可选）
INSERT INTO user_preferences (
    user_id,
    risk_tolerance,
    focused_risks,
    user_role,
    experience_level,
    region
) VALUES (
    'test_user_001',
    '{
        "deposit_tolerance": 1.5,
        "penalty_tolerance": 0.5,
        "utility_markup_tolerance": 0.3,
        "notice_period_tolerance": 45
    }'::jsonb,
    ARRAY['deposit_limit', 'penalty_excessive', 'utility_markup'],
    'tenant',
    'beginner',
    '北京'
) ON CONFLICT (user_id) DO NOTHING;

-- 7. 验证表创建
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_preferences'
ORDER BY ordinal_position;

-- 8. 查询测试数据
SELECT * FROM user_preferences LIMIT 5;

-- ============================================
-- 执行完成后的验证步骤：
-- 1. 确认表已创建：SELECT * FROM user_preferences;
-- 2. 确认触发器已创建：SELECT * FROM pg_trigger WHERE tgname = 'update_user_preferences_updated_at';
-- 3. 测试插入：INSERT INTO user_preferences (user_id) VALUES ('test_user_002');
-- 4. 测试更新：UPDATE user_preferences SET region = '上海' WHERE user_id = 'test_user_002';
-- 5. 验证 updated_at 自动更新：SELECT user_id, created_at, updated_at FROM user_preferences;
-- ============================================
