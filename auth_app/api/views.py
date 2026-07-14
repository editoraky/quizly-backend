"""Views for the authentication endpoints."""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView

from auth_app.api.serializers import RegistrationSerializer
from auth_app.api.utils import set_auth_cookies


class RegistrationView(APIView):
    """Create a new user account."""

    permission_classes = [AllowAny]

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
