"""
term_explain.py — 용어 설명 에이전트 (Context-aware & General Definitions)
"""
from typing import List, Dict, Any, Optional
import json, time

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
        print("[DBG term_explain]", *args, **kwargs)

# ============================================================
# 1. [Helper] 사용자 입력에서 '궁금한 용어' 추출하기
# ============================================================
def extract_user_target_term(user_text: str) -> Optional[str]:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    sys_msg = (
        "너는 사용자 질문에서 '설명 대상이 되는 핵심 단어(용어)'를 추출하는 분석기다.\n"
        "사용자가 특정 단어의 뜻, 정의, 개념을 물어보면 그 단어만 딱 잘라서 추출해라.\n\n"
        "예시:\n"
        "- '금리가 뭐야?' -> \"금리\"\n"
        "- '인플레이션 뜻 알려줘' -> \"인플레이션\"\n"
        "- '공매도 설명 좀' -> \"공매도\"\n"
        "- '방금 기사 용어 설명해줘' -> null (대상이 불명확)\n"
        "- '어려운 단어 뜻 풀이해줘' -> null\n\n"
        "반드시 JSON 포맷으로 답할 것: {\"term\": \"추출한단어\"} 또는 {\"term\": null}"
    )
    
    try:
        res = llm.invoke([
            ("system", sys_msg),
            ("user", user_text)
        ])
        text = res.content.strip()
        if "```json" in text: text = text.split("```json")[1].split("```")[0]
        elif "```" in text: text = text.split("```")[1].split("```")[0]
            
        data = json.loads(text)
        term = data.get("term")
        dprint(f"Extraction Raw: {text} -> Parsed: {term}")
        return term
    except Exception as e:
        dprint(f"Term extraction failed: {e}")
        return None


# ============================================================
# 2. [Mode A] 문맥 기반 설명 (Context-aware)
# ============================================================
def build_contextual_prompt(level: str) -> ChatPromptTemplate:
    style_guide = {
        "씨앗": "유치원생도 이해할 수 있는 아주 쉬운 비유를 들어 설명해줘.",
        "새싹": "초등학생이 이해할 수 있게 쉬운 말로 풀어서 설명해줘.",
        "나무": "경제학 기초 지식이 있는 대학생에게 설명하듯 명확하게 정의해줘.",
        "숲": "전문적인 경제 용어를 사용하여 깊이 있게 설명해줘."
    }.get(level, "초보자가 이해하기 쉽게 설명해줘.")

    # JSON 중괄호 Escape ({{ }})
    system_tmpl = (
        "당신은 친절한 경제 선생님입니다. 주어진 뉴스 요약문과 그 안에 포함된 '용어 목록'을 보고, "
        "각 용어가 **이 뉴스 맥락에서 어떤 의미로 쓰였는지** 설명해주세요.\n"
        f"설명 난이도: {style_guide}\n\n"
        "반드시 JSON 형식으로만 응답하세요. 스키마:\n"
        "{{\n"
        "  \"explanations\": [\n"
        "    {{\"term\": \"용어1\", \"definition\": \"설명 내용...\"}},\n"
        "    {{\"term\": \"용어2\", \"definition\": \"설명 내용...\"}}\n"
        "  ]\n"
        "}}\n"
        "제약사항:\n"
        "1. 설명은 1~2문장으로 간결하게 작성하세요.\n"
        "2. 뉴스 요약문의 내용을 참고하여 구체적으로 설명하세요."
    )

    return ChatPromptTemplate.from_messages([
        ("system", system_tmpl),
        ("human", "뉴스 요약: {summary}\n설명할 용어들: {terms}")
    ])

def explain_contextual(summary_text: str, terms: List[str], level: str) -> List[Dict]:
    """기사 문맥을 반영하여 설명"""
    if not terms: return []
    
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, model_kwargs={"response_format": {"type": "json_object"}})
    prompt = build_contextual_prompt(level)
    chain = prompt | model | JsonOutputParser()

    try:
        res = chain.invoke({"summary": summary_text, "terms": ", ".join(terms)})
        return res.get("explanations", [])
    except Exception as e:
        dprint(f"Contextual explain error: {e}")
        return []


