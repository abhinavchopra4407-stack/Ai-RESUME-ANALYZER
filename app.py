import streamlit as st
import PyPDF2
import re
import pandas as pd
import plotly.express as px
import base64
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- LOGIN STATE -------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_page():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Invalid credentials ❌")

# 🚨 MUST BE HERE
if not st.session_state.logged_in:
    login_page()
    st.stop()
         
if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False
st.set_page_config(
    page_title="",
    page_icon="🤖",
    layout="wide"
)
st.markdown("<h1 style='text-align:center;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
st.caption("AI-powered resume insights to match your dream job 🚀")
def create_pdf(report_data):
    doc = SimpleDocTemplate("resume_report.pdf")
    styles = getSampleStyleSheet()

    elements = []

# Title
    elements.append(Paragraph("AI Resume Analysis Report", styles['Title']))
    elements.append(Spacer(1, 20))

    # Score Box
    elements.append(Paragraph(f"<b>Final Score:</b> {report_data['score']}%", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # Job Role
    elements.append(Paragraph(f"<b>Target Role:</b> {report_data['job_role']}", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Matched Skills
    elements.append(Paragraph("<b>Matched Skills:</b>", styles['Heading2']))
    for skill in report_data['matched']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    elements.append(Spacer(1, 10))

    # Missing Skills
    elements.append(Paragraph("<b>Missing Skills:</b>", styles['Heading2']))
    for skill in report_data['missing']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Recommended Learning Path:</b>", styles['Heading2']))
    for skill in report_data['missing'][:5]:
        elements.append(Paragraph(f"• Learn {skill} through projects and practice", styles['Normal']))
    elements.append(Spacer(1, 20))


    doc.build(elements)
def set_bg(image_file):
    import base64
    with open(image_file, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>

    /* Transparent header */
    header {{
        background: transparent !important;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    /* Remove spacing */
    .block-container {{
        padding-top: 0rem;
    }}

    /* Full background */
    .stApp {{
        background-image: url("data:image/png;base64,{data}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}

    </style>
    """, unsafe_allow_html=True)
# ---------------- PAGE CONFIG ----------------

 
# ---------------- STYLING ----------------
st.markdown("""
<style>

/* Fix background container */
.block-container {
    background: rgba(0, 0, 0, 0.2);  /* lighter */
    padding: 20px;
    border-radius: 15px;
}

/* Fix text visibility */
h1, h2, h3, h4, h5, h6, p, div, span, label {
    color: white !important;
}

/* Input fields */
input {
    background-color: #0f172a !important;
    color: white !important;
}

/* Buttons */
button {
    background: linear-gradient(90deg, #6366f1, #22c55e);
    color: white !important;
    border-radius: 8px !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #38bdf8; }

</style>
""", unsafe_allow_html=True)
set_bg("robot.jpg")
col1, col2 = st.columns([6,1])

with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
# ---------------- EXTRACT TEXT ----------------
def extract_text(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text
 
# ---------------- SECTION EXTRACTOR ----------------
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
 
# ---------------- CLEAN SKILLS ----------------
def clean_skills(text):
    return [s.strip().title() for s in re.split(r",|\n|•", text) if len(s.strip()) > 2]
 
# ---------------- CLEAN EDUCATION ----------------
def clean_education(text):
    lines = text.split("\n")
    return [l.strip() for l in lines if len(l.strip()) > 5]
 
# ---------------- SKILL DATABASE ----------------
SKILL_DB = {
    "data scientist": [
        "python", "machine learning", "pandas", "numpy",
        "matplotlib", "seaborn", "sql", "statistics"
    ],
    "ml engineer": [
        "python", "tensorflow", "pytorch", "deep learning",
        "nlp", "cnn", "model deployment"
    ],
    "data analyst": [
        "excel", "sql", "power bi", "tableau",
        "python", "data visualization"
    ],
    "business analyst": [
        "excel", "sql", "data analysis", "power bi",
        "communication", "problem solving"
    ],
    "web developer": [
        "html", "css", "javascript", "react",
        "node.js", "mongodb"
    ],
    "frontend developer": [
        "html", "css", "javascript", "react",
        "bootstrap", "ui/ux"
    ],
    "backend developer": [
        "python", "java", "node.js", "sql",
        "api development", "database management"
    ],
    "full stack developer": [
        "html", "css", "javascript", "react",
        "node.js", "mongodb", "api"
    ],
    "android developer": [
        "java", "kotlin", "android sdk",
        "firebase", "rest api"
    ],
    "ios developer": [
        "swift", "ios sdk", "xcode",
        "api integration"
    ],
    "software engineer": [
        "data structures", "algorithms", "java",
        "python", "oop", "problem solving"
    ],
    "devops engineer": [
        "docker", "kubernetes", "ci/cd",
        "aws", "linux", "shell scripting"
    ],
    "cloud engineer": [
        "aws", "azure", "gcp",
        "cloud architecture", "networking"
    ],
    "cyber security analyst": [
        "network security", "ethical hacking",
        "penetration testing", "cryptography"
    ],
    "ai engineer": [
        "python", "machine learning", "deep learning",
        "tensorflow", "nlp"
    ],
    "nlp engineer": [
        "python", "nlp", "text processing",
        "transformers", "machine learning"
    ],
    "computer vision engineer": [
        "python", "opencv", "image processing",
        "deep learning", "cnn"
    ],
    "game developer": [
        "unity", "c#", "game design",
        "graphics", "physics"
    ],
    "blockchain developer": [
        "solidity", "ethereum", "smart contracts",
        "web3", "cryptography"
    ],
    "qa engineer": [
        "testing", "selenium", "automation testing",
        "api testing", "bug tracking"
    ]
}
 
# ---------------- SKILL MATCH ----------------
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
 
# ---------------- PROJECTS ----------------
PROJECTS = {
    "data scientist": [
        "Customer Churn Prediction",
        "House Price Prediction",
        "Fraud Detection System"
    ],
    "ml engineer": [
        "Image Classification using CNN",
        "Chatbot using NLP",
        "Recommendation System"
    ],
    "data analyst": [
        "Sales Dashboard using Power BI",
        "Customer Segmentation Analysis",
        "Excel Data Cleaning Project"
    ],
    "business analyst": [
        "Market Analysis Dashboard",
        "Customer Behavior Analysis",
        "Business KPI Tracker"
    ],
    "web developer": [
        "Portfolio Website",
        "E-commerce Website",
        "Blog Platform"
    ],
    "frontend developer": [
        "React Portfolio",
        "Weather App (API based)",
        "Netflix UI Clone"
    ],
    "backend developer": [
        "REST API using Flask/Django",
        "Authentication System",
        "Blog Backend with Database"
    ],
    "full stack developer": [
        "Full Stack E-commerce App",
        "MERN Social Media App",
        "Job Portal Website"
    ],
    "android developer": [
        "To-Do App",
        "Weather App",
        "Chat Application"
    ],
    "ios developer": [
        "Expense Tracker App",
        "Fitness Tracker",
        "Notes App"
    ],
    "software engineer": [
        "Library Management System",
        "Inventory Management System",
        "Online Code Compiler"
    ],
    "devops engineer": [
        "CI/CD Pipeline Project",
        "Dockerized Web App",
        "Kubernetes Deployment"
    ],
    "cloud engineer": [
        "AWS Hosting Project",
        "Cloud Storage System",
        "Serverless App (Lambda)"
    ],
    "cyber security analyst": [
        "Vulnerability Scanner",
        "Password Strength Checker",
        "Network Security Monitor"
    ],
    "ai engineer": [
        "AI Chatbot",
        "Face Recognition System",
        "Voice Assistant"
    ],
    "nlp engineer": [
        "Sentiment Analysis",
        "Resume Parser",
        "Text Summarization Tool"
    ],
    "computer vision engineer": [
        "Object Detection System",
        "Face Mask Detection",
        "Image Classification App"
    ],
    "game developer": [
        "2D Platformer Game",
        "Snake Game",
        "Unity 3D Game"
    ],
    "blockchain developer": [
        "Cryptocurrency Wallet",
        "Smart Contract App",
        "Voting System using Blockchain"
    ],
    "qa engineer": [
        "Automated Testing Framework",
        "Selenium Test Suite",
        "API Testing Tool"
    ]
}
 
# ---------------- STATE ----------------
if "analyze" not in st.session_state:
    st.session_state.analyze = False
 
# ---------------- UI ----------------
# ---------------- LOGIN SYSTEM ----------------

def login_page():
    st.markdown("## 🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.success("Login successful ✅")
            st.rerun()
          # 🚨 THIS IS CRITICAL
st.title("🤖 AI Resume Analyzer")
col1, col2 = st.columns([6,1])

with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()
# Create 3 columns (left empty, center content, right empty)
col1, col2, col3 = st.columns([1,2,1])

with col2:
    st.markdown("""
<style>
.block-container {
    background: transparent;
}

[data-testid="stFileUploader"] {
    border: 2px dashed #6366f1;
    padding: 30px;
    border-radius: 15px;
    text-align: center;
    background: #0f172a;
}

h1 {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Upload Resume (PDF)",
        type=["pdf"],
        label_visibility="collapsed"
    )
    set_bg("robot.jpg")
if uploaded_file is not None:

    try:
        with st.spinner("📄 Reading your resume..."):
            resume_text = extract_text(uploaded_file)

        st.success("File uploaded successfully ✅")

    except Exception as e:
        st.error("❌ Error reading PDF. Please upload a valid file.")
    set_bg("Analyst.jpg")
    # -------- STEP 1 --------
    if not st.session_state.analyze:
        st.subheader("📄 Resume Preview")
        st.text(resume_text[:1000])
 
        if st.button("🚀 Analyze Resume"):
            st.session_state.analyze = True
 
    # -------- STEP 2 --------
    else:
        sections = extract_sections(resume_text)
 
        st.subheader("🎯 Enter Job Role")
        job_role = st.text_input("Example: data scientist")
 
        col1, col2 = st.columns(2)
 
        # -------- LEFT --------
        with col1:
            st.subheader("🧠 Resume Skills")
            skills = clean_skills(sections["skills"])
            for s in skills:
                st.write("•", s)
 
            st.subheader("🎓 Education")
            edu = clean_education(sections["education"])
            for e in edu:
                st.write("•", e)
 
        # -------- RIGHT --------
        with col2:

            if job_role:

                with st.spinner("🤖 Analyzing your resume..."):

                    user_skills = extract_skills(resume_text)
                    matched, missing, score = match_skills(user_skills, job_role)
                    # ---------------- ROLE SUGGESTION ----------------
                    st.subheader("🎯 Recommended Roles")

                    role_scores = {}

                    for role, skills_list in SKILL_DB.items():
                        match_count = sum(1 for s in skills_list if s in user_skills)
                        role_scores[role] = match_count

                    # Sort roles by match
                    sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)

                    # Top 3 roles
                    top_roles = [r[0].title() for r in sorted_roles[:3]]

                    st.success(f"Best suited roles: {', '.join(top_roles)}")
                    st.subheader("📊 Score Breakdown")

                    # Skill match percentage (already calculated)
                    skill_score = score  

                    # Resume skill coverage (how many skills user has)
                    total_skills = len(matched) + len(missing)

                    if total_skills > 0:
                        resume_strength = int((len(matched) / total_skills) * 100)
                    else:
                        resume_strength = 0

                    # Final score (average)
                    final_score = int((skill_score + resume_strength) / 2)

                    # Display
                    st.write(f"✔ Skill Match: {skill_score}%")
                    st.write(f"✔ Resume Strength: {resume_strength}%")
                    st.write(f"🎯 Final Score: {final_score}%")
                    
                    # ---------------- RESUME STRENGTH FEEDBACK ----------------
                    st.subheader("📊 Resume Strength Analysis")

                    if score < 40:
                        st.error("Your resume is weak for this role. Focus on building core skills and projects.")
                    elif score < 70:
                        st.warning("Your resume is average. Improve by adding more relevant skills and projects.")
                    else:
                        st.success("Your resume is strong and well aligned with the job role!")

                    # Extra insight
                    if len(missing) > len(matched):
                        st.info("You are missing more skills than you have. Focus on skill development.")
                    else:
                        st.info("Good skill coverage. Now focus on projects and real-world experience.")
                    
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
                    <div style="
                        background-color:#0f172a;
                        padding:15px;
                        border-radius:12px;
                        border-left:5px solid #22c55e;
                        margin-top:10px;">
                        {feedback}
                    </div>
                    """, unsafe_allow_html=True)
                    st.subheader("✨ Resume Improvement Suggestions")

                    suggestions = []

                    # Based on missing skills
                    if missing:
                        suggestions.append(f"Add these skills to your resume: {', '.join(missing[:4])}")

                    # Based on score
                    if score < 50:
                        suggestions.append("Include at least 2–3 strong projects related to your domain")
                        suggestions.append("Focus on building real-world applications")

                    # General improvements
                    suggestions.extend([
                        "Use action verbs like Developed, Built, Optimized",
                        "Add measurable results (e.g., improved accuracy by 20%)",
                        "Keep resume concise (1 page if fresher)",
                        "Highlight key technical skills clearly"
                    ])

                    # Display
                    for s in suggestions:
                        st.write(f"👉 {s}")
                    # ------------------ ADD HERE ------------------

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
                        <div style="
                            background-color:#1e293b;
                            padding:10px;
                            margin:6px;
                            border-radius:10px;
                            color:#38bdf8;">
                            👉 {skill}: {suggestion}
                        </div>
                        """, unsafe_allow_html=True)

                # ✅ ALL BELOW MUST BE INSIDE if block

                st.subheader("📊 Skill Match")
                st.write("🎯 Score:", final_score, "%")

                st.subheader("✅ You Have")
                st.markdown("\n".join([f"• {m}" for m in matched]))

                st.subheader("❌ Missing")
                st.markdown("\n".join([f"• {m}" for m in missing]))

                # Chart
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
                    color_discrete_map={
                        "Matched": "#22c55e",
                        "Missing": "#ef4444"
                    }
                )
                import plotly.io as pio
                st.plotly_chart(fig, use_container_width=True)
            
                # Save pie chart as image
                
                report_data = {
    "job_role": job_role,
    "score": score,
    "matched": matched,
    "missing": missing
}
                # Report
                report = f"""
        JOB ROLE: {job_role}

        MATCHED SKILLS:
        {", ".join(matched)}

        MISSING SKILLS:
        {", ".join(missing)}

        SCORE: {score}%
        """
                
            if st.button("Generate PDF Report"):

                report_data = {
                    "job_role": job_role,
                    "score": score,
                    "matched": matched,
                    "missing": missing
                }

                create_pdf(report_data)   # ✅ NOW INSIDE

                st.success("PDF Generated Successfully ✅")

                # Download button
                with open("resume_report.pdf", "rb") as f:
                    st.download_button(
                        label="📥 Download Report",
                        data=f,
                        file_name="resume_report.pdf",
                        mime="application/pdf"
                    )
                # Projects
                    st.subheader("💡 Suggested Projects")
                    for p in PROJECTS.get(job_role.lower(), []):
                            st.write("🚀", p)