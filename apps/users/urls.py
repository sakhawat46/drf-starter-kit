from django.urls import path
from .views import (
    SignupView, LoginView,
    PasswordResetRequestAPIView, PasswordResetOTPVerifyView, PasswordResetChangeAPIView, LogoutView, ChangePassword, DeleteAccountAPIView
    , ProfileAPIView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # User Registration
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Token Refresh
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Password Reset
    path("password-reset/request/", PasswordResetRequestAPIView.as_view(), name="password-reset-request"),
    path("password-reset/verify-otp/", PasswordResetOTPVerifyView.as_view(), name="password-reset-verify-otp"),
    path("password-reset/change-password/", PasswordResetChangeAPIView.as_view(), name="password-reset-change"),
    #change password
    path("change-password/", ChangePassword.as_view(), name="change_password"),
    # Delete Account
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete-account'),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
]
