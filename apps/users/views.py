from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer, LoginSerializer, PasswordResetRequestSerializer, PasswordResetChangeSerializer, ChangePasswordSerializer, ProfileSerializer
from apps.users.models import Profile
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework import generics

User = get_user_model()

# ===== Helper Function =====
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }

class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"success": True, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )

    def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"success": False, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )



class SignupView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return self.success_response(
                "User created successfully.",
                data={
                    "email": user.email,
                    "tokens": tokens
                }
            )
        return self.error_response("Validation error", data=serializer.errors)






# ===== Login =====
class LoginView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, email=email, password=password)
            if user is None:
                return self.error_response("Invalid email or password", status_code=status.HTTP_401_UNAUTHORIZED)
            
            tokens = get_tokens_for_user(user)
            return self.success_response("Login successful", data={"tokens": tokens})
        return self.error_response("Invalid data", status_code=status.HTTP_400_BAD_REQUEST)





# ===== Password Reset =====
class PasswordResetRequestAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return self.success_response("OTP sent to email.", data={"email": serializer.validated_data["email"]})
        return self.error_response("Validation error", data=serializer.errors)


class PasswordResetOTPVerifyView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        otp = request.data.get("otp")
        if not otp:
            return self.error_response("OTP is required.")

        try:
            user = User.objects.get(otp=otp, otp_exp__gte=timezone.now(), otp_verified=False)
        except User.DoesNotExist:
            return self.error_response("Invalid or expired OTP.")

        user.otp_verified = True
        user.save()
        tokens = get_tokens_for_user(user)  # Access + Refresh token
        return self.success_response(
            "OTP verified successfully.",
            data={"tokens": tokens}
        )

class PasswordResetChangeAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetChangeSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.otp_verified = False
            request.user.otp = None
            request.user.otp_exp = None
            request.user.save()
            return self.success_response("Password reset successful.")
        return self.error_response("Passwords do not match.", data=serializer.errors)



# ===== Password Change =====
class ChangePassword(BaseAPIView, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Validation error", data=serializer.errors)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return self.error_response("Old password does not match")

        user.set_password(new_password)
        user.save()
        return self.success_response("Password changed successfully")



# ===== Logout =====
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        



class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete() # For Permanent Delete
        # user.is_active = False  # For Soft delete
        # user.email = f"deleted_{user.id}_{user.email}" # For Soft delete
        # user.save() # For Soft delete
        return Response({"message": "Your account has been deleted."}, status=status.HTTP_200_OK)


class ProfileAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, context={"request": request})
        return self.success_response("Profile fetched successfully", data=serializer.data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return self.success_response("Profile updated successfully", data=serializer.data)
        return self.error_response("Validation error", data=serializer.errors)
