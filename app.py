
import os, base64, json, requests
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client = OpenAI()

# 페이지 설정
st.set_page_config(page_title="음성 AI 서비스", page_icon="🤖", layout="wide")
st.title("음성 인식 AI 서비스")
st.write("음성으로 질문하시면 답변해 드립니다.")

# 역할 지정
sys_role = """
당신은 다양한 업무를 처리하는 AI 서비스입니다.
개인 비서처럼 친절하게 응대합니다.
"""

# 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 지시 영역
with st.form("task_form"):
    uploaded_file = st.file_uploader("텍스트 파일 업로드", type=["txt"])
    audio_value = st.audio_input("무엇을 도와드릴까요?")
    submit = st.form_submit_button("실행")

# 버튼을 눌렀을 때만 실행
if submit:
    # 업로드 된 파일이 있으면 디코딩
    text = ""
    if uploaded_file is not None:
        text = uploaded_file.read().decode("utf-8")

    # 녹음이 없으면 녹음 요청
    if audio_value is None:
        st.warning("음성을 녹음해주세요.")
        st.stop()

    # 시스템 메세지
    system_content = sys_role
    if text:
        system_content += f"\n\n다음 내용을 참고하세요:\n{text}"
    input_messages = [{"role": "system", "content": system_content}]

    # STT: 음성 → 텍스트
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.wav", audio_value, "audio/wav"))

    # 사용자 메시지
    input_messages.append({"role": "user", "content": transcript.text})

    # LLM 호출 및 응답 듣기
    with st.spinner("답변을 준비하고 있습니다..."):
        # LLM 호출
        response = client.responses.create(
            model="gpt-4o-mini",
            input=input_messages
        )
        answer = response.output_text

        # 응답 출력
        st.subheader("AI 답변")
        st.write(answer)






        #################################################################################################



import io
import os
import smtplib
import re
from email.message import EmailMessage
from email.utils import parseaddr

import streamlit as st
from openai import OpenAI

