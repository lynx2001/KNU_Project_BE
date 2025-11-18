from typing import List, Literal, Dict, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

# ✅ 여러 단계를 순서대로 반환하도록 수정
class RouteDecision(BaseModel):
    intents: List[Literal["news_find","news_summary","term_explain","quiz","qa"]]

# ✅ 시스템 프롬프트 수정 (퀴즈 상태 반영 규칙 추가)
SYSTEM_TEMPLATE = (
    "너는 뉴스 학습 튜터 시스템의 **의도 분류자(Supervisor Router)** 역할을 해. "
    "사용자의 요청을 분석해서 어떤 작업 단계들이 필요한지를 **순서대로 판단**해야 해. "

    "현재 상태 정보:\n"
    "- 퀴즈 진행 중 여부(is_quiz_active): {is_quiz_active}\n\n"

    "가능한 단계(intent)는 아래 다섯 가지야:\n"
    "1️⃣ qa — 일반적인 질문이나 사실 확인, 또는 단순 인사·잡담.\n"
    "2️⃣ news_find — 뉴스 검색 요청.\n"
    "3️⃣ news_summary — 뉴스 요약 요청.\n"
    "4️⃣ term_explain — 용어 설명 요청.\n"
    "5️⃣ quiz — 퀴즈 생성 요청 **또는 퀴즈 정답 제출**.\n\n"

    "⭐⭐ **라우팅 최우선 규칙** ⭐⭐:\n"
    "👉 만약 **is_quiz_active=True**이고, 사용자가 숫자('1', '2'...), 알파벳('O', 'X'), 또는 단답형 정답을 말했다면, "
    "다른 생각 하지 말고 무조건 **['quiz']** 로 분류해.\n"
    "   (예: '1' -> ['quiz'], '정답은 O' -> ['quiz'])\n\n"

    "그 외 일반 규칙:\n"
    " - '삼성전자 주가 알려주고 관련 기사 요약해줘' → ['qa','news_find','news_summary']\n"
    " - '최근 금리 기사 찾아서 퀴즈 내줘' → ['news_find','quiz']\n"
    " - '안녕', '고마워' → ['qa']\n\n"

    "만약 사용자의 요청이 위 단계들에 명확히 맞지 않는다면 기본적으로 ['qa'] 로 분류해.\n"
    "항상 JSON 형식으로 아래처럼만 대답해:\n"
    "{{ \"intents\": [ ...단계들... ] }}"
)


def classify_intent(user_text: str, context: Dict[str, Any] = {}) -> List[str]:
    print("[DBG router] IN:", repr(user_text))
    
    # ✅ Context에서 퀴즈 활성화 여부 확인
    is_quiz_active = bool(context.get("active_quiz"))
    if is_quiz_active:
        print(f"[DBG router] Quiz is ACTIVE. Prioritizing 'quiz' intent for answers.")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(RouteDecision)
    
    # 시스템 프롬프트에 상태 주입
    system_prompt = SYSTEM_TEMPLATE.format(is_quiz_active=str(is_quiz_active))
    
    out = llm.invoke([
        {"role":"system","content": system_prompt},
        {"role":"user","content": user_text or ""},
    ])
    
    intents = getattr(out, "intents", None)
    if intents is None:
        intents = [getattr(out, "intent", "qa")]

    print("[DBG router] OUT intents =", intents)
    return intents