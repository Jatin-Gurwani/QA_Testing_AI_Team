import streamlit as st
import sys
import os
import threading
import traceback
from pathlib import Path
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Testing AI Crew",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Lazy imports (keep Streamlit responsive) ──────────────────────────────────
def _import_crew():
    from app.crew import QACrew
    return QACrew

def _import_langfuse():
    """Attempt to import and initialise Langfuse; returns (langfuse_client, available)."""
    try:
        from openinference.instrumentation.crewai import CrewAIInstrumentor
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from openinference.instrumentation.litellm import LiteLLMInstrumentor
        from langfuse import get_client
        from dotenv import load_dotenv
        load_dotenv()
        langfuse = get_client()
        if langfuse.auth_check():
            LiteLLMInstrumentor().instrument(skip_dep_check=True)
            GoogleGenAIInstrumentor().instrument(skip_dep_check=True)
            OpenAIInstrumentor().instrument(skip_dep_check=True)
            CrewAIInstrumentor().instrument(skip_dep_check=True)
            return langfuse, True
        return None, False
    except Exception:
        return None, False


# ── Helpers ────────────────────────────────────────────────────────────────────
def extract_repo_name(repo_url: str) -> str:
    url = repo_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.replace("\\", "/").split("/")[-1]


def read_output_file(repo_name: str, relative_path: str) -> str | None:
    from app.crew import output_dir as crew_output_dir
    p = Path(crew_output_dir) / repo_name / relative_path
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None


def list_test_files(repo_name: str) -> list[Path]:
    from app.crew import output_dir as crew_output_dir
    base = Path(crew_output_dir) / repo_name / "testcases"
    return sorted(f for f in base.glob("*") if f.is_file()) if base.exists() else []


def list_rca_files(repo_name: str) -> list[Path]:
    from app.crew import output_dir as crew_output_dir
    base = Path(crew_output_dir) / repo_name / "test_results" / "fail_cases"
    return sorted(f for f in base.glob("*.md") if f.is_file()) if base.exists() else []


def get_output_dir_for_repo(repo_name: str) -> Path:
    from app.crew import output_dir as crew_output_dir
    return Path(crew_output_dir) / repo_name


# ── Task type definitions (mirrors main.py) ───────────────────────────────────
TASK_TYPES = {
    "only_generation": {
        "label": "🧪 Generate Tests Only",
        "description": "Analyze repo → Plan strategy → Write test code",
        "icon": "🧪",
        "tasks": ["Repository Analysis", "Test Strategy Planning", "Test Code Generation"],
        "agents_used": ["Repository Analyst", "Strategy Planner", "Test Writer"],
    },
    "run_testcase": {
        "label": "🚀 Full Pipeline (Generate + Execute)",
        "description": "Analyze → Plan → Write → Docker sandbox → Execute → QA Audit",
        "icon": "🚀",
        "tasks": [
            "Repository Analysis", "Test Strategy Planning", "Test Code Generation",
            "Test Environment Provisioning", "Test Execution & Root Cause Analysis",
            "QA Audit & Final Report",
        ],
        "agents_used": [
            "Repository Analyst", "Strategy Planner", "Test Writer",
            "Sandbox Engineer", "Senior Test Engineer", "QA Expert",
        ],
    },
    "both": {
        "label": "⚙️ All Tasks (Default Order)",
        "description": "Run every task in the crew's default sequential order",
        "icon": "⚙️",
        "tasks": [],
        "agents_used": ["All 6 Agents"],
    },
}


