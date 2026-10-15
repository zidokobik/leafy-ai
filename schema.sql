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
-- Kasa power strips on the farm network, reached by IP address or hostname.
CREATE TABLE public.powerboards (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK (length(trim(name)) > 0),
  host text NOT NULL UNIQUE CHECK (length(trim(host)) > 0)
);
-- Equipment plugged into one powerboard outlet. outlet_num is 1-based (outlet 1 is the
-- board's first socket). A powerboard cannot be deleted while devices still use it.
CREATE TABLE public.devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL CHECK (length(trim(name)) > 0 AND length(name) <= 100),
  device_type text NOT NULL CHECK (device_type IN ('fan', 'light', 'irrigation_pump', 'ec_doser', 'ph_doser')),
  powerboard_id uuid NOT NULL REFERENCES public.powerboards(id) ON DELETE RESTRICT,
  outlet_num integer NOT NULL CHECK (outlet_num >= 1),
  CONSTRAINT devices_powerboard_outlet_unique UNIQUE (powerboard_id, outlet_num)
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
-- Email recipients for admin notifications, managed on the Alerts page. SMTP
-- credentials live in .env, not in the database.
CREATE TABLE public.email_recipients (
  recipient_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE CHECK (length(trim(email)) > 0 AND length(email) <= 254 AND position('@' in email) > 1),
  label text CHECK (label IS NULL OR length(label) <= 120),
  enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- Audit log of every admin email send attempt. The agent's send_email tool is
-- prompt-guided to email only critical escalations and explicitly requested
-- reports; `triggered_by` is 'user' for test emails sent from the Alerts page.
CREATE TABLE public.email_logs (
  email_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recipients text[] NOT NULL,
  subject text NOT NULL,
  status text NOT NULL CHECK (status IN ('sent', 'failed')),
  error text,
  schedule_id uuid REFERENCES public.agent_scheduled_job(id) ON DELETE SET NULL,
  triggered_by text NOT NULL CHECK (triggered_by IN ('agent', 'user')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX email_logs_created_idx ON public.email_logs (created_at DESC);
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

-- Agent proposals to switch a device on for a set time. A person approves (the outlet
-- switches on and an in-process timer switches it off at ends_at) or rejects it;
-- unreviewed proposals expire at expires_at. powerboard_host/outlet_num snapshot the
-- outlet that was switched on so the switch-off still targets it if the device is
-- edited or deleted. device_name keeps the name for the log after a device is deleted.
-- status: pending -> rejected | expired | failed (could not switch on) | running;
-- running -> completed | stopped (switched off early by a person) | failed (could not
-- switch off; a critical alert is raised).
CREATE TABLE public.device_proposals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id uuid REFERENCES public.devices(id) ON DELETE SET NULL,
  device_name text NOT NULL,
  duration_seconds integer NOT NULL CHECK (duration_seconds BETWEEN 1 AND 86400),
  reason text NOT NULL CHECK (length(trim(reason)) > 0 AND length(reason) <= 2000),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'rejected', 'expired', 'running', 'completed', 'stopped', 'failed')),
  schedule_id uuid REFERENCES public.agent_scheduled_job(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  reviewed_by uuid REFERENCES public.users(user_id) ON DELETE SET NULL,
  reviewed_at timestamptz,
  powerboard_host text,
  outlet_num integer,
  started_at timestamptz,
  ends_at timestamptz,
  finished_at timestamptz,
  result_message text,
  CONSTRAINT device_proposals_expiry_check CHECK (expires_at > created_at),
  CONSTRAINT device_proposals_run_check CHECK (
    (started_at IS NULL) = (ends_at IS NULL)
    AND (started_at IS NULL OR (powerboard_host IS NOT NULL AND outlet_num IS NOT NULL))
    AND (status <> 'running' OR started_at IS NOT NULL)
  )
);
-- One open (pending or running) proposal per device.
CREATE UNIQUE INDEX device_proposals_open_device_unique
  ON public.device_proposals (device_id) WHERE status IN ('pending', 'running');
CREATE INDEX device_proposals_created_idx ON public.device_proposals (created_at DESC);

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

-- CV results: one row per camera frame x planting hole (kind 'hole') or canopy zone
-- (kind 'zone'), loaded from cv/data/runs/*/observations.csv. Insert-only: a CV fix
-- comes with a new model_version. captured_at is farm local time from the file name.
CREATE TABLE public.plant_observations (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  image_id text NOT NULL,
  model_version text NOT NULL,
  camera_id text NOT NULL,
  captured_at timestamp NOT NULL,
  level smallint NOT NULL,
  period text NOT NULL,
  hole_id text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('hole', 'zone')),
  row smallint,
  col smallint,
  in_frame real,
  occupied boolean NOT NULL,
  coverage real NOT NULL CHECK (coverage BETWEEN 0 AND 1),
  boundary_contact real CHECK (boundary_contact BETWEEN 0 AND 1),
  contact_along real CHECK (contact_along BETWEEN 0 AND 1),
  contact_across real CHECK (contact_across BETWEEN 0 AND 1),
  plant_area_px integer,
  status text NOT NULL CHECK (status IN ('empty', 'growing', 'candidate', 'ready', 'uncertain')),
  confirmed_frames smallint NOT NULL,
  flags text[] NOT NULL DEFAULT '{}',
  CONSTRAINT plant_observations_unique UNIQUE (image_id, hole_id, model_version)
);
CREATE INDEX plant_observations_camera_time_idx ON public.plant_observations (camera_id, captured_at DESC);

-- Batches of plants moved from Level 1 to Level 2. Harvest is due 7 days after the move (the
-- owner's rule), so these dates drive the harvest recommendation, not the camera. Times are farm
-- local time like plant_observations.captured_at; harvested_at stays NULL until the harvest.
CREATE TABLE public.level2_batches (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  moved_at timestamp NOT NULL UNIQUE,
  harvested_at timestamp CHECK (harvested_at IS NULL OR harvested_at >= moved_at),
  note text NOT NULL DEFAULT ''
);
-- The two moves in the archived camera frames (cv/data/periods.csv, level2_camera2 P2 and P5).
INSERT INTO public.level2_batches (moved_at, harvested_at, note) VALUES
  ('2026-09-30 11:00:27', '2026-10-07 17:00:36', 'Level 1 canopy moved up 30 Sep; harvested 7 Oct (frames)'),
  ('2026-10-08 16:00:30', NULL, 'Crowded Level 1 plants moved up 8 Oct (new Level 1 layout the same hour)');
