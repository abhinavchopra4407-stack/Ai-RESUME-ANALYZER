import streamlit as st
import PyPDF2
import re
import pandas as pd
import plotly.express as px
import base64
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus import KeepTogether
import json
from datetime import datetime, timedelta, timezone
import random
import yagmail
import os
import requests
from io import BytesIO

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

def get_chatgpt_response(prompt, context=""):
    try:
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
            "model": "qwen/qwen-2.5-7b-instruct:free",
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
                {"role": "system", "content": "You are an expert resume reviewer."},
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
• Build a data analysis dashboard"""
    
    else:
        return """🤖 **I'm your AI Career Assistant!**

Ask me about:
📝 Resume improvement tips
🎯 Career path guidance
💪 Skill development strategies
🚀 Project ideas for portfolio
🎤 Interview preparation
📊 Job search strategies"""

def get_fallback_suggestions(job_role):
    return f"""📝 **Resume Suggestions for {job_role} role:**

1. **Add Missing Keywords:** Include role-specific keywords like programming languages, frameworks, and tools

2. **Quantify Achievements:** Use numbers to show impact (e.g., "Improved performance by 40%")

3. **Use Strong Action Verbs:** Start bullets with words like Developed, Built, Optimized, Led

4. **Add a Projects Section:** Include 2-3 relevant projects with descriptions and technologies used

5. **Tailor Your Resume:** Customize for each application by matching keywords from job description

