"""OAuth sign-in for Twitch, Discord and Google.

Sessions are Bearer tokens, not cookies: the frontend and the API may end up
on different sites, and a cross-site cookie needs `SameSite=None` — which
Safari's ITP and the third-party cookie wind-down keep chipping away at. A
Bearer token works in either topology and, as a bonus, carries no ambient
credentials, so there is no CSRF surface on the API itself.

The OAuth handshake still uses a short-lived signed cookie (Starlette's
SessionMiddleware) to hold `state`, because that is what makes the callback
verifiable. It only lives for the seconds between the redirect out and back.

Provider access tokens are used once, to read the profile, and then dropped.
Nothing about a user's Twitch or Google account is stored beyond an id, a
display name and an avatar URL, so there is no refresh logic and nothing worth
stealing here.
"""

import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuth
from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import OctKey
from pymongo import ASCENDING


AUTH_SECRET = os.getenv("AUTH_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# 30 days. Long, because there is no refresh flow to renew it and re-running
# the OAuth dance is the only way back in. Revocation does not depend on this:
# `current_user` reads the user document on every request, so setting
# `disabled` locks an account out immediately regardless of token lifetime.
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))

JWT_HEADER = {"alg": "HS256"}

router = APIRouter(prefix="/auth", tags=["auth"])
oauth = OAuth()


def _provider_configured(*names):
    return all(os.getenv(name) for name in names)


# Discord is plain OAuth2 with no discovery document; Twitch and Google both
# publish one. Each provider's profile shape differs enough that a shared
# "userinfo" abstraction would only hide the differences, so each one reads
# its own.
PROVIDERS = {}

if _provider_configured("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET"):
    oauth.register(
        name="twitch",
        client_id=os.getenv("TWITCH_CLIENT_ID"),
        client_secret=os.getenv("TWITCH_CLIENT_SECRET"),
        server_metadata_url="https://id.twitch.tv/oauth2/.well-known/openid-configuration",
        client_kwargs={"scope": "openid user:read:email"},
    )
    PROVIDERS["twitch"] = "Twitch"

if _provider_configured("DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET"):
    oauth.register(
        name="discord",
        client_id=os.getenv("DISCORD_CLIENT_ID"),
        client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        client_kwargs={"scope": "identify email"},
    )
    PROVIDERS["discord"] = "Discord"

if _provider_configured("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"):
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    PROVIDERS["google"] = "Google"


def sign_in_available():
    """True when signing in is actually possible on this deployment.

    Anything that *requires* an account has to check this: with no secret or
    no provider credentials there is no way to get one, and demanding one
    would leave the app unusable rather than protected.
    """
    return bool(AUTH_SECRET and PROVIDERS)


def users_collection():
    from generate_build import get_mongo_db

    return get_mongo_db()["users"]


def ensure_indexes():
    """One account per identity. Called from the app lifespan."""
    users_collection().create_index(
        [("provider", ASCENDING), ("provider_user_id", ASCENDING)],
        unique=True,
    )


CLAIMS = jwt.JWTClaimsRegistry(
    sub={"essential": True},
    exp={"essential": True},
)


def session_key():
    return OctKey.import_key(AUTH_SECRET)


def issue_token(user_id):
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + SESSION_TTL_SECONDS}

    return jwt.encode(JWT_HEADER, payload, session_key())


def read_token(token):
    """The user id inside a session token, or None if it does not hold up."""
    try:
        decoded = jwt.decode(token, session_key(), algorithms=["HS256"])
        CLAIMS.validate(decoded.claims)
    except (JoseError, ValueError):
        return None

    subject = decoded.claims.get("sub")

    return subject if ObjectId.is_valid(subject or "") else None


def bearer_token(authorization):
    if not isinstance(authorization, str):
        return None

    scheme, _, token = authorization.partition(" ")

    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def optional_user(authorization: str = Header(default=None)):
    """The signed-in user, or None. Never raises: most routes are public."""
    token = bearer_token(authorization)

    if token is None or not AUTH_SECRET:
        return None

    user_id = read_token(token)

    if user_id is None:
        return None

    # Read on every authenticated request, so `disabled` takes effect at once
    # rather than whenever a 30-day token happens to expire.
    user = users_collection().find_one({"_id": ObjectId(user_id)})

    if user is None or user.get("disabled"):
        return None

    return user


def required_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to do that.")

    return user


def public_user(user):
    """The parts of a user document that may leave the server."""
    return {
        "id": str(user["_id"]),
        "provider": user["provider"],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
    }


