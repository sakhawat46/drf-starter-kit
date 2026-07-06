from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError
from django.conf import settings
from .utils import send_signup_otp_email

from apps.users.models import Profile
User = get_user_model()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'name']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        name = validated_data.pop('name', '')
        validated_data.pop('confirm_password')

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
        )
        # Create a profile for the user
        Profile.objects.create(user=user, name=name)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = ["email", "name", "picture"]
        read_only_fields = ["email"]






# ===== Login =====
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)



# ===== Password Reset =====
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        user.generate_otp()

        # send_mail(
        #     "Password Reset OTP",
        #     f"Your OTP for password reset is {user.otp}",
        #     settings.EMAIL_HOST_USER,
        #     [user.email],
        #     fail_silently=False,
        # )

        send_signup_otp_email(user)

        return value

class PasswordResetChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")

        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})

        return attrs
