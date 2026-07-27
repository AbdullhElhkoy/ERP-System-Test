-- =========================================================
-- ChemFlow ERP - Incremental Migration v2
-- بيضيف بس الجديد فوق البيانات الموجودة، من غير ما يمسح أو يكرر حاجة
-- آمن للتشغيل على قاعدة chemflow_erp اللي فيها بيانات حقيقية بالفعل
-- =========================================================

-- 1) إضافة الأدوار الجديدة (لو مش موجودة أصلاً، يتجاهل بهدوء)
INSERT INTO roles (role_name) VALUES
    ('QC Specialist'),
    ('Technician')
ON CONFLICT (role_name) DO NOTHING;

-- 2) إضافة إدارة الميزان الجديدة
INSERT INTO departments (department_code, department_name) VALUES
    ('SCALE', 'Scale Department')
ON CONFLICT (department_name) DO NOTHING;

-- 3) ربط إدارة الميزان بكل الـ 12 مصنع
INSERT INTO department_plant_scope (department_id, plant_id)
SELECT d.department_id, p.plant_id
FROM departments d
CROSS JOIN plants p
WHERE d.department_name = 'Scale Department'
ON CONFLICT (department_id, plant_id) DO NOTHING;

-- 4) إضافة "Technician" كمستوى 6 في كل المصانع (12 مصنع)
INSERT INTO org_positions (entity_type, plant_id, role_id, hierarchy_level)
SELECT 'plant', p.plant_id, r.role_id, 6
FROM plants p
JOIN roles r ON r.role_name = 'Technician'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 5) إضافة "QC Specialist" (مستوى 6) و"Technician" (مستوى 7) في QA وQC
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

-- 6) إضافة "Technician" (مستوى 6) في Lab SOP, Lab ECHPS, Warehouse
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, 6
FROM departments d
JOIN roles r ON r.role_name = 'Technician'
WHERE d.department_name IN ('Lab SOP', 'Lab ECHPS', 'Warehouse')
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 7) إضافة "Technician" (مستوى 5) في Sales
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, 5
FROM departments d
JOIN roles r ON r.role_name = 'Technician'
WHERE d.department_name = 'Sales'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- 8) بناء هيكل إدارة الميزان الجديدة بالكامل (5 مستويات)
INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES
    (1, 'مدير الإدارة'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'مشرف'),
    (5, 'Technician')
) AS v(hierarchy_level, role_name)
JOIN roles r ON r.role_name = v.role_name
WHERE d.department_name = 'Scale Department'
ON CONFLICT (entity_type, plant_id, department_id, role_id) DO NOTHING;

-- =========================================================
-- التحقق النهائي بعد التنفيذ
-- =========================================================
-- شغّل الاستعلامات دي بعد ما تنفذ الملف عشان تتأكد:

-- SELECT COUNT(*) FROM roles;              -- المفروض يبقى 13 (11 القديمة + 2 جديدة)
-- SELECT COUNT(*) FROM departments;         -- المفروض يبقى 7 (6 القديمة + Scale Department)
-- SELECT COUNT(*) FROM org_positions;       -- المفروض يزيد عن 89 بعدد الوظائف الجديدة
