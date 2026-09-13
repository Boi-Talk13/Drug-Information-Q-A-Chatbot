# MedCite — Drug Information Q&A Chatbot with Citations

A chatbot that answers questions about medicines using **only** official medicine PDFs.
Every answer shows the page it came from. If the PDF does not say it, the bot says so instead of guessing.

Built for the Cognizant and GITAM student buildathon. Shortlisted use case number 7.
Type: GenAI / RAG / Responsible AI.

---

## Contents

1. [The problem](#the-problem)
2. [What MedCite does](#what-medcite-does)
3. [How it works](#how-it-works)
4. [The AI, its limits, and how we stay within them](#the-ai-its-limits-and-how-we-stay-within-them)
5. [How to run it](#how-to-run-it)
6. [Settings (.env)](#settings-env)
7. [Adding a medicine PDF](#adding-a-medicine-pdf)
8. [Tech used, and why](#tech-used-and-why)
9. [Database](#database)
10. [How many users it can handle](#how-many-users-it-can-handle)
11. [Deployment (AWS)](#deployment-aws)
12. [Folder structure](#folder-structure)
13. [How we test it](#how-we-test-it)
14. [Safety](#safety)
15. [Known weak spots](#known-weak-spots)
16. [Team](#team)
17. [What we did not build](#what-we-did-not-build)
18. [Data source](#data-source)

---

## The problem

Doctors, patients and family members need correct medicine information fast.

A normal chatbot can invent a dose. For medicine, a wrong answer is dangerous.

So we built a bot that cannot answer without proof from the document.

---

## What MedCite does

- **Answers from the official label only**, and cites the page for every fact, like `[p. 11]`.
- **Click a page number** and the PDF opens beside the chat at that page, with the cited text highlighted.
- **Refuses** questions that are not about a medicine label ("what is the weather?").
- **Advice questions** ("should I stop taking it?") get the label text plus a note to ask a doctor, never a yes or no.
- **Understands typos and texting shorthand**: `wht`, `tht`, `pregent`, `shud`, `medicin` are corrected before searching.
- **13 built-in medicines** that every user can read, straight away.
- **Verified uploads**: anyone can add a medicine PDF, but only one published on rxabbvie.com, proven by pasting its link.
- **Private uploads**: a user's own PDFs are visible only to that user.
- **30 questions per user per day**, so one person cannot use up everyone's AI budget.
- **Saved answers**: a question someone already asked is answered instantly from the database, for free.
- **Chat history** is kept per user, and every answer is logged.

---

## How it works

1. **Read.** We read each PDF and keep the page number of every line.
2. **Cut.** We cut it into small pieces at the section headings (Dosage, Warnings, Side Effects...).
   A piece that is only a heading, with no facts under it, is dropped.
3. **Correct.** When someone asks a question, typos and shorthand are fixed first.
4. **Search.** Two searches run together: BM25 finds exact words, TF-IDF finds related wording.
   Everyday words are expanded into label words ("side effects" also searches "adverse reactions").
5. **Rank by section.** Every US drug label uses the same section layout, so the question's intent
   decides which section should win: "who should not take it" lifts **4 Contraindications**,
   "too many tablets" lifts **10 Overdosage**. Summary pages that repeat every topic
   (page 1 Highlights, 17 Patient Counseling) are nudged down.
6. **Send only what is needed.** Usually 3 or 4 pieces go to the AI; up to 8 when several are close.
7. **Write.** The AI writes a short answer from those pieces only, and marks the page for each fact.
8. **Verify.** Every page number in the answer is checked against the pieces we actually sent.
   A page the AI made up is removed before anyone sees it.

The search decides what is true. The AI only puts it into good English.

### Important: nothing is trained

We do not train any model. Nothing is memorised.

The bot looks the answer up in the PDF every single time, like an open book.
This is why a new PDF works straight away, with no retraining.

The AI never reads all 90 pages of a PDF. It reads about half a page, roughly **1,150 tokens per question**.

---

## The AI, its limits, and how we stay within them

MedCite uses the `openai/gpt-oss-20b` model on **Groq**.

### Groq free plan limits

These limits belong to the **Groq account**, not to one API key. A new key in the same account does not add more.

| Limit | Free plan | What it means for MedCite |
|---|---|---|
| Tokens per day | 200,000 | About **170 new AI answers a day**, shared by all users |
| Tokens per minute | 8,000 | About **7 new AI answers a minute**, shared by all users |
| Requests per day | 1,000 | Not reached first |
| Requests per minute | 30 | Not reached first |

### What happens at each limit

| Situation | Speed | Answer |
|---|---|---|
| Up to ~7 new questions a minute | Fast, 1–2 seconds | AI answer |
| More than ~7 in one minute | Some people wait ~15–20 seconds (the app retries automatically) | AI answer |
| More than ~170 in one day | Still fast | **Backup answer** (see below) |
| A question asked before | Instant | Saved AI answer, no limit used |

### The backup writer

If Groq cannot answer (for example the daily limit is used up), MedCite does not break.
It uses a built-in **backup writer** that needs no AI and no API key: it copies the best-matching
sentences straight from the PDF and adds their page numbers.

It is free and unlimited, but the answer is less clear, because sentences are joined rather than written.
The server log prints a line whenever this happens, so it is never silent.

### How we keep token use low

- **Adaptive context**: usually 3 pieces instead of 8, which halved tokens per question.
- **Saved answers shared between users**: for the built-in medicines everyone reads the same PDF,
  so one saved answer serves every user who asks the same question.
- **30 questions per user per day**: only answers the AI actually writes count.
  Saved answers, greetings and refusals are free. The count resets at midnight India time.
- Every AI call prints its token use in the server log, for example
  `[llm] tokens: 1115 in + 122 out = 1237`.

### For real traffic: Groq's paid plan

Pay-as-you-go and much higher limits. At Groq's listed price for this model
($0.075 per million input tokens, $0.30 per million output tokens), 500 questions a day
costs roughly **$1.70 a month**.

---

## How to run it

### Option 1: Docker (one command)

```
git clone https://github.com/Boi-Talk13/Drug-Information-Q-A-Chatbot.git
cd Drug-Information-Q-A-Chatbot
cp .env.example .env
```

Open `.env` and put your real Groq API key in `AI_API_KEY`. Then:

```
docker compose up --build
```

Open http://localhost:8000. The backend builds the search index from the PDFs on start.

### Option 2: Run the parts yourself (for development)

Backend (Python 3.11+):

```
pip install -r backend/requirements.txt
python3 -m uvicorn backend.api.main:app --port 8000
```

Frontend, in a second terminal:

```
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. In development the page calls the API at `localhost:8000`.
In a production build the page and the API come from the same server, so it works on any domain.

---

## Settings (.env)

All settings have safe defaults. Invalid numbers are ignored with a warning, and the default is used.
The full list with explanations is in `.env.example`.

| Setting | Default | What it does |
|---|---|---|
| `AI_API_KEY` | (empty) | Groq API key. Without it, every answer uses the backup writer |
| `AI_MODEL` | `openai/gpt-oss-20b` | The Groq model that writes answers |
| `AI_MAX_TOKENS` | `1600` | Room for the AI's hidden reasoning plus the answer. Too small gives empty answers |
| `AI_REASONING_EFFORT` | `low` | Keeps the reasoning model's thinking short |
| `TOP_K` | `8` | Most PDF pieces ever sent to the AI |
| `MIN_CONTEXT_PIECES` | `3` | Fewest pieces sent |
| `CONTEXT_MARGIN` | `0.25` | How close in score an extra piece must be to be sent |
| `MAX_CITATIONS` | `6` | Most sources listed under an answer |
| `DAILY_QUESTION_LIMIT` | `30` | AI answers per user per day |
| `USAGE_TIMEZONE` | `Asia/Kolkata` | When the daily limit resets (midnight here) |
| `DATABASE_URL` | (empty) | PostgreSQL address. Empty means a local SQLite file |
| `MAX_UPLOAD_MB` / `MAX_USER_STORAGE_MB` | `100` / `100` | Upload size limits |
| `ADMIN_KEY` | `medcite-admin` | Needed to delete a built-in medicine. Change it for a real deploy |
| `ALLOWED_ORIGINS` | local dev ports | Only needed when the page and API are on different addresses |

---

## Adding a medicine PDF

Uploads are open to everyone, but locked to one trusted source: **rxabbvie.com**.

1. Click **Upload PDF**.
2. Paste the official link, for example `https://www.rxabbvie.com/pdf/rinvoq_pi.pdf`.
3. Choose **that same file** from your computer. The file name must match the link.

Four checks run before a PDF is accepted:

| Check | Rejects |
|---|---|
| Host | Any site other than rxabbvie.com, including look-alikes such as `rxabbvie.com.evil.io` |
| Catalog | A link to a PDF that is not actually published on rxabbvie.com (280 PDFs are listed) |
| Name | A valid link paired with a different file |
| Content | A file that is not a medicine's prescribing information (for example a device manual) |

The catalog is a snapshot of the site's PDF list in `backend/sources/rxabbvie_catalog.json`.
Refresh it when AbbVie adds PDFs:

```
python3 -m backend.sources.rxabbvie --refresh
```

Uploaded PDFs are private to the user who added them. The 13 built-in PDFs in
`data/pdfs/shared/` are visible to everyone and cannot be deleted from the app.

---

## Tech used, and why

| Tool | What it does | Why this one |
|---|---|---|
| FastAPI | The backend. Takes the question, sends back the answer. | Our AI code is already Python, so the whole team works in one language. |
| React + Vite | The screen. Chat on one side, PDF on the other. | We need to click a page number and have the PDF open at that page. |
| react-pdf | Shows the real PDF pages and highlights the cited text. | The user can check every answer against the original document. |
| PyMuPDF | Reads the text out of the PDF and keeps the page number. | Most PDF readers lose the page number. Our whole project depends on it. |
| BM25 and TF-IDF (scikit-learn) | Two ways of searching. TF-IDF finds related wording, BM25 finds exact words. | Both run inside the app with no extra server, and every piece keeps its drug, section and page. |
| Groq (`openai/gpt-oss-20b`) | Writes the final answer from the text we found. | Very fast. The search already found the facts, so a small model is enough. |
| PostgreSQL / SQLite | Stores users, chats, saved answers, daily usage and a log of every answer. | PostgreSQL when configured; SQLite needs no setup, so a demo never breaks. |
| Docker | Runs everything. | Same setup on a laptop and on the AWS server. |
| AWS EC2 | Where the project is deployed. | One server runs it all. See Deployment below. |

We picked tools that are free, simple, and already known to the team.
Nothing here needs a graphics card.

---

## Database

The server forgets everything between requests, so anything that must be remembered is stored here.

| Table | What it stores | Used for |
|---|---|---|
| `users` | Browser token → short id like `user-104` | Keeping each person's uploads and chats separate, with no login |
| `answer_cache` | Saved answers | Instant, free answers to questions asked before |
| `daily_usage` | AI answers per user per day | The 30-questions-a-day limit |
| `chat_history` | Every question and answer | Each user's history, and review |
| `answers` | A log of every answer (pages, speed, refusals) | Monitoring and proving what the system said |

Two helper scripts read a PostgreSQL database named `medcite`:

```
bash db.sh                     # overview: questions per day, busiest medicines, users
bash db.sh day 2026-09-13      # everything asked on one day
bash db.sh search pregnant     # find a word in any question or answer
bash db.sh user user-104       # one person's history
bash watch-db.sh               # live view, refreshes every 10 seconds
```

---

## How many users it can handle

Measured on the real code with a temporary copy of the data and a stand-in for the AI that takes
1 second (like Groq), so no tokens were spent. A laptop was used; an AWS t3.medium will be a little slower.

**Asking questions at the same time (the server)**

| Users at once | All answered | Typical wait |
|---|---|---|
| 10 | 10 / 10 | 1.1 seconds |
| 40 | 40 / 40 | 1.2 seconds |
| 80 | 80 / 80 | 2.1 seconds |
| 80, a question asked before | 80 / 80 | **0.05 seconds** |

The server works on 40 requests at once and queues the rest. **The real limit is the Groq free plan**
(about 7 new AI answers a minute, see above), not the server.

**Uploading PDFs**

| Situation | Result |
|---|---|
| One upload | 0.2–0.3 seconds |
| 20 users upload at the same moment | All 20 succeed; the slowest waits about 8 seconds |

While PDFs are being processed, other users' requests wait too (up to about 6 seconds in the
20-upload test), because upload processing currently holds up the server. See Known weak spots.

**In short:** comfortable for a demo and for 10–20 normal users on the free AI plan;
with Groq's paid plan, the server itself can serve hundreds.

---

## Deployment (AWS)

The whole project runs on one AWS EC2 server, inside Docker, the same way it runs on a laptop.

```
                    User's browser
                          |
        +-----------------------------------+
        |        AWS EC2 - one server       |
        |                                   |
        |   Web page  ->  API (FastAPI)     |
        |                  |                |
        |                  +-> search index | BM25 + TF-IDF
        |                  +-> database     | users, chats, saved answers
        +-----------------------------------+
                          |
                 Groq AI API (outside AWS)
```

| AWS part | What it does | Why we need it |
|---|---|---|
| EC2 | The computer in the cloud. Everything runs here. | Online during the demo, so nobody needs our laptop. |
| EBS (the EC2 disk) | Holds the PDFs, the search index and the database. | These must survive a restart. |
| Security group | The firewall. Only the website port is open. | The database is never open to the internet. |

Full click-by-click console steps are in [docs/aws-deploy.md](docs/aws-deploy.md).

### Deploy steps

1. **Push the latest code to GitHub first.** The server gets its code from GitHub.
2. Create an EC2 server. In **Instance type**, pick **t3.medium** (4 GB memory).
   The first `docker compose up` builds the website on the server, and that can run out of memory on 2 GB.
3. Connect to the server and run:

```
git clone https://github.com/Boi-Talk13/Drug-Information-Q-A-Chatbot.git
cd Drug-Information-Q-A-Chatbot
cp .env.example .env
```

4. Put the real values in `.env` (at least `AI_API_KEY`), then:

```
docker compose up -d --build
```

The container uses a SQLite database stored in `data/index/` on the server's disk.
To use PostgreSQL instead, set `DATABASE_URL`.

### Cost

The habit that keeps it cheap: **stop the EC2 server when you finish work each night.**
A stopped server costs almost nothing.

### Three mistakes to avoid

1. Leaving the server running overnight. Stop it every night.
2. Not setting a billing alert. Set one at 10 dollars on day one.
3. Not deleting things after the demo. Delete the server, the disk and the public IP.
   AWS keeps charging for a disk even when the server is stopped.

### On demo day

Do not run the test sets that day. They use the same Groq daily budget as the live demo.

### One rule

The AWS server must work without our laptop. If we connect a laptop to make the demo work,
it is not a cloud deployment.

---

## Folder structure

```
backend/
  api/
    main.py            the web API: chat, upload, medicines, PDFs, usage, history
    db.py              the database: users, chats, saved answers, daily usage
  ai_answer/
    answer.py          one question: correct -> search -> pick pieces -> write -> verify pages
    llm.py             talks to Groq; the backup writer; token logging
    safety.py          greetings, advice questions, off-topic refusals, follow-ups
  search/
    hybrid.py          BM25 + TF-IDF search, section-aware ranking, off-topic check
    index.py           builds and updates the search index
    spellfix.py        typo and shorthand correction
    synonyms.py        everyday words -> label words
    bm25.py            the BM25 ranker
  pdf_reader/
    reader.py          reads PDF text and keeps page numbers
    chunker.py         cuts the text into section pieces
    validator.py       checks a PDF really is a medicine label
  sources/
    rxabbvie.py        upload source check (host, catalog, file name)
    rxabbvie_catalog.json   the 280 PDFs published on rxabbvie.com
  config.py            every setting, with safe defaults and validation
  build_index.py       builds the index from data/pdfs (run on server start)
  fetch_sample_pdfs.py downloads sample PDFs

frontend/
  src/components/      chat screen, PDF viewer, upload dialog, messages
  src/services/        talks to the backend API

data/
  pdfs/shared/         the 13 built-in medicine PDFs (committed)
  pdfs/<user-id>/      private uploads (never committed)
  index/               the search index and SQLite database (built at runtime, never committed)

docs/                  AWS deployment guide

tests/
  questions.json       main question set (32)
  holdout.json         held-out question set (26)
  tough.json           tough question set, all 13 PDFs (45)
  evaluate.py          scores accuracy: refusal F1 and citation F1
  build_answer_keys.py builds the answer keys from the PDFs (never from MedCite's answers)
  test_daily_limit.py  tests the daily limit and saved answers (no AI tokens used)
  results/             saved evaluation answers

db.sh                  browse and search the chat database
watch-db.sh            live view of the chat database
```

---

## How we test it

We do not train a model, so there is no built-in accuracy number. We measure the two
decisions MedCite actually makes, against questions where we already know the right answer.

- **Refusal:** does it refuse exactly the questions it should (off-topic ones), and never a real one?
- **Citation:** does the page it cites really contain the answer?

The right pages for every question (the answer key) are never written by hand and never taken from
MedCite's answers, so the test cannot mark its own homework. Each question says what it is about, and
`tests/build_answer_keys.py` finds the pages:

- a question about a **label section** ("what is the dose?") gets every page that section covers;
- a question about a **specific fact** ("can I crush K-TAB?") gets every PDF page whose real text states it.

Rebuild the keys after changing the PDFs or the text splitter:

```
python3 -m backend.build_index
python3 -m tests.build_answer_keys
```

### The three question sets

| Set | File | Questions | What it covers |
|---|---|---|---|
| Main | `tests/questions.json` | 32 | 5 medicines, one question per key section, plus off-topic questions |
| Held-out | `tests/holdout.json` | 26 | 5 **other** medicines. Written before any tuning and never used for it |
| Tough | `tests/tough.json` | 45 | **All 13 PDFs**, 3 questions each. Specific facts, everyday wording and real typos |

Run them:

```
python3 -m tests.evaluate
python3 -m tests.evaluate --file holdout.json
python3 -m tests.evaluate --file tough.json
python3 -m tests.evaluate --file tough.json --resume
```

Every answer is saved in `tests/results/` as soon as it arrives. If a run stops (for example the AI's
daily limit runs out), `--resume` continues from the first unanswered question. The script stops by itself
if the AI stops answering, so a backup-writer answer is never scored as the AI's.

Test the daily limit and saved answers (uses a temporary database and no AI tokens):

```
python3 -m tests.test_daily_limit
```

### Page-number accuracy

Every piece of every built-in PDF was checked against the real PDF page its text comes from.

| Text splitter | Page number correct |
|---|---|
| Earlier version | 73.5% (695 of 945 pieces) |
| **Current version** | **99.8% (948 of 950 pieces)** |

The earlier splitter guessed page numbers, and on some labels (the HUMIRA Medication Guide, FETZIMA,
AVYCAZ) it was often wrong. For example, it pointed to page 1 for HUMIRA storage instructions that are
really on page 5. The current splitter works out the page from the exact position of the text.

### Search check (current version, no AI)

Does the right page reach the AI at all? Measured on 14 September 2026 with the current splitter and
the rebuilt answer keys. This needs no AI tokens.

| Set | Right page sent to the AI | Right page ranked first |
|---|---|---|
| Main | **25 / 25 (100%)** | 22 / 25 (88.0%) |
| Held-out | **21 / 21 (100%)** | 19 / 21 (90.5%) |
| Tough | **35 / 39 (89.7%)** | 28 / 39 (71.8%) |
| All | **81 / 85 (95.3%)** | 69 / 85 (81.2%) |

Still missed: UBRELVY "2nd dose" and "most in 24 hours", FETZIMA "trouble peeing", BLEPHAMIDE "contact lenses".

### Accuracy results (with the AI)

**These numbers were measured with the earlier splitter**, on 13 September 2026, with the
`openai/gpt-oss-20b` model on Groq and a fixed 8 search pieces. Part of each test's answer key was taken
from that splitter's page numbers, which were wrong about 1 time in 4, so the numbers below are **not a
reliable measure of the current version**. They will be re-measured with answer keys built from the real
PDF pages.

| Set | Passed | Refusal precision | Refusal recall | Refusal F1 | Refusal accuracy | Citation precision | Citation recall | Citation F1 |
|---|---|---|---|---|---|---|---|---|
| Main | **32 / 32** | 1.000 | 1.000 | **1.000** | 1.000 | 0.871 | 1.000 | **0.931** |
| Held-out | **22 / 26** | 1.000 | 0.800 | **0.889** | 0.962 | 0.833 | 0.857 | **0.845** |
| Main + held-out | **54 / 58** | 1.000 | 0.917 | **0.957** | 0.983 | 0.855 | 0.935 | **0.893** |
| Tough | pending | 1.000 | 0.833 | **0.909** | 0.978 | pending | pending | pending |

What the words mean:

- **Refusal precision 1.000** means it never refused a real medicine question.
- **Citation recall** is the share of answers that cited a page inside the right section.
- **Citation precision** is the share of cited pages that were inside the right section.

**Strict scoring.** If every page of a multi-page section must be cited, not just one, citation
F1 is lower: 0.761 on main and 0.678 on held-out. We report both, so nothing is hidden.

**Tough set.** The refusal numbers are real (refusals do not use the AI). The citation numbers are
pending because the Groq daily limit ran out during the run; the tough set will be re-run with
`--resume` when the limit refills.

**Automatic test:** `tests/test_daily_limit.py` — 21 of 21 checks pass, including 6 questions sent at the
same moment stopping at exactly the limit.

---

## Safety

This is a document lookup tool. It is not a doctor.

It tells you what the medicine label says and where it says it.
It never tells a person what to take.

Rules we built in:

- If the search finds nothing, we stop. The AI is never asked to guess.
- Every page number the AI gives must point to text we actually sent it. We check this ourselves.
- Advice questions get the label text plus a note to ask a doctor. Never a yes or no.
- A question about one medicine is never answered using another medicine's PDF.
- If someone hides an instruction inside a PDF, we ignore it. PDF text is data, not orders.
- Uploads are accepted only from rxabbvie.com, and only if the file really is a medicine label.
- One user can never see another user's uploaded PDFs or chats.
- No secrets are stored in the code. The API key lives only in `.env`, which is never committed.

---

## Known weak spots

We keep this list honest instead of editing the tests until everything passes.

- A question whose words happen to appear in the labels can slip past the off-topic check.
  "Who is the prime minister of India?" and "What is 25 times 17?" were answered instead of refused.
- The patient counseling section (17) or page 1 Highlights still sometimes wins over the detailed
  section. ELAHERE eye warnings are an example.
- On very short labels (K-TAB), the summary page and the full section sit so close together that
  the wrong one is sometimes cited.
- Answers that live inside dosage tables (for example AVYCAZ dosing for kidney problems) and some
  everyday wording ("trouble peeing" for urinary retention) can miss the right page.
- While a PDF is being uploaded, other users' requests wait (a few seconds when many upload at once).
- On the free Groq plan, heavy use falls back to the less clear backup answers.

We report the refusal score as proudly as the accuracy score.
A bot that answers everything is exactly the problem this use case is about.

---

## Team

Eight members. Three on the front end, four on the back end, one lead across both.

| Part | Who | Job | Critical |
|---|---|---|---|
| Front end | Team member 1 | Chat screen, answer area, page number tags | Normal |
| Front end | Team member 2 | PDF viewer, click a page number to open that page | Normal |
| Front end | Team member 3 | Upload button, medicine list, refusal messages | Normal |
| Back end | Team member 4 | Reads PDFs, keeps page numbers, cuts by section | CRITICAL |
| Back end | Team member 5 | Builds the search, mixes the two search types, tunes it | CRITICAL |
| Back end | Team member 6 | AI instructions, follow up questions, refusals, page number checks | CRITICAL |
| Back end | Team member 7 | API, database, AWS deployment, monitoring, cost | Normal |
| Lead | Team member 8 | Joins both sides, writes and scores the test question sets, demo | Normal |

Team members 4, 5 and 6 are the spine. Read the PDF, then search it, then write
the answer. If any one of those is missing there is no demo at all.

---

## What we did not build

- Telling a person what dose to take
- Diagnosing anyone
- Real patient data
- Hospital system integration
- Training our own AI model

---

## Data source

Free public medicine PDFs from AbbVie's U.S. Prescribing Information site: https://www.rxabbvie.com/
Example from the official brief: https://www.rxabbvie.com/pdf/rinvoq_pi.pdf
