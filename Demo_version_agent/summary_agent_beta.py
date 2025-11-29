from dotenv import load_dotenv
load_dotenv()

# 필요한 라이브러리 임포트
from langchain_openai import ChatOpenAI # <<-- 변경된 부분
from langchain.chains.summarize import load_summarize_chain
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

stuff_prompt_template = """다음 텍스트를 한국어로 간결하게 요약해 주세요:

"{text}"

한국어 요약:"""
STUFF_PROMPT = PromptTemplate(template=stuff_prompt_template, input_variables=["text"])

map_prompt_template = """다음 텍스트의 핵심 내용을 한국어로 간결하게 요약해 주십시오:

"{text}"

한국어 요약:"""
MAP_PROMPT = PromptTemplate(template=map_prompt_template, input_variables=["text"])

combine_prompt_template = """아래는 여러 요약문들입니다. 이 요약문들을 종합하여 전체 내용에 대한 최종 요약본을 한국어로 작성해 주십시오.

"{text}"

한국어 최종 요약:"""
COMBINE_PROMPT = PromptTemplate(template=combine_prompt_template, input_variables=["text"])

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def summarize_agent_gpt(text_to_summarize: str):
    """
    [GPT 모델 사용] 텍스트 길이에 따라 자동으로 요약 전략을 선택하는 에이전트 함수
    """
    
    num_tokens = llm.get_num_tokens(text_to_summarize)
    
    if num_tokens < 8000:
        print("짧은 텍스트로 판단, 'Stuff' 전략을 사용합니다.")
        docs = [Document(page_content=text_to_summarize)]
        #chain = load_summarize_chain(llm, chain_type="stuff")
        chain = load_summarize_chain(llm, chain_type="stuff", prompt=STUFF_PROMPT)
        return chain.invoke({"input_documents": docs})['output_text']
    else:
        print("긴 텍스트로 판단, 'Map Reduce' 전략을 사용합니다.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        split_docs = text_splitter.create_documents([text_to_summarize])
        chain = load_summarize_chain(
            llm,
            chain_type="map_reduce",
            map_prompt=MAP_PROMPT,
            combine_prompt=COMBINE_PROMPT
        )
        return chain.invoke({"input_documents": split_docs})['output_text'] # .run() 대신 .invoke() 사용 권장

sample_text = """
악성 재고가 사라지고 있다. 신사업은 잘된다. 다들 불황이라는데 나홀로 ‘초호황’이다. SK하이닉스 얘기다. 낸드플래시처럼 기존에 안팔리던 반도체가 빠른 속도로 소진되고 있다. 인공지능(AI) 시대 핵심 ‘고속도로’인 고대역폭메모리(HBM)은 없어서 못 팔 정도다.글로벌 AI 시장의 개척자인 ‘오픈AI’가 SK하이닉 스에 손을 내밀었다. 700조원 짜리 프로젝트인 ‘스타게이트’를 도와 달라고 한다. 스타게이트는 미국 중심의 AI 인프라스트럭처다. 투자는 소프트뱅크가, 운영은 오픈AI가 맡는다. 여기에 기술 파트너로 엔비디아 마이크로소프트 Arm 등이 참여한다.이미 엔비디아에게 칩 성능에서 합격점을 받은 SK하이닉스는 이번에 오픈AI으로부터도 ‘초대장’을 받으면서 AI 시대 핵심 기업으로 인정받게 된다. SK그룹 최태원 회장과 샘 올트먼 오픈AI 최고경영자가 만난 이후 하이닉스 주가는 사상 처음으로 장중 40만원을 돌파했다.SK하이닉스 주가는 추석 연휴 직전인 지난 10월 2일 10% 가까이 급등했다. 모든 투자자들은 향후 최고의 업종으로 AI를 꼽는데, SK 하이닉스가 스타게이트를 통해 ‘프리패스’(무사통과)를 받았기 때문이다. 게다가 경쟁사 대비 저평가된 주가에 독점 기업으로서의 장점까지 갖춰 투자 매력이 높다는 평가다.하이닉스의 2022년 이후 올해 예상 실적을 보면 AI 시대가 한 기업에게 어떤 영향을 미쳤는 지 직관적으로 알 수 있다. 2022년 매출은 44조6216억원. 2023년에는 메모리 반도체 시장의 위축으로 매출이 전년 대비 26.2% 감소한 32조7657억원으로 쪼그라들었다. 하지만 여기가 바닥이었다. 하이닉스의 골칫거리였던 저가·저품질 반도체(구형 D램, 낸드 등)가 소진되기 시작한 것. 재고 부담이 극에 달했던 2023년 1분기에 재고평가손실은 무려 2조4405억원에 달했다. 재고손실은 매출원가에 반영돼 순이익을 떨어뜨린다.PC와 스마트폰 수요가 완전히 죽지 않은 가운데 하이닉스는 삼성전 자와 함께 구형 메모리에 대한 생산 감축에 들어간다. 구형 설비도 HBM 등 고마진 제품쪽으로 돌리면서 구조조정에 들어갔다. 고마진 신사업 실적이 쭉쭉 올라가면서 구형 제품 재고까지 감소하니 실적이 눈에 띄게 개선되기 시작한다.AI 기대감이 실적에 반영되기 시작한 지난 2024년 매출은 2023년 대비 2배 이상 늘어난 66 조1930억원이다. 올해는 88조8452억원으로 추정된다. 전년 대비 매출 증가율은 34.2%. 2026년의 경우 매출  성장률이 19.7%로 떨어진다. 이는 아직 ‘오픈AI 효과’가 예상 매출로 반영되지 않아서다.올해 예상 순이익은 32조3725억원(B)이다. 하이닉스 시가총액이 287조9249억원(A)이니까 주가수익비율(PER·A/B)은 8.9배다. 글 로벌 반도체 핵심 상장사로서 낮은 주가수익비율을 나타내며 극도의 저평가 상태라는 분석이 뒤따른다.월스 트리트에선 스타게이트 사업에서 메모리 반도체 부문이 140조원은 차지할 것으로 보고 있다. 지나친 낙관과 보수적 시나리오를 제외하고 스타게이트 메모리 중 30%를 점유할 것으로 추정해보면 하이닉스의 몫은 42조원이 될 것이란 분석도 있다.42조원의 스타게이트 관련 매출은 초기 3년내에 집중될 것으로 보인다. 이에 따라 하이닉스는 2027년까지 연평균 8조원 짜리 매출이 추가로 발생할 것으로 보인다. 매출 기준 주가는 매출주 가비율(PSR)로 높낮이를 판단한다. PSR을 활용하면 향후 주가 상승 여력을 예상해볼 수 있다.현재 기준 하이닉스의 예상 PSR은 3.2배다. 2026년에도 이 수준이 유지된다고 가정하고, 내년에 8조원의 예상 매출을 기존 증권가 추정치(106조3358억원)에 더하면 114조3358억원이 나온다. PSR은 2.5배 까지 낮아지니 주가는 15% 더 오를 여지가 있다는 해석이 가능하다.요즘은 글로벌 주식 투자가 대세다. 하이닉스도 그 후보군 중 하나일 뿐이다. 그러나 AI 시대 핵심 반도체 상장사라는 위치는 아무나 얻을 수 없다. HBM 공급사가 하이닉스를 포 함해 삼성전자와 마이크론으로 독과점 구조라는 것도 주된 이유다. 이중 엔비디아 등 빅테크의 인정을 받은 곳은 하이닉스가 유일하다.업계에서 하이닉스와 비교 대상군은 국내의 삼성전자와 미국 마이크론·웨스턴디지털이다. 삼성전자는 종합반도체기업(IDM)으로 주요 사업에서 하이닉스와 경쟁 체제다. 그러나 워낙 사업군이 다양해 일부 사업에선 전체 실적을 깎아 먹고 있다.에프앤가이드에 따르면 삼성전자의 올해 예상 PER은 14.5배다. 9배가 채 안되는 하이닉스에 비해 고평가됐다는 해석이 가능하다. 미국 최대 메모리 업체인 마이크론 역시 10.6배로, 실적 기준으로 봤을 때 주가는 상대적 고평가 구간이다. 마이크론 주가는 올 들어 2배 이상 오르면서 저평가 매력이 사라졌다는 분석이다.최근 낸드 사업을 늘리고 있는 웨스턴디지털은 삼성과 하이닉스의 감산 효과로 어부지리 수익을 거두고 있다. 이에 따라 주가는 올 들어서만 3배 가까이 급등했다. 다만 AI 사업과의 연관성은 하이닉스 보다 떨어진다. 올해 예상 순익 기준 PER은 16배로 치솟았다.SK하이닉스의  배당수익률은 0.6% 수준이다. 마이크론과 웨스턴디지털 역시 1%가 안되는 배당률이기 때문에 ‘도토리 키재기’다. 그러나 삼성전자의 경우 배당률이 1.6%다. 배당 장기 투자자 입장에선 실적과 배당률이 나은 삼성을 택할 수 있다는 분석이다.게다가 HBM 경쟁에 삼성전자가 뒤늦게 참전한 만큼 실적 상승 여력은 삼성이 SK 보다 더 뛰어나다는 의견도 있다. 배당 등 주주환원 정책에선 삼성이나 SK나 비슷하다. 잉여현금흐름(FCF)의 50%를 주주환원에 쓰겠다는 입장이다. 각종 투자나 세금을 내고 남은 돈 중 절반만 배당이나 자사주 소각에 활 용하겠다는 뜻이다. 배당 투자자 입장에선 두 기업 모두 그리 높은 점수를 주지 못하고 있다.
"""

if sample_text.strip():
    final_summary = summarize_agent_gpt(sample_text) 
    print("--- [원문 텍스트 (일부)] ---")
    print(sample_text)
    print("\n--- GPT 모델 최종 요약 결과 ---")
    print(final_summary)
else:
    print("요약할 텍스트를 'sample_text' 변수에 입력해주세요.")