import streamlit as st
import json
import os


# Page config

st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="📄",
    layout="centered",
)


# Minimal custom CSS

st.markdown("""
<style>
    .main { max-width: 760px; margin: auto; }
    .stTextArea textarea { font-size: 14px; }
    .result-box {
        background: #f8f9fa;
        border-left: 4px solid #4f8ef7;
        border-radius: 6px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .score-badge {
        display: inline-block;
        background: #4f8ef7;
        color: white;
        font-size: 2rem;
        font-weight: 700;
        border-radius: 50%;
        width: 64px; height: 64px;
        line-height: 64px;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .verdict-hire   { color: #16a34a; font-weight: 700; font-size: 1.2rem; }
    .verdict-nohire { color: #dc2626; font-weight: 700; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)



# Helper: call real API  (set OPENAI_API_KEY)

def analyze_with_openai(resume: str, job_desc: str) -> dict:
    """Uses OpenAI ChatCompletion. Requires OPENAI_API_KEY env var."""
    from openai import OpenAI          # pip install openai
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    system = (
        "You are an expert HR recruiter and resume screener. "
        "Respond ONLY with a valid JSON object — no markdown, no extra text."
    )
    user = f"""
Analyze the following resume against the job description.

RESUME:
{resume}

JOB DESCRIPTION:
{job_desc}

Return a JSON object with exactly these keys:
{{
  "match_score": <integer 1-10>,
  "key_strengths": [<list of strings>],
  "weaknesses": [<list of strings>],
  "verdict": "<Hire | Not Hire>",
  "summary": "<one sentence reason>"
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    return json.loads(raw)



# Helper: mock response (no API key needed)

def analyze_mock(resume: str, job_desc: str) -> dict:
    """
    Simple keyword-matching mock — no API required.
    Replace this with analyze_with_openai() once you add your API key.
    """
    resume_lower   = resume.lower()
    job_desc_lower = job_desc.lower()

    # Extract rough skill words from JD (words > 4 chars, rough heuristic)
    jd_words  = {w.strip(".,()") for w in job_desc_lower.split() if len(w) > 4}
    res_words = {w.strip(".,()") for w in resume_lower.split()   if len(w) > 4}

    matched  = jd_words & res_words
    missing  = jd_words - res_words

    score = min(10, max(1, round(len(matched) / max(len(jd_words), 1) * 10)))

    strengths = list(matched)[:5] if matched else ["General professional background"]
    weaknesses = list(missing)[:5] if missing else ["Could not detect gaps"]

    verdict = "Hire" if score >= 6 else "Not Hire"
    summary = (
        f"Candidate matches ~{score*10}% of job keywords. "
        f"{'Recommend moving forward.' if verdict == 'Hire' else 'Significant gaps detected.'}"
    )

    return {
        "match_score":   score,
        "key_strengths": [s.title() for s in strengths],
        "weaknesses":    [w.title() for w in weaknesses],
        "verdict":       verdict,
        "summary":       summary,
    }



# UI

st.title("📄 AI Resume Screener")
st.caption("Paste a resume and job description — get an instant match analysis.")

col1, col2 = st.columns(2)
with col1:
    resume = st.text_area(
        "Resume",
        placeholder="Paste the candidate's resume here…",
        height=280,
    )
with col2:
    job_desc = st.text_area(
        "Job Description",
        placeholder="Paste the job description here…",
        height=280,
    )

# ── Toggle: real API vs mock ──────────────────
use_api = st.checkbox(
    "Use OpenAI API (requires OPENAI_API_KEY set as env var)",
    value=False,
)

analyze_btn = st.button("🔍 Analyze", use_container_width=True, type="primary")


# Analysis

if analyze_btn:
    if not resume.strip() or not job_desc.strip():
        st.warning("⚠️ Please paste both a resume and a job description before analyzing.")
    else:
        with st.spinner("Analyzing…"):
            try:
                if use_api:
                    result = analyze_with_openai(resume, job_desc)
                else:
                    result = analyze_mock(resume, job_desc)
            except Exception as e:
                st.error(f"Error during analysis: {e}")
                st.stop()

        st.divider()
        st.subheader("📊 Analysis Results")

        # ── Score ───────────────────────────────
        score = result["match_score"]
        color = "#16a34a" if score >= 7 else "#f59e0b" if score >= 5 else "#dc2626"
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:1rem;">
            <div class="score-badge" style="background:{color};">{score}</div>
            <div style="color:#6b7280;font-size:0.9rem;">out of 10</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Strengths ───────────────────────────
        with st.container():
            st.markdown("**✅ Key Strengths**")
            for s in result["key_strengths"]:
                st.markdown(f"- {s}")

        st.markdown("")

        # ── Weaknesses ──────────────────────────
        with st.container():
            st.markdown("**❌ Weaknesses / Missing Skills**")
            for w in result["weaknesses"]:
                st.markdown(f"- {w}")

        st.markdown("")

        # ── Verdict ─────────────────────────────
        verdict = result["verdict"]
        cls     = "verdict-hire" if verdict == "Hire" else "verdict-nohire"
        icon    = "✅😊" if verdict == "Hire" else "🚫"
        st.markdown(
            f'<p class="{cls}">{icon} Final Verdict: {verdict}</p>',
            unsafe_allow_html=True,
        )
        st.info(result.get("summary", ""))