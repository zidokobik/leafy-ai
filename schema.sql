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
CREATE TABLE public.cameras (
  camera_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  camera_name character varying NOT NULL,
  level_id uuid,
  status character varying,
  CONSTRAINT cameras_pkey PRIMARY KEY (camera_id)
);
CREATE TABLE public.images (
  image_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  captured_at timestamp with time zone NOT NULL,
  camera_id bigint,
  crop_cycle_id bigint,
  experiment_id bigint,
  source_protocol character varying,
  image_url text,
  CONSTRAINT images_pkey PRIMARY KEY (image_id),
  CONSTRAINT images_camera_id_fkey FOREIGN KEY (camera_id) REFERENCES public.cameras(camera_id)
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
