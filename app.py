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
from datetime import datetime, timedelta
import random
import yagmail
import os
import pytz

# ============= SET INDIAN TIMEZONE =============
IST = pytz.timezone('Asia/Kolkata')

def get_indian_time():
    """Get current Indian time"""
    return datetime.now(IST)

def format_indian_time(dt):
    """Format datetime in Indian timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    return dt.astimezone(IST)

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

    # Use Indian time for history entries
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
        expiry_ist = current_ist + timedelta(minutes=5)
        
        yag.send(
            to=email,
            subject="Your Login OTP - AI Resume Analyzer",
            contents=f"""
            Your OTP is: {otp}
            
            This OTP is valid for 5 minutes.
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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login to Continue")
        
        email = st.text_input("📧 Email Address", placeholder="you@example.com", key="login_email")
        
        # Send OTP button with resend cooldown
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            send_otp_disabled = False
            button_text = "📨 Send OTP"
            
            # Check resend cooldown (30 seconds)
            if st.session_state.last_otp_sent_time:
                time_since_last = (get_indian_time() - st.session_state.last_otp_sent_time).seconds
                if time_since_last < 30:
                    send_otp_disabled = True
                    button_text = f"⏳ Wait {30 - time_since_last}s"
            
            if st.button(button_text, use_container_width=True, disabled=send_otp_disabled):
                if not email:
                    st.error("❌ Please enter email address")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Please enter a valid email address")
                else:
                    # Check resend attempts limit (max 5 resends)
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Maximum resend limit reached. Please try again later.")
                    else:
                        otp = generate_otp()
                        st.session_state.otp = otp
                        # Set expiry to 5 minutes from now in Indian time
                        st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=5)
                        st.session_state.email = email
                        st.session_state.last_otp_sent_time = get_indian_time()
                        st.session_state.otp_resend_attempts += 1
                        
                        if send_otp(email, otp):
                            st.success(f"✅ OTP sent successfully! Valid for 5 minutes.")
                            st.info(f"⏰ OTP will expire at {st.session_state.otp_expiry.strftime('%I:%M:%S %p IST')}")
                        else:
                            st.error("❌ Failed to send OTP")
        
        with col_btn2:
            # Resend OTP button
            if st.button("🔄 Resend OTP", use_container_width=True):
                if not email:
                    st.error("❌ Please enter email address first")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Please enter a valid email address")
                else:
                    # Check resend attempts limit
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Maximum resend limit (5) reached. Please try again later.")
                    else:
                        # Check cooldown period
                        if st.session_state.last_otp_sent_time:
                            time_since_last = (get_indian_time() - st.session_state.last_otp_sent_time).seconds
                            if time_since_last < 30:
                                st.error(f"❌ Please wait {30 - time_since_last} seconds before resending")
                            else:
                                otp = generate_otp()
                                st.session_state.otp = otp
                                st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=5)
                                st.session_state.last_otp_sent_time = get_indian_time()
                                st.session_state.otp_resend_attempts += 1
                                
                                if send_otp(email, otp):
                                    st.success(f"✅ New OTP sent! Valid for 5 minutes.")
                                else:
                                    st.error("❌ Failed to send OTP")
                        else:
                            otp = generate_otp()
                            st.session_state.otp = otp
                            st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=5)
                            st.session_state.last_otp_sent_time = get_indian_time()
                            st.session_state.otp_resend_attempts += 1
                            
                            if send_otp(email, otp):
                                st.success(f"✅ OTP sent! Valid for 5 minutes.")
                            else:
                                st.error("❌ Failed to send OTP")
        
        user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code", key="login_otp")
        
        # Show OTP expiry time if OTP is sent
        if st.session_state.otp_expiry:
            remaining_time = (st.session_state.otp_expiry - get_indian_time()).seconds
            if remaining_time > 0:
                st.info(f"⏰ OTP expires in {remaining_time // 60}:{remaining_time % 60:02d} minutes (IST)")
                st.progress(remaining_time / 300)  # 300 seconds = 5 minutes
            else:
                st.warning("⚠️ OTP has expired. Please request a new one.")
        
        # Verify OTP button
        if st.button("✅ Verify & Login", use_container_width=True):
            if not user_otp:
                st.error("❌ Please enter OTP")
            else:
                # Check if OTP is expired
                if is_otp_expired():
                    st.error("❌ OTP has expired. Please request a new OTP.")
                    reset_otp_state()
                else:
                    # Check attempts limit (max 3 attempts)
                    if st.session_state.otp_attempts >= 3:
                        # Lock account for 15 minutes
                        st.session_state.otp_locked_until = get_indian_time() + timedelta(minutes=15)
                        st.error("🔒 Too many failed attempts. Account locked for 15 minutes.")
                        st.rerun()
                    elif user_otp == st.session_state.get("otp"):
                        st.session_state.logged_in = True
                        st.session_state.username = st.session_state.email
                        # Reset OTP state on successful login
                        reset_otp_state()
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.otp_attempts += 1
                        remaining_attempts = 3 - st.session_state.otp_attempts
                        st.error(f"❌ Invalid OTP. {remaining_attempts} attempts remaining.")
        
        # Security notice
        st.markdown("""
        <div style='background: #1e293b; padding: 12px; border-radius: 10px; margin-top: 20px;'>
            <p style='color: #888; font-size: 12px; margin: 0;'>
            🔒 <strong>Security Features (Indian Standard Time):</strong><br>
            • OTP expires in 5 minutes<br>
            • Max 3 verification attempts<br>
            • Max 5 OTP resend requests<br>
            • Account locks after 3 failed attempts for 15 minutes
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
    "android developer": ["java", "kotlin", "android sdk", "firebase", "rest api"],
    "ios developer": ["swift", "ios sdk", "xcode", "api integration"],
    "software engineer": ["data structures", "algorithms", "java", "python", "oop", "problem solving"],
    "devops engineer": ["docker", "kubernetes", "ci/cd", "aws", "linux", "shell scripting"],
    "cloud engineer": ["aws", "azure", "gcp", "cloud architecture", "networking"],
    "cyber security analyst": ["network security", "ethical hacking", "penetration testing", "cryptography"],
    "ai engineer": ["python", "machine learning", "deep learning", "tensorflow", "nlp"],
    "nlp engineer": ["python", "nlp", "text processing", "transformers", "machine learning"],
    "computer vision engineer": ["python", "opencv", "image processing", "deep learning", "cnn"],
    "game developer": ["unity", "c#", "game design", "graphics", "physics"],
    "blockchain developer": ["solidity", "ethereum", "smart contracts", "web3", "cryptography"],
    "qa engineer": ["testing", "selenium", "automation testing", "api testing", "bug tracking"]
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
    "software engineer": ["Library Management System", "Inventory Management System", "Online Code Compiler"],
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

    # Add timestamp with Indian time
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
    elements.append(Paragraph("<b>Recommended Learning Path:</b>", styles['Heading2']))
    for skill in report_data['missing'][:5]:
        elements.append(Paragraph(f"• Learn {skill} through projects and practice", styles['Normal']))
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
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #38bdf8; }
.feedback-text {
    color: #1a1a2e !important;
    font-weight: 500;
    line-height: 1.6;
}
.feedback-text p, .feedback-text div {
    color: #1a1a2e !important;
}
.uploaded-filename {
    background: #0f172a;
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
    text-align: center;
    border: 1px solid #22c55e;
}
</style>
""", unsafe_allow_html=True)

