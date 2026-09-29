-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.users (
  user_id uuid NOT NULL,
  email character varying NOT NULL UNIQUE,
  password_hash character varying,
  first_name character varying,
  last_name character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone,
  last_login_at timestamp with time zone,
  CONSTRAINT users_pkey PRIMARY KEY (user_id)
);
CREATE TABLE public.devices (
  device_id uuid NOT NULL DEFAULT gen_random_uuid(),
  device_name character varying,
  device_category character varying,
  device_type character varying,
  level_id uuid,
  measurement_unit text,
  status character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT devices_pkey PRIMARY KEY (device_id)
);
-- Latest synced image per camera. `id` is the tutor API's `camera_name` (e.g. level1_camera1);
-- `image_url` points at the public Supabase Storage bucket the hourly sync uploads to.
CREATE TABLE public.cameras (
  id text NOT NULL,
  label text NOT NULL,
  image_url text,
  captured_at timestamp with time zone DEFAULT now(),
  CONSTRAINT cameras_pkey PRIMARY KEY (id)
);
-- Stateful dashboard alerts raised and managed by the agent. At most one active
-- alert per alert_key (partial unique index): re-raising a key updates the row and
-- bumps occurrences instead of stacking duplicate alerts. Dismissal only hides an
-- active alert from the Overview pin (a re-raise clears dismissed_at to resurface
-- it); resolution is explicit via the agent tool or the Alerts page.
CREATE TABLE public.alerts (
  alert_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_key text NOT NULL CHECK (alert_key ~ '^[a-z0-9_]{1,64}$'),
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  title text NOT NULL CHECK (length(trim(title)) > 0 AND length(title) <= 160),
  message text NOT NULL CHECK (length(trim(message)) > 0 AND length(message) <= 4000),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'resolved')),
  occurrences integer NOT NULL DEFAULT 1 CHECK (occurrences >= 1),
  schedule_id uuid REFERENCES public.agent_scheduled_job(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz,
  resolved_by text CHECK (resolved_by IN ('agent', 'user')),
  dismissed_at timestamptz,
  CONSTRAINT alerts_resolution_consistency CHECK (
    ((status = 'resolved') = (resolved_at IS NOT NULL))
    AND ((status = 'resolved') = (resolved_by IS NOT NULL))
  )
);
CREATE UNIQUE INDEX alerts_active_key_unique ON public.alerts (alert_key) WHERE status = 'active';
CREATE INDEX alerts_status_updated_idx ON public.alerts (status, updated_at DESC);
CREATE TABLE public.sensor_data (
  timestamp_ms bigint NOT NULL DEFAULT ((EXTRACT(epoch FROM clock_timestamp()) * (1000)::numeric))::bigint,
  water_ph double precision,
  ec_us_cm double precision,
  water_temp_c double precision,
  ambient_temp_c double precision,
  humidity_pct double precision,
  reservoir_level_cm double precision,
  CONSTRAINT sensor_data_pkey PRIMARY KEY (timestamp_ms)
);
CREATE TABLE public.agent_scheduled_job (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  instruction text NOT NULL,
  cron_expression text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  title text NOT NULL,
  CONSTRAINT agent_scheduled_job_pkey PRIMARY KEY (id)
);

-- Safety rules and AI decision logging. Demo devices and rules are seed data,
-- not part of this schema. Approval does not trigger hardware execution yet.
CREATE TABLE public.safety_rules (
  rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid NOT NULL REFERENCES public.devices(device_id),
  action_type text NOT NULL DEFAULT 'run_for_duration'
    CHECK (action_type IN ('run_for_duration')),
  max_duration_seconds integer NOT NULL CHECK (max_duration_seconds > 0),
  cooldown_seconds integer NOT NULL DEFAULT 0 CHECK (cooldown_seconds >= 0),
  enabled boolean NOT NULL DEFAULT true,
  CONSTRAINT safety_rules_device_action_unique UNIQUE (device_id, action_type)
);

CREATE TABLE public.ai_decisions (
  decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  summary text NOT NULL CHECK (length(trim(summary)) > 0),
  recommendation text NOT NULL CHECK (length(trim(recommendation)) > 0),
  schedule_id uuid REFERENCES public.agent_scheduled_job(id) ON DELETE SET NULL
);

CREATE TABLE public.command_requests (
  request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id uuid REFERENCES public.ai_decisions(decision_id),
  device_id uuid NOT NULL REFERENCES public.devices(device_id),
  action_type text NOT NULL DEFAULT 'run_for_duration'
    CHECK (action_type IN ('run_for_duration')),
  duration_seconds integer NOT NULL CHECK (duration_seconds > 0),
  reason text NOT NULL CHECK (length(trim(reason)) > 0),
  status text NOT NULL DEFAULT 'pending_approval'
    CHECK (status IN (
      'pending_approval', 'blocked', 'approved', 'rejected', 'expired',
      'executing', 'succeeded', 'failed', 'unknown'
    )),
  reviewed_by uuid REFERENCES public.users(user_id) ON DELETE SET NULL,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  started_at timestamptz,
  finished_at timestamptz,
  result_message text,
  CONSTRAINT command_requests_expiry_check CHECK (expires_at > created_at),
  CONSTRAINT command_requests_execution_time_check CHECK (
    finished_at IS NULL OR (started_at IS NOT NULL AND finished_at >= started_at)
  )
);

-- Conversation history for the agent chat. Interactive chats are created by
-- POST /api/v1/chat; scheduled agent runs store one conversation per execution
-- with source = 'schedule'. schedule_id survives as NULL if the schedule is deleted.
CREATE TABLE public.chat_conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL CHECK (length(trim(title)) > 0),
  source text NOT NULL DEFAULT 'chat' CHECK (source IN ('chat', 'schedule')),
  schedule_id uuid REFERENCES public.agent_scheduled_job(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- One serialized AI SDK runtime message (ai.messages.Message JSON) per row,
-- ordered by seq within its conversation. History is replaced wholesale on save.
CREATE TABLE public.chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES public.chat_conversations(id) ON DELETE CASCADE,
  seq integer NOT NULL CHECK (seq >= 0),
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chat_messages_conversation_seq_unique UNIQUE (conversation_id, seq)
);
