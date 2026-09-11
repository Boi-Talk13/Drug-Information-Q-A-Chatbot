# MedCite — Code Walkthrough (demo cheat sheet)

Use this to open the right file the moment a judge asks. Every file also has a
comment header explaining what it does.

## The 4-step pipeline (the whole product)
1. **Read the PDF, keep page numbers** → `backend/pdf_reader/reader.py`
2. **Cut into pieces by section** → `backend/pdf_reader/chunker.py`
3. **Search the pieces (BM25 + meaning)** → `backend/search/hybrid.py`, `bm25.py`
4. **AI writes the answer, we verify the pages** → `backend/ai_answer/llm.py`, `answer.py`

> One line: *the search decides what is true, the AI only writes it in good
> English, and we check every page number before the user sees it.*

## "Show me where X happens"

| Judge asks… | Open this file | Key point |
|---|---|---|
| How do you keep the page number? | `backend/pdf_reader/reader.py` | PyMuPDF; physical page = index+1, stored on every chunk |
| Why cut by section, not size? | `backend/pdf_reader/chunker.py` | split on headings so a dose is never cut in half |
| How does search work? | `backend/search/hybrid.py` | BM25 (exact words) + TF-IDF (meaning), blended 0–1 |
| Lay words like "side effects"? | `backend/search/synonyms.py` | expands to "adverse reactions" etc. |
| How is the answer written? | `backend/ai_answer/llm.py` | Groq if key set, else extractive fallback |
| **How do you stop hallucinated pages?** | `backend/ai_answer/answer.py` | `_strip_unverified_pages`, dedup, answer↔citation match |
| How does it refuse safely? | `backend/ai_answer/safety.py` | no-doc / out-of-domain / advice / greetings |
| The API endpoints | `backend/api/main.py` | `/api/chat`, `/api/upload`, `/api/drugs`, `/api/pdf`, `/api/history`, `/api/stats` |
| The database | `backend/api/db.py` | PostgreSQL (SQLite fallback); per-user `user_id` isolation |
| Multi-user separation | `backend/api/db.py` + `search/index.py` | every row/PDF tagged with owner; queries filtered by it |
| The chat screen | `frontend/src/components/ChatScreen.jsx` | orchestrates everything, calls the API |
| Clickable page citation | `frontend/src/components/Citation.jsx` + `AssistantMessage.jsx` | parses `[p. N]`, opens PDF |
| Real PDF + highlight | `frontend/src/components/PdfViewerPanel.jsx` | react-pdf, jump to page, highlight source |
| Upload / delete PDFs | `frontend/src/components/MedicineListModal.jsx` | multi-upload, per-user library |
| All API calls | `frontend/src/services/apiService.js` | chat, upload, drugs, user id |

## The 3 guarantees (say these)
1. **Correct pages** — a citation's page is the real page the text came from.
2. **No duplicate citations** — one entry per page.
3. **Answer = source** — every `[p. N]` in the answer is backed by retrieved text; invented pages are stripped. → all in `backend/ai_answer/answer.py`.

## Likely tough questions
- **"What if the AI is wrong?"** → It can't invent facts: search picks the text, the AI only rewords it, and we verify every page. Without a key it still answers extractively.
- **"Many users?"** → One database, a `user_id` on every personal row, `WHERE user_id = ?` on every read. Scales to millions; the real cap is the AI API rate limit.
- **"Is the AI key used for facts?"** → No — only for phrasing. Facts and page numbers come from our search.
- **"Deployment?"** → Docker on one small cloud VM; `Dockerfile` + `docker-compose.yml`.

## Run it
```bash
# backend (from project root)
uvicorn backend.api.main:app --port 8000
# frontend
cd frontend && npm run dev        # http://localhost:3000
# live database view
bash watch-db.sh
```
