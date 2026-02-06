# Interview Assistant

An AI-powered interview assistant that guides candidates through a structured interview flow, evaluates answers, and generates a concise summary.

**Highlights**
- Guided interview flow with timed questions and instant feedback
- Gemini-backed question generation, evaluation, and summary
- Offline-safe fallback logic when the AI API is unavailable
- Clean single-page candidate experience

**Architecture**
- Frontend: React (Vite) with Redux state management
- Backend: FastAPI service for Gemini calls and fallback logic

**Quick Start**

Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:
```bash
GEMINI_API_KEY=your-key-here
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ALLOWED_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1)(:\d+)?$
```

Run the API:
```bash
uvicorn app.main:app --reload --port 8000
```

Frontend
```bash
npm install
```

Create a root `.env`:
```bash
VITE_API_BASE_URL=http://localhost:8000
```

Run the app:
```bash
npm run dev
```

Open the URL printed by Vite.

**API Endpoints**
- `GET /api/health`
- `POST /api/question`
- `POST /api/evaluate`
- `POST /api/summary`

**Environment Variables**
- `GEMINI_API_KEY` for Gemini access
- `ALLOWED_ORIGINS` to permit frontend origins
- `ALLOWED_ORIGIN_REGEX` to allow any localhost port in development
- `VITE_API_BASE_URL` to point the frontend at the backend

**Project Structure**
```
backend/
  app/
    main.py
    schemas.py
    gemini_client.py
    fallback.py
src/
  components/
  pages/
  services/
  store/
  utils/
```

**Notes**
- If the Gemini key is missing, the backend uses deterministic fallback logic.
- If your Vite port changes, update `ALLOWED_ORIGINS` or rely on `ALLOWED_ORIGIN_REGEX`.

