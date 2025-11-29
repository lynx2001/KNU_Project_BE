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


def present_quiz(quiz_object):
    """
    generate_quiz로 '자동 생성된' 퀴즈 객체를 받아
    사용자에게 출제하고, 정답을 확인하고, 해설을 보여줍니다.
    """
    if not isinstance(quiz_object, (OXQuiz, MultipleChoice3, MultipleChoice5, ShortAnswer)):
        print("퀴즈 객체가 올바르지 않아 출력할 수 없습니다.")
        return

    print("\n" + "=" * 30)
    print(f"| 퀴즈: {quiz_object.question}")
    print("=" * 30)

    is_correct = False

    
    if isinstance(quiz_object, OXQuiz):
        user_input = input("| 답 (O / X) : ").strip().upper()
        user_answer = True if user_input == 'O' else (False if user_input == 'X' else None)
        is_correct = (user_answer == quiz_object.answer)

    
    elif isinstance(quiz_object, (MultipleChoice3, MultipleChoice5)):
        for i, option in enumerate(quiz_object.options):
            print(f"  {i + 1}. {option}")
        try:
            user_input = int(input("| 답 (번호 입력) : ").strip())
            is_correct = ((user_input - 1) == quiz_object.answer_index)
        except ValueError:
            is_correct = False

    
    elif isinstance(quiz_object, ShortAnswer):
        user_input = input("| 답 (단답형) : ").strip()
        is_correct = (user_input.replace(" ", "") == quiz_object.answer.replace(" ", ""))

    print("-" * 30)
    print(f"| 정답 여부: {'👍 정답입니다!' if is_correct else '😭 틀렸습니다.'}")
    print(f"| 정답: {quiz_object.answer if not isinstance(quiz_object, OXQuiz) else ('O' if quiz_object.answer else 'X')}")
    print(f"| 해설: {quiz_object.rationale}")
    print("=" * 30 + "\n")

if __name__ == "__main__":
    
    my_content = """
    코스피가 반도체 주식의 강세로 3% 가까이 오르며 처음으로 4200선을 넘었습니다.
    삼성전자와 SK하이닉스는 각각 11만원과 62만원을 기록하며 큰 폭으로 상승했습니다.
    APEC 회의와 한중 정상회담 이후 반도체 주식에 대한 기대감이 커졌습니다.
    개인과 기관 투자자는 주식을 많이 샀지만, 외국인 투자자는 팔았습니다.
    앞으로도 반도체 관련 소식에 주목하면 좋겠습니다.
    """

    #mylevel = "씨앗"
    #mylevel = "새싹"
    #mylevel = "나무"
    mylevel = "숲"

    print("======= [입력 텍스트]로 퀴즈 자동 생성을 시작합니다. =======")

    if mylevel == "씨앗":
        print("...O/X 퀴즈 생성 중...")
        ox_quiz = generate_quiz(my_content, "OX")
        present_quiz(ox_quiz)

    elif mylevel == "새싹":
        print("...3지선다 퀴즈 생성 중...")
        mc3_quiz = generate_quiz(my_content, "MC3")
        present_quiz(mc3_quiz)

    elif mylevel == "나무":
        print("...5지선다 퀴즈 생성 중...")
        mc5_quiz = generate_quiz(my_content, "MC5")
        present_quiz(mc5_quiz)

    elif mylevel == "숲":
        print("단답형 퀴즈 생성 중...")
        shortAnser_quiz = generate_quiz(my_content, "ShortAnswer")
        present_quiz(shortAnser_quiz)