# ── Session state defaults ────────────────────────────────────────────────────
_defaults = {
    "status": "idle",        # idle | running | done | error
    "repo_name": "",
    "repo_path_input": "",
    "error": None,
    "result_holder": None,
    "crew_thread": None,
    "task_type": "only_generation",
    "langfuse_status": None,  # None | "connected" | "unavailable"
    "run_start_time": None,
    "run_log": [],
    "past_runs": [],         # list of dicts with summary info
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Crew runner (background thread) ──────────────────────────────────────────
def _run_crew(repo_path: str, user_request: str, task_type: str, holder: dict):
    """Execute the QA crew in a background thread."""
    try:
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)

        QACrew = _import_crew()
        langfuse, langfuse_available = _import_langfuse()

        task_dict = {
            "only_generation": ["Repository Analysis", "Test Strategy Planning", "Test Code Generation"],
            "run_testcase": [
                "Repository Analysis", "Test Strategy Planning", "Test Code Generation",
                "Test Environment Provisioning", "Test Execution & Root Cause Analysis",
                "QA Audit & Final Report",
            ],
            "both": [],
        }

        tasks_list = task_dict.get(task_type, [])
        qa = QACrew(repo_path)
        qacrew = qa.crew(tasks_name_list=tasks_list)

        if langfuse_available and langfuse:
            holder["langfuse"] = "connected"
            try:
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="crewai-gui-trace",
                    input={"user_request": user_request, "repo_url": repo_path, "task_type": task_type},
                ):
                    result = qacrew.kickoff(inputs={"repo_url": repo_path, "user_request": user_request})
            except Exception:
                result = qacrew.kickoff(inputs={"repo_url": repo_path, "user_request": user_request})
            finally:
                try:
                    langfuse.flush()
                except Exception:
                    pass
        else:
            holder["langfuse"] = "unavailable"
            result = qacrew.kickoff(inputs={"repo_url": repo_path, "user_request": user_request})

        holder["status"] = "done"
        holder["result"] = str(result)
        holder["token_usage"] = str(getattr(result, "token_usage", "N/A"))
    except Exception:
        holder["status"] = "error"
        holder["error"] = traceback.format_exc()


