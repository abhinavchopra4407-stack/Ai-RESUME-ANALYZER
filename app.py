import streamlit as st
import PyPDF2
import re
import pandas as pd
import plotly.express as px
import base64
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import json
from datetime import datetime, timedelta, timezone
import random
import yagmail
import os
import requests
from io import BytesIO
import hashlib

# ============= CONFIGURATION =============
VERSION = "2.0.0"
APP_NAME = "AI Resume Analyzer"
APP_DESCRIPTION = "AI-powered resume insights to match your dream job"

# ============= INDIAN TIMEZONE =============
def get_indian_time():
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=5, minutes=30)

# ============= SESSION STATE INITIALIZATION =============
session_defaults = {
    "logged_in": False, "otp": None, "otp_expiry": None, "otp_attempts": 0,
    "otp_resend_attempts": 0, "otp_locked_until": None, "email": None,
    "username": None, "analyze": False, "saved": False, "final_score": None,
    "job_role": None, "matched": [], "missing": [], "resume_text": None,
    "uploaded_file_name": None, "last_otp_sent_time": None, "timer_running": False,
    "chat_history": [], "current_job_role": "", "matched_skills": [], "missing_skills": []
}

for key, default in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============= PAGE CONFIG =============
st.set_page_config(
    page_title=f"{APP_NAME} - Smart Career Tool",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============= HELPER FUNCTIONS =============

def generate_otp():
    return str(random.randint(100000, 999999))

def hash_email(email):
    return hashlib.sha256(email.encode()).hexdigest()[:8]

def save_history(username, job_role, score):
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    if username not in data:
        data[username] = []

    data[username].append({
        "job_role": job_role,
        "score": score,
        "date": get_indian_time().strftime("%d-%m-%Y %I:%M:%S %p IST")
    })

    with open("history.json", "w") as f:
        json.dump(data, f, indent=4)

def delete_history(username, index=None):
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        return False
    
    if username in data:
        if index is None:
            data[username] = []
        elif 0 <= index < len(data[username]):
            data[username].pop(index)
        
        with open("history.json", "w") as f:
            json.dump(data, f, indent=4)
        return True
    return False

def send_otp(email, otp):
    try:
        if "EMAIL" not in st.secrets or "PASSWORD" not in st.secrets:
            return True
            
        yag = yagmail.SMTP(user=st.secrets["EMAIL"], password=st.secrets["PASSWORD"])
        current_ist = get_indian_time()
        
        yag.send(
            to=email,
            subject=f"Your OTP - {APP_NAME}",
            contents=f"""
            🔐 Your Login OTP: {otp}
            
            Valid for 2 minutes only.
            Time: {current_ist.strftime('%I:%M:%S %p IST')}
            
            Never share this OTP with anyone.
            """
        )
        return True
    except:
        print(f"📧 OTP for {email}: {otp}")
        return True

def is_otp_expired():
    if st.session_state.otp_expiry is None:
        return True
    return get_indian_time() > st.session_state.otp_expiry

def is_account_locked():
    if st.session_state.otp_locked_until is None:
        return False
    return get_indian_time() < st.session_state.otp_locked_until

def reset_otp_state():
    st.session_state.otp = None
    st.session_state.otp_expiry = None
    st.session_state.otp_attempts = 0
    st.session_state.otp_resend_attempts = 0
    st.session_state.timer_running = False

def get_ai_response(prompt, context=""):
    try:
        if "OPENROUTER_API_KEY" in st.secrets:
            headers = {
                "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "qwen/qwen-2.5-7b-instruct:free",
                "messages": [{"role": "user", "content": f"Context: {context}\n\nQuestion: {prompt}"}],
                "max_tokens": 300
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        
        return get_fallback_response(prompt, context)
    except:
        return get_fallback_response(prompt, context)

def get_fallback_response(prompt, context=""):
    prompt_lower = prompt.lower()
    if "improve" in prompt_lower or "resume" in prompt_lower:
        return "🎯 **Quick Resume Tips:**\n• Use strong action verbs (Developed, Built, Optimized)\n• Quantify achievements with numbers\n• Tailor to job description keywords\n• Keep it concise (1-2 pages)\n• Highlight most relevant skills first"
    elif "career" in prompt_lower:
        return "🚀 **Career Advice:**\n• Build in-demand skills\n• Get relevant certifications\n• Create portfolio projects\n• Network on LinkedIn\n• Apply to 10+ jobs daily"
    elif "skill" in prompt_lower:
        return "💪 **Skill Development:**\n• Take online courses (Coursera, Udemy)\n• Build small projects daily\n• Contribute to open-source\n• Practice on LeetCode/HackerRank\n• Join study groups"
    elif "project" in prompt_lower:
        return "🚀 **Project Ideas:**\n• Portfolio website\n• Full-stack web app\n• Data analysis dashboard\n• Mobile app\n• Automation tool\n• API integration project"
    else:
        return "💡 **I'm your AI Career Assistant!**\n\nAsk me about:\n📝 Resume improvement\n🎯 Career paths\n💪 Skill development\n🚀 Project ideas\n🎤 Interview prep\n📊 Job search strategies"

def create_professional_pdf(report_data, user_email):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#6366f1'), alignment=TA_CENTER, spaceAfter=30, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#22c55e'), spaceBefore=20, spaceAfter=10, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=11, textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=6)
    score_style = ParagraphStyle('ScoreStyle', parent=styles['Normal'], fontSize=36, textColor=colors.HexColor('#22c55e'), alignment=TA_CENTER, spaceAfter=20, fontName='Helvetica-Bold')
    
    elements = []
    
    # Cover Page
    elements.append(Paragraph(f"{APP_NAME} Report", title_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("🤖", ParagraphStyle('Icon', parent=styles['Normal'], fontSize=48, alignment=TA_CENTER)))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"<b>Overall Score</b>", heading_style))
    elements.append(Paragraph(f"{report_data['score']}%", score_style))
    
    score_text = "🌟 Excellent" if report_data['score'] >= 80 else "📈 Good" if report_data['score'] >= 60 else "⚠️ Needs Improvement"
    elements.append(Paragraph(f"<b>Rating:</b> {score_text}", body_style))
    elements.append(Spacer(1, 30))
    
    # Report Info
    current_ist = get_indian_time()
    elements.append(Paragraph("Report Details", heading_style))
    elements.append(Paragraph(f"<b>Date:</b> {current_ist.strftime('%d-%m-%Y')}", body_style))
    elements.append(Paragraph(f"<b>Time:</b> {current_ist.strftime('%I:%M:%S %p IST')}", body_style))
    elements.append(Paragraph(f"<b>User:</b> {user_email}", body_style))
    elements.append(Paragraph(f"<b>Target Role:</b> {report_data['job_role'].title()}", body_style))
    elements.append(Spacer(1, 20))
    
    # Skills Analysis
    elements.append(PageBreak())
    elements.append(Paragraph("Skills Analysis", heading_style))
    elements.append(Paragraph("✅ Matched Skills", ParagraphStyle('SubHead', parent=styles['Heading3'], fontSize=14, textColor=colors.HexColor('#22c55e'), spaceAfter=8)))
    for skill in report_data['matched']:
        elements.append(Paragraph(f"• {skill}", body_style))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("❌ Missing Skills (Priority)", ParagraphStyle('SubHead', parent=styles['Heading3'], fontSize=14, textColor=colors.HexColor('#ef4444'), spaceAfter=8)))
    for skill in report_data['missing']:
        elements.append(Paragraph(f"• {skill}", body_style))
    
    # Score Table
    total = len(report_data['matched']) + len(report_data['missing'])
    coverage = int((len(report_data['matched']) / total) * 100) if total > 0 else 0
    table_data = [
        ["Metric", "Value", "Status"],
        ["Skill Match", f"{report_data['score']}%", "✅" if report_data['score'] >= 60 else "⚠️"],
        ["Skill Coverage", f"{coverage}%", "✅" if coverage >= 50 else "⚠️"],
        ["Total Skills", str(total), "📊"],
        ["Matched", str(len(report_data['matched'])), "✅"],
        ["Missing", str(len(report_data['missing'])), "📚"]
    ]
    t = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (2,0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0,0), (2,0), colors.whitesmoke),
        ('ALIGN', (0,0), (2,-1), 'CENTER'),
        ('FONTNAME', (0,0), (2,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (2,-1), 1, colors.grey),
    ]))
    elements.append(t)
    
    # Recommendations
    elements.append(PageBreak())
    elements.append(Paragraph("Recommendations", heading_style))
    recs = [
        f"1. Focus on learning: {', '.join(report_data['missing'][:3])}" if report_data['missing'] else "1. Great job! Maintain your skills",
        "2. Build 2-3 portfolio projects",
        "3. Get relevant certifications",
        "4. Quantify achievements with numbers",
        "5. Tailor resume for each application"
    ]
    for rec in recs[:5]:
        elements.append(Paragraph(rec, body_style))
        elements.append(Spacer(1, 8))
    
    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"<hr/><font size=8>Generated by {APP_NAME} v{VERSION} • {current_ist.strftime('%d-%m-%Y %H:%M:%S IST')}</font>", body_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def extract_text(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def extract_skills(text):
    skills_db = {
        "data scientist": ["python", "machine learning", "pandas", "numpy", "sql", "statistics", "tensorflow", "keras"],
        "web developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "express", "git"],
        "data analyst": ["excel", "sql", "power bi", "tableau", "python", "pandas", "matplotlib"],
        "ml engineer": ["python", "tensorflow", "pytorch", "scikit-learn", "docker", "kubernetes", "aws"],
        "backend developer": ["python", "java", "node.js", "sql", "mongodb", "rest api", "docker"],
        "frontend developer": ["html", "css", "javascript", "react", "vue", "angular", "bootstrap"],
        "full stack developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "express", "git"],
        "devops engineer": ["docker", "kubernetes", "jenkins", "aws", "linux", "terraform", "ci/cd"],
        "cybersecurity analyst": ["network security", "penetration testing", "firewall", "encryption", "linux"],
    }
    text_lower = text.lower()
    skills = []
    for role_skills in skills_db.values():
        for skill in role_skills:
            if skill in text_lower:
                skills.append(skill)
    return list(set(skills))

def match_skills(user_skills, role):
    role_skills = {
        "data scientist": ["python", "machine learning", "pandas", "numpy", "sql", "statistics", "tensorflow", "keras"],
        "web developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "express", "git"],
        "data analyst": ["excel", "sql", "power bi", "tableau", "python", "pandas", "matplotlib"],
        "ml engineer": ["python", "tensorflow", "pytorch", "scikit-learn", "docker", "kubernetes", "aws"],
        "backend developer": ["python", "java", "node.js", "sql", "mongodb", "rest api", "docker"],
        "frontend developer": ["html", "css", "javascript", "react", "vue", "angular", "bootstrap"],
        "full stack developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "express", "git"],
        "devops engineer": ["docker", "kubernetes", "jenkins", "aws", "linux", "terraform", "ci/cd"],
        "cybersecurity analyst": ["network security", "penetration testing", "firewall", "encryption", "linux"],
    }
    required = role_skills.get(role.lower(), [])
    matched = [s for s in required if s in user_skills]
    missing = [s for s in required if s not in user_skills]
    score = int((len(matched) / len(required)) * 100) if required else 0
    return matched, missing, score

# ============= LOGIN PAGE =============
def login_page():
    st.markdown(f"""
    <div style='text-align: center; padding: 40px 20px;'>
        <h1 style='font-size: 52px; background: linear-gradient(135deg, #6366f1, #22c55e); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            🤖 {APP_NAME}
        </h1>
        <p style='color: #888; font-size: 18px;'>{APP_DESCRIPTION}</p>
        <p style='color: #666; font-size: 14px;'>v{VERSION}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if is_account_locked():
        remaining = (st.session_state.otp_locked_until - get_indian_time()).seconds
        st.error(f"🔒 Account locked for {remaining // 60} minutes. Try again later.")
        st.stop()
    
    with st.form("login_form"):
        email = st.text_input("📧 Email Address", placeholder="you@example.com")
        col1, col2 = st.columns(2)
        
        with col1:
            send_disabled = False
            send_text = "📨 Send OTP"
            if st.session_state.last_otp_sent_time:
                time_since = (get_indian_time() - st.session_state.last_otp_sent_time).seconds
                if time_since < 30:
                    send_disabled = True
                    send_text = f"⏳ Wait {30 - time_since}s"
            
            if st.form_submit_button(send_text, use_container_width=True, disabled=send_disabled):
                if email and re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    if st.session_state.otp_resend_attempts < 5:
                        with st.spinner("📧 Sending OTP..."):
                            otp = generate_otp()
                            st.session_state.otp = otp
                            st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                            st.session_state.email = email
                            st.session_state.last_otp_sent_time = get_indian_time()
                            st.session_state.otp_resend_attempts += 1
                            st.session_state.timer_running = True
                            if send_otp(email, otp):
                                st.success("✅ OTP sent successfully! Check your email.")
                    else:
                        st.error("❌ Maximum resend limit reached")
                else:
                    st.error("❌ Please enter a valid email address")
        
        with col2:
            if st.form_submit_button("🔄 Resend OTP", use_container_width=True):
                if email and st.session_state.otp_resend_attempts < 5:
                    with st.spinner("📧 Resending OTP..."):
                        otp = generate_otp()
                        st.session_state.otp = otp
                        st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                        st.session_state.last_otp_sent_time = get_indian_time()
                        st.session_state.otp_resend_attempts += 1
                        send_otp(email, otp)
                        st.success("✅ New OTP sent!")
                else:
                    st.error("❌ Please enter email or limit reached")
        
        otp_input = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code")
        
        if st.session_state.otp_expiry:
            remaining = (st.session_state.otp_expiry - get_indian_time()).seconds
            if remaining > 0:
                st.progress(remaining / 120)
                st.caption(f"⏰ OTP expires in: {remaining // 60}:{remaining % 60:02d}")
        
        if st.form_submit_button("✅ Verify & Login", use_container_width=True, type="primary"):
            if not otp_input:
                st.error("❌ Please enter OTP")
            elif is_otp_expired():
                st.error("❌ OTP has expired. Please request a new one.")
            elif st.session_state.otp_attempts >= 3:
                st.session_state.otp_locked_until = get_indian_time() + timedelta(minutes=15)
                st.error("🔒 Too many failed attempts. Account locked for 15 minutes")
                st.rerun()
            elif otp_input == st.session_state.get("otp"):
                with st.spinner("🔄 Logging you in..."):
                    time.sleep(0.5)
                    st.session_state.logged_in = True
                    st.session_state.username = st.session_state.email
                    reset_otp_state()
                    st.success("✅ Login successful! Redirecting...")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.session_state.otp_attempts += 1
                remaining = 3 - st.session_state.otp_attempts
                st.error(f"❌ Invalid OTP. {remaining} attempt{'s' if remaining != 1 else ''} remaining")
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px;'>
        🔒 Secure OTP Login • 2 min expiry • Max 3 attempts • Max 5 resends
    </div>
    """, unsafe_allow_html=True)

# ============= MAIN APP =============
if not st.session_state.logged_in:
    login_page()
    st.stop()

# Custom CSS - NO WHITE BOXES
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }
    
    .block-container {
        background: transparent !important;
        padding: 20px;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        background: transparent !important;
    }
    
    .stMetric {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 15px;
        padding: 10px;
        backdrop-filter: blur(10px);
    }
    
    .stFileUploader > div {
        background: rgba(30, 41, 59, 0.3) !important;
        backdrop-filter: blur(10px);
        border: 2px dashed #6366f1;
        border-radius: 15px;
    }
    
    .stMarkdown, .stTextInput, .stButton {
        background: transparent !important;
    }
    
    .stMarkdown, .stMarkdown p, .stMarkdown div, .stMetric label {
        color: white !important;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #6366f1, #22c55e) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(99,102,241,0.4);
    }
    
    .stTextInput > div > div > input {
        background-color: #1e293b !important;
        color: white !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }
    
    .stAlert, .stInfo, .stSuccess, .stWarning, .stError {
        background: rgba(30, 41, 59, 0.5) !important;
        backdrop-filter: blur(10px);
        border: none !important;
    }
    
    .element-container, .stMarkdown, .stVerticalBlock {
        background: transparent !important;
    }
    
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.5);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
    }
    
    .stFileUploader label {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(f"""
<div style='text-align: center; padding: 20px;'>
    <h1 style='font-size: 42px; background: linear-gradient(135deg, #6366f1, #22c55e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>
        🤖 {APP_NAME}
    </h1>
    <p style='color: #aaa; font-size: 16px;'>{APP_DESCRIPTION}</p>
</div>
""", unsafe_allow_html=True)

# Stats Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 Version", VERSION)
with col2:
    st.metric("👤 User", hash_email(st.session_state.username))
with col3:
    st.metric("🕐 IST", get_indian_time().strftime("%I:%M %p"))
with col4:
    st.metric("📅 Date", get_indian_time().strftime("%d %b %Y"))

st.markdown("---")

# Main Content
main_col, chat_col = st.columns([2, 1])

with main_col:
    # Upload Section
    st.markdown("### 📄 Upload Your Resume")
    st.caption("💡 Supported format: PDF only")
    
    uploaded_file = st.file_uploader("Choose PDF file", type=["pdf"], label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f"✅ File uploaded successfully: {uploaded_file.name}")
        
        if not st.session_state.resume_text:
            with st.spinner("📖 Reading and analyzing your resume..."):
                time.sleep(1)
                resume_text = extract_text(uploaded_file)
                st.session_state.resume_text = resume_text
            st.success("✅ Resume processed successfully!")
        
        if not st.session_state.analyze:
            st.subheader("📄 Resume Preview")
            st.text_area("Preview", resume_text[:500], height=200, disabled=True)
            
            if st.button("🚀 Start Analysis", use_container_width=True):
                st.session_state.analyze = True
                st.rerun()
        
        else:
            job_role = st.text_input(
                "🎯 Target Job Role", 
                placeholder="Example: Data Scientist, Web Developer, Data Analyst, ML Engineer",
                help="Enter the job role you want to target for your resume"
            )
            
            if job_role:
                with st.spinner("🔍 Analyzing your resume against the job role..."):
                    time.sleep(1)
                    user_skills = extract_skills(resume_text)
                    matched, missing, score = match_skills(user_skills, job_role)
                    
                    if not st.session_state.saved:
                        save_history(st.session_state.username, job_role, score)
                        st.session_state.saved = True
                        st.success("✅ Analysis saved to history!")
                    
                    # Store for chat
                    st.session_state.current_job_role = job_role
                    st.session_state.matched_skills = matched
                    st.session_state.missing_skills = missing
                    st.session_state.final_score = score
                    
                    # Score Display
                    col1, col2, col3 = st.columns(3)
                    with col2:
                        st.markdown(f"""
                        <div style='text-align: center; padding: 20px; background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px); border-radius: 20px;'>
                            <h2 style='margin: 0; color: white;'>Match Score</h2>
                            <h1 style='font-size: 64px; margin: 0; color: #22c55e;'>{score}%</h1>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Feedback based on score
                    if score >= 80:
                        st.success("🌟 Excellent match! Your resume is well-aligned with this role!")
                    elif score >= 60:
                        st.info("📈 Good match! Add the missing skills to become an ideal candidate.")
                    else:
                        st.warning("⚠️ Low match. Consider upskilling or targeting a different role.")
                    
                    # Skills Display
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### ✅ Matched Skills")
                        if matched:
                            for s in matched:
                                st.write(f"✔ {s}")
                        else:
                            st.info("No matching skills found. Consider adding relevant keywords to your resume.")
                    
                    with col2:
                        st.markdown("### ❌ Missing Skills")
                        if missing:
                            for s in missing:
                                st.write(f"✖ {s}")
                        else:
                            st.success("🎉 Congratulations! You have all required skills!")
                    
                    # Actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📄 Download PDF Report", use_container_width=True):
                            with st.spinner("📄 Generating your professional PDF report..."):
                                report_data = {"job_role": job_role, "score": score, "matched": matched, "missing": missing}
                                pdf = create_professional_pdf(report_data, st.session_state.username)
                                st.success("✅ Report generated successfully!")
                                st.download_button("⬇ Click to Download PDF", pdf, f"Resume_Report_{job_role}.pdf", use_container_width=True)
                    
                    with col2:
                        if st.button("🔄 Analyze Another Resume", use_container_width=True):
                            with st.spinner("🔄 Resetting for new analysis..."):
                                time.sleep(0.5)
                                st.session_state.analyze = False
                                st.session_state.saved = False
                                st.session_state.resume_text = None
                                st.rerun()

with chat_col:
    st.markdown("### 🤖 AI Career Assistant")
    st.caption("💡 Ask me anything about resumes, careers, or skills!")
    st.markdown("---")
    
    # Chat History
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.info("👋 Hello! Ask me questions like:\n• How to improve my resume?\n• What career path is best?\n• How to learn missing skills?")
        else:
            for msg in st.session_state.chat_history[-8:]:
                if msg["role"] == "user":
                    st.markdown(f"**🙋 You:** {msg['content']}")
                else:
                    st.markdown(f"**🤖 AI:** {msg['content']}")
                st.markdown("---")
    
    # Quick Questions
    st.markdown("#### 📌 Quick Questions")
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        if st.button("📝 Improve Resume", use_container_width=True):
            with st.spinner("🤖 Getting AI response..."):
                ctx = f"Target: {st.session_state.current_job_role}"
                resp = get_ai_response("How to improve resume?", ctx)
                st.session_state.chat_history.append({"role": "user", "content": "How to improve my resume?"})
                st.session_state.chat_history.append({"role": "assistant", "content": resp})
                st.success("✅ Response received!")
                st.rerun()
        
        if st.button("💪 Missing Skills", use_container_width=True):
            with st.spinner("🤖 Getting AI response..."):
                resp = get_ai_response("How to learn missing skills?", f"Missing: {', '.join(st.session_state.missing_skills)}")
                st.session_state.chat_history.append({"role": "user", "content": "How to learn missing skills?"})
                st.session_state.chat_history.append({"role": "assistant", "content": resp})
                st.success("✅ Response received!")
                st.rerun()
    
    with col_q2:
        if st.button("🎯 Career Path", use_container_width=True):
            with st.spinner("🤖 Getting AI response..."):
                resp = get_ai_response("Career advice", f"Skills: {', '.join(st.session_state.matched_skills)}")
                st.session_state.chat_history.append({"role": "user", "content": "What career path should I follow?"})
                st.session_state.chat_history.append({"role": "assistant", "content": resp})
                st.success("✅ Response received!")
                st.rerun()
        
        if st.button("🚀 Project Ideas", use_container_width=True):
            with st.spinner("🤖 Getting AI response..."):
                resp = get_ai_response("Project ideas for portfolio", f"Role: {st.session_state.current_job_role}")
                st.session_state.chat_history.append({"role": "user", "content": "What projects should I build?"})
                st.session_state.chat_history.append({"role": "assistant", "content": resp})
                st.success("✅ Response received!")
                st.rerun()
    
    st.markdown("---")
    
    # Custom Question
    user_q = st.text_input("💬 Ask anything...", placeholder="e.g., Best Python projects for beginners?")
    if st.button("📨 Send", use_container_width=True) and user_q:
        with st.spinner("🤖 Thinking..."):
            resp = get_ai_response(user_q, f"Role: {st.session_state.current_job_role}")
            st.session_state.chat_history.append({"role": "user", "content": user_q})
            st.session_state.chat_history.append({"role": "assistant", "content": resp})
            st.success("✅ Response received!")
            st.rerun()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.success("✅ Chat history cleared!")
        st.rerun()

# History Section
st.markdown("---")
st.markdown("### 📜 Analysis History")
st.caption("Your previous resume analyses are saved here")

try:
    with open("history.json", "r") as f:
        hist_data = json.load(f)
except:
    hist_data = {}

if st.session_state.username in hist_data and hist_data[st.session_state.username]:
    for idx, item in enumerate(reversed(hist_data[st.session_state.username][-5:])):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"💼 **{item['job_role']}** | 🎯 Score: {item['score']}% | 🕒 {item['date']}")
        with col2:
            if st.button(f"🗑️ Delete", key=f"del_{idx}"):
                original_idx = len(hist_data[st.session_state.username]) - 1 - idx
                if delete_history(st.session_state.username, original_idx):
                    st.success("✅ Entry deleted successfully!")
                    st.rerun()
    
    st.caption(f"📊 Total analyses: {len(hist_data[st.session_state.username])}")
else:
    st.info("📭 No analysis history yet. Upload a resume and analyze it to get started!")

# ============= LOGOUT BUTTON AT BOTTOM =============
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        with st.spinner("🚪 Logging out..."):
            time.sleep(0.5)