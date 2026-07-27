
-- =========================================================
-- ChemFlow ERP - Organizational Structure Schema
-- PostgreSQL
-- =========================================================

-- 1) المصانع
CREATE TABLE plants (
    plant_id    SERIAL PRIMARY KEY,
    plant_code  VARCHAR(20) NOT NULL UNIQUE,
    plant_name  VARCHAR(50) NOT NULL UNIQUE
);

-- 2) الإدارات المركزية (تخدم أكتر من مصنع)
CREATE TABLE departments (
    department_id   SERIAL PRIMARY KEY,
    department_code VARCHAR(20) NOT NULL UNIQUE,
    department_name VARCHAR(50) NOT NULL UNIQUE
);

-- 3) الأدوار الوظيفية الفريدة (Master Roles)
CREATE TABLE roles (
    role_id    SERIAL PRIMARY KEY,
    role_name  VARCHAR(50) NOT NULL UNIQUE
);

-- 4) نطاق تغطية كل إدارة مركزية (أي إدارة بتخدم أي مصانع) - علاقة Many-to-Many
CREATE TABLE department_plant_scope (
    department_id INT NOT NULL REFERENCES departments(department_id) ON DELETE CASCADE,
    plant_id      INT NOT NULL REFERENCES plants(plant_id) ON DELETE CASCADE,
    PRIMARY KEY (department_id, plant_id)
);

-- 5) الوظائف الفعلية (Positions/Slots) - كل صف = وظيفة موجودة في مصنع أو إدارة
--    entity_type بيحدد هل الوظيفة دي تابعة لمصنع ولا لإدارة مركزية
CREATE TABLE org_positions (
    position_id    SERIAL PRIMARY KEY,
    entity_type    VARCHAR(10) NOT NULL CHECK (entity_type IN ('plant', 'department')),
    plant_id       INT REFERENCES plants(plant_id) ON DELETE CASCADE,
    department_id  INT REFERENCES departments(department_id) ON DELETE CASCADE,
    role_id        INT NOT NULL REFERENCES roles(role_id),
    hierarchy_level INT NOT NULL,

    -- تأكيد إن الوظيفة تابعة لمصنع أو لإدارة، مش الاتنين ولا ولا واحد
    CONSTRAINT chk_entity_link CHECK (
        (entity_type = 'plant' AND plant_id IS NOT NULL AND department_id IS NULL)
        OR
        (entity_type = 'department' AND department_id IS NOT NULL AND plant_id IS NULL)
    ),
    -- منع تكرار نفس الدور مرتين في نفس المصنع/الإدارة
    UNIQUE (entity_type, plant_id, department_id, role_id)
);

-- 6) أنواع الورديات (نهاري / أولى / ثانية / ثالثة / إجازة)
CREATE TABLE shift_types (
    shift_type_id   SERIAL PRIMARY KEY,
    shift_type_name VARCHAR(20) NOT NULL UNIQUE,
    start_time      TIME,   -- NULL للإجازة (مفيش وقت بداية)
    end_time        TIME    -- NULL للإجازة
);

-- 7) مجموعات التدوير (A, B, C, D) - نظام موحّد لكل الشركة
CREATE TABLE shift_groups (
    group_id   SERIAL PRIMARY KEY,
    group_name VARCHAR(5) NOT NULL UNIQUE
);

-- 8) دورة الـ 8 أيام: أي مجموعة شغالة في أنهي وردية في أنهي يوم من الدورة
--    day_offset من 0 لـ 7 (8 أيام دورة كاملة: يومين لكل وردية + يومين إجازة)
CREATE TABLE shift_rotation_pattern (
    group_id      INT NOT NULL REFERENCES shift_groups(group_id) ON DELETE CASCADE,
    day_offset    INT NOT NULL CHECK (day_offset BETWEEN 0 AND 7),
    shift_type_id INT NOT NULL REFERENCES shift_types(shift_type_id),
    PRIMARY KEY (group_id, day_offset)
);

-- 9) تاريخ "يوم صفر" المرجعي - نظام موحّد واحد للشركة كلها
--    بنحسب منه: day_offset = (التاريخ الحالي - reference_date) mod 8
CREATE TABLE rotation_reference (
    reference_date DATE NOT NULL
);

-- 7) الموظفين
CREATE TABLE employees (
    employee_id  SERIAL PRIMARY KEY,
    full_name    VARCHAR(100) NOT NULL,
    national_id  VARCHAR(20) UNIQUE,
    phone        VARCHAR(20),
    hire_date    DATE,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

-- 10) تعيين الموظف على وظيفة معينة (ده اللي بيربط كل حاجة ببعض)
--     shift_mode بيحدد هل الموظف "نهاري ثابت" أو "مدوّر على مجموعة"
--     لو rotating: بنسجل group_id بس، والوردية الفعلية بتتحسب يوم بيوم من الدورة
--     لو fixed: بنسجل fixed_shift_type_id (هيكون دايمًا = نهاري)
CREATE TABLE employee_assignments (
    assignment_id       SERIAL PRIMARY KEY,
    employee_id         INT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    position_id         INT NOT NULL REFERENCES org_positions(position_id) ON DELETE CASCADE,
    shift_mode          VARCHAR(10) NOT NULL CHECK (shift_mode IN ('rotating', 'fixed')),
    group_id            INT REFERENCES shift_groups(group_id),
    fixed_shift_type_id INT REFERENCES shift_types(shift_type_id),
    start_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date            DATE,
    is_current          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT chk_shift_mode_link CHECK (
        (shift_mode = 'rotating' AND group_id IS NOT NULL AND fixed_shift_type_id IS NULL)
        OR
        (shift_mode = 'fixed' AND fixed_shift_type_id IS NOT NULL AND group_id IS NULL)
    )
);