@st.fragment(run_every="2s")
def _render_running_status():
    """Render progress and check for background completion without rerunning the page."""
    holder = st.session_state.result_holder

    if holder and holder.get("status") != "running":
        st.session_state.langfuse_status = holder.get("langfuse")
        if holder["status"] == "done":
            st.session_state.status = "done"
            elapsed = ""
            if st.session_state.run_start_time:
                delta = datetime.now() - st.session_state.run_start_time
                elapsed = f"{delta.seconds // 60}m {delta.seconds % 60}s"
            st.session_state.past_runs.append({
                "repo_name": st.session_state.repo_name,
                "task_type": st.session_state.task_type,
                "time": elapsed or "?",
                "success": True,
            })
        else:
            st.session_state.status = "error"
            st.session_state.error = holder.get("error", "Unknown error")
            st.session_state.past_runs.append({
                "repo_name": st.session_state.repo_name,
                "task_type": st.session_state.task_type,
                "time": "—",
                "success": False,
            })
        st.rerun()

    elapsed_str = ""
    if st.session_state.run_start_time:
        delta = datetime.now() - st.session_state.run_start_time
        elapsed_str = f"{delta.seconds // 60}m {delta.seconds % 60}s elapsed"

    repo_display = st.session_state.repo_name
    task_info = TASK_TYPES.get(st.session_state.task_type, {})
    agent_cards_data = [
        ("&#x1F50D;", "Repository", "Analyst"),
        ("&#x1F4CB;", "Strategy", "Planner"),
        ("&#x270D;&#xFE0F;", "Test", "Writer"),
        ("&#x1F433;", "Sandbox", "Engineer"),
        ("&#x1F3C3;", "Senior Test", "Engineer"),
        ("&#x1F4CA;", "QA", "Expert"),
    ]
    if st.session_state.task_type == "only_generation":
        agent_cards_data = agent_cards_data[:3]

    agent_cards_html = "".join(
        (
            '<div class="agent-card">'
            '<div class="agent-dot"></div>'
            f'<span class="agent-emoji">{emoji}</span>'
            f'<div class="agent-name">{line1}<br>{line2}</div>'
            "</div>"
        )
        for emoji, line1, line2 in agent_cards_data
    )

    st.markdown(f"""
<div class="anim-wrap">
    <div class="anim-icon">&#x1F9EA;</div>
    <div class="anim-title">Running QA Crew</div>
    <div class="anim-sub">
        Analysing <strong style="color:#58A6FF;">{repo_display}</strong>
        &mdash; {task_info.get('description', 'processing')}&hellip;
        <br><span style="font-size:11px;color:#484F58;">{elapsed_str}</span>
    </div>
    <div class="agent-row">{agent_cards_html}</div>
    <div class="shimmer-track"></div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CSS — Dark theme with GitHub-inspired styling
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

/* ── Base ── */
html, body,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] {
    background-color: #0D1117 !important;
    color: #E6EDF3 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"]  { background-color: #0D1117 !important; border-bottom:1px solid #21262D; }
h1,h2,h3,h4,h5,p,label { font-family:'Inter',sans-serif !important; color:#E6EDF3; }
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded" !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #161B22 !important;
    border-right: 1px solid #21262D !important;
}
section[data-testid="stSidebar"] .stMarkdown p { color: #8B949E !important; font-size:13px; }
section[data-testid="stSidebar"] h1 { font-size:18px !important; }
section[data-testid="stSidebar"] h2 { font-size:15px !important; color:#8B949E !important; }
section[data-testid="stSidebar"] h3 { font-size:13px !important; color:#58A6FF !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea  > div > div > textarea {
    background-color:#161B22 !important;
    border:1px solid #30363D !important;
    border-radius:8px !important;
    color:#E6EDF3 !important;
    font-family:'Inter',sans-serif !important;
    font-size:14px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea  > div > div > textarea:focus {
    border-color:#58A6FF !important;
    box-shadow:0 0 0 3px rgba(88,166,255,0.15) !important;
    outline:none !important;
}
.stTextInput > label, .stTextArea > label {
    font-size:12px !important; font-weight:600 !important;
    color:#8B949E !important; letter-spacing:0.5px;
    text-transform: uppercase;
}
.stTextInput > div > div > input::placeholder,
.stTextArea  > div > div > textarea::placeholder { color:#484F58 !important; }

/* ── Selectbox / Radio ── */
.stSelectbox > div > div,
.stRadio > div { color: #E6EDF3 !important; }
.stSelectbox label, .stRadio label {
    font-size:12px !important; font-weight:600 !important;
    color:#8B949E !important; letter-spacing:0.5px;
    text-transform: uppercase;
}

/* ── Buttons ── */
.stButton > button {
    background-color:#1A7F37 !important;
    color:#fff !important;
    border:1px solid #2EA043 !important;
    border-radius:8px !important;
    font-family:'Inter',sans-serif !important;
    font-weight:600 !important;
    font-size:14px !important;
    padding:0.6rem 1.5rem !important;
    width:100%;
    transition: all 0.2s ease !important;
}
.stButton > button:hover:not(:disabled) {
    background-color:#2EA043 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(46,160,67,0.3) !important;
}
.stButton > button:disabled {
    background-color:#21262D !important;
    border-color:#30363D !important;
    color:#484F58 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color:#161B22 !important;
    border-bottom:1px solid #30363D !important;
    border-radius:8px 8px 0 0;
    gap:0 !important; padding:0 8px !important;
}
.stTabs [data-baseweb="tab"] {
    background-color:transparent !important; color:#8B949E !important;
    border-radius:0 !important;
    font-size:13px !important; font-weight:500 !important;
    padding:10px 20px !important;
}
.stTabs [aria-selected="true"] { color:#E6EDF3 !important; border-bottom:2px solid #58A6FF !important; }
.stTabs [data-baseweb="tab-panel"] {
    background-color:#161B22; border:1px solid #30363D;
    border-top:none; border-radius:0 0 8px 8px;
    padding:20px !important;
}

/* ── Markdown ── */
.stMarkdown p     { color:#C9D1D9 !important; font-size:14px; line-height:1.8; }
.stMarkdown h1,.stMarkdown h2,.stMarkdown h3 { color:#E6EDF3 !important; }
.stMarkdown code  {
    background:#0D1117 !important; color:#79C0FF !important;
    font-family:'JetBrains Mono',monospace; font-size:12px;
    border-radius:4px; padding:1px 6px;
}
[data-testid="stMarkdownContainer"] pre {
    background:#0D1117 !important; border:1px solid #30363D !important;
    border-radius:8px !important;
}
.stMarkdown table { font-size:13px; }
.stMarkdown th { background:#0D1117 !important; color:#8B949E !important; }
.stMarkdown td { border-color:#21262D !important; color:#C9D1D9 !important; }

.stCode > div {
    background:#0D1117 !important; border:1px solid #30363D !important;
    border-radius:8px !important; font-size:12px !important;
}

hr { border-color:#21262D !important; margin:28px 0 !important; }

[data-testid="stInfo"] {
    background:#0D2B45 !important; border-left:3px solid #58A6FF !important;
    border-radius:6px !important;
}
[data-testid="stSuccess"] {
    background:#0D3B1E !important; border-left:3px solid #56D364 !important;
    border-radius:6px !important;
}
[data-testid="stWarning"] {
    background:#3D2B00 !important; border-left:3px solid #D29922 !important;
    border-radius:6px !important;
}
[data-testid="stException"] { background:#1C0E0E !important; border-radius:8px; }

/* ── Expander ── */
details > summary {
    font-family:'JetBrains Mono',monospace !important;
    font-size:12px !important; color:#8B949E !important;
    background:#161B22 !important; border:1px solid #30363D !important;
    border-radius:6px !important; padding:9px 14px !important;
    cursor:pointer;
}
details > summary:hover { color:#E6EDF3 !important; border-color:#58A6FF !important; }
details[open] > summary { border-radius:6px 6px 0 0 !important; border-bottom-color:transparent !important; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #161B22 !important;
    border: 1px solid #30363D !important;
    border-radius: 10px !important;
    padding: 16px !important;
}
[data-testid="stMetric"] label { color: #8B949E !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.5px; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #E6EDF3 !important; font-size: 24px !important; }

/* ── Custom animation classes ── */
@keyframes float {
    0%,100% { transform:translateY(0px); }
    50%     { transform:translateY(-10px); }
}
@keyframes card-glow {
    0%,16%,100% { border-color:#30363D; box-shadow:none; }
    5%,11%      { border-color:#1F6FEB;
                  box-shadow:0 0 0 3px rgba(31,111,235,0.15),
                             0 0 20px rgba(88,166,255,0.12); }
}
@keyframes dot-pulse {
    0%,16%,100% { background:#30363D; box-shadow:none; }
    5%,11%      { background:#58A6FF; box-shadow:0 0 8px rgba(88,166,255,0.6); }
}
@keyframes shimmer {
    0%   { transform:translateX(-120%); }
    100% { transform:translateX(380%);  }
}
@keyframes fade-in {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0);    }
}

.anim-wrap {
    display:flex; flex-direction:column; align-items:center;
    padding:40px 24px 48px;
    animation: fade-in 0.5s ease-out;
}
.anim-icon {
    font-size:48px; line-height:1;
    animation: float 3s ease-in-out infinite;
    margin-bottom:20px;
    filter: drop-shadow(0 0 18px rgba(88,166,255,0.35));
}
.anim-title {
    font-size:20px; font-weight:700; color:#E6EDF3;
    margin:0 0 6px; text-align:center;
}
.anim-sub {
    font-size:13px; color:#8B949E;
    margin:0 0 36px; text-align:center;
    max-width:400px; line-height:1.6;
}
.agent-row {
    display:flex; gap:14px; justify-content:center;
    margin-bottom:36px; flex-wrap:wrap;
}
.agent-card {
    background:#161B22; border:1px solid #30363D;
    border-radius:10px; padding:14px 16px;
    width:130px; text-align:center;
    animation: card-glow 12s ease-in-out infinite;
    transition: transform 0.2s ease;
}
.agent-card:hover { transform: translateY(-3px); }
.agent-card:nth-child(1) { animation-delay:0s; }
.agent-card:nth-child(2) { animation-delay:2s; }
.agent-card:nth-child(3) { animation-delay:4s; }
.agent-card:nth-child(4) { animation-delay:6s; }
.agent-card:nth-child(5) { animation-delay:8s; }
.agent-card:nth-child(6) { animation-delay:10s; }
.agent-dot {
    width:8px; height:8px; border-radius:50%;
    background:#30363D; margin:0 auto 8px;
    animation: dot-pulse 12s ease-in-out infinite;
}
.agent-card:nth-child(1) .agent-dot { animation-delay:0s; }
.agent-card:nth-child(2) .agent-dot { animation-delay:2s; }
.agent-card:nth-child(3) .agent-dot { animation-delay:4s; }
.agent-card:nth-child(4) .agent-dot { animation-delay:6s; }
.agent-card:nth-child(5) .agent-dot { animation-delay:8s; }
.agent-card:nth-child(6) .agent-dot { animation-delay:10s; }
.agent-emoji { font-size:20px; margin-bottom:4px; line-height:1; display:block; }
.agent-name  { font-size:10px; font-weight:600; color:#8B949E; line-height:1.4; }

.shimmer-track {
    position:relative; width:280px; height:3px;
    background:#21262D; border-radius:2px; overflow:hidden;
}
.shimmer-track::after {
    content:''; position:absolute; top:0; left:0;
    width:45%; height:100%;
    background:linear-gradient(90deg,transparent,#58A6FF,transparent);
    animation: shimmer 1.8s ease-in-out infinite;
}

/* ── Results ── */
.results-header {
    display:flex; align-items:center; gap:10px;
    padding:16px 0 4px;
    animation: fade-in 0.5s ease-out;
}
.results-badge {
    background:#0D3B1E; color:#56D364;
    border:1px solid #2EA043;
    font-size:11px; font-weight:700;
    padding:3px 10px; border-radius:20px;
    text-transform:uppercase; letter-spacing:0.5px;
    display:inline-flex; align-items:center; gap:4px;
}

/* ── Phase pipeline vis ── */
.pipeline-row {
    display: flex; gap: 4px; align-items: center;
    flex-wrap: wrap; margin: 16px 0;
}
.pipeline-step {
    background: #161B22; border: 1px solid #30363D;
    border-radius: 6px; padding: 6px 12px;
    font-size: 11px; color: #8B949E; font-weight: 500;
    display: inline-flex; align-items: center; gap: 4px;
}
.pipeline-step.active {
    border-color: #58A6FF; color: #58A6FF;
    background: #0D2B45;
}
.pipeline-arrow { color: #30363D; font-size: 14px; }

/* ── Stat card grid ── */
.stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px; margin: 16px 0;
}
.stat-card {
    background: #161B22; border: 1px solid #30363D;
    border-radius: 10px; padding: 16px;
    text-align: center;
}
.stat-card .stat-value {
    font-size: 24px; font-weight: 700; color: #E6EDF3;
    margin-bottom: 2px;
}
.stat-card .stat-label {
    font-size: 11px; color: #8B949E; text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stCaption p { color:#484F58 !important; font-size:11px !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — Configuration & History
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px;">
        <span style="font-size:24px;">&#x1F9EA;</span>
        <div>
            <div style="font-size:17px;font-weight:700;color:#E6EDF3;">QA Testing AI Crew</div>
            <div style="font-size:11px;color:#58A6FF;">Phase 2 &middot; CrewAI</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── Pipeline info ──
    st.markdown("### 🔧 Pipeline Phases")
    with st.expander("📖 View all 6 agents", expanded=False):
        st.markdown("""
| # | Agent | Role |
|---|-------|------|
| 1 | 🔍 Repository Analyst | Code analysis & triage |
| 2 | 📋 Strategy Planner | Test plan design |
| 3 | ✍️ Test Writer | Test code generation |
| 4 | 🐳 Sandbox Engineer | Docker env provisioning |
| 5 | 🏃 Senior Test Engineer | Execution & RCA |
| 6 | 📊 QA Expert | Audit & final report |
        """)

    st.markdown("---")

    # ── Langfuse status ──
    st.markdown("### 📡 Observability")
    lf_status = st.session_state.get("langfuse_status")
    if lf_status == "connected":
        st.success("Langfuse connected", icon="✅")
    elif lf_status == "unavailable":
        st.warning("Langfuse unavailable", icon="⚠️")
    else:
        st.info("Status shown after run starts", icon="ℹ️")

    st.markdown("---")

    # ── Past runs ──
    st.markdown("### 📜 Run History")
    if st.session_state.past_runs:
        for i, run in enumerate(reversed(st.session_state.past_runs[-5:])):
            status_icon = "✅" if run.get("success") else "❌"
            st.markdown(
                f"**{status_icon} {run.get('repo_name', '?')}**  \n"
                f"`{run.get('task_type', '?')}` · {run.get('time', '?')}"
            )
    else:
        st.caption("No runs yet in this session.")

    st.markdown("---")
    st.caption("Built with CrewAI · Streamlit · MCP")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AREA — Header
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="display:flex;align-items:center;gap:14px;
            padding:16px 0 14px;border-bottom:1px solid #21262D;margin-bottom:28px;">
    <span style="font-size:32px;line-height:1;">&#x1F9EA;</span>
    <div>
        <div style="font-size:22px;font-weight:700;letter-spacing:-0.3px;color:#E6EDF3;">
            QA Testing AI Crew
        </div>
        <div style="font-size:12px;color:#8B949E;margin-top:2px;">
            Automated test generation, execution &amp; auditing &nbsp;&middot;&nbsp; Phase 2
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  IDLE — Input Form
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.status == "idle":

    col_form, col_preview = st.columns([3, 2], gap="large")

    with col_form:
        st.markdown("#### 📂 Repository Source")

        repo_input = st.text_input(
            "Repository Path or URL",
            placeholder="https://github.com/user/repo.git  or  D:/projects/my-app",
            help="Enter a GitHub .git URL (will be cloned), a local git repo path, or any local project folder.",
        )

        st.markdown("#### 🎯 Test Request")

        user_request = st.text_area(
            "What do you want to test?",
            placeholder='e.g.  "Write unit tests for the auth module, focus on edge cases"\n'
                        '"Test the entire repo with happy path and failure cases"\n'
                        '"Generate integration tests for the API routes"',
            height=130,
        )

        st.markdown("#### ⚙️ Pipeline Mode")

        task_type = st.radio(
            "Select execution mode",
            options=list(TASK_TYPES.keys()),
            format_func=lambda k: TASK_TYPES[k]["label"],
            horizontal=True,
            help="Choose which phases of the pipeline to run.",
        )
        st.session_state.task_type = task_type

        st.markdown("<br>", unsafe_allow_html=True)

        _ready = bool(repo_input.strip()) and bool(user_request.strip())

        if st.button("▶  Launch QA Crew", disabled=not _ready, use_container_width=True):
            holder = {"status": "running", "result": None, "error": None, "token_usage": None, "langfuse": None}
            st.session_state.result_holder = holder
            st.session_state.repo_name = extract_repo_name(repo_input)
            st.session_state.repo_path_input = repo_input.strip()
            st.session_state.status = "running"
            st.session_state.run_start_time = datetime.now()
            t = threading.Thread(
                target=_run_crew,
                args=(repo_input.strip(), user_request.strip(), task_type, holder),
                daemon=True,
            )
            st.session_state.crew_thread = t
            t.start()
            st.rerun()

    with col_preview:
        st.markdown("#### 📋 Pipeline Preview")
        selected = TASK_TYPES[task_type]

        # Show pipeline steps
        pipeline_html = '<div class="pipeline-row">'
        for i, step in enumerate(selected["tasks"] or [
            "Repository Analysis", "Test Strategy Planning", "Test Code Generation",
            "Test Environment Provisioning", "Test Execution & RCA", "QA Audit & Final Report",
        ]):
            short = step.replace("Test ", "").replace("Repository ", "Repo ").replace(" & Root Cause Analysis", " & RCA")
            if i > 0:
                pipeline_html += '<span class="pipeline-arrow">&#x2192;</span>'
            pipeline_html += f'<span class="pipeline-step active">{short}</span>'
        pipeline_html += '</div>'
        st.markdown(pipeline_html, unsafe_allow_html=True)

        st.markdown(f"**{selected['description']}**")
        st.markdown("")

        st.markdown("**Agents involved:**")
        for agent_name in selected["agents_used"]:
            st.markdown(f"- {agent_name}")

        st.markdown("---")
        st.markdown("**Output artifacts:**")
        if task_type == "only_generation":
            st.markdown("""
- `analysis_report.md`
- `test_plan.md`
- `testcases/` (test files)
- `testcases_summary.md`
            """)
        else:
            st.markdown("""
- `analysis_report.md`
- `test_plan.md`
- `testcases/` (test files)
- `testcases_summary.md`
- `sandbox_handoff.md`
- `test_results/test_report.md`
- `test_results/fail_cases/*.md`
- `final_audit_report.md`
            """)


# ══════════════════════════════════════════════════════════════════════════════
#  RUNNING — Animated Progress
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "running":
    _render_running_status()


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR — Show error with details
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "error":
    st.error("The QA Crew encountered an error.", icon="❌")

    with st.expander("🔍 Error Details", expanded=True):
        st.code(st.session_state.error or "No traceback available.", language="python")

    col1, col2, _ = st.columns([1, 1, 2])
    with col1:
        if st.button("↺  Try Again", use_container_width=True):
            st.session_state.status = "idle"
            st.session_state.error = None
            st.rerun()
    with col2:
        if st.button("🏠  Back to Home", use_container_width=True):
            for k, v in _defaults.items():
                if k != "past_runs":
                    st.session_state[k] = v
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  DONE — Results Dashboard
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "done":
    _repo = st.session_state.repo_name
    _task_type = st.session_state.task_type
    holder = st.session_state.result_holder or {}

    # ── Header ──
    st.markdown(f"""
<div class="results-header">
    <span style="font-size:20px;font-weight:700;color:#E6EDF3;">Results</span>
    <span class="results-badge">&#x2713; Complete</span>
    <span style="font-size:13px;color:#8B949E;margin-left:4px;">{_repo}</span>
    <span style="font-size:11px;color:#484F58;margin-left:auto;">
        Mode: {TASK_TYPES.get(_task_type, {}).get('label', _task_type)}
    </span>
</div>
""", unsafe_allow_html=True)

    st.markdown("")

    # ── Summary metrics ──
    _test_files = list_test_files(_repo)
    _rca_files = list_rca_files(_repo)
    _output_dir = get_output_dir_for_repo(_repo)
    _has_analysis = (_output_dir / "analysis_report.md").is_file()
    _has_plan = (_output_dir / "test_plan.md").is_file()
    _has_sandbox = (_output_dir / "sandbox_handoff.md").is_file()
    _has_exec = (_output_dir / "test_results" / "test_report.md").is_file()
    _has_audit = (_output_dir / "final_audit_report.md").is_file()

    # Count artifacts
    artifact_count = sum([_has_analysis, _has_plan, bool(_test_files), _has_sandbox, _has_exec, _has_audit])

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.metric("Test Files", len(_test_files))
    with mcol2:
        st.metric("Artifacts", artifact_count)
    with mcol3:
        st.metric("RCA Reports", len(_rca_files))
    with mcol4:
        token_usage = holder.get("token_usage", "N/A")
        st.metric("Status", "✅ Done")

    st.markdown("")

    # ── Tabbed results ──
    tab_labels = ["🧪 Test Cases", "📄 Analysis", "📋 Test Plan"]
    if _task_type in ("run_testcase", "both"):
        tab_labels += ["🐳 Sandbox", "🏃 Execution", "📊 QA Audit"]
    tab_labels.append("📝 Raw Output")

    tabs = st.tabs(tab_labels, on_change="rerun")

    def _render_result_tab(tab_index: int):
        if tab_index == 0:
            if _test_files:
                _summary = read_output_file(_repo, "testcases_summary.md")
                if _summary:
                    with st.expander("📋 Test Cases Summary", expanded=True):
                        st.markdown(_summary)

                st.markdown("---")
                st.markdown(f"**{len(_test_files)} test file(s) generated:**")

                for _f in _test_files:
                    _lang = {
                        ".py": "python", ".ts": "typescript", ".js": "javascript",
                        ".java": "java", ".go": "go", ".rb": "ruby", ".kt": "kotlin",
                        ".rs": "rust", ".cs": "csharp",
                    }.get(_f.suffix, "text")
                    file_expander = st.expander(
                        f"📄 {_f.name}", expanded=False, on_change="rerun"
                    )
                    if file_expander.open:
                        with file_expander:
                            st.code(
                                _f.read_text(encoding="utf-8", errors="replace"),
                                language=_lang,
                            )
            else:
                st.info(
                    f"No test files found under `outputs/{_repo}/testcases/`\n\n"
                    "The test writer agent may not have saved files yet."
                )
        elif tab_index == 1:
            _analysis = read_output_file(_repo, "analysis_report.md")
            if _analysis:
                st.markdown(_analysis)
            else:
                st.info(f"`outputs/{_repo}/analysis_report.md` not found.")
        elif tab_index == 2:
            _plan = read_output_file(_repo, "test_plan.md")
            if _plan:
                st.markdown(_plan)
            else:
                st.info(f"`outputs/{_repo}/test_plan.md` not found.")
        elif _task_type in ("run_testcase", "both") and tab_index == 3:
            _sandbox = read_output_file(_repo, "sandbox_handoff.md")
            if _sandbox:
                st.markdown(_sandbox)
            else:
                st.info(f"`outputs/{_repo}/sandbox_handoff.md` not found.")
        elif _task_type in ("run_testcase", "both") and tab_index == 4:
            _exec_report = read_output_file(_repo, "test_results/test_report.md")
            if _exec_report:
                st.markdown(_exec_report)
                if _rca_files:
                    st.markdown("---")
                    st.markdown("#### 🔍 Root Cause Analysis Reports")
                    for rca in _rca_files:
                        rca_expander = st.expander(
                            f"📋 {rca.stem}", expanded=False, on_change="rerun"
                        )
                        if rca_expander.open:
                            with rca_expander:
                                st.markdown(
                                    rca.read_text(encoding="utf-8", errors="replace")
                                )
            else:
                st.info(f"`outputs/{_repo}/test_results/test_report.md` not found.")

            logs_path = _output_dir / "test_results" / "container_logs.txt"
            if logs_path.is_file():
                logs_expander = st.expander(
                    "📜 Container Logs", expanded=False, on_change="rerun"
                )
                if logs_expander.open:
                    with logs_expander:
                        st.code(
                            logs_path.read_text(encoding="utf-8", errors="replace"),
                            language="text",
                        )
        elif _task_type in ("run_testcase", "both") and tab_index == 5:
            _audit = read_output_file(_repo, "final_audit_report.md")
            if _audit:
                st.markdown(_audit)
            else:
                st.info(f"`outputs/{_repo}/final_audit_report.md` not found.")
        else:
            raw_result = holder.get("result", "No raw output captured.")
            st.code(raw_result, language="text")
            token_usage = holder.get("token_usage", "N/A")
            if token_usage and token_usage != "N/A":
                st.markdown("---")
                st.markdown("**Token Usage:**")
                st.code(token_usage, language="text")

    for tab_index, tab in enumerate(tabs):
        if tab.open:
            with tab:
                _render_result_tab(tab_index)

    # ── Action buttons ──
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("↺  Run Again", use_container_width=True):
            for k, v in _defaults.items():
                if k != "past_runs":
                    st.session_state[k] = v
            st.rerun()
    with col2:
        output_path = get_output_dir_for_repo(_repo)
        if output_path.exists():
            st.markdown(f"📂 [Open outputs]({output_path.as_uri()})")
