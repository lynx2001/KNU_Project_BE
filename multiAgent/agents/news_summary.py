"""
news_summary.py — 뉴스 요약 에이전트 (LangChain + FewShot + Personalization)
"""
from typing import List, Dict, Any, Optional
import re, json, time

from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

# ============================================================
# 🔧 디버그 설정
# ============================================================
DEBUG = True

def dprint(*args, **kwargs):
    """디버그 모드일 때만 출력"""
    if DEBUG:
        print("[DBG news_summary]", *args, **kwargs)

# ---------------------------
# 0) 안전 장치: 기사 리스트 정제 + 제어문자 제거
# ---------------------------
def _strip_ctrl(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", str(text))

def sanitize_articles(items: List[Any]) -> List[Dict]:
    safe = []
    for x in items:
        if isinstance(x, dict):
            safe.append({
                "title": _strip_ctrl(x.get("title", "")),
                "url": _strip_ctrl(x.get("url", "")),
                "content": _strip_ctrl(x.get("content", "")),
            })
    return safe

SAFE_MAX_CHARS = 4000  # GPT-4o-mini 토큰 한도 고려

# ---------------------------
# 1) 레벨별 퓨샷 (스키마 유지, 개인화 문구 강화)
# ---------------------------
FEW_SHOT_EXAMPLES = {
    "씨앗": [{
        "input": "미 연준이 기준금리를 동결했다는 뉴스 본문",
        "output": {
            "summary_5sentences": (
                "미국의 기준금리가 그대로 유지되면서 당장 대출 이자나 예금 이자가 갑자기 크게 바뀌지는 않게 되었어요. "
                "집을 사려고 하거나 학자금·생활비 대출을 쓰는 사람들은 한숨 돌릴 수 있지만, 앞으로 물가와 일자리 상황을 보며 다시 결정할 수 있다는 점은 기억해야 해요. "
                "미국 금리가 그대로라서 원·달러 환율과 해외 자금 흐름에도 큰 충격은 없지만, 뉴스에 따라 서서히 움직일 수 있어요. "
                "우리나라에도 간접적인 영향이 오기 때문에, 뉴스를 볼 때 '금리·환율·물가'가 같이 움직인다는 정도만 알아두면 충분해요. "
                "지금은 겁먹기보다, 쓸데없는 소비를 조금 줄이고 다음 금리 결정 소식을 차분히 챙겨보는 연습을 하면 좋아요."
            ),
            "key_points": [
                "기준금리 동결로 단기 이자 부담 변화 제한",
                "향후 결정은 물가·고용 지표에 따라 유동적",
                "국내에는 환율·자금 흐름을 통해 간접 영향"
            ],
            "metrics": [
                {"name": "Fed Funds Rate", "value": "5.25~5.50%", "period": "이번 회의"},
                {"name": "CPI 상승률", "value": "기사 기준 수치 사용", "period": "최근 발표치"}
            ],
            "term_candidates": ["기준금리", "통화정책", "물가", "환율"]
        }
    }],
    "새싹": [{
        "input": "원/달러 환율이 1,400원을 돌파했다는 뉴스 본문",
        "output": {
            "summary_5sentences": (
                "원/달러 환율이 1,400원을 넘어서면서 수입 물가와 해외 결제 비용이 전반적으로 올라갈 수 있는 구간에 들어섰습니다. "
                "달러로 결제하는 유학비, 스트리밍·소프트웨어 구독료, 해외 직구 비용 등이 이전보다 비싸질 수 있어 지출 계획을 다시 점검할 필요가 있습니다. "
                "기업 입장에서는 원자재·에너지 수입 단가가 높아져 제품 가격 인상 압력으로 이어질 수 있고, 이는 시간이 지나 소비자 물가에도 영향을 줄 수 있습니다. "
                "다만 환율은 글로벌 경기, 금리 차이, 위험 회피 심리 변화에 따라 되돌림이 나올 수 있어 단기 급등만 보고 성급히 환전이나 투자를 결정하는 것은 바람직하지 않습니다. "
                "앞으로는 환율 흐름과 함께 물가, 미국·한국 금리 방향을 함께 보면서 큰 지출 시기와 분할 환전 전략을 생각해 보는 것이 현실적인 대응입니다."
            ),
            "key_points": [
                "환율 1,400원 돌파로 수입·해외결제 비용 부담 확대",
                "기업 원가 상승이 소비자 물가로 전가될 가능성 존재",
                "단기 급등에 과도 반응보다 지표와 흐름을 함께 관찰 필요"
            ],
            "metrics": [
                {"name": "USD/KRW", "value": "1,400원 상회", "period": "당일"},
                {"name": "WTI/원자재 가격", "value": "기사 내 수치 참조", "period": "동일 기간"}
            ],
            "term_candidates": ["환율", "수입물가", "무역수지", "위험회피"]
        }
    }],

    "나무": [{
        "input": "반도체 업황 개선 기대감으로 코스피가 상승했다는 뉴스 본문",
        "output": {
            "summary_sentences": (
                "반도체 업황 회복 기대감과 외국인 순매수세에 힘입어 코스피가 상승했습니다. "
                "최근 기업 이익 전망치도 빠르게 오르고 있습니다. "
                "하지만 주가가 실적 개선 속도보다 너무 앞서간 것은 아닌지 밸류에이션 부담을 점검할 때입니다. "
                "단기적으로 거래대금이 급증하는 등 일부 과열 신호도 나타나고 있습니다. "
                "이에 변동성 관리를 위해 분할 매도 등의 전략을 고려해볼 수 있습니다. "
                "특히 반도체 비중이 높은 포트폴리오는 글로벌 IT 수요 같은 거시 변수를 함께 모니터링해야 합니다. "
                "이번 상승을 계기로 단기 모멘텀과 펀더멘털의 괴리를 분석하는 자세가 필요합니다."
            ),
            "key_points": [
                "반도체 실적 상향과 외국인 수급이 지수 상승을 견인",
                "밸류에이션과 이익 전망의 정합성 점검 필요",
                "과열 신호 구간에서 분할 매매와 리스크 관리 전략 요구"
            ],
            "metrics": [
                {"name": "KOSPI", "value": "+1% 내외 상승", "period": "당일"},
                {"name": "반도체 업종 지수", "value": "상승", "period": "동일 기간"}
            ],
            "term_candidates": ["밸류에이션", "순매수", "모멘텀", "이익추정", "리스크관리"]
        }
    }],

    "숲": [{
        "input": "재정지출 확대와 긴축적 통화정책 병행에 대한 분석 기사 본문",
        "output": {
            "summary_sentences": (
                "확장 재정과 긴축 통화라는 상충하는 정책 조합이 시장 불확실성을 키우고 있습니다. "
                "국채 발행 확대와 높은 기준금리는 장기물 금리에 구조적인 상방 압력으로 작용합니다. "
                "이는 기간 프리미엄의 재평가로 이어질 수 있습니다. "
                "결과적으로 수익률 곡선의 형태 또한 변화할 가능성이 커졌습니다. "
                "이에 기관 투자자들은 듀레이션 노출과 커브 포지셔닝을 더욱 세심하게 조정해야 합니다. "
                "만약 재정 건전성 우려가 커지면 외국인 자금 유출과 통화가치 하락이 동반될 수 있습니다. "
                "따라서 정책 조합의 신뢰도를 해석하며 자산 비중을 조절하는 것이 중요합니다."
            ),
            "key_points": [
                "재정 확대와 통화 긴축 병행이 장기 금리 및 커브 구조에 영향",
                "국채 공급 확대와 기간프리미엄 재평가 리스크 상존",
                "정책 신뢰 약화 시 외국인 수급·통화가치에 연쇄적 파급 가능"
            ],
            "metrics": [
                {"name": "10Y-2Y 스프레드", "value": "기사 기준 수치 사용", "period": "최근"},
                {"name": "국채 발행 규모", "value": "증가", "period": "예산/발행 계획"}
            ],
            "term_candidates": ["재정정책", "통화정책", "수익률곡선", "기간프리미엄", "듀레이션", "크레딧스프레드"]
        }
    }],
}

# ---------------------------
# 2) 프롬프트 빌더
# ---------------------------
def build_summary_prompt(level: str, user_profile: Dict = None) -> ChatPromptTemplate:
    level = level if level in FEW_SHOT_EXAMPLES else "새싹"
    
    # 레벨별 설정
    cfg = {
        "씨앗": {
            "sent_avg": "25~30", "sent_max": 30,
            "jargon_max": 0, "tone": "일상어 위주, 평이·직설",
            "personalize_rules": ["유치원생이 알아 들을 수 있게 요약하라."]
        },
        "새싹": {
            "sent_avg": "35~40", "sent_max": 40,
            "jargon_max": 1, "tone": "간결·실용, 필요시 쉬운 괄호 풀이",
            "personalize_rules": ["초등학생이 알아 들을 수 있게 요약하라."]
        },
        "나무": {
            "sent_avg": "45~50", "sent_max": 50,
            "jargon_max": 3, "tone": "시장·수급 용어 허용, 과잉전문어 금지",
            "personalize_rules": ["경제학을 전공한 학부생이 알아 들을 수 있게 요약하라."]
        },
        "숲": {
            "sent_avg": "55~60", "sent_max": 60,
            "jargon_max": 5, "tone": "정책·커브·프리미엄 등 고급 용어 허용",
            "personalize_rules": ["경제학 박사 혹은 교수가 알아 들을 수 있게 요약하라."]
        }
    }.get(level, { 
        "sent_avg": "50", "sent_max": 50, "jargon_max": 2, "tone": "친절함", "personalize_rules": ["쉽게 설명하라"]
    })

    up = user_profile or {}
    interests = ", ".join(up.get("interests", [])) or "일반"
    
    parser = JsonOutputParser()
    format_instructions = parser.get_format_instructions()

    system_tmpl = (
        "당신은 경제 뉴스 요약 전문가입니다. 반드시 한국어로 답하고, 사실에 없는 내용은 추정하지 마세요.\n"
        "오직 JSON 하나만 반환하세요. 스키마는 다음과 같습니다:\n"
        f"{format_instructions}\n"
        "- summary_5sentences: 5문장 핵심 요약(문장 수 정확히 5개).\n"
        "- ** summary_len: 글자 수 500 내외로 핵심 요약 ** (정확하게 500자 내외)"
        "- key_points: 불릿 3개(간결, 중복 금지).\n"
        "- metrics: 본문에 실재하는 수치·지표만 포함(이름/값/기간 필수, 없는 경우 빈 배열).\n"
        "- term_candidates: 독자가 모를 법한 경제 용어 2~10개(기사 맥락 내에서만).\n"
        f"- 난이도·가독성 목표(KReaD): 평균 문장 길이 {cfg['sent_avg']} 단어, 최대 {cfg['sent_max']} 단어/문장, "
        f"전문용어 상한 {cfg['jargon_max']}개, 톤: {cfg['tone']}.\n"
        "- 개인화: 아래 사용자 정보를 문장에 ‘자연스럽게’ 녹여 써서 실제 행동 판단에 도움이 되게 하세요.\n"
        f"  · 관심사: {interests}\n"
        f"  · 레벨: {level}\n"
        "- 개인화 반영 규칙(레벨별 필수 포함):\n"
        f"  1) {cfg['personalize_rules'][0]}\n"
    )

    system = ChatPromptTemplate.from_messages([("system", system_tmpl)])
    
    fewshot = FewShotChatMessagePromptTemplate(
        example_prompt=ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}")
        ]),
        examples=FEW_SHOT_EXAMPLES[level],
    )

    user_tmpl = ChatPromptTemplate.from_messages([
        ("human",
         "다음 기사를 요약하세요.\n"
         "제목: {title}\n"
         "URL: {url}\n"
         "본문:\n{content}\n\n"
         "제약:\n"
         "1) 본문에 없는 수치·사실을 만들지 마세요.\n"
         "2) summary_sentences는 정확히 5문장, 총 450~550자 내외로 작성하세요.\n"
         "3) JSON 외의 불필요한 텍스트를 절대 추가하지 마세요.")
    ])

    return system + fewshot + user_tmpl


