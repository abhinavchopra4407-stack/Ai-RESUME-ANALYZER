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
if "uploaded" not in st.session_state:
    st.session_state.uploaded = False
if "resume_brief" not in st.session_state:
    st.session_state.resume_brief = None

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

def send_otp(email, otp):
    try:
        if "EMAIL" not in st.secrets or "PASSWORD" not in st.secrets:
            st.warning(f"⚠️ Demo mode: Your OTP is {otp}")
            return True
            
        yag = yagmail.SMTP(
            user=st.secrets["EMAIL"],
            password=st.secrets["PASSWORD"]
        )
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #6366f1 0%, #22c55e 100%); padding: 30px; border-radius: 12px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🤖 AI Resume Analyzer</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2>Hello,</h2>
                    <p>Your verification code is:</p>
                    <div style="background: #f5f5f5; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <span style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #6366f1;">{otp}</span>
                    </div>
                    <p>This code will expire in 10 minutes.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        yag.send(
            to=email,
            subject="🔐 Your Verification Code",
            contents=html_content
        )
        return True
        
    except Exception as e:
        st.warning(f"⚠️ Demo mode - Your OTP is: {otp}")
        return True

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
        
        email = st.text_input("📧 Email Address", placeholder="you@example.com", key="login_email_input")
        
        if st.button("📨 Send OTP", use_container_width=True):
            if not email:
                st.error("❌ Please enter email address")
            elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                st.error("❌ Please enter a valid email address")
            else:
                otp = generate_otp()
                st.session_state.otp = otp
                st.session_state.email = email
                st.info(f"📧 Test OTP: **{otp}**")
                
                if send_otp(email, otp):
                    st.success("✅ OTP sent to your email!")
        
        user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code", key="login_otp_input")
        
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
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        data = {}
    
    if username in data and data[username]:
        for item in reversed(data[username][-5:]):
            st.markdown(f"""
            <div style='
                background: #0f172a;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 10px;
                border-left: 4px solid #22c55e;
            '>
                💼 <strong>{item['job_role']}</strong> &nbsp;&nbsp; 🎯 {item['score']}% &nbsp;&nbsp; 🕒 {item['date']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 No history yet. Upload a resume to get started!")

def extract_text(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def generate_resume_brief(text):
    """Generate a comprehensive brief of the resume"""
    
    # Extract email (improved pattern)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    email_found = emails[0] if emails else "Not found"
    
    # Extract phone number (improved for Indian numbers)
    phone_pattern = r'\b(?:\+?91)?\s?[6-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    phone_found = phones[0] if phones else "Not found"
    
    # Extract name (improved - look for common name patterns)
    lines = text.split('\n')
    name = "Not found"
    for line in lines[:10]:
        line = line.strip()
        if len(line.split()) in [2, 3] and line.istitle() and len(line) < 30:
            name = line
            break
        if 'name:' in line.lower():
            name = line.split(':', 1)[1].strip()
            break
    
    # Extract skills
    common_skills = [
        'python', 'java', 'javascript', 'sql', 'react', 'angular', 'vue', 'node.js',
        'machine learning', 'deep learning', 'ai', 'data science', 'pandas', 'numpy',
        'tensorflow', 'pytorch', 'aws', 'azure', 'docker', 'kubernetes', 'git',
        'html', 'css', 'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin', 'flutter',
        'django', 'flask', 'mongodb', 'mysql', 'postgresql', 'rest api', 'graphql'
    ]
    
    found_skills = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    found_skills = list(dict.fromkeys(found_skills))
    
    # Extract education
    education_keywords = [
        'bachelor', 'master', 'b.tech', 'm.tech', 'b.e', 'm.e', 'phd', 'b.sc', 
        'm.sc', 'b.com', 'm.com', 'bca', 'mca', 'engineering', 'computer science',
        'information technology', 'diploma', 'b.b.a', 'm.b.a', 'b.a', 'm.a'
    ]
    
    education_found = []
    lines_lower = [line.lower() for line in lines]
    for i, line in enumerate(lines_lower):
        for keyword in education_keywords:
            if keyword in line and len(line) > 15:
                edu_text = lines[i].strip()
                if edu_text not in education_found:
                    education_found.append(edu_text)
                    break
        if len(education_found) >= 3:
            break
    
    # Extract projects
    project_keywords = ['project', 'projects:', 'mini project', 'major project']
    projects_found = []
    for i, line in enumerate(lines_lower):
        for keyword in project_keywords:
            if keyword in line and i + 1 < len(lines):
                project_line = lines[i].strip()
                if len(project_line) > 10:
                    projects_found.append(project_line)
                if i + 1 < len(lines) and len(lines[i+1].strip()) > 10:
                    projects_found.append(lines[i+1].strip())
                break
        if len(projects_found) >= 5:
            break
    
    projects_found = list(dict.fromkeys(projects_found))[:5]
    
    # Extract certifications
    cert_keywords = ['certification', 'certificate', 'certified', 'coursera', 'udemy', 'edx']
    certifications_found = []
    for i, line in enumerate(lines_lower):
        for keyword in cert_keywords:
            if keyword in line:
                cert_line = lines[i].strip()
                if len(cert_line) > 10:
                    certifications_found.append(cert_line)
                    break
        if len(certifications_found) >= 3:
            break
    
    # Extract links
    github_pattern = r'github\.com/[^\s]+'
    linkedin_pattern = r'linkedin\.com/in/[^\s]+'
    
    github = re.findall(github_pattern, text_lower)
    linkedin = re.findall(linkedin_pattern, text_lower)
    
    # Determine if fresher
    exp_pattern = r'\b(19|20)\d{2}\s*[-–to]+\s*(?:present|current|(19|20)\d{2})\b'
    experiences = re.findall(exp_pattern, text, re.IGNORECASE)
    
    internship_keywords = ['intern', 'internship', 'trainee']
    has_internship = any(keyword in text_lower for keyword in internship_keywords)
    
    if len(experiences) > 0:
        experience_level = f"{len(experiences)} years"
        is_fresher = False
    elif has_internship:
        experience_level = "Internship Experience"
        is_fresher = True
    else:
        experience_level = "Fresher / Entry Level"
        is_fresher = True
    
    brief = {
        'name': name,
        'email': email_found,
        'phone': phone_found,
        'skills': found_skills[:15],
        'education': education_found,
        'projects': projects_found,
        'certifications': certifications_found,
        'github': github[0] if github else None,
        'linkedin': linkedin[0] if linkedin else None,
        'experience_level': experience_level,
        'is_fresher': is_fresher,
        'has_internship': has_internship
    }
    
    return brief

def display_resume_brief(brief):
    """Display the resume brief in a nice format"""
    
    st.markdown("""
    <style>
    .brief-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    .brief-header {
        background: linear-gradient(135deg, #6366f1, #22c55e);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .info-card {
        background: #0f172a;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #334155;
    }
    .info-label {
        font-size: 12px;
        color: #888;
        margin-bottom: 8px;
    }
    .info-value {
        font-size: 16px;
        font-weight: bold;
        color: #22c55e;
        word-break: break-all;
    }
    .skill-tag {
        background: #6366f1;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        display: inline-block;
        margin: 5px;
        font-size: 13px;
    }
    .project-item {
        background: #0f172a;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 3px solid #22c55e;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class='brief-header'>
        <h2 style='color: white; margin: 0;'>📄 Resume Brief</h2>
        <p style='color: white; margin: 5px 0 0 0; opacity: 0.9'>Quick overview of your resume</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Personal Information Grid
    st.markdown("### 👤 Personal Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class='info-card'>
            <div class='info-label'>Name</div>
            <div class='info-value'>{brief['name']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        email_display = brief['email'] if brief['email'] != "Not found" else "❌ Not found"
        st.markdown(f"""
        <div class='info-card'>
            <div class='info-label'>📧 Email</div>
            <div class='info-value' style='font-size: 12px;'>{email_display}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='info-card'>
            <div class='info-label'>📞 Phone</div>
            <div class='info-value'>{brief['phone']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Links if available
    if brief['github'] or brief['linkedin']:
        st.markdown("### 🔗 Online Presence")
        cols = st.columns(2)
        if brief['github']:
            with cols[0]:
                st.markdown(f"""
                <div class='info-card'>
                    <div class='info-label'>💻 GitHub</div>
                    <div class='info-value' style='font-size: 12px;'>{brief['github']}</div>
                </div>
                """, unsafe_allow_html=True)
        if brief['linkedin']:
            with cols[1]:
                st.markdown(f"""
                <div class='info-card'>
                    <div class='info-label'>🔗 LinkedIn</div>
                    <div class='info-value' style='font-size: 12px;'>{brief['linkedin']}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # Experience Level
    st.markdown("### 💼 Experience Level")
    if brief['is_fresher']:
        if brief['has_internship']:
            st.info("🎓 **Fresher with Internship Experience** - Great! Highlight your internship projects and learnings.")
        else:
            st.warning("🎓 **Fresher** - Focus on showcasing your projects, certifications, and academic achievements.")
    else:
        st.success(f"📈 **{brief['experience_level']}** - Experienced professional")
    
    # Skills
    st.markdown("### 🛠️ Technical Skills")
    if brief['skills']:
        skills_html = ""
        for skill in brief['skills']:
            skills_html += f"<span class='skill-tag'>{skill}</span>"
        st.markdown(skills_html, unsafe_allow_html=True)
        st.caption(f"Total skills detected: {len(brief['skills'])}")
    else:
        st.info("No technical skills detected. Add skills like Python, Java, SQL, etc.")
    
    # Projects
    if brief['projects']:
        st.markdown("### 🚀 Projects")
        for project in brief['projects']:
            st.markdown(f"""
            <div class='project-item'>
                📌 {project[:100]}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("💡 No projects detected. Adding projects will strengthen your resume significantly!")
    
    # Education
    if brief['education']:
        st.markdown("### 🎓 Education")
        for edu in brief['education']:
            st.markdown(f"• {edu}")
    else:
        st.warning("⚠️ Education section not clearly identified")
    
    # Certifications
    if brief['certifications']:
        st.markdown("### 📜 Certifications")
        for cert in brief['certifications']:
            st.markdown(f"• {cert}")
    
    # Resume Insights
    st.markdown("### 💡 Resume Insights")
    
    insights = []
    
    if len(brief['skills']) < 5:
        insights.append("📌 **Add more technical skills** - Include programming languages, frameworks, and tools relevant to your target role.")
    elif len(brief['skills']) > 10:
        insights.append("✅ **Great skill diversity** - You have a good range of technical skills!")
    
    if len(brief['projects']) == 0:
        insights.append("🚀 **Add projects** - As a fresher, projects are crucial to demonstrate practical skills.")
    elif len(brief['projects']) < 3:
        insights.append("💪 **Add more projects** - 3-4 quality projects will make your resume stand out.")
    else:
        insights.append("✅ **Good project portfolio** - Your projects showcase practical experience.")
    
    if not brief['education']:
        insights.append("🎓 **Highlight education** - Add your degree, university, and CGPA/percentage.")
    
    if not brief['certifications']:
        insights.append("📜 **Add certifications** - Online courses from Coursera, Udemy, or NPTEL add credibility.")
    
    if not brief['github'] and not brief['linkedin']:
        insights.append("🔗 **Add GitHub & LinkedIn** - These are essential for recruiters to check your work.")
    
    insights.extend([
        "📊 **Add achievements** - Include hackathon wins, coding competition rankings, or academic achievements.",
        "🎯 **Tailor your resume** - Customize skills and projects for each job application.",
        "📝 **Add a summary** - A 2-3 line professional summary at the top helps recruiters understand your profile."
    ])
    
    for insight in insights[:6]:
        st.markdown(insight)
    
    # Pro tip
    st.markdown("""
    <div style='background: #1e293b; padding: 15px; border-radius: 10px; margin-top: 15px; border-left: 4px solid #22c55e;'>
        <strong>💡 Pro Tip for Freshers:</strong><br>
        Focus on showing your project work, internship experience (if any), and technical skills.
        Employers value practical knowledge over years of experience for entry-level roles!
    </div>
    """, unsafe_allow_html=True)

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
    "software engineer": ["data structures", "algorithms", "java", "python", "oop", "problem solving"],
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

# ============= STEP 4: CHECK LOGIN STATUS =============
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= STEP 5: MAIN APP =============

# Main app title
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='font-size: 42px; color: white; margin: 0;'>🤖 AI Resume Analyzer</h1>
    <p style='color: white; font-size: 16px; margin-top: 10px;'>AI-powered resume insights to match your dream job 🚀</p>
</div>
""", unsafe_allow_html=True)

# Create layout
col1, col2 = st.columns([3, 1])

with col2:
    st.markdown(f"""
    <div style='background: #1e293b; padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center;'>
        <div style='font-size: 48px;'>👤</div>
        <h3 style='color: white; margin: 10px 0;'>Welcome!</h3>
        <p style='color: #888; font-size: 12px;'>{st.session_state.username}</p>
    </div>
    """, unsafe_allow_html=True)

with col1:
    # History section
    st.markdown("### 📜 Your Previous Reports")
    show_history(st.session_state.username)
    
    st.markdown("---")
    
    # Upload section
    st.markdown("### 📄 Upload Your Resume")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="resume_uploader")
    
    if uploaded_file is not None:
        try:
            with st.spinner("📄 Reading your resume..."):
                resume_text = extract_text(uploaded_file)
                st.success("✅ File uploaded successfully!")
                st.session_state.resume_text = resume_text
                st.session_state.uploaded = True
                
                # Generate and display resume brief
                st.session_state.resume_brief = generate_resume_brief(resume_text)
                
        except Exception as e:
            st.error(f"❌ Error reading PDF: {str(e)}")
    
    # Display resume brief if available
    if st.session_state.get('uploaded', False) and st.session_state.resume_brief:
        display_resume_brief(st.session_state.resume_brief)
        
        # Analysis button
        st.markdown("---")
        if not st.session_state.get('analyze', False):
            if st.button("🚀 Continue to Detailed Analysis", use_container_width=True):
                st.session_state.analyze = True
                st.rerun()
        else:
            st.markdown("### 🎯 Job Role Analysis")
            job_role = st.text_input("Enter your target job role:", placeholder="e.g., Data Scientist, ML Engineer, Web Developer")
            
            if job_role:
                with st.spinner("🤖 Analyzing your resume..."):
                    user_skills = extract_skills(st.session_state.resume_text)
                    matched, missing, score = match_skills(user_skills, job_role)
                
                # Save to history
                if not st.session_state.get('saved', False):
                    save_history(st.session_state.username, job_role, score)
                    st.session_state.saved = True
                
                # Display results
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown(f"### ✅ Matched Skills ({len(matched)})")
                    for skill in matched:
                        st.write(f"✔ {skill}")
                
                with col_b:
                    st.markdown(f"### ❌ Missing Skills ({len(missing)})")
                    for skill in missing:
                        st.write(f"✖ {skill}")
                
                # Score display
                st.markdown("---")
                st.markdown(f"## 🎯 Match Score: {score}%")
                
                # Progress bar
                st.progress(score / 100)
                
                if score >= 80:
                    st.success("🌟 Excellent match! Your resume is well-aligned with this role.")
                elif score >= 60:
                    st.info("📈 Good match! Add the missing skills to improve further.")
                else:
                    st.warning("⚠️ Low match. Consider upskilling or targeting a different role.")
                
                # Reset analysis button
                if st.button("🔄 Analyze Another Resume", use_container_width=True):
                    st.session_state.analyze = False
                    st.session_state.uploaded = False
                    st.session_state.resume_brief = None
                    st.rerun()

# Logout button at bottom
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("""
<div style='text-align: center; padding: 20px; margin-top: 20px;'>
    <p style='color: #666; font-size: 12px;'>© 2024 AI Resume Analyzer | Secure & Private</p>
</div>
""", unsafe_allow_html=True)