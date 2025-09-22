from django.utils import timezone
from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(required = False, default=timezone.now)
    
    class Meta:
        model = Article
        fields = ["id", "title", "content", "author", "url", "journal", "created_at"]
        read_only_fields = ["id"]

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
        return value
    