# ---------------------------
# 3) 단일 기사 요약 (JSON 파싱 + 재시도)
# ---------------------------
def _json_loose_parse(s: str) -> Dict:
    try:
        return json.loads(s)
    except Exception:
        s2 = s.strip()
        s2 = re.sub(r"^```json\s*|\s*```$", "", s2, flags=re.IGNORECASE | re.DOTALL)
        try:
            return json.loads(s2)
        except Exception:
            return {}

def summarize_one(article: Dict, level: str, user_profile: Dict) -> Dict:
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        timeout=60,
        model_kwargs={"response_format": {"type": "json_object"}},
    )
    parser = JsonOutputParser()
    prompt = build_summary_prompt(level, user_profile)

    title = article.get("title", "")
    url = article.get("url", "")
    raw_content = (article.get("content", "") or "")
    content = _strip_ctrl(raw_content)[:SAFE_MAX_CHARS]

    if not content.strip():
        dprint(f"Skip empty content for: {title}")
        return {
            "title": title, "url": url, "level": level,
            "summary_5sentences": "본문이 비어 있어 요약을 제공할 수 없습니다.",
            "key_points": ["본문 누락"], "metrics": [], "term_candidates": [],
            "_error": "empty_content"
        }

    last_err = None
    for attempt in range(3):
        try:
            if attempt > 0:
                dprint(f"Retry summary ({attempt+1}/3) for: {title[:10]}...")
            
            chain = prompt | model
            raw = chain.invoke({"title": title, "url": url, "content": content})
            text = raw.content if hasattr(raw, "content") else str(raw)
            
            data = _json_loose_parse(text)
            if not data:
                data = parser.parse(text)

            # 최소 필드 보정
            data.setdefault("summary_5sentences", "")
            data.setdefault("key_points", [])
            data.setdefault("metrics", [])
            data.setdefault("term_candidates", [])
            
            # 성공 시 디버그 로그
            dprint(f"Summary OK: {title[:10]}... (len={len(data['summary_5sentences'])})")
            return {"title": title, "url": url, "level": level, **data}
            
        except Exception as e:
            last_err = str(e)
            dprint(f"Summary failed attempt {attempt+1}: {e}")
            time.sleep(0.5 * (attempt + 1))

    dprint(f"Give up summarizing: {title[:10]}...")
    return {
        "title": title, "url": url, "level": level,
        "summary_5sentences": f"요약 중 오류가 발생했습니다. ({last_err})",
        "key_points": ["처리 실패"], "metrics": [], "term_candidates": [], "_error": str(last_err)
    }


