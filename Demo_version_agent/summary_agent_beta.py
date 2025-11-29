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