-- إندكسات لتسريع أكتر استعلامات هتتكرر
CREATE INDEX idx_positions_plant ON org_positions(plant_id);
CREATE INDEX idx_positions_department ON org_positions(department_id);
CREATE INDEX idx_assignments_employee ON employee_assignments(employee_id);
CREATE INDEX idx_assignments_position ON employee_assignments(position_id);

-- =========================================================
-- Function: حساب وردية أي مجموعة في أي تاريخ
-- بتحسب day_offset من تاريخ المرجع، وترجع نوع الوردية
-- =========================================================
CREATE OR REPLACE FUNCTION get_group_shift(p_group_name VARCHAR, p_date DATE)
RETURNS VARCHAR AS $$
DECLARE
    v_offset INT;
    v_shift_name VARCHAR;
    v_ref_date DATE;
BEGIN
    SELECT reference_date INTO v_ref_date FROM rotation_reference LIMIT 1;

    v_offset := MOD((p_date - v_ref_date)::INT, 8);
    IF v_offset < 0 THEN
        v_offset := v_offset + 8;
    END IF;

    SELECT st.shift_type_name INTO v_shift_name
    FROM shift_rotation_pattern srp
    JOIN shift_groups sg ON sg.group_id = srp.group_id
    JOIN shift_types st ON st.shift_type_id = srp.shift_type_id
    WHERE sg.group_name = p_group_name AND srp.day_offset = v_offset;

    RETURN v_shift_name;
END;
$$ LANGUAGE plpgsql;

-- =========================================================
-- View: وردية كل موظف "مدوّر" في تاريخ النهاردة
-- (الموظفين "الثابتين/نهاري" مش محتاجين حساب، ورديتهم معروفة دايمًا)
-- =========================================================
CREATE OR REPLACE VIEW v_today_shift_rotating AS
SELECT
    e.employee_id,
    e.full_name,
    sg.group_name,
    get_group_shift(sg.group_name, CURRENT_DATE) AS today_shift
FROM employee_assignments ea
JOIN employees e ON e.employee_id = ea.employee_id
JOIN shift_groups sg ON sg.group_id = ea.group_id
WHERE ea.shift_mode = 'rotating' AND ea.is_current = TRUE;


-- =========================================================
-- Seed Data: roles
-- =========================================================

INSERT INTO roles (role_name) VALUES
    ('مدير إنتاج'),
    ('رئيس قسم'),
    ('رئيس وردية'),
    ('الكيميائي'),
    ('مشرف'),
    ('مدير الإدارة'),
    ('مدير المعمل'),
    ('مدير المخازن'),
    ('أمين مخزن'),
    ('مدير المبيعات'),
    ('مهندس مسؤول');

-- Seed Data: plants

INSERT INTO plants (plant_code, plant_name) VALUES
    ('DCP', 'DCP'),
    ('GCC1', 'GCC1'),
    ('GCC2', 'GCC2'),
    ('PA', 'PA'),
    ('SA200', 'SA 200'),
    ('SA600', 'SA 600'),
    ('SOPA', 'SOP A'),
    ('SOPB', 'SOP B'),
    ('SOPC', 'SOP C'),
    ('SOPD', 'SOP D'),
    ('SOPH', 'SOP H'),
    ('GSOP', 'G SOP');

-- Seed Data: departments

INSERT INTO departments (department_code, department_name) VALUES
    ('QA', 'QA'),
    ('QC', 'QC'),
    ('LAB_SOP', 'Lab SOP'),
    ('LAB_ECHPS', 'Lab ECHPS'),
    ('WH', 'Warehouse'),
    ('SALES', 'Sales');

-- Seed Data: department_plant_scope (أي إدارة بتخدم أي مصانع)

