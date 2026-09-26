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
CREATE TABLE public.alerts (
  alert_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  severity character varying,
  alert_type character varying,
  message text,
  device_id uuid,
  decision_id bigint,
  crop_cycle_id bigint,
  acknowledged_by uuid,
  acknowledge_at timestamp with time zone,
  CONSTRAINT alerts_pkey PRIMARY KEY (alert_id),
  CONSTRAINT alerts_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id),
  CONSTRAINT alerts_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES public.users(user_id)
);
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

-- alerts.decision_id remains an existing bigint without a foreign key;
-- it is not linked to the UUID key in ai_decisions.
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