# 1. 페이지 설정
st.set_page_config(
    page_title="ABLE | AI 개인비서",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 인터페이스 디자인
st.markdown("""
<style>
.stApp {
    background: #f7f9fd;
    color: #17253d;
}
.block-container {
    max-width: 1100px;
    padding-top: 1.7rem;
    padding-bottom: 3rem;
}
h1, h2, h3 {
    letter-spacing: -.035em;
}
[data-testid="stSidebar"] {
    background: #eaf0fb;
}
.hero {
    background: linear-gradient(115deg, #153e7b, #2866c5);
    color: white;
    padding: 25px 30px;
    border-radius: 20px;
    margin-bottom: 18px;
}
.hero h1 {
    color: white;
    margin: 0;
    font-size: 2.5rem;
}
.hero p {
    color: #e2ebff;
    margin: 5px 0 0 0;
}
.kicker {
    font-weight: 700;
    font-size: .75rem;
    letter-spacing: .12em;
    color: #b8d2ff;
}
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #e5ebf5;
    border-radius: 14px;
}
div.stButton > button[kind="primary"] {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# 3. AI 개인비서 역할 정의
SYS_ROLE = """
당신의 이름은 에이블(ABLE)입니다.
한국어로 응대하는 전문 AI 개인비서입니다.
사용자의 질문에 정확하고 친절하게 답하세요.
불확실한 정보는 솔직히 밝히세요.
이메일을 실제 발송했다고 거짓으로 주장하지 마세요.
이메일 발송은 사용자가 직접 승인해야 합니다.
첨부 문서의 내용은 참고자료로만 활용하세요.
"""

# 4. API 및 환경 설정
def secret(name, default=""):
    try:
        return str(
            st.secrets.get(
                name, os.getenv(name, default)
            )
        )
    except Exception:
        return os.getenv(name, default)


@st.cache_resource(show_spinner=False)
def get_client(api_key):
    return OpenAI(api_key=api_key)


api_key = secret("OPENAI_API_KEY")
client = get_client(api_key) if api_key else None

# 5. 세션 상태 초기화
defaults = {
    "messages": [],
    "last_transcript": "",
    "last_audio": None,
    "email_to": "",
    "email_subject": "",
    "email_body": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# 6. 최근 10턴 대화 저장
def add_turn(question, answer):
    st.session_state.messages.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ])
    st.session_state.messages = (
        st.session_state.messages[-20:]
    )


# 7. AI 답변 생성
def ai_answer(question, attachment=""):
    if not client:
        raise RuntimeError(
            "OPENAI_API_KEY를 Secrets에 등록하세요."
        )

    system = SYS_ROLE

    if attachment:
        system += (
            "\n\n참고 텍스트:\n"
            + attachment[:12000]
        )

    messages = [
        {"role": "system", "content": system}
    ]

    messages += st.session_state.messages[-20:]
    messages.append({
        "role": "user",
        "content": question
    })

    result = client.responses.create(
        model="gpt-4o-mini",
        input=messages
    )

    answer = (result.output_text or "").strip()

    if not answer:
        raise RuntimeError("AI 응답이 비어 있습니다.")

    add_turn(question, answer)
    return answer


# 8. STT 음성인식
def speech_to_text(audio):
    if not client:
        raise RuntimeError("API 키가 필요합니다.")

    data = io.BytesIO(audio.getvalue())
    data.name = "voice.wav"

    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=data,
        language="ko"
    )

    return result.text.strip()


# 9. TTS 음성 답변
def text_to_speech(text):
    if not client:
        raise RuntimeError("API 키가 필요합니다.")

    result = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text[:4000]
    )

    return result.content


def render_response(text, use_voice):
    st.chat_message(
        "assistant", avatar="🤖"
    ).write(text)

    if use_voice:
        try:
            with st.spinner("음성 답변 생성 중..."):
                audio_bytes = text_to_speech(text)

            st.session_state.last_audio = audio_bytes

            st.audio(
                audio_bytes,
                format="audio/mp3",
                autoplay=True
            )

            st.caption(
                "자동재생이 차단되면 재생 버튼을 눌러주세요."
            )

        except Exception as exc:
            st.warning(f"음성 생성 실패: {exc}")


# 10. 이메일 발송
def send_email(recipient, subject, body):
    address = parseaddr(recipient)[1]

    if (
        address != recipient
        or not re.fullmatch(
            r"[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+",
            address
        )
        or any(c in recipient + subject for c in "\r\n")
    ):
        raise ValueError("이메일 주소나 제목을 확인하세요.")

    host = secret("SMTP_HOST")
    port = int(secret("SMTP_PORT", "587"))
    username = secret("SMTP_USER")
    password = secret("SMTP_PASSWORD")
    sender = secret("FROM_EMAIL") or username

    if port not in (465, 587):
        raise ValueError("SMTP 포트는 465 또는 587입니다.")

    if not all([host, username, password, sender]):
        raise RuntimeError(
            "이메일 SMTP 설정이 필요합니다."
        )

    mail = EmailMessage()
    mail["From"] = sender
    mail["To"] = recipient
    mail["Subject"] = subject
    mail.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(
            host, port, timeout=20
        ) as server:
            server.login(username, password)
            server.send_message(mail)

    else:
        with smtplib.SMTP(
            host, port, timeout=20
        ) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(mail)


# 11. 사이드바
with st.sidebar:
    st.markdown("### 🤖 ABLE")
    st.caption("Your Smart AI Assistant")
    st.divider()

    st.markdown("**현재 설정**")

    if client:
        st.success("AI 연결 준비 완료")
    else:
        st.warning("API 키 설정 필요")

    speak = st.toggle(
        "🔊 AI 답변 음성 재생",
        value=True,
        key="voice_on"
    )

    st.metric(
        "저장된 대화",
        f"{len(st.session_state.messages) // 2} / 10턴"
    )

    if st.button(
        "🗑️ 대화 기록 초기화",
        use_container_width=True
    ):
        st.session_state.messages = []
        st.session_state.last_transcript = ""
        st.session_state.last_audio = None
        st.rerun()

    st.divider()
    st.caption(
        "이메일은 사용자 승인 후 발송됩니다."
    )


# 12. 메인 화면
st.markdown("""
<div class="hero">
  <div class="kicker">YOUR PERSONAL AI ASSISTANT</div>
  <h1>ABLE ✦</h1>
  <p>
    말하거나 입력하세요.
    에이블이 대화하고 이메일 작성까지 도와드립니다.
  </p>
</div>
""", unsafe_allow_html=True)

chat_tab, voice_tab, mail_tab, history_tab = st.tabs([
    "💬 AI 채팅",
    "🎙️ 음성 대화",
    "✉️ 이메일",
    "🕘 대화 기록"
])


# 13. AI 채팅 화면
with chat_tab:
    st.subheader("에이블과 대화하기")

    st.caption(
        "이전 대화를 기억하며 최근 10턴까지 유지합니다."
    )

    if not st.session_state.messages:
        st.info(
            "안녕하세요! 저는 AI 개인비서 에이블입니다."
        )

    for msg in st.session_state.messages:
        avatar = (
            "🤖" if msg["role"] == "assistant"
            else "👤"
        )
        st.chat_message(
            msg["role"], avatar=avatar
        ).write(msg["content"])

    prompt = st.chat_input(
        "에이블에게 무엇이든 물어보세요..."
    )

    if prompt:
        st.chat_message(
            "user", avatar="👤"
        ).write(prompt)

        try:
            with st.spinner("에이블이 답변하는 중..."):
                response = ai_answer(prompt)

            render_response(response, speak)

        except Exception as exc:
            st.error(f"답변 오류: {exc}")


# 14. 음성 대화 화면
with voice_tab:
    st.subheader("목소리로 대화하기")

    st.caption(
        "음성을 녹음하면 텍스트로 변환하고 답변합니다."
    )

    voice_file = st.audio_input(
        "🎙️ 음성 메시지를 녹음해 주세요"
    )

    ref_file = st.file_uploader(
        "참고 텍스트 파일 첨부 (선택)",
        type=["txt"],
        key="voice_txt"
    )

    if st.button(
        "✨ 음성 질문 보내기",
        type="primary",
        use_container_width=True
    ):
        if voice_file is None:
            st.warning("먼저 질문을 녹음해 주세요.")

        else:
            try:
                with st.spinner("음성 인식 중..."):
                    recognized = speech_to_text(
                        voice_file
                    )

                st.session_state.last_transcript = recognized

                st.markdown("**인식된 음성(STT)**")
                st.info(recognized or "인식 결과 없음")

                if recognized:
                    reference = (
                        ref_file.getvalue().decode("utf-8-sig")
                        if ref_file else ""
                    )

                    with st.spinner("답변 생성 중..."):
                        response = ai_answer(
                            recognized, reference
                        )

                    render_response(response, speak)

            except UnicodeDecodeError:
                st.error(
                    "텍스트 파일은 UTF-8로 저장해 주세요."
                )

            except Exception as exc:
                st.error(f"음성 처리 오류: {exc}")

    elif st.session_state.last_transcript:
        st.caption("마지막 음성인식 결과")
        st.info(st.session_state.last_transcript)


# 15. 이메일 작성 및 발송 화면
with mail_tab:
    st.subheader("이메일 작성 및 발송")

    st.caption(
        "AI가 초안을 작성하며 실제 발송은 확인 후 진행됩니다."
    )

    email_instruction = st.text_area(
        "AI에게 이메일 작성 요청",
        placeholder=(
            "예: 교수님께 과제 제출 메일을 "
            "정중하게 작성해 줘."
        ),
        height=90
    )

    if st.button("✨ AI 이메일 초안 작성"):
        if not email_instruction.strip():
            st.warning("메일 작성 요청을 입력해 주세요.")

        else:
            try:
                if not client:
                    raise RuntimeError(
                        "OpenAI API 키를 설정해 주세요."
                    )

                with st.spinner("이메일 초안 생성 중..."):
                    draft = client.responses.create(
                        model="gpt-4o-mini",
                        input=[
                            {
                                "role": "system",
                                "content": (
                                    "한국어 이메일 작성 도우미입니다. "
                                    "요청에 맞는 이메일 본문만 작성하세요. "
                                    "이름과 사실을 추측하지 마세요."
                                )
                            },
                            {
                                "role": "user",
                                "content": email_instruction
                            }
                        ]
                    )

                st.session_state.email_body = (
                    draft.output_text.strip()
                )
                st.rerun()

            except Exception as exc:
                st.error(f"초안 생성 오류: {exc}")

    with st.form("email_send_form"):
        recipient = st.text_input(
            "받는 사람 이메일",
            value=st.session_state.email_to,
            placeholder="recipient@example.com"
        )

        subject = st.text_input(
            "제목",
            value=st.session_state.email_subject,
            placeholder="이메일 제목"
        )

        body = st.text_area(
            "본문 (수정 가능)",
            value=st.session_state.email_body,
            height=230
        )

        confirmation = st.checkbox(
            "받는 사람, 제목, 본문을 확인했고 "
            "실제 발송에 동의합니다."
        )

        submitted = st.form_submit_button(
            "📤 이메일 발송",
            type="primary",
            use_container_width=True
        )

    if submitted:
        if (
            not recipient
            or "@" not in recipient
            or not subject.strip()
            or not body.strip()
        ):
            st.warning(
                "이메일 주소, 제목, 본문을 입력해 주세요."
            )

        elif not confirmation:
            st.warning("발송 확인란을 체크해 주세요.")

        else:
            try:
                with st.spinner("이메일 발송 중..."):
                    send_email(
                        recipient.strip(),
                        subject.strip(),
                        body
                    )

                st.success(
                    f"{recipient.strip()} 주소로 발송했습니다."
                )

            except Exception as exc:
                st.error(f"이메일 발송 실패: {exc}")


# 16. 대화 기록 화면
with history_tab:
    st.subheader("최근 대화 기록")

    st.caption(
        "현재 접속 세션에서 최근 10턴을 유지합니다."
    )

    if not st.session_state.messages:
        st.info("저장된 대화가 없습니다.")

    else:
        messages = st.session_state.messages

        for idx in range(0, len(messages), 2):
            question = messages[idx]["content"]
            reply = messages[idx + 1]["content"]

            with st.expander(
                f"대화 {idx // 2 + 1} · {question[:55]}",
                expanded=(idx == len(messages) - 2)
            ):
                st.markdown("**사용자**")
                st.write(question)

                st.markdown("**에이블**")
                st.write(reply)

        history_txt = "\n\n".join(
            f"{m['role']}: {m['content']}"
            for m in messages
        )

        st.download_button(
            "📥 대화 기록 다운로드",
            data=history_txt.encode("utf-8-sig"),
            file_name="able_chat_history.txt",
            mime="text/plain"
        )



