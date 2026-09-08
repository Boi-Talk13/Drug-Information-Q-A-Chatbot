# Drug Information Q&A Chatbot with Citations

A chatbot that answers questions about medicines using only official medicine PDFs.
Every answer shows the page it came from. If the PDF does not say it, the bot says it does not know.

Built for the Cognizant and GITAM student buildathon. Shortlisted use case number 7.
Type: GenAI / RAG / Responsible AI.

---



## The problem

Doctors, patients and family members need correct medicine information fast.

A normal chatbot can invent a dose. For medicine, a wrong answer is dangerous.

So we built a bot that cannot answer without proof from the document.

---

## How it works

Four steps.

1. We read the PDF and keep the page number of every line.
2. We cut it into small pieces at the section headings, such as Dose, Warnings and Side Effects.
3. When someone asks a question, we search those pieces and pick the best five.
4. Only those five go to the AI. The AI writes the answer and marks the page.

The search decides what is true. The AI only puts it into good English.
So the AI cannot invent anything.

### Important

We do not train any model. Nothing is memorised.

The bot looks the answer up in the PDF every single time, like an open book.
This is why a new PDF works straight away, with no retraining.

The AI never reads all 90 pages of a PDF. The search picks 5 small pieces,
so the AI reads about half a page. That is why it is fast and cheap.

---

## What makes it different

Most chatbots try to answer everything.

This one refuses when the document does not have the answer, and it shows you
the page for everything it does answer. You can click the page number and check
it yourself.

---

## How to run it

```
git clone https://github.com/Boi-Talk13/Drug-Information-Q-A-Chatbot.git
cd Drug-Information-Q-A-Chatbot
cp .env.example .env
```

Open `.env` and put your real API key in it.

```
docker compose up
```

Then open http://localhost:8000 in your browser.

---

## Tech used, and why

| Tool | What it does | Why this one |
|---|---|---|
| FastAPI | The backend. Takes the question, sends back the answer. | Our AI code is already Python, so the whole team works in one language. |
| React | The screen. Chat on one side, PDF on the other. | We need to click a page number and have the PDF open at that page. Simpler tools reload the whole screen and cannot do this. |
| PyMuPDF | Reads the text out of the PDF and keeps the page number. | Most PDF readers lose the page number. This one keeps it, and our whole project depends on page numbers. |
| Chroma and BM25 | Two ways of searching. Chroma finds meaning, BM25 finds exact words. | Chroma stores the drug, section and page number together with the text, so the page number comes back with every search result. BM25 is added because drug names need exact matching. |
| An AI model API | Writes the final answer from the text we found. | The search already found the facts, so the AI only has to write. A small cheap model does that well. |
| PostgreSQL | Stores the chats and a record of every answer. | Free, safe, and the whole team has used it. The monitoring dashboard reads from it. |
| Docker | Runs everything. | Same setup on a laptop and on the AWS server, so nothing new breaks on demo day. |
| AWS | Where the project is deployed. | One small EC2 server runs it all. See the Deployment section below. |

We picked tools that are free, simple, and already known to the team.
Nothing here needs a big graphics card or a new account.

---

## Deployment (AWS)

The whole project runs on one small AWS EC2 server. Everything is inside Docker,
the same way it runs on a laptop.

```
                    User's browser
                          |
        +-----------------------------------+
        |     AWS EC2 - one small server     |
        |                                    |
        |   Web screen  ->  API              |
        |                    |               |
        |                    +-> Chroma      |  search
        |                    +-> PostgreSQL  |  chats and records
        +-----------------------------------+
             |                        |
        AWS S3                  AWS CloudWatch
    the PDF files             logs and numbers
                                      |
                             AI model API (outside AWS)
```

| AWS part | What it does | Why we need it |
|---|---|---|
| EC2 | One small computer in the cloud. Everything runs here. | This is the machine that is online during the demo, so nobody needs our laptop. |
| S3 | Stores the medicine PDF files. | PDFs are big. Keeping them here keeps the server disk small and the files safe if the server is deleted. |
| EBS (the EC2 disk) | Holds the Chroma index and the PostgreSQL data. | These must survive a restart. |
| CloudWatch | Collects the logs and the numbers. | This is where the monitoring lives. |
| IAM role | Lets the server read from S3. | So no AWS password ever goes inside our code. |
| Security group | The firewall. Only the website port is open. | The database is never open to the internet. |

Full click-by-click console steps are in [docs/aws-deploy.md](docs/aws-deploy.md).

### Deploy steps

```
ssh into the EC2 server
git clone https://github.com/Boi-Talk13/Drug-Information-Q-A-Chatbot.git
cd Drug-Information-Q-A-Chatbot
cp .env.example .env
```

Put the real values in `.env`, then:

```
docker compose up -d
```

### Cost

About 3 to 8 dollars for the whole week. S3 and CloudWatch stay inside the AWS
free tier at our size.

The habit that keeps it cheap: **stop the EC2 server when you finish work each
night.** A stopped server costs almost nothing. Left running all week it costs
around four times more, for no reason.

### Three mistakes to avoid

1. Leaving the server running overnight. Stop it every night.
2. Not setting a billing alert. Set one at 10 dollars on day one, before anything else.
3. Not deleting things after the demo. Delete the server, the disk, the public IP
   and the S3 files. AWS keeps charging for a disk even when the server is stopped.

### One rule

The AWS server must work without our laptop. If we connect a laptop to make the
demo work, it is not a cloud deployment.

---

## Folder structure

```
backend/
  api/           the web API
  pdf_reader/    reads PDFs, keeps page numbers, cuts into pieces
  search/        builds the Chroma index and searches it
  ai_answer/     talks to the AI, checks the page numbers are real

frontend/
  src/           the chat screen and the PDF viewer

data/
  pdfs/          the medicine PDFs we load (kept in AWS S3 when deployed)
  index/         the Chroma search index (built from the PDFs, not committed)

docs/            architecture diagram, screenshots, demo video link

tests/           the 60 test questions and the scoring script
```

---



## How we test it

We wrote about 60 questions before we started tuning anything, and we did not
change them afterwards. They are in `tests/questions.json`.

| Type of question | What a good result looks like |
|---|---|
| Normal question | Right answer, and the page number is the real page |
| Short follow up | "And for children?" still finds the right drug and section |
| Question the PDF cannot answer | It refuses instead of making something up |
| Advice question | Gives the label text and points to a doctor |

We report the refusal score as proudly as the accuracy score.
A bot that answers everything is exactly the problem this use case is about.

---

## Safety

This is a document lookup tool. It is not a doctor.

It tells you what the medicine label says and where it says it.
It never tells a person what to take.

Rules we built in:

- If the search finds nothing, we stop. The AI is never asked to guess.
- Every page number the AI gives must point to text we actually found. We check this ourselves.
- Advice questions get the label text plus a note to ask a doctor. Never a yes or no.
- A question about one medicine is never answered using another medicine's PDF.
- If someone hides an instruction inside a PDF, we ignore it. PDF text is data, not orders.

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
| Lead | Team member 8 | Joins both sides, writes and scores the 60 tests, demo | Normal |

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

Free public medicine PDFs. Example from the official brief:
https://www.rxabbvie.com/pdf/rinvoq_pi.pdf
