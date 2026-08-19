"""
Statistical Process Control (SPC) Engine.

Provides:
- ``get_available_spc_tests()`` — auto-discover tests from ConformityRule.
- ``compute_spc()`` — Cp, Cpk, Pp, Ppk, Cpm, Sigma Level, DPMO.
- ``detect_nelson_violations()`` — all 8 Nelson Rules for individuals charts.
- ``get_spc_report()`` — combined convenience function.
"""

from __future__ import annotations

import math
import datetime
from typing import Any

from django.db.models import Q

from custom_permissions.models import get_viewable_plant_ids

# ── d2 constant for n=2 (moving range) ────────────────────────────────────
_D2 = 1.128


# ---------------------------------------------------------------------------
# Auto-discovery
# ---------------------------------------------------------------------------

def get_available_spc_tests(user=None, plant: int | None = None) -> list[dict]:
    """
    Returns every test that has >= 1 associated result and a ConformityRule.

    Auto-updates as new test types get results — zero code changes needed.
    """
    from factory.models import ConformityRule, TestDefinition

    qs = ConformityRule.objects.select_related("plant", "test", "quality_grade").filter(
        test__isnull=False,
    )

    plant_ids = _allowed_plant_ids(user)
    if plant_ids is not None:
        qs = qs.filter(plant_id__in=plant_ids)
    if plant:
        qs = qs.filter(plant_id=plant)

    seen = set()
    results = []
    for rule in qs:
        test = rule.test
        if test is None:
            continue

        key = (rule.plant_id, test.id)
        if key in seen:
            continue
        seen.add(key)

        # Check if any results exist for this test
        from lab.models import SampleTestResult
        has_results = SampleTestResult.objects.filter(
            test_name=test.name,
            sample__plant_id=rule.plant_id,
        ).exists()

        if not has_results:
            continue

        results.append({
            "plant_id": rule.plant_id,
            "plant_name": rule.plant.plant_name if rule.plant else "",
            "test_id": test.id,
            "test_name": test.name,
            "test_category": test.category,
            "unit": test.unit or "",
            "rule_id": rule.id,
            "rule_name": rule.name,
            "min_value": float(rule.min_value) if rule.min_value is not None else None,
            "max_value": float(rule.max_value) if rule.max_value is not None else None,
            "quality_grade": str(rule.quality_grade) if rule.quality_grade else "",
        })

    return results


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------