INSERT INTO department_plant_scope (department_id, plant_id)
SELECT d.department_id, p.plant_id
FROM departments d
JOIN plants p ON p.plant_name = ANY (
    CASE d.department_name

        WHEN 'QA' THEN ARRAY['DCP', 'GCC1', 'GCC2', 'PA', 'SA 200', 'SA 600', 'SOP A', 'SOP B', 'SOP C', 'SOP D', 'SOP H', 'G SOP']

        WHEN 'QC' THEN ARRAY['DCP', 'GCC1', 'GCC2', 'PA', 'SA 200', 'SA 600', 'SOP A', 'SOP B', 'SOP C', 'SOP D', 'SOP H', 'G SOP']

        WHEN 'Warehouse' THEN ARRAY['DCP', 'GCC1', 'GCC2', 'PA', 'SA 200', 'SA 600', 'SOP A', 'SOP B', 'SOP C', 'SOP D', 'SOP H', 'G SOP']

        WHEN 'Sales' THEN ARRAY['DCP', 'GCC1', 'GCC2', 'PA', 'SA 200', 'SA 600', 'SOP A', 'SOP B', 'SOP C', 'SOP D', 'SOP H', 'G SOP']

        WHEN 'Lab SOP' THEN ARRAY['SA 200', 'SA 600', 'SOP A', 'SOP B', 'SOP C', 'SOP D', 'SOP H', 'G SOP']

        WHEN 'Lab ECHPS' THEN ARRAY['DCP', 'GCC1', 'GCC2', 'PA']

    END
);

-- Seed Data: org_positions - وظائف المصانع (12 مصنع x 5 مستويات)

INSERT INTO org_positions (entity_type, plant_id, role_id, hierarchy_level)
SELECT 'plant', p.plant_id, r.role_id, v.hierarchy_level
FROM plants p
CROSS JOIN (VALUES

    (1, 'مدير إنتاج'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'الكيميائي'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name;

-- Seed Data: org_positions - وظائف الإدارات المركزية (لكل إدارة مستوياتها الخاصة)

-- QA

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير الإدارة'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'الكيميائي'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'QA';


-- QC

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير الإدارة'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'الكيميائي'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'QC';


-- Lab SOP

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير المعمل'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'الكيميائي'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'Lab SOP';


-- Lab ECHPS

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير المعمل'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'الكيميائي'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'Lab ECHPS';


-- Warehouse

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير المخازن'),
    (2, 'رئيس قسم'),
    (3, 'رئيس وردية'),
    (4, 'أمين مخزن'),
    (5, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'Warehouse';


-- Sales

INSERT INTO org_positions (entity_type, department_id, role_id, hierarchy_level)
SELECT 'department', d.department_id, r.role_id, v.hierarchy_level
FROM departments d
CROSS JOIN (VALUES

    (1, 'مدير المبيعات'),
    (2, 'رئيس قسم'),
    (3, 'مهندس مسؤول'),
    (4, 'مشرف')
) AS v(hierarchy_level, role_name)

JOIN roles r ON r.role_name = v.role_name

WHERE d.department_name = 'Sales';


-- Seed Data: shift_types (أنواع الورديات)

INSERT INTO shift_types (shift_type_name, start_time, end_time) VALUES
    ('نهاري', '08:00', '16:00'),
    ('أولى', '08:00', '16:00'),
    ('ثانية', '16:00', '00:00'),
    ('ثالثة', '00:00', '08:00'),
    ('إجازة', NULL, NULL);

-- Seed Data: shift_groups (المجموعات الأربعة)

INSERT INTO shift_groups (group_name) VALUES
    ('A'), ('B'), ('C'), ('D');

-- Seed Data: shift_rotation_pattern (دورة الـ 8 أيام لكل مجموعة)

INSERT INTO shift_rotation_pattern (group_id, day_offset, shift_type_id)
SELECT sg.group_id, v.day_offset, st.shift_type_id
FROM shift_groups sg
JOIN (VALUES

    ('A', 0, 'ثانية'),
    ('A', 1, 'ثانية'),
    ('A', 2, 'ثالثة'),
    ('A', 3, 'ثالثة'),
    ('A', 4, 'إجازة'),
    ('A', 5, 'إجازة'),
    ('A', 6, 'أولى'),
    ('A', 7, 'أولى'),
    ('B', 0, 'ثالثة'),
    ('B', 1, 'ثالثة'),
    ('B', 2, 'إجازة'),
    ('B', 3, 'إجازة'),
    ('B', 4, 'أولى'),
    ('B', 5, 'أولى'),
    ('B', 6, 'ثانية'),
    ('B', 7, 'ثانية'),
    ('C', 0, 'أولى'),
    ('C', 1, 'أولى'),
    ('C', 2, 'ثانية'),
    ('C', 3, 'ثانية'),
    ('C', 4, 'ثالثة'),
    ('C', 5, 'ثالثة'),
    ('C', 6, 'إجازة'),
    ('C', 7, 'إجازة'),
    ('D', 0, 'إجازة'),
    ('D', 1, 'إجازة'),
    ('D', 2, 'أولى'),
    ('D', 3, 'أولى'),
    ('D', 4, 'ثانية'),
    ('D', 5, 'ثانية'),
    ('D', 6, 'ثالثة'),
    ('D', 7, 'ثالثة')
) AS v(group_name, day_offset, shift_type_name) ON v.group_name = sg.group_name

JOIN shift_types st ON st.shift_type_name = v.shift_type_name;

-- Seed Data: rotation_reference (تاريخ يوم صفر - عدّله ليوم فعلي تعرف فيه بداية دورة المجموعة A من أولى)

INSERT INTO rotation_reference (reference_date) VALUES ('2026-07-20');
