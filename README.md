# Vision

Your private AI team, run from Telegram. Vision is the chief of staff; the others each own one part of the
startup. Only your Telegram account can talk to it.

## The team

| Name | Role |
|---|---|
| Vision | Chief of Staff and your personal assistant. Talk to Vision by default. |
| Jarvis | Executive assistant: emails, messages, meetings, follow-ups |
| Friday | Marketing and content: reels, posts, captions, content calendar |
| Ultron | Product and engineering: specs, code, bugs, build plans |
| Jocasta | Research and strategy: reports, competitors, summarising your notes |
| Edith | Operations: repetitive work, turning tasks into procedures |
| Veronica | Sales and customers: outreach, pitches, support replies |
| Zola | Finance and data: budgets, pricing maths, metrics |
| Jim | Quality reviewer: checks work before it goes out |
| Herbie | Quick jobs: translation (English, Tamil, Hindi), rewriting, formatting |

## Setup

First get two keys:
- **Telegram bot token:** in Telegram, message @BotFather, send `/newbot`, follow the prompts.
- **Gemini key:** free at https://aistudio.google.com/apikey

Then pick where Vision lives.

### Option A: your laptop (simplest, works only while the laptop is on and awake)

**Windows:** install Python from python.org (tick "Add Python to PATH"). Double-click `run-windows.bat`.
Notepad opens `.env`: paste the token and the key, save, close, and double-click `run-windows.bat` again.
To start Vision automatically: press Win+R, type `shell:startup`, and put a shortcut to `run-windows.bat`
in that folder. In Power settings, set "When plugged in, put my device to sleep" to Never.

**Mac:** in Terminal, `cd` into this folder and run `bash run-mac-linux.sh`. Fill in `.env`, run it again.

### Option B: Google Cloud's free e2-micro VM (always on)

1. Create the VM in us-central1, us-west1 or us-east1, machine type e2-micro, Ubuntu, standard persistent
   disk (30 GB or less), no static IP. Any other region or size costs money.
2. Click **SSH** next to the VM to open a terminal in your browser. Use the **Upload file** button to upload
   `vision.zip`, then run: `sudo apt-get install -y unzip && unzip vision.zip && cd vision && bash install.sh`
3. Run `nano .env`, paste the token and the key, save (Ctrl+O, Enter, Ctrl+X), run `bash install.sh` again.

### Both options: lock it to you

Send `/whoami` to your bot, put the number in `.env` as `OWNER_ID`, then restart Vision
(laptop: close and reopen it; VM: `sudo docker compose restart vision`). Fill in `company.md` and restart once more.

Only one copy of Vision can run per bot at a time. No ports need opening anywhere: Vision calls out to
Telegram, nothing calls in.

## Using it

- Type or send a voice note: "Plan my day", "Create the next reel".
- Name someone to go straight to them: "Friday, three post ideas for this week".
- `/team`, `/procedures`, `/run create-next-reel`, `/remember <fact>`, `/facts`, `/forget <n>`, `/skip`

## When an agent needs you

If an agent gets stuck in the middle of a procedure, the work pauses and you get "Jocasta needs you ▸
<question>". Your next message is taken as the answer and the work carries on. Unanswered questions are
repeated every 10 minutes, three times. To make your phone ring as well, fill in `CALLMEBOT_USER` in `.env`
(steps are in that file). Only the sentence "Vision needs your decision" goes to that service.

## Web research

Jocasta searches the live web through Gemini's Google Search grounding. `/run trend-blog` researches the
week's AI and startup news, writes a blog post, has Jim check it, and gives you a short message ready to
forward to your WhatsApp community.

## Changing it

- **New team member:** add a file in `agents/` (copy an existing one). The file name is the name you call.
- **New procedure:** add a file in `procedures/`. Each `## Step title @agent` is one step; add `[approval]`
  to a heading and Vision waits for your Approve button after that step. Or ask Edith to write one.
- **Schedules:** edit `schedules.yaml`.
- After any change: `sudo docker compose restart vision`

## Backups and the pen drive

`bash backup.sh` packs everything into `backups/`. It also runs nightly at 02:30. Copy the newest file to an
encrypted pen drive. To bring Vision up on another machine: unpack it, run `bash install.sh`.
Stop the copy on the VM first (`sudo docker compose down`), because two copies cannot share one bot.

## What this version does not do yet

It thinks, writes, plans, reviews and runs multi-step procedures. It does not yet act in your accounts:
no sending email, posting to Instagram or WhatsApp, video generation or running code. Those are added as tools, one
at a time, each behind your approval.

## Privacy note

On Gemini's free tier, Google may use what you send to improve its products. Do not send passwords, bank
details or customer personal data through Vision while it runs on the free tier.
