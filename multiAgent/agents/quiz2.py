"""
quiz.py — 퀴즈 생성 및 채점 에이전트 (Interactive Quiz & Daily Batch)
"""
from typing import List, Dict, Any, Optional
import json, time, re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

# ============================================================
# 🔧 디버그 설정
# ============================================================
DEBUG = True

def dprint(*args, **kwargs):
    if DEBUG:
        print("[DBG quiz]", *args, **kwargs)

# ============================================================
# 1. [Helper] 사용자 의도 파악 (출제 vs 정답제출)
# ============================================================
def analyze_user_intent(text: str) -> Dict:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    sys_msg = (
        "너는 사용자의 발화 의도를 분석하는 모델이다.\n"
        "사용자가 퀴즈를 내달라고 하는지(REQUEST), 아니면 퀴즈의 정답을 맞히고 있는지(ANSWER) 판단해라.\n"
        "만약 REQUEST라면, 사용자가 원하는 퀴즈 타입(OX, choice, short)과 개수(n)도 추출해라.\n\n"
        "규칙:\n"
        "1. 타입: 'OX퀴즈'->OX, '객관식/4지선다'->choice, '단답형/주관식'->short. 언급 없으면 null.\n"
        "2. 개수: 언급 없으면 1 (기본값).\n"
        "3. 정답 제출일 경우: '정답은 O야', '1번', '금리' 등 답을 말하는 패턴이면 ANSWER로 분류.\n\n"
        "출력 JSON 예시:\n"
        "- \"OX 퀴즈 하나 내줘\": {\"action\": \"REQUEST\", \"type\": \"OX\", \"count\": 1}\n"
        "- \"객관식으로 3개\": {\"action\": \"REQUEST\", \"type\": \"choice\", \"count\": 3}\n"
        "- \"정답은 O\": {\"action\": \"ANSWER\", \"user_answer\": \"O\"}\n"
        "- \"1번이야\": {\"action\": \"ANSWER\", \"user_answer\": \"1\"}\n"
        "- \"모르겠어\": {\"action\": \"GIVEUP\"}"
    )

    try:
        res = llm.invoke([("system", sys_msg), ("user", text)])
        raw = res.content.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw: raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw)
    except Exception as e:
        dprint(f"Intent analysis failed: {e}")
        return {"action": "REQUEST", "type": None, "count": 1}


# ============================================================
# 2. [Generator] 퀴즈 생성
# ============================================================
def build_quiz_prompt(level: str, q_type: str = None) -> ChatPromptTemplate:
    # 1) 레벨 및 요청 타입에 따른 설정
    level_config = {
        "씨앗": {"type": "OX", "desc": "아주 쉬운 OX 퀴즈"},
        "새싹": {"type": "choice", "desc": "기초 내용을 묻는 4지 선다형"},
        "나무": {"type": "choice", "desc": "세부 내용을 묻는 4지 선다형"},
        "숲":   {"type": "short", "desc": "핵심 단어를 묻는 단답형(주관식)"}
    }
    
    target_type = q_type if q_type else level_config.get(level, level_config["새싹"])["type"]
    desc = level_config.get(level, level_config["새싹"])["desc"]
    
    if q_type:
        desc = f"사용자가 요청한 {q_type} 형식의 문제"

    # 2) 프롬프트 생성
    # ✅ [핵심 수정] .format() 호출을 제거하고, f-string과 일반 문자열 결합으로 해결합니다.
    # - f-string 부분: {desc}, {target_type} 변수가 바로 들어감
    # - 일반 문자열 부분: {{ }}가 그대로 유지되어 LangChain에 전달됨 (LangChain이 이를 JSON 중괄호로 인식)
    
    system_tmpl = (
        "당신은 경제 뉴스 퀴즈 출제자입니다. 제공된 [뉴스 요약]과 [용어 설명]을 바탕으로 "
        "사용자가 내용을 이해했는지 확인하는 퀴즈를 만들어주세요.\n"
        f"요구사항: {desc}\n"
        f"형식: {target_type} (OX / choice / short)\n\n"
        "반드시 JSON 포맷으로 응답:\n"
        "{{\n"
        "  \"quizzes\": [\n"
        "    {{\n"
        f"      \"type\": \"{target_type}\",\n"  # 여기가 f-string이므로 target_type이 주입됨
        "      \"question\": \"문제 지문\",\n"
        "      \"options\": [\"보기1\", \"보기2\", \"보기3\", \"보기4\"] (단답형이면 빈 리스트 [], OX면 [\"O\", \"X\"]),\n"
        "      \"answer\": \"정답 (보기 중 하나, 단답형이면 단어)\",\n"
        "      \"explanation\": \"정답 해설 (왜 정답인지, 오답은 왜 아닌지)\"\n"
        "    }}\n"
        "  ]\n"
        "}}\n"
        "제약:\n"
        "1. 단답형 정답은 본문에 있는 명사 단어 위주로 하세요.\n"
        "2. 한국어로 자연스럽게 작성하세요."
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_tmpl), # .format() 제거함!
        ("human", "뉴스 요약: {summary}\n용어 설명: {terms}")
    ])

