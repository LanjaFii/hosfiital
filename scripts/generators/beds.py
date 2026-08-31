from datetime import datetime
from backend.app.models.models import Bed, ServiceCapacity, Service


def generate_beds_and_capacity(session, services, rnd):
    """Create beds and initial service_capacity for each service."""
    capacities = {}
    # reload service rows from DB to ensure stable PKs in this session
    codes = [s.code for s in services]
    db_services = {s.code: s for s in session.query(Service).filter(Service.code.in_(codes)).all()}
    for code in codes:
        s = db_services.get(code)
        # base beds by service code heuristic
        base = {
            'URG': 30,
            'MED': 40,
            'SURG': 35,
            'CARD': 25,
            'PED': 20,
            'MAT': 30,
        }.get(s.code, 10)
        # add small random variation
        beds_total = max(5, int(base * (0.9 + rnd.random() * 0.2)))
        # create beds
        for i in range(beds_total):
            b = Bed(service_id=s.id, bed_code=f"{s.code}-B{i+1}", active=True, created_at=datetime.utcnow())
            session.add(b)
        # create capacity record at start
        sc = ServiceCapacity(service_id=s.id, as_of=datetime.utcnow(), beds_total=beds_total, notes="initial")
        session.add(sc)
        capacities[s.id] = beds_total
    session.flush()
    return capacities
