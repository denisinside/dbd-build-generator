"""The streaming endpoint: progress frames, then the build, over one request.

The pipeline itself is covered elsewhere. What is worth pinning here is the
plumbing around it — worker thread, queue, SSE framing, the concurrency slot —
because a leak there is invisible until the generator stops answering.
"""

import json
import threading

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


@pytest.fixture(autouse=True)
def fresh_jobs():
    main._jobs.clear()
    yield
    main._jobs.clear()


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
    # The job id comes first, before anything can go wrong with the connection.
    assert [name for name, _ in events] == ["job", "step", "step", "build"]
    assert events[2][1] == {"stage": "research", "detail": "Verifying Sprint Burst"}
    assert events[-1][1]["build_title"] == "Fast Repairs"
    assert ObjectId.is_valid(events[-1][1]["id"])


# --- picking a build back up after the stream dies --------------------------


def test_a_finished_build_stays_readable_by_job_id(client, monkeypatch):
    """The case the whole job registry exists for: the client went away.

    A phone that locks kills the stream, not the build. If the result were
    only ever written into that stream, the visitor would have paid a minute
    and a slice of their quota for nothing.
    """
    api, _ = client
    monkeypatch.setattr(
        main,
        "run_generate_build",
        scripted_build([("research", "Verifying Sprint Burst")]),
    )

    events = read_events(api.post("/api/builds/stream", json={"prompt": "fast repair build"}))
    job_id = events[0][1]["job_id"]

    job = api.get(f"/api/builds/jobs/{job_id}").json()

    assert job["status"] == "done"
    assert job["steps"] == [{"stage": "research", "detail": "Verifying Sprint Burst"}]
    assert job["build"]["build_title"] == "Fast Repairs"
    assert ObjectId.is_valid(job["build"]["id"])
    # Owner identifiers are no more public here than they are in the feed.
    assert "session_id" not in job["build"]


def test_a_failed_build_reports_its_error_by_job_id(client, monkeypatch):
    api, _ = client
    monkeypatch.setattr(
        main,
        "run_generate_build",
        scripted_build([], failure=ValueError("ungroundable")),
    )

    events = read_events(api.post("/api/builds/stream", json={"prompt": "nonsense build"}))
    job = api.get(f"/api/builds/jobs/{events[0][1]['job_id']}").json()

    assert job["status"] == "error"
    assert job["error"]["status"] == 422
    assert "ungroundable" not in job["error"]["detail"]


def test_a_build_nobody_is_watching_still_lands_in_its_job(client, monkeypatch):
    """The disconnected phone, exactly: nothing ever drains the event queue.

    The slot is released only after the result has been published, so the
    build being finished is what this waits on.
    """
    api, builds = client
    monkeypatch.setattr(
        main, "run_generate_build", scripted_build([("research", "Verifying Sprint Burst")])
    )

    released = threading.Event()
    job_id, _unread = main.start_build_worker(
        "fast repair build", None, None, released.set
    )

    assert released.wait(timeout=10)
    assert builds.inserted[0]["prompt"] == "fast repair build"

    job = api.get(f"/api/builds/jobs/{job_id}").json()

    assert job["status"] == "done"
    assert job["build"]["build_title"] == "Fast Repairs"


def test_an_unknown_job_is_404_rather_than_a_crash(client):
    api, _ = client

    assert api.get("/api/builds/jobs/deadbeef").status_code == 404


def test_only_finished_jobs_are_forgotten(client, monkeypatch):
    """A running build has no deadline; dropping it would lose the result."""
    api, _ = client
    monkeypatch.setattr(main, "run_generate_build", scripted_build([]))

    events = read_events(api.post("/api/builds/stream", json={"prompt": "fast repair build"}))
    finished = events[0][1]["job_id"]
    main._jobs[finished]["finished_at"] -= main.JOB_RETENTION_SECONDS + 1
    main._jobs["still-running"] = {"status": "running", "steps": [], "build": None, "error": None}

    with main._jobs_lock:
        main.forget_stale_jobs()

    assert finished not in main._jobs
    assert "still-running" in main._jobs


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
