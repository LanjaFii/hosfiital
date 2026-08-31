from datetime import datetime
from backend.app.models.models import Budget, Expense


def generate_budgets(session, services, rnd, year=None):
    year = year or datetime.utcnow().year
    budgets = {}
    # fetch existing budgets for the year to avoid duplicates
    existing = {b.service_id: int(b.budget_amount) for b in session.query(Budget).filter(Budget.year == year).all()}
    for s in services:
        base = {
            'URG': 500000,
            'MED': 400000,
            'SURG': 450000,
            'CARD': 300000,
            'PED': 250000,
            'MAT': 350000,
        }.get(s.code, 100000)
        if s.id in existing:
            budgets[s.id] = existing[s.id]
            continue
            continue
        amount = int(base * (0.9 + rnd.random() * 0.2))
        b = Budget(service_id=s.id, year=year, budget_amount=amount, currency="EUR")
        session.add(b)
        budgets[s.id] = amount
    session.flush()
    return budgets


def generate_expenses_for_day(session, services, budgets, day, demand_factors, rnd, scenario=None):
    # generate expense entries influenced by demand_factors (dict service_id->factor)
    # ensure we use Service ids consistent with DB
    service_ids = [s.id for s in services]
    service_codes = {s.id: s.code for s in services}

    # For the special test-only 'budget_overrun' scenario we compute expenses
    # from a daily base independent from the annual budgets so short bursts
    # of high demand can realistically exceed the stored budget numbers.
    if scenario == 'budget_overrun':
        base_daily_by_code = {
            'URG': 10000,
            'MED': 8000,
            'SURG': 9000,
            'CARD': 6000,
            'PED': 4000,
            'MAT': 7000,
        }
        for sid in service_ids:
            factor = demand_factors.get(sid, 1.0)
            code = service_codes.get(sid)
            base = base_daily_by_code.get(code, 2000)
            amount = float(max(0.0, base * factor * (0.5 + rnd.random())))
            e = Expense(service_id=sid, period_start=day, period_end=day, amount=amount, currency="EUR", category="ops")
            session.add(e)
        session.flush()
        return

    for sid in service_ids:
        factor = demand_factors.get(sid, 1.0)
        base = budgets.get(sid, 100000) / 365.0
        amount = float(max(0.0, base * factor * (0.5 + rnd.random())))
        e = Expense(service_id=sid, period_start=day, period_end=day, amount=amount, currency="EUR", category="ops")
        session.add(e)
    session.flush()
