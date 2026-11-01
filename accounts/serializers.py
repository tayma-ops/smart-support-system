from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.crypto import constant_time_compare
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import User


class RevocableTokenRefreshSerializer(TokenRefreshSerializer):
    """Apply password revocation to refreshes after API, web or admin changes."""

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        try:
            user = User.objects.get(
                **{api_settings.USER_ID_FIELD: refresh.get(api_settings.USER_ID_CLAIM)}
            )
        except (User.DoesNotExist, ValueError, TypeError):
            raise AuthenticationFailed("Invalid refresh token.") from None
        if not api_settings.USER_AUTHENTICATION_RULE(user) or (
            api_settings.CHECK_REVOKE_TOKEN
            and not constant_time_compare(
                refresh.get(api_settings.REVOKE_TOKEN_CLAIM, ""),
                get_md5_hash_password(user.password),
            )
        ):
            raise AuthenticationFailed("Invalid refresh token.")
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "departments",
            "is_active",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "role",
            "departments",
            "is_active",
        ]


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), lookup="iexact")]
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        user = User(**{key: value for key, value in attrs.items() if key != "password"})
        try:
            password_validation.validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from None
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AdminUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ["id", "username", "email"]

    def validate(self, attrs):
        # Prevent a lone administrator from accidentally locking themselves out.
        if self.instance == self.context["request"].user and (
            attrs.get("role", self.instance.role) != "admin"
            or not attrs.get("is_active", True)
        ):
            raise serializers.ValidationError(
                "Change your own administrator access through another administrator."
            )
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": "Incorrect password."})
        try:
            password_validation.validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.messages}) from None
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
