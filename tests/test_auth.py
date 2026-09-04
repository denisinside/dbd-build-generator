"""Sign-in: token handling, redirect safety, and who may see whose builds."""

import time

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import auth
import main


SECRET = "test-secret-not-the-real-one"


@pytest.fixture(autouse=True)
def secret(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_SECRET", SECRET)


class FakeUsers:
    def __init__(self, documents=None):
        self.documents = list(documents or [])

    def find_one(self, query):
        for document in self.documents:
            if all(document.get(field) == value for field, value in query.items()):
                return document

        return None

    def update_one(self, query, update, upsert=False):
        existing = self.find_one(query)

        if existing is None:
            if not upsert:
                return

            existing = {"_id": ObjectId(), **query, **update.get("$setOnInsert", {})}
            self.documents.append(existing)

        existing.update(update.get("$set", {}))

        for field, amount in update.get("$inc", {}).items():
            existing[field] = existing.get(field, 0) + amount

    def create_index(self, *args, **kwargs):
        return None


class RecordingBuilds:
    """Captures the query instead of reimplementing MongoDB."""

    def __init__(self):
        self.query = None
        self.updates = []

    def find(self, query, projection=None):
        self.query = query
        return self

    def sort(self, *args):
        return self

    def limit(self, *args):
        return []

    def update_many(self, query, update):
        self.updates.append((query, update))
        return type("Result", (), {"modified_count": 2})()


# --- session tokens ---------------------------------------------------------


def test_a_token_round_trips_to_its_user():
    user_id = ObjectId()

    assert auth.read_token(auth.issue_token(user_id)) == str(user_id)


def test_a_token_signed_with_another_secret_is_refused(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_SECRET", "someone-elses-secret")
    forged = auth.issue_token(ObjectId())

    monkeypatch.setattr(auth, "AUTH_SECRET", SECRET)
    assert auth.read_token(forged) is None


def test_a_tampered_token_is_refused():
    token = auth.issue_token(ObjectId())
    head, payload, signature = token.split(".")

    assert auth.read_token(f"{head}.{payload}x.{signature}") is None


def test_an_expired_token_is_refused(monkeypatch):
    monkeypatch.setattr(auth, "SESSION_TTL_SECONDS", -1)

    assert auth.read_token(auth.issue_token(ObjectId())) is None


def test_a_token_carrying_junk_instead_of_a_user_id_is_refused():
    from joserfc import jwt

    now = int(time.time())
    token = jwt.encode(
        auth.JWT_HEADER,
        {"sub": "../../admin", "iat": now, "exp": now + 60},
        auth.session_key(),
    )

    assert auth.read_token(token) is None


@pytest.mark.parametrize(
    "header, expected",
    [
        ("Bearer abc", "abc"),
        ("bearer abc", "abc"),
        ("Basic abc", None),
        ("abc", None),
        ("Bearer ", None),
        (None, None),
    ],
)
def test_bearer_parsing(header, expected):
    assert auth.bearer_token(header) == expected


# --- redirect safety --------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "//evil.example",
        "https://evil.example",
        "http://evil.example/path",
        "",
        None,
        123,
    ],
)
def test_a_login_redirect_may_not_leave_the_site(raw):
    """`next` is attacker-controlled: a login link is a fine phishing vector."""
    assert auth.safe_redirect_path(raw) == "/"


@pytest.mark.parametrize("raw", ["/", "/build/abc", "/build/abc?x=1"])
def test_a_relative_redirect_is_kept(raw):
    assert auth.safe_redirect_path(raw) == raw


# --- accounts ---------------------------------------------------------------


def profile(**overrides):
    base = {
        "provider": "twitch",
        "provider_user_id": "42",
        "display_name": "streamer",
        "avatar_url": "https://cdn.example/a.png",
        "email": "s@example.com",
    }
    base.update(overrides)
    return base


def test_signing_in_twice_does_not_create_a_second_account(monkeypatch):
    users = FakeUsers()
    monkeypatch.setattr(auth, "users_collection", lambda: users)

    first = auth.upsert_user(profile())
    second = auth.upsert_user(profile(display_name="renamed"))

    assert len(users.documents) == 1
    assert first["_id"] == second["_id"]
    assert second["display_name"] == "renamed"


def test_the_same_id_from_another_provider_is_another_account(monkeypatch):
    users = FakeUsers()
    monkeypatch.setattr(auth, "users_collection", lambda: users)

    auth.upsert_user(profile(provider="twitch"))
    auth.upsert_user(profile(provider="discord"))

    assert len(users.documents) == 2


