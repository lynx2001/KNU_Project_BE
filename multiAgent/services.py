import traceback
from langchain_core.messages import HumanMessage, AIMessage
from accounts.models import Profile
from .graph_app import APP 
from django.forms.models import model_to_dict
from typing import Dict, TypedDict, Any, Annotated, List, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage

class GraphState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    plan: List[str]
    completed: List[str]
    cursor: int
    last_agent: Optional[str]
    loop_count: int
    current_intent: Optional[str]
    context: Dict[str, Any]
    profile: Dict[str, Any]

def run_agent(user, question_text, context=None):
    """
    Django View에서 호출하는 AI 에이전트 실행 함수 (1회 실행)
    
    Args:
        user: Django User 모델 인스턴스 (request.user)
        question_text: 사용자 질문 (str)
        context: (선택) 이전 대화 맥락이나 퀴즈 상태 등 (dict)
    Returns:
        str: AI의 답변
    """

    user_grade = "숲"
    try:
        user_profile = getattr(user, 'profile', None)
        user_grade = user_profile.__getattribute__("grade")
    except Exception as e:
        print(f"[AI Service] 프로필 조회 실패 (기본값 '씨앗' 사용): {e}")
        user_grade = "숲"

    print(f"[AI Service] 사용자: {user.username} | 등급: {user_grade}")

        
    # profile_data = {
    #     "username": user.username,
    #     "email": getattr(user, 'email', ''),
    #     "grade": user_grade, 
    # }

    # 2. 상태(State) 초기화
    # 단발성 질문 처리를 위한 초기 상태

    profile_dict: Dict[str, Any] = model_to_dict(user_profile) if user_profile else {}


    initial_state: GraphState = {
        "messages": [HumanMessage(content=question_text)],
        "plan": [],
        "completed": [],
        "cursor": 0,
        "last_agent": None,
        "loop_count": 0,
        "current_intent": None,
        "context": context if context else {}, 
        "profile": profile_dict
    }

    # initial_state: GraphState = {
    #     "messages": [HumanMessage(content=question_text)],
    #     "context": context if context else {}, 
    #     "profile": profile_dict
    # }


    try:
        # 3. LangGraph 실행 (APP.invoke)
        # while loop 없이 한 번만 실행하여 결과를 받아옵니다.
        output = APP.invoke(initial_state)
        
        final_answer = ""
        
        if isinstance(output, dict) and "messages" in output:
            messages = output["messages"]

            for m in reversed(messages):
                if isinstance(m, AIMessage):
                    content = str(m.content)
                    # [supervisor] 메시지나 내부 도구 호출 메시지는 제외
                    if not content.startswith("[supervisor]") and content.strip():
                        final_answer = content
                        break
            
            # 적절한 답변을 못 찾은 경우 안전장치 (마지막 메시지 반환)
            if not final_answer and messages:
                final_answer = str(messages[-1].content)
                
        return final_answer if final_answer else "죄송합니다. 답변을 생성할 수 없습니다."

    except Exception as e:
        print(f"🔴 [AI Error] {e}")
        traceback.print_exc()
        return "시스템 에러가 발생하여 답변을 가져오지 못했습니다."