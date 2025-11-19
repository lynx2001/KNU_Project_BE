"""
news_find.py — 뉴스 수집/검색 에이전트
"""

from __future__ import annotations

import os
import re
import time
import requests
import feedparser
import bs4
from typing import List, Dict, Any, Optional

from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# 설정
# ------------------------------------------------------------------------------
DEBUG = True

ONDEMAND_PER_FEED_LIMIT = 50
ONDEMAND_DAYS_BACK = 5

PER_FEED_LIMIT = 5
FEEDS = [
    "https://www.hankyung.com/feed/economy",        # 한국경제
    "https://www.yna.co.kr/rss/economy.xml",        # 연합뉴스 (JTBC 대체)
    "https://www.mk.co.kr/rss/30100041/",           # 매일경제
]

UA_HEADERS = {"User-Agent": os.getenv("USER_AGENT", "NewsTutorAgent/1.0")}

# 매체별 기본 SoupStrainer (빠른 경로)
DOMAIN_PARSE_ONLY = {
    "www.hankyung.com": ("div", {"id": "articletxt"}),
    "www.yna.co.kr": ("div", {"class": "story-news article"}),
    "www.mk.co.kr": ("p", {"refid": True}),
}

# DB API(옵션)
NEWS_DB_API_BASE = os.getenv("NEWS_DB_API_BASE", "").rstrip("/")
NEWS_DB_SEARCH_PATH = os.getenv("NEWS_DB_SEARCH_PATH", "/api/search").strip()

# ------------------------------------------------------------------------------
# 데이터 모델
# ------------------------------------------------------------------------------
class NewsDoc:
    def __init__(self, title: str, url: str, published_at: int = 0,
                 source: str = "", summary: str = "", content: str = ""):
        self.title = title
        self.url = url
        self.published_at = published_at
        self.source = source
        self.summary = summary
        self.content = content

# ------------------------------------------------------------------------------
# 유틸
# ------------------------------------------------------------------------------
def _domain_of(url: str) -> str:
    return url.split("/")[2] if "://" in url else url

def _norm(text: str) -> str:
    return " ".join((text or "").split())

def _parse_time(entry) -> int:
    try:
        if getattr(entry, "published_parsed", None):
            return int(time.mktime(entry.published_parsed))
    except Exception:
        pass
    return 0

def _dedup_by_title(docs: List[NewsDoc]) -> List[NewsDoc]:
    seen, out = set(), []
    for d in docs:
        if d.title not in seen:
            seen.add(d.title)
            out.append(d)
    return out

def _keyword_matches_any(title: str, summary: str, content: str, keyword: Optional[str]) -> bool:
    if not keyword:
        return True
    kw = keyword.lower()
    return kw in (title or "").lower() or kw in (summary or "").lower() or kw in (content or "").lower()

def _score_by_keyword(title: str, summary: str, keyword: str) -> int:
    if not keyword:
        return 0
    t = (title or "").lower()
    s = (summary or "").lower()
    kw = keyword.lower()
    score = 0
    if kw in t: score += 3
    if kw in s: score += 1
    return score

# ------------------------------------------------------------------------------
# DB API
# ------------------------------------------------------------------------------
def search_db_api_by_keyword(keyword: str, limit: int = 6) -> list[NewsDoc]:
    out: list[NewsDoc] = []
    if not NEWS_DB_API_BASE:
        if DEBUG: print("[DBG db] skip: NEWS_DB_API_BASE not set")
        return out
    try:
        url = f"{NEWS_DB_API_BASE}{NEWS_DB_SEARCH_PATH}"
        resp = requests.get(url, params={"q": keyword, "limit": limit}, timeout=5)
        resp.raise_for_status()
        data = resp.json() or []
        for it in data:
            title = _norm(it.get("title", ""))
            link  = _norm(it.get("url", ""))
            if not title or not link: continue
            out.append(
                NewsDoc(
                    title=title,
                    url=link,
                    published_at=int(it.get("published_at") or 0),
                    source=_norm(it.get("source", "")),
                    summary=_norm(it.get("summary", "")),
                    content="",
                )
            )
        if DEBUG: print(f"[DBG db] results={len(out)} for '{keyword}'")
        return out
    except Exception as e:
        if DEBUG: print("[DBG db] error:", repr(e))
        return out

# ------------------------------------------------------------------------------
# RSS 메타 수집
# ------------------------------------------------------------------------------
def collect_rss_meta_via_feedparser(
    feeds: List[str],
    per_feed_limit: int = PER_FEED_LIMIT,
    days_back: Optional[int] = None,
) -> List[NewsDoc]:
    docs: List[NewsDoc] = []
    cutoff = None
    if days_back and days_back > 0:
        cutoff = time.time() - days_back * 86400

    for rss_url in feeds:
        parsed = feedparser.parse(rss_url)
        source = _domain_of(rss_url)
        cnt = 0
        entries = getattr(parsed, "entries", []) or []
        for e in entries[:per_feed_limit]:
            title = _norm(getattr(e, "title", ""))
            link = _norm(getattr(e, "link", ""))
            if not title or not link: continue
            ts = _parse_time(e)
            if cutoff is not None and ts and ts < cutoff: continue
            summary = _norm(getattr(e, "summary", "")) or _norm(getattr(e, "description", ""))
            docs.append(NewsDoc(title, link, ts, source, summary))
            cnt += 1
        if DEBUG: print(f"[RSS] {source} : {cnt} fetched")

    if DEBUG: print(f"[RSS] total collected = {len(docs)} (meta only)")
    return docs