# ---------------------------
# 4) 메인 핸들러 (Chatbot)
# ---------------------------
def handle(text: str, profile: Optional[Dict[str, Any]] = None, state: Optional[Dict[str, Any]] = None) -> AIMessage:
    dprint("[handle] ENTER news_summary_node")
    
    ctx = (state or {}).get("context", {})
    profile = profile or (state or {}).get("profile", {}) or {}
    
    if isinstance(profile, dict):
        # 딕셔너리로 넘어온 경우 (현재 Django 환경)
        level = profile.get("grade", "새싹")
    else:
        # 객체로 넘어온 경우 (기존 환경 호환)
        level = getattr(profile, "grade", "새싹")
        
    articles = ctx.get("selected_articles", [])
    
    dprint(f"Profile Level: {level}, Articles to summarize: {len(articles)}")
    
    if not articles:
        dprint("No articles found in context.")
        return AIMessage(content="[news_summary] 요약할 기사가 없습니다. 먼저 뉴스를 검색해 주세요.")

    sanitized = sanitize_articles(articles)
    summaries = []
    
    for i, art in enumerate(sanitized, 1):
        dprint(f"[{i}/{len(sanitized)}] Summarizing: {art.get('title','Untitled')}")
        res = summarize_one(art, level, profile)
        summaries.append(res)

    # 결과를 State Context에 저장
    ctx["summaries"] = summaries
    dprint(f"Saved {len(summaries)} summaries to context['summaries']")

    # 챗봇 응답 생성
    msg_lines = [f"[news_summary] 총 {len(summaries)}건의 기사를 요약했습니다.\n"]
    for i, s in enumerate(summaries, 1):
        title = s.get("title", "무제")
        url = s.get("url", "") # ✅ URL 가져오기
        summary = s.get("summary_5sentences", "")
        
        msg_lines.append(f"{i}. {title}")
        if url: # ✅ URL이 있으면 출력
            msg_lines.append(f"   🔗 {url}")
        msg_lines.append(f"   [요약] {summary}\n") 
    
    return AIMessage(content="\n".join(msg_lines))


