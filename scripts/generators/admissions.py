from datetime import datetime, timedelta
from backend.app.models.models import Admission, OccupancySnapshot, ActivityRecord


def simulate_admissions(session, services, capacities, start_date, days, rnd, scenario_demand_fn):
    # maintain active patients per service as list of discharge dates
    active = {s.id: [] for s in services}
    activity_records = []
    for day_offset in range(days):
        day = datetime.combine(start_date + timedelta(days=day_offset), datetime.min.time())
        demand_factors = scenario_demand_fn(day_offset)
        # for each service, generate admissions up to capacity
        for s in services:
            cap = capacities.get(s.id, 10)
            factor = demand_factors.get(s.id, 1.0)
            # baseline daily admissions per service
            base_adm = max(1, int(cap * 0.05))
            target_adm = int(base_adm * factor)
            # determine available slots
            curr_occ = len([d for d in active[s.id] if d > day])
            available = max(0, cap - curr_occ)
            admissions_today = min(target_adm, available)
            discharges_today = 0
            # create admissions
            for i in range(admissions_today):
                los_days = max(1, int(2 + rnd.random() * 6))
                discharged_at = day + timedelta(days=los_days)
                adm = Admission(service_id=s.id, admitted_at=day, discharged_at=discharged_at, patient_hash=None, status="discharged")
                session.add(adm)
                active[s.id].append(discharged_at)
            # compute discharges (those with discharge == today)
            before = len(active[s.id])
            active[s.id] = [d for d in active[s.id] if d > day]
            after = len(active[s.id])
            discharges_today = before - after

            # occupancy snapshot
            occupied = len([d for d in active[s.id] if d > day])
            snap = OccupancySnapshot(service_id=s.id, snapshot_at=day, occupied_beds=occupied, available_beds=max(0, cap - occupied))
            session.add(snap)

            # activity record (daily)
            ar = ActivityRecord(service_id=s.id, period_start=day, period_end=day, admissions_count=admissions_today, discharges_count=discharges_today, visits_count=0, metric_payload={})
            session.add(ar)

        session.flush()
