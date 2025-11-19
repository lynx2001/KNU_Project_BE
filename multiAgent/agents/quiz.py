"""
quiz.py — 퀴즈 생성 및 채점 에이전트
(v3: quiz.py의 생성 로직 + 그래프 핸들러 결합)
"""
import os, uuid, json, re, random
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.globals import set_llm_cache
from langchain_core.messages import AIMessage

# --- 0. 설정 및 로드 ---
set_llm_cache(None)  # 전역 LLM 캐시 비활성화
load_dotenv()

# ============================================================
# 🔧 디버그 설정 (v2 스타일)
# ============================================================
DEBUG = True

def dprint(*args, **kwargs):
    if DEBUG:
        print("[DBG quiz]", *args, **kwargs)

# --- 1. LLM 모델 초기화 ---
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.9,
    top_p=1.0,
    presence_penalty=0.6,
    frequency_penalty=0.3,
)

# --- 2. Pydantic 퀴즈 구조 정의 (기존 quiz.py 로직) ---
# (원본 quiz.py의 Pydantic 모델)
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
    answer: List[str] = Field(description="정답 리스트 (단어 또는 짧은 구). '...요인 중 하나는?'처럼 답이 여러 개일 수 있는 경우, 가능한 단답형 정답을 리스트에 모두 포함하세요.")
    rationale: str = Field(description="정답에 대한 간단한 해설")