# Set background
try:
    set_bg("robot.jpg")
except:
    pass

# Header with title only
st.markdown("<h1 style='text-align:center;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
st.caption("AI-powered resume insights to match your dream job 🚀")

# Show current Indian time in main app
current_ist = get_indian_time()
st.info(f"🕐 Indian Standard Time (IST): {current_ist.strftime('%d-%m-%Y %I:%M:%S %p')}")

# Create layout
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("""
    <style>
    [data-testid="stFileUploader"] {
        border: 2px dashed #6366f1;
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        background: #0f172a;
    }
    </style>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        label_visibility="collapsed"
    )

if uploaded_file is not None:
    # Show readable filename
    st.session_state.uploaded_file_name = uploaded_file.name
    st.markdown(f"""
    <div class='uploaded-filename'>
        📄 <strong>Uploaded File:</strong> {uploaded_file.name}
    </div>
    """, unsafe_allow_html=True)
    
    # Process with spinner
    with st.spinner("📄 Processing your resume..."):
        time.sleep(1)
        resume_text = extract_text(uploaded_file)
        st.session_state.resume_text = resume_text
    
    st.success("✅ File uploaded successfully!")
    
    try:
        set_bg("Analyst.jpg")
    except:
        pass
    
    # Step 1: Preview and Analyze
    if not st.session_state.analyze:
        st.subheader("📄 Resume Preview")
        st.text(resume_text[:1000])
        
        if st.button("🚀 Analyze Resume", use_container_width=True):
            st.session_state.analyze = True
            st.rerun()
    
    # Step 2: Analysis
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
                    
                    if "saved" not in st.session_state or not st.session_state.saved:
                        save_history(st.session_state.username, job_role, score)
                        st.session_state.saved = True
                    
                    # Role suggestions
                    st.subheader("🎯 Recommended Roles")
                    role_scores = {}
                    for role, skills_list in SKILL_DB.items():
                        match_count = sum(1 for s in skills_list if s in user_skills)
                        role_scores[role] = match_count
                    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
                    top_roles = [r[0].title() for r in sorted_roles[:3]]
                    st.success(f"Best suited roles: {', '.join(top_roles)}")
                    
                    # Score breakdown
                    st.subheader("📊 Score Breakdown")
                    skill_score = score
                    total_skills = len(matched) + len(missing)
                    resume_strength = int((len(matched) / total_skills) * 100) if total_skills > 0 else 0
                    final_score = int((skill_score + resume_strength) / 2)
                    
                    st.write(f"✔ Skill Match: {skill_score}%")
                    st.write(f"✔ Resume Strength: {resume_strength}%")
                    st.write(f"🎯 Final Score: {final_score}%")
                    
                    # Store in session state
                    st.session_state.final_score = final_score
                    st.session_state.job_role = job_role
                    st.session_state.matched = matched
                    st.session_state.missing = missing
                    
                    # Resume Strength Analysis
                    st.subheader("📊 Resume Strength Analysis")
                    if score < 40:
                        st.error("Your resume is weak for this role. Focus on building core skills and projects.")
                    elif score < 70:
                        st.warning("Your resume is average. Improve by adding more relevant skills and projects.")
                    else:
                        st.success("Your resume is strong and well aligned with the job role!")
                    
                    if len(missing) > len(matched):
                        st.info("You are missing more skills than you have. Focus on skill development.")
                    else:
                        st.info("Good skill coverage. Now focus on projects and real-world experience.")
                    
                    # Feedback with dark text
                    st.subheader("📌 Feedback")
                    if score < 40:
                        feedback = f"""
                        <div class='feedback-text' style='background-color:#ffe6e6; padding:15px; border-radius:12px; border-left:5px solid #ef4444;'>
                            <p style='color:#1a1a2e !important; margin:0;'><strong>Your resume has limited matching skills for the role of {job_role}.</strong></p>
                            <p style='color:#1a1a2e !important;'>You need to focus on building strong fundamentals and adding relevant projects.</p>
                            <br>
                            <p style='color:#1a1a2e !important;'><strong>👉 Start with:</strong></p>
                            <ul style='color:#1a1a2e !important;'>
                                <li>Learning core concepts</li>
                                <li>Building 2–3 beginner projects</li>
                                <li>Adding missing skills like {", ".join(missing[:3])}</li>
                            </ul>
                        </div>
                        """
                    elif score < 70:
                        feedback = f"""
                        <div class='feedback-text' style='background-color:#fff3e6; padding:15px; border-radius:12px; border-left:5px solid #f59e0b;'>
                            <p style='color:#1a1a2e !important; margin:0;'><strong>Your profile is good but needs improvement for the role of {job_role}.</strong></p>
                            <p style='color:#1a1a2e !important;'>You already have some relevant skills like {", ".join(matched[:3])}.</p>
                            <br>
                            <p style='color:#1a1a2e !important;'><strong>👉 To improve:</strong></p>
                            <ul style='color:#1a1a2e !important;'>
                                <li>Learn advanced tools like {", ".join(missing[:3])}</li>
                                <li>Add real-world projects</li>
                                <li>Strengthen your resume with achievements</li>
                            </ul>
                        </div>
                        """
                    else:
                        feedback = f"""
                        <div class='feedback-text' style='background-color:#e6ffe6; padding:15px; border-radius:12px; border-left:5px solid #22c55e;'>
                            <p style='color:#1a1a2e !important; margin:0;'><strong>Excellent! Your resume is well aligned with the role of {job_role}.</strong></p>
                            <p style='color:#1a1a2e !important;'>You have strong skills like {", ".join(matched[:3])}.</p>
                            <br>
                            <p style='color:#1a1a2e !important;'><strong>👉 To go further:</strong></p>
                            <ul style='color:#1a1a2e !important;'>
                                <li>Work on advanced projects</li>
                                <li>Build a portfolio</li>
                                <li>Prepare for interviews</li>
                            </ul>
                        </div>
                        """
                    
                    st.markdown(feedback, unsafe_allow_html=True)
                    
                    # Resume Improvement Suggestions
                    st.subheader("✨ Resume Improvement Suggestions")
                    suggestions = []
                    if missing:
                        suggestions.append(f"Add these skills to your resume: {', '.join(missing[:4])}")
                    if score < 50:
                        suggestions.append("Include at least 2–3 strong projects related to your domain")
                        suggestions.append("Focus on building real-world applications")
                    suggestions.extend([
                        "Use action verbs like Developed, Built, Optimized",
                        "Add measurable results (e.g., improved accuracy by 20%)",
                        "Keep resume concise (1 page if fresher)",
                        "Highlight key technical skills clearly"
                    ])
                    for s in suggestions:
                        st.write(f"👉 {s}")
                    
                    # Skill Improvement Guide
                    SKILL_GUIDE = {
                        "tensorflow": "Learn deep learning & build CNN projects",
                        "nlp": "Work on chatbot or sentiment analysis",
                        "pytorch": "Practice model building with PyTorch",
                        "cnn": "Build image classification projects",
                        "machine learning": "Practice regression & classification models",
                        "statistics": "Focus on probability & distributions"
                    }
                    
                    st.subheader("📚 Skill Improvement Guide")
                    for skill in missing:
                        suggestion = SKILL_GUIDE.get(skill.lower(), "Practice this skill")
                        st.markdown(f"""
                        <div style="background-color:#1e293b; padding:10px; margin:6px; border-radius:10px; color:#38bdf8;">
                            👉 {skill}: {suggestion}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Skills display
                    st.subheader("✅ You Have")
                    for m in matched:
                        st.write(f"• {m}")
                    
                    st.subheader("❌ Missing")
                    for m in missing:
                        st.write(f"• {m}")
                    
                    # Skill Distribution Chart
                    st.subheader("📊 Skill Distribution")
                    data = {
                        "Category": ["Matched", "Missing"],
                        "Count": [len(matched), len(missing)]
                    }
                    fig = px.pie(
                        values=data["Count"],
                        names=data["Category"],
                        title="Skill Match Overview",
                        color=data["Category"],
                        color_discrete_map={"Matched": "#22c55e", "Missing": "#ef4444"}
                    )
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # PDF Report Generation
                    if st.button("📄 Generate PDF Report", use_container_width=True):
                        report_data = {
                            "job_role": job_role.title(),
                            "score": final_score,}