import os
import io
import time
import random
import itertools
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request  
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader
import docx

# .env file se secret API keys load karne ke liye
load_dotenv()

app = FastAPI(title="VIRACORP Multi-Language Engine (Groq Powered)", version="9.3.0")

# Enable CORS for Frontend Interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq ka stable aur super fast model
GROQ_MODEL = "openai/gpt-oss-20b"

# --- MULTI-KEY ROTATION & FAILOVER SYSTEM ---
# Yeh .env se saari keys utha kar aik list bana lega (Chahe jitni marzi keys rakho)
API_KEYS = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4")
]
# Sirf woh keys rakhega jo mojood (not None/empty) hain
API_KEYS = [k for k in API_KEYS if k and k.strip()]

if not API_KEYS:
    print("[VIRACORP Warning]: No Groq API keys found in .env file!")

# Keys ko gol gol ghumane ke liye iterator
key_cycle = itertools.cycle(API_KEYS) if API_KEYS else None

def get_next_groq_client():
    """Har request par agli key uthaye ga, agar aik ki limit cross ho tou agli par switch ho jaye ga."""
    if not key_cycle:
        return Groq(api_key="")
    current_key = next(key_cycle)
    return Groq(api_key=current_key)


def query_groq_api(prompt: str, language: str = "Auto") -> str:
    """
    Queries Groq API with multi-key automatic failover & multi-language force.
    """
    if not API_KEYS:
        return "Backend Error: No GROQ_API_KEY is found in your .env file."

    # Multilingual Enforcement Logic
    if language == "Auto" or not language:
        lang_instruction = (
            "CRITICAL LANGUAGE RULE: Detect the language of the user's prompt below. "
            "If the user wrote in Roman Urdu/Hindi, you MUST reply strictly in Roman Urdu. "
            "If the user wrote in Urdu , reply in Urdu. "
            "If in Pashto, reply in Pashto. "
            "NEVER reply in English if the user's prompt is in another language!"
        )
    else:
        lang_instruction = f"CRITICAL LANGUAGE RULE: You MUST reply strictly in this language: '{language}'."

    system_instruction = (
        f"You are a friendly, warm, and conversational AI Career Assistant for VIRACORP. "
        f"If anyone asks who built, created, or established you, or who is your owner/CEO, you must proudly state that "
        f"you were established by VIRACORP, and the Owner & CEO is Muhammad Mubashir. "
        f"{lang_instruction} "
        f"Keep responses engaging, polite, professional, point-to-point, and ATS-aligned."
    )
    
    full_user_content = f"{prompt}\n\n[Reminder: You must reply in the exact same language as the prompt above.]"

    # Multi-key automatic failover loop
    attempts = len(API_KEYS)
    for _ in range(attempts):
        try:
            groq_client = get_next_groq_client()
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": full_user_content}
                ],
                temperature=0.7,
                max_tokens=2048,
            )
            
            if completion.choices and completion.choices[0].message.content:
                return completion.choices[0].message.content
                
        except Exception as err:
            err_str = str(err)
            print(f"[VIRACORP Key Switch Notice]: Key failed or limit reached ({err_str}). Trying next key...")
            continue # Agli key par chale jao

    return "VIRACORP Engine Notice: All API keys exhausted or system busy. Please try again later."
    

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    ext = filename.split(".")[-1].lower()
    text = ""
    try:
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        elif ext in ["docx", "doc"]:
            doc = docx.Document(io.BytesIO(file_bytes))
            for p in doc.paragraphs:
                text += p.text + "\n"
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        text = f"Error reading file content: {str(e)}"
    return text.strip()


# --- REQUEST SCHEMAS ---

class ChatReq(BaseModel):
    prompt: str
    language: Optional[str] = "Auto"

class CvTestReq(BaseModel):
    resume_text: str
    language: Optional[str] = "Auto"

