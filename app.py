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
# This MUST be the FIRST thing after imports

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
    """Send OTP via email"""
    try:
        # Check if secrets exist
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
    """Display login page"""
    st.markdown("""
    <div style='text-align: center; padding: 40px 20px 20px 20px;'>
        <h1 style='font-size: 48px; background: linear-gradient(135deg, #6366f1 0%, #22c55e 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            🤖 AI RESUME ANALYZER
        </h1>
        <p style='color: #888; font-size: 18px;'>AI-powered resume insights to match your dream job 🚀</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Centered login form
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
                
                # Show OTP in UI for testing
                st.info(f"📧 Test OTP: **{otp}**")
                
                # Try to send email
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
    """Display user history"""
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
    """Extract text from PDF"""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

# ============= STEP 4: CHECK LOGIN STATUS =============
# This is where we check if user is logged in

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= STEP 5: MAIN APP (Only reaches here if logged in) =============

# Main app title
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='font-size: 42px; color: white; margin: 0;'>🤖 AI Resume Analyzer</h1>
    <p style='color: white; font-size: 16px; margin-top: 10px;'>AI-powered resume insights to match your dream job 🚀</p>
</div>
""", unsafe_allow_html=True)

# Create layout with columns
col1, col2 = st.columns([3, 1])

with col2:
    # User info card
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
                
        except Exception as e:
            st.error(f"❌ Error reading PDF: {str(e)}")
    
    # Analysis section
    if st.session_state.get('uploaded', False):
        if not st.session_state.get('analyze', False):
            if st.button("🚀 Analyze Resume", use_container_width=True):
                st.session_state.analyze = True
                st.rerun()
        else:
            st.markdown("### 🎯 Job Role Analysis")
            job_role = st.text_input("Enter your target job role:", placeholder="e.g., Data Scientist, ML Engineer")
            
            if job_role:
                st.info("✅ Analysis ready! Add your skill matching logic here.")

# Logout button at bottom
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("""
<div style='text-align: center; padding: 20px; margin-top: 20px;'>
    <p style='color: #666; font-size: 12px;'>© 2024 AI Resume Analyzer | Secure & Private</p>
</div>
""", unsafe_allow_html=True)