def upsert_user(profile):
    """Create or refresh the account behind one provider identity."""
    now = datetime.now(timezone.utc)
    users_collection().update_one(
        {"provider": profile["provider"], "provider_user_id": profile["provider_user_id"]},
        {
            "$set": {
                "display_name": profile["display_name"],
                "avatar_url": profile.get("avatar_url"),
                "email": profile.get("email"),
                "last_login_at": now,
            },
            "$setOnInsert": {"created_at": now, "disabled": False},
        },
        upsert=True,
    )

    return users_collection().find_one(
        {"provider": profile["provider"], "provider_user_id": profile["provider_user_id"]}
    )


async def fetch_twitch_profile(client, token):
    response = await client.get(
        "https://api.twitch.tv/helix/users",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "Client-Id": os.getenv("TWITCH_CLIENT_ID"),
        },
    )
    response.raise_for_status()
    user = response.json()["data"][0]

    return {
        "provider": "twitch",
        "provider_user_id": user["id"],
        "display_name": user.get("display_name") or user.get("login"),
        "avatar_url": user.get("profile_image_url"),
        "email": user.get("email"),
    }


async def fetch_discord_profile(client, token):
    response = await client.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    response.raise_for_status()
    user = response.json()

    if user.get("avatar"):
        avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
    else:
        # Default avatars for the post-discriminator username scheme.
        avatar = f"https://cdn.discordapp.com/embed/avatars/{(int(user['id']) >> 22) % 6}.png"

    return {
        "provider": "discord",
        "provider_user_id": user["id"],
        "display_name": user.get("global_name") or user.get("username"),
        "avatar_url": avatar,
        "email": user.get("email"),
    }


async def fetch_google_profile(client, token):
    user = token.get("userinfo") or {}

    if not user:
        response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
        response.raise_for_status()
        user = response.json()

    return {
        "provider": "google",
        "provider_user_id": user["sub"],
        "display_name": user.get("name") or user.get("email"),
        "avatar_url": user.get("picture"),
        "email": user.get("email"),
    }


PROFILE_READERS = {
    "twitch": fetch_twitch_profile,
    "discord": fetch_discord_profile,
    "google": fetch_google_profile,
}


def safe_redirect_path(raw):
    """A path on our own frontend, never somewhere else.

    Without this the `next` parameter is an open redirect: a link to our own
    login URL could bounce a signed-in user straight to an attacker's page.
    """
    if not isinstance(raw, str) or not raw.startswith("/") or raw.startswith("//"):
        return "/"

    return raw


@router.get("/providers")
def list_providers():
    """What the sign-in UI should offer. Empty when nothing is configured."""
    if not AUTH_SECRET:
        return []

    return [{"id": key, "name": name} for key, name in PROVIDERS.items()]


@router.get("/{provider}/login")
async def login(provider: str, request: Request, next: str = "/"):
    if provider not in PROVIDERS or not AUTH_SECRET:
        raise HTTPException(status_code=404, detail="Unknown sign-in provider")

    request.session["post_login_path"] = safe_redirect_path(next)
    redirect_uri = str(request.url_for("callback", provider=provider))

    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback", name="callback")
async def callback(provider: str, request: Request):
    if provider not in PROVIDERS or not AUTH_SECRET:
        raise HTTPException(status_code=404, detail="Unknown sign-in provider")

    path = safe_redirect_path(request.session.pop("post_login_path", "/"))

    try:
        token = await oauth.create_client(provider).authorize_access_token(request)

        async with httpx.AsyncClient(timeout=10) as client:
            profile = await PROFILE_READERS[provider](client, token)
    except Exception:
        # A failed handshake is a normal thing (denied consent, expired state),
        # not a server error worth a stack trace in the user's face.
        return RedirectResponse(f"{FRONTEND_URL}/auth/callback?error=sign_in_failed")

    user = upsert_user(profile)

    # The token goes in the fragment, not the query: fragments are not sent to
    # servers, do not appear in access logs, and are not passed on in Referer.
    fragment = urlencode({"token": issue_token(user["_id"]), "next": path})

    return RedirectResponse(f"{FRONTEND_URL}/auth/callback#{fragment}")


@router.get("/me")
def me(user=Depends(required_user)):
    return public_user(user)


@router.post("/claim")
def claim_anonymous_builds(
    user=Depends(required_user),
    x_session_id: str = Header(default=None),
):
    """Move this browser's anonymous builds onto the account that just signed in.

    Without it, everything a tester generated before logging in silently stops
    being theirs.
    """
    from main import builds_collection, clean_session_id

    session_id = clean_session_id(x_session_id)

    if session_id is None:
        return {"claimed": 0}

    result = builds_collection().update_many(
        {"session_id": session_id, "user_id": None},
        {"$set": {"user_id": user["_id"]}},
    )

    return {"claimed": result.modified_count}
