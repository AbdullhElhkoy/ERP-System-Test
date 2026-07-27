from plants.models import Plant, OrgPosition, DepartmentPlantScope


def get_user_position(user):
    """
    يرجّع المنصب التنظيمي بتاع المستخدم، أو None لو مالوش منصب أو مالوش profile خالص.
    """
    profile = getattr(user, "profile", None)
    if not profile or not profile.org_position:
        return None
    return profile.org_position


def get_editable_plant_ids(user):
    """
    نطاق التعديل (Write): المصانع اللي المستخدم يقدر يعدّل بياناتها.
    - منصب تابع لمصنع مباشرة -> مصنعه بس
    - منصب تابع لإدارة مركزية -> كل المصانع اللي الإدارة دي بتخدمها (department_plant_scope)
    - مفيش منصب خالص -> مفيش صلاحية تعديل على أي مصنع
    """
    position = get_user_position(user)
    if not position:
        return Plant.objects.none()

    if position.entity_type == "plant" and position.plant:
        return Plant.objects.filter(plant_id=position.plant_id)

    if position.entity_type == "department" and position.department:
        scoped_plant_ids = DepartmentPlantScope.objects.filter(
            department=position.department
        ).values_list("plant_id", flat=True)
        return Plant.objects.filter(plant_id__in=scoped_plant_ids)

    return Plant.objects.none()


def get_viewable_plant_ids(user):
    """
    نطاق المشاهدة (Read): المصانع اللي المستخدم يقدر يشوف بياناتها بس مش يعدّلها.
    - منصب تابع لمصنع -> كل مصانع نفس الـ Phase بتاعته
    - منصب تابع لإدارة مركزية -> كل المصانع اللي بتخدمها (نفس نطاق التعديل)
    - مفيش منصب خالص -> مفيش مشاهدة لأي مصنع
    """
    position = get_user_position(user)
    if not position:
        return Plant.objects.none()

    if position.entity_type == "plant" and position.plant:
        plant_phase = position.plant.phase
        if plant_phase is None:
            return Plant.objects.filter(plant_id=position.plant_id)
        return Plant.objects.filter(phase=plant_phase)

    if position.entity_type == "department" and position.department:
        scoped_plant_ids = DepartmentPlantScope.objects.filter(
            department=position.department
        ).values_list("plant_id", flat=True)
        return Plant.objects.filter(plant_id__in=scoped_plant_ids)

    return Plant.objects.none()


def can_view_plant(user, plant_id):
    """اختصار سريع: هل المستخدم يقدر يشوف بيانات المصنع ده؟"""
    return get_viewable_plant_ids(user).filter(plant_id=plant_id).exists()


def can_edit_plant(user, plant_id):
    """اختصار سريع: هل المستخدم يقدر يعدّل بيانات المصنع ده؟"""
    return get_editable_plant_ids(user).filter(plant_id=plant_id).exists()