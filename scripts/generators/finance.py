from datetime import datetime
from backend.app.models.models import Budget, Expense


def generate_budgets(session, services, rnd, year=None):
    year = year or datetime.utcnow().year
    budgets = {}
    for s in services:
        base = {
            'URG': 500000,
            'MED': 400000,
            'SURG': 450000,
            'CARD': 300000,
            'PED': 250000,
            'MAT': 350000,
        }.get(s.code, 100000)
        amount = int(base * (0.9 + rnd.random() * 0.2))
        b = Budget(service_id=s.id, year=year, budget_amount=amount, currency="EUR")
        session.add(b)
        budgets[s.id] = amount
    session.flush()
    return budgets


def generate_expenses_for_day(session, services, budgets, day, demand_factors, rnd):
    # generate expense entries influenced by demand_factors (dict service_id->factor)
    for s in services:
        factor = demand_factors.get(s.id, 1.0)
        base = budgets.get(s.id, 100000) / 365.0
        amount = float(max(0.0, base * factor * (0.5 + rnd.random())))
        e = Expense(service_id=s.id, period_start=day, period_end=day, amount=amount, currency="EUR", category="ops")
        session.add(e)
    session.flush()
