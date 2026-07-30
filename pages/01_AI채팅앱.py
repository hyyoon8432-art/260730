import streamlit as st
from openai import OpenAI

# 페이지 기본 설정
st.set_page_config(page_title="AI 정보 교과 선생님", page_icon="🤖", layout="wide")
st.title("🤖 AI 정보 교과 선생님")

# 비밀 금고(secrets)에서 API 키를 꺼내 접속 준비
client = OpenAI(
    api_key=st.secrets["SOLAR_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)

# 과목 목록 및 과목별 맞춤 시스템 프롬프트 설정
SUBJECTS = {
    "고등학교 정보": (
        "너는 고등학교 '정보' 과목을 가르치는 친절한 선생님이야. "
        "컴퓨팅 사고력, 프로그래밍 기초, 데이터 및 정보 표현 등을 쉽고 친절하게 설명해 줘. "
        "어려운 개념은 알기 쉬운 예시를 들고, 반드시 순수 한국어로만 답해줘."
    ),
    "고등학교 인공지능기초": (
        "너는 고등학교 '인공지능기초' 과목을 가르치는 친절한 선생님이야. "
        "머신러닝, 딥러닝, 인공지능 윤리, 사회적 영향 등을 중고등학생 눈높이에 맞춰 설명해 줘. "
        "어려운 용어는 쉬운 말로 풀어서 반드시 순수 한국어로만 답해줘."
    ),
    "고등학교 데이터과학": (
        "너는 고등학교 '데이터과학' 과목을 가르치는 친절한 선생님이야. "
        "데이터 수집, 정제, 분석, 시각화 및 인사이트 도출 과정을 친절하게 설명해 줘. "
        "실생활 데이터 활용 예시를 적극 활용하고, 반드시 순수 한국어로만 답해줘."
    ),
    "고등학교 정보과학": (
        "너는 고등학교 '정보과학' 과목을 가르치는 친절한 선생님이야. "
        "알고리즘, 자료구조, 컴퓨터 아키텍처 등 깊이 있는 컴퓨터 과학 개념을 친절하게 설명해 줘. "
        "원리를 체계적이고 알기 쉽게 풀어쓰며, 반드시 순수 한국어로만 답해줘."
    )
}

# session_state에 과목별 대화 기록 세션 초기화
if "subject_messages" not in st.session_state:
    st.session_state.subject_messages = {
        subject: [{"role": "system", "content": prompt}]
        for subject, prompt in SUBJECTS.items()
    }

# 제목 아랫줄에 과목 선택 탭 생성
tabs = st.tabs(list(SUBJECTS.keys()))

# 탭별 독립적인 채팅 UI 및 로직 생성
for tab, (subject_name, system_prompt) in zip(tabs, SUBJECTS.items()):
    with tab:
        st.subheader(f"📖 {subject_name} 채팅창")
        
        # 현재 과목의 대화 기록 불러오기
        current_messages = st.session_state.subject_messages[subject_name]

        # 이전 대화 내용 그리기 (system 메시지 제외)
        for msg in current_messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 과목별 독립 입력창 (key 값으로 구분 필수)
        user_input = st.chat_input(
            f"[{subject_name}] 궁금한 것을 물어보세요!", 
            key=f"chat_input_{subject_name}"
        )

        if user_input:
            # 사용자 메시지 기록 추가 및 출력
            current_messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # AI 응답 받아오기 및 스트리밍 출력
            with st.chat_message("assistant"):
                try:
                    stream = client.chat.completions.create(
                        model="solar-open2",
                        messages=current_messages, # 해당 과목의 대화 히스토리만 전달
                        reasoning_effort="none",
                        stream=True,
                    )
                    
                    answer = st.write_stream(
                        chunk.choices[0].delta.content or ""
                        for chunk in stream 
                        if chunk.choices and chunk.choices[0].delta.content
                    )
                    
                    if answer:
                        current_messages.append({"role": "assistant", "content": answer})
                        
                except Exception as e:
                    # 실패 시 방금 입력한 사용자 질문 제거하여 상태 복구
                    current_messages.pop()
                    st.error("응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.")
