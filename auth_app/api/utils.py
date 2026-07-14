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
