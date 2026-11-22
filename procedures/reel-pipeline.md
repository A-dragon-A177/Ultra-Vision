---
name: reel-pipeline
description: "Create and post an Instagram Reel: script → audio → video → Instagram"
owner: friday
---

## Step 1: Research trending topic @friday

Search for the most engaging AI topic right now. Use TOOL_CALL: reddit.trending() to see what's hot on AI subreddits.
Pick the best topic and explain in 2 sentences why it'll perform well on Instagram.

## Step 2: Write reel script @friday

Write a punchy 60–90 second narration script for an Instagram Reel about the trending topic.
Format: Hook (5 sec) → 3 key insights (45 sec) → CTA (10 sec).
Keep sentences short. Each sentence becomes one spoken line. End with "Follow Neesh AI for more."
Output ONLY the narration script text — no scene directions or headers.

## Step 3: Create video @friday

Take the script from Step 2 and create the video using:
TOOL_CALL: video.create_reel(script=<script from step 2>, title=<topic title>, style="branded")

If status is "error" and mentions ffmpeg, tell the founder: download ffmpeg from https://ffmpeg.org/download.html and add to PATH.
Otherwise report the video_path and size_mb.

## Step 4: Write Instagram caption @friday

Write a compelling Instagram Reel caption with:
- Hook line (no hashtags, plain text)
- 3–5 bullet insights
- CTA: "Follow @neeshai for daily AI updates"
- 15–20 relevant hashtags on the last line

## Step 5: Post to Instagram @friday [approval]

Review the caption from Step 4, then post the reel:
TOOL_CALL: video.upload_instagram(video_path=<path from step 3>, caption=<caption from step 4>)

Report the result. If status is "manual", the video is ready at the given path — open Instagram to upload.
If status is "published", share the post URL with the founder.
