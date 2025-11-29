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
