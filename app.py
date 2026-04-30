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
from datetime import datetime
import random
import yagmail
import os

# ============= STEP 1: IMMEDIATE SESSION STATE INITIALIZATION =============
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "otp" not in st.session_state:
    st.session_state.otp = None
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
    """Save history to JSON file - persists across logouts"""
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
        "date": datetime.now().strftime("%d-%m-%Y %H:%M")
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
            # Delete all history for this user
            data[username] = []
        else:
            # Delete specific entry
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
        
        yag.send(
            to=email,
            subject="Your Login OTP - AI Resume Analyzer",
            contents=f"Your OTP is: {otp}\n\nThis OTP is valid for this session only."
        )
        return True
    except Exception as e:
        st.error("❌ Failed to send OTP. Please try again.")
        return False

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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Login to Continue")
        
        email = st.text_input("📧 Email Address", placeholder="you@example.com")
        
        if st.button("📨 Send OTP", use_container_width=True):
            if not email:
                st.error("❌ Please enter email address")
            elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                st.error("❌ Please enter a valid email address")
            else:
                otp = generate_otp()
                st.session_state.otp = otp
                st.session_state.email = email
                
                if send_otp(email, otp):
                    st.success("✅ OTP sent successfully to your email!")
        
        user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code")
        
        if st.button("✅ Verify & Login", use_container_width=True):
            if not user_otp:
                st.error("❌ Please enter OTP")
            elif user_otp == st.session_state.get("otp"):
                st.session_state.logged_in = True
                st.session_state.username = st.session_state.email
                st.success("✅ Login successful! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid OTP. Please try again.")

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
                    # Calculate original index
                    original_idx = len(data[username]) - 1 - idx
                    if delete_history(username, original_idx):
                        st.success("✅ Entry deleted!")
                        st.rerun()
            with col3:
                if st.button(f"📄", key=f"view_{idx}"):
                    st.info(f"Report for {item['job_role']} - Score: {item['score']}%")
        
        # Option to delete all history
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

    elements.append(Paragraph("AI Resume Analysis Report", styles['Title']))
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
</style>
""", unsafe_allow_html=True)

# Set background
try:
    set_bg("robot.jpg")
except:
    pass

# Header with logout
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("<h1 style='text-align:center;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
    st.caption("AI-powered resume insights to match your dream job 🚀")
with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# Create layout without history at the top
# Just the upload section first
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
    try:
        with st.spinner("📄 Reading your resume..."):
            resume_text = extract_text(uploaded_file)
            st.session_state.resume_text = resume_text
        st.success("File uploaded successfully ✅")
    except Exception as e:
        st.error("❌ Error reading PDF. Please upload a valid file.")
    
    try:
        set_bg("Analyst.jpg")
    except:
        pass
    
    # Step 1: Preview and Analyze
    if not st.session_state.analyze:
        st.subheader("📄 Resume Preview")
        st.text(resume_text[:1000])
        
        if st.button("🚀 Analyze Resume"):
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
                    
                    # Store in session state for PDF generation
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
                    
                    # Feedback
                    st.subheader("📌 Feedback")
                    if score < 40:
                        feedback = f"""
                        Your resume has limited matching skills for the role of {job_role}.
                        
                        You need to focus on building strong fundamentals and adding relevant projects.
                        
                        👉 Start with:
                        • Learning core concepts
                        • Building 2–3 beginner projects
                        • Adding missing skills like {", ".join(missing[:3])}
                        """
                    elif score < 70:
                        feedback = f"""
                        Your profile is good but needs improvement for the role of {job_role}.
                        
                        You already have some relevant skills like {", ".join(matched[:3])}.
                        
                        👉 To improve:
                        • Learn advanced tools like {", ".join(missing[:3])}
                        • Add real-world projects
                        • Strengthen your resume with achievements
                        """
                    else:
                        feedback = f"""
                        Excellent! Your resume is well aligned with the role of {job_role}.
                        
                        You have strong skills like {", ".join(matched[:3])}.
                        
                        👉 To go further:
                        • Work on advanced projects
                        • Build a portfolio
                        • Prepare for interviews
                        """
                    
                    st.markdown(f"""
                    <div style="background-color:#0f172a; padding:15px; border-radius:12px; border-left:5px solid #22c55e; margin-top:10px;">
                        {feedback}
                    </div>
                    """, unsafe_allow_html=True)
                    
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
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # PDF Report Generation
                    if st.button("📄 Generate PDF Report"):
                        report_data = {
                            "job_role": job_role,
                            "score": final_score,
                            "matched": matched,
                            "missing": missing
                        }
                        create_pdf(report_data)
                        with open("resume_report.pdf", "rb") as f:
                            st.download_button(
                                "⬇ Download Report",
                                f,
                                file_name="resume_report.pdf"
                            )
                    
                    # Suggested Projects
                    st.subheader("💡 Suggested Projects")
                    for p in PROJECTS.get(job_role.lower(), []):
                        st.write("🚀", p)
                    
                    # Reset button
                    if st.button("🔄 Analyze Another Resume"):
                        st.session_state.analyze = False
                        st.session_state.saved = False
                        st.rerun()

# Show history at the bottom (after analysis)
st.markdown("---")
show_history(st.session_state.username)

# Footer
st.markdown("""
<div style='text-align: center; padding: 20px; margin-top: 20px;'>
    <p style='color: #666; font-size: 12px;'>© 2024 AI Resume Analyzer | Secure & Private</p>
</div>
""", unsafe_allow_html=True)