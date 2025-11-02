"""
Seed demo data for testing and demonstration.

Creates 3 pre-defined users at different stages of their journey:
- demo1@nvox.com (password: Demo1234) - At BOARD stage (mid-journey)
- demo2@nvox.com (password: Demo1234) - At WARD stage (late-journey, post-surgery)
- demo3@nvox.com (password: Demo1234) - At HOME stage (successful completion)

These users demonstrate the normal journey path:
REFERRAL → WORKUP → MATCH → DONOR → BOARD → PREOP → ORSCHED → SURG → ICU → WARD → HOME

Note: This script seeds user data only. Journey routing is handled by the graph-based
routing engine using the journey_edges table (populated via migration 005_populate_journey_edges.sql).
The comments showing routing logic (e.g., "40-100 → WORKUP") reference the graph edge conditions
that determine stage transitions.
"""

import json
from utils.hashing import hash_email, hash_password
import asyncio
import asyncpg
import os
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def seed_demo_data():
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "transplant_journey"),
        "user": os.getenv("DB_USER", "transplant_user"),
        "password": os.getenv("DB_PASSWORD", "change_me_in_production"),
    }

    print(f"Connecting to database at {db_config['host']}:{db_config['port']}...")

    conn = await asyncpg.connect(**db_config)

    try:
        edge_count = await conn.fetchval("SELECT COUNT(*) FROM journey_edges")
        if edge_count == 0:
            print("Error: journey_edges table is empty!")
            print("Please run migration 005_populate_journey_edges.sql first.")
            return
        print(f"✓ Found {edge_count} journey edges in database")

        existing = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE email_hash = $1",
            hash_email("demo1@nvox.com")
        )

        if existing > 0:
            print("Demo data already exists. Skipping seed...")
            return

        print("\nCreating demo users...")

        demo_users = [
            {
                "email": "demo1@nvox.com",
                "password": "Demo1234",
                "stage": "BOARD",
                "answers": {
                    # REFERRAL stage
                    "ref_age": 45,
                    "ref_has_nephrologist_note": "yes",
                    "ref_karnofsky": 80,  # 40-100 → WORKUP
                    # WORKUP stage
                    "wrk_egfr": 12,  # 0-15.999 → MATCH
                    "wrk_infections_active": 0,
                    "wrk_support": "Spouse provides full-time care at home",
                    # MATCH stage
                    "mtc_pra": 25,  # 0-79.999 → DONOR
                    "mtc_donor_available": 1,
                    "mtc_notes": "No prior transplants or transfusions",
                    # DONOR stage
                    "dnr_bmi": 24.5,
                    "dnr_clearance": 1,  # 1 → BOARD
                    "dnr_motivation": "Sister wants to donate to help family member",
                    # BOARD stage - currently here
                    "brd_risk_score": 5.5,  # 0-6.999 → PREOP (when continue)
                    "brd_needs_more_tests": 0,
                    "brd_comment": "Patient approved for transplant, low risk profile"
                }
            },
            {
                "email": "demo2@nvox.com",
                "password": "Demo1234",
                "stage": "WARD",
                "answers": {
                    # REFERRAL stage
                    "ref_age": 52,
                    "ref_has_nephrologist_note": "yes",
                    "ref_karnofsky": 90,
                    # WORKUP stage
                    "wrk_egfr": 14,
                    "wrk_infections_active": 0,
                    "wrk_support": "Spouse and adult children available",
                    # MATCH stage
                    "mtc_pra": 10,
                    "mtc_donor_available": 1,
                    "mtc_notes": "One prior pregnancy, no other sensitizing events",
                    # DONOR stage
                    "dnr_bmi": 26.0,
                    "dnr_clearance": 1,
                    "dnr_motivation": "Spouse donation, excellent psychosocial evaluation",
                    # BOARD stage
                    "brd_risk_score": 4.0,
                    "brd_needs_more_tests": 0,
                    "brd_comment": "Excellent candidate, proceed with surgery planning",
                    # PREOP stage
                    "prp_bp": 135,  # 60-179.999 → ORSCHED
                    "prp_hba1c": 5.8,
                    "prp_infection_status": 0,
                    # ORSCHED stage
                    "ors_final_crossmatch": 1,  # 1 → SURG
                    "ors_days_to_or": 3,
                    "ors_consent_status": "yes",
                    # SURG stage
                    "srg_warm_isch_time": 35,  # 0-120 → ICU
                    "srg_est_blood_loss": 250,
                    "srg_approach": "robotic",
                    "icu_urine_hr": 150,
                    "icu_lactate": 1.2,
                    "icu_airway_stable": 1,  # 1 → WARD
                    "wrd_pain_score": 3,
                    "wrd_walk_meters": 200,
                    "wrd_teaching_done": "yes"
                }
            },
            {
                "email": "demo3@nvox.com",
                "password": "Demo1234",
                "stage": "HOME",
                "answers": {
                    "ref_age": 38,
                    "ref_has_nephrologist_note": "yes",
                    "ref_karnofsky": 85,
                    "wrk_egfr": 11,
                    "wrk_infections_active": 0,
                    "wrk_support": "Family member available for support",
                    "mtc_pra": 5,
                    "mtc_donor_available": 1,
                    "mtc_notes": "No prior transplants, transfusions, or pregnancies",
                    "dnr_bmi": 23.8,
                    "dnr_clearance": 1,
                    "dnr_motivation": "Brother donation, strong family support system",
                    "brd_risk_score": 3.5,
                    "brd_needs_more_tests": 0,
                    "brd_comment": "Young patient with excellent prognosis",
                    "prp_bp": 120,
                    "prp_hba1c": 5.2,
                    "prp_infection_status": 0,
                    "ors_final_crossmatch": 1,
                    "ors_days_to_or": 1,
                    "ors_consent_status": "yes",
                    "srg_warm_isch_time": 28,
                    "srg_est_blood_loss": 180,
                    "srg_approach": "laparoscopic",
                    "icu_urine_hr": 180,
                    "icu_lactate": 0.9,
                    "icu_airway_stable": 1,
                    "wrd_pain_score": 2,
                    "wrd_walk_meters": 500,
                    "wrd_teaching_done": "yes",
                    "hom_creatinine": 1.2,
                    "hom_tac_trough": 8.5,
                    "hom_symptom": "none"
                }
            }
        ]

        for user_data in demo_users:
            print(f"\nCreating user: {user_data['email']}")

            user_id = uuid4()
            email_hash = hash_email(user_data['email'])
            password_hash = hash_password(user_data['password'])

            journey_started_at = (datetime.now(timezone.utc) - timedelta(days=7)).replace(tzinfo=None)

            await conn.execute(
                """
                INSERT INTO users (id, email_hash, password_hash, journey_stage, journey_started_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                email_hash,
                password_hash,
                user_data['stage'],
                journey_started_at
            )
            print(f"  ✓ User created with ID: {user_id}")

            await conn.execute(
                """
                INSERT INTO user_journey_state (user_id, current_stage_id, visit_number, journey_started_at)
                VALUES ($1, $2, 1, $3)
                """,
                user_id,
                user_data['stage'],
                journey_started_at
            )
            print(f"  ✓ Journey state initialized at {user_data['stage']}")

            await conn.execute(
                """
                INSERT INTO user_journey_path (user_id, stage_id, visit_number, is_current)
                VALUES ($1, $2, 1, TRUE)
                """,
                user_id,
                user_data['stage']
            )
            print(f"  ✓ Journey path entry created")

            await conn.execute(
                """
                INSERT INTO stage_transitions (
                    user_id, from_stage_id, to_stage_id, from_visit_number,
                    to_visit_number, transition_reason
                )
                VALUES ($1, NULL, $2, NULL, 1, $3)
                """,
                user_id,
                user_data['stage'],
                "Demo user initial signup"
            )
            print(f"  ✓ Initial transition recorded")

            stages_in_order = ["REFERRAL", "WORKUP", "MATCH", "DONOR", "BOARD", "PREOP", "ORSCHED", "SURG", "ICU", "WARD", "HOME", "COMPLX", "RELIST", "EXIT"]
            current_stage_index = stages_in_order.index(user_data['stage'])

            answer_count = 0
            for question_id, answer_value in user_data['answers'].items():
                if question_id.startswith("ref_"):
                    stage_id = "REFERRAL"
                elif question_id.startswith("wrk_"):
                    stage_id = "WORKUP"
                elif question_id.startswith("mtc_"):
                    stage_id = "MATCH"
                elif question_id.startswith("dnr_"):
                    stage_id = "DONOR"
                elif question_id.startswith("brd_"):
                    stage_id = "BOARD"
                elif question_id.startswith("prp_"):
                    stage_id = "PREOP"
                elif question_id.startswith("ors_"):
                    stage_id = "ORSCHED"
                elif question_id.startswith("srg_"):
                    stage_id = "SURG"
                elif question_id.startswith("icu_"):
                    stage_id = "ICU"
                elif question_id.startswith("wrd_"):
                    stage_id = "WARD"
                elif question_id.startswith("hom_"):
                    stage_id = "HOME"
                elif question_id.startswith("cpx_"):
                    stage_id = "COMPLX"
                elif question_id.startswith("rlt_"):
                    stage_id = "RELIST"
                elif question_id.startswith("ext_"):
                    stage_id = "EXIT"
                else:
                    stage_id = user_data['stage']

                if stages_in_order.index(stage_id) <= current_stage_index:
                    await conn.execute(
                        """
                        INSERT INTO user_answers (
                            user_id, stage_id, question_id, answer_value,
                            visit_number, version, is_current
                        )
                        VALUES ($1, $2, $3, $4, 1, 1, TRUE)
                        """,
                        user_id,
                        stage_id,
                        question_id,
                        json.dumps(answer_value)
                    )
                    answer_count += 1

            print(f"  ✓ {answer_count} answers added")
            print(f"  ✓ User {user_data['email']} fully seeded")

        print("\nDemo data seeded successfully!")
        print("\nDemo users created:")
        print("  - demo1@nvox.com (password: Demo1234) - At BOARD stage (mid-journey)")
        print("  - demo2@nvox.com (password: Demo1234) - At WARD stage (post-surgery)")
        print("  - demo3@nvox.com (password: Demo1234) - At HOME stage (successful completion)")
        print("\nNormal journey path demonstrated:")
        print("  REFERRAL → WORKUP → MATCH → DONOR → BOARD → PREOP → ORSCHED → SURG → ICU → WARD → HOME")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
