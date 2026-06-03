-- Rebuild AI provider RLS policies after schema iterations.
-- This is safe to run more than once.

ALTER TABLE public.ai_provider_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_model_configs ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_provider_configs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_model_configs TO authenticated;

ALTER TABLE public.agent_model_configs
  DROP CONSTRAINT IF EXISTS agent_model_configs_api_protocol_check;

ALTER TABLE public.agent_model_configs
  ADD CONSTRAINT agent_model_configs_api_protocol_check
  CHECK (api_protocol IN ('openai', 'anthropic', 'qwen', 'request'));

UPDATE public.agent_model_configs
SET api_protocol = 'request'
WHERE provider_name = 'custom'
  AND api_protocol IS DISTINCT FROM 'request';

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

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'unique_ai_provider_user_provider'
      AND conrelid = 'public.ai_provider_configs'::regclass
  ) THEN
    ALTER TABLE public.ai_provider_configs
      ADD CONSTRAINT unique_ai_provider_user_provider
      UNIQUE (user_id, provider_name);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'unique_agent_model_user_agent'
      AND conrelid = 'public.agent_model_configs'::regclass
  ) THEN
    ALTER TABLE public.agent_model_configs
      ADD CONSTRAINT unique_agent_model_user_agent
      UNIQUE (user_id, agent_name);
  END IF;
END $$;

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
