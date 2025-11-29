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
