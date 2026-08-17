-- Phase 1: Organizational Data — Departments + DepartmentPlantScope
-- Run this in the Codespace: psql -U chemflow_user -d chemflow_db -f backend/sql/phase1_org_data.sql

-- Lab departments
INSERT INTO departments (department_code, department_name, category)
VALUES
    ('LAB', 'Laboratory', 'lab'),
    ('LAB-CHEM', 'Chemical Lab', 'lab')
ON CONFLICT (department_code) DO NOTHING;

-- QC departments
INSERT INTO departments (department_code, department_name, category)
VALUES
    ('QC', 'Quality Control', 'qc'),
    ('QC-FINAL', 'Final QC', 'qc')
ON CONFLICT (department_code) DO NOTHING;

-- Link all lab/qc departments to all plants
INSERT INTO department_plant_scope (department_id, plant_id)
SELECT d.department_id, p.plant_id
FROM departments d
CROSS JOIN plants p
WHERE d.category IN ('lab', 'qc')
ON CONFLICT (department_id, plant_id) DO NOTHING;
