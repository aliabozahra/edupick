# EduPick — Deployment Guide (100% free tiers)

The project is split into two independently deployable apps:

```
gradduation_project/
├─ back/                         ← Flask API + AI (deploy as the "backend")
│  ├─ app.py                     ← entry point (Flask app = `app`)
│  ├─ ai_core, interview_engine, roadmap_agent, comparison_tool, quiz_agent, llms
│  ├─ data/                      ← RAG data (ships with the backend)
│  ├─ requirements.txt, Procfile, Dockerfile, .env.example
│  └─ _archive/                  ← old experiments (not deployed)
└─ Front/graduation-project--front/   ← React + Vite (deploy as the "frontend")
   ├─ src/config.js              ← reads VITE_API_URL
   ├─ vercel.json, public/_redirects   ← SPA routing
   └─ .env.example
```

Everything talks over HTTP, so the two can live on different hosts.

---

## Recommended free stack

| Piece | Free service | Why |
|------|--------------|-----|
| **Frontend** | **Vercel** (or Netlify / Cloudflare Pages) | free static hosting, global CDN, auto-deploy from GitHub |
| **Backend (AI)** | **Hugging Face Spaces – Docker** | free, ~16 GB RAM — enough for sentence-transformers + chromadb + crewai (Render/Railway free = 512 MB and usually too small) |
| **Database** | **MongoDB Atlas – M0** | free 512 MB cluster |
| **Vector store** | **Chroma**, rebuilt at startup from `back/data` | no extra service needed |
| **LLMs** | **Groq** (free), **OpenRouter** (free models), **Gemini** (free) | already wired in `llms.py` |
| **Web search** | **Serper.dev** | free 2,500 queries |
| **Email (reset)** | **Gmail App Password** | free |

---

## 1) Database — MongoDB Atlas (free)

1. Create an account at mongodb.com/atlas → build a free **M0** cluster.
2. Database Access → add a user (username + password).
3. Network Access → allow `0.0.0.0/0` (any IP) so the host can connect.
4. Connect → "Drivers" → copy the connection string:
   `mongodb+srv://USER:PASS@cluster0.xxxx.mongodb.net/?retryWrites=true&w=majority`
5. You'll paste this as `MONGO_URL` in the backend env.

---

## 2) Backend — Hugging Face Spaces (Docker, free)

1. huggingface.co → **New Space** → SDK = **Docker** → blank.
2. Push the **contents of `back/`** to the Space repo (the `Dockerfile` is already there). Either:
   - drag-drop files in the web UI, or
   - `git remote add space https://huggingface.co/spaces/<you>/edupick-api` then push.
3. Space → **Settings → Secrets** → add (from `back/.env.example`):
   - `MONGO_URL`, `MONGO_DB`
   - `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `SERPER_API_KEY`
   - `FRONTEND_ORIGIN` = your Vercel URL (e.g. `https://edupick.vercel.app`)
   - `EMAIL_SENDER`, `EMAIL_PASSWORD` (Gmail App Password)
4. It builds and serves on port **7860**. Your API base URL is the Space URL, e.g.
   `https://<you>-edupick-api.hf.space`
5. First request is slow (downloads the embedding model + builds the vector store once). After that it's cached.

> **Render / Railway / Fly.io** also work with the same `Dockerfile` or the `Procfile`
> (`web: gunicorn app:app ...`). On Render's *free* plan the ML libraries may exceed
> 512 MB RAM — prefer Hugging Face Spaces or a paid 1 GB+ instance if you hit OOM.

---

## 3) Frontend — Vercel (free)

1. Push the repo to GitHub.
2. vercel.com → **New Project** → import the repo.
3. **Root Directory** = `Front/graduation-project--front`.
4. Framework preset = **Vite** (build `npm run build`, output `dist`). `vercel.json` already
   handles SPA routing.
5. **Environment Variables** → add:
   - `VITE_API_URL` = your backend URL (e.g. `https://<you>-edupick-api.hf.space`)
6. Deploy. Copy the resulting URL and put it back into the backend's `FRONTEND_ORIGIN`
   secret (step 2.3), then redeploy the backend so CORS allows it.

(Netlify is identical: base dir `Front/graduation-project--front`, build `npm run build`,
publish `dist`; `public/_redirects` handles routing.)

---

## 4) Wire-up checklist

- [ ] Backend env has the real `MONGO_URL` + all API keys.
- [ ] Backend `FRONTEND_ORIGIN` = exact frontend URL (no trailing slash).
- [ ] Frontend `VITE_API_URL` = exact backend URL (no trailing slash).
- [ ] Visit the backend root URL → should return `{"message": "Backend running successfully 🚀"}`.
- [ ] Sign up / log in from the deployed frontend.

---

## Local development

```bash
# Backend
cd back
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env        # fill in keys
python app.py                 # http://localhost:5000

# Frontend (new terminal)
cd Front/graduation-project--front
npm install
copy .env.example .env        # VITE_API_URL=http://localhost:5000
npm run dev                   # http://localhost:5173
```

---

## Notes / gotchas

- **Secrets**: `.env` files are git-ignored. Never commit real keys. If the old Gmail
  password was ever committed, rotate it.
- **Cold starts**: free backends sleep when idle; the first call after a nap takes longer.
- **Vector store**: rebuilt automatically if `back/chroma_interview` is empty. On hosts with
  ephemeral disks it rebuilds on each cold start (a one-time delay). To persist it, mount a
  disk and set `CHROMA_DIR` to it.
- **Gemini**: direct Gemini billing may be $0-quota; the app already falls back to Groq.
