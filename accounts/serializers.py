from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import Profile
from typing import Any, Dict, cast

class ProfileSerializer(serializers.ModelSerializer):
    grade = serializers.CharField(read_only=True)
    class Meta:
        model = Profile

        fields = ["nickname", "phone_number", "score", "grade"]
        #fields = ["nickname", "phone_number", "score", "picture", "grade"]
        read_only_fields = ["grade"]

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data["username"],
            email = validated_data.get("email"),
            password=validated_data["password"]
        )
        Profile.objects.create(user=user)
        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined"]


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True, label="기존 비밀번호")
    new_password = serializers.CharField(
        required=True, 
        write_only=True, 
        validators=[validate_password],
        label="새 비밀번호"
    )
    #new_password2 = serializers.CharField(required=True, write_only=True, label="새 비밀번호 확인")

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("기존 비밀번호가 올바르지 않습니다.")
        return value

    # def validate(self, data):
    #     if data.get('new_password') != data.get('new_password2'):
    #         raise serializers.ValidationError({"new_password": "새 비밀번호가 일치하지 않습니다."})
    #     return data

    def save(self, **kwargs):
        data = cast(Dict[str, Any], self.validated_data)
        password = data.get('new_password')

        user = self.context["request"].user
        user.set_password(password)
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(label="JWT Refresh 토큰")

    default_error_messages = {
        'bad_token': '잘못된 토큰이거나 만료된 토큰입니다.'
    }
    
    def validate(self, attrs):
        token = attrs.get('refresh')
        if self.token is None:
            raise serializers.ValidationError("Refresh 토큰이 필요합니다.")
        
        self.token = token
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')