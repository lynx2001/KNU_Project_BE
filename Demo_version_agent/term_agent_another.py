import os
from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
from dotenv import load_dotenv

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
langchain_key = os.getenv("LANGCHAIN_API_KEY")


class EconomicTerm(BaseModel):
    """뉴스에서 추출한 개별 핵심 경제 용어"""
    term: str = Field(description="뉴스에서 추출한 핵심 경제 용어")

class ExtractedTerms(BaseModel):
    """추출된 경제 용어 목록을 감싸는 모델"""
    terms: List[EconomicTerm] = Field(description="추출된 경제 용어 목록")

try:
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
except Exception as e:
    if "api_key" in str(e):
        print("="*50)
        print("!! 오류: OPENAI_API_KEY가 설정되지 않았습니다.")
        print("환경 변수로 API 키를 설정해주세요.")
        print("="*50)
        exit()
    else:
        print(f"LLM 초기화 오류: {e}")
        exit()

summarization_prompt_template = """
당신은 유능한 뉴스 편집자입니다. 학생들의 경제 교육을 위해
다음 원본 뉴스 기사의 핵심 내용을 3~4 문장으로 요약해주세요.

원본 기사:
{full_news_article}

요약:
"""

prompt_summarizer = ChatPromptTemplate.from_template(summarization_prompt_template)

summarization_chain = prompt_summarizer | llm | StrOutputParser()


extraction_prompt_template = """
당신은 유능한 경제 분석가입니다. 학생들을 교육할 목적으로 다음 뉴스 요약본에서 
교육적으로 의미 있는 핵심 경제 용어를 3개에서 5개 사이로 추출해야 합니다.

뉴스 요약:
{news_summary}
"""

prompt_extractor = ChatPromptTemplate.from_template(extraction_prompt_template)

extraction_chain = prompt_extractor | llm.with_structured_output(ExtractedTerms)


explanation_prompt_template = """
당신은 친절한 경제 선생님입니다. 다음 경제 용어에 대해 학생이 이해하기 쉽게 설명해주세요.
특히, 이 용어가 아래 '뉴스 문맥'에서 어떤 의미로 사용되었는지에 초점을 맞춰야 합니다.

**[매우 중요] 설명은 반드시 1줄에서 최대 3줄 이내로 간결하게 요약해야 합니다.**

경제 용어: {term}
뉴스 문맥: {context}

간결한 설명 (1~3줄):
"""

prompt_explainer = ChatPromptTemplate.from_messages([
    ("system", explanation_prompt_template)
])

explanation_chain = prompt_explainer | llm | StrOutputParser()


def process_single_article(full_news_article: str) -> dict:
    """
    하나의 원본 뉴스 기사를 받아 [요약 -> 용어 추출 -> 용어 설명] 파이프라인을 실행합니다.
    """
    
    print(f"\n--- [기사 처리 시작] ---")
    
    try:
        print("[1] 기사 요약 중...")
        news_summary = summarization_chain.invoke({"full_news_article": full_news_article})
        print(f" 요약 완료: {news_summary[:50]}...")

        print("[2] 용어 추출 중...")
        extracted_data = extraction_chain.invoke({"news_summary": news_summary})
        print(f" 용어 추출 완료: {', '.join([t.term for t in extracted_data.terms])}")

        if not extracted_data.terms:
            print("! 추출된 경제 용어가 없습니다.")
            return {"summary": news_summary, "education_content": []}

        print("[3] 용어 설명 생성 중...")
        final_education_content = []
        for item in extracted_data.terms:
            explanation = explanation_chain.invoke({
                "term": item.term,
                "context": news_summary  
            })
            
            final_education_content.append({
                "term": item.term,
                "explanation": explanation.strip() 
            })
        print(" 모든 용어 설명 완료")

        return {
            "summary": news_summary,
            "education_content": final_education_content
        }

    except Exception as e:
        print(f"!! 기사 처리 중 오류 발생: {e}")
        return {"summary": "처리 중 오류가 발생했습니다.", "education_content": []}


if __name__ == "__main__":
    
    
    news_article_1 = """
    (로이터=뉴스1) = 미국 연방준비제도(연준·Fed)가 2일(현지시간) 기준 금리를 5.25~5.50%로 동결했다. 
    이는 지난해 9월 이후 7회 연속 동결이다. 제롬 파월 연준 의장은 기자회견에서 "인플레이션이 지난 1년간 
    상당히 완화됐지만, 여전히 너무 높다"며 "인플레이션이 2% 목표를 향해 지속 가능하게 움직인다는 
    더 큰 확신이 생길 때까지 금리 인하를 시작하는 것이 적절하지 않다"고 밝혔다. 
    시장은 파월 의장의 발언을 '매파적'으로 해석하며 연내 금리 인하 기대감을 낮췄다.
    """
    
    news_article_2 = """
    (서울=연합뉴스) 코스피가 2일 외국인과 기관의 '쌍끌이' 매도세에 밀려 2,600선 아래로 하락 마감했다. 
    이날 코스피 종가는 전 거래일보다 30.17포인트(1.15%) 내린 2,591.31로 집계됐다. 
    미국발 금리 인하 지연 우려가 투자 심리를 위축시킨 것으로 풀이된다. 
    특히 반도체 대장주인 삼성전자와 SK하이닉스가 동반 하락하며 지수 하락을 부추겼다. 
    원·달러 환율은 전일 대비 5.4원 오른 1,380.5원에 마감하며 환율 불안정성도 커졌다.
    """

    news_article_3 = """
    (뉴욕=AP/뉴시스) = 엔비디아가 시장 예상치를 뛰어넘는 1분기 실적을 발표하며 '어닝 서프라이즈'를 기록했다. 
    매출은 전년 동기 대비 262% 증가한 260억 달러를 기록했으며, 특히 데이터센터 부문 매출이 
    AI 붐에 힘입어 427% 급증했다. 실적 발표 후 엔비디아 주가는 시간 외 거래에서 7% 이상 급등했다. 
    이러한 호실적은 AI 반도체 시장의 폭발적인 성장을 재확인시켜주었으며, 관련 기술주 랠리에 
    대한 기대감을 키우고 있다.
    """

    list_of_news_articles = [news_article_1, news_article_2, news_article_3]
    
    all_results = []
    
    for article in list_of_news_articles:
        result_for_article = process_single_article(article)
        all_results.append(result_for_article)
    
    print("\n\n" + "="*50)
    print("--- [최종 API 응답 (JSON 예시)] ---")
    print("="*50)
    
    print(json.dumps(all_results, indent=2, ensure_ascii=False))