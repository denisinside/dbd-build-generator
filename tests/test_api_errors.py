"""What the caller sees when generation fails, instead of a bare 500."""

import pytest
from fastapi import HTTPException

import main


def call_generate(monkeypatch, outcome):
    monkeypatch.setattr(main, "run_generate_build", outcome)

    with pytest.raises(HTTPException) as failure:
        main.generate_build(main.GenerateBuildRequest(prompt="fast gen repair build"))

    return failure.value


def raises(error):
    def outcome(_prompt, **_kwargs):
        raise error

    return outcome


def test_ungroundable_build_is_422(monkeypatch):
    failure = call_generate(monkeypatch, raises(ValueError("could not ground build")))

    assert failure.status_code == 422
    assert "could not ground build" not in failure.detail


def test_upstream_failure_is_502(monkeypatch):
    failure = call_generate(monkeypatch, raises(TimeoutError("openrouter timed out")))

    assert failure.status_code == 502
    assert "openrouter" not in failure.detail.lower()


def test_a_502_refunds_the_quota_hit_it_charged(monkeypatch):
    """The failure is ours, so the caller should not lose an attempt to it."""
    monkeypatch.setattr(main, "run_generate_build", raises(TimeoutError("down")))
    refunded = []
    monkeypatch.setattr(main, "refund_generate_hit", refunded.append)

    with pytest.raises(HTTPException):
        main.create_build("fast gen repair build", rate_limit_client="ip:1.2.3.4")

    assert refunded == ["ip:1.2.3.4"]


def test_a_422_does_not_refund_the_quota_hit(monkeypatch):
    """The model answered several times; only a service failure gets refunded."""
    monkeypatch.setattr(main, "run_generate_build", raises(ValueError("bad build")))
    refunded = []
    monkeypatch.setattr(main, "refund_generate_hit", refunded.append)

    with pytest.raises(HTTPException):
        main.create_build("fast gen repair build", rate_limit_client="ip:1.2.3.4")

    assert refunded == []


def test_a_rejected_prompt_is_still_400(monkeypatch):
    failure = call_generate(
        monkeypatch,
        lambda _prompt, **_kwargs: {
            "error": {"code": "invalid_build_request", "message": "Не білд."}
        },
    )

    assert failure.status_code == 400
    assert failure.detail == "Не білд."
