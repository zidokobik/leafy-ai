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
CREATE TABLE public.roles (
  role_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  role_name character varying NOT NULL UNIQUE,
  description character varying,
  CONSTRAINT roles_pkey PRIMARY KEY (role_id)
);
CREATE TABLE public.permissions (
  permission_id uuid NOT NULL DEFAULT gen_random_uuid(),
  resource character varying,
  action character varying,
  description character varying,
  permission_code character varying NOT NULL UNIQUE,
  CONSTRAINT permissions_pkey PRIMARY KEY (permission_id)
);
CREATE TABLE public.user_role (
  user_id uuid NOT NULL,
  role_id bigint NOT NULL,
  assigned_at timestamp with time zone NOT NULL,
  assigned_by uuid,
  CONSTRAINT user_role_pkey PRIMARY KEY (user_id, role_id),
  CONSTRAINT user_role_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(role_id),
  CONSTRAINT user_role_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id),
  CONSTRAINT user_role_assigned_by_fkey FOREIGN KEY (assigned_by) REFERENCES public.users(user_id)
);
CREATE TABLE public.sensor_data (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  water_ph double precision,
  ec_us_cm double precision,
  water_temp_c double precision,
  ambient_temp_c double precision,
  humidity_pct double precision,
  reservoir_level_cm double precision,
  irrigation_pump_state smallint,
  ec_target_us_cm double precision,
  created_at timestamp with time zone NOT NULL,
  CONSTRAINT sensor_data_pkey PRIMARY KEY (id)
);
CREATE TABLE public.role_permission (
  role_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  permission_id uuid NOT NULL,
  CONSTRAINT role_permission_pkey PRIMARY KEY (role_id, permission_id),
  CONSTRAINT role_permission_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(permission_id),
  CONSTRAINT role_permission_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(role_id)
);
CREATE TABLE public.levels (
  level_id uuid NOT NULL DEFAULT gen_random_uuid(),
  level_number integer NOT NULL UNIQUE,
  level_name character varying,
  description character varying,
  CONSTRAINT levels_pkey PRIMARY KEY (level_id)
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
  CONSTRAINT devices_pkey PRIMARY KEY (device_id),
  CONSTRAINT devices_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.levels(level_id)
);
CREATE TABLE public.cameras (
  camera_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  camera_name character varying NOT NULL,
  level_id uuid,
  status character varying,
  CONSTRAINT cameras_pkey PRIMARY KEY (camera_id),
  CONSTRAINT cameras_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.levels(level_id)
);
CREATE TABLE public.device_limits (
  limit_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  device_id uuid NOT NULL,
  parameter character varying,
  min_value numeric,
  max_value numeric,
  created_by timestamp with time zone,
  CONSTRAINT device_limits_pkey PRIMARY KEY (limit_id),
  CONSTRAINT device_limits_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id)
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
CREATE TABLE public.growth_stages (
  stage_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  stage_name character varying NOT NULL,
  stage_order integer,
  description character varying,
  CONSTRAINT growth_stages_pkey PRIMARY KEY (stage_id)
);
CREATE TABLE public.crop_cycles (
  crop_cycle_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  level_id uuid,
  current_stage_id bigint,
  crop_name character varying,
  planted_at timestamp with time zone,
  expected_harvest_at timestamp with time zone,
  status character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT crop_cycles_pkey PRIMARY KEY (crop_cycle_id),
  CONSTRAINT crop_cycles_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.levels(level_id),
  CONSTRAINT crop_cycles_current_stage_id_fkey FOREIGN KEY (current_stage_id) REFERENCES public.growth_stages(stage_id)
);
CREATE TABLE public.grow_schedules (
  schedule_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  crop_cycle_id bigint,
  name character varying,
  version integer,
  source character varying,
  is_active boolean,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT grow_schedules_pkey PRIMARY KEY (schedule_id),
  CONSTRAINT grow_schedules_crop_cycle_id_fkey FOREIGN KEY (crop_cycle_id) REFERENCES public.crop_cycles(crop_cycle_id)
);
CREATE TABLE public.schedule_targets (
  target_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  schedule_id bigint,
  stage_id bigint,
  parameter character varying,
  target_min numeric,
  target_max numeric,
  setpoint numeric,
  CONSTRAINT schedule_targets_pkey PRIMARY KEY (target_id),
  CONSTRAINT schedule_targets_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.grow_schedules(schedule_id),
  CONSTRAINT schedule_targets_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.growth_stages(stage_id)
);
CREATE TABLE public.ai_decisions (
  decision_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  crop_cycle_id bigint,
  schedule_id bigint,
  device_id uuid,
  decision_type character varying,
  risk_level character varying,
  recommended_action text,
  explanation text,
  trend_confirmed boolean,
  model_name character varying,
  status character varying,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT ai_decisions_pkey PRIMARY KEY (decision_id),
  CONSTRAINT ai_decisions_crop_cycle_id_fkey FOREIGN KEY (crop_cycle_id) REFERENCES public.crop_cycles(crop_cycle_id),
  CONSTRAINT ai_decisions_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.grow_schedules(schedule_id),
  CONSTRAINT ai_decisions_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id)
);
CREATE TABLE public.decision_evidence (
  evidence_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  decision_id bigint,
  sensor_id uuid,
  image_id bigint,
  note character varying,
  CONSTRAINT decision_evidence_pkey PRIMARY KEY (evidence_id),
  CONSTRAINT decision_evidence_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.images(image_id),
  CONSTRAINT decision_evidence_sensor_id_fkey FOREIGN KEY (sensor_id) REFERENCES public.sensor_data(id),
  CONSTRAINT decision_evidence_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.ai_decisions(decision_id)
);
CREATE TABLE public.approvals (
  approval_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  decision_id bigint,
  user_id uuid,
  action character varying,
  reason text,
  decided_at timestamp with time zone NOT NULL,
  CONSTRAINT approvals_pkey PRIMARY KEY (approval_id),
  CONSTRAINT approvals_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.ai_decisions(decision_id),
  CONSTRAINT approvals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
CREATE TABLE public.command_executions (
  command_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  decision_id bigint,
  device_id uuid,
  issued_by_user_id uuid,
  command_type character varying,
  command_value numeric,
  safety_check_passed boolean,
  status character varying,
  executed_at timestamp with time zone NOT NULL,
  CONSTRAINT command_executions_pkey PRIMARY KEY (command_id),
  CONSTRAINT command_executions_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.ai_decisions(decision_id),
  CONSTRAINT command_executions_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(device_id),
  CONSTRAINT command_executions_issued_by_user_id_fkey FOREIGN KEY (issued_by_user_id) REFERENCES public.users(user_id)
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
  CONSTRAINT alerts_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES public.ai_decisions(decision_id),
  CONSTRAINT alerts_crop_cycle_id_fkey FOREIGN KEY (crop_cycle_id) REFERENCES public.crop_cycles(crop_cycle_id),
  CONSTRAINT alerts_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES public.users(user_id)
);
CREATE TABLE public.audit_log (
  audit_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid,
  entity_type character varying,
  entity_id bigint,
  action character varying,
  details jsonb,
  created_at timestamp with time zone NOT NULL,
  CONSTRAINT audit_log_pkey PRIMARY KEY (audit_id),
  CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);