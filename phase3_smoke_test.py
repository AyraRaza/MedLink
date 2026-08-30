from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Auth still works
register_a = client.post(
    "/api/v1/auth/register",
    json={"email": "orga@example.com", "password": "StrongPass123!", "full_name": "Org A User"},
)
assert register_a.status_code == 201, register_a.text
register_b = client.post(
    "/api/v1/auth/register",
    json={"email": "orgb@example.com", "password": "StrongPass123!", "full_name": "Org B User"},
)
assert register_b.status_code == 201, register_b.text

login_a = client.post(
    "/api/v1/auth/login",
    json={"email": "orga@example.com", "password": "StrongPass123!"},
)
assert login_a.status_code == 200, login_a.text
user_a_headers = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

login_b = client.post(
    "/api/v1/auth/login",
    json={"email": "orgb@example.com", "password": "StrongPass123!"},
)
assert login_b.status_code == 200, login_b.text
user_b_headers = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

# Organization creation still works
org_a = client.post(
    "/api/v1/organizations",
    json={
        "name": "Alpha Hospital",
        "registration_number": "REG-ALPHA-001",
        "organization_type": "HOSPITAL",
        "email": "alpha@example.com",
        "phone": "1234567890",
        "address": "Street 1",
        "city": "Delhi",
        "state": "DL",
        "pincode": "110001",
    },
    headers=user_a_headers,
)
assert org_a.status_code == 201, org_a.text
org_a_id = org_a.json()["id"]

org_b = client.post(
    "/api/v1/organizations",
    json={
        "name": "Beta Hospital",
        "registration_number": "REG-BETA-001",
        "organization_type": "HOSPITAL",
        "email": "beta@example.com",
        "phone": "0987654321",
        "address": "Street 2",
        "city": "Mumbai",
        "state": "MH",
        "pincode": "400001",
    },
    headers=user_b_headers,
)
assert org_b.status_code == 201, org_b.text
org_b_id = org_b.json()["id"]

# User without organization cannot use resources
register_no_org = client.post(
    "/api/v1/auth/register",
    json={"email": "noorg@example.com", "password": "StrongPass123!", "full_name": "No Org User"},
)
assert register_no_org.status_code == 201, register_no_org.text
login_no_org = client.post(
    "/api/v1/auth/login",
    json={"email": "noorg@example.com", "password": "StrongPass123!"},
)
assert login_no_org.status_code == 200, login_no_org.text
no_org_headers = {"Authorization": f"Bearer {login_no_org.json()['access_token']}"}
assert client.post(
    "/api/v1/resources",
    json={"name": "Broken machine", "category": "EQUIPMENT", "quantity": 1, "unit": "units"},
    headers=no_org_headers,
).status_code == 403
assert client.get("/api/v1/resources", headers=no_org_headers).status_code in (403, 200)

# Create resources and ensure org assignment is correct
resource_a = client.post(
    "/api/v1/resources",
    json={
        "name": "Ventilator",
        "category": "EQUIPMENT",
        "description": "ICU ventilator",
        "quantity": 3,
        "unit": "units",
        "availability_status": "AVAILABLE",
        "condition": "NEW",
    },
    headers=user_a_headers,
)
assert resource_a.status_code == 201, resource_a.text
resource_a_data = resource_a.json()
assert resource_a_data["organization_id"] == org_a_id

resource_b = client.post(
    "/api/v1/resources",
    json={
        "name": "Paracetamol",
        "category": "MEDICINE",
        "description": "Pain relief",
        "quantity": 500,
        "unit": "tablets",
        "availability_status": "LOW_STOCK",
        "condition": "GOOD",
        "expiry_date": "2027-01-01T00:00:00Z",
    },
    headers=user_b_headers,
)
assert resource_b.status_code == 201, resource_b.text
resource_b_data = resource_b.json()
assert resource_b_data["organization_id"] == org_b_id

# Org-scoped listing
list_a = client.get("/api/v1/resources", headers=user_a_headers)
assert list_a.status_code == 200, list_a.text
ids_a = {item["id"] for item in list_a.json()}
assert resource_a_data["id"] in ids_a
assert resource_b_data["id"] not in ids_a

list_b = client.get("/api/v1/resources", headers=user_b_headers)
assert list_b.status_code == 200, list_b.text
ids_b = {item["id"] for item in list_b.json()}
assert resource_b_data["id"] in ids_b
assert resource_a_data["id"] not in ids_b

# Cross-organization access is denied
assert client.get(f"/api/v1/resources/{resource_b_data['id']}", headers=user_a_headers).status_code in (403, 404)
assert client.get(f"/api/v1/resources/{resource_a_data['id']}", headers=user_b_headers).status_code in (403, 404)

# Fetch, update, validate, and deactivate
resource_detail = client.get(f"/api/v1/resources/{resource_a_data['id']}", headers=user_a_headers)
assert resource_detail.status_code == 200, resource_detail.text

resource_update = client.patch(
    f"/api/v1/resources/{resource_a_data['id']}",
    json={
        "quantity": 2,
        "availability_status": "LOW_STOCK",
        "description": "Updated ICU ventilator",
    },
    headers=user_a_headers,
)
assert resource_update.status_code == 200, resource_update.text
assert resource_update.json()["quantity"] == 2
assert resource_update.json()["description"] == "Updated ICU ventilator"

negative_quantity = client.patch(
    f"/api/v1/resources/{resource_a_data['id']}",
    json={"quantity": -1},
    headers=user_a_headers,
)
assert negative_quantity.status_code == 422, negative_quantity.text

invalid_enum = client.post(
    "/api/v1/resources",
    json={"name": "Bad item", "category": "INVALID", "quantity": 1, "unit": "units"},
    headers=user_a_headers,
)
assert invalid_enum.status_code == 422, invalid_enum.text

deactivate = client.delete(f"/api/v1/resources/{resource_a_data['id']}", headers=user_a_headers)
assert deactivate.status_code == 200, deactivate.text
assert deactivate.json()["is_active"] is False

health = client.get("/health")
assert health.status_code == 200, health.text
assert health.json()["status"] == "ok"

print("API verification passed")