# --- 3. 퀴즈 '자동 생성' 함수 (기존 quiz.py 로직) ---
# (원본 quiz.py의 생성 프롬프트 및 함수)
QUIZ_STYLE_VARIANTS = [
    "보기는 난이도 순으로 섞고, 오답엔 실제 헷갈리는 개념을 섞어라.",
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
# (기존 term_prompt_template_text 변수 전체를 이걸로 교체)

# (기존 term_prompt_template_text 변수 전체를 이걸로 교체)

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
'''
prompt_template_text = """
당신은 주어진 내용을 바탕으로 퀴즈를 출제하는 전문 교사입니다.
제시된 {context} 내용을 기반으로, 학생들의 이해도를 평가할 수 있는 퀴즈를 생성해야 합니다.
[유형별 규칙]
요청된 퀴즈 유형({task})에 따라 다음 규칙을 준수하세요.
1. "ShortAnswer" (단답형) 요청 시:
   - 질문(question): 질문의 답이 반드시 {context} 내용에 나오는 '핵심 단어' 또는 '단일 개념' (한두 단어)이 되도록 질문을 구성해야 합니다.
   - 정답(answer): '한 단어' 또는 '매우 짧은 구'여야 합니다. 반드시 리스트(List[str]) 형태여야 합니다.
   - [중요] 만약 질문의 답이 '...중 하나'처럼 여러 개일 수 있다면, 가능한 모든 정답을 리스트에 담아 제공해야 합니다.
2. "MC4", "OX" 요청 시:
   - {context}의 내용을 기반으로 질문, 보기, 정답을 구성하세요.
[공통 지시사항]
1. 퀴즈 유형: {task} (위의 유형별 규칙을 따르세요)
2. 출력 형식: 아래 {format_instructions} 에 명시된 JSON 형식을 철저히 준수해야 합니다.
3. 해설 포함: 모든 문제에는 정답에 대한 간단한 해설(rationale)을 포함해야 합니다.
4. 스타일 가이드: {variant}
5. 안전 규칙(엄수): {safe_rules}
[내용]
{context}
"""
'''
'''
term_prompt_template_text = """
당신은 주어진 내용을 바탕으로 '경제 용어' 퀴즈를 출제하는 전문 교사입니다.
제시된 {context} 내용에서 **핵심 경제 용어**를 선정해야 합니다.
[유형별 규칙 1: "ShortAnswer" (단답형) 요청 시]
- 질문(question): 용어의 '정의' 또는 '설명'이 되어야 합니다.
- 정답(answer): '용어' 자체가 되어야 합니다. 반드시 리스트(List[str]) 형태여야 합니다.
[유형별 규칙 2: "MC4" (객관식) 요청 시]
- 질문(question): "다음 중 '[정의]'에 해당하는 경제 용어는 무엇인가?"와 같이, 정의를 제시하고 용어를 묻는 형식이 되어야 합니다.
- 보기(options): 정답 용어 1개와, {context}에 등장하는 다른 용어 또는 관련 분야의 그럴듯한 '다른 용어'들로 구성되어야 합니다.
[유형별 규칙 3: "OX" (참/거짓) 요청 시]
- 질문(question): "'[용어]'는 [정의]를 의미한다. (O/X)"와 같이, 용어와 정의의 관계가 올바른지 묻는 형식이 되어야 합니다.
[공통 지시사항]
(이하 quiz.py 원본과 동일)
...
1. 퀴즈 유형: {task}
2. 근거: 용어는 반드시 {context} 본문에 등장하거나, 본문의 핵심 개념과 직접적으로 관련된 용어여야 합니다.
3. 출력 형식: 아래 {format_instructions} 에 명시된 JSON 형식을 철저히 준수해야 합니다.
4. 해설 포함: 모든 문제에는 정답(용어)에 대한 간단한 해설(rationale)을 포함해야 합니다.
5. 스타일 가이드: {variant}
6. 안전 규칙(엄수): {safe_rules}
[내용]
{context}
"""
'''
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
    model_class, task_description = None, None
    
    if is_term_quiz:
        selected_prompt_template = term_prompt_template_text
        task_prefix = "경제 용어 "
    else:
        selected_prompt_template = prompt_template_text
        task_prefix = ""
    
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
        dprint(f"오류: 지원하지 않는 퀴즈 유형입니다. ({quiz_type})")
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
        dprint(f"퀴즈 생성 중 오류 발생: {e}")
        return None

def generate_quiz_candidates(context: str, quiz_type: str, k: int = 3, is_term_quiz: bool = False):
    return [q for _ in range(k) if (q := generate_quiz(context, quiz_type, is_term_quiz=is_term_quiz))]

def pick_one_quiz(context: str, quiz_type: str, k: int = 3, is_term_quiz: bool = False):
    cands = generate_quiz_candidates(context, quiz_type, k, is_term_quiz=is_term_quiz)
    def score(q):
        rationale_len = len(getattr(q, "rationale", "") or "")
        uniq_opts = len(set(getattr(q, "options", []) or []))
        return rationale_len + uniq_opts
    cands.sort(key=score, reverse=True)
    return (random.choice(cands[:2]) if len(cands) >= 2 else (cands[0] if cands else None))

def pick_many_quizzes(context: str, quiz_type: str, n: int = 2, k: int = 4, is_term_quiz: bool = False):
    quizzes, seen = [], set()
    max_trials = n * 5
    trials = 0
    while len(quizzes) < n and trials < max_trials:
        trials += 1
        q = pick_one_quiz(context, quiz_type, k=k, is_term_quiz=is_term_quiz)
        if not q:
            continue
        if q.question in seen:
            continue
        seen.add(q.question)
        quizzes.append(q)
    return quizzes

# --- 4. [신규 추가] 그래프 호환을 위한 헬퍼 ---

def analyze_user_intent(text: str) -> Dict:
    """사용자 의도를 '퀴즈 요청'과 '정답 제출'로 분리"""
    llm_analyzer = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    sys_msg = (
        "너는 사용자의 발화 의도를 분석하는 모델이다.\n"
        "사용자가 퀴즈를 내달라고 하는지(REQUEST), 아니면 퀴즈의 정답을 맞히고 있는지(ANSWER) 판단해라.\n"
        "만약 REQUEST라면, 사용자가 원하는 퀴즈 타입(OX, MC4, ShortAnswer)과 개수(n), 그리고 '용어 퀴즈'인지(is_term)인지 추출해라.\n\n"
        "규칙:\n"
        "1. 타입: 'OX퀴즈'->OX, '객관식/4지선다'->MC4, '단답형/주관식'->ShortAnswer. 언급 없으면 null.\n"
        "2. 개수: 언급 없으면 1 (기본값).\n"
        "3. 용어: '용어 퀴즈', '단어 퀴즈' 등 언급 시 is_term: true. 아니면 false.\n"
        "4. 정답 제출일 경우: '정답은 O야', '1번', '금리' 등 답을 말하는 패턴이면 ANSWER로 분류.\n\n"
        "출력 JSON 예시:\n"
        "- \"OX 퀴즈 하나 내줘\": {\"action\": \"REQUEST\", \"type\": \"OX\", \"count\": 1, \"is_term\": false}\n"
        "- \"용어 퀴즈 3개\": {\"action\": \"REQUEST\", \"type\": null, \"count\": 3, \"is_term\": true}\n"
        "- \"정답은 O\": {\"action\": \"ANSWER\", \"user_answer\": \"O\"}\n"
        "- \"1번이야\": {\"action\": \"ANSWER\", \"user_answer\": \"1\"}\n"
        "- \"모르겠어\": {\"action\": \"GIVEUP\"}"
    )

    try:
        res = llm_analyzer.invoke([("system", sys_msg), ("user", text)])
        raw = res.content.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e:
        dprint(f"Intent analysis failed: {e}")
        # supervisor_router.py가 퀴즈 상태에서 입력을 'quiz'로 분류한 경우,
        # 사용자가 '1'이나 'O'만 입력했을 수 있으므로 ANSWER로 가정
        if re.fullmatch(r"^\s*([0-9]|O|X)\s*$", text, re.IGNORECASE):
             return {"action": "ANSWER", "user_answer": text.strip()}
        return {"action": "REQUEST", "type": None, "count": 1, "is_term": False}

def _normalize_answer(text: str) -> str:
    """채점을 위한 정규화"""
    return (text or "").lower().replace(" ", "")

def _check_short_answer(user_answer: str, correct_answers: List[str]) -> bool:
    """quiz.py 원본의 유연한 단답형 채점 로직"""
    user_norm = _normalize_answer(user_answer)
    if not user_norm: return False
    
    for correct_answer in correct_answers:
        answer_norm = _normalize_answer(correct_answer)
        if not answer_norm: continue

        # 1. 완전 일치
        if user_norm == answer_norm:
            return True
        
        # 2. 유연한 포함 관계 (원본 quiz.py 로직)
        try:
            if len(user_norm) > len(answer_norm):
                longer_str, shorter_str = user_norm, answer_norm
            else:
                longer_str, shorter_str = answer_norm, user_norm

            if shorter_str in longer_str and (len(shorter_str) / len(longer_str)) >= 0.8:
                return True
        except ZeroDivisionError:
            continue
            
    return False

def _format_correct_answer(quiz_data: Dict) -> str:
    """quiz.py 원본의 정답 포맷팅 로직"""
    q_type = quiz_data.get("type_str", "") # active_quiz에 저장된 Pydantic 모델 이름
    
    if q_type == "OXQuiz":
        return "O" if quiz_data.get("answer") else "X"
    elif q_type == "MultipleChoice4":
        idx = quiz_data.get("answer_index", -1)
        opts = quiz_data.get("options", [])
        if 0 <= idx < len(opts):
            return f"{idx + 1}. {opts[idx]}"
        return "[정답 오류]"
    elif q_type == "ShortAnswer":
        return ", ".join(quiz_data.get("answer", []))
    return str(quiz_data.get("answer", "[N/A]"))


# --- 5. [신규 추가] 메인 핸들러 (그래프 호출용) ---
def handle(text: str, profile: Optional[Dict[str, Any]] = None, state: Optional[Dict[str, Any]] = None) -> AIMessage:
    dprint("[handle] ENTER quiz_node (v3)")

    ctx = (state or {}).get("context", {})
    profile = profile or (state or {}).get("profile", {}) or {}
    
    if isinstance(profile, dict):
        # 딕셔너리로 넘어온 경우 (현재 Django 환경)
        level = profile.get("grade", "새싹")
    else:
        # 객체로 넘어온 경우 (기존 환경 호환)
        level = getattr(profile, "grade", "새싹")
    
    intent_data = analyze_user_intent(text)
    action = intent_data.get("action")
    dprint(f"User Action: {action}, Data: {intent_data}")

    # --- CASE A: 정답 채점 ---
    if action == "ANSWER" or action == "GIVEUP":
        active_quiz = ctx.get("active_quiz")
        if not active_quiz:
            dprint("No active quiz found in context. Ignoring ANSWER.")
            return AIMessage(content="[quiz] 채점할 문제가 없어요. 먼저 퀴즈를 요청해 주세요.")
        
        dprint(f"Grading active quiz: {active_quiz.get('question')[:20]}...")
        
        user_ans = intent_data.get("user_answer", "").strip()
        explanation = active_quiz.get("rationale", "")
        q_type_str = active_quiz.get("type_str", "") # 'OXQuiz', 'MultipleChoice4', 'ShortAnswer'
        
        is_correct = False
        if action == "GIVEUP":
            dprint("User gave up.")
            is_correct = False # 포기는 오답 처리
        
        # O/X 채점
        elif q_type_str == "OXQuiz":
            correct_ans_bool = active_quiz.get("answer", False)
            user_ans_norm = user_ans.upper()
            if (user_ans_norm in ["O", "0", "TRUE"]) and correct_ans_bool: is_correct = True
            elif (user_ans_norm in ["X", "FALSE"]) and not correct_ans_bool: is_correct = True
        
        # 객관식 채점
        elif q_type_str == "MultipleChoice4":
            correct_idx = active_quiz.get("answer_index", -1)
            try:
                user_idx = int(re.sub(r"[^0-9]", "", user_ans)) - 1
                if user_idx == correct_idx:
                    is_correct = True
            except ValueError:
                is_correct = False # 숫자로 변환 실패
        
        # 단답형 채점
        elif q_type_str == "ShortAnswer":
            correct_answers_list = active_quiz.get("answer", [])
            is_correct = _check_short_answer(user_ans, correct_answers_list)

        # 채점 결과 전송
        ctx["active_quiz"] = None # 퀴즈 상태 초기화
        formatted_answer = _format_correct_answer(active_quiz)

        if is_correct:
            dprint("Correct answer.")
            return AIMessage(content=f"🎉 **정답입니다!**\n\n💡 해설: {explanation}")
        else:
            dprint(f"Wrong answer. User: '{user_ans}', Correct: '{formatted_answer}'")
            if action == "GIVEUP":
                return AIMessage(content=f"정답은 **{formatted_answer}** 입니다.\n\n💡 해설: {explanation}")
            else:
                return AIMessage(content=f"땡! 아쉽네요. 😅\n정답은 **{formatted_answer}** 입니다.\n\n💡 해설: {explanation}")


    # --- CASE B: 퀴즈 출제 ---
    dprint("Requesting new quiz.")
    summaries = ctx.get("summaries", [])
    if not summaries:
        dprint("No summaries found.")
        return AIMessage(content="[quiz] 퀴즈를 만들 기사가 없어요. 뉴스 검색과 요약을 먼저 해주세요.")

    # quiz.py __main__의 레벨별 유형 매핑 적용
    level_to_type_map = {
        "씨앗": "OX",
        "새싹": "MC4",
        "나무": "MC4",
        "숲": "ShortAnswer"
    }
    
    req_type = intent_data.get("type") # OX, MC4, ShortAnswer
    req_count = intent_data.get("count", 1)
    req_is_term = intent_data.get("is_term", False)
    
    # 사용자가 타입을 지정하지 않으면, 레벨에 따라 자동 설정
    target_quiz_type = req_type if req_type else level_to_type_map.get(level, "MC4")
    
    # 컨텍스트 선택 (가장 최근 요약본)
    target_article = summaries[-1]
    # quiz.py의 생성 함수는 '요약문' 텍스트를 받음
    context_text = target_article.get("summary_5sentences", "")
    if not context_text:
        context_text = target_article.get("title", "") # 요약이 없으면 제목이라도
        
    dprint(f"Generating {req_count} quiz(zes) of type '{target_quiz_type}' (is_term={req_is_term}) for level '{level}'...")
    
    quizzes = pick_many_quizzes(
        context_text, 
        target_quiz_type, 
        n=req_count, 
        k=4, 
        is_term_quiz=req_is_term
    )
    
    if not quizzes:
        dprint("Failed to generate any quiz.")
        return AIMessage(content="[quiz] 문제를 생성하지 못했어요. (요약 내용이 너무 짧거나 오류 발생)")

    # (N개 요청했어도 일단 1개만 출제하고 나머지는 버림 - 대화형이므로)
    first_q_model = quizzes[0]
    
    # Pydantic 모델을 state에 저장하기 위해 dict로 변환
    # [중요] Pydantic 모델 클래스 이름을 저장해야 채점 시 타입을 알 수 있음
    active_quiz_data = first_q_model.model_dump()
    active_quiz_data["type_str"] = first_q_model.__class__.__name__ # 'OXQuiz', 'MultipleChoice4', 'ShortAnswer'
    
    ctx["active_quiz"] = active_quiz_data
    dprint(f"Saved active quiz to context. Type: {active_quiz_data['type_str']}")

    # 사용자에게 보낼 메시지 포맷팅
    q_type_lbl = {
        "OXQuiz": "OX 퀴즈", 
        "MultipleChoice4": "객관식", 
        "ShortAnswer": "단답형"
    }.get(active_quiz_data["type_str"], "퀴즈")
    
    if req_is_term:
        q_type_lbl = f"경제 용어 {q_type_lbl}"

    msg = [f"[quiz] **{q_type_lbl}**를 냈어요!\n"]
    msg.append(f"Q. {active_quiz_data['question']}\n")
    
    if active_quiz_data["type_str"] == "MultipleChoice4":
        for i, opt in enumerate(active_quiz_data['options'], 1):
            msg.append(f"   {i}) {opt}")
    elif active_quiz_data["type_str"] == "OXQuiz":
         msg.append("   (O / X)")
    
    msg.append("\n정답을 입력해 주세요! 👇")
    
    return AIMessage(content="\n".join(msg))

# ============================================================
# 4. [Batch] 데일리 파이프라인용 함수 (✅ 이 부분을 추가하세요)
# ============================================================
def build_daily_quizzes(state: Dict[str, Any], profile: Dict) -> List[Dict]:
    """
    매일 아침 실행되는 배치 작업용 함수.
    ... (주석 생략) ...
    """
    summaries = state.get("context", {}).get("summaries", [])
    level = profile.get("level", "새싹")
    
    level_config = {
        "씨앗": {"type": "OX", "count": 2},
        "새싹": {"type": "choice", "count": 2}, 
        "나무": {"type": "choice", "count": 2}, 
        "숲":   {"type": "short", "count": 2}  
    }
    config = level_config.get(level, level_config["새싹"])
    
    level_to_api_type = {
        "choice": "MC4",
        "short": "ShortAnswer",
        "OX": "OX"
    }
    q_type_api = level_to_api_type.get(config["type"], "MC4")
    q_count = config["count"]
    
    all_quizzes = []
    
    dprint(f"[Batch] Building {q_count} quizzes (Type: {q_type_api}) for {len(summaries)} articles...")

    for item in summaries:
        context_text = item.get("summary_5sentences", "")
        if not context_text:
            context_text = item.get("title", "")
            
        # ✅ [핵심 수정] 
        # 1. pick_many_quizzes 함수를 호출 (generate_quiz 대신)
        # 2. 'q_type=...' -> 'quiz_type=...' (올바른 인자명 사용)
        qs_models = pick_many_quizzes(
            context_text, 
            quiz_type=q_type_api, 
            n=q_count, 
            k=4, 
            is_term_quiz=False
        )
        
        # Pydantic 모델을 DB 저장을 위해 dict로 변환
        qs_data = []
        for qm in qs_models:
            q_dict = qm.model_dump()
            
            # Pydantic 모델의 'rationale'을 API가 요구하는 'explanation'으로 매핑
            q_dict["explanation"] = q_dict.get("rationale", "")
            
            # API가 요구하는 'type' 필드 추가
            q_dict["type"] = q_type_api 

            # 'answer' 필드 통일 (daily_job.py가 쓰기 편하도록)
            if q_type_api == "OX":
                q_dict["answer"] = "O" if q_dict.get("answer") else "X"
            elif q_type_api == "MC4":
                idx = q_dict.get("answer_index", -1)
                opts = q_dict.get("options", [])
                if 0 <= idx < len(opts):
                    q_dict["answer"] = opts[idx] # 정답 텍스트
                else:
                    q_dict["answer"] = "" # 오류
            elif q_type_api == "ShortAnswer":
                q_dict["answer"] = ", ".join(q_dict.get("answer", [])) # 리스트를 문자열로

            qs_data.append(q_dict)

        item["quizzes"] = qs_data 
        all_quizzes.append({"title": item.get("title"), "questions": qs_data})
        
    return all_quizzes