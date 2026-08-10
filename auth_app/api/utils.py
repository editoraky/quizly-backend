"""Helpers for handing JWTs to the client as HttpOnly cookies."""

from django.conf import settings


def set_token_cookie(response, key, token, lifetime):
    """Attach one JWT to the response as an HttpOnly cookie."""
    response.set_cookie(
        key=key,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        max_age=int(lifetime.total_seconds()),
    )


def set_auth_cookies(response, access_token, refresh_token):
    """Attach both JWTs to the response."""
    jwt_settings = settings.SIMPLE_JWT
    set_token_cookie(
        response, "access_token", access_token,
        jwt_settings["ACCESS_TOKEN_LIFETIME"],
    )
    set_token_cookie(
        response, "refresh_token", refresh_token,
        jwt_settings["REFRESH_TOKEN_LIFETIME"],
    )
    return response


def delete_auth_cookies(response):
    """Delete both auth cookies (mirror of set_auth_cookies)."""
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")


def set_access_cookie(response, access_token):
    """Set only the access_token as an HttpOnly cookie (used on token refresh).

    Reuses set_token_cookie so the cookie carries the same max_age as the one
    handed out at login. Without it the refreshed cookie would be a session
    cookie and disappear when the browser closes, giving the same token two
    different lifetimes depending on how it was issued.
    """
    set_token_cookie(
        response, "access_token", access_token,
        settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"],
    )
    return response
