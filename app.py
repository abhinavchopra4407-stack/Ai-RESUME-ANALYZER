import streamlit as st
import PyPDF2
import re
import pandas as pd
import plotly.express as px
import base64
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import json
from datetime import datetime, timedelta, timezone
import random
import yagmail
import os

# ============= INDIAN TIMEZONE (UTC +5:30) =============
def get_indian_time():
    """Get current Indian time"""
    utc_now = datetime.now(timezone.utc)
    ist_time = utc_now + timedelta(hours=5, minutes=30)
    return ist_time

# ============= STEP 1: IMMEDIATE SESSION STATE INITIALIZATION =============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "otp" not in st.session_state:
    st.session_state.otp = None
if "otp_expiry" not in st.session_state:
    st.session_state.otp_expiry = None
if "otp_attempts" not in st.session_state:
    st.session_state.otp_attempts = 0
if "otp_resend_attempts" not in st.session_state:
    st.session_state.otp_resend_attempts = 0
if "otp_locked_until" not in st.session_state:
    st.session_state.otp_locked_until = None
if "email" not in st.session_state:
    st.session_state.email = None
if "username" not in st.session_state:
    st.session_state.username = None
if "analyze" not in st.session_state:
    st.session_state.analyze = False
if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False
if "saved" not in st.session_state:
    st.session_state.saved = False
if "final_score" not in st.session_state:
    st.session_state.final_score = None
if "job_role" not in st.session_state:
    st.session_state.job_role = None
if "matched" not in st.session_state:
    st.session_state.matched = []
if "missing" not in st.session_state:
    st.session_state.missing = []
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "last_otp_sent_time" not in st.session_state:
    st.session_state.last_otp_sent_time = None
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False

# ============= STEP 2: PAGE CONFIGURATION =============
st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="🤖",
    layout="wide"
)

# ============= STEP 3: DEFINE ALL FUNCTIONS =============

def generate_otp():
    return str(random.randint(100000, 999999))

def save_history(username, job_role, score):
    """Save history to JSON file with Indian time"""
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    if username not in data:
        data[username] = []

    current_ist_time = get_indian_time()
    
    data[username].append({
        "job_role": job_role,
        "score": score,
        "date": current_ist_time.strftime("%d-%m-%Y %I:%M:%S %p IST")
    })

    with open("history.json", "w") as f:
        json.dump(data, f, indent=4)

def delete_history(username, index=None):
    """Delete specific history entry or all history for a user"""
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        return False
    
    if username in data:
        if index is None:
            data[username] = []
        else:
            if 0 <= index < len(data[username]):
                data[username].pop(index)
        
        with open("history.json", "w") as f:
            json.dump(data, f, indent=4)
        return True
    return False

def send_otp(email, otp):
    try:
        if "EMAIL" not in st.secrets or "PASSWORD" not in st.secrets:
            st.error("❌ Email configuration missing")
            return False
            
        yag = yagmail.SMTP(
            user=st.secrets["EMAIL"],
            password=st.secrets["PASSWORD"]
        )
        
        current_ist = get_indian_time()
        expiry_ist = current_ist + timedelta(minutes=2)
        
        yag.send(
            to=email,
            subject="Your Login OTP - AI Resume Analyzer",
            contents=f"""
            Your OTP is: {otp}
            
            This OTP is valid for 2 minutes only.
            Generated at: {current_ist.strftime('%I:%M:%S %p IST')}
            Expires at: {expiry_ist.strftime('%I:%M:%S %p IST')}
            
            Security Notice: Do not share this OTP with anyone.
            
            If you didn't request this, please ignore this email.
            """
        )
        return True
    except Exception as e:
        st.error("❌ Failed to send OTP. Please try again.")
        return False

def is_otp_expired():
    """Check if OTP has expired using Indian time"""
    if st.session_state.otp_expiry is None:
        return True
    return get_indian_time() > st.session_state.otp_expiry

def is_account_locked():
    """Check if account is locked using Indian time"""
    if st.session_state.otp_locked_until is None:
        return False
    return get_indian_time() < st.session_state.otp_locked_until

def reset_otp_state():
    """Reset OTP related session state"""
    st.session_state.otp = None
    st.session_state.otp_expiry = None
    st.session_state.otp_attempts = 0
    st.session_state.otp_resend_attempts = 0
    st.session_state.timer_running = False

