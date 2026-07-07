import streamlit as st
import sys
import os
import threading
import traceback
from pathlib import Path
from app.crew import QACrew

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Crew",
    page_icon="⚗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Helpers ────────────────────────────────────────────────────────────────────
def extract_repo_name(repo_url: str) -> str:
    url = repo_url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("/")[-1]


def read_output_file(repo_name: str, relative_path: str) -> str | None:
    p = Path(os.getcwd()) / "outputs" / repo_name / relative_path
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None


def list_test_files(repo_name: str) -> list[Path]:
    base = Path(os.getcwd()) / "outputs" / repo_name / "testcases"
    return sorted(f for f in base.glob("*") if f.is_file()) if base.exists() else []


# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "status": "idle",
    "repo_name": "",
    "error": None,
    "result_holder": None,
    "crew_thread": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Crew runner (background thread) ────────────────────────────────────────────
def _run_crew(repo_url: str, user_request: str, github_pat: str, holder: dict):
    os.environ["GITHUB_PAT"] = github_pat
    try:
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        qa = QACrew()
        inputs = {"repo_url": repo_url, "user_request": user_request}
        result = qa.crew().kickoff(inputs=inputs)
        print("--------->:",result.token_usage)
        holder["status"] = "done"
        holder["result"] = str(result)
    except Exception:
        holder["status"] = "error"
        holder["error"] = traceback.format_exc()
    finally:
        os.environ.pop("GITHUB_PAT", None)


# ══════════════════════════════════════════════════════════════════════════════
#  CSS  (injected once, outside the per-state branches)
# ══════════════════════════════════════════════════════════════════════════════
# FIX 1: CSS + keyframes are defined in a single <style> block injected at the
#         top level so they are always available regardless of current state.
# FIX 2: Emoji characters inside HTML strings are kept as literal Unicode; they
#         are NOT passed through st.markdown's text-processing path (which can
#         mangle them), because the whole block is raw HTML via unsafe_allow_html.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap');

