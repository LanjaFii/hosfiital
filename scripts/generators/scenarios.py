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
            return {sid: base * (0.9 + rnd.random() * 0.2) for sid in services_ids}
    elif scenario == "budget_overrun":
        def fn(day):
            # slightly increasing demand
            t = day / max(1, days - 1)
            base = 1.0 + 0.3 * t
            return {sid: base * (0.9 + rnd.random() * 0.2) for sid in services_ids}
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
            # delete application tables data
            for tbl in ['recommendations', 'analyses', 'energy_consumption', 'expenses', 'budgets', 'staff_levels', 'activity_records', 'occupancy_snapshots', 'admissions', 'service_capacity', 'beds', 'services']:
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
            generate_expenses_for_day(session, services, budgets, day, demand, rnd)
            generate_energy_for_day(session, services, day, demand, rnd)
            session.commit()
