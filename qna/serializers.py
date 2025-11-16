from rest_framework import serializers
from .models import QnA

class QnASerializer(serializers.ModelSerializer):
    
    class Meta:
        model = QnA
        fields = ["id", "question", "answer"]
        read_only_fields = ["id"]