class CvCreateReq(BaseModel):
    full_name: str
    father_name: Optional[str] = ""
    email: str
    phone: str
    address: Optional[str] = ""
    target_role: str
    summary: Optional[str] = ""
    education: List[str]
    work_experience: List[str]
    skills: List[str]
    projects: Optional[List[str]] = []
    certifications: Optional[List[str]] = []
    languages_known: Optional[List[str]] = ["English", "Urdu"]
    additional_notes: Optional[str] = ""
    language: Optional[str] = "Auto"

class IntQuestionsReq(BaseModel):
    category: str
    language: Optional[str] = "Auto"

class IntEvalReq(BaseModel):
    category: str
    questions: List[str]
    answers: List[str]
    language: Optional[str] = "Auto"


# --- STATUS STEPS ---

STATUS_STEPS = {
    "cv_process": [
        "VIRACORP Searching profile criteria...",
        "Analyzing industry skills & ATS alignment...",
        "Reading work experience & background...",
        "Structuring professional resume formatting...",
        "VIRACORP Finalizing document..."
    ],
    "interview_process": [
        "VIRACORP Searching domain database...",
        "Analyzing candidate response patterns...",
        "Reading technical competencies...",
        "VIRACORP Computing final ATS score..."
    ],
    "chat_process": [
        "VIRACORP Searching intelligence base...",
        "Analyzing query context...",
        "VIRACORP Formulating response..."
    ]
}


# --- API ENDPOINTS ---

@app.get("/")
def health():
    return {
        "status": "VIRACORP Engine 9.3.0 Active (Groq Powered, Multi-Language & Dynamic)",
        "multilingual_chat": "Enabled",
        "transmission_loaders": "Active"
    }

@app.post("/api/chat")
async def chat_endpoint(req: ChatReq):
    res = query_groq_api(req.prompt, req.language)
    return {
        "result": res,
        "status_flow": STATUS_STEPS["chat_process"]
    }

@app.post("/api/cv/test")
async def test_cv(req: CvTestReq):
    prompt = f"Analyze this CV for ATS Score (0-100), grammar errors, and job objective match. Be encouraging and helpful:\n\n{req.resume_text}"
    res = query_groq_api(prompt, req.language)
    return {
        "result": res,
        "status_flow": STATUS_STEPS["cv_process"]
    }

@app.post("/api/cv/improve")
async def improve_cv(req: CvTestReq):
    prompt = f"Improve and rewrite this CV content into a professional ATS Markdown format:\n\n{req.resume_text}"
    res = query_groq_api(prompt, req.language)
    return {
        "result": res,
        "status_flow": STATUS_STEPS["cv_process"]
    }

