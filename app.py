"""
Scene Builder - AI 연기 대본 생성 앱
"""

import streamlit as st
import random
import re
import os
import time
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ─────────────────────────────────────────
# 환경 설정
# ─────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)
HISTORY_FILE = Path(__file__).parent / "history.json"

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
# API 키 확인 (시작 시)
# ─────────────────────────────────────────
if not GEMINI_API_KEY:
    st.error(
        "⚠️ **GEMINI_API_KEY가 설정되지 않았습니다.**\n\n"
        "프로젝트 폴더의 `.env` 파일에 아래와 같이 추가해주세요:\n"
        "```\nGEMINI_API_KEY=여기에_키_입력\n```\n"
        "키 발급: https://aistudio.google.com"
    )
    st.stop()

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

    .director-box {
        background-color: #0d1117;
        border: 1px solid #e94560;
        border-radius: 12px;
        padding: 24px 28px;
        margin-top: 16px;
        font-family: 'Noto Serif KR', Georgia, serif;
        font-size: 0.97rem;
        line-height: 1.85;
        color: #e6edf3;
    }
    .director-box h4 {
        color: #e94560;
        margin: 16px 0 6px 0;
        font-size: 1rem;
    }
    .director-box h4:first-child { margin-top: 0; }

    .script-box {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 28px 32px;
        margin-top: 16px;
        font-family: 'Noto Serif KR', Georgia, serif;
        line-height: 1.9;
        white-space: pre-wrap;
        color: #e6edf3;
    }
    .script-box .stage-dir {
        color: #f0a500;
        font-weight: bold;
    }
    .script-box .line-num {
        color: #484f58;
        font-size: 0.78em;
        user-select: none;
        margin-right: 10px;
        font-family: monospace;
    }

    .script-box-sm {
        background-color: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px 20px;
        font-family: 'Noto Serif KR', Georgia, serif;
        font-size: 0.88rem;
        line-height: 1.7;
        white-space: pre-wrap;
        color: #adbac7;
        max-height: 300px;
        overflow-y: auto;
    }

    .warn-badge {
        background-color: #3d2000;
        border: 1px solid #f0a500;
        border-radius: 8px;
        padding: 8px 14px;
        color: #f0a500;
        font-size: 0.9rem;
        margin: 8px 0;
    }

    /* 모바일 대응 */
    @media (max-width: 768px) {
        .script-box {
            padding: 16px 14px;
            font-size: 0.95rem;
        }
        .member-badge {
            font-size: 0.85rem;
            padding: 3px 10px;
        }
        .result-header { font-size: 1.1rem; }
        [data-testid="stSidebar"] { min-width: 260px !important; }
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# 세션 초기화
# ─────────────────────────────────────────
def init_session():
    defaults = {
        "team_result": None,
        "script": None,
        "script_stack": [],
        "script_history": [],
        "script_alt": None,
        "director_report": None,
        "font_size": 16,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ─────────────────────────────────────────
# 히스토리 영구 저장 / 불러오기
# ─────────────────────────────────────────
def load_history_file() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_history_file(history: list):
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def save_to_history(script: str, genre: str, mood: str):
    entry = {
        "script": script,
        "label": f"{genre} / {mood}  ({datetime.now().strftime('%m-%d %H:%M')})",
        "ts": datetime.now().isoformat(),
    }
    history = st.session_state["script_history"]
    history.insert(0, entry)
    history = history[:10]  # 세션 내 최대 10개
    st.session_state["script_history"] = history

    # 파일에도 동기화 (최대 30개)
    file_history = load_history_file()
    file_history.insert(0, entry)
    save_history_file(file_history[:30])


# 앱 시작 시 파일 히스토리를 세션에 병합 (세션이 비어있을 때만)
if not st.session_state["script_history"]:
    st.session_state["script_history"] = load_history_file()[:10]


# ─────────────────────────────────────────
# PDF 생성
# ─────────────────────────────────────────
def generate_pdf(script: str, genre: str, mood: str) -> bytes | None:
    if not PDF_AVAILABLE:
        return None
    try:
        pdf = FPDF()
        pdf.add_page()
        # Windows 맑은 고딕, macOS AppleGothic 순으로 시도
        font_candidates = [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\gulim.ttc",
            "/System/Library/Fonts/AppleGothic.ttf",
        ]
        font_loaded = False
        for fp in font_candidates:
            if os.path.exists(fp):
                pdf.add_font("KR", "", fp)
                pdf.set_font("KR", size=11)
                font_loaded = True
                break
        if not font_loaded:
            pdf.set_font("Helvetica", size=11)

        pdf.set_title(f"Scene Builder — {genre} / {mood}")
        pdf.set_margins(20, 20, 20)
        pdf.set_auto_page_break(auto=True, margin=20)

        # 줄 번호 포함 출력
        lines = script.split("\n")
        for i, line in enumerate(lines, 1):
            numbered_line = f"{i:3d}  {line}"
            pdf.multi_cell(0, 7, numbered_line)

        return bytes(pdf.output())
    except Exception:
        return None


# ─────────────────────────────────────────
# API 호출 (재시도 포함)
# ─────────────────────────────────────────
def call_gemini(prompt: str, retries: int = 3) -> str:
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(GEMINI_URL, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.HTTPError as e:
            last_error = e
            if response.status_code == 429:
                time.sleep(2 ** attempt)
            else:
                raise
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_error


# ─────────────────────────────────────────
# 팀 나누기 로직
# ─────────────────────────────────────────
def split_into_teams(names: list[str], mode_preset: str = "랜덤", team_a_size: int = None) -> dict:
    n = len(names)

    if n == 1:
        return {"mode": "monologue", "teams": [names]}

    if mode_preset == "앙상블" or n == 2:
        return {"mode": "ensemble", "teams": [names]}

    if mode_preset == "유닛 분할":
        shuffled = names.copy()
        random.shuffle(shuffled)
        sp = team_a_size if team_a_size is not None else random.randint(1, n - 1)
        sp = max(1, min(sp, n - 1))
        return {"mode": "unit", "teams": [shuffled[:sp], shuffled[sp:]]}

    mode = random.choice(["ensemble", "unit"])
    if mode == "ensemble":
        return {"mode": "ensemble", "teams": [names]}

    shuffled = names.copy()
    random.shuffle(shuffled)
    split_point = random.randint(1, n - 1)
    return {"mode": "unit", "teams": [shuffled[:split_point], shuffled[split_point:]]}


# ─────────────────────────────────────────
# 대본 품질 검증
# ─────────────────────────────────────────
def validate_script(script: str, result: dict) -> list[str]:
    warnings = []
    all_characters = [name for team in result["teams"] for name in team]
    for char in all_characters:
        if char not in script:
            warnings.append(f"'{char}'의 대사가 대본에서 발견되지 않았습니다.")
    if script.count("(") < 2:
        warnings.append("행동지문(괄호)이 거의 없습니다. AI가 형식 지시를 무시했을 수 있습니다.")
    return warnings


# ─────────────────────────────────────────
# Gemini 프롬프트 / 생성 함수
# ─────────────────────────────────────────
def build_prompt(result: dict, genre: str, mood: str, situation: str,
                 script_lines: int = 5, monologue_type: str = "내면 독백",
                 variation_hint: str = "") -> str:
    mode = result["mode"]
    teams = result["teams"]

    if mode == "monologue":
        cast_info = f"1인 독백 — 출연자: {teams[0][0]}"
        scene_type = (
            f"내면 독백 씬 (인물의 내면 생각과 감정을 말하는 방식)"
            if monologue_type == "내면 독백"
            else "관객 독백 씬 (관객에게 직접 말을 거는 방식)"
        )
        lines_rule = f"독백 대사를 정확히 {script_lines}개 작성합니다."
    elif mode == "ensemble":
        members = ", ".join(teams[0])
        cast_info = f"전체 앙상블 — 출연자: {members}"
        scene_type = "앙상블 씬 (모든 출연자가 함께 등장)"
        lines_rule = f"각 캐릭터가 정확히 {script_lines}번씩 대사를 주고받는 분량으로 작성합니다."
    else:
        team_texts = [f"팀 {chr(65+i)}: {', '.join(team)}" for i, team in enumerate(teams)]
        cast_info = " / ".join(team_texts)
        scene_type = "유닛 분할 씬 (각 팀이 별개의 장면에서 등장, 팀별로 나누어 작성)"
        lines_rule = f"각 캐릭터가 정확히 {script_lines}번씩 대사를 주고받는 분량으로 작성합니다."

    variation_line = f"\n- 창작 방향 힌트: {variation_hint}" if variation_hint else ""

    return f"""
당신은 전문 연기 대본 작가입니다. 아래 조건에 맞는 연기 연습용 단막극 대본을 작성해주세요.

[조건]
- 장르: {genre}
- 분위기: {mood}
- 상황 설정: {situation}
- 씬 유형: {scene_type}
- 출연진: {cast_info}{variation_line}

[작성 규칙]
1. 대본은 반드시 한국어로 작성합니다.
2. 출연자 이름을 그대로 캐릭터 이름으로 사용합니다.
3. 형식은 아래처럼 "이름: 대사" 형태로 작성합니다.
4. 지문(행동 묘사)은 반드시 괄호( )로 감쌉니다. 예: (문을 열며), (잠시 침묵하며), (테이블을 주먹으로 치며)
5. {lines_rule}
6. 대본 앞에 씬 제목과 간단한 배경 설명(2~3줄)을 넣어주세요.
7. 유닛 분할인 경우 팀별로 구분선(───)을 넣어 각 팀의 씬을 분리해주세요.

지금 바로 대본을 작성해주세요.
""".strip()


def generate_script(result, genre, mood, situation, script_lines=5,
                    monologue_type="내면 독백", variation_hint="") -> str:
    prompt = build_prompt(result, genre, mood, situation, script_lines, monologue_type, variation_hint)
    return call_gemini(prompt)


def generate_director_report(script: str, result: dict) -> str:
    cast_str = ", ".join(name for team in result["teams"] for name in team)
    prompt = f"""
당신은 전문 연기 디렉터입니다. 아래 대본을 분석해 배우들을 위한 연기 가이드를 작성해주세요.

[대본]
{script}

[출연진]
{cast_str}

[작성 규칙]
1. 반드시 한국어로 작성합니다.
2. 아래 세 항목을 순서대로 작성합니다.
3. 간결하고 실용적으로 작성합니다.

## 인물별 목표 (Objective)
각 인물이 이 씬에서 얻으려는 것을 1~2문장으로 설명합니다.
형식: 인물명 — 목표 설명

## 감정 곡선 (Beats)
씬 안에서 감정이 전환되는 결정적 지점을 3~5개 짚어줍니다.
형식: Beat N — (어떤 대사/행동 이후) → 감정 변화 설명

## 미장센 제안
실제 연기 시 활용할 수 있는 소품, 동선, 공간 배치를 3가지 추천합니다.
형식: 번호. 제안 내용

지금 바로 작성해주세요.
""".strip()
    return call_gemini(prompt)


def generate_retake(script: str, retake_instruction: str) -> str:
    prompt = f"""
당신은 전문 연기 대본 작가입니다. 아래 원본 대본을 주어진 지시에 따라 수정해주세요.

[원본 대본]
{script}

[수정 지시]
{retake_instruction}

[작성 규칙]
1. 반드시 한국어로 작성합니다.
2. 출연진과 기본 상황은 유지하면서 지시에 따라 수정합니다.
3. 기존 형식(이름: 대사, 지문은 괄호)을 유지합니다.
4. 원본과 분량이 비슷하게 유지합니다.

수정된 대본만 작성해주세요. 설명은 넣지 마세요.
""".strip()
    return call_gemini(prompt)


# ─────────────────────────────────────────
# 렌더링 헬퍼
# ─────────────────────────────────────────
def highlight_script(script: str) -> str:
    return re.sub(r'(\([^)]+\))', r'<span class="stage-dir">\1</span>', script)


def add_line_numbers(script: str) -> str:
    lines = script.split("\n")
    numbered = [
        f'<span class="line-num">{i:3d}</span>{line}'
        for i, line in enumerate(lines, 1)
    ]
    return "\n".join(numbered)


def render_script_box(script: str, font_size: int, show_line_numbers: bool = True):
    rendered = highlight_script(script)
    if show_line_numbers:
        rendered = add_line_numbers(rendered)
    st.markdown(
        f'<div class="script-box" style="font-size:{font_size}px">{rendered}</div>',
        unsafe_allow_html=True,
    )


def render_team_result(result: dict):
    mode = result["mode"]
    teams = result["teams"]
    mode_labels = {"monologue": "🎤 독백 모드", "ensemble": "🎭 전체 앙상블", "unit": "⚡ 유닛 분할"}
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
        st.markdown(f'<div class="team-card"><h3>앙상블 팀 전체</h3>{members_html}</div>',
                    unsafe_allow_html=True)
    else:
        team_icons = ["🔴", "🔵", "🟢", "🟡"]
        cols = st.columns(len(teams))
        for idx, (col, team) in enumerate(zip(cols, teams)):
            with col:
                icon = team_icons[idx % len(team_icons)]
                members_html = "".join(f'<span class="member-badge">{m}</span>' for m in team)
                st.markdown(f"""
                <div class="team-card">
                    <h3>{icon} 팀 {chr(65+idx)} &nbsp;·&nbsp; {len(team)}명</h3>
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

    st.subheader("👥 참여 인원 설정")
    num_people = st.slider("참여 인원수", min_value=1, max_value=20, value=2, step=1,
                           help="1명은 독백, 2명 이상은 앙상블 또는 유닛 분할로 진행됩니다.")
    st.divider()

    st.subheader("✍️ 이름 입력")
    names = []
    if num_people <= 6:
        for i in range(num_people):
            name = st.text_input(
                label=f"참여자 {i + 1}",
                value=f"배우{i + 1}",
                placeholder=f"참여자 {i + 1} 이름",
                key=f"name_{i}",
            )
            names.append(name.strip() if name.strip() else f"참여자{i+1}")
    else:
        default_names = ", ".join(f"배우{i+1}" for i in range(num_people))
        raw = st.text_area(
            f"이름 {num_people}개를 쉼표로 구분해 입력",
            value=default_names,
            height=100,
            help="예: 김철수, 이영희, 박민준 ...",
            key="names_bulk",
        )
        parsed = [n.strip() for n in raw.split(",") if n.strip()]
        while len(parsed) < num_people:
            parsed.append(f"참여자{len(parsed)+1}")
        names = parsed[:num_people]
        st.caption(f"인식된 이름: {' · '.join(names)}")

    st.divider()

    st.subheader("🎯 팀 나누기 방식")
    team_mode_options = ["랜덤", "앙상블"]
    if num_people >= 3:
        team_mode_options.append("유닛 분할")
    team_mode = st.radio(
        "방식 선택",
        team_mode_options,
        help="랜덤: 버튼을 누를 때마다 자동 결정 / 앙상블: 모두 함께 / 유닛 분할: 두 팀으로 직접 설정",
    )
    team_a_size = None
    if team_mode == "유닛 분할" and num_people >= 3:
        team_a_size = st.slider("팀 A 인원수", min_value=1, max_value=num_people - 1,
                                value=num_people // 2, step=1)
        st.caption(f"팀 A: {team_a_size}명 · 팀 B: {num_people - team_a_size}명  (팀 내 순서는 매번 랜덤)")

    st.divider()

    st.subheader("🎬 대본 설정")
    genre = st.selectbox("장르", ["드라마", "로맨스", "스릴러", "코미디", "SF", "판타지", "역사극"])
    mood = st.selectbox("분위기", ["긴장감 있는", "따뜻한", "유머러스한", "슬픈", "신비로운", "격렬한"])
    situation = st.text_area(
        "상황 설정",
        value="카페에서 오랜 친구를 우연히 만났다.",
        placeholder="예: 병원 복도에서 가족이 수술 결과를 기다리고 있다.",
        height=80,
    )

    monologue_type = "내면 독백"
    if num_people == 1:
        monologue_type = st.radio("독백 방식", ["내면 독백", "관객 독백"],
                                  help="내면 독백: 인물의 내면 생각 / 관객 독백: 관객에게 직접 말을 거는 방식")

    lines_label = "독백 대사 수" if num_people == 1 else "캐릭터당 대사 수"
    script_lines = st.slider(lines_label, min_value=3, max_value=10, value=5, step=1,
                             help="많을수록 분량이 늘어납니다.")

    st.divider()

    st.subheader("🔤 화면 설정")
    font_size = st.slider("대본 글자 크기", min_value=12, max_value=24, value=16, step=1,
                          help="연기 중 보기 편한 크기로 조절하세요.")
    show_line_numbers = st.toggle("줄 번호 표시", value=True,
                                  help="'37번 줄부터 다시' 처럼 연습할 때 유용합니다.")
    st.session_state["font_size"] = font_size

    st.divider()
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
        st.session_state["team_result"] = split_into_teams(names, team_mode, team_a_size)
        st.session_state["script"] = None
        st.session_state["script_stack"] = []
        st.session_state["script_alt"] = None
        st.session_state["director_report"] = None

if st.session_state["team_result"]:
    result = st.session_state["team_result"]
    render_team_result(result)
    st.divider()

    gen_btn = st.button("📝 AI 대본 생성하기", use_container_width=True, type="primary")

    if gen_btn:
        with st.status("✍️ 대본 생성 중...", expanded=True) as status:
            st.write("Gemini AI에 요청 중...")
            try:
                script_text = generate_script(
                    result, genre, mood, situation, script_lines, monologue_type
                )
                st.write("품질 검사 중...")
                warnings = validate_script(script_text, result)
                st.write("히스토리 저장 중...")
                save_to_history(script_text, genre, mood)
                st.session_state["script"] = script_text
                st.session_state["script_stack"] = []
                st.session_state["script_alt"] = None
                st.session_state["director_report"] = None
                status.update(label="✅ 대본 생성 완료!", state="complete")
            except Exception as e:
                status.update(label="❌ 오류 발생", state="error")
                st.error(f"대본 생성 중 오류가 발생했습니다: {e}")

    if st.session_state.get("script"):
        warnings = validate_script(st.session_state["script"], result)
        for w in warnings:
            st.markdown(f'<div class="warn-badge">⚠️ {w}</div>', unsafe_allow_html=True)

        st.subheader("📄 생성된 대본")
        render_script_box(st.session_state["script"], font_size, show_line_numbers)

        # 다운로드 버튼 (TXT + PDF)
        fname_base = f"scene_{genre}_{mood}_{datetime.now().strftime('%m%d_%H%M')}"
        dl_col1, dl_col2, _ = st.columns([1, 1, 2])
        with dl_col1:
            st.download_button(
                label="⬇️ TXT 다운로드",
                data=st.session_state["script"].encode("utf-8"),
                file_name=f"{fname_base}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with dl_col2:
            pdf_bytes = generate_pdf(st.session_state["script"], genre, mood)
            if pdf_bytes:
                st.download_button(
                    label="⬇️ PDF 다운로드",
                    data=pdf_bytes,
                    file_name=f"{fname_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.caption("PDF: fpdf2 설치 필요")

        st.divider()

        # ── 버전 비교 ──
        st.subheader("🔀 버전 비교")
        st.caption("같은 설정으로 다른 버전을 생성해 나란히 비교합니다.")
        alt_btn = st.button("✨ 다른 버전 생성하기", use_container_width=True)
        if alt_btn:
            variation_hints = [
                "인물 간의 갈등을 더 직접적으로 표현해줘.",
                "대사를 더 함축적이고 여백 있게 써줘.",
                "유머와 위트를 살짝 가미해줘.",
                "인물의 내면 심리를 대사에 더 녹여줘.",
            ]
            hint = random.choice(variation_hints)
            with st.status("✨ 다른 버전 생성 중...", expanded=True) as status:
                st.write(f"창작 방향: {hint}")
                try:
                    alt = generate_script(
                        result, genre, mood, situation, script_lines,
                        monologue_type, variation_hint=hint
                    )
                    st.session_state["script_alt"] = alt
                    status.update(label="✅ 완료!", state="complete")
                except Exception as e:
                    status.update(label="❌ 오류", state="error")
                    st.error(str(e))

        if st.session_state.get("script_alt"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**버전 A (현재)**")
                render_script_box(st.session_state["script"], font_size, show_line_numbers)
                if st.button("✅ 버전 A 선택", use_container_width=True):
                    st.session_state["script_alt"] = None
                    st.rerun()
            with col_b:
                st.markdown("**버전 B (새 버전)**")
                render_script_box(st.session_state["script_alt"], font_size, show_line_numbers)
                if st.button("✅ 버전 B 선택", use_container_width=True):
                    save_to_history(st.session_state["script_alt"], genre, mood)
                    st.session_state["script"] = st.session_state["script_alt"]
                    st.session_state["script_alt"] = None
                    st.session_state["director_report"] = None
                    st.rerun()

        st.divider()

        # ── AI 디렉터 리포트 ──
        st.subheader("🎬 AI 디렉터 리포트")
        director_btn = st.button("🔍 연기 가이드 분석하기", use_container_width=True)
        if director_btn:
            with st.status("🎬 대본 분석 중...", expanded=True) as status:
                st.write("인물 목표 분석 중...")
                try:
                    report = generate_director_report(st.session_state["script"], result)
                    st.session_state["director_report"] = report
                    status.update(label="✅ 분석 완료!", state="complete")
                except Exception as e:
                    status.update(label="❌ 오류", state="error")
                    st.error(str(e))

        if st.session_state.get("director_report"):
            report_html = re.sub(r'## (.+)', r'<h4>\1</h4>', st.session_state["director_report"])
            st.markdown(f'<div class="director-box">{report_html}</div>', unsafe_allow_html=True)

        st.divider()

        # ── 실시간 리테이크 ──
        st.subheader("🔄 리테이크")
        retake_col, undo_col = st.columns([3, 1])
        with undo_col:
            undo_disabled = len(st.session_state["script_stack"]) == 0
            if st.button("↩️ 되돌리기", use_container_width=True, disabled=undo_disabled):
                st.session_state["script"] = st.session_state["script_stack"].pop()
                st.session_state["director_report"] = None
                st.rerun()
        with retake_col:
            st.caption(f"되돌리기 가능 횟수: {len(st.session_state['script_stack'])}회")

        preset_options = [
            "직접 입력",
            "감정의 수위를 2배로 높여줘.",
            "대사보다는 침묵과 행동 위주로 바꿔줘.",
            "마지막에 예상치 못한 반전을 넣어줘.",
            "전체적인 템포를 빠르고 긴박하게 바꿔줘.",
            "두 인물 사이의 긴장감과 갈등을 극대화해줘.",
        ]
        retake_preset = st.selectbox("수정 지시 선택", preset_options, key="retake_preset")
        if retake_preset == "직접 입력":
            retake_input = st.text_input("수정 지시 직접 입력",
                                         placeholder="예: 코미디 요소를 추가해줘.",
                                         key="retake_custom")
        else:
            retake_input = retake_preset

        retake_btn = st.button("✏️ 리테이크 실행", use_container_width=True, type="primary")
        if retake_btn:
            if not retake_input.strip():
                st.warning("수정 지시를 입력해주세요.")
            else:
                with st.status("✏️ 대본 수정 중...", expanded=True) as status:
                    st.write(f"지시: {retake_input}")
                    try:
                        new_script = generate_retake(st.session_state["script"], retake_input)
                        st.session_state["script_stack"].append(st.session_state["script"])
                        st.session_state["script"] = new_script
                        st.session_state["director_report"] = None
                        save_to_history(new_script, genre, mood)
                        status.update(label="✅ 수정 완료!", state="complete")
                        st.rerun()
                    except Exception as e:
                        status.update(label="❌ 오류", state="error")
                        st.error(str(e))

else:
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


# ─────────────────────────────────────────
# 대본 히스토리 (하단)
# ─────────────────────────────────────────
if st.session_state["script_history"]:
    st.divider()
    with st.expander(f"📚 대본 히스토리 ({len(st.session_state['script_history'])}개 저장됨 · 새로고침 후에도 유지)", expanded=False):
        for i, entry in enumerate(st.session_state["script_history"]):
            h_col1, h_col2 = st.columns([4, 1])
            with h_col1:
                st.markdown(f"**{i+1}. {entry['label']}**")
            with h_col2:
                if st.button("불러오기", key=f"hist_{i}"):
                    st.session_state["script"] = entry["script"]
                    st.session_state["script_stack"] = []
                    st.session_state["script_alt"] = None
                    st.session_state["director_report"] = None
                    st.rerun()
            st.markdown(
                f'<div class="script-box-sm">{highlight_script(entry["script"])}</div>',
                unsafe_allow_html=True,
            )
            if i < len(st.session_state["script_history"]) - 1:
                st.markdown("---")
