"""The hourly cap on the one endpoint that spends money."""

import pytest
from fastapi import HTTPException

import main


class FakeRequest:
    def __init__(self, host):
        self.client = type("Client", (), {"host": host})()


@pytest.fixture(autouse=True)
def clean_counters():
    main._recent_generates.clear()
    yield
    main._recent_generates.clear()


def test_requests_under_the_limit_pass(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 3)
    request = FakeRequest("1.2.3.4")

    for _ in range(3):
        main.enforce_generate_limit(request)


def test_the_next_request_is_rejected(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 2)
    request = FakeRequest("1.2.3.4")
    main.enforce_generate_limit(request)
    main.enforce_generate_limit(request)

    with pytest.raises(HTTPException) as rejected:
        main.enforce_generate_limit(request)

    assert rejected.value.status_code == 429
    assert "2 per hour" in rejected.value.detail
    assert int(rejected.value.headers["Retry-After"]) > 0


def test_clients_have_separate_budgets(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    main.enforce_generate_limit(FakeRequest("1.2.3.4"))
    main.enforce_generate_limit(FakeRequest("5.6.7.8"))


def test_hits_expire_after_the_window(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    request = FakeRequest("1.2.3.4")
    main.enforce_generate_limit(request)

    # Pretend the recorded hit happened just over an hour ago.
    hits = main._recent_generates["1.2.3.4"]
    hits[0] -= main.RATE_LIMIT_WINDOW_SECONDS + 1

    main.enforce_generate_limit(request)
    assert len(hits) == 1


def test_a_zero_limit_disables_the_cap(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 0)
    request = FakeRequest("1.2.3.4")

    for _ in range(50):
        main.enforce_generate_limit(request)

    assert not main._recent_generates


def test_a_client_without_an_address_still_counts(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    request = FakeRequest("1.2.3.4")
    request.client = None
    main.enforce_generate_limit(request)

    with pytest.raises(HTTPException):
        main.enforce_generate_limit(request)