# ------------------------------------------------------------------------------
# 본문 스크랩
# ------------------------------------------------------------------------------
def _scrape_hankyung_via_loader(url: str) -> str:
    try:
        loader = WebBaseLoader(
            web_paths=(url,),
            bs_kwargs=dict(parse_only=bs4.SoupStrainer("div", attrs={"id": "articletxt"})),
            header_template=UA_HEADERS,
        )
        docs = loader.load()
        if not docs: return ""
        return " ".join(s.strip() for s in (docs[0].page_content or "").split("\n") if s.strip())
    except Exception as e:
        if DEBUG: print("[scrape fail] hankyung:", repr(e))
        return ""

def _scrape_yonhap(url: str, timeout: int = 15) -> str:
    try:
        loader = WebBaseLoader(
            web_paths=(url,),
            bs_kwargs=dict(parse_only=bs4.SoupStrainer("div", attrs={"class": "story-news article"})),
            header_template=UA_HEADERS,
        )
        docs = loader.load()
        if docs:
            text = docs[0].page_content.strip()
            text = " ".join(s.strip() for s in text.split("\n") if s.strip())
            return re.sub(r"\[[^\]]*\]", "", text)
    except Exception: pass
    
    try:
        r = requests.get(url, headers=UA_HEADERS, timeout=timeout)
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        container = soup.select_one("div.story-news.article")
        if not container: return ""
        for bad in container.select("script, style, figure, aside"): bad.decompose()
        for br in container.find_all("br"): br.replace_with("\n")
        
        text = container.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\[[^\]]*\]", "", text)
        return text
    except Exception as e:
        if DEBUG: print("[scrape fail] yonhap:", repr(e))
        return ""

def _scrape_mk(url: str, timeout: int = 15) -> str:
    try:
        resp = requests.get(url, headers=UA_HEADERS, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        if DEBUG: print("[scrape fail] mk GET:", repr(e))
        return ""
    soup = bs4.BeautifulSoup(resp.text, "html.parser")
    container = soup.select_one("div.news_cnt_detail_wrap")
    if not container: return ""
    for bad in container.select(".ad_wrap, .ad_wrap_ad_wide, script, style, figure, aside"): bad.decompose()
    
    text = container.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)

def scrape_article_via_loader(url: str) -> str:
    dom = _domain_of(url)
    if "hankyung.com" in dom: return _scrape_hankyung_via_loader(url)
    if "yna.co.kr" in dom: return _scrape_yonhap(url)
    if "mk.co.kr" in dom: return _scrape_mk(url)

    tag_attrs = DOMAIN_PARSE_ONLY.get(dom)
    if not tag_attrs: return ""
    try:
        loader = WebBaseLoader(
            web_paths=(url,),
            bs_kwargs=dict(parse_only=bs4.SoupStrainer(tag_attrs[0], attrs=tag_attrs[1])),
            header_template=UA_HEADERS,
        )
        docs = loader.load()
        if not docs: return ""
        return _norm(docs[0].page_content or "")
    except Exception as e:
        if DEBUG: print("[scrape fail]", dom, repr(e))
        return ""

# ------------------------------------------------------------------------------
# LLM 파라미터 추출
# ------------------------------------------------------------------------------
class SearchParams(BaseModel):
    keyword: Optional[str] = Field(None, description="핵심 키워드")
    k: int = Field(1, ge=1, le=5, description="개수")
    reason: Optional[str] = Field(None, description="이유")

