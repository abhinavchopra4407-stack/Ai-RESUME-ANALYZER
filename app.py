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
    
    # Basic stats
    word_count = len(text.split())
    char_count = len(text)
    
    # Extract name (try to find from first few lines)
    lines = text.split('\n')
    potential_name = lines[0].strip() if lines else "Not found"
    if len(potential_name) > 30 or len(potential_name) < 2:
        potential_name = "Not clearly mentioned"
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    email_found = emails[0] if emails else "Not found"
    
    # Extract phone number
    phone_pattern = r'\b(?:\+?91)?\s?[6-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    phone_found = phones[0] if phones else "Not found"
    
    # Extract skills (common tech skills)
    common_skills = [
        'python', 'java', 'javascript', 'sql', 'react', 'angular', 'vue', 'node.js',
        'machine learning', 'deep learning', 'ai', 'data science', 'pandas', 'numpy',
        'tensorflow', 'pytorch', 'aws', 'azure', 'docker', 'kubernetes', 'git',
        'html', 'css', 'c++', 'c#', 'php', 'ruby', 'swift', 'kotlin', 'flutter'
    ]
    
    found_skills = []
    text_lower = text.lower()
    for skill in common_skills:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    # Extract education (look for degree names)
    education_keywords = ['bachelor', 'master', 'b.tech', 'm.tech', 'b.e', 'm.e', 
                         'phd', 'b.sc', 'm.sc', 'b.com', 'm.com', 'bca', 'mca',
                         'engineering', 'computer science', 'information technology']
    
    education_found = []
    lines_lower = [line.lower() for line in lines]
    for i, line in enumerate(lines_lower):
        for keyword in education_keywords:
            if keyword in line and len(line) > 10:
                education_found.append(lines[i].strip())
                break
    
    # Extract experience (look for year patterns)
    exp_pattern = r'\b(19|20)\d{2}\s*[-–to]+\s*(?:present|current|(19|20)\d{2})\b'
    experiences = re.findall(exp_pattern, text, re.IGNORECASE)
    years_of_exp = len(set(experiences)) if experiences else 0
    
    # Count sections
    sections = {
        'education': len([e for e in education_found if e]),
        'skills': len(found_skills),
        'experience': years_of_exp
    }
    
    brief = {
        'name': potential_name,
        'email': email_found,
        'phone': phone_found,
        'word_count': word_count,
        'char_count': char_count,
        'skills': found_skills[:10],  # Top 10 skills
        'education': education_found[:3],  # Top 3 education entries
        'experience_years': years_of_exp,
        'sections': sections
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
    .brief-stat {
        background: #0f172a;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #334155;
    }
    .brief-stat-number {
        font-size: 28px;
        font-weight: bold;
        color: #22c55e;
    }
    .skill-tag {
        background: #6366f1;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        display: inline-block;
        margin: 5px;
        font-size: 14px;
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
    
    # Personal Information
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='brief-stat'>
                <div>👤 Name</div>
                <div class='brief-stat-number' style='font-size: 18px;'>{brief['name'][:30]}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='brief-stat'>
                <div>📧 Email</div>
                <div class='brief-stat-number' style='font-size: 14px;'>{brief['email']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='brief-stat'>
                <div>📞 Phone</div>
                <div class='brief-stat-number' style='font-size: 16px;'>{brief['phone']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Statistics
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='brief-stat'>
            <div>📊 Word Count</div>
            <div class='brief-stat-number'>{brief['word_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='brief-stat'>
            <div>📝 Characters</div>
            <div class='brief-stat-number'>{brief['char_count']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='brief-stat'>
            <div>💼 Experience</div>
            <div class='brief-stat-number'>{brief['experience_years']} years</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class='brief-stat'>
            <div>🎯 Skills Found</div>
            <div class='brief-stat-number'>{len(brief['skills'])}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Skills
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔧 Technical Skills Found", expanded=True):
        skills_html = ""
        for skill in brief['skills']:
            skills_html += f"<span class='skill-tag'>{skill}</span>"
        st.markdown(skills_html, unsafe_allow_html=True)
        
        if not brief['skills']:
            st.info("No common technical skills detected. Consider adding more keywords.")
    
    # Education
    with st.expander("🎓 Education", expanded=True):
        if brief['education']:
            for edu in brief['education']:
                st.markdown(f"• {edu}")
        else:
            st.info("Education section not clearly identified")
    
    # Resume Strengths & Suggestions
    with st.expander("💡 Quick Insights", expanded=True):
        insights = []
        
        if brief['word_count'] < 300:
            insights.append("⚠️ Your resume seems too short. Aim for 400-600 words for a strong resume.")
        elif brief['word_count'] > 1000:
            insights.append("📄 Your resume is quite detailed. Consider keeping it concise (1-2 pages).")
        else:
            insights.append("✅ Good resume length! Well balanced.")
        
        if len(brief['skills']) < 5:
            insights.append("⚠️ Add more technical skills to improve ATS scoring.")
        elif len(brief['skills']) > 15:
            insights.append("✅ Excellent! You have a diverse skill set.")
        else:
            insights.append("✅ Good number of skills listed.")
        
        if brief['experience_years'] == 0:
            insights.append("💪 Highlight your projects and internships if you're a fresher.")
        elif brief['experience_years'] < 3:
            insights.append("📈 Showcase your achievements and growth in early career.")
        else:
            insights.append("🏆 Strong experience! Highlight leadership and impact.")
        
        for insight in insights:
            st.markdown(insight)
    
    # Section breakdown
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📊 Section Breakdown")
    
    section_data = {
        'Section': ['Education', 'Skills', 'Experience'],
        'Detected': [brief['sections']['education'], brief['sections']['skills'], brief['sections']['experience']]
    }
    
    fig = px.bar(section_data, x='Section', y='Detected', 
                 title="Resume Section Coverage",
                 color='Detected',
                 color_continuous_scale=['#ef4444', '#f59e0b', '#22c55e'])
    fig.update_layout(
        plot_bgcolor='#0f172a',
        paper_bgcolor='#0f172a',
        font_color='white',
        title_font_color='white'
    )
    st.plotly_chart(fig, use_container_width=True)

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
            job_role = st.text_input("Enter your target job role:", placeholder="e.g., Data Scientist, ML Engineer")
            
            if job_role:
                st.info("✅ Ready for detailed analysis! Add your skill matching logic here.")

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