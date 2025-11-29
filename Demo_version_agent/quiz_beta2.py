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

prompt_template_text = """
당신은 주어진 내용을 바탕으로 퀴즈를 출제하는 전문 교사입니다.
제시된 {context} 내용을 기반으로, 학생들의 이해도를 평가할 수 있는 퀴즈를 생성해야 합니다.

반드시 다음 지시사항을 따라주세요:
1. 퀴즈 유형: {task}
2. 출력 형식: 아래 {format_instructions} 에 명시된 JSON 형식을 철저히 준수해야 합니다.
3. 해설 포함: 모든 문제에는 정답에 대한 간단한 해설(rationale)을 포함해야 합니다.

[내용]
{context}
"""


def generate_quiz(context: str, quiz_type: str):
    """
    주어진 내용(context)과 퀴즈 유형(quiz_type)에 따라 퀴즈를 '자동으로 생성'합니다.
    """
    model_class, task_description = None, None

    if quiz_type == "OX":
        model_class = OXQuiz
        task_description = "O/X 퀴즈 1개"
    elif quiz_type == "MC3":
        model_class = MultipleChoice3
        task_description = "3지선다 객관식 퀴즈 1개"
    elif quiz_type == "MC5":
        model_class = MultipleChoice5
        task_description = "5지선다 객관식 퀴즈 1개"
    elif quiz_type == "ShortAnswer":
        model_class = ShortAnswer
        task_description = "단답형 퀴즈 1개"
    else:
        print(f"오류: 지원하지 않는 퀴즈 유형입니다. ({quiz_type})")
        return None

    try:
        parser = PydanticOutputParser(pydantic_object=model_class)
        format_instructions = parser.get_format_instructions()

        prompt = ChatPromptTemplate.from_template(
            template=prompt_template_text,
            partial_variables={"format_instructions": format_instructions}
        )

        chain = prompt | llm | parser

        result = chain.invoke({
            "context": context,
            "task": task_description
        })
        return result

    except Exception as e:
        print(f"퀴즈 생성 중 오류 발생: {e}")
        return None
