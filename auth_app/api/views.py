"""Views for the authentication endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError

from .services import blacklist_token
from .serializers import RegistrationSerializer
from .utils import set_auth_cookies, delete_auth_cookies, set_access_cookie


class RegistrationView(APIView):
    """Create a new user account."""

    permission_classes = [AllowAny]
    authentication_classes = []  # Register läuft abgemeldet → keine Cookie-Auth


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

    authentication_classes = []  # Login läuft abgemeldet → keine Cookie-Auth
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
    """Loggt den User aus: blacklistet den Refresh-Token, löscht beide Cookies."""

    permission_classes = [IsAuthenticated]  # Doku Seite 3: geschützt, sonst 401

    def post(self, request):
        """Loggt den User aus: blacklistet das Refresh-Token, falls vorhanden, und löscht beide Cookies immer (idempotent)."""
        refresh_token = request.COOKIES.get("refresh_token")  # (1) sicher lesen statt hart zugreifen
        if refresh_token:  # (2) nur wenn ein Cookie da ist
            try:
                blacklist_token(refresh_token)  # (3) Versuch — kann bei Müll-Token scheitern
            except TokenError:
                pass  # ungültiges Token = keine Sitzung zum Blacklisten; Logout bleibt idempotent
        response = Response(
            {"detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."},
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)  # läuft jetzt IMMER
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """Erneuert den Access-Token aus dem refresh_token-Cookie und gibt ihn als Cookie zurück."""

    authentication_classes = []  # läuft bei abgelaufenem Access → darf ihn NICHT prüfen
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Refresh-Token aus dem Cookie holen, prüfen, neuen Access-Token als Cookie setzen."""
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
        """401-Antwort für fehlendes oder ungültiges Refresh-Token (Doku Seite 4)."""
        return Response(
            {"detail": "Refresh token missing or invalid"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

