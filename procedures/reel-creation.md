---
name: reel-creation
description: "Full end-to-end pipeline for creating, auditing, and posting a Neesh AI Instagram Reel — from audit analysis to WhatsApp approval and Instagram posting"
owner: friday
goal: "Increase Neesh AI Instagram followers and WhatsApp community members (Explorers + Founders groups)"
---

# Reel Creation Pipeline

**Trigger:** When Abhishek says "create a reel", "next reel", "make a reel about [topic]", or names a topic from the Content Engine / Graveyard Engine.

**Primary goal:** Every reel must grow Instagram followers AND drive WhatsApp community joins (Explorers + Founders groups).

**Two external chats used in this pipeline:**
- **IG Audit + Edit chat:** https://claude.ai/share/dbb8606c-d4cb-4034-90be-0103cb2dd9f5
- **Script generation chat:** Claude Code → "AI video editor" folder (open it there)

---

## Step 1: Instagram Performance Audit @friday

Open the IG Audit chat: https://claude.ai/share/dbb8606c-d4cb-4034-90be-0103cb2dd9f5

Run the audit skill on the Neesh AI account:
```
/ig-audit @neeshai
```

Analyze:
- Why previous reels failed to reach 10M views
- Hook retention (did frame 1 stop the scroll?)
- Watch time curve (where did people drop off?)
- CTA effectiveness (did they follow / join WhatsApp?)
- Format issues (pacing, text card speed, music)
- Content pillar alignment (P1/P2/P3/P4 from Content Engine)

Summarize the top 5 failure reasons with specific, actionable fixes.

---

## Step 2: Script Generation @friday

Open the **Script generation chat** in Claude Code → AI video editor folder.

Send the full audit analysis from Step 1 and say:

> "Here is the latest ig-audit analysis: [paste analysis]
> 
> Based on these drawbacks, write a perfect word-by-word script for a reel about: [TOPIC]
> 
> Content Engine guidelines:
> - 20–35 seconds total
> - Speech starts at 0.0 seconds
> - Frame 1: a real number, headline or screenshot (no slow build)
> - Hook names a job, industry, brand or ₹ figure
> - One idea per reel, one CTA matched to the pillar
> - Each text card readable in 2.5 seconds
> - Every number has its source on screen
> - Fix all issues found in the audit
> - Goal: stop the scroll in 1 second, drive follows + WhatsApp joins
> 
> Give me the COMPLETE word-by-word script — every single word spoken, in order."

**TOPIC selection:** Use the topic Abhishek gave, OR pick from:
- Content Engine P1: AI × Jobs India (Mon/Wed)
- Content Engine P2: Idea Verdict (Wed)
- Content Engine P3: Startup Autopsy — Graveyard Engine story bank (Fri)
- Content Engine P4: Build Log / Neesh behind the scenes (Sun)

Save the final word-by-word script to: `C:\Vision\brain\outputs\reel-script-latest.txt`

---

## Step 3: NotebookLM Video Generation @friday

Open NotebookLM: https://notebooklm.google.com (session already saved)

1. Click **"New Notebook"**
2. Add source → **"Paste text"** → paste the full word-by-word script → click **Insert**
3. In the notes area, save a note titled "Word-by-Word Script" containing the full script
4. Go to **Studio** (right side panel)
5. Click **"Video overview"**
6. Choose **"Short"**
7. Select **"Customized topic"** and enter EXACTLY this prompt:

```
Create a futuristic visually appealing short video exactly using the same script word by word - 1. Give different futuristic tech graphic style for ALL frames 2. use slight dark navy/teal background throughout the video as the background colour Create the short form video with exactly same words in the script - word by word - Nothing more than that
```

