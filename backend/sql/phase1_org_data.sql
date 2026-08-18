-- Phase 1: Organizational Data — Departments + DepartmentPlantScope
-- Run in Codespace: PGPASSWORD='ChemFlowSecure2026!!' psql -h localhost -U chemflow_user -d chemflow_db -f sql/phase1_org_data.sql

-- Ensure category column exists on departments (managed=False table)
ALTER TABLE departments ADD COLUMN IF NOT EXISTS category VARCHAR(20);

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

-- Update category for any existing rows that might be missing it
UPDATE departments SET category = 'lab' WHERE department_code IN ('LAB', 'LAB-CHEM') AND category IS NULL;
UPDATE departments SET category = 'qc' WHERE department_code IN ('QC', 'QC-FINAL') AND category IS NULL;

-- Link all lab/qc departments to all plants
INSERT INTO department_plant_scope (department_id, plant_id)
SELECT d.department_id, p.plant_id
FROM departments d
CROSS JOIN plants p
WHERE d.category IN ('lab', 'qc')
ON CONFLICT (department_id, plant_id) DO NOTHING;
