from rest_framework import serializers
from .models import Summary, SummaryGroup
from article.serializers import ArticleSerializer

class SummarySerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)
    
    class Meta:
        model = Summary
        fields = ["id", "article", "title", "content"]
        read_only_fields = ["id"]

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
        return value

class SummaryGroupSerializer(serializers.ModelSerializer):
    summaries = SummarySerializer(many=True, read_only=True)
    
    class Meta:
        model = SummaryGroup
        fields = ["id", "date", "group_index", "created_at", "summaries"]