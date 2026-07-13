"""Serializers for user registration."""

from django.contrib.auth.models import User
from rest_framework import serializers


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate registration data and create a user with a hashed password."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirmed_password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        """Reject an email that another user already registered with."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate(self, attrs):
        """Reject a confirmation that does not match the password."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """Create the user, dropping the confirmation and hashing the password."""
        validated_data.pop("confirmed_password")
        return User.objects.create_user(**validated_data)
    