# ============================================================
# 3. [Mode B] 일반 정의 설명 (General Knowledge)
# ============================================================
def explain_general(term: str, level: str) -> Dict:
    style_guide = {
        "씨앗": "아주 쉬운 비유(예: 용돈, 장난감)를 들어 유치원생에게 설명하듯 해줘.",
        "새싹": "초등학생도 이해할 수 있는 쉬운 단어로 설명해줘.",
        "나무": "대학생 수준으로 정확한 경제적 정의와 예시를 들어줘.",
        "숲": "전문가 수준의 깊이 있는 정의와 경제적 함의를 설명해줘."
    }.get(level, "쉽게 설명해줘.")

    system_tmpl = (
        "당신은 경제 용어 사전입니다. 사용자가 묻는 용어에 대해 "
        "뉴스 문맥 없이도 이해할 수 있는 **일반적인 정의**를 내려주세요.\n"
        f"난이도: {style_guide}\n\n"
        "반드시 JSON 형식으로 응답:\n"
        "{{\n"
        "  \"term\": \"{term}\",\n"
        "  \"definition\": \"설명내용(1~2문장)\"\n"
        "}}"
    )
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
    
    try:
        msg = system_tmpl.format(term=term)
        res = llm.invoke([("system", msg), ("human", "설명해줘")])
        return json.loads(res.content)
    except Exception as e:
        dprint(f"General explain error: {e}")
        return {"term": term, "definition": "죄송해요, 용어 설명을 생성하는 중 오류가 발생했어요."}


# ============================================================
# 4. 메인 핸들러 (Chatbot)
# ============================================================
def handle(text: str, profile: Optional[Dict[str, Any]] = None, state: Optional[Dict[str, Any]] = None) -> AIMessage:
    dprint("[handle] ENTER term_explain_node")

    ctx = (state or {}).get("context", {})
    profile = profile or (state or {}).get("profile", {}) or {}
    level = profile.get("level", "새싹")
    
    target_term = extract_user_target_term(text)
    dprint(f"User Target Term: {target_term}")

    summaries = ctx.get("summaries", [])

    # CASE 1: 특정 용어 질문
    if target_term:
        related_summary = None
        for s in summaries:
            content_blob = (s.get("title","") + s.get("summary_5sentences","") + " ".join(s.get("term_candidates",[])))
            if target_term in content_blob:
                related_summary = s
                break
        
        if related_summary:
            dprint(" -> Term found in context! Using Contextual Explanation.")
            explanations = explain_contextual(
                related_summary.get("summary_5sentences", ""), 
                [target_term], 
                level
            )
            if explanations:
                defi = explanations[0].get("definition", "")
                msg = (f"[term_explain] 이 용어는 방금 본 뉴스에 나오는 말이에요.\n\n"
                       f"📖 **{target_term}** (문맥 정의)\n{defi}\n\n"
                       f"(관련 기사: {related_summary.get('title')})")
                return AIMessage(content=msg)
        
        dprint(" -> Term NOT found in context. Using General Explanation.")
        res = explain_general(target_term, level)
        defi = res.get("definition", "")
        msg = (f"[term_explain] 뉴스에는 없지만, '{level}' 수준으로 설명해 드릴게요.\n\n"
               f"💡 **{target_term}** (일반 정의)\n{defi}")
        return AIMessage(content=msg)


    # CASE 2: 전체 설명 요청 (배치 함수 재사용 가능하지만, 여기선 직접 호출)
    dprint(" -> General request. Explaining all candidates in summaries.")
    if not summaries:
        return AIMessage(content="[term_explain] 설명할 요약문이 없습니다. 뉴스 요약을 먼저 진행해주세요.")

    # 아래 배치 함수와 로직 동일
    all_explanations = build_daily_term_explanations({"context": ctx}, profile)
    
    # 컨텍스트 저장은 배치 함수 내부에서 summaries를 수정하므로 이미 반영됨
    # 하지만 명시적으로 ctx 업데이트
    ctx["term_explanations"] = all_explanations

    msg_lines = [f"[term_explain] '{level}' 수준에 맞춰 주요 용어를 풀이했습니다.\n"]
    for group in all_explanations:
        msg_lines.append(f"🔹 기사: {group['title']}")
        for d in group["definitions"]:
            msg_lines.append(f"   • **{d['term']}**: {d['definition']}")
        msg_lines.append("")
    
    return AIMessage(content="\n".join(msg_lines))


# ============================================================
# 5. [Batch] 데일리 파이프라인용 함수
# ============================================================
def build_daily_term_explanations(state: Dict[str, Any], profile: Dict) -> List[Dict]:
    """
    매일 아침 실행되는 배치 작업용 함수.
    state['context']['summaries']의 모든 기사에 대해
    포함된 용어(term_candidates)를 모두 설명하여 저장함.
    """
    ctx = state.get("context", {})
    summaries = ctx.get("summaries", [])
    level = profile.get("level", "새싹")
    
    all_explanations = []
    
    dprint(f"[Batch] Building term explanations for {len(summaries)} articles...")
    
    for item in summaries:
        candidates = item.get("term_candidates", [])
        if not candidates:
            continue
            
        # 기사 문맥 반영 설명 생성
        defs = explain_contextual(item.get("summary_5sentences", ""), candidates, level)
        
        # 결과 저장 (기사 객체 내부)
        item["explanations"] = defs 
        
        if defs:
            all_explanations.append({
                "title": item.get("title", ""),
                "definitions": defs
            })
            
    return all_explanations