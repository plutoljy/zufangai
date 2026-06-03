-- User-configurable AI provider settings for analysis agents.
-- RAG embeddings stay on the backend EMBEDDING_* configuration.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS ai_provider_configs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  provider_name TEXT NOT NULL CHECK (provider_name IN ('openai', 'claude', 'qwen', 'custom')),
  api_key_encrypted TEXT NOT NULL,
  base_url TEXT,
  model_name TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT unique_ai_provider_user_provider UNIQUE (user_id, provider_name)
);

CREATE TABLE IF NOT EXISTS agent_model_configs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  agent_name TEXT NOT NULL CHECK (agent_name IN ('owl', 'dog', 'beaver', 'cat')),
  provider_name TEXT NOT NULL CHECK (provider_name IN ('openai', 'claude', 'qwen', 'custom')),
  api_protocol TEXT CHECK (api_protocol IN ('openai', 'anthropic', 'qwen', 'request')),
  api_key_encrypted TEXT,
  base_url TEXT,
  model_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT unique_agent_model_user_agent UNIQUE (user_id, agent_name)
);

ALTER TABLE agent_model_configs DROP CONSTRAINT IF EXISTS agent_model_provider_fk;

ALTER TABLE agent_model_configs
  ADD COLUMN IF NOT EXISTS api_protocol TEXT;

ALTER TABLE agent_model_configs
  DROP CONSTRAINT IF EXISTS agent_model_configs_api_protocol_check;

ALTER TABLE agent_model_configs
  ADD CONSTRAINT agent_model_configs_api_protocol_check
  CHECK (api_protocol IN ('openai', 'anthropic', 'qwen', 'request'));

ALTER TABLE agent_model_configs
  ADD COLUMN IF NOT EXISTS api_key_encrypted TEXT;

ALTER TABLE agent_model_configs
  ADD COLUMN IF NOT EXISTS base_url TEXT;

UPDATE agent_model_configs
SET api_protocol = CASE
  WHEN provider_name = 'claude' THEN 'anthropic'
  WHEN provider_name = 'qwen' THEN 'qwen'
  WHEN provider_name = 'custom' THEN 'request'
  ELSE 'openai'
END
WHERE api_protocol IS NULL;

ALTER TABLE public.ai_provider_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_model_configs ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_provider_configs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_model_configs TO authenticated;

DO $$
DECLARE
  policy_record record;
BEGIN
  FOR policy_record IN
    SELECT policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'ai_provider_configs'
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON public.ai_provider_configs',
      policy_record.policyname
    );
  END LOOP;

  FOR policy_record IN
    SELECT policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'agent_model_configs'
  LOOP
    EXECUTE format(
      'DROP POLICY IF EXISTS %I ON public.agent_model_configs',
      policy_record.policyname
    );
  END LOOP;
END $$;

CREATE POLICY "Users manage own AI provider configs"
  ON public.ai_provider_configs
  FOR ALL
  TO authenticated
  USING ((select auth.uid())::text = user_id)
  WITH CHECK ((select auth.uid())::text = user_id);

CREATE POLICY "Users manage own agent model configs"
  ON public.agent_model_configs
  FOR ALL
  TO authenticated
  USING ((select auth.uid())::text = user_id)
  WITH CHECK ((select auth.uid())::text = user_id);

CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_user_id
  ON ai_provider_configs(user_id);

CREATE INDEX IF NOT EXISTS idx_agent_model_configs_user_id
  ON agent_model_configs(user_id);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_ai_provider_configs_updated_at ON ai_provider_configs;
CREATE TRIGGER update_ai_provider_configs_updated_at
BEFORE UPDATE ON ai_provider_configs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_model_configs_updated_at ON agent_model_configs;
CREATE TRIGGER update_agent_model_configs_updated_at
BEFORE UPDATE ON agent_model_configs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION public.upsert_agent_model_config(
  p_user_id TEXT,
  p_agent_name TEXT,
  p_provider_name TEXT,
  p_api_protocol TEXT,
  p_api_key_encrypted TEXT,
  p_base_url TEXT,
  p_model_name TEXT
)
RETURNS public.agent_model_configs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  saved_row public.agent_model_configs;
BEGIN
  IF auth.uid() IS NULL OR auth.uid()::text <> p_user_id THEN
    RAISE EXCEPTION 'Forbidden'
      USING ERRCODE = '42501';
  END IF;

  INSERT INTO public.agent_model_configs (
    user_id,
    agent_name,
    provider_name,
    api_protocol,
    api_key_encrypted,
    base_url,
    model_name
  )
  VALUES (
    p_user_id,
    p_agent_name,
    p_provider_name,
    p_api_protocol,
    p_api_key_encrypted,
    p_base_url,
    p_model_name
  )
  ON CONFLICT (user_id, agent_name)
  DO UPDATE SET
    provider_name = EXCLUDED.provider_name,
    api_protocol = EXCLUDED.api_protocol,
    api_key_encrypted = COALESCE(
      EXCLUDED.api_key_encrypted,
      agent_model_configs.api_key_encrypted
    ),
    base_url = EXCLUDED.base_url,
    model_name = EXCLUDED.model_name,
    updated_at = NOW()
  RETURNING * INTO saved_row;

  RETURN saved_row;
END;
$$;

REVOKE ALL ON FUNCTION public.upsert_agent_model_config(
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT
) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.upsert_agent_model_config(
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT,
  TEXT
) TO authenticated;
