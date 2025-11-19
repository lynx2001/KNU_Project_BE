# graph_app.py
from __future__ import annotations
from typing import Annotated, List, Optional, TypedDict, Any, Dict
try:
    from .common import * 
    from .supervisor_router import classify_intent
    from .agents import qa, news_find, news_summary, term_explain, quiz
except ImportError:
    # 혹시라도 단독 실행할 경우를 대비한 예외처리
    from common import *
    from supervisor_router import classify_intent
    from agents import qa, news_find, news_summary, term_explain, quiz

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage


# ---------- 유틸 ----------
def _ensure_ai(res) -> AIMessage:
    return res if isinstance(res, AIMessage) else AIMessage(content=str(res))

def _extract_user_message(state: "GraphState") -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

def _get_profile(state: "GraphState") -> Dict[str, Any]:
    if isinstance(state.get("profile"), dict):
        return state["profile"]
    ctx = state.get("context") or {}
    prof = ctx.get("profile")
    return prof if isinstance(prof, dict) else {}

def _safe_handle(agent_mod, user_text: str, profile: Dict[str, Any], state: Dict[str, Any]):
    try:
        return agent_mod.handle(user_text, profile=profile, state=state)
    except TypeError:
        return agent_mod.handle(user_text)


# ---------- 그래프 상태 ----------
class GraphState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    plan: List[str]
    completed: List[str]
    cursor: int
    last_agent: Optional[str]
    loop_count: int
    current_intent: Optional[str]
    context: Dict[str, Any]
    profile: Dict[str, Any]


# ---------- Supervisor Node (수정됨) ----------
def supervisor_node(state: GraphState) -> dict:
    print("[DBG supervisor] ENTER")
    msgs = state.get("messages", [])
    
    # 1. 사용자 입력 텍스트 추출
    user = next((m for m in reversed(msgs) if isinstance(m, HumanMessage)), None)
    user_text = user.content if user else ""
    print("[DBG supervisor] user_text =", repr(user_text))

    # 2. 기존 상태 가져오기
    plan = state.get("plan", [])
    cursor = state.get("cursor", 0)

    profile = _get_profile(state)

    # 3. 새로운 턴 감지
    last_msg = msgs[-1] if msgs else None
    is_new_turn = isinstance(last_msg, HumanMessage)

    if not plan or is_new_turn:
        print(f"[DBG supervisor] Re-planning (Reason: {'No plan' if not plan else 'New input'})")
        
        # ✅ [핵심 수정] context를 함께 넘겨줍니다!
        ctx = state.get("context", {})
        plan = classify_intent(user_text, context=ctx) 
        
        if not plan:
            plan = ["qa"]
        cursor = 0 

    print("[DBG supervisor] plan =", plan, "cursor =", cursor)

    next_intent = plan[cursor] if cursor < len(plan) else "end"
    print("[DBG supervisor] next_intent =", next_intent)

    out = {
        "plan": plan,
        "cursor": cursor,
        "last_agent": next_intent if next_intent != "end" else None,
        "loop_count": state.get("loop_count", 0) + 1,
        "current_intent": next_intent,
        "profile": profile,
    }
    print("[DBG supervisor] RETURN keys:", list(out.keys()))
    return out


# ---------- Agent Nodes (기존 유지) ----------
def qa_node(state: GraphState) -> dict:
    print("\n[DBG node] ENTER qa_node")
    print("[DBG node] plan:", state.get("plan"), "cursor:", state.get("cursor"))

    user_text = _extract_user_message(state)
    profile = _get_profile(state)

    print("[DBG node] user_text =", repr(user_text))
    res = _safe_handle(qa, user_text, profile=profile, state=state)
    print("[DBG node] qa.handle() returned:", type(res), "-", repr(res))

    plan = state.get("plan", [])
    cursor = min(state.get("cursor", 0) + 1, len(plan))
    completed = list(set(state.get("completed", []) + ["qa"]))

    ctx = dict(state.get("context", {}))

    out = {
        "messages": [_ensure_ai(res)],
        "completed": completed,
        "cursor": cursor,
        "last_agent": "qa",
        "current_intent": None,
        "context": ctx,
        "profile": profile,
    }
    return out


