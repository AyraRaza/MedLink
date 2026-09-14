from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import BiomedicalResource, Organization, User


# Avoid duplicate metadata index declarations already present on resources.
for table in Base.metadata.tables.values():
    seen_names = set()
    for index in list(table.indexes):
        if index.name in seen_names:
            table.indexes.remove(index)
        else:
            seen_names.add(index.name)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

organizations = [
    Organization(name="Alpha", registration_number="ALPHA", verification_status="VERIFIED"),
    Organization(name="Beta", registration_number="BETA", verification_status="VERIFIED"),
    Organization(name="Other", registration_number="OTHER", verification_status="VERIFIED"),
    Organization(name="Pending", registration_number="PENDING", verification_status="PENDING"),
]
db.add_all(organizations)
db.flush()

users = [
    User(email="alpha@example.com", password_hash="test", full_name="Alpha", organization_id=organizations[0].id),
    User(email="beta@example.com", password_hash="test", full_name="Beta", organization_id=organizations[1].id),
    User(email="other@example.com", password_hash="test", full_name="Other", organization_id=organizations[2].id),
    User(email="pending@example.com", password_hash="test", full_name="Pending", organization_id=organizations[3].id),
]
db.add_all(users)
db.flush()

resource = BiomedicalResource(
    organization_id=organizations[1].id,
    name="Shared supply",
    category="MEDICAL_SUPPLY",
    quantity=10,
    unit="units",
    availability_status="AVAILABLE",
    condition="NEW",
)
own_resource = BiomedicalResource(
    organization_id=organizations[0].id,
    name="Private supply",
    category="MEDICAL_SUPPLY",
    quantity=4,
    unit="units",
    availability_status="AVAILABLE",
    condition="NEW",
)
db.add_all([resource, own_resource])
db.commit()


def override_db():
    yield db


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def headers(user):
    token = create_access_token(str(user.id), user.role, user.organization_id)
    return {"Authorization": f"Bearer {token}"}


alpha_headers = headers(users[0])
beta_headers = headers(users[1])
other_headers = headers(users[2])
pending_headers = headers(users[3])

try:
    discovery = client.get("/api/v1/resource-sharing/resources", headers=alpha_headers)
    assert discovery.status_code == 200
    assert {item["id"] for item in discovery.json()} == {resource.id}

    request_response = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": resource.id, "requested_quantity": 3},
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["id"]
    assert request_response.json()["status"] == "PENDING"

    assert client.post(
        f"/api/v1/resource-requests/{request_id}/fulfill", headers=beta_headers
    ).status_code == 400
    assert client.post(
        f"/api/v1/resource-requests/{request_id}/approve", headers=beta_headers
    ).status_code == 200

    assert client.post(
        f"/api/v1/resource-requests/{request_id}/fulfill", headers=alpha_headers
    ).status_code == 403
    assert client.post(
        f"/api/v1/resource-requests/{request_id}/fulfill", headers=other_headers
    ).status_code in (403, 404)

    before_fulfillment = db.get(BiomedicalResource, resource.id).quantity
    fulfillment = client.post(
        f"/api/v1/resource-requests/{request_id}/fulfill", headers=beta_headers
    )
    assert fulfillment.status_code == 200
    assert fulfillment.json()["status"] == "FULFILLED"
    assert db.get(BiomedicalResource, resource.id).quantity == before_fulfillment - 3

    assert client.post(
        f"/api/v1/resource-requests/{request_id}/fulfill", headers=beta_headers
    ).status_code == 400
    assert client.post(
        f"/api/v1/resource-requests/{request_id}/receive", headers=beta_headers
    ).status_code == 403

    before_receipt = db.get(BiomedicalResource, resource.id).quantity
    receipt = client.post(
        f"/api/v1/resource-requests/{request_id}/receive", headers=alpha_headers
    )
    assert receipt.status_code == 200
    assert receipt.json()["status"] == "RECEIVED"
    assert db.get(BiomedicalResource, resource.id).quantity == before_receipt
    assert client.post(
        f"/api/v1/resource-requests/{request_id}/receive", headers=alpha_headers
    ).status_code == 400

    pending_request = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": resource.id, "requested_quantity": 1},
    )
    assert pending_request.status_code == 201
    pending_id = pending_request.json()["id"]
    assert client.post(
        f"/api/v1/resource-requests/{pending_id}/fulfill", headers=beta_headers
    ).status_code == 400
    assert client.post(
        f"/api/v1/resource-requests/{pending_id}/cancel", headers=alpha_headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/resource-requests/{pending_id}/fulfill", headers=beta_headers
    ).status_code == 400

    rejected_request = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": resource.id, "requested_quantity": 1},
    )
    assert rejected_request.status_code == 201
    rejected_id = rejected_request.json()["id"]
    assert client.post(
        f"/api/v1/resource-requests/{rejected_id}/reject", headers=beta_headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/resource-requests/{rejected_id}/fulfill", headers=beta_headers
    ).status_code == 400

    insufficient_request = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": resource.id, "requested_quantity": 5},
    )
    assert insufficient_request.status_code == 201
    insufficient_id = insufficient_request.json()["id"]
    assert client.post(
        f"/api/v1/resource-requests/{insufficient_id}/approve", headers=beta_headers
    ).status_code == 200
    db.execute(
        update(BiomedicalResource)
        .where(BiomedicalResource.id == resource.id)
        .values(quantity=1)
    )
    db.commit()
    assert client.post(
        f"/api/v1/resource-requests/{insufficient_id}/fulfill", headers=beta_headers
    ).status_code == 400
    assert db.get(BiomedicalResource, resource.id).quantity == 1

    unavailable_request = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": resource.id, "requested_quantity": 1},
    )
    assert unavailable_request.status_code == 201
    unavailable_id = unavailable_request.json()["id"]
    assert client.post(
        f"/api/v1/resource-requests/{unavailable_id}/approve", headers=beta_headers
    ).status_code == 200
    db.execute(
        update(BiomedicalResource)
        .where(BiomedicalResource.id == resource.id)
        .values(quantity=1, availability_status="UNAVAILABLE")
    )
    db.commit()
    assert client.post(
        f"/api/v1/resource-requests/{unavailable_id}/fulfill", headers=beta_headers
    ).status_code == 400
    assert db.get(BiomedicalResource, resource.id).quantity == 1

    own_request = client.post(
        "/api/v1/resource-requests",
        headers=alpha_headers,
        json={"resource_id": own_resource.id, "requested_quantity": 1},
    )
    assert own_request.status_code == 400

    assert client.get("/api/v1/resources", headers=alpha_headers).status_code == 200
    assert client.get(
        f"/api/v1/resources/{resource.id}", headers=alpha_headers
    ).status_code == 403
    assert client.get(
        "/api/v1/resource-sharing/resources", headers=pending_headers
    ).status_code == 403

    print("Phase 5B smoke test passed")
finally:
    app.dependency_overrides.pop(get_db, None)
    db.close()
