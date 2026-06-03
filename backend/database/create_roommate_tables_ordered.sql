-- 合租伙伴匹配功能 - 数据库表结构（按依赖顺序）
-- 创建日期: 2026-05-06

-- 第一批：独立表（无外键依赖）

-- 1. 用户在线状态表 (user_presence)
CREATE TABLE IF NOT EXISTS user_presence (
    user_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'offline' CHECK (status IN ('online', 'away', 'offline')),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    device_info JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 宠物画像表 (roommate_profiles)
CREATE TABLE IF NOT EXISTS roommate_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    lifestyle_habits JSONB NOT NULL DEFAULT '{}'::jsonb,
    deal_breakers JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_preferences_id UUID,
    pet_personality JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_profiles_user ON roommate_profiles(user_id);

-- 3. 合租需求表 (roommate_requests)
CREATE TABLE IF NOT EXISTS roommate_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_id UUID NOT NULL REFERENCES roommate_profiles(profile_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    rent_range JSONB,
    mode TEXT NOT NULL DEFAULT 'quick' CHECK (mode IN ('quick', 'deep')),
    interview_config JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'interviewing', 'completed', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_requests_user ON roommate_requests(user_id);
CREATE INDEX idx_requests_status ON roommate_requests(status, created_at DESC);
CREATE INDEX idx_requests_location ON roommate_requests(location) WHERE location IS NOT NULL;

-- 4. 宠物面试表 (pet_interviews)
CREATE TABLE IF NOT EXISTS pet_interviews (
    interview_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES roommate_requests(request_id) ON DELETE CASCADE,
    applicant_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    dialogue JSONB DEFAULT '[]'::jsonb,
    temperature FLOAT DEFAULT 0.7,
    max_questions INT DEFAULT 10,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'abandoned')),
    detected_issues JSONB DEFAULT '[]'::jsonb,
    consistency_alerts JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_interviews_request ON pet_interviews(request_id);
CREATE INDEX idx_interviews_applicant ON pet_interviews(applicant_id);
CREATE INDEX idx_interviews_status ON pet_interviews(status, created_at DESC);

-- 5. 匹配结果表 (match_results)
CREATE TABLE IF NOT EXISTS match_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID NOT NULL REFERENCES pet_interviews(interview_id) ON DELETE CASCADE,
    overall_score INT CHECK (overall_score >= 0 AND overall_score <= 100),
    deal_breaker_analysis JSONB DEFAULT '{}'::jsonb,
    common_grounds JSONB DEFAULT '[]'::jsonb,
    integrity_assessment JSONB DEFAULT '{}'::jsonb,
    summary TEXT,
    recommendation TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(interview_id)
);

CREATE INDEX idx_results_interview ON match_results(interview_id);
CREATE INDEX idx_results_score ON match_results(overall_score DESC);

-- 第二批：聊天系统表

-- 6. 聊天会话表 (chat_conversations)
CREATE TABLE IF NOT EXISTS chat_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id UUID REFERENCES pet_interviews(interview_id) ON DELETE CASCADE,
    participant_ids TEXT[] NOT NULL,
    conversation_type TEXT NOT NULL CHECK (conversation_type IN ('pet_interview', 'user_direct', 'mixed')),
    last_message_id UUID,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unread_count JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversations_participants ON chat_conversations USING GIN(participant_ids);
CREATE INDEX idx_conversations_last_message ON chat_conversations(last_message_at DESC);
CREATE INDEX idx_conversations_interview ON chat_conversations(interview_id) WHERE interview_id IS NOT NULL;

-- 7. 聊天消息表 (chat_messages)
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('pet', 'user', 'system')),
    content TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('text', 'question', 'answer', 'user_interrupt')),
    reply_to_id UUID REFERENCES chat_messages(message_id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sending', 'sent', 'delivered', 'read', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_messages_conversation ON chat_messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_sender ON chat_messages(sender_id, created_at DESC);
CREATE INDEX idx_messages_reply_to ON chat_messages(reply_to_id) WHERE reply_to_id IS NOT NULL;

-- 8. 消息已读状态表 (message_read_status)
CREATE TABLE IF NOT EXISTS message_read_status (
    user_id TEXT NOT NULL,
    conversation_id UUID NOT NULL REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    last_read_message_id UUID REFERENCES chat_messages(message_id) ON DELETE SET NULL,
    last_read_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    unread_count INT DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, conversation_id)
);

CREATE INDEX idx_read_status_user ON message_read_status(user_id, last_read_at DESC);

-- 9. 消息队列表 (message_queue)
CREATE TABLE IF NOT EXISTS message_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES chat_messages(message_id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES chat_conversations(conversation_id) ON DELETE CASCADE,
    task_type TEXT NOT NULL CHECK (task_type IN ('send_message', 'pet_generate_question', 'analyze_answer', 'check_integrity')),
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_queue_status ON message_queue(status, created_at) WHERE status IN ('pending', 'processing');

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表添加更新时间触发器
CREATE TRIGGER update_user_presence_updated_at BEFORE UPDATE ON user_presence
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roommate_profiles_updated_at BEFORE UPDATE ON roommate_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roommate_requests_updated_at BEFORE UPDATE ON roommate_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pet_interviews_updated_at BEFORE UPDATE ON pet_interviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_results_updated_at BEFORE UPDATE ON match_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON chat_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_messages_updated_at BEFORE UPDATE ON chat_messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_message_read_status_updated_at BEFORE UPDATE ON message_read_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 添加注释
COMMENT ON TABLE user_presence IS '用户在线状态表 - 跟踪用户在线/离线状态';
COMMENT ON TABLE roommate_profiles IS '宠物画像表 - 用户的生活习惯和踩雷点';
COMMENT ON TABLE roommate_requests IS '合租需求表 - 发布的合租需求';
COMMENT ON TABLE pet_interviews IS '宠物面试表 - 宠物对话记录';
COMMENT ON TABLE match_results IS '匹配结果表 - LLM分析的匹配结果';
COMMENT ON TABLE chat_conversations IS '聊天会话表 - 管理宠物面试和用户直接对话';
COMMENT ON TABLE chat_messages IS '聊天消息表 - 存储所有消息（宠物和用户）';
COMMENT ON TABLE message_read_status IS '消息已读状态表 - 跟踪用户的已读状态';
COMMENT ON TABLE message_queue IS '消息队列表 - 异步任务处理队列';
