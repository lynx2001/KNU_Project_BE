import traceback
import requests
from dotenv import load_dotenv
load_dotenv()
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Max
from ...agents import news_find, news_summary, term_explain, quiz
from accounts.models import Profile
from article.models import Article
from summary.models import Summary, SummaryGroup
from quiz.models import QuizOption, ShortAnswerQuiz, MultipleChoiceQuiz, OXQuiz
from term.models import Term


class Command(BaseCommand):

    def handle(self, *args, **options):
        print("🚀 데일리 파이프라인 (DB 연동 모드) 시작...")

        all_profiles = Profile.objects.filter(user__is_active=True)
        if not all_profiles:
            self.stdout.write("❌ 처리할 사용자가 없습니다.")
            return
        
        self.stdout.write(f"✅ 총 {len(all_profiles)}명의 사용자를 처리합니다.")

        for profile in all_profiles:
            self.stdout.write(f"\n--- [사용자: {profile.user.username}] 작업 시작 ---")

            profile_dict = {
                #"level": "숲", 
                "level": profile.grade, 
                "interests": ""
            }
            state = {"context": {}}
            
            # -------------------------------------------------------
            # STEP 1. 뉴스 수집 및 저장 (Article)
            # -------------------------------------------------------
            print("1️⃣ 뉴스 수집 중...")
            articles = news_find.build_daily_top3(profile=profile_dict, state=state)
            
            saved_articles = []
            saved_articles_orm = []
            
            for art in articles:
                try:
                    db_article = Article.objects.create(
                        url=art["url"], 
                        defaults={
                            "title": art["title"],
                            "content": art.get("content", "")[:5000],
                            "author": art.get("source", "Unknown"),
                            "journal": art.get("source", "Unknown"),
                            "created_at": art.get("source", "2001-01-01 11:11:11.111000"),
                            "user": profile.user
                        }
                    )
                    art["db_id"] = db_article.pk
                    saved_articles.append(art)
                    saved_articles_orm.append(db_article)

                    # if created:
                    #     self.stdout.write(self.style.SUCCESS(f"   -> 기사 저장 완료 (ID: {db_article.pk})"))
                    # else:
                    #     self.stdout.write(f"   -> 기사 중복/조회 (ID: {db_article.pk})")
                except Exception as e:
                    self.stderr.write(f"   -> 기사 저장 DB 오류: {e}")
                    traceback.print_exc()

            if not saved_articles:
                print("❌ 저장된 기사가 하나도 없습니다. 파이프라인을 종료합니다.")
                return

            # -------------------------------------------------------
            # STEP 2. 요약 및 용어 생성 및 저장 (Summary + Terms)
            # -------------------------------------------------------
            self.stdout.write(f"--- 2️⃣ [사용자: {profile.user.username}] 요약/용어 생성 중... ---")

            state["context"]["daily_pool"] = saved_articles
            state["context"]["selected_articles"] = saved_articles
            
            summaries = news_summary.build_daily_summaries(state=state, profile=profile_dict)
            
            term_explain.build_daily_term_explanations(state={"context": {"summaries": summaries}}, profile=profile_dict)

            saved_summaries_orm = [] 
            saved_summaries_with_db_id = []

            for i, summ in enumerate(summaries):
                try:
                    article_orm_object = saved_articles_orm[i]
                except IndexError:
                    self.stderr.write(f"   -> [오류] 기사(STEP 1)와 요약(STEP 2) 개수가 불일치. 건너뜁니다.")
                    continue
                terms_payload = [
                        {"term": t["term"], "meaning": t["definition"]}
                        for t in summ.get("explanations", [])
                    ]
                try:
                    with transaction.atomic():

                        today = timezone.localdate()
        
                        last_index_data = SummaryGroup.objects.filter(date=today).aggregate(max_index=Max('group_index'))
                        last_index = last_index_data.get('max_index')

                        if last_index is None:
                            next_index = 1
                        else:
                            next_index = last_index + 1

                        new_summary_group = SummaryGroup.objects.create(date=today, group_index=next_index)

                        db_summary = Summary.objects.create(
                            article=article_orm_object, 
                            title=summ["title"],
                            content=summ["summary_5sentences"],
                            group=new_summary_group
                        )

                        term_objects_to_link = []
                        for t_data in terms_payload:
                            term_obj, _ = Term.objects.get_or_create(
                                term=t_data["term"],
                                defaults={'meaning': t_data["meaning"]}
                            )
                            term_objects_to_link.append(term_obj)

                        if term_objects_to_link:
                            db_summary.terms.set(term_objects_to_link)

                    # 4. [공통] 성공 시 처리 (daily_job.py와 동일)
                    summ["db_id"] = db_summary.pk
                    saved_summaries_with_db_id.append(summ)
                    saved_summaries_orm.append(db_summary)

                    self.stdout.write(self.style.SUCCESS(f"   -> 요약/용어 저장 완료 (ID: {db_summary.pk})"))
                
                except Exception as e:
                    self.stderr.write(f"   -> 요약/용어 저장 DB 오류: {e}")
                    traceback.print_exc()

            # -------------------------------------------------------
            # STEP 3. 퀴즈 생성 및 저장 (Quiz)
            # -------------------------------------------------------
            self.stdout.write(f"--- 3️⃣ [사용자: {profile.user.username}] 퀴즈 생성 중... ---")

            # AI 에이전트 호출 (daily_job.py와 동일)
            state['context']['summaries'] = saved_summaries_with_db_id
            all_quizzes_from_agent = quiz.build_daily_quizzes(state=state, profile=profile_dict)

            # 💡 [수정] 'db_id' 맵 대신, 'Summary ORM 객체' 맵을 사용
            summary_orm_map = {s.title: s for s in saved_summaries_orm}

            total_quiz_count = 0
            success_quiz_count = 0

            for quiz_group in all_quizzes_from_agent:
                title = quiz_group["title"]
                
                # 💡 [수정] ID 대신 ORM 객체를 가져옴
                summary_orm_object = summary_orm_map.get(title) 
                
                if not summary_orm_object:
                    self.stdout.write(f"   -> 스킵: 일치하는 요약(ORM)이 없음 (기사: {title[:10]}...)")
                    continue

                for q in quiz_group["questions"]:
                    total_quiz_count += 1
                    
                    q_type_from_agent = q["type"]
                    
                    try:
                        if q_type_from_agent == "OX":
                            ans_val = str(q["answer"]).upper()
                            correct_bool = (ans_val in ["O", "TRUE", "1"])
                            
                            db_quiz = OXQuiz.objects.create(
                                summary=summary_orm_object,
                                question=q["question"],
                                explanation=q.get("explanation", ""),
                                correct_answer=correct_bool
                            )
                            
                        elif q_type_from_agent == "ShortAnswer":
                            db_quiz = ShortAnswerQuiz.objects.create(
                                summary=summary_orm_object,
                                question=q["question"],
                                explanation=q.get("explanation", ""),
                                correct_answer=str(q["answer"])
                            )

                        elif q_type_from_agent == "MC4":
                            options_payload = q.get("options", [])
                            correct_answer_text = str(q["answer"]) 
                            
                            if len(options_payload) != 4:
                                 self.stdout.write(f"    -> [경고] MC4 퀴즈 보기 4개 아님. 스킵.")
                                 continue 

                            correct_count = 0
                            options_to_create = []
                            for idx, opt_text in enumerate(options_payload):
                                is_correct = (str(opt_text) == correct_answer_text)
                                if is_correct: 
                                    correct_count += 1
                                
                                options_to_create.append(
                                    QuizOption(
                                        text=opt_text,
                                        order=idx + 1,
                                        is_correct=is_correct
                                    )
                                )
                            
                            if correct_count != 1:
                                self.stdout.write(f"    -> [경고] MC4 퀴즈 정답 1개 아님. 스킵.")
                                continue
                            
                            with transaction.atomic():
                                db_quiz = MultipleChoiceQuiz.objects.create(
                                    summary=summary_orm_object,
                                    question=q["question"],
                                    explanation=q.get("explanation", ""),
                                    choice_type=MultipleChoiceQuiz.TYPE_MC4
                                )
                                
                                for opt in options_to_create:
                                    opt.quiz = db_quiz

                                QuizOption.objects.bulk_create(options_to_create)
                        
                        else:
                            self.stdout.write(f"   -> 알 수 없는 퀴즈 유형: {q_type_from_agent}")
                            continue

                        success_quiz_count += 1
                        self.stdout.write(self.style.SUCCESS(f"    -> {q_type_from_agent} 퀴즈 1개 저장 완료 (ID: {db_quiz.pk})"))

                    except Exception as e:
                        self.stderr.write(f"    -> 퀴즈 저장 DB 오류 ({q_type_from_agent}): {e}")
                        traceback.print_exc()

            self.stdout.write(f"✅ [사용자: {profile.user.username}] 퀴즈 생성 시도: {total_quiz_count}개 / 저장 성공: {success_quiz_count}개")
        
        self.stdout.write(self.style.SUCCESS("🎉 모든 사용자 작업 완료!"))