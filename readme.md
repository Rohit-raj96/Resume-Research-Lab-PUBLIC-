# Resume Research Lab

**Resume Research Lab** is an end‑to‑end ATS (Applicant Tracking System) research and experimentation project that analyzes resumes against job descriptions using NLP, scoring heuristics, and ML‑assisted logic.  
The project provides both a **Streamlit UI** for interactive analysis and a **FastAPI backend** for programmatic access.

---

## 🚀 Live Demo

🔗 **Streamlit App**: https://resume-research-lab.streamlit.app/

---

## 🎯 Key Features

- 📄 **Resume Parsing (PDF)** – Extracts structured text from resumes
- 🧾 **Job Description Parsing** – Optional JD upload for contextual scoring
- 📊 **ATS Scoring Engine** – Match score, verdict, and red flags
- 📚 **Batch Resume Ranking** – Compare multiple resumes against one JD
- 🧠 **Modular Core Logic** – Parsing, scoring, and ranking are reusable
- 🌐 **FastAPI Backend** – Clean REST APIs with Swagger documentation
- 🎨 **Streamlit Frontend** – Interactive UI for recruiters and analysts

---

## 🧱 Project Architecture

```
resume_lab/
├── app2.py                  # Streamlit application (UI)
├── backend/                 # FastAPI backend
│   └── app/
│       ├── main.py          # FastAPI entry point
│       ├── api/             # API routes
│       ├── schemas/         # Request/response models
│       └── services/        # Business logic layer
├── core/                    # Shared ATS logic (parsing, scoring, ranking)
├── docs/
│   └── images/              # Documentation screenshots
├── requirements.txt
├── .gitignore
```

---

## 🖥️ Streamlit Application

The Streamlit UI (`app2.py`) allows:

- Uploading a resume (PDF)
- Uploading an optional job description
- Viewing ATS score, verdict, and analysis
- Batch ranking of multiple resumes

Run locally:

```bash
streamlit run app2.py
```

---

## ⚙️ FastAPI Backend

The FastAPI service exposes ATS functionality via REST APIs.

### Run locally

```bash
uvicorn backend.app.main:app --reload
```

### Available Endpoints

- `GET /health` – Health check
- `POST /analyze/resume` – Resume + JD analysis

### Swagger UI

```
http://127.0.0.1:8000/docs
```

---

## 📦 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Rohit-raj96/Resume-Research-Lab-PUBLIC-.git
cd resume_lab
```

### 2. Create virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🧪 Technology Stack

- **Python 3.10+**
- **Streamlit** – UI layer
- **FastAPI** – Backend APIs
- **PyMuPDF** – PDF parsing
- **Pandas / NumPy** – Data processing
- **Scikit‑learn (optional)** – ML‑based scoring

---

## 📌 Use Cases

- Resume screening automation
- ATS behavior research
- HR analytics experiments
- Resume–JD matching demos
- Interview / portfolio project

---

## 🛠️ Roadmap

- JD requirement extraction with weights
- Confidence‑based scoring
- Side‑by‑side resume comparison
- Exportable ATS reports (CSV/PDF)
- Auth & role‑based access (future)

---

## 📄 License

This project is for **research, learning, and demonstration purposes**.

---

## 👤 Author

**Rohit Garg**  
AI / ML Engineer  
📍 Gurugram, India

---

> If you are a recruiter, hiring manager, or developer reviewing this project, feel free to explore the live demo or reach out for discussion.

