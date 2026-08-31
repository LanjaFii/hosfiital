from typing import Iterable


class ValidationError(Exception):
    pass


def ensure_non_negative_expenses(expenses: Iterable[dict]):
    bad = [e for e in expenses if e['amount'] is None or float(e['amount']) < 0]
    if bad:
        raise ValidationError(f"Expenses contain negative or null amounts: {len(bad)} rows")


def ensure_dates_consistent(rows: Iterable[dict], date_fields=('period_start', 'period_end')):
    bad = []
    for r in rows:
        start = r.get(date_fields[0])
        end = r.get(date_fields[1])
        if start and end and start > end:
            bad.append(r)
    if bad:
        raise ValidationError(f"Found {len(bad)} rows with start > end")


def ensure_no_duplicate_snapshots(rows: Iterable[dict], key_fields=('service_id', 'snapshot_at')):
    seen = set()
    dup = []
    for r in rows:
        key = tuple(r[k] for k in key_fields)
        if key in seen:
            dup.append(r)
        else:
            seen.add(key)
    if dup:
        raise ValidationError(f"Found {len(dup)} duplicate snapshots")
