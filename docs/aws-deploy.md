# Deploying to AWS

Owner: team member 7.

Everything here is done in the AWS Console website, by clicking. No command line
tools to install on your laptop.

We deploy on **Day 5**, not Day 7. The first deploy always finds two or three
problems nobody expected. You want to find them with two days spare, not two hours.

---

## What we are deploying

One small server that runs everything.

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
```

Not many servers. Not Lambda. One machine, everything in Docker, the same way it
runs on a laptop.

---

## Before anything: set a billing alarm

Console -> search **Billing** -> Budgets -> Create budget -> Cost budget

- Amount: **10 USD**
- Email: yours

Do this first, before creating anything. It takes five minutes and it is the only
thing standing between the team and a surprise bill.

---

## Step 1. Create the S3 bucket for the PDFs

Console -> **S3** -> Create bucket

- Name: `drugqa-pdfs-<something-unique>`
- Region: pick the closest one, and **use the same region for everything after this**
- Block all public access: leave it **ticked ON**
- Create

Then upload the medicine PDFs into the bucket.

---

## Step 2. Create an IAM role so the server can read S3

Console -> **IAM** -> Roles -> Create role

- Trusted entity type: **AWS service**
- Use case: **EC2**
- Permissions: search for and tick `AmazonS3ReadOnlyAccess`
- Name: `drugqa-ec2-role`
- Create role

This is how the server reads S3 with **no AWS password anywhere in our code**.

---

## Step 3. Launch the EC2 server

Console -> **EC2** -> Instances -> Launch instance

| Field | What to choose |
|---|---|
| Name | `drugqa-server` |
| OS image | Ubuntu Server 24.04 LTS |
| Instance type | `t3.small` if you build the frontend on your laptop, `t3.medium` if you build it on the server |
| Key pair | Create a new one, download the .pem file, keep it safe |
| Storage | **20 GB** (not the default 8 GB) |

Under **Network settings -> Edit**, allow:

| Port | Source | Why |
|---|---|---|
| 22 (SSH) | **My IP** only | So only we can log in |
| 80 (HTTP) | Anywhere | So judges can open the site |
| 443 (HTTPS) | Anywhere | For later, if we add HTTPS |

**Do not open port 5432.** That is the database. It stays closed to the internet.

Under **Advanced details -> IAM instance profile**, choose `drugqa-ec2-role`.

Launch instance.

---

## Step 4. Connect to the server

Select the instance -> **Connect** button -> **EC2 Instance Connect** tab -> Connect.

This opens a terminal inside your browser. No .pem file needed, no PuTTY, nothing
to install. This is the easiest way.

---

## Step 5. Install Docker

Paste this into that browser terminal:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
```

Close the terminal and Connect again. This step is needed for the group change to
take effect. If you skip it, every docker command says "permission denied".

---

## Step 6. Get the project and run it

```bash
git clone https://github.com/Boi-Talk13/Drug-Information-Q-A-Chatbot.git
cd Drug-Information-Q-A-Chatbot
cp .env.example .env
nano .env
```

Put the real values in. Save with `Ctrl+O`, then Enter, then `Ctrl+X`.

```bash
docker compose up -d
```

Check it is running:

```bash
docker compose ps
docker compose logs -f
```

---

## Step 7. Open it

On the instance page, copy the **Public IPv4 address** and open it in a browser.

That is the live demo link.

---

## Keep the link from changing

**When you stop the server, the public IP changes.** Start it again the next day
and the old link is dead. If a mentor has that link, it stops working.

Fix: EC2 -> **Elastic IPs** -> Allocate Elastic IP address -> Associate it with
the instance. Now the address never changes.

Note: an Elastic IP costs a small amount per hour while the instance is stopped.
It is a few rupees a day. Worth it for a link that stays alive. Release it on Day 7.

---

## Every night

Instances -> select ours -> **Instance state -> Stop**

**Stop, not Terminate.** Stop keeps everything and costs almost nothing.
Terminate deletes the machine.

A server left running all week costs around four times more than one stopped
every night, for no benefit.

---

## Day 7, after the demo

Do these in order:

1. EC2 -> Instance state -> **Terminate**
2. EC2 -> **Volumes** -> delete any volume left behind
3. EC2 -> **Elastic IPs** -> **Release**
4. S3 -> empty the bucket -> delete the bucket
5. Check Billing the next day and confirm it is going to zero

Step 2 is the one people forget. A volume keeps charging after the instance is gone.

---

## Five things that break between laptop and cloud

Fix these while building locally. Do not leave them for deploy day.

| Problem | Why it happens | Fix |
|---|---|---|
| Server runs out of memory | `t3.small` has 2 GB. Building React on it will crash. | Build the React files on your laptop and commit the built files, or use `t3.medium`. |
| Frontend cannot reach the backend | The frontend calls `localhost:8000`. On AWS, localhost means the visitor's own computer, so nothing is found. | Never hardcode the URL. See the fix below. |
| CORS errors in the browser | Frontend and backend on different ports. | Same fix as below. |
| Docker image will not run | A Mac builds ARM images. EC2 is usually Intel. | Never copy images from a laptop. On the server, `git clone` and let it build there. |
| Repo becomes huge and slow | The PDFs and the search index were committed. | PDFs live in S3. Build the Chroma index on the server once. |

### The fix that removes two of these at once

Build React into plain files, and let **FastAPI serve those files itself**.

Then there is one server, one port, one URL. The frontend calls `/api/ask` with no
domain in front of it. No CORS. No API URL setting to change between laptop and AWS.

Decide this on Day 1. It is less work than the alternative, not more.

---

## Notes

- The demo link will be `http://<ip>` with no padlock. That is fine for a demo.
  If a judge asks, HTTPS is a small job with Caddy, but do not spend time on it
  before Day 6.
- The AWS server must work **without anyone's laptop**. If we connect a laptop to
  make the demo work, it is not a cloud deployment, and a judge will notice.

---

## Checklist

- [ ] Billing budget set at 10 USD
- [ ] S3 bucket created, PDFs uploaded
- [ ] IAM role created and attached to the instance
- [ ] EC2 launched, 20 GB disk, correct ports open, 5432 closed
- [ ] Docker installed, project running
- [ ] Public IP opens the working site
- [ ] Elastic IP attached so the link stays the same
- [ ] Whole team has the link
- [ ] Someone tests the link on their phone, on mobile data, with every laptop closed
- [ ] Server stopped at the end of each day
- [ ] Day 7 teardown done and billing checked
