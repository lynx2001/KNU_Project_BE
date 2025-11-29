import os, uuid
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.globals import set_llm_cache
import random


#퀴즈 캐시 비활성화 함으로써 중복방지
set_llm_cache(None)  


load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.9,
    top_p=1.0,
    presence_penalty=0.6,
    frequency_penalty=0.3,
)

class OXQuiz(BaseModel):
    question: str = Field(description="O/X 질문")
    answer: bool = Field(description="정답 (True=O, False=X)")
    rationale: str = Field(description="정답에 대한 간단한 해설")

class MultipleChoice4(BaseModel):
    question: str = Field(description="4지선다 질문")
    options: List[str] = Field(description="4개의 보기 리스트 (반드시 4개)")
    answer_index: int = Field(description="정답 보기의 인덱스 (0, 1, 2, 3)")
    rationale: str = Field(description="정답에 대한 간단한 해설")

class ShortAnswer(BaseModel):
    question: str = Field(description="단답형 질문")
    # answer: str = Field(description="정답 (단어 또는 짧은 구)") # (이전 코드)
    answer: List[str] = Field(description="정답 리스트 (단어 또는 짧은 구). '...요인 중 하나는?'처럼 답이 여러 개일 수 있는 경우, 가능한 단답형 정답을 리스트에 모두 포함하세요. (예: ['미국 셧다운 종료 기대감', '배당소득 분리과세 완화'])")
    rationale: str = Field(description="정답에 대한 간단한 해설")

QUIZ_STYLE_VARIANTS = [
    "보기는 난이도 순으로 섞고, 오답엔 실제 헷갈리는 개념을 섞어라.",
    #"지문 속 수치를 활용해 함정 보기를 만들어라.",
    "정답 해설은 1문장 요약 + 핵심 근거 1개로 써라.",
    "질문은 사실 확인형으로, 보기는 원인/결과를 섞어라.",
]

SAFE_RULES = """
- 숫자 함정 금지: 정확한 수치 (소수점을 포함하는 숫자)를 판단하는 문제를 출제하는 건 되도록 삼가할 것.
- O/X는 개념·사실 확인형 위주(정의, 주체 비교, 원인-결과). 숫자는 반올림 기준 등 ‘명확한 여유(버퍼)’가 있을 때만 사용.
- 객관식 숫자 보기는 정답은 확실히 구분할 수 있게 소수점 없이 출제.
- 불필요한 이중부정, 애매모호 표현, 트릭 금지. 근거는 본문에서 명확히 찾을 수 있어야 함.
"""
