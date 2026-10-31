import json

from backend import db

CLAIM = "CLM-1001"


def approve(client, payout, claim=CLAIM):
    client.post(f"/api/claims/{claim}/start")
    return client.post(
        f"/api/claims/{claim}/decision",
        json={
            "decision": "approve",
            "payout": payout,
            "explanation": "Covered.",
            "policy_section": "Section 3",
        },
    )


def pay(client, amount, claim=CLAIM):
    return client.post(f"/api/claims/{claim}/payment", json={"amount": amount})


def state(client, claim=CLAIM):
    return client.get(f"/api/claims/{claim}").json()["state"]


def test_state_transitions(client):
    assert state(client) == "waiting"
    assert client.post(f"/api/claims/{CLAIM}/start").json()["state"] == "in_progress"
    assert client.post(f"/api/claims/{CLAIM}/start").status_code == 200
    assert approve(client, 420).json()["state"] == "decided"


def test_over_limit_needs_sign_off(client):
    assert approve(client, 1250).json()["state"] == "awaiting_sign_off"
    assert pay(client, 1250).status_code == 409
    assert client.get(f"/api/claims/{CLAIM}").json()["payment"] is None
    signed = client.post(f"/api/claims/{CLAIM}/sign-off", json={"handler_id": "HND-01"})
    assert signed.json()["state"] == "decided"
    assert signed.json()["sign_off"]["name"] == "Dana Whitfield"
    paid = pay(client, 1250)
    assert paid.status_code == 200
    assert paid.json()["payment"]["amount"] == 1250


def test_limit_boundary(client):
    approve(client, 1000)
    assert pay(client, 1000).status_code == 200
    approve(client, 1000.01, "CLM-1002")
    assert pay(client, 1000.01, "CLM-1002").status_code == 409


def test_pay_refusals(client):
    assert pay(client, 10).status_code == 409
    approve(client, 100)
    assert pay(client, 99).status_code == 409
    assert pay(client, 100).status_code == 200
    assert pay(client, 100).status_code == 409
    assert pay(client, 10, "CLM-0000").status_code == 404


def test_declined_and_referred_are_not_paid(client):
    for decision, claim in (("decline", "CLM-1002"), ("refer", "CLM-1003")):
        client.post(f"/api/claims/{claim}/start")
        body = {
            "decision": decision,
            "payout": 0,
            "explanation": "No.",
            "policy_section": "Section 9",
        }
        response = client.post(f"/api/claims/{claim}/decision", json=body)
        assert response.status_code == 200
        assert state(client, claim) == "decided"
        assert pay(client, 0, claim).status_code == 409


def test_decision_rules(client):
    url = f"/api/claims/{CLAIM}/decision"
    body = {
        "decision": "approve",
        "payout": 5,
        "explanation": "x",
        "policy_section": "y",
    }
    assert client.post(url, json=body).status_code == 409
    client.post(f"/api/claims/{CLAIM}/start")
    assert client.post(url, json={**body, "payout": 0}).status_code == 422
    assert client.post(url, json={**body, "decision": "decline"}).status_code == 422
    assert client.post(url, json=body).status_code == 200
    assert client.post(url, json=body).status_code == 409
    assert client.post(f"/api/claims/{CLAIM}/start").status_code == 409


def test_sign_off_refusals(client):
    url = f"/api/claims/{CLAIM}/sign-off"
    assert client.post(url, json={"handler_id": "HND-99"}).status_code == 404
    approve(client, 500)
    assert client.post(url, json={"handler_id": "HND-01"}).status_code == 409


def test_sign_off_needs_permission(client):
    approve(client, 1500)
    conn = db.connect()
    body = json.loads(
        conn.execute("SELECT body FROM records WHERE id = 'HND-03'").fetchone()[0]
    )
    body["can_approve_over_limit"] = False
    conn.execute("UPDATE records SET body = ? WHERE id = 'HND-03'", (json.dumps(body),))
    conn.commit()
    url = f"/api/claims/{CLAIM}/sign-off"
    assert client.post(url, json={"handler_id": "HND-03"}).status_code == 403


def test_steps(client):
    client.post(f"/api/claims/{CLAIM}/start")
    client.post(f"/api/claims/{CLAIM}/steps", json={"text": "Read the claim"})
    steps = client.post(f"/api/claims/{CLAIM}/steps", json={"text": "Read the policy"})
    assert [s["text"] for s in steps.json()["steps"]] == [
        "Read the claim",
        "Read the policy",
    ]
