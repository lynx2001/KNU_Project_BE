from rest_framework import serializers
from .models import Summary

class SummarySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Summary
        fields = ["id", "article_id", "title", "content"]
        read_only_fields = ["id"]

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
        return value
    