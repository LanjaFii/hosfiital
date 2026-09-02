from datetime import timedelta
import random
from backend.app.db.session import SessionLocal, engine
from scripts.generators.services import generate_services
from scripts.generators.beds import generate_beds_and_capacity
from scripts.generators.staff import generate_staff_levels
from scripts.generators.finance import generate_budgets, generate_expenses_for_day
from scripts.generators.energy import generate_energy_for_day
from scripts.generators.admissions import simulate_admissions


def demand_fn_factory(scenario, services_ids, days, rnd):
    # returns a function day_offset -> dict(service_id -> factor)
    if scenario == "normal":
        def fn(day):
            return {sid: 1.0 + rnd.random() * 0.1 for sid in services_ids}
    elif scenario == "saturation":
        # progressive linear increase from 1.0 to 1.6 over days
        def fn(day):
            t = day / max(1, days - 1)
            base = 1.0 + 0.6 * t
            # amplify demand to reliably saturate capacity over the scenario
            # multiplier chosen to be large enough to fill beds over a few days
            mult = 8.0
            # bias one service (first) to ensure a per-service saturation can appear
            out = {}
            for i, sid in enumerate(services_ids):
                factor = base * (0.9 + rnd.random() * 0.2) * mult
                if i == 0:
                    factor = factor * 2.5
                out[sid] = factor
            return out
    elif scenario == "budget_overrun":
        def fn(day):
            # slightly increasing demand
            t = day / max(1, days - 1)
            base = 1.0 + 0.3 * t
            # amplify expense-driving demand so daily expenses can exceed prorated budgets
            # multiplier chosen to make short scenarios (few days) reliably exceed budget thresholds
            mult = 60.0
            return {sid: base * (0.9 + rnd.random() * 0.2) * mult for sid in services_ids}
    else:
        def fn(day):
            return {sid: 1.0 for sid in services_ids}
    return fn


def run_scenario(name: str, days: int, seed: int, start_date, reset: bool = False):
    rnd = random.Random(seed)
    with SessionLocal() as session:
        # reset data if requested
        from sqlalchemy import text

        if reset:
            # Truncate all application tables to ensure clean state and reset sequences
            # Use RESTART IDENTITY CASCADE to avoid FK / sequence issues between runs
            # Use ordered deletes with commits to avoid DB-level deadlocks in CI/local
            tables = [
                'recommendations', 'analyses', 'energy_consumption', 'expenses', 'budgets',
                'staff_levels', 'activity_records', 'occupancy_snapshots', 'admissions',
                'service_capacity', 'beds', 'services', 'kpi_daily'
            ]
            for tbl in tables:
                session.execute(text(f"DELETE FROM {tbl};"))
                session.commit()

        # services
        services = generate_services(session)
        session.commit()

        # beds and capacity
        capacities = generate_beds_and_capacity(session, services, rnd)
        session.commit()

        # staff
        staff = generate_staff_levels(session, services, capacities, rnd)
        session.commit()

        # budgets
        budgets = generate_budgets(session, services, rnd)
        session.commit()

        # For the test-only "budget_overrun" scenario, reduce budgets deterministically
        # to make short-run expense spikes realistically exceed prorated budgets.
        if name == 'budget_overrun':
            from backend.app.models.models import Budget
            from datetime import datetime

            year = datetime.utcnow().year
            # scale down factor chosen to remain realistic but induce overruns in short scenarios
            scale_down = 8
            for sid, amt in list(budgets.items()):
                new_amt = max(1000, int(amt / scale_down))
                session.query(Budget).filter(Budget.service_id == sid, Budget.year == year).update({"budget_amount": new_amt})
                budgets[sid] = new_amt
            session.commit()

        # prepare demand function
        services_ids = [s.id for s in services]
        demand_fn = demand_fn_factory(name, services_ids, days, rnd)

        # simulate admissions, occupancy, activity
        simulate_admissions(session, services, capacities, start_date, days, rnd, demand_fn)
        session.commit()

        # generate per-day expenses and energy based on activity
        for day_offset in range(days):
            day = start_date + timedelta(days=day_offset)
            demand = demand_fn(day_offset)
            generate_expenses_for_day(session, services, budgets, day, demand, rnd, name)
            generate_energy_for_day(session, services, day, demand, rnd)
            session.commit()