@app.post("/api/cv/create")
async def create_cv(request: Request):
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
            full_name = data.get("full_name", "Valued Candidate")
            email = data.get("email", "candidate@email.com")
            phone = data.get("phone", "+92 300 0000000")
            target_role = data.get("target_role", "Professional")
            father_name = data.get("father_name", "")
            address = data.get("address", "")
            summary = data.get("summary", "")
            skills = data.get("skills", "")
            languages_known = data.get("languages_known", "")
            education = data.get("education", "")
            work_experience = data.get("work_experience", "")
            projects = data.get("projects", "")
            certifications = data.get("certifications", "")
            template_style = data.get("template_style", "Modern ATS")
            language = data.get("language", "Auto")
            extracted_file_text = ""
        else:
            form = await request.form()
            full_name = form.get("full_name", "Valued Candidate")
            email = form.get("email", "candidate@email.com")
            phone = form.get("phone", "+92 300 0000000")
            target_role = form.get("target_role", "Professional")
            father_name = form.get("father_name", "")
            address = form.get("address", "")
            summary = form.get("summary", "")
            skills = form.get("skills", "")
            languages_known = form.get("languages_known", "")
            education = form.get("education", "")
            work_experience = form.get("work_experience", "")
            projects = form.get("projects", "")
            certifications = form.get("certifications", "")
            template_style = form.get("template_style", "Modern ATS")
            language = form.get("language", "Auto")
            
            extracted_file_text = ""
            file = form.get("file")
            if file and hasattr(file, "filename") and file.filename:
                file_bytes = await file.read()
                if file_bytes:
                    extracted_file_text = extract_text_from_file(file_bytes, file.filename)

    except Exception as e:
        return {"result": f"Error parsing form data: {str(e)}", "status_flow": []}

    prompt = f"""CRITICAL LANGUAGE INSTRUCTION: You MUST write the entire resume response strictly in this language: '{language}'. If '{language}' is Roman Urdu, write the summary, bullet points, and descriptions in natural Roman Urdu. If it is Urdu, write in Urdu script.

Generate a professional, high-scoring ATS Resume using the selected template style: '{template_style}' in clean Markdown format based strictly on the candidate's provided details below:

### CANDIDATE INFORMATION:
- **Full Name:** {full_name}
- **Father's Name:** {father_name}
- **Email:** {email} | **Phone:** {phone} | **Location:** {address}
- **Target Role:** {target_role}

### PROFESSIONAL SUMMARY:
{summary if summary else f'Motivated and results-driven {target_role} with strong dedication to excellence.'}

### SKILLS & COMPETENCIES:
{skills if skills else 'Communication, Problem Solving, Teamwork'}

### WORK EXPERIENCE:
{work_experience if work_experience else 'Professional experience aligned with industry standards.'}

### EDUCATION:
{education if education else 'Bachelor\'s Degree / Relevant Education'}

### PROJECTS:
{projects if projects else 'N/A'}

### CERTIFICATIONS:
{certifications if certifications else 'N/A'}

### LANGUAGES:
{languages_known if languages_known else 'English, Urdu'}

### REFERENCE / UPLOADED DOCUMENT DATA (Incorporate if relevant):
{extracted_file_text[:1500] if extracted_file_text else 'N/A'}

Format this specifically tailored to the '{template_style}' layout with clear visual hierarchy, professional section headers, and powerful ATS bullet points using the exact data provided above.
"""
    
    res = query_groq_api(prompt, language)
    res += f"\n\n---\n*Template Style: {template_style} | Verified & Published by VIRACORP AI Career Engine (Established by Muhammad Mubashir)*"
    
    return {
        "result": res,
        "template_applied": template_style,
        "status_flow": STATUS_STEPS["cv_process"]
    }

@app.post("/api/interview/questions")
async def get_questions(req: IntQuestionsReq):
    random_seed = random.randint(1000, 9999)
    prompt = f"Generate exactly 5 completely unique, fresh, and randomized technical & HR interview questions (Variation ID: {random_seed}) for job field: '{req.category}'. Return as a clean numbered list 1-5."
    
    raw = query_groq_api(prompt, req.language)
    lines = [line.strip() for line in raw.split("\n") if line.strip() and any(c.isdigit() for c in line[:3])]
    if len(lines) < 5:
        lines = [
            f"1. Can you explain a complex project you handled in {req.category}?",
            f"2. What tools or frameworks do you prefer most in {req.category}?",
            "3. How do you handle unexpected blockers or tight deadlines?",
            "4. Describe a time you worked in a team to resolve a tough problem.",
            "5. Why should VIRACORP hire you for this role?"
        ]
    return {
        "questions": lines[:5],
        "status_flow": STATUS_STEPS["interview_process"]
    }

@app.post("/api/interview/evaluate")
async def evaluate_quiz(req: IntEvalReq):
    qa_formatted = "\n".join([f"Q{i+1}: {q}\nAnswer: {a}\n" for i, (q, a) in enumerate(zip(req.questions, req.answers))])
    prompt = f"""Evaluate these 5 interview answers for candidate in '{req.category}':

{qa_formatted}

Provide in a friendly, encouraging tone:
1. Overall ATS Interview Score (0-100)
2. Detailed constructive feedback on each answer
3. Hiring Recommendation
"""
    res = query_groq_api(prompt, req.language)
    return {
        "result": res,
        "status_flow": STATUS_STEPS["interview_process"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)