def login_page():
    st.markdown("""
    <div style='text-align: center; padding: 40px 20px 20px 20px;'>
        <h1 style='font-size: 48px; background: linear-gradient(135deg, #6366f1 0%, #22c55e 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            🤖 AI RESUME ANALYZER
        </h1>
        <p style='color: #888; font-size: 18px;'>AI-powered resume insights to match your dream job 🚀</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Show current Indian time
    current_ist = get_indian_time()
    st.info(f"🕐 Current Indian Time: {current_ist.strftime('%I:%M:%S %p IST')} | {current_ist.strftime('%d-%m-%Y')}")
    
    # Check if account is locked
    if is_account_locked():
        lock_remaining = (st.session_state.otp_locked_until - get_indian_time()).seconds
        st.error(f"🔒 Too many failed attempts. Account locked for {lock_remaining // 60} minutes and {lock_remaining % 60} seconds.")
        st.stop()
    
    # Create a simple form for login
    with st.form(key="login_form"):
        email = st.text_input("📧 Email Address", placeholder="you@example.com")
        
        # Two columns for Send OTP and Resend OTP
        col1, col2 = st.columns(2)
        
        with col1:
            send_disabled = False
            send_text = "📨 Send OTP"
            if st.session_state.last_otp_sent_time:
                time_since = (get_indian_time() - st.session_state.last_otp_sent_time).seconds
                if time_since < 30:
                    send_disabled = True
                    send_text = f"⏳ Wait {30 - time_since}s"
            
            send_clicked = st.form_submit_button(send_text, use_container_width=True, disabled=send_disabled)
            if send_clicked:
                if not email:
                    st.error("❌ Please enter email address")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Please enter a valid email address")
                else:
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Maximum resend limit reached. Please try again later.")
                    else:
                        otp = generate_otp()
                        st.session_state.otp = otp
                        st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                        st.session_state.email = email
                        st.session_state.last_otp_sent_time = get_indian_time()
                        st.session_state.otp_resend_attempts += 1
                        st.session_state.timer_running = True
                        
                        if send_otp(email, otp):
                            st.success(f"✅ OTP sent successfully! Valid for 2 minutes.")
                        else:
                            st.error("❌ Failed to send OTP")
        
        with col2:
            resend_clicked = st.form_submit_button("🔄 Resend OTP", use_container_width=True)
            if resend_clicked:
                if not email:
                    st.error("❌ Please enter email address first")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Please enter a valid email address")
                else:
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Maximum resend limit (5) reached. Please try again later.")
                    else:
                        if st.session_state.last_otp_sent_time:
                            time_since = (get_indian_time() - st.session_state.last_otp_sent_time).seconds
                            if time_since < 30:
                                st.error(f"❌ Please wait {30 - time_since} seconds before resending")
                            else:
                                otp = generate_otp()
                                st.session_state.otp = otp
                                st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                                st.session_state.last_otp_sent_time = get_indian_time()
                                st.session_state.otp_resend_attempts += 1
                                st.session_state.timer_running = True
                                
                                if send_otp(email, otp):
                                    st.success(f"✅ New OTP sent! Valid for 2 minutes.")
                                else:
                                    st.error("❌ Failed to send OTP")
                        else:
                            otp = generate_otp()
                            st.session_state.otp = otp
                            st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                            st.session_state.last_otp_sent_time = get_indian_time()
                            st.session_state.otp_resend_attempts += 1
                            st.session_state.timer_running = True
                            
                            if send_otp(email, otp):
                                st.success(f"✅ OTP sent! Valid for 2 minutes.")
                            else:
                                st.error("❌ Failed to send OTP")
        
        # OTP Input
        user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code")
        
        # Show timer if OTP is active
        if st.session_state.otp_expiry and st.session_state.timer_running:
            remaining = (st.session_state.otp_expiry - get_indian_time()).seconds
            if remaining > 0:
                mins = remaining // 60
                secs = remaining % 60
                st.info(f"⏰ OTP expires in: {mins:02d}:{secs:02d}")
                st.progress(remaining / 120)
            else:
                st.warning("⚠️ OTP has expired! Please request a new one.")
                st.session_state.timer_running = False
        
        # VERIFY BUTTON - This is the key part
        st.markdown("---")
        verify_clicked = st.form_submit_button("✅ Verify OTP", use_container_width=True, type="primary")
        
        if verify_clicked:
            if not user_otp:
                st.error("❌ Please enter OTP")
            else:
                if is_otp_expired():
                    st.error("❌ OTP has expired. Please request a new OTP.")
                    reset_otp_state()
                    st.rerun()
                else:
                    if st.session_state.otp_attempts >= 3:
                        st.session_state.otp_locked_until = get_indian_time() + timedelta(minutes=15)
                        st.error("🔒 Too many failed attempts. Account locked for 15 minutes.")
                        st.rerun()
                    elif user_otp == st.session_state.get("otp"):
                        st.session_state.logged_in = True
                        st.session_state.username = st.session_state.email
                        reset_otp_state()
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.otp_attempts += 1
                        remaining = 3 - st.session_state.otp_attempts
                        st.error(f"❌ Invalid OTP. {remaining} attempts remaining.")
        
        st.markdown("---")
        
        # Security notice
        st.markdown("""
        <div style='background: #1e293b; padding: 12px; border-radius: 10px;'>
            <p style='color: #888; font-size: 12px; margin: 0;'>
            🔒 <strong>Security Features:</strong><br>
            • ⏰ OTP expires in <strong style='color:#22c55e'>2 minutes</strong><br>
            • 🔢 Max <strong style='color:#22c55e'>3</strong> verification attempts<br>
            • 🔄 Max <strong style='color:#22c55e'>5</strong> OTP resend requests<br>
            • 🔒 Account locks after 3 failed attempts for <strong style='color:#22c55e'>15 minutes</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)

