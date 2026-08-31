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
    for code, name in SERVICES_TEMPLATE:
        s = Service(code=code, name=name, description=f"Service {name}")
        session.add(s)
        services.append(s)
    session.flush()
    return services