def _collect_measurements(
    plant_id: int,
    test_name: str,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> list[dict]:
    """
    Pull ordered individual measurements for a (plant, test) pair.

    Returns list of ``{value, timestamp, sample_code}``.
    """
    from lab.models import SampleTestResult

    qs = SampleTestResult.objects.select_related("sample").filter(
        test_name=test_name,
        sample__plant_id=plant_id,
        result__isnull=False,
    ).order_by("entered_at", "id")

    if date_from:
        qs = qs.filter(entered_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(entered_at__date__lte=date_to)

    measurements = []
    for r in qs:
        measurements.append({
            "value": float(r.result),
            "timestamp": r.entered_at.isoformat() if r.entered_at else None,
            "sample_code": r.sample.sample_code if r.sample else "",
        })

    return measurements


# ---------------------------------------------------------------------------
# Core SPC Statistics
# ---------------------------------------------------------------------------

def _compute_sigma_within(values: list[float]) -> float:
    """σ_within = mean(|x_i − x_{i-1}|) / d2  (I-MR, n=2)."""
    if len(values) < 2:
        return 0.0
    mr = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    return sum(mr) / len(mr) / _D2


def _compute_sigma_overall(values: list[float]) -> float:
    """Standard deviation of all values (pooled)."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def compute_spc(
    plant_id: int,
    test_name: str,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict[str, Any]:
    """
    Compute SPC metrics for a given (plant, test, date_range).

    Returns dict with Cp, Cpk, Pp, Ppk, Cpm, Sigma Level, DPMO,
    plus ``provisional`` flag if n < 20.
    """
    from factory.models import ConformityRule

    measurements = _collect_measurements(plant_id, test_name, date_from, date_to)
    values = [m["value"] for m in measurements]
    n = len(values)

    # Get spec limits from ConformityRule
    usl = None
    lsl = None
    target = None

    rule = ConformityRule.objects.filter(
        plant_id=plant_id,
        test__name=test_name,
    ).first()

    if rule:
        if rule.min_value is not None:
            lsl = float(rule.min_value)
        if rule.max_value is not None:
            usl = float(rule.max_value)
        # Target = midpoint of spec if both limits exist
        if usl is not None and lsl is not None:
            target = (usl + lsl) / 2.0

    # Base stats
    mu = sum(values) / n if n > 0 else 0.0
    sigma_within = _compute_sigma_within(values)
    sigma_overall = _compute_sigma_overall(values)

    # ── Capability indices ─────────────────────────────────────────────
    cp = None
    cpu = None
    cpl = None
    cpk = None
    pp = None
    ppu = None
    ppl = None
    ppk = None
    cpm = None

    if sigma_within > 0:
        if usl is not None and lsl is not None:
            cp = (usl - lsl) / (6 * sigma_within)
            cpu = (usl - mu) / (3 * sigma_within)
            cpl = (mu - lsl) / (3 * sigma_within)
            cpk = min(cpu, cpl)
        elif usl is not None:
            cpu = (usl - mu) / (3 * sigma_within)
            cpk = cpu
            cp = cpu  # one-sided
        elif lsl is not None:
            cpl = (mu - lsl) / (3 * sigma_within)
            cpk = cpl
            cp = cpl  # one-sided

    if sigma_overall > 0:
        if usl is not None and lsl is not None:
            pp = (usl - lsl) / (6 * sigma_overall)
            ppu = (usl - mu) / (3 * sigma_overall)
            ppl = (mu - lsl) / (3 * sigma_overall)
            ppk = min(ppu, ppl)
        elif usl is not None:
            ppu = (usl - mu) / (3 * sigma_overall)
            ppk = ppu
            pp = ppu
        elif lsl is not None:
            ppl = (mu - lsl) / (3 * sigma_overall)
            ppk = ppl
            pp = ppl

        # Cpm — only when target exists
        if target is not None:
            cpm_numerator = (usl - lsl) if (usl is not None and lsl is not None) else None
            if cpm_numerator is not None:
                cpm_denom = 6 * math.sqrt(sigma_overall ** 2 + (mu - target) ** 2)
                cpm = cpm_numerator / cpm_denom if cpm_denom > 0 else None

    # ── Sigma Level ────────────────────────────────────────────────────
    sigma_level = None
    if cpk is not None:
        sigma_level = 3 * cpk + 1.5

    # ── DPMO ───────────────────────────────────────────────────────────
    oos_count = 0
    for v in values:
        if usl is not None and v > usl:
            oos_count += 1
        elif lsl is not None and v < lsl:
            oos_count += 1
    dpmo = (oos_count / n * 1_000_000) if n > 0 else 0.0

    # ── Provisional flag ───────────────────────────────────────────────
    provisional = n < 20

    # ── Nelson Rules ───────────────────────────────────────────────────
    nelson_violations = detect_nelson_violations(values)

    return {
        "plant_id": plant_id,
        "test_name": test_name,
        "n": n,
        "provisional": provisional,
        "mu": round(mu, 6),
        "sigma_within": round(sigma_within, 6),
        "sigma_overall": round(sigma_overall, 6),
        "spec": {
            "usl": usl,
            "lsl": lsl,
            "target": target,
        },
        "cp": round(cp, 4) if cp is not None else None,
        "cpu": round(cpu, 4) if cpu is not None else None,
        "cpl": round(cpl, 4) if cpl is not None else None,
        "cpk": round(cpk, 4) if cpk is not None else None,
        "pp": round(pp, 4) if pp is not None else None,
        "ppu": round(ppu, 4) if ppu is not None else None,
        "ppl": round(ppl, 4) if ppl is not None else None,
        "ppk": round(ppk, 4) if ppk is not None else None,
        "cpm": round(cpm, 4) if cpm is not None else None,
        "sigma_level": round(sigma_level, 2) if sigma_level is not None else None,
        "dpmo": round(dpmo, 2),
        "nelson_violations": nelson_violations,
        "measurements": measurements,
    }


# ---------------------------------------------------------------------------
# Nelson Rules — individuals chart
# ---------------------------------------------------------------------------
# All 8 rules against individual values using mean ± 1σ/2σ/3σ zones.

_NELSON_DESCRIPTIONS = {
    1: "1 point beyond 3σ",
    2: "9 points in a row same side of mean",
    3: "6 points in a row steadily trending",
    4: "14 points in a row alternating direction",
    5: "2 of 3 points beyond 2σ, same side",
    6: "4 of 5 points beyond 1σ, same side",
    7: "15 points in a row within 1σ (stratification)",
    8: "8 points in a row beyond 1σ (none within 1σ)",
}


def detect_nelson_violations(values: list[float]) -> list[dict]:
    """Run all 8 Nelson Rules on individual measurements."""
    if len(values) < 2:
        return []

    mu = sum(values) / len(values)
    sigma = _compute_sigma_overall(values)
    if sigma == 0:
        return []

    violations = []

    # Pre-compute zone assignments for each point
    def _zone(v):
        d = abs(v - mu)
        if d <= sigma:
            return 0  # within 1σ (zone C)
        elif d <= 2 * sigma:
            return 1  # 1σ to 2σ (zone B)
        else:
            return 2  # beyond 2σ (zone A)

    def _side(v):
        if v > mu:
            return 1
        elif v < mu:
            return -1
        return 0

    n = len(values)

    # Rule 1: 1 point beyond 3σ
    rule1 = [i for i, v in enumerate(values) if abs(v - mu) > 3 * sigma]
    if rule1:
        violations.append({"rule": 1, "point_indices": rule1, "description": _NELSON_DESCRIPTIONS[1]})

    # Rule 2: 9 points in a row same side of mean
    rule2 = _find_run_same_side(values, mu, n=9)
    if rule2 is not None:
        violations.append({"rule": 2, "point_indices": rule2, "description": _NELSON_DESCRIPTIONS[2]})

    # Rule 3: 6 points in a row steadily trending (up or down)
    rule3 = _find_trend(values, n=6)
    if rule3 is not None:
        violations.append({"rule": 3, "point_indices": rule3, "description": _NELSON_DESCRIPTIONS[3]})

    # Rule 4: 14 points in a row alternating direction
    rule4 = _find_alternating(values, n=14)
    if rule4 is not None:
        violations.append({"rule": 4, "point_indices": rule4, "description": _NELSON_DESCRIPTIONS[4]})

    # Rule 5: 2 of 3 points beyond 2σ, same side
    rule5 = _find_m_of_n_beyond(values, mu, sigma, m=2, n_window=3, zone_threshold=2)
    if rule5:
        violations.append({"rule": 5, "point_indices": rule5, "description": _NELSON_DESCRIPTIONS[5]})

    # Rule 6: 4 of 5 points beyond 1σ, same side
    rule6 = _find_m_of_n_beyond(values, mu, sigma, m=4, n_window=5, zone_threshold=1)
    if rule6:
        violations.append({"rule": 6, "point_indices": rule6, "description": _NELSON_DESCRIPTIONS[6]})

    # Rule 7: 15 points in a row within 1σ (stratification)
    rule7 = _find_run_within_1sigma(values, mu, sigma, n=15)
    if rule7 is not None:
        violations.append({"rule": 7, "point_indices": rule7, "description": _NELSON_DESCRIPTIONS[7]})

    # Rule 8: 8 points in a row beyond 1σ, none within 1σ
    rule8 = _find_run_beyond_1sigma(values, mu, sigma, n=8)
    if rule8 is not None:
        violations.append({"rule": 8, "point_indices": rule8, "description": _NELSON_DESCRIPTIONS[8]})

    return violations


def _find_run_same_side(values, mu, n=9):
    """Rule 2: n consecutive points on the same side of mean."""
    for start in range(len(values) - n + 1):
        window = values[start:start + n]
        sides = [_side(v) for v in window]
        if all(s == sides[0] for s in sides) and sides[0] != 0:
            return list(range(start, start + n))
    return None


def _find_trend(values, n=6):
    """Rule 3: n consecutive points steadily increasing or decreasing."""
    for start in range(len(values) - n + 1):
        window = values[start:start + n]
        diffs = [window[i + 1] - window[i] for i in range(len(window) - 1)]
        if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
            return list(range(start, start + n))
    return None


def _find_alternating(values, n=14):
    """Rule 4: n consecutive points alternating direction."""
    for start in range(len(values) - n + 1):
        window = values[start:start + n]
        alternating = True
        for i in range(2, len(window)):
            if (window[i] - window[i - 1]) * (window[i - 1] - window[i - 2]) >= 0:
                alternating = False
                break
        if alternating:
            return list(range(start, start + n))
    return None


def _find_m_of_n_beyond(values, mu, sigma, m=2, n_window=3, zone_threshold=2):
    """Rule 5/6: m of n consecutive points beyond zone_threshold*σ on same side."""
    indices = []
    for start in range(len(values) - n_window + 1):
        window = values[start:start + n_window]
        beyond_same = 0
        side = None
        for i, v in enumerate(window):
            d = v - mu
            if abs(d) > zone_threshold * sigma:
                s = 1 if d > 0 else -1
                if side is None:
                    side = s
                if s == side:
                    beyond_same += 1
        if beyond_same >= m and side is not None:
            indices.extend(range(start, start + n_window))
    return sorted(set(indices)) if indices else None


def _find_run_within_1sigma(values, mu, sigma, n=15):
    """Rule 7: n consecutive points within 1σ of mean."""
    for start in range(len(values) - n + 1):
        window = values[start:start + n]
        if all(abs(v - mu) <= sigma for v in window):
            return list(range(start, start + n))
    return None


def _find_run_beyond_1sigma(values, mu, sigma, n=8):
    """Rule 8: n consecutive points beyond 1σ, none within 1σ."""
    for start in range(len(values) - n + 1):
        window = values[start:start + n]
        if all(abs(v - mu) > sigma for v in window):
            return list(range(start, start + n))
    return None


# ---------------------------------------------------------------------------
# Combined convenience
# ---------------------------------------------------------------------------

def get_spc_report(
    plant_id: int,
    test_name: str,
    user=None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> dict:
    """
    Combined SPC report: available tests + compute + violations.
    """
    spc_data = compute_spc(plant_id, test_name, date_from, date_to)

    # Add available tests list for context
    available = get_available_spc_tests(user=user, plant=plant_id)

    return {
        "spc": spc_data,
        "available_tests": available,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed_plant_ids(user):
    if user is None or getattr(user, "is_superuser", False):
        return None
    return get_viewable_plant_ids(user)
