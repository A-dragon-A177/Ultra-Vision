---
name: reddit-growth
description: "Reddit promotional growth plan for Neesh AI — find opportunities and engage authentically"
owner: friday
---

## Step 1: Find engagement opportunities @friday

Scan Reddit for posts where Neesh AI can add genuine value:
TOOL_CALL: reddit.opportunities()

Analyze the results. Pick the top 3 opportunities where a helpful comment about AI tools or Neesh AI would be genuinely relevant and welcome (NOT spammy).
For each one explain: the post topic, why we can add value, and the angle for our comment.

## Step 2: Draft authentic comments @friday

For each opportunity from Step 1, write a helpful Reddit comment that:
- Actually answers or adds value to the post
- Naturally mentions Neesh AI or links to it ONLY if genuinely relevant
- Sounds like a real person, not a marketing bot
- Is 3–6 sentences max
- Never starts with "As an AI" or sounds promotional

Present all 3 comments for approval.

## Step 3: Post comments @friday [approval]

Post the approved comments. For each approved comment:
TOOL_CALL: reddit.comment(post_url=<url>, comment=<text>)

Report each result. Wait 2–5 minutes between comments to avoid Reddit's rate limits.

## Step 4: Weekly growth post @friday

Write a value-add post for r/AIAssistants or r/artificial:
- Share a genuine insight, tutorial, or comparison about AI tools
- Mention Neesh AI casually if appropriate
- Include 1–2 bullet points with actionable takeaways

Then post it:
TOOL_CALL: reddit.post(subreddit="AIAssistants", title=<title>, content=<body>)

Report the post URL.
