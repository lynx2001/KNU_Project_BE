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

prompt_template_text = """
당신은 주어진 내용을 바탕으로 퀴즈를 출제하는 전문 교사입니다.
제시된 {context} 내용을 기반으로, 학생들의 이해도를 평가할 수 있는 퀴즈를 생성해야 합니다.

---
[유형별 규칙]
요청된 퀴즈 유형({task})에 따라 다음 규칙을 준수하세요.

1. "ShortAnswer" (단답형) 요청 시:
   - **질문(question)**: 질문의 답이 반드시 {context} 내용에 나오는 **'핵심 단어' 또는 '단일 개념' (한두 단어)**이 되도록 질문을 구성해야 합니다.
   - **정답(answer)**: '한 단어' 또는 '매우 짧은 구'여야 합니다. **반드시 리스트(List[str]) 형태여야 합니다.**
   - **[중요]** 만약 질문의 답이 '...중 하나'처럼 여러 개일 수 있다면, 가능한 모든 정답을 리스트에 담아 제공해야 합니다.
   - [나쁜 예시]: 질문: "물가 상승의 원인과 결과는?" (X - 답이 김)
   - [좋은 예시 1 (단일 답)]: 질문: "기업이 주주에게 이익을 분배하는 돈을 무엇이라 하는가?", 정답: ["배당금"]
   - [좋은 예시 2 (복수 답)]: 질문: "이 보고서가 지적한 두 가지 주요 위험 요인 중 하나는?", 정답: ["환율 변동", "공급망 불안"]

2. "MC4", "OX" 요청 시:
   - {context}의 내용을 기반으로 질문, 보기, 정답을 구성하세요.
---

[공통 지"시사항]
1. 퀴즈 유형: {task} (위의 유형별 규칙을 따르세요)
2. 출력 형식: 아래 {format_instructions} 에 명시된 JSON 형식을 철저히 준수해야 합니다.
3. 해설 포함: 모든 문제에는 정답에 대한 간단한 해설(rationale)을 포함해야 합니다.
4. 스타일 가이드: {variant}
5. 안전 규칙(엄수): {safe_rules}
    
추가 지시: 동일한 내용이라도 매 실행마다 표현, 포맷, 보기 구성과 오답 함정은 다르게 생성하세요.
    DIVERSITY_KEY는 의미 없는 값이며, 다양성을 높이기 위한 힌트입니다.

[내용]
{context}
"""

term_prompt_template_text = """
당신은 주어진 내용을 바탕으로 '경제 용어' 퀴즈를 출제하는 전문 교사입니다.
제시된 {context} 내용에서 **핵심 경제 용어**를 선정해야 합니다.

요청된 퀴즈 유형({task})에 따라 다음 규칙을 준수하세요.

---
[유형별 규칙 1: "ShortAnswer" (단답형) 요청 시]
- **질문(question)**: 용어의 '정의' 또는 '설명'이 되어야 합니다.
- **정답(answer)**: '용어' 자체가 되어야 합니다. **반드시 리스트(List[str]) 형태여야 합니다.**
- [예시]
  - 질문: "주식, 채권 등 유가증권이 거래되는 구체적인 시장을 무엇이라고 합니까?"
  - 정답: ["유가증권시장"]

[유형별 규칙 2: "MC4" (객관식) 요청 시]
- **질문(question)**: "다음 중 '[정의]'에 해당하는 경제 용어는 무엇인가?"와 같이, 정의를 제시하고 용어를 묻는 형식이 되어야 합니다.
- **보기(options)**: 정답 용어 1개와, {context}에 등장하는 다른 용어 또는 관련 분야의 **그럴듯한 '다른 용어'**들로 구성되어야 합니다. **보기는 '정의'나 '설명'이 아닌 '용어'여야 합니다.**
- **정답(answer_index)**: 정답 용어의 인덱스.
- [예시]
  - 질문: "상장된 모든 주식의 시장 가치를 합산한 총액을 의미하는 용어는 무엇인가?"
  - 보기: ["코스피", "시가총액", "순매수", "데이터센터", "유가증권시장"]
  - 정답 인덱스: 1

[유형별 규칙 3: "OX" (참/거짓) 요청 시]
- **질문(question)**: "'[용어]'는 [정의]를 의미한다. (O/X)"와 같이, 용어와 정의의 관계가 올바른지 묻는 형식이 되어야 합니다.
- **정답(answer)**: True 또는 False.
- [예시]
  - 질문: "'순매도'는 투자자가 주식을 산 수량이 판 수량보다 많은 것을 의미한다. (O/X)"
  - 정답: False
---

[공통 지시사항]
1. 퀴즈 유형: {task} (위의 유형별 규칙을 따르세요)
2. 근거: 용어는 반드시 {context} 본문에 등장하거나, 본문의 핵심 개념과 직접적으로 관련된 용어여야 합니다.
3. 출력 형식: 아래 {format_instructions} 에 명시된 JSON 형식을 철저히 준수해야 합니다.
4. 해설 포함: 모든 문제에는 정답(용어)에 대한 간단한 해설(rationale)을 포함해야 합니다.
5. 스타일 가이드: {variant}
6. 안전 규칙(엄수): {safe_rules}
    
추가 지시: 동일한 내용이라도 매 실행마다 표현, 포맷, 대상 용어는 다르게 생성하세요.
    DIVERSITY_KEY는 의미 없는 값이며, 다양성을 높이기 위한 힌트입니다.

[내용]
{context}
"""

