"""
Scene Builder - AI 연기 대본 생성 앱
2단계: Gemini API 연결 + 대본 생성
"""

import streamlit as st
import random
import os
import requests
from dotenv import load_dotenv

# 로컬은 .env에서, 배포 환경은 Streamlit secrets에서 API 키 로드
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

# ─────────────────────────────────────────
# 페이지 기본 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Scene Builder",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# 커스텀 CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #1a1a2e; color: #e0e0e0; }

    .team-card {
        background: linear-gradient(135deg, #16213e, #0f3460);
        border: 1px solid #e94560;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 10px 0;
    }
    .team-card h3 { color: #e94560; margin: 0 0 8px 0; font-size: 1.1rem; }

    .member-badge {
        display: inline-block;
        background-color: #0f3460;
        border: 1px solid #e94560;
        color: #ffffff;
        border-radius: 20px;
        padding: 4px 14px;
        margin: 4px 4px;
        font-size: 0.95rem;
    }

    .result-header {
        text-align: center;
        color: #e94560;
        font-size: 1.4rem;
        font-weight: bold;
        margin-bottom: 12px;
    }

    .monologue-card {
        background: linear-gradient(135deg, #2d1b69, #11998e);
        border: 1px solid #38ef7d;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
    }

    /* 대본 출력 박스 */
    .script-box {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 28px 32px;
        margin-top: 16px;
        font-family: 'Noto Serif KR', Georgia, serif;
        font-size: 1rem;
        line-height: 1.9;
        white-space: pre-wrap;
        color: #e6edf3;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# 팀 나누기 로직
# ─────────────────────────────────────────
def split_into_teams(names: list[str]) -> dict:
    n = len(names)

    if n == 1:
        return {"mode": "monologue", "teams": [names]}

    mode = random.choice(["ensemble", "unit"])

    if mode == "ensemble" or n == 2:
        return {"mode": "ensemble", "teams": [names]}

    shuffled = names.copy()
    random.shuffle(shuffled)
    split_point = random.randint(1, n - 1)
    return {"mode": "unit", "teams": [shuffled[:split_point], shuffled[split_point:]]}


# ─────────────────────────────────────────
# Gemini 대본 생성 함수
# ─────────────────────────────────────────
def build_prompt(result: dict, genre: str, mood: str, situation: str) -> str:
    """팀 배정 결과와 설정값으로 Gemini 프롬프트를 구성합니다."""

    mode = result["mode"]
    teams = result["teams"]

    # 출연진 정보 텍스트 구성
    if mode == "monologue":
        cast_info = f"1인 독백 — 출연자: {teams[0][0]}"
        scene_type = "독백 씬 (혼자 말하는 내면 독백 또는 관객에게 말하는 방식)"
    elif mode == "ensemble":
        members = ", ".join(teams[0])
        cast_info = f"전체 앙상블 — 출연자: {members}"
        scene_type = "앙상블 씬 (모든 출연자가 함께 등장)"
    else:
        team_texts = []
        for i, team in enumerate(teams):
            team_texts.append(f"팀 {chr(65+i)}: {', '.join(team)}")
        cast_info = " / ".join(team_texts)
        scene_type = "유닛 분할 씬 (각 팀이 별개의 장면에서 등장, 팀별로 나누어 작성)"

    prompt = f"""
당신은 전문 연기 대본 작가입니다. 아래 조건에 맞는 연기 연습용 단막극 대본을 작성해주세요.

[조건]
- 장르: {genre}
- 분위기: {mood}
- 상황 설정: {situation}
- 씬 유형: {scene_type}
- 출연진: {cast_info}

[작성 규칙]
1. 대본은 반드시 한국어로 작성합니다.
2. 출연자 이름을 그대로 캐릭터 이름으로 사용합니다.
3. 형식은 아래처럼 "이름: 대사" 형태로 작성합니다.
4. 지문(행동 묘사)은 *(별표)로 감쌉니다. 예: *문을 열며*
5. 전체 분량은 A4 한 페이지 분량(약 20~30줄)으로 작성합니다.
6. 대본 앞에 씬 제목과 간단한 배경 설명(2~3줄)을 넣어주세요.
7. 유닛 분할인 경우 팀별로 구분선(───)을 넣어 각 팀의 씬을 분리해주세요.

지금 바로 대본을 작성해주세요.
""".strip()

    return prompt


def generate_script(result: dict, genre: str, mood: str, situation: str) -> str:
    """Gemini REST API를 직접 호출해 대본을 생성합니다."""
    prompt = build_prompt(result, genre, mood, situation)
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_URL, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


# ─────────────────────────────────────────
# 팀 배정 결과 카드 렌더링
# ─────────────────────────────────────────
def render_team_result(result: dict):
    mode = result["mode"]
    teams = result["teams"]

    mode_labels = {
        "monologue": "🎤 독백 모드",
        "ensemble": "🎭 전체 앙상블",
        "unit": "⚡ 유닛 분할",
    }
    mode_descriptions = {
        "monologue": "혼자만의 무대! 독백 씬을 연습합니다.",
        "ensemble": "모두 함께! 앙상블 장면을 연습합니다.",
        "unit": "팀을 나눠 서로 다른 씬을 연습합니다.",
    }

    st.markdown(f'<div class="result-header">{mode_labels[mode]}</div>', unsafe_allow_html=True)
    st.caption(mode_descriptions[mode])
    st.divider()

    if mode == "monologue":
        name = teams[0][0]
        st.markdown(f"""
        <div class="monologue-card">
            <h2 style="color:#38ef7d; margin:0;">🌟 {name}</h2>
            <p style="color:#cccccc; margin-top:8px;">솔로 퍼포먼스 — 당신만의 무대입니다</p>
        </div>
        """, unsafe_allow_html=True)

    elif mode == "ensemble":
        members_html = "".join(f'<span class="member-badge">🎭 {m}</span>' for m in teams[0])
        st.markdown(f"""
        <div class="team-card">
            <h3>앙상블 팀 전체</h3>
            {members_html}
        </div>
        """, unsafe_allow_html=True)

    else:
        team_icons = ["🔴", "🔵", "🟢", "🟡"]
        cols = st.columns(len(teams))
        for idx, (col, team) in enumerate(zip(cols, teams)):
            with col:
                icon = team_icons[idx % len(team_icons)]
                members_html = "".join(f'<span class="member-badge">{m}</span>' for m in team)
                st.markdown(f"""
                <div class="team-card">
                    <h3>{icon} 팀 {chr(65 + idx)} &nbsp;·&nbsp; {len(team)}명</h3>
                    {members_html}
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────
with st.sidebar:
    st.title("🎭 Scene Builder")
    st.caption("AI 연기 대본 생성기")
    st.divider()

    # ── 인원 설정 ──
    st.subheader("👥 참여 인원 설정")
    num_people = st.slider("참여 인원수", min_value=1, max_value=6, value=2, step=1,
                           help="1명은 독백, 2명 이상은 앙상블 또는 유닛 분할로 진행됩니다.")
    st.divider()

    # ── 이름 입력 ──
    st.subheader("✍️ 이름 입력")
    names = []
    for i in range(num_people):
        name = st.text_input(
            label=f"참여자 {i + 1}",
            value=f"배우{i + 1}",
            placeholder=f"참여자 {i + 1} 이름",
            key=f"name_{i}",
        )
        names.append(name.strip() if name.strip() else f"참여자{i + 1}")

    st.divider()

    # ── 대본 설정 ──
    st.subheader("🎬 대본 설정")

    genre = st.selectbox(
        "장르",
        ["드라마", "로맨스", "스릴러", "코미디", "SF", "판타지", "역사극"],
        help="생성될 대본의 장르를 선택합니다.",
    )

    mood = st.selectbox(
        "분위기",
        ["긴장감 있는", "따뜻한", "유머러스한", "슬픈", "신비로운", "격렬한"],
        help="씬의 전반적인 분위기를 선택합니다.",
    )

    situation = st.text_area(
        "상황 설정",
        value="카페에서 오랜 친구를 우연히 만났다.",
        placeholder="예: 병원 복도에서 가족이 수술 결과를 기다리고 있다.",
        height=80,
        help="대본의 배경 상황을 직접 입력하세요.",
    )

    st.divider()

    # ── 버튼 ──
    split_btn = st.button("🎲 팀 나누기", use_container_width=True, type="primary")
    st.caption("버튼을 누를 때마다 새로운 배정이 이루어집니다.")


# ─────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────
st.title("🎭 Scene Builder")
st.markdown("취미 연기 스터디를 위한 **AI 맞춤형 대본 생성기**")
st.divider()

if split_btn:
    if not all(names):
        st.warning("⚠️ 모든 참여자의 이름을 입력해 주세요.")
    else:
        # 팀 배정 실행 및 결과를 세션에 저장 (대본 생성 버튼 클릭 시도 유지)
        st.session_state["team_result"] = split_into_teams(names)
        st.session_state["script"] = None  # 팀 바뀌면 기존 대본 초기화

# 팀 배정 결과가 있으면 표시
if "team_result" in st.session_state and st.session_state["team_result"]:
    result = st.session_state["team_result"]
    render_team_result(result)

    st.divider()

    # 대본 생성 버튼
    gen_btn = st.button("📝 AI 대본 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        with st.spinner("✍️ Gemini AI가 대본을 작성 중입니다..."):
            try:
                script_text = generate_script(result, genre, mood, situation)
                st.session_state["script"] = script_text
            except Exception as e:
                st.error(f"대본 생성 중 오류가 발생했습니다: {e}")

    # 생성된 대본 표시
    if st.session_state.get("script"):
        st.subheader("📄 생성된 대본")
        st.markdown(
            f'<div class="script-box">{st.session_state["script"]}</div>',
            unsafe_allow_html=True,
        )

        # 대본 다운로드 버튼
        st.download_button(
            label="⬇️ 대본 다운로드 (.txt)",
            data=st.session_state["script"].encode("utf-8"),
            file_name="scene_builder_script.txt",
            mime="text/plain",
            use_container_width=True,
        )

else:
    # 초기 안내 화면
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        #### 1️⃣ 인원 설정
        사이드바에서 참여 인원수를
        슬라이더로 선택하세요.
        """)
    with col2:
        st.markdown("""
        #### 2️⃣ 대본 설정
        장르, 분위기, 상황을
        사이드바에서 설정하세요.
        """)
    with col3:
        st.markdown("""
        #### 3️⃣ 생성하기
        팀 나누기 → AI 대본 생성
        버튼을 순서대로 누르세요.
        """)

    st.divider()
    st.markdown("""
    > **Scene Builder**는 취미 연기 스터디 그룹을 위한 대본 생성 앱입니다.
    > 왼쪽 사이드바에서 인원과 설정을 완료하고 **🎲 팀 나누기** 버튼을 눌러보세요!
    """)
