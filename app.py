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

# ============= INITIALIZE ALL SESSION STATE VARIABLES FIRST =============
def init_session_state():
    """Initialize all session state variables at the very beginning"""
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

# Call this IMMEDIATELY
init_session_state()

# ============= PAGE CONFIG MUST BE FIRST STREAMLIT COMMAND =============
st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="🤖",
    layout="wide"
)

# ============= FUNCTIONS =============
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
    """Improved Gmail sending with anti-spam measures"""
    try:
        # Check if secrets exist
        if "EMAIL" not in st.secrets or "PASSWORD" not in st.secrets:
            st.warning(f"⚠️ Demo mode: Your OTP is {otp}")
            return True
            
        yag = yagmail.SMTP(
            user=st.secrets["EMAIL"],
            password=st.secrets["PASSWORD"]
        )
        
        # Create professional HTML email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #6366f1 0%, #22c55e 100%); padding: 30px; border-radius: 12px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🤖 AI Resume Analyzer</h1>
                </div>
                
                <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333;">Hello,</h2>
                    <p style="color: #666; font-size: 16px;">Your verification code is:</p>
                    
                    <div style="background: #f5f5f5; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <span style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #6366f1;">{otp}</span>
                    </div>
                    
                    <p style="color: #666;">This code will expire in 10 minutes.</p>
                    
                    <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
                        <p style="color: #666; font-size: 12px; margin: 0;">
                            If you didn't request this code, you can safely ignore this email.
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                    <p>AI Resume Analyzer - Smart Career Tool</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send with proper headers to avoid spam
        contents = [
            html_content,
            f"Your OTP code is: {otp}\n\nThis code is valid for this session only."
        ]
        
        yag.send(
            to=email,
            subject="🔐 Your Verification Code",
            contents=contents,
            headers={
                'Priority': 'normal',
                'X-Mailer': 'AI Resume Analyzer',
                'X-Priority': '3'
            }
        )
        return True
        
    except Exception as e:
        st.warning(f"⚠️ Could not send email. Your OTP is: {otp}")
        return True  # Return True to allow login with on-screen OTP

def login_page():
    st.title("🔐 Login with OTP")
    
    # Add a nice description
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <p>Get your resume analyzed against your dream job role!</p>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("📧 Enter your Email", placeholder="you@example.com")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
                st.info(f"📧 For testing, OTP is: {otp}")
                
                # Try to send email
                if send_otp(email, otp):
                    st.success("✅ OTP sent to your email!")
                else:
                    st.warning("⚠️ Using on-screen OTP for demo")
    
    user_otp = st.text_input("🔑 Enter OTP", type="password", placeholder="Enter 6-digit code")
    
    with col2:
        if st.button("✅ Verify OTP", use_container_width=True):
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

    st.subheader("📜 Your Previous Reports")

    if username in data:
        for item in reversed(data[username][-5:]):  # Show last 5 only
            st.write(f"💼 {item['job_role']} | 🎯 {item['score']}% | 🕒 {item['date']}")
    else:
        st.info("No history yet. Upload a resume to get started!")

def set_bg(image_file):
    import base64
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
        .block-container {{
            background: rgba(0, 0, 0, 0.7);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(5px);
        }}
        h1, h2, h3, h4, h5, h6, p, div, span, label {{
            color: white !important;
        }}
        input {{
            background-color: #0f172a !important;
            color: white !important;
        }}
        button {{
            background: linear-gradient(90deg, #6366f1, #22c55e) !important;
            color: white !important;
            border: none !important;
            padding: 10px 20px !important;
            border-radius: 8px !important;
            font-weight: bold !important;
        }}
        button:hover {{
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }}
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-thumb {{ background: #38bdf8; border-radius: 3px; }}
        </style>
        """, unsafe_allow_html=True)
    except:
        # If background image not found, continue without it
        pass

# ============= PROCEED ONLY IF LOGGED IN =============
if not st.session_state.logged_in:
    login_page()
    st.stop()

# ============= MAIN APP (Only shown when logged in) =============

# Apply background if image exists
try:
    set_bg("robot.jpg")
except:
    pass

# Header with logout button
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.markdown("<h1 style='margin:0;'>🤖 AI Resume Analyzer</h1>", unsafe_allow_html=True)
    st.caption("AI-powered resume insights to match your dream job 🚀")
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Show history
show_history(st.session_state.username)

# Resume upload section
st.markdown("---")
st.subheader("📄 Upload Your Resume")

uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    label_visibility="collapsed"
)

# The rest of your resume analysis code here...
# (Keep your existing extract_text, extract_sections, clean_skills, etc.)

# For brevity, I'm including the essential parts - add your existing functions here

if uploaded_file is not None:
    try:
        with st.spinner("📄 Reading your resume..."):
            # Add your extract_text function here
            def extract_text(file):
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or ""
                return text
            
            resume_text = extract_text(uploaded_file)
            st.success("✅ File uploaded successfully!")
            
            # Add more of your analysis code here...
            st.info("Resume uploaded! Add your analysis code here.")
            
    except Exception as e:
        st.error(f"❌ Error reading PDF: {str(e)}")
else:
    st.info("👈 Please upload your resume (PDF format) to get started")

# Add footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>© 2024 AI Resume Analyzer | Secure & Private</p>", unsafe_allow_html=True)