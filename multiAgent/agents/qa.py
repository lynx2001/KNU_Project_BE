"""
qa_agent.py — LLM 기반 라우팅 + Smalltalk / Internal RAG / WebSearch 3-모드 QA Agent
그래프 노드에서 바로 호출 가능한 버전.
"""

from __future__ import annotations
import os, re
from typing import Optional, Dict, Any, List, Tuple, Literal
from dataclasses import dataclass
from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import AIMessage
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

load_dotenv()

# ============================================================
# 🔧 디버그 스위치
# ============================================================
DEBUG = True
def dprint(*args, **kwargs):
    if DEBUG:
        print("[DBG qa]", *args, **kwargs)


# ============================================================
# 📘 내부 요약 기반 RAG 유틸
# ============================================================
ORDINAL_PAT = re.compile(r"(첫 ?번째|두 ?번째|세 ?번째|1 ?번|2 ?번|3 ?번)")
SUMMARY_HINT_PAT = re.compile(r"(요약|오늘|정리|핵심)", re.IGNORECASE)

def _resolve_ordinal_korean(text: str) -> Optional[int]:
    t = text.replace(" ", "")
    if "첫번째" in t or "1번" in t: return 0
    if "두번째" in t or "2번" in t: return 1
    if "세번째" in t or "3번" in t: return 2
    return None

def _collect_internal_corpus(state: Dict[str, Any]) -> List[Tuple[str, str]]:
    corpus: List[Tuple[str, str]] = []
    ctx = state.get("context", {})
    sums = ctx.get("summaries") or []
    arts = ctx.get("selected_articles") or []

    for i, s in enumerate(sums):
        body = ""
        if s.get("tl_dr"): body += s["tl_dr"] + "\n"
        if s.get("bullets"):
            body += "\n".join(f"- {b}" for b in s["bullets"])
        if body.strip():
            corpus.append((f"summary:{i}", body))
    for i, a in enumerate(arts):
        content = (a.get("content") or "").strip()
        if content:
            corpus.append((f"article:{i}", content[:4000]))
    return corpus

def _build_ephemeral_store(corpus: List[Tuple[str, str]]) -> Optional[FAISS]:
    if not corpus:
        return None
    docs = [Document(page_content=txt, metadata={"doc_id": did}) for did, txt in corpus]
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    splits = splitter.split_documents(docs)
    vs = FAISS.from_documents(splits, OpenAIEmbeddings())
    return vs

