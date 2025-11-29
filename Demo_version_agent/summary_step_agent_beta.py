import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.chains import load_summarize_chain
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

# 1. 입문 (경제 용어 비유 설명)
PROMPT_INTRO = PromptTemplate(
    template="""당신은 경제학을 전혀 모르는 사람에게 설명하는 친절한 경제 선생님입니다.
다음 기사 내용을, 마치 우리 동네 가게나 우리 집 살림에 빗대어 설명하듯이, 전문 용어를 전혀 사용하지 않고 가장 쉽게 풀어서 2문장으로 요약해 주세요:

"{text}"

가장 쉬운 비유 경제 요약:""",
    input_variables=["text"]
)

# 2. 초보 (자연스러운 문단 요약) 
PROMPT_BEGINNER = PromptTemplate(
    template="""당신은 경제 뉴스를 처음 접하는 사람들을 위한 친절한 안내자입니다.
다음 기사의 핵심 내용을 가장 쉬운 단어를 사용하여 3문장의 자연스러운 글로 요약해 주세요. 번호를 붙이거나 목록으로 만들지 말고, 글의 흐름에 따라 무슨 일이 있었는지 이야기하듯이 설명해주세요.

"{text}"

핵심 내용 요약:""",
    input_variables=["text"]
)

# 3. 중급 (거시경제 관점 분석)
PROMPT_INTERMEDIATE = PromptTemplate(
    template="""당신은 경제 동향을 파-악하고 있는 투자자를 위해 브리핑하는 애널리스트입니다.
다음 기사의 내용을 수요와 공급, 통화 정책, 시장 심리 등 거시경제적 관점에서 분석하고, 그 인과관계를 중심으로 4문장 이내로 요약해 주세요:

"{text}"

거시경제 분석 요약:""",
    input_variables=["text"]
)

# 4. 상급 (경제 이론/정책적 함의)
PROMPT_ADVANCED = PromptTemplate(
    template="""당신은 경제 정책 입안자나 기관 투자자에게 자문하는 수석 이코노미스트입니다.
다음 기사의 현상을 특정 경제 이론이나 과거 유사 사례와 연결지어 분석하고, 잠재적인 2차 파급 효과와 장기적인 정책적 함의를 포함하여 4문장 이내로 통찰력 있는 요약을 제공해 주세요:

"{text}"

심층 경제 분석 요약:""",
    input_variables=["text"]
)

llm = ChatOpenAI(model="gpt-4o", temperature=0)

def get_summary_with_prompt(text_to_summarize: str, prompt: PromptTemplate):
    """
    주어진 프롬프트를 사용하여 텍스트를 요약하는 함수.
    'Stuff' 전략은 텍스트 전체를 한번에 처리하는 가장 간단한 방식입니다.
    """
    
    docs = [Document(page_content=text_to_summarize)]
    
    
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
    
    
    summary = chain.invoke({"input_documents": docs})['output_text']
    return summary.strip()

sample_text = """
코스피가 사상 처음으로 3500선을 돌파한 가운데 추석 연휴 이후 상승세를 이어갈지 주목된다. 연휴기간 중 발표될 미국 경제지표와 미 증시의 움직임이 우리 증시에 어떤 영향을 미칠지 투자자의 관심이 쏠리고 있다.8일 증권가에 따르면 국내 증시는 개천절부터 한글날까지 이어지는 추석 연휴로 오는 9일까지 휴 장한다.연휴 전날인 지난 2일 코스피는 역사상 최초로 3500 고지를 밟았다. 삼성전자와 SK하이닉스가 오픈AI와 함께 인공지능(AI) 인프라 구축 사업 ‘스타게이트 프로젝트’에 참여한다는 소식이 호재로 작용하며 지수 상승을 견인했다. 삼성전자와 SK하이닉스는 장중 각각 ‘9만전자’와 ‘40만닉스’를 터치하기도 했다.역대 두  번째로 긴 추석 연휴로 인해 증시가 5거래일간 휴장하는 가운데 이 기간 글로벌 금융시장의 주요 이벤트가  기다리고 있다.특히 미국 연방준비제도(Fed·연준)의 9월 연방공개시장위원회(FOMC) 의사록은 연속적 금리인 하 기대와 맞물려 주목된다. 의사록을 통해 연준의 향후 금리 정책 방향을 확인할 수 있으며, 이는 글로벌  금융시장뿐 아니라 국내 증시에도 직접적인 영향을 미칠 것으로 예상된다.김두언 하나증권 연구원은 “의사록에서 소수의견의 강도와 인플레이션 재부각 우려, 금리인하 속도 조절 관련 언급이 확인될 경우 연속 금리  인하에 대한 낙관론이 약화될 수 있다”며 “연준의 독립성 위협과 결부된 연준 내 의견도 주목할 이슈”라고  설명했다.증권가에서는 추석 연휴 이후 코스피의 추가 상승 가능성이 높다고 입을 모은다. 연휴 직후 삼성전자를 시작으로 발표될 3분기 실적 시즌이 국내 증시의 상승 동력을 재차 자극할 것이란 분석이다. 삼성전자 는 이달 셋째주 초에 잠정 실적을 발표할 것으로 예상된다.추석 연휴 이후 코스피 상승은 실제 통계적으로도 증명됐다. 하나증권에 따르면 지난 2000년부터 지난해까지 25년간 코스피 수익률을 살펴본 결과, 명절 전  일주일 동안 평균 -0.43%로 마이너스 수익률을 보이던 지수는 연휴 이후 일주일 동안 0.51% 상승하며 반전했다.한지영 키움증권 연구원은 “정부의 정책 모멘텀 회복과 미국 AI 수요 확장성과 반도체 업사이클 진입 가 능성, 연준 금리인하 기대감, 기존 주도주의 모멘텀 유지 등 최근 코스피 강세를 주도하는 요인들이 당분간 훼손되지 않을 것”이라며 “이달 코스피 방향성은 ‘단기 변동성 후 상승’으로 잡고 가는 것이 적절하다”고 말했다.
"""

if __name__ == "__main__":
    if not sample_text.strip():
        print("요약할 텍스트를 'sample_text' 변수에 입력해주세요.")
    else:
        
        prompts_by_level = {
            "입문": PROMPT_INTRO,
            "초보": PROMPT_BEGINNER,
            "중급": PROMPT_INTERMEDIATE,
            "상급": PROMPT_ADVANCED
        }
        
        print("--- [수준별 요약 생성 시작] ---")
        
        
        for level, prompt in prompts_by_level.items():
            print(f"\n✅ [{level}] 수준 요약을 생성 중입니다...")
            summary = get_summary_with_prompt(sample_text, prompt)
            print(f"--- [결과: {level}] ---")
            print(summary)
            
        print("\n\n--- [모든 작업 완료] ---")