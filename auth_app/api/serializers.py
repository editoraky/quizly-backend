"""Serializers for user registration."""

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
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
        """Reject a mismatching confirmation or a password Django rates as weak.

        AUTH_PASSWORD_VALIDATORS only run where the code calls them, so without
        this the endpoint would accept "abc" while createsuperuser refuses it.
        The unsaved user carries username and email, which is what the
        similarity validator compares the password against.
        """
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"password": "Passwords do not match."}
            )
        candidate = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": list(error.messages)}
            ) from error
        return attrs

    def create(self, validated_data):
        """Create the user, dropping the confirmation and hashing the password."""
        validated_data.pop("confirmed_password")
        return User.objects.create_user(**validated_data)
    
