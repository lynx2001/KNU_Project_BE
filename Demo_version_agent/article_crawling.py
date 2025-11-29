import os
import pathlib
import requests
import bs4
import time
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import feedparser


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import WebBaseLoader





load_dotenv()

# --- LANGCHAIN AGENT FUNCTIONS (수정 없음) ---
def filter_candidates_by_title(news_list: list, user_profile: dict) -> list:
    # ... (기존 코드와 동일)
    print("\n🤖 [1단계] AI가 제목을 기반으로 뉴스 후보군을 필터링합니다...")
    formatted_news_titles = "\n".join([f"{i+1}. {article['title']}" for i, article in enumerate(news_list)])
    prompt = ChatPromptTemplate.from_template("""
     당신은 경제 뉴스 큐레이터입니다. [사용자 정보]와 [뉴스 제목 목록]을 보고,
     사용자에게 가장 관련성 높아 보이는 기사 7개를 선택해주세요.

     [레벨 정의]
     - 씨앗: 경제 용어가 낯선 완전 입문자.
     - 새싹: 기본적인 경제 개념을 배우는 초급자.
     - 나무: 주요 경제 지표를 이해하는 중급자.
     - 숲: 경제 흐름을 종합적으로 분석하는 고급자.

     [사용자 정보]
     - 레벨: {level}
     - 최근 관심사: {chat_history}

     [뉴스 제목 목록]
     {news_titles}

     [요청]
     가장 적합한 기사 7개의 번호를 JSON 형식으로 알려주세요.
     예시: {{"selected_indices": [3, 8, 15, 2, 9, 1, 11]}}""")
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    parser = JsonOutputParser()
    chain = prompt | model | parser
    try:
        response = chain.invoke({"level": user_profile['level'], "chat_history": ", ".join(user_profile['chat_history']), "news_titles": formatted_news_titles})
        selected_indices = response['selected_indices']
        candidate_news = [news_list[i-1] for i in selected_indices if 0 < i <= len(news_list)]
        print(f"✅ 1단계 필터링 완료. 후보 뉴스 {len(candidate_news)}건 선택.")
        return candidate_news
    except Exception as e:
        print(f"🔴 1단계 AI 필터링 실패: {e}")
        return news_list[:7]

def select_final_articles_by_content(candidate_news: list, user_profile: dict) -> list:
    # ... (기존 코드와 동일)
    print("\n🤖 [2단계] AI가 스크랩한 본문을 기반으로 최종 뉴스를 선별합니다...")
    formatted_candidates = "\n\n".join([f"기사 #{i+1}:\n- 제목: {article['title']}\n- 본문 일부: {article.get('content', '내용 없음')}" for i, article in enumerate(candidate_news)])
    prompt = ChatPromptTemplate.from_template("""당신은 개인 맞춤형 경제 뉴스 큐레이터입니다. 사용자의 경제 지식 수준과 관심사를 고려하여, 아래 [후보 뉴스 목록]의 '본문'을 읽고 사용자에게 가장 유익하고 중요한 최종 기사 3개를 골라주세요. [사용자 정보] - 레벨: {level} - 최근 관심사: {chat_history} [후보 뉴스 목록 (제목과 본문)] {candidate_contents} [요청] 가장 적합한 최종 기사 3개의 번호('기사 #')를 JSON 형식으로 알려주세요. 예시: {{"final_indices": [2, 5, 1]}}""")
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    parser = JsonOutputParser()
    chain = prompt | model | parser
    try:
        response = chain.invoke({"level": user_profile['level'], "chat_history": ", ".join(user_profile['chat_history']), "candidate_contents": formatted_candidates})
        final_indices = response['final_indices']
        final_news = [candidate_news[i-1] for i in final_indices if 0 < i <= len(candidate_news)]
        print(f"✅ 2단계 선별 완료. 최종 뉴스 3건 확정.")
        return final_news
    except Exception as e:
        print(f"🔴 2단계 AI 선별 실패: {e}")
        return candidate_news[:3]

def news_collection_pipeline():
    """뉴스 수집부터 2단계 AI 큐레이션까지 전체 프로세스를 실행합니다."""

    sample_user_profile = {
        'level': '새싹',
        'chat_history': ['미국 금리 인상', '환율 전망', '코스피 지수']
    }

    # [변경] feedparser를 사용하여 RSS 피드에서 뉴스 가져오기
    print("📰 뉴스 수집 에이전트: 매일경제 RSS 피드에서 최신 뉴스를 수집합니다...")
    rss_url = "https://www.mk.co.kr/rss/50200011/"
    feed = feedparser.parse(rss_url)

    # RSS 피드에서 제목과 URL을 추출하여 gnews와 동일한 형태로 가공
    all_news = [{'title': entry.title, 'url': entry.link} for entry in feed.entries[:20]]

    if not all_news:
        print("🔴 RSS 피드에서 뉴스를 수집하지 못했습니다.")
        return
    print(f"✅ 뉴스 {len(all_news)}건 수집 완료.")

    candidate_news = filter_candidates_by_title(all_news, sample_user_profile)

    # [변경] 스크레이핑 로직을 '매일경제' 전용으로 단순화
    print("\n🕸️ 후보 뉴스의 본문 스크레이핑을 시작합니다...")
    for article in candidate_news:
        try:
            loader = WebBaseLoader(
                web_paths=(article['url'],),
                bs_kwargs=dict(parse_only=bs4.SoupStrainer("p", attrs={"refid": True})),
                header_template={"User-Agent": "Mozilla/5.0"},
            )
            docs = loader.load()
            content = docs[0].page_content if docs else "매일경제 뉴스 본문을 로드하지 못했습니다."
        except Exception as e:
            content = f"매일경제 뉴스 스크레이핑 중 오류: {e}"

        article['content'] = content

        print(f"\n--- [스크랩 내용 확인] {article['title']} ---")
        print(content[:1500] + "...")
        print(article['url'])
        print("-" * 50)

    print("✅ 모든 후보 뉴스의 본문 스크레이핑 완료.")

    final_three_news = select_final_articles_by_content(candidate_news, sample_user_profile)

    print("\n--- 🌟 최종 선별된 사용자 맞춤 뉴스 3선 🌟 ---")
    for i, article in enumerate(final_three_news, 1):
        print(f"  {i}. {article['title']}")
        print(f"  - 본문: {article['content']}")
        print(f"     - 링크: {article['url']}")
    print("---------------------------------------------")
    return final_three_news, sample_user_profile