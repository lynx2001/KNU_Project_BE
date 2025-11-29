import os, uuid
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.globals import set_llm_cache
import random


#퀴즈 캐시 비활성화 함으로써 중복방지
set_llm_cache(None)  


load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.9,
    top_p=1.0,
    presence_penalty=0.6,
    frequency_penalty=0.3,
)