def show_history(username):
    """Display user history with delete option"""
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    st.subheader("📜 Your Previous Reports")
    
    if username in data and data[username]:
        for idx, item in enumerate(reversed(data[username])):
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(f"💼 {item['job_role']} | 🎯 {item['score']}% | 🕒 {item['date']}")
            with col2:
                if st.button(f"🗑️", key=f"del_{idx}"):
                    original_idx = len(data[username]) - 1 - idx
                    if delete_history(username, original_idx):
                        st.success("✅ Entry deleted!")
                        st.rerun()
            with col3:
                if st.button(f"📄", key=f"view_{idx}"):
                    st.info(f"Report for {item['job_role']} - Score: {item['score']}%")
        
        if st.button("🗑️ Delete All History", use_container_width=True):
            if delete_history(username):
                st.success("✅ All history deleted!")
                st.rerun()
    else:
        st.info("No history yet. Upload a resume to get started!")

def set_bg(image_file):
    try:
        with open(image_file, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{data}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """, unsafe_allow_html=True)
    except:
        pass

def extract_text(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def extract_sections(text):
    sections = {"skills": "", "education": ""}
    text_lower = text.lower()
 
    skill_match = re.search(r"skills(.*?)(education|projects|experience|$)", text_lower, re.DOTALL)
    if skill_match:
        sections["skills"] = skill_match.group(1)
 
    edu_match = re.search(r"education(.*?)(projects|experience|skills|$)", text_lower, re.DOTALL)
    if edu_match:
        sections["education"] = edu_match.group(1)
 
    return sections

def clean_skills(text):
    return [s.strip().title() for s in re.split(r",|\n|•", text) if len(s.strip()) > 2]

def clean_education(text):
    lines = text.split("\n")
    return [l.strip() for l in lines if len(l.strip()) > 5]

# SKILL DATABASE
SKILL_DB = {
    "data scientist": ["python", "machine learning", "pandas", "numpy", "matplotlib", "seaborn", "sql", "statistics"],
    "ml engineer": ["python", "tensorflow", "pytorch", "deep learning", "nlp", "cnn", "model deployment"],
    "data analyst": ["excel", "sql", "power bi", "tableau", "python", "data visualization"],
    "business analyst": ["excel", "sql", "data analysis", "power bi", "communication", "problem solving"],
    "web developer": ["html", "css", "javascript", "react", "node.js", "mongodb"],
    "frontend developer": ["html", "css", "javascript", "react", "bootstrap", "ui/ux"],
    "backend developer": ["python", "java", "node.js", "sql", "api development", "database management"],
    "full stack developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "api"],
}

PROJECTS = {
    "data scientist": ["Customer Churn Prediction", "House Price Prediction", "Fraud Detection System"],
    "ml engineer": ["Image Classification using CNN", "Chatbot using NLP", "Recommendation System"],
    "data analyst": ["Sales Dashboard using Power BI", "Customer Segmentation Analysis", "Excel Data Cleaning Project"],
    "business analyst": ["Market Analysis Dashboard", "Customer Behavior Analysis", "Business KPI Tracker"],
    "web developer": ["Portfolio Website", "E-commerce Website", "Blog Platform"],
    "frontend developer": ["React Portfolio", "Weather App (API based)", "Netflix UI Clone"],
    "backend developer": ["REST API using Flask/Django", "Authentication System", "Blog Backend with Database"],
    "full stack developer": ["Full Stack E-commerce App", "MERN Social Media App", "Job Portal Website"],
}

def extract_skills(text):
    text = text.lower()
    skills = []
    for role in SKILL_DB.values():
        for s in role:
            if s in text:
                skills.append(s)
    return list(set(skills))

def match_skills(user_skills, role):
    required = SKILL_DB.get(role.lower(), [])
    matched = [s for s in required if s in user_skills]
    missing = [s for s in required if s not in user_skills]
    score = int((len(matched) / len(required)) * 100) if required else 0
    return matched, missing, score

def create_pdf(report_data):
    doc = SimpleDocTemplate("resume_report.pdf")
    styles = getSampleStyleSheet()
    elements = []

    current_ist = get_indian_time()
    
    elements.append(Paragraph("AI Resume Analysis Report", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Generated on: {current_ist.strftime('%d-%m-%Y %I:%M:%S %p IST')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"<b>Final Score:</b> {report_data['score']}%", styles['Heading2']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"<b>Target Role:</b> {report_data['job_role']}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>Matched Skills:</b>", styles['Heading2']))
    for skill in report_data['matched']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Missing Skills:</b>", styles['Heading2']))
    for skill in report_data['missing']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    elements.append(Spacer(1, 20))

    doc.build(elements)

# ============= STEP 4: CHECK LOGIN STATUS =============
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= STEP 5: MAIN APP =============

# Apply styling
st.markdown("""
<style>
.block-container {
    background: rgba(0, 0, 0, 0.2);
    padding: 20px;
    border-radius: 15px;
}
h1, h2, h3, h4, h5, h6, p, div, span, label {
    color: white !important;
}
input {
    background-color: #0f172a !important;
    color: white !important;
}
button {
    background: linear-gradient(90deg, #6366f1, #22c55e);
    color: white !important;
    border-radius: 8px !important;
}
button[kind="primary"] {
    background: linear-gradient(90deg, #22c55e, #6366f1) !important;
}
</style>
""", unsafe_allow_html=True)

# Set background
try:
    set_bg("robot.jpg")
except:
    pass

# Header
st.markdown("<h1 style='text-align:center;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
st.caption("AI-powered resume insights to match your dream job 🚀")

current_ist = get_indian_time()
st.info(f"🕐 Indian Standard Time (IST): {current_ist.strftime('%d-%m-%Y %I:%M:%S %p')}")

# Upload section
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        label_visibility="collapsed"
    )

if uploaded_file is not None:
    st.session_state.uploaded_file_name = uploaded_file.name
    st.markdown(f"""
    <div style='background: #0f172a; padding: 10px; border-radius: 8px; margin: 10px 0; text-align: center; border: 1px solid #22c55e;'>
        📄 <strong>Uploaded File:</strong> {uploaded_file.name}
    </div>
    """, unsafe_allow_html=True)
    
    with st.spinner("📄 Processing your resume..."):
        time.sleep(1)
        resume_text = extract_text(uploaded_file)
        st.session_state.resume_text = resume_text
    
    st.success("✅ File uploaded successfully!")
    
    if not st.session_state.analyze:
        st.subheader("📄 Resume Preview")
        st.text(resume_text[:1000])
        
        if st.button("🚀 Analyze Resume", use_container_width=True):
            st.session_state.analyze = True
            st.rerun()
    
    else:
        sections = extract_sections(resume_text)
        
        st.subheader("🎯 Enter Job Role")
        job_role = st.text_input("Example: data scientist", key="job_role_input")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("🧠 Resume Skills")
            skills = clean_skills(sections["skills"])
            for s in skills:
                st.write("•", s)
            
            st.subheader("🎓 Education")
            edu = clean_education(sections["education"])
            for e in edu:
                st.write("•", e)
        
        with col_right:
            if job_role:
                with st.spinner("🤖 Analyzing your resume..."):
                    user_skills = extract_skills(resume_text)
                    matched, missing, score = match_skills(user_skills, job_role)
                    
                    if not st.session_state.get('saved', False):
                        save_history(st.session_state.username, job_role, score)
                        st.session_state.saved = True
                    
                    st.subheader("🎯 Recommended Roles")
                    role_scores = {}
                    for role, skills_list in SKILL_DB.items():
                        match_count = sum(1 for s in skills_list if s in user_skills)
                        role_scores[role] = match_count
                    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
                    top_roles = [r[0].title() for r in sorted_roles[:3]]
                    st.success(f"Best suited roles: {', '.join(top_roles)}")
                    
                    st.subheader("📊 Score Breakdown")
                    skill_score = score
                    total_skills = len(matched) + len(missing)
                    resume_strength = int((len(matched) / total_skills) * 100) if total_skills > 0 else 0
                    final_score = int((skill_score + resume_strength) / 2)
                    
                    st.write(f"✔ Skill Match: {skill_score}%")
                    st.write(f"✔ Resume Strength: {resume_strength}%")
                    st.write(f"🎯 Final Score: {final_score}%")
                    
                    st.subheader("✅ You Have")
                    for m in matched:
                        st.write(f"• {m}")
                    
                    st.subheader("❌ Missing")
                    for m in missing:
                        st.write(f"• {m}")
                    
                    if st.button("🔄 Analyze Another Resume", use_container_width=True):
                        st.session_state.analyze = False
                        st.session_state.saved = False
                        st.rerun()

# Show history
st.markdown("---")
show_history(st.session_state.username)

# Logout button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("""
<div style='text-align: center; padding: 20px; margin-top: 20px;'>
    <p style='color: #666; font-size: 12px;'>© 2024 AI Resume Analyzer | Secure & Private</p>
</div>
""", unsafe_allow_html=True)