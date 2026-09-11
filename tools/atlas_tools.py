"""
ATLAS Agent Toolset — Operations & Production Engine
Aster Foods | Project Monsoon (Packaged Beverage)

Core question: "Can we deliver on time?"
Target: 30,000 units within 84 days at <= ₹65/unit COGS.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass
class ProductionSchedule:
    total_units: int
    batch_size: int
    num_batches: int
    co_packer_lead_time_days: int
    raw_material_lead_time_days: int
    packaging_procurement_days: int
    qa_release_days: int
    estimated_total_days: int
    can_deliver_before_day84: bool
    cogs_per_unit_inr: float


def calculate_production_schedule(
    total_units: int = 30000,
    co_packer_daily_capacity: int = 5000,
    raw_material_lead_days: int = 14,
    packaging_procurement_days: int = 18,
    qa_testing_days: int = 7,
    production_start_day: int = 22,  # Starts immediately after Day 21 Gatekeeper sign-off
) -> Dict:
    """
    Computes critical path schedule for producing 30,000 units by Day 84.
    """
    procurement_days = max(raw_material_lead_days, packaging_procurement_days)
    run_days = int((total_units + co_packer_daily_capacity - 1) / co_packer_daily_capacity)
    total_pipeline_days = procurement_days + run_days + qa_testing_days
    final_completion_day = production_start_day + total_pipeline_days

    on_time = final_completion_day <= 84
    slack_days = 84 - final_completion_day

    return {
        "target_units": total_units,
        "production_start_day": production_start_day,
        "procurement_lead_time_days": procurement_days,
        "co_packer_run_days": run_days,
        "qa_microbiology_testing_days": qa_testing_days,
        "projected_completion_day": final_completion_day,
        "launch_deadline_day": 84,
        "slack_buffer_days": slack_days,
        "can_deliver_on_time": on_time,
        "status": "GREEN" if on_time and slack_days >= 7 else ("YELLOW" if on_time else "RED"),
    }


def audit_unit_cogs(
    raw_materials_inr: float,
    bottle_or_can_inr: float,
    label_and_carton_inr: float,
    co_packer_filling_fee_inr: float,
    inbound_freight_inr: float,
    qa_testing_cost_per_unit_inr: float,
) -> Dict:
    """
    Audits the bill of materials (BOM) to ensure unit COGS strictly <= ₹65.00.
    """
    total_cogs = (
        raw_materials_inr
        + bottle_or_can_inr
        + label_and_carton_inr
        + co_packer_filling_fee_inr
        + inbound_freight_inr
        + qa_testing_cost_per_unit_inr
    )
    is_compliant = total_cogs <= 65.0
    margin_at_120_mrp = 120.0 - total_cogs

    return {
        "calculated_unit_cogs_inr": round(total_cogs, 2),
        "target_cogs_cap_inr": 65.0,
        "cost_variance_inr": round(total_cogs - 65.0, 2),
        "cogs_compliant": is_compliant,
        "gross_margin_per_unit_inr": round(margin_at_120_mrp, 2),
        "gross_margin_percent": round((margin_at_120_mrp / 120.0) * 100, 2),
        "bom_breakdown": {
            "raw_ingredients": raw_materials_inr,
            "bottle_or_can": bottle_or_can_inr,
            "label_and_carton": label_and_carton_inr,
            "co_packing_fee": co_packer_filling_fee_inr,
            "inbound_freight": inbound_freight_inr,
            "qa_testing": qa_testing_cost_per_unit_inr,
        },
        "escalation_required": not is_compliant,
    }


def evaluate_co_packer(
    name: str,
    location: str,
    minimum_order_qty: int,
    daily_capacity: int,
    certifications: List[str],  # e.g., ["FSSAI", "GMP", "ISO 22000"]
    filling_cost_per_unit_inr: float,
) -> Dict:
    """
    Evaluates co-packer suitability for Aster Foods' 30,000 unit batch.
    """
    has_fssai = "FSSAI" in certifications
    has_gmp = "GMP" in certifications
    moq_ok = minimum_order_qty <= 30000
    cost_ok = filling_cost_per_unit_inr <= 14.0

    qualified = has_fssai and moq_ok and cost_ok

    return {
        "co_packer_name": name,
        "qualified": qualified,
        "fssai_certified": has_fssai,
        "gmp_certified": has_gmp,
        "moq_acceptable": moq_ok,
        "filling_cost_per_unit_inr": filling_cost_per_unit_inr,
        "risk_assessment": "LOW" if (qualified and has_gmp) else ("MEDIUM" if qualified else "HIGH"),
        "notes": "Qualified partner" if qualified else "Disqualified: check MOQ, FSSAI, or pricing.",
    }


def log_inventory_batch(
    batch_code: str,
    units_produced: int,
    damaged_or_spoilage_units: int,
    qa_lab_passed: bool,
    warehouse_location: str,
) -> Dict:
    """
    Records batch completion and net saleable inventory.
    """
    net_saleable = units_produced - damaged_or_spoilage_units
    yield_rate = round((net_saleable / max(units_produced, 1)) * 100, 2)

    return {
        "batch_code": batch_code,
        "gross_units": units_produced,
        "spoilage_units": damaged_or_spoilage_units,
        "net_saleable_units": net_saleable,
        "batch_yield_rate_percent": yield_rate,
        "qa_released": qa_lab_passed,
        "warehouse_location": warehouse_location,
        "ready_for_distribution": qa_lab_passed and net_saleable > 0,
    }
