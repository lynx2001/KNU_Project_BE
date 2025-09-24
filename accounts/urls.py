from django.urls import path
from .views import UserSignupView, UserProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("signup/", UserSignupView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),  # JWT 로그인
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileView.as_view(), name="profile"),  # 인증 필요
]
