"""
LEDGER Agent Toolset — Finance & Treasury Engine
Aster Foods | Project Monsoon (Packaged Beverage)

Core question: "Can we fund the plan?"
Mandate: Guard the ₹24 Lakhs launch budget, track cash runway, model scenario stress tests.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

TOTAL_LAUNCH_BUDGET = 2400000.0  # ₹24 Lakhs


def calculate_cash_runway(
    current_day: int,
    disbursements_by_agent: Dict[str, float],
    projected_commitments_inr: float,
) -> Dict:
    """
    Computes real-time cash burn, available liquidity, and runway across the 84-day window.
    """
    total_spent = sum(disbursements_by_agent.values())
    remaining_cash = TOTAL_LAUNCH_BUDGET - total_spent
    uncommitted_cash = remaining_cash - projected_commitments_inr

    days_remaining = max(0, 84 - current_day)
    avg_burn_per_day = round(total_spent / max(1, current_day), 2)
    projected_total_spend = round(total_spent + (avg_burn_per_day * days_remaining), 2)

    is_solvent = remaining_cash >= 0 and uncommitted_cash >= 0

    return {
        "current_day": current_day,
        "days_remaining_to_launch": days_remaining,
        "total_budget_inr": TOTAL_LAUNCH_BUDGET,
        "total_spent_inr": total_spent,
        "remaining_cash_inr": remaining_cash,
        "committed_liabilities_inr": projected_commitments_inr,
        "free_liquidity_inr": uncommitted_cash,
        "burn_by_agent_inr": disbursements_by_agent,
        "avg_daily_burn_inr": avg_burn_per_day,
        "is_solvent": is_solvent,
        "budget_variance_inr": round(TOTAL_LAUNCH_BUDGET - projected_total_spend, 2),
        "solvency_status": "HEALTHY" if uncommitted_cash > 100000 else ("TIGHT" if is_solvent else "DEFICIT"),
    }


def model_pnl_and_breakeven(
    units_sold: int,
    retail_price_inr: float = 120.0,
    actual_cogs_per_unit_inr: float = 65.0,
    marketing_and_fixed_costs_inr: float = 450000.0,
    retailer_margin_percent: float = 20.0,  # Trade margin for distributors / retailers
) -> Dict:
    """
    Models revenue, contribution margins, and breakeven unit volume.
    """
    net_realized_price = retail_price_inr * (1 - (retailer_margin_percent / 100.0))
    gross_revenue = units_sold * retail_price_inr
    net_revenue = units_sold * net_realized_price
    total_cogs = units_sold * actual_cogs_per_unit_inr

    unit_contribution_margin = net_realized_price - actual_cogs_per_unit_inr
    breakeven_units = (
        int(marketing_and_fixed_costs_inr / max(0.01, unit_contribution_margin))
        if unit_contribution_margin > 0
        else -1
    )

    operating_profit = (units_sold * unit_contribution_margin) - marketing_and_fixed_costs_inr

    return {
        "units_sold": units_sold,
        "mrp_inr": retail_price_inr,
        "retailer_margin_percent": retailer_margin_percent,
        "net_realized_price_per_unit_inr": round(net_realized_price, 2),
        "cogs_per_unit_inr": actual_cogs_per_unit_inr,
        "unit_contribution_margin_inr": round(unit_contribution_margin, 2),
        "gross_revenue_inr": round(gross_revenue, 2),
        "net_revenue_inr": round(net_revenue, 2),
        "total_cogs_inr": round(total_cogs, 2),
        "breakeven_units": breakeven_units,
        "breakeven_achieved": units_sold >= breakeven_units if breakeven_units > 0 else False,
        "projected_operating_profit_inr": round(operating_profit, 2),
    }


def authorize_disbursement(
    requesting_agent: str,
    amount_inr: float,
    purpose: str,
    milestone_day: int,
) -> Dict:
    """
    Enforces financial governance and releases tranches based on milestone verification.
    """
    # Allocation caps per agent
    caps = {
        "ATLAS": 1800000.0,
        "PULSE": 350000.0,
        "LEDGER": 100000.0,
        "NOVA": 80000.0,
        "PRISM": 40000.0,
        "JARVIS": 30000.0,
    }

    allocated_cap = caps.get(requesting_agent, 0.0)

    # Special rule: Day 21 Gatekeeper check for ATLAS bulk production spend (> ₹5,00,000)
    if requesting_agent == "ATLAS" and amount_inr > 500000.0 and milestone_day < 21:
        return {
            "approved": False,
            "status": "REJECTED_GATEKEEPER_LOCK",
            "reason": "Mass production tranche (> ₹5L) cannot be disbursed before Day 21 Demand Validation sign-off.",
        }

    approved = amount_inr <= allocated_cap
    return {
        "approved": approved,
        "requesting_agent": requesting_agent,
        "amount_requested_inr": amount_inr,
        "agent_cap_inr": allocated_cap,
        "status": "DISBURSED" if approved else "ESCALATED_TO_FOUNDER",
        "purpose": purpose,
    }
