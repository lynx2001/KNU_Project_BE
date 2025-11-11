from rest_framework import serializers
from .models import Quiz, QuizOption, UserQuizAnswer

class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["id", "text", "order"]

class QuizSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "summary",
            "quiz_type",
            "question",
            "explanation",
            "options",
        ]

class QuizOptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ["text", "is_correct", "order"]


class QuizCreateSerializer(serializers.ModelSerializer):
    options = QuizOptionCreateSerializer(many=True, required=False)

    class Meta:
        model = Quiz
        fields = [
            "summary",
            "quiz_type",
            "question",
            "explanation",
            "correct_bool",
            "correct_text",
            "options",
        ]

    def validate(self, attrs):
        qt = attrs.get("quiz_type")
        options = attrs.get("options", [])
        correct_bool = attrs.get("correct_bool")
        correct_text = (attrs.get("correct_text") or "").strip()

        # 유형별 규칙 강제
        if qt == Quiz.TYPE_OX:
            # OX: 정답 bool 필수, 보기 없음
            if correct_bool is None:
                raise serializers.ValidationError("OX 유형은 correct_bool이 필요합니다.")
            if options:
                raise serializers.ValidationError("OX 유형에는 options를 사용하지 않습니다.")
            attrs["correct_text"] = ""

        elif qt in (Quiz.TYPE_MC3, Quiz.TYPE_MC5):
            # MC3/MC5: 지정 개수의 보기 + 정답 1개
            required_cnt = 3 if qt == Quiz.TYPE_MC3 else 5
            if len(options) != required_cnt:
                raise serializers.ValidationError(
                    f"{qt} 유형은 보기 {required_cnt}개가 필요합니다."
                )
            correct_cnt = sum(1 for o in options if o.get("is_correct"))
            if correct_cnt != 1:
                raise serializers.ValidationError(
                    f"{qt} 유형은 is_correct=True 인 보기가 정확히 1개여야 합니다."
                )
            attrs["correct_bool"] = None
            attrs["correct_text"] = ""

        elif qt == Quiz.TYPE_SC:
            # 단답형: correct_text 필수
            if not correct_text:
                raise serializers.ValidationError(
                    "단답형(SC)은 correct_text(정답 문자열)가 필요합니다."
                )
            attrs["correct_text"] = correct_text
            attrs["correct_bool"] = None
            # options는 사용 안 함
            if options:
                raise serializers.ValidationError("단답형에는 options를 사용하지 않습니다.")

        else:
            raise serializers.ValidationError("지원하지 않는 quiz_type 입니다.")

        return attrs

    def create(self, validated_data):
        options_data = validated_data.pop("options", [])
        quiz = Quiz.objects.create(**validated_data)

        # MC3/MC5일 때만 보기 생성
        if quiz.quiz_type in (Quiz.TYPE_MC3, Quiz.TYPE_MC5):
            for idx, opt in enumerate(options_data, start=1):
                QuizOption.objects.create(
                    quiz=quiz,
                    text=opt["text"],
                    is_correct=opt.get("is_correct", False),
                    order=opt.get("order", idx),
                )

        return quiz