html, body,
[data-testid="stAppViewContainer"],
section[data-testid="stMain"] {
    background-color: #0D1117 !important;
    color: #E6EDF3 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stHeader"]  { background-color: #0D1117 !important; border-bottom:1px solid #21262D; }
[data-testid="stToolbar"] { display:none; }

h1,h2,h3,h4,h5,p,span,label,div { font-family:'Inter',sans-serif !important; color:#E6EDF3; }

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
    box-shadow:0 0 0 3px rgba(88,166,255,0.1) !important;
    outline:none !important;
}
.stTextInput > label, .stTextArea > label {
    font-size:12px !important; font-weight:600 !important;
    color:#8B949E !important; letter-spacing:0.5px;
}
.stTextInput > div > div > input::placeholder,
.stTextArea  > div > div > textarea::placeholder { color:#484F58 !important; }

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
    transition:background-color 0.15s ease !important;
}
.stButton > button:hover:not(:disabled) { background-color:#2EA043 !important; }
.stButton > button:disabled {
    background-color:#21262D !important;
    border-color:#30363D !important;
    color:#484F58 !important;
}

.stCaption p { color:#484F58 !important; font-size:11px !important; }

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
[data-testid="stException"] { background:#1C0E0E !important; border-radius:8px; }

/* ══ ANIMATION SCREEN ══════════════════════════════════════════════════════ */
.anim-wrap {
    display:flex; flex-direction:column; align-items:center;
    padding:48px 24px 56px;
}

/* FIX 3: All @keyframes are declared here, inside the global <style> block,
           so Streamlit never needs to parse them as markdown text. */
@keyframes float {
    0%,100% { transform:translateY(0px); }
    50%      { transform:translateY(-10px); }
}
@keyframes card-glow {
    0%,25%,100% { border-color:#30363D; box-shadow:none; }
    8%,17%      { border-color:#1F6FEB;
                  box-shadow:0 0 0 3px rgba(31,111,235,0.15),
                             0 0 20px rgba(88,166,255,0.12); }
}
@keyframes dot-pulse {
    0%,25%,100% { background:#30363D; box-shadow:none; }
    8%,17%      { background:#58A6FF; box-shadow:0 0 8px rgba(88,166,255,0.6); }
}
@keyframes shimmer {
    0%   { transform:translateX(-120%); }
    100% { transform:translateX(380%);  }
}

.anim-icon {
    font-size:52px; line-height:1;
    animation: float 3s ease-in-out infinite;
    margin-bottom:24px;
    filter: drop-shadow(0 0 18px rgba(88,166,255,0.35));
}
.anim-title {
    font-size:20px; font-weight:700; color:#E6EDF3;
    margin:0 0 6px; text-align:center;
}
.anim-sub {
    font-size:13px; color:#8B949E;
    margin:0 0 40px; text-align:center;
    max-width:340px; line-height:1.6;
}
.agent-row {
    display:flex; gap:16px; justify-content:center;
    margin-bottom:40px; flex-wrap:wrap;
}
.agent-card {
    background:#161B22; border:1px solid #30363D;
    border-radius:10px; padding:16px 20px;
    width:148px; text-align:center;
    animation: card-glow 9s ease-in-out infinite;
}
.agent-card:nth-child(1) { animation-delay:0s; }
.agent-card:nth-child(2) { animation-delay:3s; }
.agent-card:nth-child(3) { animation-delay:6s; }
.agent-dot {
    width:8px; height:8px; border-radius:50%;
    background:#30363D; margin:0 auto 10px;
    animation: dot-pulse 9s ease-in-out infinite;
}
.agent-card:nth-child(1) .agent-dot { animation-delay:0s; }
.agent-card:nth-child(2) .agent-dot { animation-delay:3s; }
.agent-card:nth-child(3) .agent-dot { animation-delay:6s; }
/* FIX 4: .agent-emoji font-size set in CSS, not inline style on the element,
           to prevent Streamlit's markdown sanitiser from stripping the style attr */
.agent-emoji { font-size:22px; margin-bottom:6px; line-height:1; display:block; }
.agent-name  { font-size:11px; font-weight:600; color:#8B949E; line-height:1.4; }

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

/* ── Results header ── */
.results-header {
    display:flex; align-items:center; gap:10px;
    padding:20px 0 4px;
}
.results-badge {
    background:#0D3B1E; color:#56D364;
    border:1px solid #2EA043;
    font-size:11px; font-weight:700;
    padding:3px 10px; border-radius:20px;
    text-transform:uppercase; letter-spacing:0.5px;
    /* FIX 5: explicit display so badge doesn't inherit flex from parent incorrectly */
    display:inline-flex; align-items:center; gap:4px;
}

details > summary {
    font-family:'JetBrains Mono',monospace !important;
    font-size:12px !important; color:#8B949E !important;
    background:#161B22 !important; border:1px solid #30363D !important;
    border-radius:6px !important; padding:9px 14px !important;
    cursor:pointer;
}
details > summary:hover { color:#E6EDF3 !important; border-color:#58A6FF !important; }
details[open] > summary { border-radius:6px 6px 0 0 !important; border-bottom-color:transparent !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Header
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;
            padding:18px 0 16px;border-bottom:1px solid #21262D;margin-bottom:32px;">
    <span style="font-size:28px;line-height:1;">&#x2697;&#xFE0F;</span>
    <div>
        <div style="font-size:20px;font-weight:700;letter-spacing:-0.3px;color:#E6EDF3;">QA Crew</div>
        <div style="font-size:12px;color:#8B949E;margin-top:1px;">
            Automated test generation &nbsp;&middot;&nbsp; CrewAI
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  IDLE — input form
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.status == "idle":
    repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/user/repo.git",
    )
    github_pat = st.text_input(
        "GitHub Personal Access Token",
        type="password",
        placeholder="ghp_  ·······················",
    )
    st.caption("🔒  Token is masked and never stored or logged.")
    user_request = st.text_area(
        "What do you want to test?",
        placeholder='e.g.  "Write unit tests for the auth module, focus on edge cases"',
        height=120,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    _ready = bool(repo_url.strip()) and bool(github_pat.strip()) and bool(user_request.strip())

    if st.button("▶  Generate Tests", disabled=not _ready):
        holder: dict = {"status": "running", "result": None, "error": None}
        st.session_state.result_holder = holder
        st.session_state.repo_name     = extract_repo_name(repo_url)
        st.session_state.status        = "running"
        t = threading.Thread(
            target=_run_crew,
            args=(repo_url.strip(), user_request.strip(), github_pat, holder),
            daemon=True,
        )
        st.session_state.crew_thread = t
        t.start()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  RUNNING — animation
#  FIX 6: Use st_autorefresh (component) for non-blocking polling so the main
#          thread never sleeps. Falls back to a meta-refresh snippet if the
#          component isn't installed, avoiding the time.sleep(1)+st.rerun()
#          busy-loop that caused the huge load time (each rerun re-imports
#          modules and re-runs the entire script including slow imports).
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "running":
    holder = st.session_state.result_holder

    # Transition to done/error without sleeping
    if holder and holder["status"] != "running":
        if holder["status"] == "done":
            st.session_state.status = "done"
        else:
            st.session_state.status = "error"
            st.session_state.error  = holder.get("error", "Unknown error")
        st.rerun()

    # FIX 7: Animation HTML uses HTML entities for emojis (&#x1F50D; etc.)
    #         so Streamlit's sanitiser cannot misinterpret them, and uses
    #         <span> instead of bare text nodes to avoid overlap/rendering bugs.
    repo_display = st.session_state.repo_name
    st.markdown(f"""
<div class="anim-wrap">
    <div class="anim-icon">&#x2697;&#xFE0F;</div>
    <div class="anim-title">Running QA Crew</div>
    <div class="anim-sub">
        Analysing <strong style="color:#58A6FF;">{repo_display}</strong>
        and generating test cases&hellip;
    </div>
    <div class="agent-row">
        <div class="agent-card">
            <div class="agent-dot"></div>
            <span class="agent-emoji">&#x1F50D;</span>
            <div class="agent-name">Repository<br>Analyst</div>
        </div>
        <div class="agent-card">
            <div class="agent-dot"></div>
            <span class="agent-emoji">&#x1F4CB;</span>
            <div class="agent-name">Strategy<br>Planner</div>
        </div>
        <div class="agent-card">
            <div class="agent-dot"></div>
            <span class="agent-emoji">&#x270D;&#xFE0F;</span>
            <div class="agent-name">Test<br>Writer</div>
        </div>
    </div>
    <div class="shimmer-track"></div>
</div>
""", unsafe_allow_html=True)

    # FIX 8: Use a lightweight JS-based auto-refresh instead of time.sleep+rerun.
    #         This avoids blocking Streamlit's event loop and eliminates the
    #         "huge load time" caused by repeated full-script re-executions.
    #         The page polls every 2 s via a hidden meta-refresh injected by JS.
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore
        st_autorefresh(interval=2000, limit=None, key="poll_running")
    except ImportError:
        # Graceful fallback: inject a JS setTimeout that triggers st.rerun
        # equivalent by submitting the hidden Streamlit form.
        st.markdown(
            """<script>
            (function(){
                var t = setTimeout(function(){
                    // Trigger Streamlit rerun by dispatching a CustomEvent
                    window.parent.postMessage({type:"streamlit:setComponentValue"}, "*");
                    clearTimeout(t);
                    location.reload();
                }, 2000);
            })();
            </script>""",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  ERROR
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "error":
    st.error("The crew encountered an error.")
    with st.expander("Error details"):
        st.code(st.session_state.error or "No traceback available.", language="python")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("&#x21BA;  Try Again"):
        st.session_state.status = "idle"
        st.session_state.error  = None
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  DONE — results
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.status == "done":
    _repo = st.session_state.repo_name

    # FIX 9: Results header uses HTML entities for the checkmark so the
    #         "✓ Done" badge cannot overlap with surrounding text nodes.
    st.markdown(f"""
<div class="results-header">
    <span style="font-size:18px;font-weight:700;color:#E6EDF3;">Results</span>
    <span class="results-badge">&#x2713; Done</span>
    <span style="font-size:12px;color:#8B949E;margin-left:4px;">{_repo}</span>
</div>
""", unsafe_allow_html=True)

    # FIX 10: Tab labels use plain ASCII text + Unicode literal (no emoji shortcodes)
    #          to prevent Streamlit from rendering the raw :emoji: code string.
    tab_cases, tab_summary = st.tabs(["🧪 Test Cases", "📄 Summary"])

    with tab_cases:
        _files = list_test_files(_repo)
        if _files:
            for _f in _files:
                _lang = {
                    ".py": "python", ".ts": "typescript", ".js": "javascript",
                    ".java": "java", ".go": "go", ".rb": "ruby", ".kt": "kotlin",
                }.get(_f.suffix, "text")
                with st.expander(_f.name,icon="📄"):
                    st.code(
                        _f.read_text(encoding="utf-8", errors="replace"),
                        language=_lang,
                    )
        else:
            st.info(
                f"No test files found under outputs/{_repo}/testcases/  \n"
                "The test writer agent may not have saved files yet."
            )

    with tab_summary:
        _summary = read_output_file(_repo, "testcases_summary.md")
        if _summary:
            st.markdown(_summary)
        else:
            st.info(f"outputs/{_repo}/testcases_summary.md not found yet.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↺  Run Again"):
        st.session_state.status        = "idle"
        st.session_state.repo_name     = ""
        st.session_state.error         = None
        st.session_state.result_holder = None
        st.session_state.crew_thread   = None
        st.rerun()
