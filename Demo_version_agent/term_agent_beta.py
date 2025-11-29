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
    
def generate_new_definition(state: TermAgentState) -> Dict:
    """[노드 4 - Cache Miss] 웹 검색(Tool)을 사용하여 새 정의를 생성합니다."""
    print(f"--- [Node 4] 새 정의 생성 (Web Search) ---")
    term = state['current_term']
    context = state['input_text']

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", 
         "당신은 경제 용어 사전입니다. 사용자가 요청한 경제 용어의 정의를 찾아야 합니다. \n"
         "반드시 'tavily_search' 도구를 사용해 신뢰할 수 있는 정보를 검색하세요. \n"
         "검색된 정보를 바탕으로, 해당 용어의 핵심 정의를 2~3문장으로 간결하게 요약/설명해 주세요. \n"
         "문맥을 참고하여, 만약 여러 의미가 있다면 가장 관련성 높은 의미를 선택하세요."),
        ("user", f"경제 용어: '{term}'\n\n참고 문맥:\n{context}")
    ])
    

    tool_agent = create_openai_tools_agent(llm_generator, tools, prompt_template)
    agent_executor = AgentExecutor(agent=tool_agent, tools=tools, verbose=False)
    
    try:
        
        response = agent_executor.invoke({"input": f"정의: {term}"})
        new_definition = response['output']
        
        current_definitions = state['final_definitions']
        current_definitions[term] = new_definition
        
        return {"final_definitions": current_definitions}
    except Exception as e:
        print(f"!! 정의 생성 실패: {e}")
        current_definitions = state['final_definitions']
        current_definitions[term] = "오류: 정의를 생성하지 못했습니다."
        return {"final_definitions": current_definitions}

def fetch_from_db(state: TermAgentState) -> Dict:
    """[노드 5 - Cache Hit] DB에 용어가 있을 때, 조회된 결과를 가져옵니다."""
    print(f"--- [Node 5] DB 정의 사용 ---")
    term = state['current_term']
    definition = state['_db_lookup_result']
    
    current_definitions = state['final_definitions']
    current_definitions[term] = definition
    
    return {"final_definitions": current_definitions}

def update_db_mock(state: TermAgentState) -> Dict:
    """[노드 6 - Cache Miss 이후] 새로 생성된 정의를 DB에 저장(갱신)합니다."""
    print(f"--- [Node 6] DB 갱신 시도 ---")
    term = state['current_term']
    new_definition = state['final_definitions'][term]
    
    print(f"  [Log] '감독관'에게 '{term}'의 새 정의 저장을 요청합니다...")
    
    if "오류" not in new_definition:
        FAKE_DB[term] = new_definition
        print(f"  [DB Updated] FAKE_DB가 '{term}'로 갱신되었습니다.")
    
    return {} # 상태 변경 없음


def should_continue(state: TermAgentState) -> str:
    """[엣지 1] 처리할 용어가 더 있는지 (current_term) 확인합니다."""
    if state['current_term'] is None:
        print("\n--- [루프 종료] 모든 용어 처리 완료 ---")
        return END
    else:
        return "continue_processing" 

def route_after_db_check(state: TermAgentState) -> str:
    """[엣지 2] DB 조회 결과(Cache Hit / Miss)에 따라 경로를 분기합니다."""
    if state['_db_lookup_result']:
        return "fetch_from_db"
    else:
        return "generate_new_definition" 


workflow = StateGraph(TermAgentState)


workflow.add_node("extract_terms", extract_terms)
workflow.add_node("select_next_term", select_next_term) 
workflow.add_node("check_vector_db_mock", check_vector_db_mock)
workflow.add_node("generate_new_definition", generate_new_definition)
workflow.add_node("fetch_from_db", fetch_from_db)
workflow.add_node("update_db_mock", update_db_mock)

workflow.set_entry_point("extract_terms")
workflow.add_edge("extract_terms", "select_next_term")


workflow.add_conditional_edges(
    "select_next_term",
    should_continue,
    {
        "continue_processing": "check_vector_db_mock", 
        END: END
    }
)

workflow.add_conditional_edges(
    "check_vector_db_mock",
    route_after_db_check,
    {
        "fetch_from_db": "fetch_from_db",
        "generate_new_definition": "generate_new_definition"
    }
)

workflow.add_edge("generate_new_definition", "update_db_mock")
workflow.add_edge("update_db_mock", "select_next_term")
workflow.add_edge("fetch_from_db", "select_next_term")

app = workflow.compile()
