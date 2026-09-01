from datetime import datetime, timedelta
from backend.app.models.models import Admission, OccupancySnapshot, ActivityRecord


def simulate_admissions(session, services, capacities, start_date, days, rnd, scenario_demand_fn):
    # maintain active patients per service as list of discharge dates
    active = {s.id: [] for s in services}
    activity_records = []
    # LOS generation in original script: los_days = max(1, int(2 + rnd.random() * 6)) -> values in {2..7}
    MAX_LOS = 7
    last_day = start_date + timedelta(days=days - 1)

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
            # generate target admissions up to available slots
            admissions_today = min(target_adm, available)
            discharges_today = 0
            # create admissions
            created = 0
            for i in range(admissions_today):
                remaining_days = (last_day - day.date()).days
                los_days = max(1, int(2 + rnd.random() * 6))
                if los_days > remaining_days:
                    # this admission would finish after the window: mark as ongoing
                    discharged_at = None
                    status = "active"
                    # in-memory sentinel so patient counts as active through window
                    sentinel_discharge = datetime.combine(last_day + timedelta(days=MAX_LOS + 1), datetime.max.time())
                    session.add(Admission(service_id=s.id, admitted_at=day, discharged_at=discharged_at, patient_hash=None, status=status))
                    active[s.id].append(sentinel_discharge)
                    created += 1
                else:
                    discharged_at = day + timedelta(days=los_days)
                    status = "discharged"
                    session.add(Admission(service_id=s.id, admitted_at=day, discharged_at=discharged_at, patient_hash=None, status=status))
                    active[s.id].append(discharged_at)
                    created += 1
            admissions_today = created
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
