"""The streaming endpoint: progress frames, then the build, over one request.

The pipeline itself is covered elsewhere. What is worth pinning here is the
plumbing around it — worker thread, queue, SSE framing, the concurrency slot —
because a leak there is invisible until the generator stops answering.
"""

import json

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import main


class FakeBuilds:
    def __init__(self):
        self.inserted = []

    def insert_one(self, document):
        self.inserted.append(document)
        return type("Result", (), {"inserted_id": ObjectId()})()

    def create_index(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def fresh_rate_limit():
    """Every test starts with the hourly cap untouched."""
    main._recent_generates.clear()
    yield
    main._recent_generates.clear()


@pytest.fixture
def client(monkeypatch):
    builds = FakeBuilds()
    monkeypatch.setattr(main, "builds_collection", lambda: builds)
    # The lifespan pings MongoDB; TestClient without a context manager skips it.
    return TestClient(main.app), builds


def scripted_build(steps, result=None, failure=None):
    def run(prompt, on_step=None):
        for stage, detail in steps:
            on_step(stage, detail)

        if failure is not None:
            raise failure

        return result or {"build_title": "Fast Repairs", "role": "Survivor"}

    return run


def read_events(response):
    events = []

    for frame in response.text.split("\n\n"):
        if not frame.strip():
            continue

        name = next(line[len("event:"):].strip() for line in frame.split("\n")
                    if line.startswith("event:"))
        data = next(line[len("data:"):].strip() for line in frame.split("\n")
                    if line.startswith("data:"))
        events.append((name, json.loads(data)))

    return events


def test_steps_arrive_before_the_build(client, monkeypatch):
    api, builds = client
    monkeypatch.setattr(
        main,
        "run_generate_build",
        scripted_build([("classifying", "Reading your request"),
                        ("research", "Verifying Sprint Burst")]),
    )

    response = api.post("/api/builds/stream", json={"prompt": "fast repair build"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = read_events(response)
    assert [name for name, _ in events] == ["step", "step", "build"]
    assert events[1][1] == {"stage": "research", "detail": "Verifying Sprint Burst"}
    assert events[-1][1]["build_title"] == "Fast Repairs"
    assert ObjectId.is_valid(events[-1][1]["id"])


def test_a_failure_arrives_as_an_error_frame(client, monkeypatch):
    api, _ = client
    monkeypatch.setattr(
        main,
        "run_generate_build",
        scripted_build([("classifying", "Reading your request")],
                       failure=ValueError("ungroundable")),
    )

    events = read_events(api.post("/api/builds/stream", json={"prompt": "nonsense build"}))

    name, payload = events[-1]
    assert name == "error"
    assert payload["status"] == 422
    # The upstream message never reaches the browser.
    assert "ungroundable" not in payload["detail"]


def test_the_session_header_marks_ownership_but_never_leaves(client, monkeypatch):
    api, builds = client
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))

    session = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    events = read_events(
        api.post(
            "/api/builds/stream",
            json={"prompt": "fast repair build"},
            headers={"X-Session-Id": session},
        )
    )

    assert builds.inserted[0]["session_id"] == session
    # An owner token is not public data, and the feed is.
    assert "session_id" not in events[-1][1]


def test_a_junk_session_header_is_dropped_rather_than_stored(client, monkeypatch):
    api, builds = client
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))

    api.post(
        "/api/builds/stream",
        json={"prompt": "fast repair build"},
        headers={"X-Session-Id": "../../etc/passwd"},
    )

    assert builds.inserted[0]["session_id"] is None


def test_the_slot_is_returned_after_every_build(client, monkeypatch):
    """A leaked slot is silent until the generator stops answering entirely."""
    api, _ = client
    monkeypatch.setattr(
        main,
        "run_generate_build",
        scripted_build([], failure=RuntimeError("upstream is down")),
    )

    for _ in range(main.GENERATE_CONCURRENCY + 2):
        response = api.post("/api/builds/stream", json={"prompt": "fast repair build"})
        assert response.status_code == 200


def test_a_busy_generator_answers_503_instead_of_hanging(client, monkeypatch):
    api, _ = client

    for _ in range(main.GENERATE_CONCURRENCY):
        assert main._generate_slots.acquire(blocking=False)

    try:
        response = api.post("/api/builds/stream", json={"prompt": "fast repair build"})

        assert response.status_code == 503
        assert response.headers["Retry-After"] == "30"
    finally:
        for _ in range(main.GENERATE_CONCURRENCY):
            main._generate_slots.release()


# --- the account gate -------------------------------------------------------


def signed_in_as(user):
    main.app.dependency_overrides[main.auth.optional_user] = lambda: user


def test_generating_needs_an_account_once_sign_in_is_possible(client, monkeypatch):
    """Hiding the button is not enough: this is a plain HTTP call."""
    api, builds = client
    monkeypatch.setattr(main.auth, "sign_in_available", lambda: True)
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))
    signed_in_as(None)

    try:
        for path in ["/api/builds/stream", "/api/builds/generate"]:
            response = api.post(path, json={"prompt": "fast repair build"})

            assert response.status_code == 401, path
            assert "Sign in" in response.json()["detail"]

        assert builds.inserted == []
    finally:
        main.app.dependency_overrides.clear()


def test_a_signed_in_caller_generates_normally(client, monkeypatch):
    api, builds = client
    monkeypatch.setattr(main.auth, "sign_in_available", lambda: True)
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))
    signed_in_as({"_id": ObjectId(), "display_name": "streamer"})

    try:
        response = api.post("/api/builds/stream", json={"prompt": "fast repair build"})

        assert response.status_code == 200
        assert builds.inserted[0]["author_name"] == "streamer"
    finally:
        main.app.dependency_overrides.clear()


def test_generation_stays_open_when_nobody_can_sign_in(client, monkeypatch):
    """Requiring an account nobody can create would brick the app, not guard it."""
    api, builds = client
    monkeypatch.setattr(main.auth, "sign_in_available", lambda: False)
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))
    signed_in_as(None)

    try:
        response = api.post("/api/builds/stream", json={"prompt": "fast repair build"})

        assert response.status_code == 200
        assert builds.inserted[0]["user_id"] is None
    finally:
        main.app.dependency_overrides.clear()
