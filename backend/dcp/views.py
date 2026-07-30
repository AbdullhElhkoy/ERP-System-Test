import math
from django.http import JsonResponse
from .models import FinalProductSiloReading, FinalProductSampleLot


def next_sequence_preview(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized access"}, status=401)

    plant_id = request.GET.get("plant_id")
    weight = request.GET.get("weight")
    silo = request.GET.get("silo", "").upper()

    if not plant_id or not weight:
        return JsonResponse({"error": "missing params"}, status=400)

    try:
        weight_num = int(float(weight))
    except ValueError:
        return JsonResponse({"error": "invalid weight"}, status=400)

    last_reading = (
        FinalProductSiloReading.objects
        .filter(plant_id=plant_id)
        .order_by("-id")
        .first()
    )

    previous_cumulative = float(last_reading.cumulative_weight_tons) if last_reading else 0
    new_cumulative = previous_cumulative + weight_num
    cycle_number = math.ceil(new_cumulative / 10000.0) if new_cumulative > 0 else 1

    last_lot = (
        FinalProductSampleLot.objects
        .filter(silo_reading__plant_id=plant_id)
        .order_by("-lot_number")
        .first()
    )
    start_lot = (last_lot.lot_number + 1) if last_lot else 1
    lot_numbers = [start_lot + i for i in range(weight_num)]  # ← قائمة أرقام حقيقية، مش نص مجمّع
    lots_sequence = "+".join(str(n) for n in lot_numbers)

    silo_char = "A"
    if "B" in silo:
        silo_char = "B"
    elif "C" in silo:
        silo_char = "C"

    full_sample_code = f"{cycle_number}C({lots_sequence}){silo_char}"

    return JsonResponse({
        "sample_code_preview": full_sample_code,
        "lots": lot_numbers,   # ← السطر الجديد المهم
    })