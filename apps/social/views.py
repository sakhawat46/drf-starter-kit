from django.shortcuts import render

from allauth.socialaccount.providers.oauth2.client import OAuth2Error
import imghdr
from urllib.parse import urlparse
import requests
import jwt
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.base import ContentFile
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
User = get_user_model()


class BaseAPIView(APIView):
    """Small helper base view providing standardized success/error responses."""
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        """Return consistent JSON for successful operations."""
        return Response({"success": True, "message": message, "status": status_code, "data": data or {}}, status=status_code)

    def error_response(self, message="Request failed", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Return consistent JSON for failed operations."""
        return Response({"success": False, "message": message, "status": status_code, "errors": data or {}}, status=status_code)



class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

    def post(self, request, *args, **kwargs):
        """
        Social login via Google. After allauth handles the social login,
        update the custom User model fields (name, profile_pic) from
        Google's extra_data if available, then return JWT tokens + user info.
        """
        try:
            # let allauth/dj-rest-auth process the login and create/get user
            super().post(request, *args, **kwargs)

            user = getattr(self, "user", None) or getattr(self, "request", None).user
            if not user or not getattr(user, "is_authenticated", False):
                return Response({"error": "Authentication failed."}, status=status.HTTP_400_BAD_REQUEST)

            # Try to get extra_data from socialaccount (Google)
            social_account = user.socialaccount_set.first()
            extra_data = social_account.extra_data if social_account else {}

            first_name = extra_data.get("given_name", "")
            last_name = extra_data.get("family_name", "")
            picture_url = extra_data.get("picture", None)

            # Update the user's name field (your User model has a single `name` field)
            combined_name = " ".join(part for part in [first_name, last_name] if part).strip()
            if combined_name:
                user.name = combined_name
            else:
                # Fallback: if no google name info, ensure user.name is not empty
                if not getattr(user, "name", ""):
                    user.name = user.email.split("@")[0]

            # Download and save profile picture to user's profile_pic if available and not already set
            if picture_url:
                # Only fetch and save if the user doesn't already have a profile_pic
                try:
                    if not getattr(user, "profile_pic", None):
                        r = requests.get(picture_url, timeout=10)
                        if r.status_code == 200 and r.content:
                            img_type = imghdr.what(None, h=r.content)
                            if img_type in ("jpeg", "png", "gif", "bmp", "webp"):
                                # Build a filename with extension
                                filename = urlparse(picture_url).path.split("/")[-1] or f"user_{user.id}_google"
                                if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")):
                                    # normalize extension
                                    ext = "jpg" if img_type == "jpeg" else img_type
                                    filename = f"{filename}.{ext}"
                                user.profile_pic.save(filename, ContentFile(r.content), save=False)
                except Exception:
                    # If fetching/saving image fails, ignore (we don't want to break login)
                    pass

            # Ensure user is active and save changes
            user.is_active = True
            user.save()

            # Create JWT (using SimpleJWT RefreshToken)
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "success": True,
                    "message": "Google login successful.",
                    "status": status.HTTP_200_OK,
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "name": user.name,
                        # "profile_pic": request.build_absolute_uri(user.profile_pic.url) if getattr(user, "profile_pic") else None,
                    },
                }
            )

        except OAuth2Error as e:
            return Response(
                {"error": "Failed to fetch Google user info. Token may be expired.", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            # Generic fallback so we don't leak internal traceback to client
            return Response({"error": "Google login failed.", "detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)








from django.conf import settings
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter, AppleOAuth2Client
from oauthlib.oauth2 import OAuth2Error
from rest_framework import status

class AppleLoginView(BaseAPIView, SocialLoginView):
    adapter_class = AppleOAuth2Adapter
    client_class = AppleOAuth2Client
    callback_url = getattr(settings, "APPLE_CALLBACK_URL", None)

    def post(self, request, *args, **kwargs):
        try:
            code = request.data.get("code")
            id_token = request.data.get("id_token")
            if not code or not id_token:
                return self.error_response(
                    message="code and id_token are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            response = super().post(request, *args, **kwargs)
            if getattr(response, "status_code", 200) >= 400:
                return self.error_response(
                    message="Apple login failed.",
                    data=getattr(response, "data", {}),
                    status_code=response.status_code,
                )

            user = getattr(self, "user", None) or getattr(request, "user", None)
            if not user or not getattr(user, "is_authenticated", False):
                return self.error_response(
                    message="Apple login failed. User not authenticated.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            return self.success_response(
                message="Apple login successful.",
                data={
                    "access": getattr(response, "data", {}).get("access"),
                    "refresh": getattr(response, "data", {}).get("refresh"),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                    }
                },
                status_code=status.HTTP_200_OK
            )

        except OAuth2Error as e:
            return self.error_response(
                message="Apple login failed. Please login again.",
                data={"detail": str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )


APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


def verify_apple_id_token(id_token):
    client_id = getattr(settings, "APPLE_CLIENT_ID", None)
    if not client_id:
        raise ValueError("APPLE_CLIENT_ID is not configured")

    jwk_client = jwt.PyJWKClient(APPLE_JWKS_URL)
    signing_key = jwk_client.get_signing_key_from_jwt(id_token)

    decoded = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer="https://appleid.apple.com",
    )
    return decoded


class AppleIdTokenLoginView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        id_token = request.data.get("id_token")
        if not id_token:
            return self.error_response(
                message="id_token is required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            decoded = verify_apple_id_token(id_token)
        except Exception as exc:
            return self.error_response(
                message="Invalid Apple id_token",
                data={"detail": str(exc)},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        email = decoded.get("email")
        if not email:
            return self.error_response(
                message="Apple id_token does not include email. Login failed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        name = decoded.get("name") or email.split("@")[0]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"name": name, "is_active": True},
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password", "is_active"])
        else:
            if not getattr(user, "name", ""):
                user.name = name
                user.save(update_fields=["name"])

        refresh = RefreshToken.for_user(user)

        return self.success_response(
            message="Apple login successful.",
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    # "profile_pic": request.build_absolute_uri(user.profile_pic.url) if getattr(user, "profile_pic") else None,
                },
            },
            status_code=status.HTTP_200_OK,
        )

