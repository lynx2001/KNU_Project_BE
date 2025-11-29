import os
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

load_dotenv()


llm = ChatOpenAI(temperature=0.7, model="gpt-4o")

#각 퀴즈 형식
class OXQuiz(BaseModel):
    question: str = Field(description="O/X 질문")
    answer: bool = Field(description="정답 (True=O, False=X)")
    rationale: str = Field(description="정답에 대한 간단한 해설")

class MultipleChoice3(BaseModel):
    question: str = Field(description="3지선다 질문")
    options: List[str] = Field(description="3개의 보기 리스트 (반드시 3개)")
    answer_index: int = Field(description="정답 보기의 인덱스 (0, 1, 2)")
    rationale: str = Field(description="정답에 대한 간단한 해설")

class MultipleChoice5(BaseModel):
    question: str = Field(description="5지선다 질문")
    options: List[str] = Field(description="5개의 보기 리스트 (반드시 5개)")
    answer_index: int = Field(description="정답 보기의 인덱스 (0~4)")
    rationale: str = Field(description="정답에 대한 간단한 해설")

class ShortAnswer(BaseModel):
    question: str = Field(description="단답형 질문")
    answer: str = Field(description="정답 (단어 또는 짧은 구)")
    rationale: str = Field(description="정답에 대한 간단한 해설")
