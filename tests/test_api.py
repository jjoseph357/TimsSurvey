import threading
import time

import pytest

from app import create_app
from jobs import JobManager


class FakeAutomator:
    """Stands in for a Selenium automator; blocks until the test releases it."""

    def __init__(self, site, gate):
        self.site = site
        self.gate = gate
        self.status = "Idle"
        self.progress = 0
        self.logs = []
        self.result_code = None
        self.result_image_path = None
        self.code_image_path = None

    def start_survey(self, code, on_success=None):
        self.status = "Running"
        self.gate.wait(timeout=5)
        self.result_code = "VAL-" + code[-4:]
        self.status = "Completed"
        self.progress = 100
        if on_success:
            on_success()


@pytest.fixture
def gate():
    g = threading.Event()
    yield g
    g.set()


def make_client(gate, max_concurrent=10):
    manager = JobManager(lambda site: FakeAutomator(site, gate), max_concurrent=max_concurrent)
    return create_app(manager, counter_file=None).test_client()


def wait_for(predicate, timeout=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def jobs(client):
    return client.get("/api/jobs").get_json()["jobs"]


def test_submitting_several_codes_tracks_each_job(gate):
    client = make_client(gate)

    resp = client.post("/api/start", json={"codes": [
        "1234-5678-9012-3456-78901",
        "3BNM6JL4021TG12",
    ]})

    assert resp.status_code == 200
    listed = jobs(client)
    assert [(j["code"], j["site"]) for j in listed] == [
        ("123456789012345678901", "tims"),
        ("3BNM6JL4021TG12", "dq"),
    ]
    assert {j["id"] for j in listed} == set(resp.get_json()["job_ids"])


def test_codes_beyond_the_limit_queue_then_all_complete(gate):
    client = make_client(gate, max_concurrent=2)
    codes = ["111111111111111111111", "222222222222222222222", "333333333333333333333"]

    client.post("/api/start", json={"codes": codes})

    assert wait_for(lambda: [j["state"] for j in jobs(client)] == ["running", "running", "queued"])
    gate.set()
    assert wait_for(lambda: all(j["state"] == "done" for j in jobs(client)))
    assert [j["result_code"] for j in jobs(client)] == ["VAL-1111", "VAL-2222", "VAL-3333"]
    assert client.get("/api/jobs").get_json()["global_counter"] == 13


def test_rejects_unrecognized_code_but_starts_the_valid_ones(gate):
    client = make_client(gate)

    resp = client.post("/api/start", json={"codes": ["12345", "3BNM6JL4021TG12"]})

    assert resp.status_code == 200
    assert "12345" in resp.get_json()["errors"][0]
    assert [j["code"] for j in jobs(client)] == ["3BNM6JL4021TG12"]


def test_all_codes_invalid_is_an_error(gate):
    client = make_client(gate)

    resp = client.post("/api/start", json={"codes": ["12345"]})

    assert resp.status_code == 400
    assert jobs(client) == []