# ============================================================
# 5. [Batch] 데일리 파이프라인용 함수
# ============================================================
def build_daily_summaries(state: Dict[str, Any], profile: Dict) -> List[Dict]:
    """
    매일 아침 실행되는 배치 작업용 함수.
    state['context']['daily_pool'] (또는 selected_articles)의 기사를 읽어 
    일괄 요약하고 결과를 반환함.
    """
    ctx = state.get("context", {})
    level = profile.get("level", "새싹")
    
    # 1. 요약 대상 식별
    # 배치 모드에서는 보통 'daily_pool'(news_find의 결과)을 사용
    # 없으면 selected_articles(테스트용) 폴백
    source_articles = ctx.get("daily_pool") or ctx.get("selected_articles", [])
    
    dprint(f"[Batch] Starting daily summary for {len(source_articles)} articles (Level: {level})")
    
    if not source_articles:
        dprint("[Batch] No articles to summarize.")
        return []

    sanitized = sanitize_articles(source_articles)
    daily_summaries = []
    
    for i, art in enumerate(sanitized, 1):
        dprint(f"[Batch] Summarizing [{i}/{len(sanitized)}]: {art.get('title','Untitled')}")
        res = summarize_one(art, level, profile)
        daily_summaries.append(res)
        
    # 결과 저장 (보통 파이프라인 스크립트에서 state에 할당하겠지만, 여기서도 반환)
    return daily_summaries