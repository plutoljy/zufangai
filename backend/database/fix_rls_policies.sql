-- ============================================
-- 修复 RLS 策略 - 允许匿名访问
-- ============================================

-- 1. 删除现有策略
DROP POLICY IF EXISTS "Users can read own preferences" ON user_preferences;
DROP POLICY IF EXISTS "Users can insert own preferences" ON user_preferences;
DROP POLICY IF EXISTS "Users can update own preferences" ON user_preferences;
DROP POLICY IF EXISTS "Users can delete own preferences" ON user_preferences;

-- 2. 创建新的宽松策略（适用于开发环境）
-- 注意：生产环境应该根据实际的认证系统调整这些策略

-- 允许所有读取操作
CREATE POLICY "Allow all to read preferences"
    ON user_preferences
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- 允许所有插入操作
CREATE POLICY "Allow all to insert preferences"
    ON user_preferences
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- 允许所有更新操作
CREATE POLICY "Allow all to update preferences"
    ON user_preferences
    FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- 允许所有删除操作
CREATE POLICY "Allow all to delete preferences"
    ON user_preferences
    FOR DELETE
    TO anon, authenticated
    USING (true);

-- 3. 验证策略
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'user_preferences';

-- 4. 插入测试数据
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
) ON CONFLICT (user_id) DO UPDATE SET
    risk_tolerance = EXCLUDED.risk_tolerance,
    focused_risks = EXCLUDED.focused_risks,
    user_role = EXCLUDED.user_role,
    experience_level = EXCLUDED.experience_level,
    region = EXCLUDED.region,
    updated_at = NOW();

-- 5. 查询测试数据
SELECT * FROM user_preferences WHERE user_id = 'test_user_001';
