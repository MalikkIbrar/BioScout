# 🌿 BioScout — AI-Powered Wildlife Observation Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0-green?logo=django)](https://djangoproject.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?logo=streamlit)](https://streamlit.io)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek_V3-purple)](https://deepseek.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

BioScout is a full-stack AI wildlife observation platform for Pakistan and South Asia. Citizens, researchers, and nature enthusiasts can photograph wildlife, get instant AI species identification, and ask natural-language questions answered by a RAG knowledge base of 50 species.

---

## ✨ Features

- **AI Species Identification** — Upload a photo, get the species name, confidence score, and ecological details via DeepSeek Vision + iNaturalist fallback
- **RAG Q&A Chatbot** — Ask anything about South Asian wildlife; answers are grounded in a curated knowledge base (no hallucinations)
- **Hybrid Search** — BM25 keyword search + ChromaDB vector search fused with Reciprocal Rank Fusion
- **Interactive Map** — All observations plotted on a Folium map with category colour-coding
- **JWT Authentication** — Register, login, and submit observations securely
- **REST API** — Full DRF API with Swagger docs at `/api/docs/`
- **50-species Knowledge Base** — Birds, mammals, reptiles, plants, and insects of Pakistan

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Frontend | Streamlit |
| AI / LLM | DeepSeek V3 (Vision + Chat) |
| RAG | ChromaDB + BM25 (rank_bm25) + RRF fusion |
| Embeddings | all-MiniLM-L6-v2 via onnxruntime (no torch) |
| Auth | JWT via djangorestframework-simplejwt |
| API Docs | drf-spectacular (Swagger UI) |
| Maps | Folium + streamlit-folium |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Deployment | Railway (backend) + Streamlit Cloud (frontend) |

---

## 🧠 RAG Architecture

```
User Question
      ↓
Hybrid Retriever
 ├── BM25 keyword search (rank_bm25)        ← great for species names
 └── Vector semantic search (ChromaDB)      ← great for concepts
      ↓
Reciprocal Rank Fusion (RRF score merging)
      ↓
Top-3 Species Documents (grounded context)
      ↓
DeepSeek LLM (generates answer from context)
      ↓
Answer + Sources + Confidence Score
```

**Retrieval accuracy: 70% on 10-question benchmark** (BM25 contributed 7 hits, vector 3 hits, both methods combined on 20 results).

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/MalikkIbrar/BioScout.git
cd BioScout
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

### 3. Run migrations & seed data

```bash
python manage.py migrate
python manage.py seed_data          # 20 Pakistan wildlife observations
python manage.py build_rag_index    # Build ChromaDB + BM25 indexes
```

### 4. Start servers

```bash
# Terminal 1 — Django backend
python manage.py runserver

# Terminal 2 — Streamlit frontend
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/observations/` | List all observations (paginated, filterable) |
| POST | `/api/observations/` | Submit new observation (JWT required) |
| GET | `/api/observations/search/?q=eagle` | Full-text search |
| GET | `/api/stats/` | Platform statistics |
| POST | `/api/identify/` | AI species identification from image |
| POST | `/api/species-qa/` | Simple DeepSeek Q&A |
| POST | `/api/species-qa/rag/` | RAG-grounded Q&A |
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, get JWT tokens |
| GET | `/api/docs/` | Swagger UI |

---

## 🧪 Running Tests

```bash
python manage.py test observations
```

---

## 🚢 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway + Streamlit Cloud deployment guide.

### Environment variables required in production

```
SECRET_KEY=<long-random-string>
DEBUG=False
ALLOWED_HOSTS=your-domain.railway.app
DATABASE_URL=postgresql://...
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
BASE_URL=https://your-domain.railway.app
```

---

## 📁 Project Structure

```
BioScout/
├── backend/                  # Django project config
│   ├── settings.py
│   └── urls.py
├── observations/             # Main Django app
│   ├── models.py             # Observation model
│   ├── views.py              # REST API views
│   ├── ai_views.py           # AI identification + Q&A endpoints
│   ├── auth_views.py         # JWT register/login
│   ├── serializers.py
│   ├── urls.py
│   ├── rag/                  # RAG system
│   │   ├── knowledge_base.py # 50 species documents
│   │   ├── vector_store.py   # ChromaDB vector search
│   │   ├── bm25_search.py    # BM25 keyword search
│   │   ├── hybrid_retriever.py # RRF fusion
│   │   └── evaluate.py       # Benchmark evaluation
│   └── management/commands/
│       ├── seed_data.py      # 20 Pakistan observations
│       ├── build_rag_index.py
│       └── evaluate_rag.py
├── frontend/
│   ├── app.py                # Streamlit 6-page app
│   └── utils.py              # API client functions
├── data/
│   ├── chroma_db/            # ChromaDB vector index
│   └── bm25_index.pkl        # BM25 serialised index
├── .env.example
├── requirements.txt
├── Procfile                  # Railway deployment
└── RAG_LEARNING.md           # Deep-dive RAG explanation
```

---

## 📖 Learn More

- [RAG_LEARNING.md](RAG_LEARNING.md) — Deep-dive explanation of the RAG system with pseudocode, for AI engineers
- [DEPLOYMENT.md](DEPLOYMENT.md) — Step-by-step Railway + Streamlit Cloud deployment

---

## 👤 Author

**Malik Ibrar** — AI Engineer

[![GitHub](https://img.shields.io/badge/GitHub-MalikkIbrar-181717?logo=github)](https://github.com/MalikkIbrar/BioScout)
[![Upwork](https://img.shields.io/badge/Upwork-Available-6fda44?logo=upwork)](https://upwork.com)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
