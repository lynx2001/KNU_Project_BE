# quiz/serializers.py

from rest_framework import serializers
from .models import (
    OXQuiz, ShortAnswerQuiz, MultipleChoiceQuiz, QuizOption, UserQuizAnswer
)

# --- 조회용 (Read) Serializers ---

class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["id", "text", "order"] # is_correct 필드는 정답이므로 숨김

class OXQuizSerializer(serializers.ModelSerializer):
    quiz_type = serializers.CharField(default="OX", read_only=True)
    class Meta:
        model = OXQuiz
        fields = ["id", "summary", "question", "explanation", "quiz_type"]

class ShortAnswerQuizSerializer(serializers.ModelSerializer):
    quiz_type = serializers.CharField(default="SC", read_only=True)
    class Meta:
        model = ShortAnswerQuiz
        fields = ["id", "summary", "question", "explanation", "quiz_type"]

class MultipleChoiceQuizSerializer(serializers.ModelSerializer):
    quiz_type = serializers.SerializerMethodField()
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = MultipleChoiceQuiz
        fields = ["id", "summary", "question", "explanation", "quiz_type", "options"]

    def get_quiz_type(self, obj):
        return f"MC{obj.choice_type}"


# --- 생성용 (Write/Create) Serializers ---

class QuizOptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["text", "is_correct", "order"]

class MultipleChoiceQuizCreateSerializer(serializers.ModelSerializer):
    options = QuizOptionCreateSerializer(many=True, write_only=True)

    class Meta:
        model = MultipleChoiceQuiz
        fields = ["summary", "question", "explanation", "choice_type", "options"]

    def validate(self, attrs):
        options = attrs.get("options", [])
        choice_type = attrs.get("choice_type")

        # 보기 개수 검사
        if len(options) != choice_type:
            raise serializers.ValidationError(f"MC{choice_type} 유형은 보기 {choice_type}개가 필요합니다.")
        
        # 정답 보기 개수 검사
        correct_cnt = sum(1 for o in options if o.get("is_correct"))
        if correct_cnt != 1:
            raise serializers.ValidationError("정확히 1개의 보기에 is_correct=True를 설정해야 합니다.")
            
        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop("options")
        mc_quiz = MultipleChoiceQuiz.objects.create(**validated_data)
        for opt_data in options_data:
            QuizOption.objects.create(quiz=mc_quiz, **opt_data)
        return mc_quiz


# --- 모든 퀴즈 생성 요청을 받아 분배하는 Serializer ---

class QuizCreateSerializer(serializers.Serializer):
    quiz_type = serializers.ChoiceField(choices=["OX", "SC", "MC3", "MC5"])
    
    # 모든 유형의 필드를 allow_null=True로 받음 (유효성 검사는 각자 시리얼라이저에서)
    summary = serializers.IntegerField() # 실제로는 PrimaryKeyRelatedField 등이 더 적합
    question = serializers.CharField()
    explanation = serializers.CharField(required=False, allow_blank=True)
    correct_answer_bool = serializers.BooleanField(required=False, allow_null=True)
    correct_answer_text = serializers.CharField(required=False, allow_blank=True)
    options = QuizOptionCreateSerializer(many=True, required=False)

    def validate(self, attrs):
        quiz_type = attrs.get('quiz_type')
        
        if quiz_type == "OX":
            if attrs.get('correct_answer_bool') is None:
                raise serializers.ValidationError("OX 유형은 correct_answer_bool이 필요합니다.")
        elif quiz_type == "SC":
            if not attrs.get('correct_answer_text'):
                raise serializers.ValidationError("SC 유형은 correct_answer_text가 필요합니다.")
        elif quiz_type in ("MC3", "MC5"):
            if not attrs.get('options'):
                raise serializers.ValidationError("객관식 유형은 options가 필요합니다.")

        return attrs

    def create(self, validated_data):
        quiz_type = validated_data.get('quiz_type')
        
        if quiz_type == 'OX':
            serializer = OXQuizSerializer(data={
                "summary": validated_data.get('summary'),
                "question": validated_data.get('question'),
                "explanation": validated_data.get('explanation'),
                "correct_answer": validated_data.get('correct_answer_bool')
            })
        elif quiz_type == 'SC':
            serializer = ShortAnswerQuizSerializer(data={
                "summary": validated_data.get('summary'),
                "question": validated_data.get('question'),
                "explanation": validated_data.get('explanation'),
                "correct_answer": validated_data.get('correct_answer_text')
            })
        elif quiz_type in ('MC3', 'MC5'):
            serializer = MultipleChoiceQuizCreateSerializer(data={
                "summary": validated_data.get('summary'),
                "question": validated_data.get('question'),
                "explanation": validated_data.get('explanation'),
                "choice_type": 3 if quiz_type == 'MC3' else 5,
                "options": validated_data.get('options')
            })
        else:
            raise serializers.ValidationError("지원하지 않는 quiz_type 입니다.")
            
        serializer.is_valid(raise_exception=True)
        return serializer.save()