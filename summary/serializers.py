from rest_framework import serializers
from .models import Summary, SummaryGroup
from article.models import Article
from term.models import Term
from term.serializers import TermSerializer
from django.utils import timezone
from django.db.models import Max

class SummarySerializer(serializers.ModelSerializer):
    article = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(),
        allow_null=True
    )

    terms = TermSerializer(many=True, required=False)

    group = serializers.PrimaryKeyRelatedField(
        queryset=SummaryGroup.objects.all(),
        required=False,
    )

    class Meta:
        model = Summary
        fields = ["id", "article", "title", "content", "terms", "group"]
        read_only_fields = ["id"]

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
        return value
    
    def create(self, validated_data):
        terms_data = validated_data.pop('terms', [])
        group = validated_data.pop('group', None)

        if group is None:
            today = timezone.now().date()
            
            last_index_data = SummaryGroup.objects.filter(date=today).aggregate(max_index=Max('group_index'))
            last_index = last_index_data.get('max_index')
            
            if last_index is None:
                next_index = 1
            else:
                next_index = last_index + 1
            
            group = SummaryGroup.objects.create(date=today, group_index=next_index)
        
        summary = Summary.objects.create(group=group, **validated_data)

        for term_item in terms_data:
            term_obj, created = Term.objects.get_or_create(
                term=term_item['term'],
                defaults={'meaning': term_item['meaning']}
            )
            summary.terms.add(term_obj)

        return summary

class SummaryGroupSerializer(serializers.ModelSerializer):
    summaries = SummarySerializer(many=True, read_only=True)
    
    class Meta:
        model = SummaryGroup
        fields = ["id", "date", "group_index", "created_at", "summaries"]