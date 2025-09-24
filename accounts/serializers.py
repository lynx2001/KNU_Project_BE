from rest_framework import serializers
from .models import User

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "nickname", "phone_number"]

    def create(self, validated_data):
        user = User(
            username = validated_data["username"],
            email = validated_data["email"],
            nickname = validated_data.get("nickname"),
            phone_number = validated_data.get("phone_number"),
        )

        user.set_password(validated_data["password"])
        user.save()

        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "nickname", "phone_number", "created_at"]