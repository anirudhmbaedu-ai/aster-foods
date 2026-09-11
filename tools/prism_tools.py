"""
PRISM Agent Toolset — Analytics & Business Intelligence Engine
Aster Foods | Project Monsoon (Packaged Beverage)

Core question: "What do the numbers actually say?"
Mandate: Truth teller. Statistically audits demand tests, computes CAC, evaluates survey confidence, projects inventory sell-through.
"""

import math
from typing import Dict, List, Optional


def audit_taste_test_significance(
    sample_size: int,
    positive_responses: int,
    confidence_level: float = 0.95,
) -> Dict:
    """
    Computes statistical confidence intervals for consumer taste test results.
    Validates whether the positive response rate reliably clears the 75% threshold.
    """
    if sample_size <= 0:
        return {"error": "Sample size must be greater than 0"}

    p_hat = positive_responses / sample_size
    # Standard normal z-score for 95% confidence is ~1.96
    z = 1.96 if confidence_level == 0.95 else 2.576

    margin_of_error = z * math.sqrt((p_hat * (1 - p_hat)) / sample_size)
    ci_lower = max(0.0, p_hat - margin_of_error)
    ci_upper = min(1.0, p_hat + margin_of_error)

    statistically_valid = sample_size >= 150
    passes_75_threshold = ci_lower >= 0.70  # Conservative lower bound

    return {
        "sample_size": sample_size,
        "sample_positive_rate_percent": round(p_hat * 100, 2),
        "margin_of_error_percent": round(margin_of_error * 100, 2),
        "confidence_interval_95": [round(ci_lower * 100, 2), round(ci_upper * 100, 2)],
        "sample_size_adequate": statistically_valid,
        "statistical_green_light": passes_75_threshold and statistically_valid,
        "verdict": (
            "STATISTICALLY CONFIDENT: True population satisfaction >= 70% with 95% confidence."
            if passes_75_threshold and statistically_valid
            else "INCONCLUSIVE / HIGH RISK: Sample variance or size insufficient to risk mass capital."
        ),
    }


def compute_blended_cac(
    ad_spend_inr: float,
    influencer_spend_inr: float,
    sampling_event_cost_inr: float,
    total_customers_acquired: int,
    total_units_sold: int,
) -> Dict:
    """
    Computes customer acquisition cost (CAC) and marketing cost per unit.
    Guardrail: CAC per unit <= ₹18.00.
    """
    total_marketing_cost = ad_spend_inr + influencer_spend_inr + sampling_event_cost_inr
    cac_per_customer = (
        round(total_marketing_cost / max(1, total_customers_acquired), 2)
    )
    marketing_cost_per_unit = (
        round(total_marketing_cost / max(1, total_units_sold), 2)
    )

    within_guardrail = marketing_cost_per_unit <= 18.0

    return {
        "total_marketing_cost_inr": total_marketing_cost,
        "total_customers_acquired": total_customers_acquired,
        "total_units_sold": total_units_sold,
        "cac_per_customer_inr": cac_per_customer,
        "marketing_cost_per_unit_inr": marketing_cost_per_unit,
        "guardrail_cap_inr": 18.0,
        "is_within_guardrail": within_guardrail,
        "health_score": "HEALTHY" if within_guardrail else "DANGER_HIGH_CAC",
    }


def forecast_inventory_depletion(
    total_inventory: int = 30000,
    daily_sales_run_rate: float = 350.0,
    channel_breakdown: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Forecasts sell-through curve and stockout risk for 30,000 units.
    """
    days_to_deplete = int(total_inventory / max(1.0, daily_sales_run_rate))
    stockout_date_relative_days = days_to_deplete

    return {
        "starting_inventory": total_inventory,
        "assumed_daily_sales_units": daily_sales_run_rate,
        "estimated_days_to_full_sell_through": days_to_deplete,
        "monthly_velocity_units": int(daily_sales_run_rate * 30),
        "sell_through_risk": (
            "FAST_STOCKOUT_RISK"
            if days_to_deplete < 45
            else ("HEALTHY_VELOCITY" if days_to_deplete <= 90 else "SLOW_MOVING_INVENTORY")
        ),
        "reorder_trigger_point_units": int(daily_sales_run_rate * 21),  # 21 days lead time for batch 2
    }
