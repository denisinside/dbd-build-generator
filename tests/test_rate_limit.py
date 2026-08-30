"""The hourly cap on the one endpoint that spends money."""

import pytest
from bson import ObjectId
from fastapi import HTTPException

import main


class FakeRequest:
    def __init__(self, host):
        self.client = type("Client", (), {"host": host})()


def account(limit=None, user_id=None):
    return {"_id": user_id or ObjectId(), "generate_limit_per_hour": limit}


@pytest.fixture(autouse=True)
def clean_counters():
    main._recent_generates.clear()
    yield
    main._recent_generates.clear()


def test_requests_under_the_limit_pass(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 3)
    request = FakeRequest("1.2.3.4")

    for _ in range(3):
        main.enforce_generate_limit(request, None)


def test_the_next_request_is_rejected(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 2)
    request = FakeRequest("1.2.3.4")
    main.enforce_generate_limit(request, None)
    main.enforce_generate_limit(request, None)

    with pytest.raises(HTTPException) as rejected:
        main.enforce_generate_limit(request, None)

    assert rejected.value.status_code == 429
    assert "2 per hour" in rejected.value.detail
    assert int(rejected.value.headers["Retry-After"]) > 0


def test_clients_have_separate_budgets(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    main.enforce_generate_limit(FakeRequest("1.2.3.4"), None)
    main.enforce_generate_limit(FakeRequest("5.6.7.8"), None)


def test_hits_expire_after_the_window(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    request = FakeRequest("1.2.3.4")
    main.enforce_generate_limit(request, None)

    # Pretend the recorded hit happened just over an hour ago.
    hits = main._recent_generates["ip:1.2.3.4"]
    hits[0] -= main.RATE_LIMIT_WINDOW_SECONDS + 1

    main.enforce_generate_limit(request, None)
    assert len(hits) == 1


def test_a_zero_limit_disables_the_cap(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 0)
    request = FakeRequest("1.2.3.4")

    for _ in range(50):
        main.enforce_generate_limit(request, None)

    assert not main._recent_generates


def test_a_client_without_an_address_still_counts(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    request = FakeRequest("1.2.3.4")
    request.client = None
    main.enforce_generate_limit(request, None)

    with pytest.raises(HTTPException):
        main.enforce_generate_limit(request, None)


def test_signed_in_users_are_counted_per_account_not_per_address(monkeypatch):
    """The point of the whole exercise: one CGNAT address is not one person."""
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    shared_address = FakeRequest("1.2.3.4")

    main.enforce_generate_limit(shared_address, account())
    main.enforce_generate_limit(shared_address, account())

    # And the same account is still capped, whichever address it comes from.
    same_user = account(user_id=ObjectId())
    main.enforce_generate_limit(FakeRequest("1.2.3.4"), same_user)

    with pytest.raises(HTTPException):
        main.enforce_generate_limit(FakeRequest("9.9.9.9"), same_user)


def test_a_per_account_override_raises_the_ceiling(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    generous = account(limit=3)

    for _ in range(3):
        main.enforce_generate_limit(FakeRequest("1.2.3.4"), generous)

    with pytest.raises(HTTPException) as rejected:
        main.enforce_generate_limit(FakeRequest("1.2.3.4"), generous)

    assert "3 per hour" in rejected.value.detail


def test_an_anonymous_client_cannot_spend_an_accounts_budget(monkeypatch):
    monkeypatch.setattr(main, "GENERATE_LIMIT_PER_HOUR", 1)
    user = account()

    main.enforce_generate_limit(FakeRequest("1.2.3.4"), user)
    # Same address, but signed out: a separate bucket, so it still passes.
    main.enforce_generate_limit(FakeRequest("1.2.3.4"), None)