def generate_quiz(summary_item: Dict, level: str, q_type: str = None, count: int = 1) -> List[Dict]:
    summary_text = summary_item.get("summary_5sentences", "")
    explanations = summary_item.get("explanations", [])
    terms_text = "\n".join([f"- {e['term']}: {e['definition']}" for e in explanations])
    
    title = summary_item.get("title", "")
    dprint(f"Generatng {count} quizzes ({q_type or 'Auto'}) for: {title}")

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, model_kwargs={"response_format": {"type": "json_object"}})
    prompt = build_quiz_prompt(level, q_type)
    chain = prompt | model | JsonOutputParser()
    
    try:
        # invoke
        res = chain.invoke({"summary": summary_text, "terms": terms_text})
        
        quizzes = res.get("quizzes", [])
        return quizzes[:count]
    except Exception as e:
        dprint(f"Quiz gen error: {e}")
        return []


# ============================================================
# 3. 메인 핸들러
# ============================================================
def handle(text: str, profile: Optional[Dict[str, Any]] = None, state: Optional[Dict[str, Any]] = None) -> AIMessage:
    dprint("[handle] ENTER quiz_node")

    ctx = (state or {}).get("context", {})
    profile = profile or (state or {}).get("profile", {}) or {}
    level = profile.get("level", "새싹")
    
    intent_data = analyze_user_intent(text)
    action = intent_data.get("action")
    dprint(f"User Action: {action}, Data: {intent_data}")

    # --- CASE A: 정답 채점 ---
    if action == "ANSWER" or action == "GIVEUP":
        active_quiz = ctx.get("active_quiz")
        if not active_quiz:
            return AIMessage(content="[quiz] 채점할 문제가 없어요. 먼저 퀴즈를 요청해 주세요.")
        
        user_ans = intent_data.get("user_answer", "").strip()
        correct_ans = active_quiz.get("answer", "").strip()
        explanation = active_quiz.get("explanation", "")
        
        is_correct = False
        if action == "GIVEUP":
            msg = f"[quiz] 정답은 **{correct_ans}** 입니다.\n\n💡 해설: {explanation}"
            ctx["active_quiz"] = None
            return AIMessage(content=msg)
            
        if active_quiz["type"] == "OX":
            if user_ans.upper() in ["O", "0", "YES", "TRUE"] and correct_ans.upper() == "O": is_correct = True
            elif user_ans.upper() in ["X", "NO", "FALSE"] and correct_ans.upper() == "X": is_correct = True
        elif active_quiz["type"] == "choice":
            if user_ans in correct_ans or correct_ans in user_ans: is_correct = True
        else:
            if user_ans.replace(" ","") == correct_ans.replace(" ",""): is_correct = True
        
        if is_correct:
            ctx["active_quiz"] = None
            return AIMessage(content=f"🎉 **정답입니다!**\n\n💡 해설: {explanation}")
        else:
            ctx["active_quiz"] = None
            return AIMessage(content=f"땡! 아쉽네요. 😅\n정답은 **{correct_ans}** 입니다.\n\n💡 해설: {explanation}")


    # --- CASE B: 퀴즈 출제 ---
    summaries = ctx.get("summaries", [])
    if not summaries:
        return AIMessage(content="[quiz] 퀴즈를 만들 기사가 없어요. 뉴스 검색과 요약을 먼저 해주세요.")

    req_type = intent_data.get("type")
    req_count = intent_data.get("count", 1)
    # 가장 최근 기사 사용
    target_article = summaries[-1]
    
    quizzes = generate_quiz(target_article, level, q_type=req_type, count=req_count)
    
    if not quizzes:
        return AIMessage(content="[quiz] 문제를 생성하지 못했어요.")

    first_q = quizzes[0]
    ctx["active_quiz"] = first_q
    
    q_type_lbl = {"OX": "OX 퀴즈", "choice": "객관식", "short": "단답형"}.get(first_q['type'], "퀴즈")
    
    msg = [f"[quiz] 방금 읽은 기사로 **{q_type_lbl}**를 냈어요! ({level} 단계)\n"]
    msg.append(f"Q. {first_q['question']}\n")
    
    if first_q['type'] == "choice":
        for i, opt in enumerate(first_q['options'], 1):
            msg.append(f"   {i}) {opt}")
    elif first_q['type'] == "OX":
         msg.append("   (O / X)")
    
    msg.append("\n정답을 입력해 주세요! 👇")
    
    return AIMessage(content="\n".join(msg))