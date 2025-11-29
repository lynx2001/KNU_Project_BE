import os
import json
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_tavily import TavilySearch 

from langchain.agents import AgentExecutor
from langchain_openai.agents import create_openai_tools_agent
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

FAKE_DB = {}

class EconomicTerm(BaseModel):
    term: str = Field(description="뉴스에서 추출한 핵심 경제 용어")

class ExtractedTerms(BaseModel):
    terms: List[EconomicTerm] = Field(description="추출된 경제 용어 목록")

class TermAgentState(TypedDict):
    input_text: str
    extracted_terms: List[str]
    current_term: Optional[str]
    final_definitions: Dict[str, str]
    _db_lookup_result: Optional[str]


llm_extractor = ChatOpenAI(model="gpt-4o", temperature=0)
llm_generator = ChatOpenAI(model="gpt-4o", temperature=0)

search_tool = TavilySearch(max_results=3, search_depth="basic")
tools = [search_tool]

def extract_terms(state: TermAgentState) -> Dict:
    """[노드 1] 텍스트에서 용어를 추출합니다."""
    print(f"--- [Node 1] 용어 추출 시작 ---")
    input_text = state['input_text']
    
    prompt = ChatPromptTemplate.from_template(
        "당신은 경제 분석가입니다. 다음 텍스트에서 교육적으로 의미 있는 핵심 경제 용어를 3~5개 추출하세요.\n\n"
        "텍스트: {text}"
    )
    extraction_chain = prompt | llm_extractor.with_structured_output(ExtractedTerms)
    
    try:
        result = extraction_chain.invoke({"text": input_text})
        term_list = [t.term for t in result.terms]
        print(f"추출 완료: {term_list}")
        
        return {
            "extracted_terms": term_list,
            "final_definitions": {}
        }
    except Exception as e:
        print(f"!! 용어 추출 실패: {e}")
        return {"extracted_terms": [], "final_definitions": {}}


def select_next_term(state: TermAgentState) -> Dict:
    """[노드 2 - 신규] 처리할 다음 용어를 선택하고 상태를 업데이트합니다."""
    print(f"--- [Node 2] 다음 용어 선택 ---")
    terms_list = state.get("extracted_terms", [])
    
    if not terms_list:
        print("  [Log] 처리할 용어가 더 없습니다.")
        return {"current_term": None} 

    
    current_term = terms_list.pop(0)
    print(f"  [Log] 다음 용어 처리: {current_term}")
    
    
    return {
        "current_term": current_term,
        "extracted_terms": terms_list 
    }

def check_vector_db_mock(state: TermAgentState) -> Dict:
    """[노드 3] 용어가 Vector DB에 있는지 '시뮬레이션'합니다."""
    print(f"--- [Node 3] DB 조회 시도 ---")
    current_term = state['current_term'] 
    
    print(f"  [Log] '감독관'에게 '{current_term}' 용어 조회를 요청합니다...")
    
    if current_term in FAKE_DB:
        print(f"  [Cache Hit] DB에서 '{current_term}'의 정의를 찾았습니다.")
        return {"_db_lookup_result": FAKE_DB[current_term]}
    else:
        print(f"  [Cache Miss] DB에 '{current_term}'의 정의가 없습니다.")
        return {"_db_lookup_result": None}