8. Paste the word-by-word script into the script box
9. Click **"Generate now"**
10. Wait for NotebookLM to finish generating (may take 5–15 minutes)
11. Click **Download** once generated
12. The video will be in `C:\Users\Abhishek\Downloads\` — note the filename

---

## Step 4: Video Editing @friday

Open the IG Audit + Edit chat: https://claude.ai/share/dbb8606c-d4cb-4034-90be-0103cb2dd9f5

Send both:
1. The word-by-word script (from `C:\Vision\brain\outputs\reel-script-latest.txt`)
2. The downloaded video file (from Downloads)

Say:
> "Here is the word-by-word script and the NotebookLM-generated video. Please edit this video to match the script exactly, optimizing for Instagram Reels virality. Apply all the fixes from the audit analysis."

Wait for the edited video to be ready. Download it and save to:
`C:\Vision\data\videos\reel-edited-latest.mp4`

---

## Step 4.1: Quality Audit Loop @friday

Send the edited video to the IG Audit + Edit chat and request:
```
/ig-audit [video file]
Score this reel out of 100.
```

**If score >= 70:** Proceed to Step 5.

**If score < 70:** 
- Extract the specific list of changes needed from the audit
- Go back to the **Script generation chat** in Claude Code
- Send: "The reel scored [X]/100. Here are the required changes: [list]. Please revise the word-by-word script to fix these."
- Get revised script → redo Step 3 (NotebookLM) → redo Step 4 (editing) → audit again
- **Repeat until score >= 70**

---

## Step 5: WhatsApp Notification @friday [approval]

Send the final edited video to Abhishek via WhatsApp Web:
TOOL_CALL: browser.whatsapp(community_name="8072710854", message="🎬 Reel is ready! Score: [X]/100\n\nVideo is attached. Reply 'POST' to approve and I'll post it to Instagram, or give me feedback to revise.")

Then attempt a call to 8072710854 to notify Abhishek the reel is ready.
TOOL_CALL: computer.run(cmd="start ms-phone://call?PhoneNumber=8072710854")

If call fails, the WhatsApp message is sufficient — Abhishek will see it.

**Wait for Abhishek's reply** before proceeding.

---

## Step 6: Await Approval @friday

Monitor the WhatsApp reply from 8072710854.

- If reply is **"POST"** or any approval → proceed to Step 7
- If reply contains feedback → go back to Step 2 (Script generation) with the feedback and loop
- If no reply after 2 hours → send a follow-up WhatsApp reminder

---

## Step 7: Get Caption @friday

Go to the **Script generation chat** in Claude Code → AI video editor folder.

Run:
```
/ig-caption
```

Provide the final script and ask for a caption optimized for:
- Saving the post (saves boost reach)
- Driving comments (comment your job title / comment VALIDATE)
- WhatsApp community joins (Explorers + Founders group link in bio)
- Relevant hashtags (#startupindia #indianstartups #founders #neeshai etc.)

Save the caption to: `C:\Vision\brain\outputs\reel-caption-latest.txt`

---

## Step 8: Post to Instagram @friday [approval]

Post the final video with the caption from Step 7:
TOOL_CALL: video.upload_instagram(video_path="C:\Vision\data\videos\reel-edited-latest.mp4", caption=<caption from step 7>)

After posting, confirm with Abhishek via WhatsApp:
TOOL_CALL: browser.whatsapp(community_name="8072710854", message="✅ Reel posted to Instagram!\n\nCaption included call-to-action to join WhatsApp community (Explorers + Founders). Monitor comments for engagement in the first hour — reply to every comment mentioning a job title.")

---

## Content Pillars Quick Reference

| Pillar | Day | Topic | CTA |
|--------|-----|-------|-----|
| P1 · AI × Jobs | Mon | AI stat + job industry + startup problem | "Comment your job title" |
| P2 · Idea Verdict | Wed | Rate audience startup ideas | "Drop your idea in one line" |
| P3 · Startup Autopsy | Fri | Indian startup failure story | "Save this before you build" |
| P4 · Build Log | Sun | Neesh behind the scenes | "Comment SPRINT" / WhatsApp join |

## Graveyard Engine Topics (ready to use)

Priority order for Startup Autopsy reels:
1. **Koo** — $60M, no market need, India's Twitter shut down 2024
2. **Hike Messenger** — $261M, lost to WhatsApp's network effect
3. **WhiteHat Jr** — $300M, unit economics never worked
4. **ZestMoney** — $150M, BNPL unit economics
5. **GoMechanic** — $100M, legal/regulatory collapse
6. **PepperTap** — $51M, too early for quick commerce
7. **TinyOwl** — $27M, ran out of cash in 2015 boom

## WhatsApp Community CTAs

Always end reels or captions with one of:
- "Join our Founders group → link in bio (for builders testing ideas)"
- "Join Explorers community → link in bio (for job professionals discovering startup ideas)"
- "Comment your industry and I'll DM you the validation checklist"
