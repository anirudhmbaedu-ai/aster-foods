"""
NOVA Agent Toolset — HR, Talent & Operational Capacity Engine
Aster Foods | Project Monsoon (Packaged Beverage)

Core question: "What skills and capacity do we need?"
Mandate: Sources specialized human contractors (food scientists, QA auditors, sampling reps) and monitors AI team operational capacity.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

NOVA_BUDGET_CAP = 80000.0  # ₹80,000 allocated for human contractor capacity


def audit_skills_gap(project_phase_day: int) -> Dict:
    """
    Identifies human specialized skill gaps required at specific milestones in the 84-day window.
    """
    required_roles = []
    if project_phase_day <= 21:
        required_roles.append({
            "role": "Consultant Beverage Technologist",
            "skills": ["Formulation stabilization", "Preservative optimization", "Sensory protocol"],
            "urgency": "CRITICAL",
            "estimated_cost_inr": 35000.0,
            "duration_days": 10,
        })
    elif 22 <= project_phase_day <= 60:
        required_roles.append({
            "role": "Third-Party QA / Plant Auditor",
            "skills": ["FSSAI hygiene audit", "HACCP audit at co-packer facility", "Batch release"],
            "urgency": "HIGH",
            "estimated_cost_inr": 20000.0,
            "duration_days": 5,
        })
    elif project_phase_day > 60:
        required_roles.append({
            "role": "Field Sampling Promoters (x4)",
            "skills": ["Customer engagement", "Retail sampling booth management", "Stock replenishment"],
            "urgency": "MEDIUM",
            "estimated_cost_inr": 25000.0,
            "duration_days": 14,
        })

    total_contractor_cost = sum(r["estimated_cost_inr"] for r in required_roles)
    budget_ok = total_contractor_cost <= NOVA_BUDGET_CAP

    return {
        "current_day": project_phase_day,
        "active_skill_gaps": required_roles,
        "total_estimated_cost_inr": total_contractor_cost,
        "nova_budget_cap_inr": NOVA_BUDGET_CAP,
        "within_budget": budget_ok,
        "capacity_readiness": "READY" if budget_ok else "OVER_BUDGET_ALERT",
    }


def hire_contractor(
    contractor_name: str,
    role: str,
    fee_inr: float,
    scope_of_work: str,
    day_disbursed: int,
) -> Dict:
    """
    Onboards and logs a contractor contract, verifying scope and budget cap.
    """
    if fee_inr > NOVA_BUDGET_CAP:
        return {
            "status": "REJECTED",
            "error": f"Fee ₹{fee_inr} exceeds total HR contractor budget of ₹{NOVA_BUDGET_CAP}",
        }

    return {
        "contractor_id": f"CONT-{abs(hash(contractor_name)) % 10000}",
        "contractor_name": contractor_name,
        "role": role,
        "fee_inr": fee_inr,
        "scope": scope_of_work,
        "onboarded_on_day": day_disbursed,
        "status": "ENGAGED",
    }


def monitor_agent_system_health(agent_statuses: Dict[str, str]) -> Dict:
    """
    Audits uptime and operational bottlenecks across all 6 autonomous agents.
    """
    all_operational = all(status == "OPERATIONAL" for status in agent_statuses.values())
    stalled_agents = [agent for agent, status in agent_statuses.items() if status != "OPERATIONAL"]

    return {
        "total_agents": len(agent_statuses),
        "all_agents_healthy": all_operational,
        "stalled_agents": stalled_agents,
        "team_capacity_percent": round(
            ((len(agent_statuses) - len(stalled_agents)) / max(1, len(agent_statuses))) * 100, 1
        ),
        "status": "HEALTHY" if all_operational else "ALERT_AGENT_DEGRADED",
    }
