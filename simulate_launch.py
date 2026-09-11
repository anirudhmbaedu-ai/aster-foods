"""
Project Monsoon — Full Multi-Agent Simulation Engine
Aster Foods | Packaged Beverage Launch (84 Days, 30,000 Units, ₹24 Lakhs)

Simulates the coordinated workflow across all 6 AI agents:
JARVIS -> LEDGER -> ATLAS -> PULSE -> PRISM -> NOVA
"""

import json
import tools.jarvis_tools as jt
import tools.ledger_tools as lt
import tools.atlas_tools as at
import tools.pulse_tools as pt
import tools.prism_tools as prt
import tools.nova_tools as nt


def simulate_project_monsoon():
    print("=" * 70)
    print("🚀 ASTER FOODS: PROJECT MONSOON MULTI-AGENT LAUNCH SIMULATION")
    print("Target: 30,000 Units | Timeline: 84 Days | Budget: ₹24,00,000")
    print("=" * 70)

    # -------------------------------------------------------------
    # DAY 1: Initialization & Team Alignment (JARVIS & NOVA)
    # -------------------------------------------------------------
    print("\n[DAY 1] JARVIS broadcasts organization-wide directive:")
    d1 = jt.issue_executive_directive(
        current_day=1,
        primary_focus_agent="NOVA & ATLAS",
        directive_summary="Engage beverage technologist by Day 3 and prepare 200 benchtop taste samples by Day 7.",
        blocking_conditions=["FSSAI formula compliance", "Recipe shelf-life stability"],
    )
    print(f"  Directive: {d1['executive_instruction']}")

    print("\n[DAY 3] NOVA audits skills gap and onboards formulation chemist:")
    skills = nt.audit_skills_gap(project_phase_day=3)
    hire = nt.hire_contractor(
        contractor_name="Dr. S. Nair",
        role="Consultant Beverage Technologist",
        fee_inr=35000.0,
        scope_of_work="Ready-To-Drink formulation stabilization, preservative optimization, and 200 sample prep.",
        day_disbursed=3,
    )
    print(f"  Contracted: {hire['contractor_name']} ({hire['role']}) for ₹{hire['fee_inr']:,.0f}")

    # -------------------------------------------------------------
    # DAYS 8-20: Sensory & Digital Demand Testing (PULSE & PRISM)
    # -------------------------------------------------------------
    print("\n[DAYS 8–20] PULSE runs digital smoke test and blind taste sampling:")
    ad_res = pt.run_ad_smoke_test(
        campaign_name="Monsoon Hydration Pilot",
        channel="Meta",
        target_demographic="Urban 18-35 Fitness & Busy Professionals",
        daily_budget_inr=2500.0,
        days_to_run=10,
        price_point_tested=120.0,
    )
    taste_res = pt.fetch_taste_test_metrics(batch_sample_id="SAMPLE-BATCH-001")
    print(f"  Ad Campaign Spent: ₹{ad_res['budget_spent_inr']:,.0f} | CTR: {ad_res['ctr_percent']}% | Intent: {ad_res['intent_conversion_rate']}%")
    print(f"  Taste Trial Sample Size: {taste_res['total_respondents']} | Avg Taste Score: {taste_res['taste_score_avg_out_of_10']}/10 | Would Buy Again: {taste_res['would_buy_again_percent']}%")

    print("\n[DAY 20] PRISM conducts independent statistical verification:")
    stat_audit = prt.audit_taste_test_significance(
        sample_size=taste_res["total_respondents"],
        positive_responses=int(taste_res["total_respondents"] * (taste_res["would_buy_again_percent"] / 100.0)),
    )
    print(f"  PRISM 95% Confidence Interval: {stat_audit['confidence_interval_95'][0]}% - {stat_audit['confidence_interval_95'][1]}%")
    print(f"  Statistical Green Light: {stat_audit['statistical_green_light']} ({stat_audit['verdict']})")

    # -------------------------------------------------------------
    # DAY 21: THE MASTER GATEKEEPER CHECKPOINT
    # -------------------------------------------------------------
    print("\n" + "#" * 70)
    print("🚦 [DAY 21 GATEWAY] EXECUTIVE DEMAND VALIDATION REVIEW")
    print("#" * 70)
    gatekeeper_report = pt.generate_day21_validation_report(
        ad_results=ad_res,
        taste_results=taste_res,
        current_marketing_burn_inr=ad_res["budget_spent_inr"] + 15000.0,
    )
    print(f"  Gatekeeper Passed: {gatekeeper_report['demand_gatekeeper_passed']}")
    print(f"  Recommendation: {gatekeeper_report['recommendation']}")

    # LEDGER authorizes Tranche 2 release for ATLAS
    tranche_2 = lt.authorize_disbursement(
        requesting_agent="ATLAS",
        amount_inr=1200000.0,
        purpose="Raw materials and bottle procurement advance for 30,000 units",
        milestone_day=21,
    )
    print(f"  LEDGER Disbursement Status: {tranche_2['status']} for ₹{tranche_2['amount_requested_inr']:,.0f}")

    # -------------------------------------------------------------
    # DAYS 22-60: Manufacturing & Production (ATLAS & LEDGER)
    # -------------------------------------------------------------
    print("\n[DAYS 22–53] ATLAS executes manufacturing schedule and BOM audit:")
    cogs_audit = at.audit_unit_cogs(
        raw_materials_inr=22.0,
        bottle_or_can_inr=16.0,
        label_and_carton_inr=7.0,
        co_packer_filling_fee_inr=10.0,
        inbound_freight_inr=5.0,
        qa_testing_cost_per_unit_inr=2.0,
    )
    print(f"  BOM Calculated COGS: ₹{cogs_audit['calculated_unit_cogs_inr']:.2f} / unit (Cap: ₹{cogs_audit['target_cogs_cap_inr']:.2f})")
    print(f"  Gross Margin at ₹120 MRP: ₹{cogs_audit['gross_margin_per_unit_inr']:.2f} ({cogs_audit['gross_margin_percent']}%)")

    sched = at.calculate_production_schedule(total_units=30000, production_start_day=22)
    print(f"  Projected Production Completion: Day {sched['projected_completion_day']} (Slack buffer: {sched['slack_buffer_days']} days)")

    # Finished batch logged
    batch = at.log_inventory_batch(
        batch_code="MONSOON-B01",
        units_produced=30500,
        damaged_or_spoilage_units=420,
        qa_lab_passed=True,
        warehouse_location="Central Hub Warehouse, Bay 4",
    )
    print(f"  Batch Completed: {batch['net_saleable_units']:,} net saleable units | Yield: {batch['batch_yield_rate_percent']}% | QA Released: {batch['qa_released']}")

    # -------------------------------------------------------------
    # DAY 60: Distribution Pre-Orders & Unit Economics Audit
    # -------------------------------------------------------------
    print("\n[DAY 60] PULSE locks in retail channel commitments:")
    commitments = [
        {"partner_name": "Blinkit / Zepto Quick-Commerce", "channel_type": "Q-Commerce", "units": 10000},
        {"partner_name": "Nature's Basket & Modern Trade", "channel_type": "Retail", "units": 6500},
        {"partner_name": "Selected Premium Cafes & Gyms", "channel_type": "Gym/Cafe", "units": 2000},
    ]
    preorders = pt.track_channel_commitments(commitments)
    print(f"  Committed Units: {preorders['total_units_committed']:,} / 30,000 ({preorders['progress_percent']}%)")
    print(f"  Day 60 Goal (15,000 units minimum) Met: {preorders['milestone_day60_goal_met']}")

    # -------------------------------------------------------------
    # DAY 84: LAUNCH DAY & SOLVENCY REPORT (LEDGER & JARVIS)
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("🎉 [DAY 84 LAUNCH DAY] PROJECT MONSOON COMMERCIALLY LIVE!")
    print("=" * 70)

    # Cash burn reconciliation
    total_spent = {
        "ATLAS": 1785000.0,
        "PULSE": 342000.0,
        "LEDGER": 65000.0,
        "NOVA": 75000.0,
        "PRISM": 35000.0,
        "JARVIS": 20000.0,
    }
    runway = lt.calculate_cash_runway(current_day=84, disbursements_by_agent=total_spent, projected_commitments_inr=0.0)
    print(f"  Total Budget: ₹{runway['total_budget_inr']:,.0f}")
    print(f"  Total Actual Spend: ₹{runway['total_spent_inr']:,.0f}")
    print(f"  Remaining Cash Reserve: ₹{runway['remaining_cash_inr']:,.0f}")
    print(f"  Financial Solvency Status: {runway['solvency_status']}")

    # Final Launch Status from JARVIS
    final_status = jt.get_current_launch_status(
        current_day=84,
        agent_milestones={},
        total_spent_inr=runway['total_spent_inr'],
        units_completed=batch['net_saleable_units'],
    )
    print(f"  Launch Readiness Score: {final_status['launch_readiness_score_out_of_100']} / 100")
    print(f"  Health: {final_status['health']}")
    print(f"  30,000 Units Ready for Immediate Dispatch: YES")
    print("=" * 70)


if __name__ == "__main__":
    simulate_project_monsoon()
