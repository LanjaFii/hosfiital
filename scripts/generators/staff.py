from datetime import datetime
from backend.app.models.models import StaffLevel, Service


def generate_staff_levels(session, services, capacities, rnd, start_date=None):
    staff_map = {}
    # staff levels are effective at the start of the simulated window.
    as_of = datetime.combine(start_date, datetime.min.time()) if start_date else datetime.utcnow()
    # reload service rows to ensure ids match DB
    codes = [s.code for s in services]
    db_services = {s.code: s for s in session.query(Service).filter(Service.code.in_(codes)).all()}
    for code, s_obj in db_services.items():
        beds = capacities.get(s_obj.id, 10)
        # approximate staff: heads = beds * factor
        factor = 0.2 + rnd.random() * 0.3
        headcount = max(1, int(beds * factor))
        sl = StaffLevel(service_id=s_obj.id, as_of=as_of, role="nurse", headcount=headcount, fte=float(headcount))
        session.add(sl)
        staff_map[s_obj.id] = headcount
    session.flush()
    return staff_map
