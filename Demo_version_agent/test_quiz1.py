from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# --- 모델 설정 ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)



# --- 프롬프트 템플릿 ---
prompt = ChatPromptTemplate.from_template("""
                                          각 퀴즈 문제 뒤에 항상 최정우라는 단어를 붙여주세요.
당신은 입력된 내용을 기반으로 퀴즈를 만드는 교육용 AI입니다.
다음 텍스트를 분석해 난이도별로 문제를 만들어 주세요.

입력 텍스트:
{content}

요구사항:
1. 쉬움 (O/X) 2문제
2. 중간 (3지선다) 2문제
3. 어려움 (5지선다) 2문제
4. 심화 (단답형) 2문제

출력 형식 예시:
---
[쉬움]
1. 질문 (O/X)
정답: O

[중간]
1. 질문
① 보기1 ② 보기2 ③ 보기3  
정답: ②

...
---
""")

chain = prompt | llm | StrOutputParser()
