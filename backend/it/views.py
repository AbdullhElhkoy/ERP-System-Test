from django.db.models import Count, Q
from django.shortcuts import render

from employees.models import Employee
from plants.models import Plant

from .models import ITAsset, EmployeeAccount, AssetHandover, ITClearance


def it_dashboard(request):
    plant_id = request.GET.get("plant")
    plants = Plant.objects.all()

    assets_qs = ITAsset.objects.all()
    accounts_qs = EmployeeAccount.objects.all()

    if plant_id:
        assets_qs = assets_qs.filter(plant_id=plant_id)
        accounts_qs = accounts_qs.filter(plant_id=plant_id)

    total_assets = assets_qs.count()
    assigned_assets = assets_qs.filter(status="assigned").count()
    available_assets = assets_qs.filter(status="available").count()
    in_maintenance = assets_qs.filter(status="in_maintenance").count()

    total_accounts = accounts_qs.count()
    active_accounts = accounts_qs.filter(status="active").count()
    disabled_accounts = accounts_qs.filter(status="disabled").count()
    pending_accounts = accounts_qs.filter(status="pending").count()

    by_category = (
        assets_qs.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    pending_clearances = ITClearance.objects.filter(
        status=ITClearance.STATUS_PENDING
    ).select_related("employee")[:10]

    recent_handovers = AssetHandover.objects.select_related("asset", "employee")[:10]

    from datetime import date, timedelta
    upcoming_warranty = assets_qs.filter(
        warranty_end__gte=date.today(),
        warranty_end__lte=date.today() + timedelta(days=90),
    ).select_related("category")[:10]

    context = {
        "total_assets": total_assets,
        "assigned_assets": assigned_assets,
        "available_assets": available_assets,
        "in_maintenance": in_maintenance,
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "disabled_accounts": disabled_accounts,
        "pending_accounts": pending_accounts,
        "by_category": by_category,
        "pending_clearances": pending_clearances,
        "recent_handovers": recent_handovers,
        "upcoming_warranty": upcoming_warranty,
        "plants": plants,
        "selected_plant": int(plant_id) if plant_id else None,
    }
    return render(request, "it/dashboard.html", context)
