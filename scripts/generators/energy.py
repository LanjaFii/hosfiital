from backend.app.models.models import EnergyConsumption


def generate_energy_for_day(session, services, day, activity_factors, rnd):
    for s in services:
        act = activity_factors.get(s.id, 1.0)
        base_kwh = {
            'URG': 1000,
            'MED': 800,
            'SURG': 900,
            'CARD': 600,
            'PED': 400,
            'MAT': 700,
        }.get(s.code, 300)
        consumption = float(base_kwh * act * (0.8 + rnd.random() * 0.4))
        ec = EnergyConsumption(service_id=s.id, measured_at=day, consumption_kwh=consumption, cost=None, source="sim")
        session.add(ec)
    session.flush()
