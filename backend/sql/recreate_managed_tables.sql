-- Recreate all managed=False tables (plants + employees)
-- These are NOT created by Django migrations (managed=False)

DROP TABLE IF EXISTS employee_assignments, employees, rotation_reference, shift_rotation_pattern, shift_groups, shift_types, org_position_department_scope, org_positions, department_plant_scope, departments, roles, plants CASCADE;

-- Plants tables
CREATE TABLE plants (
    plant_id SERIAL PRIMARY KEY,
    plant_name VARCHAR(50) UNIQUE NOT NULL,
    product_type VARCHAR(50) DEFAULT ''
);

CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    department_code VARCHAR(20) UNIQUE NOT NULL,
    department_name VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(20) DEFAULT '',
    parent_department_id INT REFERENCES departments(department_id)
);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE department_plant_scope (
    id SERIAL PRIMARY KEY,
    department_id INT NOT NULL REFERENCES departments(department_id),
    plant_id INT NOT NULL REFERENCES plants(plant_id),
    UNIQUE(department_id, plant_id)
);

CREATE TABLE org_positions (
    position_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(10) NOT NULL,
    plant_id INT REFERENCES plants(plant_id),
    department_id INT REFERENCES departments(department_id),
    role_id INT NOT NULL REFERENCES roles(role_id),
    hierarchy_level INT NOT NULL
);

CREATE TABLE org_position_department_scope (
    id SERIAL PRIMARY KEY,
    position_id INT NOT NULL REFERENCES org_positions(position_id),
    department_id INT NOT NULL REFERENCES departments(department_id),
    UNIQUE(position_id, department_id)
);

-- Employees tables
CREATE TABLE shift_types (
    shift_type_id SERIAL PRIMARY KEY,
    shift_type_name VARCHAR(20) UNIQUE NOT NULL,
    start_time TIME,
    end_time TIME
);

CREATE TABLE shift_groups (
    group_id SERIAL PRIMARY KEY,
    group_name VARCHAR(5) UNIQUE NOT NULL
);

CREATE TABLE shift_rotation_pattern (
    id BIGSERIAL PRIMARY KEY,
    group_id INT NOT NULL REFERENCES shift_groups(group_id),
    day_offset INT NOT NULL,
    shift_type_id INT NOT NULL REFERENCES shift_types(shift_type_id),
    UNIQUE(group_id, day_offset)
);

CREATE TABLE rotation_reference (
    id BIGSERIAL PRIMARY KEY,
    reference_date DATE NOT NULL
);

CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    national_id VARCHAR(20) UNIQUE,
    phone VARCHAR(20),
    hire_date DATE,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE employee_assignments (
    assignment_id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(employee_id),
    position_id INT NOT NULL REFERENCES org_positions(position_id),
    shift_mode VARCHAR(10) NOT NULL,
    group_id INT REFERENCES shift_groups(group_id),
    fixed_shift_type_id INT REFERENCES shift_types(shift_type_id),
    start_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN DEFAULT true
);

-- Seed minimal data
INSERT INTO shift_types (shift_type_name, start_time, end_time) VALUES
    ('First', '08:00', '16:00'),
    ('Second', '16:00', '00:00'),
    ('Third', '00:00', '08:00'),
    ('Off', NULL, NULL);

INSERT INTO shift_groups (group_name) VALUES ('A'), ('B'), ('C'), ('D');

INSERT INTO rotation_reference (reference_date) VALUES ('2026-01-01');

INSERT INTO departments (department_name, department_code, category) VALUES
    ('QC Lab', 'QC_LAB', 'lab'),
    ('Production Floor', 'PROD_FLOOR', 'production');

INSERT INTO plants (plant_name, product_type) VALUES ('Plant A', 'cement');

INSERT INTO department_plant_scope (department_id, plant_id)
    SELECT d.department_id, p.plant_id FROM departments d, plants p;