def news_find_node(state: GraphState) -> dict:
    print("\n[DBG node] ENTER news_find_node")
    print("[DBG node] plan:", state.get("plan"), "cursor:", state.get("cursor"))

    user_text = _extract_user_message(state)
    profile = _get_profile(state)

    print("[DBG node] user_text =", repr(user_text))
    res = _safe_handle(news_find, user_text, profile=profile, state=state)
    print("[DBG node] news_find.handle() returned:", type(res), "-", repr(res))

    plan = state.get("plan", [])
    cursor = min(state.get("cursor", 0) + 1, len(plan))
    completed = list(set(state.get("completed", []) + ["news_find"]))

    ctx = dict(state.get("context", {}))

    out = {
        "messages": [_ensure_ai(res)],
        "completed": completed,
        "cursor": cursor,
        "last_agent": "news_find",
        "current_intent": None,
        "context": ctx,
        "profile": profile,
    }
    return out


def news_summary_node(state: GraphState) -> dict:
    print("\n[DBG node] ENTER news_summary_node")
    print("[DBG node] plan:", state.get("plan"), "cursor:", state.get("cursor"))

    user_text = _extract_user_message(state)
    profile = _get_profile(state)

    print("[DBG node] user_text =", repr(user_text))
    res = _safe_handle(news_summary, user_text, profile=profile, state=state)
    print("[DBG node] news_summary.handle() returned:", type(res), "-", repr(res))

    plan = state.get("plan", [])
    cursor = min(state.get("cursor", 0) + 1, len(plan))
    completed = list(set(state.get("completed", []) + ["news_summary"]))

    ctx = dict(state.get("context", {}))

    out = {
        "messages": [_ensure_ai(res)],
        "completed": completed,
        "cursor": cursor,
        "last_agent": "news_summary",
        "current_intent": None,
        "context": ctx,
        "profile": profile,
    }
    return out


def term_explain_node(state: GraphState) -> dict:
    print("\n[DBG node] ENTER term_explain_node")
    print("[DBG node] plan:", state.get("plan"), "cursor:", state.get("cursor"))

    user_text = _extract_user_message(state)
    profile = _get_profile(state)

    print("[DBG node] user_text =", repr(user_text))
    res = _safe_handle(term_explain, user_text, profile=profile, state=state)
    print("[DBG node] term_explain.handle() returned:", type(res), "-", repr(res))

    plan = state.get("plan", [])
    cursor = min(state.get("cursor", 0) + 1, len(plan))
    completed = list(set(state.get("completed", []) + ["term_explain"]))

    ctx = dict(state.get("context", {}))

    out = {
        "messages": [_ensure_ai(res)],
        "completed": completed,
        "cursor": cursor,
        "last_agent": "term_explain",
        "current_intent": None,
        "context": ctx,
        "profile": profile,
    }
    return out


def quiz_node(state: GraphState) -> dict:
    print("\n[DBG node] ENTER quiz_node")
    print("[DBG node] plan:", state.get("plan"), "cursor:", state.get("cursor"))

    user_text = _extract_user_message(state)
    profile = _get_profile(state)

    print("[DBG node] user_text =", repr(user_text))
    res = _safe_handle(quiz, user_text, profile=profile, state=state)
    print("[DBG node] quiz.handle() returned:", type(res), "-", repr(res))

    plan = state.get("plan", [])
    cursor = min(state.get("cursor", 0) + 1, len(plan))
    completed = list(set(state.get("completed", []) + ["quiz"]))

    ctx = dict(state.get("context", {}))

    out = {
        "messages": [_ensure_ai(res)],
        "completed": completed,
        "cursor": cursor,
        "last_agent": "quiz",
        "current_intent": None,
        "context": ctx,
        "profile": profile,
    }
    return out


# ---------- 라우팅 ----------
def route_from_supervisor(state: GraphState) -> str:
    intent = state.get("current_intent", "end")
    allowed = {"qa", "news_find", "news_summary", "term_explain", "quiz"}
    dest = intent if intent in allowed else "end"
    print(f"[DBG route] current_intent={intent} -> dest={dest}")
    return dest

def route_after_agent(_: GraphState) -> str:
    return "supervisor"


# ---------- 그래프 빌드 ----------
def build_app():
    g = StateGraph(GraphState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("qa", qa_node)
    g.add_node("news_find", news_find_node)
    g.add_node("news_summary", news_summary_node)
    g.add_node("term_explain", term_explain_node)
    g.add_node("quiz", quiz_node)

    g.add_edge(START, "supervisor")

    g.add_conditional_edges("supervisor", route_from_supervisor, {
        "qa": "qa",
        "news_find": "news_find",
        "news_summary": "news_summary",
        "term_explain": "term_explain",
        "quiz": "quiz",
        "end": END,
    })

    for node in ["qa", "news_find", "news_summary", "term_explain", "quiz"]:
        g.add_conditional_edges(node, lambda s: "supervisor", {"supervisor": "supervisor"})

    return g.compile()


APP = build_app()