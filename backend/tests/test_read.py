import re
from pathlib import Path

from backend import db

ROOT = Path(__file__).parent.parent.parent


def test_seed_counts():
    conn = db.connect()
    counts = dict(
        conn.execute("SELECT kind, COUNT(*) FROM records GROUP BY kind").fetchall()
    )
    assert counts == {
        "claims": 25,
        "policies": 50,
        "customers": 49,
        "plans": 3,
        "handlers": 3,
        "company": 1,
    }


def test_seed_is_not_repeated():
    db.connect().close()
    conn = db.connect()
    assert conn.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 131


def test_list_claims_all_waiting(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {claim["state"] for claim in claims} == {"waiting"}
    assert claims[0]["customer_name"] == "Maya Patel"


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["claim_id"] == "CLM-1001"
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert claim["documents"]
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["steps"] == []


def test_get_records(client):
    assert client.get("/api/policies/POL-2001").json()["plan"] == "premium"
    assert client.get("/api/plans/premium").json()["deductible"] == 50
    assert client.get("/api/customers/CUS-3001").json()["previous_claims"]
    assert len(client.get("/api/handlers").json()) == 3
    assert client.get("/api/company").json()["payout_approval_limit"] == 1000


def test_unknown_record(client):
    assert client.get("/api/claims/CLM-0000").status_code == 404


def test_documents(client):
    assert "Policy Wording" in client.get("/api/policy-wording").json()["text"]
    assert "UnderCover Agent" in client.get("/api/instructions").json()["text"]


def test_sources_never_open_the_answer_key():
    sources = [*ROOT.glob("backend/**/*.py"), *ROOT.glob("agent/**/*.py")]
    for source in sources:
        if source != Path(__file__):
            assert not re.search(r"evals", source.read_text(encoding="utf-8")), source


def test_operations_follow_the_api_rules(client):
    schema = client.get("/openapi.json").json()
    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            assert op.get("operationId"), (path, method)
            description = op.get("description", "")
            assert description, (path, method)
            assert "\n" not in description.strip(), (path, method)
            assert all(p["required"] for p in op.get("parameters", [])), (path, method)
            if "requestBody" in op:
                assert op["requestBody"]["required"], (path, method)
                ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                body = schema["components"]["schemas"][ref.split("/")[-1]]
                assert set(body["properties"]) == set(body["required"]), (path, method)
