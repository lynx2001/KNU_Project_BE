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
