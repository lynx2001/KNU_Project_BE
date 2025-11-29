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