def _internal_rag_answer(
    question: str,
    state: Dict[str, Any],
    level: str = "beginner",
    top_k: int = 4,
    force_pick: Optional[int] = None
) -> Optional[AIMessage]:
    corpus = _collect_internal_corpus(state)
    if not corpus:
        dprint("internal RAG: no corpus → fallback")
        return None

    selected_texts: List[str] = []
    if force_pick is not None:
        for did, txt in corpus:
            if did == f"summary:{force_pick}" or did == f"article:{force_pick}":
                selected_texts.append(txt)
        if not selected_texts:
            dprint("internal RAG: forced pick not found → search all")

    if not selected_texts:
        vs = _build_ephemeral_store(corpus)
        if vs:
            hits = vs.similarity_search(question, k=top_k)
            selected_texts = [h.page_content for h in hits]
        else:
            selected_texts = []

    ctx_text = "\n\n---\n\n".join(selected_texts[:3]) if selected_texts else "(관련 내부 요약을 찾지 못했습니다.)"
    sys = (
        "너는 사용자가 오늘 학습한 요약/기사 내용을 근거로 설명하는 튜터야. "
        "반드시 제공된 컨텍스트 내에서만 답하고, 문맥에 없는 내용은 추측하지 말아라. "
        f"사용자 수준(level={level})에 맞춰 간단히 설명하고, 필요하면 한 줄 예시를 들어라."
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    res = llm.invoke([
        {"role": "system", "content": sys},
        {"role": "user", "content": f"질문: {question}\n\n[내부 컨텍스트]\n{ctx_text}"},
    ])
    return AIMessage(content=res.content)


# ============================================================
# 💬 SMALLTALK
# ============================================================
_SMALLTALK_PAT = re.compile(r"^\s*(안녕|하이|헬로|hello|반가워|고마워|감사|잘\s*지내|ㅎㅇ)\b", re.IGNORECASE)
def qa_smalltalk(user_text: str) -> AIMessage:
    dprint("mode=SMALLTALK")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    res = llm.invoke([
        {"role": "system", "content": "너는 공손하고 간결하게 대화하는 어시스턴트다."},
        {"role": "user", "content": user_text},
    ])
    return AIMessage(content=res.content)


# ============================================================
# 🌐 Tavily Search (공식 > 커뮤니티 폴백)
# ============================================================
def _tavily_results(query: str, k: int = 1) -> List[Dict[str, Any]]:
    """Tavily community tool만 사용 (결과 기본 1개)."""
    dprint("WEB.search (community only):", query, "k=", k)
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tool = TavilySearchResults(max_results=k)
        results = tool.invoke({"query": query})
        dprint("tavily community ok; n_results=", len(results) if isinstance(results, list) else "n/a")
        return results if isinstance(results, list) else []
    except Exception as e:
        dprint("tavily community failed:", repr(e))
        return []

def qa_web_summarize(query: str, results: List[Dict[str, Any]], level: str = "beginner") -> AIMessage:
    dprint("mode=WEB.summarize: n_results=", len(results))
    top = results[:1]  # ← 여기!
    refs_text = "\n".join(
        f"- {r.get('title','(제목없음)')} {r.get('url','')}"
        for r in top if isinstance(r, dict)
    ) or "(검색 결과가 없습니다)"
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    sys = (
        "너는 뉴스/웹 검색 결과를 사용자 질의에 맞춰 핵심만 정리하는 어시스턴트다. "
        f"사용자 수준(level={level})에 맞춰 간결하게 요약하고, 가능한 경우 참고링크도 함께 제공해."
    )
    res = llm.invoke([
        {"role": "system", "content": sys},
        {"role": "user", "content": f"사용자 질문: {query}\n\n검색 결과(상위 3개):\n{refs_text}"},
    ])
    return AIMessage(content=res.content)


# ============================================================
# 🤖 LLM 기반 라우팅
# ============================================================
class QARouteDecision(BaseModel):
    mode: Literal["smalltalk", "internal", "web"]
    forced_index: Optional[int] = None
    reason: Optional[str] = None

_QA_ROUTE_SYSTEM = (
    "너는 QA 서브에이전트의 라우터야. 아래 세 모드 중 하나를 고른다.\n"
    " - smalltalk: 인사/잡담/감사 등 도구 불필요한 일상 대화.\n"
    " - internal: 사용자가 오늘 학습한 요약/기사에 기대어 답해야 할 때. "
    "   '요약', '오늘', '첫번째/두번째/세번째/1번/2번/3번' 같은 표현이 있고, "
    "   내부 요약(summaries)이 실제로 존재할 때 internal을 선택한다.\n"
    " - web: 그 밖의 모든 정보 탐색/사실 확인(외부 검색 필요) 상황.\n\n"
    "규칙:\n"
    "1) 인사/잡담이면 smalltalk.\n"
    "2) 내부 요약을 참조한 질문 + 내부 요약이 state에 존재하면 internal.\n"
    "3) 그 외는 web.\n"
    "4) 사용자가 '두번째/3번' 등을 말하면 forced_index를 0부터 시작해 지정(두번째=1, 3번=2). 못찾으면 null.\n"
    "반드시 JSON으로만 답하라."
)

def qa_llm_route(user_text: str, has_summaries: bool) -> QARouteDecision:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(QARouteDecision)
    sys = _QA_ROUTE_SYSTEM + f"\n\n[컨텍스트] has_summaries={has_summaries}"
    out = llm.invoke([
        {"role": "system", "content": sys},
        {"role": "user", "content": user_text or ""},
    ])
    dprint("llm-route:", out.model_dump())
    return out


# ============================================================
# 🧩 Main Entrypoint (그래프 호출용)
# ============================================================
def handle(user_text: str, profile: Optional[Dict[str, Any]] = None, state: Optional[Dict[str, Any]] = None) -> AIMessage:
    """
    - smalltalk → LLM
    - internal → 내부 summaries/articles 기반 RAG로 답변
    - web → Tavily 검색 → 요약
    """
    try:
        ctx = (state or {}).get("context", {})
        has_summaries = bool(ctx.get("summaries"))
        decision = qa_llm_route(user_text, has_summaries)
        mode = decision.mode
        forced = decision.forced_index
        dprint(f"route decided: mode={mode}, forced_index={forced}, reason={decision.reason}")

        if mode == "smalltalk":
            return qa_smalltalk(user_text)

        if mode == "internal":
            level = (profile or {}).get("level", "beginner")
            ans = _internal_rag_answer(user_text, state or {}, level=level, force_pick=forced)
            if ans is not None:
                return ans
            dprint("internal RAG unavailable → fallback to WEB")

        # WEB (default)
        results = _tavily_results(user_text, k=1)
        level = (profile or {}).get("level", "beginner")
        return qa_web_summarize(user_text, results, level=level)

    except Exception as e:
        dprint("handle() error:", repr(e))
        return AIMessage(content=f"[qa/error] 문제가 발생했어요: {e!r}")