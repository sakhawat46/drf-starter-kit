from django.urls import path
from .views import GoogleLoginView, AppleIdTokenLoginView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Social login with Google; expects access_token
    path('google/', GoogleLoginView.as_view(), name='google_login'),
    
    # Social login with Apple; expects identity_token
    path('apple/', AppleIdTokenLoginView.as_view(), name='apple_login'),
]
