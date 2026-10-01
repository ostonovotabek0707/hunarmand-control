CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  parent_id UUID REFERENCES organizations(id),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE regions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  code TEXT UNIQUE NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE districts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  region_id UUID NOT NULL REFERENCES regions(id),
  name TEXT NOT NULL,
  code TEXT UNIQUE NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE departments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  district_id UUID NOT NULL REFERENCES districts(id),
  name TEXT NOT NULL,
  code TEXT UNIQUE NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone TEXT UNIQUE NOT NULL,
  role_id UUID NOT NULL REFERENCES roles(id),
  organization_id UUID REFERENCES organizations(id),
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deactivated_at TIMESTAMPTZ
);

CREATE TABLE employee_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  full_name TEXT NOT NULL,
  position TEXT,
  employee_number TEXT UNIQUE,
  department_id UUID REFERENCES departments(id),
  hire_date DATE
);

CREATE TABLE devices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  device_uuid TEXT NOT NULL UNIQUE,
  manufacturer TEXT,
  model TEXT,
  os_version TEXT,
  app_version TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ
);

CREATE TABLE monthly_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_number TEXT UNIQUE NOT NULL,
  year INT NOT NULL,
  month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
  organization_id UUID REFERENCES organizations(id),
  status TEXT NOT NULL DEFAULT 'DRAFT',
  created_by UUID REFERENCES users(id),
  published_by UUID REFERENCES users(id),
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(year, month, organization_id)
);

CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_number TEXT UNIQUE NOT NULL,
  plan_id UUID REFERENCES monthly_plans(id),
  title TEXT NOT NULL,
  description TEXT,
  priority TEXT NOT NULL DEFAULT 'NORMAL',
  task_type TEXT NOT NULL DEFAULT 'MIXED',
  start_date DATE,
  deadline DATE,
  status TEXT NOT NULL DEFAULT 'NEW',
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  cancelled_at TIMESTAMPTZ,
  cancel_reason TEXT
);

CREATE TABLE task_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id),
  employee_id UUID NOT NULL REFERENCES users(id),
  assignment_role TEXT NOT NULL DEFAULT 'EXECUTOR',
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  accepted_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE TABLE task_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id),
  submitted_by UUID NOT NULL REFERENCES users(id),
  text_result TEXT,
  numeric_result NUMERIC,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_by UUID REFERENCES users(id),
  reviewed_at TIMESTAMPTZ,
  review_status TEXT NOT NULL DEFAULT 'UNDER_REVIEW',
  return_reason TEXT
);

CREATE TABLE attendance_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_uuid UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES users(id),
  device_id UUID REFERENCES devices(id),
  event_type TEXT NOT NULL,
  server_time TIMESTAMPTZ NOT NULL DEFAULT now(),
  device_time TIMESTAMPTZ,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  accuracy_m DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE gps_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES users(id),
  attendance_start_event UUID REFERENCES attendance_events(id),
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE gps_points (
  id BIGSERIAL PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES gps_sessions(id),
  employee_id UUID NOT NULL REFERENCES users(id),
  recorded_at TIMESTAMPTZ NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  accuracy_m DOUBLE PRECISION,
  speed_mps DOUBLE PRECISION,
  battery_level SMALLINT,
  provider TEXT,
  mock_location BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX gps_points_employee_time_idx ON gps_points(employee_id, recorded_at);
CREATE INDEX gps_points_session_time_idx ON gps_points(session_id, recorded_at);

CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY,
  actor_user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID,
  old_data JSONB,
  new_data JSONB,
  ip_address INET,
  device_id UUID REFERENCES devices(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO roles(name) VALUES
('SUPER_ADMIN'),('REGIONAL_HEAD'),('REGIONAL_MANAGER'),('DISTRICT_HEAD'),('EMPLOYEE')
ON CONFLICT DO NOTHING;