💡 **Pro Tip:** Always include metrics and results, not just responsibilities!"""

def create_professional_pdf(report_data, user_email):
    """Create a comprehensive professional PDF report"""
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    # Custom styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#6366f1'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName='Helvetica-Bold'
    )
    
    # Heading style
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#22c55e'),
        spaceBefore=20,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    )
    
    # Subheading style
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#6366f1'),
        spaceBefore=15,
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    # Body text style
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.black,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Score style
    score_style = ParagraphStyle(
        'ScoreStyle',
        parent=styles['Normal'],
        fontSize=36,
        textColor=colors.HexColor('#22c55e'),
        alignment=TA_CENTER,
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    # ========== COVER PAGE ==========
    # Title
    elements.append(Paragraph("AI Resume Analysis Report", title_style))
    elements.append(Spacer(1, 20))
    
    # AI Icon and decorative line
    elements.append(Paragraph("🤖", ParagraphStyle('Icon', parent=styles['Normal'], fontSize=48, alignment=TA_CENTER)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Powered by Advanced AI Technology", body_style))
    elements.append(Spacer(1, 30))
    
    # Score Box
    elements.append(Paragraph(f"<b>Overall Match Score</b>", heading_style))
    elements.append(Paragraph(f"{report_data['score']}%", score_style))
    
    # Score gauge visualization (text-based)
    if report_data['score'] >= 80:
        score_level = "🌟 Excellent"
        score_color = "#22c55e"
    elif report_data['score'] >= 60:
        score_level = "📈 Good"
        score_color = "#f59e0b"
    else:
        score_level = "⚠️ Needs Improvement"
        score_color = "#ef4444"
    
    elements.append(Paragraph(f"<b>Rating:</b> <font color='{score_color}'>{score_level}</font>", body_style))
    elements.append(Spacer(1, 20))
    
    # ========== REPORT INFORMATION ==========
    current_ist = get_indian_time()
    elements.append(Paragraph("Report Information", heading_style))
    elements.append(Paragraph(f"<b>Generated on:</b> {current_ist.strftime('%d-%m-%Y')}", body_style))
    elements.append(Paragraph(f"<b>Time:</b> {current_ist.strftime('%I:%M:%S %p IST')}", body_style))
    elements.append(Paragraph(f"<b>User:</b> {user_email}", body_style))
    elements.append(Paragraph(f"<b>Target Role:</b> {report_data['job_role'].title()}", body_style))
    elements.append(Spacer(1, 20))
    
    # ========== SKILLS ANALYSIS ==========
    elements.append(PageBreak())
    elements.append(Paragraph("Skills Analysis", heading_style))
    
    # Matched Skills
    elements.append(Paragraph("✅ Matched Skills", subheading_style))
    if report_data['matched']:
        for skill in report_data['matched']:
            elements.append(Paragraph(f"• {skill}", body_style))
    else:
        elements.append(Paragraph("No matching skills found", body_style))
    elements.append(Spacer(1, 15))
    
    # Missing Skills
    elements.append(Paragraph("❌ Missing Skills", subheading_style))
    if report_data['missing']:
        for skill in report_data['missing']:
            elements.append(Paragraph(f"• {skill} (Priority: High)", body_style))
    else:
        elements.append(Paragraph("Great! You have all required skills!", body_style))
    
    elements.append(Spacer(1, 20))
    
    # ========== SCORE BREAKDOWN ==========
    elements.append(Paragraph("Score Breakdown", heading_style))
    
    # Score details
    total_skills = len(report_data['matched']) + len(report_data['missing'])
    skill_coverage = int((len(report_data['matched']) / total_skills) * 100) if total_skills > 0 else 0
    
    # Table for score breakdown
    score_data = [
        ["Metric", "Value", "Status"],
        ["Skill Match", f"{report_data['score']}%", "✅" if report_data['score'] >= 60 else "⚠️"],
        ["Skill Coverage", f"{skill_coverage}%", "✅" if skill_coverage >= 50 else "⚠️"],
        ["Total Skills Analyzed", str(total_skills), "📊"],
        ["Matched Skills", str(len(report_data['matched'])), "✅"],
        ["Missing Skills", str(len(report_data['missing'])), "📚"]
    ]
    
    t = Table(score_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (2, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (2, 0), 12),
        ('BOTTOMPADDING', (0, 0), (2, 0), 12),
        ('BACKGROUND', (0, 1), (2, -1), colors.beige),
        ('GRID', (0, 0), (2, -1), 1, colors.grey),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # ========== RESUME STRENGTH ANALYSIS ==========
    elements.append(PageBreak())
    elements.append(Paragraph("Resume Strength Analysis", heading_style))
    
    # Determine strength level
    if report_data['score'] >= 80:
        strength = "Excellent"
        strength_color = "#22c55e"
        recommendation = "Your resume is well-aligned with the target role. Focus on interview preparation."
    elif report_data['score'] >= 60:
        strength = "Good"
        strength_color = "#f59e0b"
        recommendation = "Your resume has good potential. Add missing skills to become an ideal candidate."
    elif report_data['score'] >= 40:
        strength = "Average"
        strength_color = "#ef4444"
        recommendation = "Significant improvement needed. Focus on building core skills and projects."
    else:
        strength = "Weak"
        strength_color = "#dc2626"
        recommendation = "Major overhaul needed. Consider upskilling and restructuring your resume."
    
    elements.append(Paragraph(f"<b>Strength Level:</b> <font color='{strength_color}'>{strength}</font>", body_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Recommendation:</b> {recommendation}", body_style))
    elements.append(Spacer(1, 20))
    
    # ========== LEARNING PATH ==========
    elements.append(Paragraph("Recommended Learning Path", heading_style))
    
    if report_data['missing']:
        for idx, skill in enumerate(report_data['missing'][:7], 1):
            elements.append(Paragraph(f"{idx}. <b>Learn {skill.title()}</b> through online courses and hands-on projects", body_style))
            elements.append(Spacer(1, 5))
    else:
        elements.append(Paragraph("Congratulations! You have all required skills. Focus on advanced topics and interview preparation.", body_style))
    
    elements.append(Spacer(1, 20))
    
    # ========== IMPROVEMENT SUGGESTIONS ==========
    elements.append(PageBreak())
    elements.append(Paragraph("Actionable Improvement Suggestions", heading_style))
    
    suggestions = []
    
    if report_data['missing']:
        suggestions.append(f"1. <b>Skill Development:</b> Prioritize learning {', '.join(report_data['missing'][:3])}")
    
    if report_data['score'] < 60:
        suggestions.append("2. <b>Project Portfolio:</b> Build 2-3 strong projects demonstrating your skills")
        suggestions.append("3. <b>Certifications:</b> Get relevant certifications from recognized platforms")
    
    suggestions.append("4. <b>Resume Format:</b> Use a clean, ATS-friendly format with clear section headers")
    suggestions.append("5. <b>Quantify Achievements:</b> Add numbers and metrics to your accomplishments")
    suggestions.append("6. <b>Action Verbs:</b> Start bullet points with strong action verbs")
    suggestions.append("7. <b>Tailor Content:</b> Customize your resume for each job application")
    
    for suggestion in suggestions[:8]:
        elements.append(Paragraph(suggestion, body_style))
        elements.append(Spacer(1, 8))
    
    # ========== ADDITIONAL RESOURCES ==========
    elements.append(PageBreak())
    elements.append(Paragraph("Additional Resources & Tips", heading_style))
    
    resources = [
        "📚 <b>Online Learning Platforms:</b> Coursera, Udemy, edX, NPTEL",
        "💻 <b>Practice Platforms:</b> LeetCode, HackerRank, Kaggle",
        "🔧 <b>Portfolio Hosting:</b> GitHub, GitLab, Personal Website",
        "📝 <b>Resume Templates:</b> Overleaf, Canva, Novoresume",
        "🌐 <b>Networking:</b> LinkedIn, GitHub, Stack Overflow",
        "🎯 <b>Job Portals:</b> LinkedIn Jobs, Naukri, Indeed, AngelList"
    ]
    
    for resource in resources:
        elements.append(Paragraph(resource, body_style))
        elements.append(Spacer(1, 10))
    
    # ========== FINAL NOTE ==========
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("<b>Need More Help?</b>", subheading_style))
    elements.append(Paragraph("Use the AI Career Assistant in the app for personalized advice and answers to your specific questions.", body_style))
    elements.append(Spacer(1, 20))
    
    # Footer
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(f"<hr/>", body_style))
    elements.append(Paragraph(f"<font size=8><i>Generated by AI Resume Analyzer • {current_ist.strftime('%d-%m-%Y %I:%M:%S %p IST')}</i></font>", body_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

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
    "data scientist": ["python", "machine learning", "pandas", "numpy", "sql", "statistics", "data visualization"],
    "ml engineer": ["python", "tensorflow", "pytorch", "deep learning", "nlp", "cnn", "model deployment"],
    "data analyst": ["excel", "sql", "power bi", "tableau", "python", "data visualization", "statistics"],
    "web developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "git"],
    "frontend developer": ["html", "css", "javascript", "react", "bootstrap", "tailwind", "git"],
    "backend developer": ["python", "java", "node.js", "sql", "api development", "database management", "docker"],
    "full stack developer": ["html", "css", "javascript", "react", "node.js", "mongodb", "git", "rest api"],
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
                        st.session_state.final_score = score
                        st.session_state.job_role = job_role
                        st.session_state.matched = matched
                        st.session_state.missing = missing
                        
                        st.subheader("📊 Score")
                        st.metric("Match Score", f"{score}%")
                        
                        st.subheader("✅ Matched Skills")
                        for m in matched:
                            st.write(f"✔ {m}")
                        
                        st.subheader("❌ Missing Skills")
                        for m in missing:
                            st.write(f"✖ {m}")
                        
                        # PDF Report Generation
                        if st.button("📄 Generate Detailed PDF Report", use_container_width=True):
                            with st.spinner("Generating PDF report..."):
                                report_data = {
                                    "job_role": job_role,
                                    "score": score,
                                    "matched": matched,
                                    "missing": missing
                                }
                                pdf_buffer = create_professional_pdf(report_data, st.session_state.username)
                                
                                st.download_button(
                                    label="⬇ Download PDF Report",
                                    data=pdf_buffer,
                                    file_name=f"Resume_Analysis_Report_{job_role}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                        
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

st.markdown("""
<div style='text-align: center; padding: 20px; margin-top: 20px;'>
    <p style='color: #666; font-size: 12px;'>© 2025 AI Resume Analyzer | Secure & Private | Powered by AI</p>
</div>
""", unsafe_allow_html=True)