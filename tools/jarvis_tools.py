"""
JARVIS Agent Toolset — General Management & Orchestration Engine
Aster Foods | Project Monsoon (Packaged Beverage)

Core question: "What should the whole team do next?"
Mandate: The Master Orchestrator. Coordinates the 5 specialist agents, enforces the 84-day countdown, resolves cross-functional trade-offs.
"""

from typing import Dict, List, Optional


PROJECT_TOTAL_BUDGET_INR = 2400000.0
PROJECT_TOTAL_UNITS = 30000
PROJECT_TOTAL_DAYS = 84


def get_current_launch_status(
    current_day: int,
    agent_milestones: Dict[str, Dict],
    total_spent_inr: float,
    units_completed: int,
) -> Dict:
    """
    Computes master launch readiness score, days remaining, and detects bottlenecks.
    """
    days_left = max(0, PROJECT_TOTAL_DAYS - current_day)
    budget_left = PROJECT_TOTAL_BUDGET_INR - total_spent_inr
    burn_pct = round((total_spent_inr / PROJECT_TOTAL_BUDGET_INR) * 100, 2)
    timeline_pct = round((current_day / PROJECT_TOTAL_DAYS) * 100, 2)

    # Check for bottlenecks
    bottlenecks = []
    for agent, data in agent_milestones.items():
        if data.get("status") in ["DELAYED", "BLOCKED", "RED"]:
            bottlenecks.append(f"{agent}: {data.get('issue', 'Unspecified bottleneck')}")

    readiness_score = max(0, min(100, int(100 - (len(bottlenecks) * 20))))

    return {
        "current_day": current_day,
        "days_to_launch": days_left,
        "budget_spent_inr": total_spent_inr,
        "budget_remaining_inr": budget_left,
        "budget_consumed_percent": burn_pct,
        "timeline_elapsed_percent": timeline_pct,
        "units_produced": units_completed,
        "target_units": PROJECT_TOTAL_UNITS,
        "active_bottlenecks": bottlenecks,
        "launch_readiness_score_out_of_100": readiness_score,
        "health": "ON_TRACK" if not bottlenecks else ("WARNING" if len(bottlenecks) <= 2 else "CRITICAL"),
    }


def issue_executive_directive(
    current_day: int,
    primary_focus_agent: str,
    directive_summary: str,
    blocking_conditions: List[str],
) -> Dict:
    """
    Publishes the priority directive for the entire organization answering: "What should the whole team do next?"
    """
    return {
        "day": current_day,
        "directive_id": f"DIR-DAY{current_day:02d}",
        "lead_agent": primary_focus_agent,
        "executive_instruction": directive_summary,
        "critical_prerequisites": blocking_conditions,
        "status": "ACTIVE_DIRECTIVE",
    }


def resolve_cross_agent_conflict(
    issue_type: str,  # e.g., "BUDGET_OVERRUN", "SCHEDULE_SLIPPAGE", "GATEWAY_FAILURE"
    involved_agents: List[str],
    context: str,
) -> Dict:
    """
    Arbitrates conflicts between specialist agents using Project Monsoon's core hierarchy:
    Quality/Safety > Unit Economics (<= ₹65) > Timeline (84 Days) > Scope.
    """
    decision_tree = {
        "GATEWAY_FAILURE": "Halt mass capital release. Re-run 7-day sensory iteration before committing ATLAS production.",
        "BUDGET_OVERRUN": "Rebalance unspent contingency from LEDGER buffer; enforce strictly <= ₹65 COGS.",
        "SCHEDULE_SLIPPAGE": "Authorize overtime with co-packer or expedite logistics if within ₹50k buffer.",
    }

    arbitration = decision_tree.get(
        issue_type, "Escalate immediately to human founder with options matrix."
    )

    return {
        "conflict_type": issue_type,
        "involved_agents": involved_agents,
        "context": context,
        "jarvis_ruling": arbitration,
        "escalate_to_human_founder": issue_type not in decision_tree,
    }
