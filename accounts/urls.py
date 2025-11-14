from django.urls import path
from .views import UserSignupView, ProfileView, PasswordChangeView, LogoutView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("signup/", UserSignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),  # JWT 로그인
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password-change/", PasswordChangeView.as_view(), name="password_change"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),  # 인증 필요
]