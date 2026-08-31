from backend.app.models.models import EnergyConsumption


def generate_energy_for_day(session, services, day, activity_factors, rnd):
    # use service ids and codes from DB-consistent objects
    service_ids = [s.id for s in services]
    service_codes = {s.id: s.code for s in services}
    for sid in service_ids:
        act = activity_factors.get(sid, 1.0)
        code = service_codes.get(sid)
        base_kwh = {
            'URG': 1000,
            'MED': 800,
            'SURG': 900,
            'CARD': 600,
            'PED': 400,
            'MAT': 700,
        }.get(code, 300)
        consumption = float(base_kwh * act * (0.8 + rnd.random() * 0.4))
        ec = EnergyConsumption(service_id=sid, measured_at=day, consumption_kwh=consumption, cost=None, source="sim")
        session.add(ec)
    session.flush()
