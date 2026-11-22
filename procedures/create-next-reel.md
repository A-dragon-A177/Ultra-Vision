---
name: create-next-reel
description: Full reel pipeline — angle, script, NotebookLM audio, edit, caption, Instagram post
owner: friday
---

## Research the angle @jocasta
Search the web for what is performing in the niche right now: trending formats, hooks that are stopping
people mid-scroll, and topics the target audience is talking about this week.
Then, using the company profile and the founder's request, propose three angles for the next reel.
For each angle: the single idea, why the target customer would stop scrolling, and the hook line.
Recommend one and say why in one sentence.
Save your research to brain/outputs/YYYY-MM-DD-reel-research.md.

## Write the script @friday [approval]
Write the reel for the recommended angle (or the one the founder chose).
- 30 to 45 seconds when spoken at 2.5 words per second (75–110 words total).
- Word for word, split into beats. For each beat: spoken line + on-screen text.
- Hook in the first 3 seconds (question, bold claim, or surprising stat).
- One idea only. End with one clear call to action.
- Include: music mood suggestion, visual direction for each beat.
Save to brain/outputs/YYYY-MM-DD-reel-script.md.

## Review the script @jim
Review the script against the company profile. Check:
- Is the hook strong enough to stop scrolling in 3 seconds?
- Does every beat move the idea forward (no filler)?
- Is the CTA specific and easy to act on?
- Does the tone match the company voice?
Give your verdict. Fix every problem. Output the final corrected script in full beat format.

## Generate audio in NotebookLM @vision [approval]
The script is ready. Vision will now try to generate the audio automatically.

TOOL_CALL: browser.notebooklm_create_audio(script=<full_script_text>, notebook_title="Vision Reel <date>")

If the result is status=ready: the audio file is available. Tell the founder the download URL.
If the result is status=option_b or needs_manual: tell the founder to go to the NotebookLM URL in the result,
paste the script from brain/outputs/latest-script-for-notebooklm.txt, click Generate > Audio Overview,
then come back and say "audio ready" with the filename or URL.

Wait for the founder to confirm the audio is ready before moving to the next step.

## Edit and final polish @friday [approval]
Using the audio/video from the previous step and the final script, write:
1. Editing notes: exact timestamps where on-screen text appears, any B-roll needed, music entry/exit point.
2. The final caption (first line = standalone hook, 150–220 characters).
3. 10–15 hashtags: mix of niche (5), mid-size (5), and broad (3–5).
4. A suggested cover frame description (what moment to freeze for the thumbnail).

Output everything the founder needs to do the final edit, in one clean block.
Save to brain/outputs/YYYY-MM-DD-reel-final-package.md.

## Post to Instagram @vision [approval]
Vision will post the reel using the Instagram API (or open the browser if the API is not configured).

TOOL_CALL: instagram.post_reel(video_url=<url_or_path>, caption=<final_caption>)

If status=not_configured: open Instagram in the browser (save_session instagram) and use the browser fallback.
Report the post URL or status back to the founder.

Tell the founder: "Reel posted. Here's what the next one in the series should cover: <one-line suggestion>."
