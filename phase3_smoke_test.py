from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


test_id = uuid4().hex
password = "StrongPass123!"
emails = {
    "org_a": f"phase3-org-a-{test_id}@example.com",
    "org_b": f"phase3-org-b-{test_id}@example.com",
    "no_org": f"phase3-no-org-{test_id}@example.com",
}
organization_emails = {
    "org_a": f"phase3-org-a-{test_id}@example.com",
    "org_b": f"phase3-org-b-{test_id}@example.com",
}
registration_numbers = {
    "org_a": f"PHASE3-ALPHA-{test_id}".upper(),
    "org_b": f"PHASE3-BETA-{test_id}".upper(),
}

# SQLAlchemy metadata includes duplicate declarations for some indexed columns.
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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
previous_get_db_override = app.dependency_overrides.get(get_db)
had_get_db_override = get_db in app.dependency_overrides


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


try:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        for key, full_name in (
            ("org_a", "Org A User"),
            ("org_b", "Org B User"),
            ("no_org", "User Without Organization"),
        ):
            registration = client.post(
                "/api/v1/auth/register",
                json={
                    "email": emails[key],
                    "password": password,
                    "full_name": full_name,
                },
            )
            assert registration.status_code == 201, registration.text
            assert registration.json()["email"] == emails[key]

        user_headers = {}
        for key in emails:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": emails[key], "password": password},
            )
            assert login.status_code == 200, login.text
            assert login.json()["token_type"] == "bearer"
            user_headers[key] = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }

        organization_payloads = {
            "org_a": {
                "name": f"Alpha Hospital {test_id}",
                "registration_number": registration_numbers["org_a"],
                "organization_type": "HOSPITAL",
                "email": organization_emails["org_a"],
                "phone": "1234567890",
                "address": "Street 1",
                "city": "Delhi",
                "state": "DL",
                "pincode": "110001",
            },
            "org_b": {
                "name": f"Beta Hospital {test_id}",
                "registration_number": registration_numbers["org_b"],
                "organization_type": "HOSPITAL",
                "email": organization_emails["org_b"],
                "phone": "0987654321",
                "address": "Street 2",
                "city": "Mumbai",
                "state": "MH",
                "pincode": "400001",
            },
        }
        organization_ids = {}
        for key in ("org_a", "org_b"):
            organization = client.post(
                "/api/v1/organizations",
                json=organization_payloads[key],
                headers=user_headers[key],
            )
            assert organization.status_code == 201, organization.text
            organization_data = organization.json()
            assert organization_data["registration_number"] == registration_numbers[key]
            assert organization_data["email"] == organization_emails[key]
            assert organization_data["verification_status"] == "PENDING"
            organization_ids[key] = organization_data["id"]

        no_org_resource = client.post(
            "/api/v1/resources",
            json={
                "name": "Broken machine",
                "category": "EQUIPMENT",
                "quantity": 1,
                "unit": "units",
            },
            headers=user_headers["no_org"],
        )
        assert no_org_resource.status_code == 403, no_org_resource.text
        no_org_listing = client.get(
            "/api/v1/resources",
            headers=user_headers["no_org"],
        )
        assert no_org_listing.status_code == 403, no_org_listing.text

        resource_payloads = {
            "org_a": {
                "name": "Ventilator",
                "category": "EQUIPMENT",
                "description": "ICU ventilator",
                "quantity": 3,
                "unit": "units",
                "availability_status": "AVAILABLE",
                "condition": "NEW",
            },
            "org_b": {
                "name": "Paracetamol",
                "category": "MEDICINE",
                "description": "Pain relief",
                "quantity": 500,
                "unit": "tablets",
                "availability_status": "LOW_STOCK",
                "condition": "GOOD",
                "expiry_date": "2027-01-01T00:00:00Z",
            },
        }
        resources = {}
        for key in ("org_a", "org_b"):
            resource = client.post(
                "/api/v1/resources",
                json=resource_payloads[key],
                headers=user_headers[key],
            )
            assert resource.status_code == 201, resource.text
            resource_data = resource.json()
            assert resource_data["organization_id"] == organization_ids[key]
            resources[key] = resource_data

        for key, other_key in (("org_a", "org_b"), ("org_b", "org_a")):
            listing = client.get("/api/v1/resources", headers=user_headers[key])
            assert listing.status_code == 200, listing.text
            listed_ids = {item["id"] for item in listing.json()}
            assert resources[key]["id"] in listed_ids
            assert resources[other_key]["id"] not in listed_ids

            cross_org_access = client.get(
                f"/api/v1/resources/{resources[other_key]['id']}",
                headers=user_headers[key],
            )
            assert cross_org_access.status_code == 403, cross_org_access.text

        resource_id = resources["org_a"]["id"]
        resource_detail = client.get(
            f"/api/v1/resources/{resource_id}",
            headers=user_headers["org_a"],
        )
        assert resource_detail.status_code == 200, resource_detail.text

        update_payload = {
            "quantity": 2,
            "availability_status": "LOW_STOCK",
            "description": "Updated ICU ventilator",
        }
        resource_update = client.patch(
            f"/api/v1/resources/{resource_id}",
            json=update_payload,
            headers=user_headers["org_a"],
        )
        assert resource_update.status_code == 200, resource_update.text
        updated_resource = resource_update.json()
        assert updated_resource["quantity"] == update_payload["quantity"]
        assert updated_resource["availability_status"] == update_payload["availability_status"]
        assert updated_resource["description"] == update_payload["description"]

        negative_quantity = client.patch(
            f"/api/v1/resources/{resource_id}",
            json={"quantity": -1},
            headers=user_headers["org_a"],
        )
        assert negative_quantity.status_code == 422, negative_quantity.text

        invalid_enum = client.post(
            "/api/v1/resources",
            json={
                "name": "Bad item",
                "category": "INVALID",
                "quantity": 1,
                "unit": "units",
            },
            headers=user_headers["org_a"],
        )
        assert invalid_enum.status_code == 422, invalid_enum.text

        deactivation = client.delete(
            f"/api/v1/resources/{resource_id}",
            headers=user_headers["org_a"],
        )
        assert deactivation.status_code == 200, deactivation.text
        assert deactivation.json()["is_active"] is False
        org_a_listing = client.get(
            "/api/v1/resources",
            headers=user_headers["org_a"],
        )
        assert org_a_listing.status_code == 200, org_a_listing.text
        assert resource_id not in {item["id"] for item in org_a_listing.json()}

        health = client.get("/health")
        assert health.status_code == 200, health.text
        assert health.json()["status"] == "ok"

    print("Phase 3 smoke test passed")
finally:
    if had_get_db_override:
        app.dependency_overrides[get_db] = previous_get_db_override
    else:
        app.dependency_overrides.pop(get_db, None)
    engine.dispose()