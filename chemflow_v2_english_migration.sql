-- =========================================================
-- ChemFlow ERP - Full English Translation + Incremental Migration v2
-- =========================================================

-- =========================================================
-- PART 1: ترجمة الأدوار الموجودة بالفعل من عربي لإنجليزي
-- (UPDATE بسيط - بيغيّر الاسم بس، نفس الـ ID، نفس الروابط،
--  مش هيأثر على أي وظيفة أو موظف مرتبط بيهم)
-- =========================================================

UPDATE roles SET role_name = 'Production Manager'    WHERE role_name = 'مدير إنتاج';
UPDATE roles SET role_name = 'Section Head'           WHERE role_name = 'رئيس قسم';
UPDATE roles SET role_name = 'Shift Leader'           WHERE role_name = 'رئيس وردية';
UPDATE roles SET role_name = 'Chemist'                WHERE role_name = 'الكيميائي';
UPDATE roles SET role_name = 'Supervisor'             WHERE role_name = 'مشرف';
UPDATE roles SET role_name = 'Department Manager'     WHERE role_name = 'مدير الإدارة';
UPDATE roles SET role_name = 'Lab Manager'            WHERE role_name = 'مدير المعمل';
UPDATE roles SET role_name = 'Warehouse Manager'      WHERE role_name = 'مدير المخازن';
UPDATE roles SET role_name = 'Storekeeper'            WHERE role_name = 'أمين مخزن';
UPDATE roles SET role_name = 'Sales Manager'          WHERE role_name = 'مدير المبيعات';
UPDATE roles SET role_name = 'Responsible Engineer'   WHERE role_name = 'مهندس مسؤول';

-- تحقق سريع: المفروض الاستعلام ده يرجّع صفر صفوف (يعني مفيش عربي متبقي)
-- SELECT * FROM roles WHERE role_name ~ '[\u0600-\u06FF]';

-- =========================================================
-- PART 2: Incremental Migration v2 (English only)
-- Adds only what's new, safe to run on existing data
-- =========================================================

-- 1) Add new roles (skipped quietly if they already exist)
INSERT INTO roles (role_name) VALUES
    ('QC Specialist'),
    ('Technician')
ON CONFLICT (role_name) DO NOTHING;

-- 2) Add the new Scale Department
INSERT INTO departments (department_code, department_name) VALUES
    ('SCALE', 'Scale Department')
ON CONFLICT (department_name) DO NOTHING;

-- 3) Link Scale Department to all 12 plants
INSERT INTO department_plant_scope (department_id, plant_id)
SELECT d.department_id, p.plant_id
FROM departments d
CROSS JOIN plants p
WHERE d.department_name = 'Scale Department'
ON CONFLICT (department_id, plant_id) DO NOTHING;

-- 4) Add "Technician" as level 6 in every plant (12 plants)
INSERT INTO org_positions (entity_type, plant_id, role_id, hierarchy_level)
SELECT 'plant', p.plant_id, r.role_id, 6
FROM plants p
JOIN roles r ON r.role_name = 'Technician'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 5) Add "QC Specialist" (level 6) and "Technician" (level 7) in QA and QC
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES
    (6, 'QC Specialist'),
    (7, 'Technician')
) AS v(hierarchy_level, role_name)
JOIN roles r ON r.role_name = v.role_name
WHERE d.department_name IN ('QA', 'QC')
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 6) Add "Technician" (level 6) in Lab SOP, Lab ECHPS, Warehouse
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, 6
FROM departments d
JOIN roles r ON r.role_name = 'Technician'
WHERE d.department_name IN ('Lab SOP', 'Lab ECHPS', 'Warehouse')
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 7) Add "Technician" (level 5) in Sales
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, 5
FROM departments d
JOIN roles r ON r.role_name = 'Technician'
WHERE d.department_name = 'Sales'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 8) Build the full Scale Department hierarchy (5 levels)
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES
    (1, 'Department Manager'),
    (2, 'Section Head'),
    (3, 'Shift Leader'),
    (4, 'Supervisor'),
    (5, 'Technician')
) AS v(hierarchy_level, role_name)
JOIN roles r ON r.role_name = v.role_name
WHERE d.department_name = 'Scale Department'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- =========================================================
-- Final verification - run these after executing the script
-- =========================================================
-- SELECT * FROM roles ORDER BY role_id;      -- expect 13 rows, all in English
-- SELECT COUNT(*) FROM departments;           -- expect 7 (6 original + Scale Department)
-- SELECT COUNT(*) FROM org_positions;         -- expect more than 89
