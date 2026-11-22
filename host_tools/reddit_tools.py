"""
Reddit automation for Neesh AI growth.
Uses PRAW for posting, commenting, and finding promotion opportunities.
Env vars: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
"""
from __future__ import annotations
import asyncio, os, re, time
from typing import Optional

NEESH_AI_SUBREDDITS = [
    "artificial", "MachineLearning", "AIpromptEngineering", "singularity",
    "ChatGPT", "LLMDevs", "learnmachinelearning", "OpenAI", "AIAssistants",
    "Entrepreneur", "startups", "SideProject", "indiehackers",
]

PROMO_KEYWORDS = [
    "ai tool", "looking for ai", "recommend", "automation", "ai startup",
    "ai assistant", "productivity", "work faster", "help with", "anyone know",
    "suggestion", "what do you use", "tools for",
]


def _reddit():
    import praw
    return praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        username=os.environ.get("REDDIT_USERNAME", ""),
        password=os.environ.get("REDDIT_PASSWORD", ""),
        user_agent="NeeshAI/1.0 (by u/neeshai)",
    )


def _has_creds() -> bool:
    return bool(os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"))


# ── Post to subreddit ─────────────────────────────────────────────────────

async def submit_post(subreddit: str, title: str, content: str,
                      url: Optional[str] = None) -> dict:
    if not _has_creds():
        return {"status": "error", "message": "Reddit credentials not configured. Add REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD to .env"}
    try:
        reddit = await asyncio.get_event_loop().run_in_executor(None, _reddit)
        sub = reddit.subreddit(subreddit)
        if url:
            post = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sub.submit(title, url=url)
            )
        else:
            post = await asyncio.get_event_loop().run_in_executor(
                None, lambda: sub.submit(title, selftext=content)
            )
        return {
            "status": "posted",
            "post_id": post.id,
            "url": f"https://www.reddit.com{post.permalink}",
            "subreddit": subreddit,
            "title": title,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Comment on post ───────────────────────────────────────────────────────

async def post_comment(post_url: str, comment: str) -> dict:
    if not _has_creds():
        return {"status": "error", "message": "Reddit credentials not configured"}
    try:
        reddit = await asyncio.get_event_loop().run_in_executor(None, _reddit)
        # Extract post ID from URL: https://www.reddit.com/r/sub/comments/POST_ID/...
        m = re.search(r"/comments/([a-z0-9]+)/", post_url)
        if not m:
            return {"status": "error", "message": f"Could not extract post ID from URL: {post_url}"}
        post_id = m.group(1)
        post = await asyncio.get_event_loop().run_in_executor(
            None, lambda: reddit.submission(id=post_id)
        )
        reply = await asyncio.get_event_loop().run_in_executor(
            None, lambda: post.reply(comment)
        )
        return {
            "status": "commented",
            "comment_id": reply.id,
            "post_url": post_url,
            "chars": len(comment),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Get trending posts ────────────────────────────────────────────────────

async def get_trending(subreddits: list = None, limit: int = 5) -> dict:
    if subreddits is None:
        subreddits = NEESH_AI_SUBREDDITS[:4]
    if not _has_creds():
        return {"status": "error", "message": "Reddit credentials not configured"}
    try:
        reddit = await asyncio.get_event_loop().run_in_executor(None, _reddit)
        results = []
        for sub_name in subreddits[:6]:
            sub = reddit.subreddit(sub_name)
            posts = await asyncio.get_event_loop().run_in_executor(
                None, lambda s=sub: list(s.hot(limit=limit))
            )
            for p in posts:
                results.append({
                    "subreddit": sub_name,
                    "title": p.title,
                    "score": p.score,
                    "comments": p.num_comments,
                    "url": f"https://www.reddit.com{p.permalink}",
                    "age_hours": round((time.time() - p.created_utc) / 3600, 1),
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return {"status": "ok", "posts": results[:20]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Find promotion opportunities ──────────────────────────────────────────

async def find_opportunities() -> dict:
    """Find posts where Neesh AI could add value with a helpful comment."""
    if not _has_creds():
        return {"status": "error", "message": "Reddit credentials not configured"}
    try:
        reddit = await asyncio.get_event_loop().run_in_executor(None, _reddit)
        opportunities = []
        for sub_name in NEESH_AI_SUBREDDITS[:8]:
            sub = reddit.subreddit(sub_name)
            new_posts = await asyncio.get_event_loop().run_in_executor(
                None, lambda s=sub: list(s.new(limit=20))
            )
            for p in new_posts:
                title_lower = p.title.lower()
                body_lower = (p.selftext or "").lower()
                matched = [kw for kw in PROMO_KEYWORDS
                           if kw in title_lower or kw in body_lower]
                if matched:
                    # Recent posts (< 6 hours) with low comment count are ideal
                    age_hours = (time.time() - p.created_utc) / 3600
                    if age_hours < 6 and p.num_comments < 15:
                        opportunities.append({
                            "subreddit": sub_name,
                            "title": p.title,
                            "score": p.score,
                            "comments": p.num_comments,
                            "age_hours": round(age_hours, 1),
                            "url": f"https://www.reddit.com{p.permalink}",
                            "matched_keywords": matched,
                            "preview": (p.selftext or "")[:200],
                        })
        # Sort by freshness + engagement potential
        opportunities.sort(key=lambda x: (x["age_hours"], -x["score"]))
        return {"status": "ok", "opportunities": opportunities[:10]}
    except Exception as e:
        return {"status": "error", "message": str(e)}
