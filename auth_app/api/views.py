"""Views for the authentication endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from .services import blacklist_token
from .serializers import RegistrationSerializer
from .utils import set_auth_cookies, delete_auth_cookies, set_access_cookie


class RegistrationView(APIView):
    """Create a new user account."""

    permission_classes = [AllowAny]
    authentication_classes = []  # Register runs while logged out → no cookie auth


    def post(self, request):
        """Validate the payload and create the user."""
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Log a user in and hand over both JWTs as HttpOnly cookies."""

    authentication_classes = []  # Login runs while logged out → no cookie auth
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Let SimpleJWT authenticate, then move the tokens into cookies."""
        token_response = super().post(request, *args, **kwargs)
        user = User.objects.get(username=request.data["username"])

        response = Response({
            "detail": "Login successfully!",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }, status=status.HTTP_200_OK)

        return set_auth_cookies(
            response,
            token_response.data["access"],
            token_response.data["refresh"],
        )


class LogoutView(APIView):
    """Log the user out: blacklist the refresh token, delete both cookies."""

    permission_classes = [IsAuthenticated]  # Docs page 3: protected, otherwise 401

    def post(self, request):
        """Log the user out: blacklist the refresh token if present, and always delete both cookies (idempotent)."""
        refresh_token = request.COOKIES.get("refresh_token")  # (1) read safely instead of accessing directly
        if refresh_token:  # (2) only if a cookie is present
            try:
                blacklist_token(refresh_token)  # (3) attempt — may fail on a garbage token
            except TokenError:
                pass  # invalid token = no session to blacklist; logout stays idempotent
        response = Response(
            {"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)  # now runs ALWAYS
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Refresh the access token from the refresh_token cookie and return it as a cookie."""

    authentication_classes = []  # runs when access has expired → must NOT validate it
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Read the refresh token from the cookie, validate it, set a new access token as a cookie."""
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return self._unauthorized()
        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return self._unauthorized()
        response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
        return set_access_cookie(response, serializer.validated_data["access"])

    def _unauthorized(self):
        """401 response for a missing or invalid refresh token (Docs page 4)."""
        return Response(
            {"detail": "Refresh token missing or invalid"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