def test_a_disabled_account_is_signed_out_immediately(monkeypatch):
    user_id = ObjectId()
    users = FakeUsers([{"_id": user_id, "provider": "twitch", "disabled": True}])
    monkeypatch.setattr(auth, "users_collection", lambda: users)

    token = auth.issue_token(user_id)

    assert auth.optional_user(f"Bearer {token}") is None


def test_logging_out_invalidates_every_previously_issued_token(monkeypatch):
    user_id = ObjectId()
    users = FakeUsers([{"_id": user_id, "provider": "twitch"}])
    monkeypatch.setattr(auth, "users_collection", lambda: users)

    old_token = auth.issue_token(user_id)
    assert auth.optional_user(f"Bearer {old_token}") is not None

    auth.logout({"_id": user_id})

    # The old token is dead even though it has not expired.
    assert auth.optional_user(f"Bearer {old_token}") is None

    current_version = users.find_one({"_id": user_id})["token_version"]
    fresh_token = auth.issue_token(user_id, current_version)
    assert auth.optional_user(f"Bearer {fresh_token}") is not None


def test_a_live_account_resolves_from_its_token(monkeypatch):
    user_id = ObjectId()
    users = FakeUsers([{"_id": user_id, "provider": "twitch", "display_name": "streamer"}])
    monkeypatch.setattr(auth, "users_collection", lambda: users)

    user = auth.optional_user(f"Bearer {auth.issue_token(user_id)}")

    assert auth.public_user(user) == {
        "id": str(user_id),
        "provider": "twitch",
        "display_name": "streamer",
        "avatar_url": None,
    }


def test_an_account_id_never_leaves_in_a_build(monkeypatch):
    document = {
        "_id": ObjectId(),
        "build_title": "Fast Repairs",
        "session_id": "aaaabbbbccccdddd",
        "user_id": ObjectId(),
        "author_name": "streamer",
    }

    serialized = main.serialize_build(document)

    assert "user_id" not in serialized
    assert "session_id" not in serialized
    # The publishable half of the owner still travels, for feed credit.
    assert serialized["author_name"] == "streamer"


# --- ownership --------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    builds = RecordingBuilds()
    monkeypatch.setattr(main, "builds_collection", lambda: builds)
    api = TestClient(main.app)

    yield api, builds

    main.app.dependency_overrides.clear()


def sign_in_as(user):
    main.app.dependency_overrides[auth.optional_user] = lambda: user


def test_my_builds_are_filtered_by_account_when_signed_in(client):
    api, builds = client
    user_id = ObjectId()
    sign_in_as({"_id": user_id, "display_name": "streamer"})

    api.get("/api/builds?mine=1", headers={"X-Session-Id": "aaaabbbbccccdddd"})

    # The account wins over whatever anonymous token the browser still sends,
    # so signing in on a shared machine never surfaces the last person's builds.
    assert builds.query == {"user_id": user_id}


def test_my_builds_fall_back_to_the_browser_token_when_signed_out(client):
    api, builds = client
    sign_in_as(None)

    api.get("/api/builds?mine=1", headers={"X-Session-Id": "aaaabbbbccccdddd"})

    assert builds.query == {"session_id": "aaaabbbbccccdddd"}


def test_the_shared_feed_is_never_filtered(client):
    api, builds = client
    sign_in_as({"_id": ObjectId()})

    api.get("/api/builds")

    assert builds.query == {}


def test_a_signed_out_client_with_no_token_gets_nothing_rather_than_everything(client):
    api, builds = client
    sign_in_as(None)

    response = api.get("/api/builds?mine=1")

    assert response.json() == []
    assert builds.query is None


def test_claiming_moves_only_this_browsers_unowned_builds(client, monkeypatch):
    _, builds = client
    user = {"_id": ObjectId()}

    result = auth.claim_anonymous_builds(user, "aaaabbbbccccdddd")

    query, update = builds.updates[0]
    assert query == {"session_id": "aaaabbbbccccdddd", "user_id": None}
    assert update == {"$set": {"user_id": user["_id"]}}
    assert result == {"claimed": 2}


def test_claiming_without_a_browser_token_is_a_no_op(client):
    _, builds = client

    assert auth.claim_anonymous_builds({"_id": ObjectId()}, None) == {"claimed": 0}
    assert builds.updates == []


def test_a_junk_browser_token_claims_nothing(client):
    _, builds = client

    assert auth.claim_anonymous_builds({"_id": ObjectId()}, "../../etc/passwd") == {
        "claimed": 0
    }
    assert builds.updates == []


