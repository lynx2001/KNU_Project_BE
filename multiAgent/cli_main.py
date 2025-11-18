import requests
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# 환경 변수에서 Django 접속 정보 읽기
DJANGO_API_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000")
DJANGO_USER = os.environ.get("DJANGO_USER")
DJANGO_PASSWORD = os.environ.get("DJANGO_PASSWORD")

def get_auth_token(username, password):
    """Django 백엔드에 로그인하여 JWT 액세스 토큰을 받습니다."""
    login_url = f"{DJANGO_API_URL}/accounts/login/"
    try:
        res = requests.post(login_url, data={"username": username, "password": password})
        if res.status_code == 200:
            return res.json().get("access") # access 토큰 반환
        else:
            print(f"[ERROR] 로그인 실패: {res.status_code} {res.text}")
            return None
    except requests.RequestException as e:
        print(f"[ERROR] 로그인 API 연결 실패: {e}")
        return None

def get_user_profile(token):
    """JWT 토큰을 헤더에 담아 사용자 프로필을 조회합니다."""
    profile_url = f"{DJANGO_API_URL}/accounts/profile/"
    headers = {
        "Authorization": f"Bearer {token}" # <--- 핵심: Bearer 토큰 사용
    }
    try:
        res = requests.get(profile_url, headers=headers)
        if res.status_code == 200:
            return res.json() # 프로필 데이터(dict) 반환
        else:
            print(f"[ERROR] 프로필 조회 실패: {res.status_code} {res.text}")
            return None
    except requests.RequestException as e:
        print(f"[ERROR] 프로필 API 연결 실패: {e}")
        return None
    
from langchain_core.messages import HumanMessage, AIMessage
from graph_app import APP
import traceback

def main():
    print("=" * 70)
    print("🤖 News Tutor — Foundation (LLM Supervisor Routing)")
    print("=" * 70)

    # ========== [핵심 구현] 시작: 로그인 및 프로필 로드 ==========
    print("로그인 및 프로필 정보 로드 중...")
    initial_profile = {} # 기본 빈 프로필
    if not DJANGO_USER or not DJANGO_PASSWORD:
        print("[WARN] .env에 DJANGO_USER 또는 DJANGO_PASSWORD가 없습니다.")
    else:
        # 1. 로그인하여 토큰 받기
        access_token = get_auth_token(DJANGO_USER, DJANGO_PASSWORD)
        
        if access_token:
            # 2. 토큰으로 프로필 조회하기
            profile_data = get_user_profile(access_token)
            if profile_data:
                initial_profile = profile_data
                print(f"✅ 프로필 로드 성공: {initial_profile.get('grade')}")
            else:
                print("❌ 프로필 로드에 실패했습니다.")
        else:
            print("❌ 로그인에 실패했습니다.")
    # ========== [핵심 구현] 종료 ==========


    # ✅ [수정] 빈 프로필 대신, 위에서 가져온 프로필로 초기화
    current_state = {
        "messages": [],
        "context": {},
        "profile": initial_profile  # <--- 가져온 프로필 정보 주입
    }

    print("Type your message. 'exit' to quit.")
    print("=" * 70)

    while True:
        try:
            q = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not q:
            continue
        if q.lower() in ("exit", "quit"):
            print("Bye!")
            break

        # 1. 사용자 메시지를 현재 State의 메시지 기록에 추가
        current_state["messages"].append(HumanMessage(content=q))

        # ----- 그래프 호출 전: 기존 메시지 길이 기억 -----
        prev_len = len(current_state["messages"])

        # ----- 그래프 호출 -----
        try:
            # ✅ [핵심 수정] messages만 넣는 게 아니라, current_state 전체를 넘깁니다.
            # 그래야 'news_find'가 채워넣은 'context'가 다음 턴에도 유지됩니다.
            out = APP.invoke(current_state)
        except Exception as e:
            print("\n[ERROR] APP.invoke failed:", repr(e))
            traceback.print_exc()
            continue

        print("\nAssistant:")

        # 2. 그래프 실행 결과를 다시 current_state에 덮어씌워 '기억'을 갱신합니다.
        # (여기서 context 안에 있는 selected_articles가 유지됩니다)
        if isinstance(out, dict):
            current_state = out
        else:
            print(" (no dict output) raw:", out)
            continue

        # ----- 이번 턴에 새로 추가된 메시지들만 추출 -----
        # out["messages"]는 전체 대화 기록이므로, 아까 기억한 길이(prev_len) 이후 것만 가져옵니다.
        new_msgs = current_state["messages"][prev_len:]

        # ----- 새로 추가된 AI 메시지들만 출력 (supervisor 제외) -----
        shown = False
        for m in new_msgs:
            # Supervisor나 ToolMessage 등은 숨기고, 실제 AI의 대답만 출력
            if isinstance(m, AIMessage) and not str(m.content).startswith("[supervisor]"):
                print(" ", m.content)
                shown = True

        # 에이전트가 메시지를 남기지 않은 경우 (디버깅용)
        if not shown:
            print(" (no new agent output) debug dump below:")
            for m in new_msgs:
                t = m.__class__.__name__
                c = getattr(m, "content", str(m))
                print(f"  - {t}: {c}")

if __name__ == "__main__":
    main()