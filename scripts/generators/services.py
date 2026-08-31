from backend.app.models.models import Service


SERVICES_TEMPLATE = [
    ("URG", "Urgences"),
    ("MED", "Médecine générale"),
    ("SURG", "Chirurgie"),
    ("CARD", "Cardiologie"),
    ("PED", "Pédiatrie"),
    ("MAT", "Maternité"),
]


def generate_services(session):
    services = []
    codes = [c for c, _ in SERVICES_TEMPLATE]
    # fetch existing services to be idempotent
    existing = {s.code: s for s in session.query(Service).filter(Service.code.in_(codes)).all()}
    for code, name in SERVICES_TEMPLATE:
        if code in existing:
            services.append(existing[code])
        else:
            s = Service(code=code, name=name, description=f"Service {name}")
            session.add(s)
            services.append(s)
    session.flush()
    return services
