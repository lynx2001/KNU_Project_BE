from django.utils import timezone
from rest_framework import serializers
from .models import Term

class TermSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Term
        fields = ["term", "meaning"]
        read_only_fields = ["id"]

#    def validate_title(self, value):
#        if len(value.strip()) < 2:
#            raise serializers.ValidationError("제목은 2자 이상이어야 합니다.")
#        return value
    