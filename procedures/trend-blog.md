---
name: trend-blog
description: Research current AI and startup trends, write a blog post, and post the summary to WhatsApp community
owner: jocasta
---

## Research this week's trends @jocasta
Search the web for the most important developments of the last 7 days in AI, startups, and anything
relevant to the niche in the company profile (India-focused where relevant).
Pick the 5 that matter most to the audience. For each: what happened, the date, why it matters to a
founder, and the source URL.
If the founder named a specific topic in the request, focus on that instead.
Save to brain/outputs/YYYY-MM-DD-trend-research.md.

## Write the blog post @jocasta [approval]
Write a blog post of 500 to 700 words from the research:
- A specific, curiosity-driven headline (not "This Week in AI")
- A two-sentence opening that explains why this week matters right now
- One short section per trend (3–5 sentences each)
- A closing takeaway: what should a solo founder do about this?
- Sources list at the end (URLs from research step)
Use only facts from the research. No filler, no generic motivation.
Save to brain/outputs/YYYY-MM-DD-blog-<slug>.md.

## Review the post @jim
Check every claim in the blog post against the research step. Remove or correct anything not supported.
Check: does the headline earn clicks without being clickbait? Is every section tight?
Fix the writing. Output the final blog post in full, ready to publish.

## Write the WhatsApp community message @herbie
Write the message for the founder's WhatsApp community (from brain/wiki/about-me.md, section: Accounts).
Format:
- One hook line (makes them want to read the full post)
- Three bullet points with the key takeaways (one line each, plain language)
- Last line: "Full post: [link]" — the founder will fill in the link before posting.
Maximum 90 words. Plain text, reads well on a phone. No markdown, no asterisks.
Output only the message, nothing else.

## Post to WhatsApp community @vision [approval]
Vision will open WhatsApp Web and type the message into the community.

TOOL_CALL: browser.whatsapp_post_to_community(community_name=<community_name_from_about_me>, message=<whatsapp_message_from_previous_step>)

If status=typed: tell the founder "Message is ready in WhatsApp Web. Press Send when you have added the blog link."
If status=needs_scan: tell the founder to run: python save_session.py whatsapp
If status=not_found: ask the founder to confirm the exact community name from brain/wiki/about-me.md.

Report the final status.
