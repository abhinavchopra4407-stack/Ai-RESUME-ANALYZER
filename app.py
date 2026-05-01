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
import requests

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
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_job_role" not in st.session_state:
    st.session_state.current_job_role = ""
if "matched_skills" not in st.session_state:
    st.session_state.matched_skills = []
if "missing_skills" not in st.session_state:
    st.session_state.missing_skills = []

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

def get_chatgpt_response(prompt, context=""):
    """Get response using OpenRouter API (Free)"""
    try:
        # Check if OpenRouter API key is configured
        if "OPENROUTER_API_KEY" not in st.secrets:
            return get_fallback_response(prompt, context)
        
        api_key = st.secrets["OPENROUTER_API_KEY"]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-resume-analyzer.streamlit.app",
            "X-Title": "AI Resume Analyzer"
        }
        
        full_prompt = f"""You are an AI Resume Assistant helping job seekers improve their resumes and careers.

Context from resume analysis:
{context}

User question: {prompt}

Please provide helpful, practical, and concise advice. Keep responses to 2-4 sentences maximum.
"""
        
        data = {
            "model": "qwen/qwen-2.5-7b-instruct:free",  # Free model on OpenRouter
            "messages": [
                {"role": "system", "content": "You are a helpful resume and career advisor assistant."},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return get_fallback_response(prompt, context)
            
    except requests.exceptions.Timeout:
        return "⏰ Request timed out. Please try again."
    except Exception as e:
        return get_fallback_response(prompt, context)

def get_resume_suggestions(resume_text, job_role):
    """Get AI-powered resume suggestions using OpenRouter"""
    try:
        if "OPENROUTER_API_KEY" not in st.secrets:
            return get_fallback_suggestions(job_role)
        
        api_key = st.secrets["OPENROUTER_API_KEY"]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-resume-analyzer.streamlit.app",
            "X-Title": "AI Resume Analyzer"
        }
        
        prompt = f"""Provide 5 specific, actionable suggestions to improve this resume for a {job_role} position.

Resume excerpt: {resume_text[:2500]}

Format the response as bullet points with clear headings. Focus on:
1. Missing keywords/skills
2. Quantifiable achievements
3. Action verbs to use
4. Format improvements
5. Overall impact

Keep each suggestion concise.
"""
        
        data = {
            "model": "qwen/qwen-2.5-7b-instruct:free",
            "messages": [
                {"role": "system", "content": "You are an expert resume reviewer. Provide specific, actionable advice."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return get_fallback_suggestions(job_role)
            
    except Exception as e:
        return get_fallback_suggestions(job_role)

def get_fallback_response(prompt, context=""):
    """Fallback responses when API is not available"""
    prompt_lower = prompt.lower()
    
    if "improve" in prompt_lower or "resume" in prompt_lower:
        return """📝 **Resume Improvement Tips:**
• Use strong action verbs (Developed, Built, Optimized, Led)
• Quantify achievements with specific numbers and percentages
• Tailor your resume to each job description using keywords
• Keep it concise (1-2 pages for experienced professionals)
• Highlight your most relevant skills and projects first"""
    
    elif "career" in prompt_lower or "path" in prompt_lower:
        return """🎯 **Career Path Advice:**
• Focus on building in-demand skills in your target industry
• Get relevant certifications from recognized platforms
• Build a portfolio of 3-4 quality projects
• Network with professionals in your field on LinkedIn
• Consider internships or freelance work for experience"""
    
    elif "missing" in prompt_lower or "skill" in prompt_lower:
        missing = context if context else "relevant"
        return f"""💪 **How to Learn Missing Skills:**
• Take structured online courses (Coursera, Udemy, edX)
• Build small projects applying each skill
• Contribute to open-source projects
• Practice daily for 30-60 minutes
• Join coding bootcamps or study groups"""
    
    elif "project" in prompt_lower:
        return """🚀 **Project Ideas for Your Portfolio:**
• Build a personal portfolio website
• Create a full-stack web application
• Develop an automation tool for daily tasks
• Contribute to open-source on GitHub
• Build a data analysis dashboard
• Create a mobile app for a specific problem"""
    
    elif "interview" in prompt_lower:
        return """🎤 **Interview Preparation Tips:**
• Research the company thoroughly before interview
• Practice common behavioral questions (STAR method)
• Prepare questions to ask the interviewer
• Review technical concepts in your domain
• Do mock interviews with friends or online"""
    
    else:
        return """🤖 **I'm your AI Career Assistant!**

Ask me about:
📝 Resume improvement tips
🎯 Career path guidance
💪 Skill development strategies
🚀 Project ideas for portfolio
🎤 Interview preparation
📊 Job search strategies
🔧 Technical skill advice

Try asking a specific question for better results!"""

def get_fallback_suggestions(job_role):
    """Fallback suggestions when API is not available"""
    return f"""📝 **Resume Suggestions for {job_role} role:**

1. **Add Missing Keywords:** Include role-specific keywords like:
   - Programming languages (Python, Java, JavaScript)
   - Frameworks (React, Django, Spring Boot)
   - Tools (Git, Docker, AWS)

2. **Quantify Achievements:** Use numbers to show impact:
   - "Improved performance by 40%"
   - "Managed team of 5 developers"
   - "Reduced costs by $50,000"

3. **Use Strong Action Verbs:** Start bullets with:
   - Developed, Built, Created, Designed
   - Optimized, Improved, Enhanced
   - Led, Managed, Coordinated

4. **Add a Projects Section:** Include 2-3 relevant projects with:
   - Project name and description
   - Technologies used
   - Link to GitHub/live demo

5. **Tailor Your Resume:** Customize for each application:
   - Match keywords from job description
   - Highlight most relevant experience first
   - Remove irrelevant information

💡 **Pro Tip:** Always include metrics and results, not just responsibilities!"""

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
    
    current_ist = get_indian_time()
    st.info(f"🕐 Current Indian Time: {current_ist.strftime('%I:%M:%S %p IST')} | {current_ist.strftime('%d-%m-%Y')}")
    
    if is_account_locked():
        lock_remaining = (st.session_state.otp_locked_until - get_indian_time()).seconds
        st.error(f"🔒 Too many failed attempts. Account locked for {lock_remaining // 60} minutes.")
        st.stop()
    
    with st.form(key="login_form"):
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
                if not email:
                    st.error("❌ Please enter email")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Invalid email")
                else:
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Max resend limit reached")
                    else:
                        otp = generate_otp()
                        st.session_state.otp = otp
                        st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                        st.session_state.email = email
                        st.session_state.last_otp_sent_time = get_indian_time()
                        st.session_state.otp_resend_attempts += 1
                        st.session_state.timer_running = True
                        
                        if send_otp(email, otp):
                            st.success("✅ OTP sent! Valid for 2 minutes.")
        
        with col2:
            if st.form_submit_button("🔄 Resend OTP", use_container_width=True):
                if not email:
                    st.error("❌ Enter email first")
                elif not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                    st.error("❌ Invalid email")
                else:
                    if st.session_state.otp_resend_attempts >= 5:
                        st.error("❌ Max limit reached")
                    else:
                        otp = generate_otp()
                        st.session_state.otp = otp
                        st.session_state.otp_expiry = get_indian_time() + timedelta(minutes=2)
                        st.session_state.last_otp_sent_time = get_indian_time()
                        st.session_state.otp_resend_attempts += 1
                        st.session_state.timer_running = True
                        
                        if send_otp(email, otp):
                            st.success("✅ New OTP sent!")
        
        user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code")
        
        if st.session_state.otp_expiry and st.session_state.timer_running:
            remaining = (st.session_state.otp_expiry - get_indian_time()).seconds
            if remaining > 0:
                st.info(f"⏰ OTP expires in: {remaining // 60}:{remaining % 60:02d}")
                st.progress(remaining / 120)
        
        st.markdown("---")
        
        if st.form_submit_button("✅ Verify OTP", use_container_width=True, type="primary"):
            if not user_otp:
                st.error("❌ Please enter OTP")
            else:
                if is_otp_expired():
                    st.error("❌ OTP expired")
                    reset_otp_state()
                else:
                    if st.session_state.otp_attempts >= 3:
                        st.session_state.otp_locked_until = get_indian_time() + timedelta(minutes=15)
                        st.error("🔒 Account locked for 15 minutes")
                    elif user_otp == st.session_state.get("otp"):
                        st.session_state.logged_in = True
                        st.session_state.username = st.session_state.email
                        reset_otp_state()
                        st.success("✅ Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.session_state.otp_attempts += 1
                        remaining = 3 - st.session_state.otp_attempts
                        st.error(f"❌ Invalid OTP. {remaining} attempts left")
        
        st.markdown("""
        <div style='background: #1e293b; padding: 12px; border-radius: 10px; margin-top: 20px;'>
            <p style='color: #888; font-size: 12px;'>🔒 OTP expires in 2 minutes | Max 3 attempts | Max 5 resends</p>
        </div>
        """, unsafe_allow_html=True)

def show_history(username):
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
                        st.rerun()
        
        if st.button("🗑️ Delete All History", use_container_width=True):
            delete_history(username)
            st.rerun()
    else:
        st.info("No history yet")

def set_bg(image_file):
    try:
        with open(image_file, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{data}");
            background-size: cover;
            background-attachment: fixed;
        }}
        .block-container {{
            background: rgba(0, 0, 0, 0.7);
            padding: 20px;
            border-radius: 15px;
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

SKILL_DB = {
    "data scientist": ["python", "machine learning", "pandas", "numpy", "sql", "statistics"],
    "ml engineer": ["python", "tensorflow", "pytorch", "deep learning", "nlp", "cnn"],
    "data analyst": ["excel", "sql", "power bi", "tableau", "python", "data visualization"],
    "web developer": ["html", "css", "javascript", "react", "node.js", "mongodb"],
    "frontend developer": ["html", "css", "javascript", "react", "bootstrap"],
    "backend developer": ["python", "java", "node.js", "sql", "api development"],
    "full stack developer": ["html", "css", "javascript", "react", "node.js", "mongodb"],
}

PROJECTS = {
    "data scientist": ["Customer Churn Prediction", "House Price Prediction", "Fraud Detection"],
    "web developer": ["Portfolio Website", "E-commerce Site", "Blog Platform"],
    "data analyst": ["Sales Dashboard", "Customer Segmentation", "Excel Analysis"],
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
    elements.append(Paragraph(f"Score: {report_data['score']}%", styles['Heading2']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"Role: {report_data['job_role']}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Matched Skills:", styles['Heading2']))
    for skill in report_data['matched']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Missing Skills:", styles['Heading2']))
    for skill in report_data['missing']:
        elements.append(Paragraph(f"• {skill}", styles['Normal']))
    doc.build(elements)

# ============= STEP 4: CHECK LOGIN STATUS =============
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= STEP 5: MAIN APP =============

st.markdown("""
<style>
.block-container { background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 15px; }
h1, h2, h3, p, div, span, label { color: white !important; }
input { background-color: #0f172a !important; color: white !important; }
button { background: linear-gradient(90deg, #6366f1, #22c55e); color: white !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

try:
    set_bg("robot.jpg")
except:
    pass

st.markdown("<h1 style='text-align:center;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
st.caption("AI-powered resume insights to match your dream job 🚀")

# Two columns for main content and chat
main_col, chat_col = st.columns([2, 1])

with main_col:
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], label_visibility="collapsed")
    
    if uploaded_file:
        st.markdown(f"📄 **File:** {uploaded_file.name}")
        
        with st.spinner("Processing..."):
            resume_text = extract_text(uploaded_file)
            st.session_state.resume_text = resume_text
        
        st.success("✅ File uploaded!")
        
        if not st.session_state.analyze:
            st.subheader("📄 Resume Preview")
            st.text(resume_text[:500])
            if st.button("🚀 Analyze Resume"):
                st.session_state.analyze = True
                st.rerun()
        
        else:
            sections = extract_sections(resume_text)
            job_role = st.text_input("🎯 Enter Job Role", placeholder="data scientist, web developer, etc.")
            
            col_left, col_right = st.columns(2)
            with col_left:
                st.subheader("🧠 Skills Found")
                skills = clean_skills(sections["skills"])
                for s in skills[:10]:
                    st.write(f"• {s}")
            
            with col_right:
                if job_role:
                    with st.spinner("Analyzing..."):
                        user_skills = extract_skills(resume_text)
                        matched, missing, score = match_skills(user_skills, job_role)
                        
                        if not st.session_state.saved:
                            save_history(st.session_state.username, job_role, score)
                            st.session_state.saved = True
                        
                        # Store for chat
                        st.session_state.current_job_role = job_role
                        st.session_state.matched_skills = matched
                        st.session_state.missing_skills = missing
                        
                        st.subheader("📊 Score")
                        st.metric("Match Score", f"{score}%")
                        
                        st.subheader("✅ Matched Skills")
                        for m in matched:
                            st.write(f"✔ {m}")
                        
                        st.subheader("❌ Missing Skills")
                        for m in missing:
                            st.write(f"✖ {m}")
                        
                        if st.button("🤖 Get AI Suggestions"):
                            with st.spinner("Getting AI suggestions from OpenRouter..."):
                                suggestions = get_resume_suggestions(resume_text, job_role)
                                st.markdown("### 💡 AI Suggestions")
                                st.markdown(suggestions)
                        
                        if st.button("🔄 Analyze Another"):
                            st.session_state.analyze = False
                            st.session_state.saved = False
                            st.rerun()

with chat_col:
    st.markdown("### 🤖 AI Career Assistant")
    st.markdown("*Powered by OpenRouter (Free)*")
    st.markdown("---")
    
    # Chat history display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history[-10:]:
            if msg["role"] == "user":
                st.markdown(f"**🙋 You:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Assistant:** {msg['content']}")
            st.markdown("---")
    
    # Quick questions
    st.markdown("#### 📌 Quick Questions")
    col_q1, col_q2 = st.columns(2)
    
    with col_q1:
        if st.button("📝 Improve Resume", use_container_width=True):
            with st.spinner("Getting AI response..."):
                context = f"Target Role: {st.session_state.current_job_role}"
                response = get_chatgpt_response("How can I improve my resume?", context)
                st.session_state.chat_history.append({"role": "user", "content": "How can I improve my resume?"})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
        
        if st.button("💪 Missing Skills", use_container_width=True):
            with st.spinner("Getting AI response..."):
                context = f"Missing skills: {', '.join(st.session_state.missing_skills)}"
                response = get_chatgpt_response("How to learn my missing skills?", context)
                st.session_state.chat_history.append({"role": "user", "content": "How to learn my missing skills?"})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    with col_q2:
        if st.button("🎯 Career Path", use_container_width=True):
            with st.spinner("Getting AI response..."):
                context = f"Skills: {', '.join(st.session_state.matched_skills)}"
                response = get_chatgpt_response("What career path should I follow?", context)
                st.session_state.chat_history.append({"role": "user", "content": "What career path should I follow?"})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
        
        if st.button("🚀 Project Ideas", use_container_width=True):
            with st.spinner("Getting AI response..."):
                context = f"Role: {st.session_state.current_job_role}"
                response = get_chatgpt_response("What projects should I build?", context)
                st.session_state.chat_history.append({"role": "user", "content": "What projects should I build?"})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    st.markdown("---")
    
    # Custom question input
    user_question = st.text_input("💬 Ask a custom question:", placeholder="e.g., How to write a better summary?")
    
    if st.button("📨 Send Message", use_container_width=True):
        if user_question:
            with st.spinner("Getting AI response from OpenRouter..."):
                context = f"Target Role: {st.session_state.current_job_role}\nMatched Skills: {', '.join(st.session_state.matched_skills)}\nMissing Skills: {', '.join(st.session_state.missing_skills)}"
                response = get_chatgpt_response(user_question, context)
                st.session_state.chat_history.append({"role": "user", "content": user_question})
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                st.rerun()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
    
    # API Status
    if "OPENROUTER_API_KEY" in st.secrets:
        st.caption("✅ AI Assistant Active (OpenRouter)")
    else:
        st.caption("⚠️ Demo Mode: Add OPENROUTER_API_KEY to secrets for AI responses")

# History section
st.markdown("---")
show_history(st.session_state.username)

# Logout
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()