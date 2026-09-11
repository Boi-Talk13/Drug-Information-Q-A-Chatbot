# MedCite backend

Read a medicine PDF, search it, and answer with a page number for every fact.
The search decides what is true; the AI only writes it in good English. If the
document does not say it, the bot says so instead of guessing.

## What each part does

```
backend/
  pdf_reader/   reads PDFs with PyMuPDF, keeps the page number of every line,
                cuts each PDF into pieces at the section headings
  search/       BM25 (exact words) + TF-IDF cosine (meaning), mixed together;
                query expansion so "side effects" finds "adverse reactions"
  ai_answer/    writes the answer (Groq if a key is set, else extractive),
                then verifies every [p. N] against the retrieved text
  api/          FastAPI app + a small SQLite answer log for monitoring
```

## The three guarantees (enforced in `ai_answer/answer.py`)

1. **Correct pages** — a citation's page is the real physical PDF page the text
   came from, so clicking it in the viewer lands on the right page.
2. **No duplicates** — the citation list has exactly one entry per page.
3. **Answer and source match** — every `[p. N]` left in the answer also appears
   in the citation list; any page the model invents (not in the retrieved
   pieces) is stripped out before the user sees it.

If the match is weak but present, the bot gives the closest related label text
and says it is related — instead of a flat "I don't know". It only refuses when
there is essentially nothing, when the drug's PDF isn't loaded, or when the
question is outside what a drug label covers.

## Run it locally (no Docker)

```bash
pip install -r backend/requirements.txt

# 1. Put medicine PDFs in data/pdfs (file name sets the drug id:
#    rinvoq_pi.pdf -> "rinvoq", matching the frontend dropdown), or fetch samples:
python -m backend.fetch_sample_pdfs

# 2. Build the search index
python -m backend.build_index

# 3. Start the API
uvicorn backend.api.main:app --reload --port 8000
```

Then run the frontend (`cd frontend && npm install && npm run dev`) and toggle
**Live API** on in the header, or build the frontend (`npm run build`) and open
http://localhost:8000 — the API serves the built app on the same port.

No API key is required: without `AI_API_KEY` the backend answers extractively
from the PDF text (page numbers still guaranteed). Set a Groq key in `.env` for
smoother prose.

## Endpoints

| Method | Path          | Purpose |
|--------|---------------|---------|
| POST   | `/api/chat`   | `{question, history, drug_filter}` → answer + citations |
| POST   | `/api/upload` | multipart `file=<pdf>` → `{id, name, pages}`; re-indexes |
| GET    | `/api/drugs`  | indexed medicines |
| GET    | `/api/health` | status, mode (groq/extractive), indexed drugs |
| GET    | `/api/stats`  | monitoring: questions, refusals, refusal rate, latency |
