"""Custom authentication reading the JWT from an HttpOnly cookie instead of the Authorization header."""

from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate a request via the access_token stored in an HttpOnly cookie."""

    def authenticate(self, request):
        """Read access_token cookie, validate it, return (user, token); None if the cookie is absent."""
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
