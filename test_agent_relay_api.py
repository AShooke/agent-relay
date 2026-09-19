"""HTTP integration test for the running Agent Relay service."""

from __future__ import annotations

import os
import uuid

import httpx


def register(client: httpx.Client, name: str) -> tuple[dict, dict[str, str]]:
    response = client.post("/api/v1/agents", json={"name": name})
    assert response.status_code == 201
    data = response.json()
    return data, {"Authorization": f"Bearer {data['token']}"}


def test_acceptance_scenario_one_against_running_api():
    base_url = os.getenv("RELAY_API_URL", "http://localhost:8000")
    with httpx.Client(base_url=base_url, timeout=10) as client:
        sender, sender_headers = register(client, f"sender-{uuid.uuid4().hex[:8]}")
        recipient, recipient_headers = register(client, f"recipient-{uuid.uuid4().hex[:8]}")

        sent = client.post(
            "/api/v1/tasks",
            headers=sender_headers,
            json={"to": recipient["agent_id"], "input": "hello relay"},
        )
        assert sent.status_code == 201
        task_id = sent.json()["task_id"]

        claim = client.post(
            "/api/v1/tasks/claim",
            headers=recipient_headers,
            json={"worker_id": "compose-test-worker", "wait_seconds": 0},
        )
        assert claim.status_code == 200
        claim_data = claim.json()
        assert claim_data["task_id"] == task_id

        completed = client.post(
            f"/api/v1/tasks/{task_id}/complete",
            headers=recipient_headers,
            json={"claim_token": claim_data["claim_token"], "output": "HELLO RELAY"},
        )
        assert completed.status_code == 200

        result = client.get(f"/api/v1/tasks/{task_id}", headers=sender_headers)
        assert result.status_code == 200
        assert result.json()["status"] == "completed"