import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

# 형님의 모델들 임포트
from article.models import Article
from summary.models import Summary, SummaryGroup
from term.models import Term
from quiz.models import OXQuiz

User = get_user_model()

class Command(BaseCommand):
    help = '7일치 테스트 데이터 생성 (하루 3개 기사, 각각 다른 그룹 인덱스 1,2,3 할당)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', 
            type=str, 
            help='데이터를 추가할 기존 사용자의 아이디(Username)',
            required=True
        )

    def handle(self, *args, **options):
        target_username = options['username']
        
        try:
            user = User.objects.get(username=target_username)
            self.stdout.write(f"🚀 사용자 '{target_username}' 계정을 찾았습니다. 데이터 생성을 시작합니다...")
        except User.DoesNotExist:
            raise CommandError(f"❌ 사용자 '{target_username}'을(를) 찾을 수 없습니다.")

        # 1. 공통 용어(Term) 풀 생성
        term_data = [
            ("기준금리", "중앙은행이 시중 은행과 거래할 때 적용하는 이자율"),
            ("인플레이션", "물가가 지속적으로 오르는 현상"),
            ("양적완화", "중앙은행이 시장에 돈을 풀어 유동성을 공급하는 정책"),
            ("KOSPI", "대한민국 주식시장의 종합주가지수"),
            ("환율", "자국 화폐와 외국 화폐의 교환 비율"),
        ]
        term_objects = []
        for t_text, t_mean in term_data:
            term, _ = Term.objects.get_or_create(term=t_text, defaults={'meaning': t_mean})
            term_objects.append(term)
        self.stdout.write(f" - 용어 {len(term_objects)}개 준비 완료")

        # 2. 최근 7일 루프 (오늘 ~ 6일 전)
        now = timezone.now()
        
        for i in range(7):
            base_date = now - timedelta(days=i)
            date_str = base_date.strftime("%Y-%m-%d")
            
            self.stdout.write(f"\n[{date_str}] 데이터 생성 중...")

            # 하루에 기사 3개씩 생성 (j = 1, 2, 3)
            for j in range(1, 4):
                # ★ 핵심 수정: 기사마다 별도의 SummaryGroup 생성 & 인덱스 부여
                # group_index를 j (1, 2, 3)로 설정하여 각각 다른 그룹으로 만듦
                group, _ = SummaryGroup.objects.get_or_create(
                    date=base_date.date(),
                    group_index=j  # <--- 여기가 핵심 (1, 2, 3)
                )

                # 시간차 적용 (1시간 간격)
                article_time = base_date - timedelta(hours=j)

                # (1) Article 생성
                title = f"[{date_str}] 경제 뉴스 {j} (그룹 {j})"
                article = Article.objects.create(
                    user=user,
                    title=title,
                    content=f"[{date_str}] {j}번째 뉴스입니다. 이 기사는 그룹 {j}번에 속합니다. (작성시간: {article_time.strftime('%H:%M')})",
                    author="AI 기자",
                    journal="이콘일보",
                    url=f"http://econagent.com/news/{i}/{j}"
                )
                article.created_at = article_time
                article.save()

                # (2) Summary 생성 (위에서 만든 개별 그룹에 연결)
                summary = Summary.objects.create(
                    article=article,
                    group=group, # <--- 개별 그룹 연결
                    title=f"{title} (3줄 요약)",
                    content=f"1. {date_str}의 {j}번째 기사입니다.\n2. 그룹 인덱스는 {j}입니다.\n3. 용어와 퀴즈를 확인하세요."
                )
                
                # (3) 용어 연결 (2개)
                selected_terms = random.sample(term_objects, 2)
                summary.terms.add(*selected_terms)

                # (4) OX Quiz 2개 생성
                OXQuiz.objects.create(
                    summary=summary,
                    question=f"이 기사는 그룹 {j}번에 속하는 뉴스이다. (O/X)",
                    explanation=f"맞습니다. 이 기사의 그룹 인덱스는 {j}입니다.",
                    correct_answer=True
                )

                OXQuiz.objects.create(
                    summary=summary,
                    question="이 기사는 '연예' 뉴스이다. (O/X)",
                    explanation="틀렸습니다. '경제' 뉴스입니다.",
                    correct_answer=False
                )
            
            self.stdout.write(f" -> 기사 3개 / 그룹(1,2,3) 분리 완료")

        self.stdout.write(self.style.SUCCESS(f"\n🎉 사용자 '{target_username}'에게 데이터 생성 완료! (기사별 개별 그룹 적용)"))