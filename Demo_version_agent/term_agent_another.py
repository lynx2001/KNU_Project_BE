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