def post_shuffle(quiz):
    from copy import deepcopy
    q = deepcopy(quiz)

    if isinstance(q, MultipleChoice4):
        idx = q.answer_index
        correct = q.options[idx]
        random.shuffle(q.options)
        q.answer_index = q.options.index(correct)
    return q

def generate_quiz(context: str, quiz_type: str, is_term_quiz: bool = False):
    """
    주어진 내용(context)과 퀴즈 유형(quiz_type)에 따라 퀴즈를 '자동으로 생성'합니다.
    [수정됨]: is_term_quiz=True이면 '경제 용어' 프롬프트를 사용합니다.
    """
    
    model_class, task_description = None, None
    
    if is_term_quiz:
        selected_prompt_template = term_prompt_template_text
        task_prefix = "경제 용어 " # 작업 설명에 추가
    else:
        selected_prompt_template = prompt_template_text
        task_prefix = "" # 일반 퀴즈
    
    if quiz_type == "OX":
        model_class = OXQuiz
        task_description = f"{task_prefix}O/X 퀴즈 1개"
    elif quiz_type == "MC4":
        model_class = MultipleChoice4
        task_description = f"{task_prefix}4지선다 객관식 퀴즈 1개"
    elif quiz_type == "ShortAnswer":
        model_class = ShortAnswer
        task_description = f"{task_prefix}단답형 퀴즈 1개" 
    else:
        print(f"오류: 지원하지 않는 퀴즈 유형입니다. ({quiz_type})")
        return None

    try:
        parser = PydanticOutputParser(pydantic_object=model_class)
        format_instructions = parser.get_format_instructions()
        
        entropy = uuid.uuid4().hex  
        variant = random.choice(QUIZ_STYLE_VARIANTS)

        prompt = ChatPromptTemplate.from_template(
            template=selected_prompt_template + "\n[DIVERSITY_KEY]\n{diversity}\n",
            partial_variables={"format_instructions": format_instructions}
        )
        
        chain = prompt | llm | parser
        
        
        result = chain.invoke({
            "context": context,
            "task": task_description,
            "diversity": entropy,      
            "variant": variant,
            "safe_rules": SAFE_RULES,
        })
        
    
        if not is_term_quiz or (isinstance(result, ShortAnswer)):
             return post_shuffle(result)
        else:
             return result 
        
    except Exception as e:
        print(f"퀴즈 생성 중 오류 발생: {e}")
        return None
