from django.db.models import Prefetch
from plants.models import OrgPosition, Role

from .models import Screen, ScreenColumn, ColumnPermission


def get_user_role(user):
    """Return the user's Role via their OrgPosition, or None."""
    profile = getattr(user, "profile", None)
    if not profile:
        return None
    position = getattr(profile, "org_position", None)
    if not position:
        return None
    return getattr(position, "role", None)


def get_screen_permissions(user, screen_code):
    """
    Return {column_code: 'hidden'|'view'|'edit'} for the given screen.

    Rules:
    - superuser → all 'edit'
    - no role → all 'hidden'
    - column has no ColumnPermission for this role → 'hidden' (fail-closed)
    """
    if user.is_superuser:
        cols = ScreenColumn.objects.filter(screen__code=screen_code)
        return {c.code: ColumnPermission.LEVEL_EDIT for c in cols}

    role = get_user_role(user)
    if not role:
        cols = ScreenColumn.objects.filter(screen__code=screen_code)
        return {c.code: ColumnPermission.LEVEL_HIDDEN for c in cols}

    perms = ColumnPermission.objects.filter(
        column__screen__code=screen_code,
        role=role,
    ).select_related("column")

    perm_map = {p.column.code: p.level for p in perms}

    cols = ScreenColumn.objects.filter(screen__code=screen_code)
    return {c.code: perm_map.get(c.code, ColumnPermission.LEVEL_HIDDEN) for c in cols}


def can_edit_column(user, screen_code, column_code):
    """Quick check: can the user edit this specific column?"""
    perms = get_screen_permissions(user, screen_code)
    return perms.get(column_code) == ColumnPermission.LEVEL_EDIT


def can_view_column(user, screen_code, column_code):
    """Quick check: can the user at least view this column?"""
    perms = get_screen_permissions(user, screen_code)
    return perms.get(column_code) in (ColumnPermission.LEVEL_VIEW, ColumnPermission.LEVEL_EDIT)
