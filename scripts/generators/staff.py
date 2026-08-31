from datetime import datetime
from backend.app.models.models import StaffLevel


def generate_staff_levels(session, services, capacities, rnd):
    staff_map = {}
    for s in services:
        beds = capacities.get(s.id, 10)
        # approximate staff: heads = beds * factor
        factor = 0.2 + rnd.random() * 0.3
        headcount = max(1, int(beds * factor))
        sl = StaffLevel(service_id=s.id, as_of=datetime.utcnow(), role="nurse", headcount=headcount, fte=float(headcount))
        session.add(sl)
        staff_map[s.id] = headcount
    session.flush()
    return staff_map
