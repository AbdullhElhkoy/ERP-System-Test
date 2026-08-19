from django.contrib import admin
from django.db.models import Count, Q
from django.shortcuts import render

from employees.models import Employee
from plants.models import Plant, Department

from .models import (
    HREmployeeProfile, Attendance, Leave, Contract, Discipline, Training,
)


def hr_dashboard(request):
    plant_id = request.GET.get("plant")
    plants = Plant.objects.all()

    employees_qs = Employee.objects.filter(is_active=True)
    all_employees = Employee.objects.all()

    if plant_id:
        employees_qs = employees_qs.filter(hr_profile__plant_id=plant_id)
        all_employees = all_employees.filter(hr_profile__plant_id=plant_id)

    total = all_employees.count()
    active = employees_qs.count()
    on_leave = all_employees.filter(hr_profile__status="on_leave").count()
    terminated = all_employees.filter(hr_profile__status="terminated").count()

    by_plant = (
        HREmployeeProfile.objects.values("plant__plant_name")
        .annotate(count=Count("employee"))
        .order_by("-count")
    )

    by_department = (
        HREmployeeProfile.objects.values("department__department_name")
        .annotate(count=Count("employee"))
        .order_by("-count")
    )

    from datetime import date, timedelta
    upcoming_contracts = Contract.objects.filter(
        end_date__gte=date.today(),
        end_date__lte=date.today() + timedelta(days=30),
        status="active",
    ).select_related("employee")[:10]

    recent_disciplines = Discipline.objects.select_related("employee")[:5]
    recent_trainings = Training.objects.select_related("employee")[:5]

    from django.contrib.auth import get_user_model
    User = get_user_model()

    context = {
        "total_employees": total,
        "active_employees": active,
        "on_leave": on_leave,
        "terminated": terminated,
        "by_plant": by_plant,
        "by_department": by_department,
        "upcoming_contracts": upcoming_contracts,
        "recent_disciplines": recent_disciplines,
        "recent_trainings": recent_trainings,
        "plants": plants,
        "selected_plant": int(plant_id) if plant_id else None,
    }
    return render(request, "hr/dashboard.html", context)
