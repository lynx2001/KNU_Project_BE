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