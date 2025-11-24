from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from accounts.models import Profile
from .models import OXQuiz, ShortAnswerQuiz, MultipleChoiceQuiz, QuizOption, UserQuizAnswer
from .serializers import (
    OXQuizSerializer, ShortAnswerQuizSerializer, MultipleChoiceQuizSerializer,
    QuizCreateSerializer,
    QuizSubmitSerializer
)
from django_filters.rest_framework import DjangoFilterBackend

# --- 유형별 조회/수정/삭제 ViewSets ---

class OXQuizViewSet(viewsets.ModelViewSet):
    queryset = OXQuiz.objects.all()
    serializer_class = OXQuizSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['summary']

class ShortAnswerQuizViewSet(viewsets.ModelViewSet):
    queryset = ShortAnswerQuiz.objects.all()
    serializer_class = ShortAnswerQuizSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['summary']

class MultipleChoiceQuizViewSet(viewsets.ModelViewSet):
    queryset = MultipleChoiceQuiz.objects.all()
    serializer_class = MultipleChoiceQuizSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['summary']


# --- 통합 퀴즈 생성 API View ---

class QuizCreateAPIView(APIView):
    permission_classes = [permissions.AllowAny] # 생성은 로그인한 사용자만

    def post(self, request, *args, **kwargs):
        """
        모든 유형의 퀴즈를 이 엔드포인트에서 생성합니다.
        request body에 "quiz_type" 필드 (OX, SC, MC4)가 필수입니다.
        """
        serializer = QuizCreateSerializer(data=request.data)
        if serializer.is_valid():
            quiz_instance = serializer.save()
            
            if isinstance(quiz_instance, OXQuiz):
                response_serializer = OXQuizSerializer(quiz_instance)
            elif isinstance(quiz_instance, ShortAnswerQuiz):
                response_serializer = ShortAnswerQuizSerializer(quiz_instance)
            elif isinstance(quiz_instance, MultipleChoiceQuiz):
                response_serializer = MultipleChoiceQuizSerializer(quiz_instance)
            else:
                return Response({"error": "Unknown quiz type created"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# (new) 퀴즈 2개 이상 동시 생성 API View
class QuizBulkCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated] # 생성은 로그인한 사용자만

    def post(self, request, *args, **kwargs):
        """
        퀴즈 2개가 담긴 리스트(배열)를 받아 한 번에 생성합니다.
        request body: [ {quiz_type: "OX", ...}, {quiz_type: "SC", ...} ]
        """
        
        # 'many=True' 옵션을 사용하여 리스트 데이터를 처리
        serializer = QuizCreateSerializer(data=request.data, many=True)
        
        if serializer.is_valid():
            try:
                # 2개 모두 성공하거나, 1개라도 실패하면 모두 롤백 (All or Nothing)
                with transaction.atomic():
                    quiz_instances = serializer.save()
                
                # 생성된 객체들을 다시 직렬화하여 반환 (유형에 맞게)
                response_data = []
                for instance in quiz_instances:
                    if isinstance(instance, OXQuiz):
                        response_data.append(OXQuizSerializer(instance).data)
                    elif isinstance(instance, ShortAnswerQuiz):
                        response_data.append(ShortAnswerQuizSerializer(instance).data)
                    elif isinstance(instance, MultipleChoiceQuiz):
                        response_data.append(MultipleChoiceQuizSerializer(instance).data)

                return Response(response_data, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                # 트랜잭션 중 오류 발생 시
                return Response({"error": f"퀴즈 생성 중 오류 발생: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# (new) 퀴즈 제출 및 채점 API View
class QuizSubmitAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_type_id, object_id, *args, **kwargs):
        """
        사용자의 퀴즈 답변을 받아 채점하고 점수를 반영합니다.
        URL: /api/quiz/submit/<content_type_id>/<object_id>/
        """
        
        try:
            content_type = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return Response({"error": "잘못된 퀴즈 유형(ContentType)입니다."}, status=status.HTTP_404_NOT_FOUND)

        # 1-2. 퀴즈 모델 클래스 검증 (e.g. OXQuiz)
        model_class = content_type.model_class() 
        if model_class not in [OXQuiz, MultipleChoiceQuiz, ShortAnswerQuiz]:
            return Response({"error": "잘못된 퀴즈 모델입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1-3. 실제 퀴즈 객체(instance) 가져오기
        #    (여기서 404가 나면 get_object_or_404가 오류를 반환)
        quiz = get_object_or_404(model_class, pk=object_id)

        # 2. 이미 푼 문제인지 확인 (중복 제출 방지)
        if UserQuizAnswer.objects.filter(user=request.user, content_type=content_type, object_id=object_id).exists():
            return Response({"error": "이미 제출한 답변입니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        # 3. 답변 데이터 검증
        submit_serializer = QuizSubmitSerializer(data=request.data)
        if not submit_serializer.is_valid():
            return Response(submit_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = submit_serializer.validated_data
        is_correct = False
        user_answer_data = {
            "user": request.user,
            "quiz": quiz,
            "is_correct": False,
        }

        # 4. 퀴즈 유형별 채점
        model_name = content_type.model
        
        try:
            if model_name == 'oxquiz':
                user_ans = validated_data.get('ox_answer')
                if user_ans is None:
                    raise ValueError("ox_answer(True/False)가 필요합니다.")
                is_correct = (quiz.correct_answer == user_ans)
                user_answer_data['ox_answer'] = user_ans

            elif model_name == 'shortanswerquiz':
                user_ans = validated_data.get('text_answer', '')
                is_correct = (quiz.correct_answer.strip().lower() == user_ans.strip().lower())
                user_answer_data['text_answer'] = user_ans

            elif model_name == 'multiplechoicequiz':
                user_ans_id = validated_data.get('selected_option_id')
                if user_ans_id is None:
                    raise ValueError("selected_option_id가 필요합니다.")
                
                selected_option = get_object_or_404(QuizOption, pk=user_ans_id, quiz=quiz)
                is_correct = selected_option.is_correct
                user_answer_data['selected_option'] = selected_option
            
        except (QuizOption.DoesNotExist, ValueError) as e:
            return Response({"error": f"답변 처리 중 오류: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 5. 채점 결과 저장 및 점수 반영 (트랜잭션)
        try:
            with transaction.atomic():
                # 5-1. UserQuizAnswer에 기록 저장
                user_answer_data['is_correct'] = is_correct
                UserQuizAnswer.objects.create(**user_answer_data)
                
                new_score = request.user.profile.score
                
                # 5-2. 정답일 경우, 점수 반영
                if is_correct:
                    # (점수 정책은 여기서 수정, 예: +100점)
                    profile = request.user.profile # accounts.models의 Profile
                    profile.score += 10
                    profile.save()
                    new_score = profile.score

            # 6. 결과 반환
            return Response({
                "is_correct": is_correct,
                "explanation": quiz.explanation,
                "new_score": new_score,
                "grade": request.user.profile.grade # accounts.models의 @property
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"채점 결과 저장 중 오류: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)