# --- the OAuth callback -----------------------------------------------------
#
# Where a provider's answer turns into an account. `main.app` only mounts the
# auth router when AUTH_SECRET is set at import time, so these build a small
# app around the same router instead.


def auth_app(monkeypatch, users):
    from fastapi import FastAPI
    from starlette.middleware.sessions import SessionMiddleware

    monkeypatch.setattr(auth, "users_collection", lambda: users)
    monkeypatch.setattr(auth, "FRONTEND_URL", "https://dbd.example")

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=SECRET)
    app.include_router(auth.router)

    return TestClient(app, follow_redirects=False)


class FakeOAuthClient:
    def __init__(self, token=None, failure=None):
        self.token = token
        self.failure = failure

    async def authorize_redirect(self, request, redirect_uri):
        from fastapi.responses import RedirectResponse

        return RedirectResponse("https://provider.example/authorize")

    async def authorize_access_token(self, request):
        if self.failure is not None:
            raise self.failure

        return self.token


def use_provider(monkeypatch, client, reader=None):
    monkeypatch.setitem(auth.PROVIDERS, "twitch", "Twitch")
    monkeypatch.setattr(auth.oauth, "create_client", lambda name: client)

    async def read(_http_client, _token):
        return reader or profile()

    monkeypatch.setitem(auth.PROFILE_READERS, "twitch", read)


def fragment_of(location):
    from urllib.parse import parse_qs, urlparse

    return parse_qs(urlparse(location).fragment)


def test_a_completed_handshake_creates_an_account_and_hands_back_a_token(monkeypatch):
    users = FakeUsers()
    api = auth_app(monkeypatch, users)
    use_provider(monkeypatch, FakeOAuthClient(token={"access_token": "provider-token"}))

    response = api.get("/auth/twitch/callback")

    assert response.is_redirect
    location = response.headers["location"]
    assert location.startswith("https://dbd.example/auth/callback#")

    # The token rides in the fragment, never the query string.
    assert "?token=" not in location

    fragment = fragment_of(location)
    assert auth.read_token(fragment["token"][0]) == str(users.documents[0]["_id"])
    assert users.documents[0]["display_name"] == "streamer"


def test_a_refused_handshake_creates_nothing(monkeypatch):
    users = FakeUsers()
    api = auth_app(monkeypatch, users)
    use_provider(monkeypatch, FakeOAuthClient(failure=RuntimeError("state mismatch")))

    response = api.get("/auth/twitch/callback")

    assert response.is_redirect
    assert response.headers["location"] == (
        "https://dbd.example/auth/callback?error=sign_in_failed"
    )
    assert users.documents == []


def test_an_unknown_provider_is_a_404(monkeypatch):
    api = auth_app(monkeypatch, FakeUsers())

    assert api.get("/auth/myspace/login").status_code == 404
    assert api.get("/auth/myspace/callback").status_code == 404


def test_the_landing_path_survives_the_handshake(monkeypatch):
    users = FakeUsers()
    api = auth_app(monkeypatch, users)
    use_provider(monkeypatch, FakeOAuthClient(token={"access_token": "provider-token"}))

    # The login step is what stores the path in the OAuth session cookie.
    api.get("/auth/twitch/login?next=/build/abc")
    response = api.get("/auth/twitch/callback")

    assert fragment_of(response.headers["location"])["next"] == ["/build/abc"]


def test_an_offsite_landing_path_is_replaced_before_it_is_stored(monkeypatch):
    users = FakeUsers()
    api = auth_app(monkeypatch, users)
    use_provider(monkeypatch, FakeOAuthClient(token={"access_token": "provider-token"}))

    api.get("/auth/twitch/login?next=https://evil.example/phish")
    response = api.get("/auth/twitch/callback")

    assert fragment_of(response.headers["location"])["next"] == ["/"]


# --- when sign-in is possible at all ----------------------------------------


@pytest.mark.parametrize(
    "secret, providers, expected",
    [
        ("a-secret", {"twitch": "Twitch"}, True),
        ("a-secret", {}, False),
        ("", {"twitch": "Twitch"}, False),
        ("", {}, False),
    ],
)
def test_sign_in_is_only_available_with_a_secret_and_a_provider(
    monkeypatch, secret, providers, expected
):
    """A secret with no provider credentials still leaves nobody able to log in."""
    monkeypatch.setattr(auth, "AUTH_SECRET", secret)
    monkeypatch.setattr(auth, "PROVIDERS", providers)

    assert auth.sign_in_available() is expected


def test_the_provider_list_is_empty_when_sign_in_is_off(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_SECRET", "")

    assert auth.list_providers() == []
