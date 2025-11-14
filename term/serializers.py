from django.utils import timezone
from rest_framework import serializers
from .models import Term

class TermSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Term
        fields = ["term", "meaning"]
        read_only_fields = ["id"]