def extract_search_params_llm(user_text: str) -> SearchParams:
    sys_prompt = (
        "사용자의 입력에서 뉴스 검색을 위한 '핵심 키워드(keyword)'와 '요청 개수(k)'를 추출하세요.\n"
        "반드시 아래 JSON 포맷으로만 응답하세요. 코드블록이나 다른 말은 쓰지 마세요.\n\n"
        "{\n"
        '  "keyword": "검색어" (명확하지 않으면 null),\n'
        '  "k": 숫자 (1~5 사이, 언급 없으면 1),\n'
        '  "reason": "추출 근거"\n'
        "}\n\n"
        "예시:\n"
        "- '삼성전자 기사 3개 찾아줘' -> {\"keyword\": \"삼성전자\", \"k\": 3, \"reason\": \"키워드 삼성전자, 3개 요청\"}\n"
        "- '최근 경제 뉴스 보여줘' -> {\"keyword\": \"경제\", \"k\": 1, \"reason\": \"키워드 경제, 개수 미지정(기본값 1)\"}\n"
        "- '요약해줘' -> {\"keyword\": null, \"k\": 1, \"reason\": \"검색 키워드 없음\"}"
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    try:
        res = llm.invoke([("system", sys_prompt), ("user", user_text)])
        text = res.content.strip()
        
        # ✅ [수정] 마크다운 코드 블록 제거 (```json ... ```)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        import json
        parsed = json.loads(text)
        if DEBUG:
            print(f"[DBG params] LLM 추출 결과 -> 키워드: '{parsed.get('keyword')}', 개수: {parsed.get('k')}")
            print(f"             이유: {parsed.get('reason')}")
        return SearchParams(**parsed)
        
    except Exception as e:
        if DEBUG: print(f"[DBG] params extract failed: {e}") # 디버그용 로그 추가
        return SearchParams(keyword=None, k=1, reason="fallback")

# ------------------------------------------------------------------------------
# Daily Top 3 (본문 기반)
# ------------------------------------------------------------------------------
def build_daily_top3(profile: Optional[Dict[str, Any]] = None,
                     state: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    # 1) 메타 수집
    meta = collect_rss_meta_via_feedparser(FEEDS, per_feed_limit=PER_FEED_LIMIT)

    # 2) 전건 본문 스크랩
    full: List[NewsDoc] = []
    for d in meta:
        d.content = scrape_article_via_loader(d.url)
        full.append(d)
        if DEBUG:
            print(f"[daily] scraped {len(d.content):>4} | {d.source} | {d.title[:30]}")

    # 3) 관심사 기반 필터
    interests = set((profile or {}).get("interests", []))
    def _hit(doc: NewsDoc) -> bool:
        if not interests: return True
        t, s, c = doc.title.lower(), doc.summary.lower(), (doc.content or "").lower()
        return any(k.lower() in t or k.lower() in s or k.lower() in c for k in interests)

    full = [d for d in full if _hit(d)]

    # 4) 중복 제거 & 최신순 -> Top 3
    full = _dedup_by_title(full)
    full.sort(key=lambda d: d.published_at, reverse=True)
    picks = full[:3]

    # ✅ [핵심 수정] content 필드를 포함하여 반환하도록 수정
    daily = [
        {
            "title": d.title,
            "url": d.url,
            "source": d.source,
            "published_at": int(d.published_at),
            "summary": d.summary,
            "content": d.content,  # ★ 여기를 추가했습니다!
        }
        for d in picks
    ]

    if state is not None:
        ctx = state.setdefault("context", {})
        ctx["daily_pool"] = daily
        if DEBUG: print("[daily] saved daily_pool:", len(daily))

    return daily

# ------------------------------------------------------------------------------
# On-Demand (챗봇)
# ------------------------------------------------------------------------------
def handle_on_demand(user_text: str, state: Optional[Dict] = None, profile: Optional[Dict] = None) -> AIMessage:
    params = extract_search_params_llm(user_text)
    keyword, k = params.keyword, params.k
    
    picks: list[NewsDoc] = []
    # DB 검색 생략 (필요시 추가)
    
    # RSS 검색
    meta = collect_rss_meta_via_feedparser(FEEDS, per_feed_limit=ONDEMAND_PER_FEED_LIMIT, days_back=ONDEMAND_DAYS_BACK)
    if keyword:
        meta = [d for d in meta if _keyword_matches_any(d.title, d.summary, "", keyword)]
    meta.sort(key=lambda d: d.published_at, reverse=True)
    
    # 중복 제거 및 선택
    seen = set()
    for d in meta:
        if d.url not in seen:
            seen.add(d.url)
            picks.append(d)
            if len(picks) >= k: break
            
    if not picks:
        return AIMessage(content=f"[news_find] '{keyword}' 관련 기사를 찾지 못했습니다.")

    # 본문 스크랩
    ctx_articles = []
    for d in picks:
        d.content = scrape_article_via_loader(d.url)
        ctx_articles.append({
            "title": d.title, "url": d.url, "source": d.source,
            "published_at": int(d.published_at), "summary": d.summary,
            "content": d.content 
        })

    if state is not None:
        ctx = state.setdefault("context", {})
        ctx["selected_articles"] = ctx_articles
        ctx["news_candidates"] = ctx_articles # UI용

    lines = [f"[news_find] '{keyword or '최근'}' 관련 상위 {len(picks)}개"]
    for i, d in enumerate(picks, 1):
        lines.append(f"{i}. {d.title} ({d.source})\n   {d.url}")
    
    return AIMessage(content="\n".join(lines))

def handle(user_text: str, profile: Optional[Dict] = None, state: Optional[Dict] = None) -> AIMessage:
    if DEBUG: print("[DBG handle] enter news_find.handle()")
    return handle_on_demand(user_text=user_text, state=state, profile=profile)