from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import UserSignupSerializer, UserProfileSerializer, ProfileSerializer, PasswordChangeSerializer, LogoutSerializer
from django.contrib.auth import get_user_model
from .models import Profile
from typing import Dict, Any, cast

User = get_user_model()

class UserSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():

            user = serializer.save()
            # user_data = UserProfileSerializer(user).data
            return Response({"message": "회원가입 성공"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # def get(self, request):
        # 디버깅용: 로그인만 확인
        # return Response(
        #     {
        #         "id": request.user.id,
        #         "username": request.user.username,
        #         "email": request.user.email,
        #     },
        #     status=200,
        # )

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        #profile = request.user.profile

        user_data = cast(Dict[str, Any], UserProfileSerializer(user).data)
        profile_data = cast(Dict[str, Any], ProfileSerializer(profile).data)
        
        merged = {**user_data, **profile_data,}

        return Response(merged, status=status.HTTP_200_OK)
    
    def patch(self, request):
        user = request.user
        #profile = request.user.profile
        profile, _ = Profile.objects.get_or_create(user=user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            user_data = cast(Dict[str, Any], UserProfileSerializer(request.user).data)
            profile_data = cast(Dict[str, Any], serializer.data)
            merged = {**user_data, **profile_data}

            return Response(merged, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request},)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK,)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "로그아웃 되었습니다."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
