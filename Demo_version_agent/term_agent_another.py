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


# ----------------------------------------------------
# 4. Chain 1: 경제 용어 추출 체인
# ----------------------------------------------------

extraction_prompt_template = """
당신은 유능한 경제 분석가입니다. 학생들을 교육할 목적으로 다음 뉴스 요약본에서 
교육적으로 의미 있는 핵심 경제 용어를 3개에서 5개 사이로 추출해야 합니다.

뉴스 요약:
{news_summary}
"""

prompt_extractor = ChatPromptTemplate.from_template(extraction_prompt_template)

extraction_chain = prompt_extractor | llm.with_structured_output(ExtractedTerms)

# ----------------------------------------------------
# 5. Chain 2: 경제 용어 설명 체인
# ----------------------------------------------------

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
        # --- [Step 1] Chain 0: 기사 요약 ---
        print("[1] 기사 요약 중...")
        news_summary = summarization_chain.invoke({"full_news_article": full_news_article})
        print(f"✅ 요약 완료: {news_summary[:50]}...")

        # --- [Step 2] Chain 1: 용어 추출 ---
        print("[2] 용어 추출 중...")
        extracted_data = extraction_chain.invoke({"news_summary": news_summary})
        print(f"✅ 용어 추출 완료: {', '.join([t.term for t in extracted_data.terms])}")

        if not extracted_data.terms:
            print("! 추출된 경제 용어가 없습니다.")
            return {"summary": news_summary, "education_content": []}

        # --- [Step 3] Chain 2: 용어 설명 ---
        print("[3] 용어 설명 생성 중...")
        final_education_content = []
        for item in extracted_data.terms:
            explanation = explanation_chain.invoke({
                "term": item.term,
                "context": news_summary  # 요약본을 문맥으로 제공
            })
            
            final_education_content.append({
                "term": item.term,
                "explanation": explanation.strip() 
            })
        print("✅ 모든 용어 설명 완료")

        # --- [Step 4] 결과 조합 ---
        return {
            "summary": news_summary,
            "education_content": final_education_content
        }

    except Exception as e:
        print(f"!! 기사 처리 중 오류 발생: {e}")
        return {"summary": "처리 중 오류가 발생했습니다.", "education_content": []}
