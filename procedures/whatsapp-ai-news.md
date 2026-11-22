---
name: whatsapp-ai-news
description: "Find trending AI news and post to WhatsApp community"
owner: friday
---

## Step 1: Find trending AI news @friday

Use TOOL_CALL: reddit.trending(subreddits=["artificial", "MachineLearning", "singularity"], limit=10)
Pick the top 3 most interesting posts. For each one summarize in 2 lines what the news is and why it matters.

## Step 2: Write WhatsApp post @friday

Write a WhatsApp community post with the top 3 AI stories. Format:
```
🤖 *AI News Today* — [date]

1️⃣ *[Title]* 
[2-line summary + link]

2️⃣ *[Title]*
[2-line summary + link]

3️⃣ *[Title]*
[2-line summary + link]

Follow us for daily AI updates!
— Neesh AI Team
```
Keep it conversational, mobile-friendly, with emoji.

## Step 3: Post to WhatsApp @friday [approval]

Post the message to the AI community:
TOOL_CALL: browser.whatsapp(community_name="Neesh AI", message=<post from step 2>)

If not_found: tell the founder the community name wasn't matched — check brain/wiki/about-me.md for the exact group name.
If needs_qr: tell the founder to run `python C:\Vision\save_session.py whatsapp` and scan the QR code.
Otherwise report: sent successfully to <group>, <chars> characters.
