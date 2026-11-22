"""Vision's core: the agent team, routing, memory and procedures."""
import json
import os
import re
import sqlite3
import time
from pathlib import Path

import yaml

from . import llm

# Browser + Instagram tools — imported lazily so Vision starts even without Playwright installed
def _browser():
    from . import browser
    return browser

def _instagram():
    from . import instagram
    return instagram

# Host tools client — calls Windows host FastAPI server
def _tools():
    from . import tools
    return tools

ROOT = Path(os.environ.get("VISION_HOME", Path(__file__).resolve().parent.parent))
DB_PATH = ROOT / "data" / "vision.db"
CHIEF = "vision"


# ---------- files ----------

def _split(text):
    """Split a markdown file into (frontmatter dict, body)."""
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        return yaml.safe_load(fm) or {}, body.strip()
    return {}, text.strip()


def load_agents():
    agents = {}
    for f in sorted((ROOT / "agents").glob("*.md")):
        meta, body = _split(f.read_text(encoding="utf-8"))
        name = str(meta.get("name") or f.stem).lower()
        agents[name] = {
            "name": name,
            "title": meta.get("title", ""),
            "handles": meta.get("handles", ""),
            "search": bool(meta.get("web_search", False)),
            "quality": bool(meta.get("quality", False)),
            "prompt": body,
        }
    if CHIEF not in agents:
        raise RuntimeError("agents/vision.md is missing")
    return agents


def load_procedures():
    procs = {}
    for f in sorted((ROOT / "procedures").glob("*.md")):
        meta, body = _split(f.read_text(encoding="utf-8"))
        name = str(meta.get("name") or f.stem).lower()
        steps = []
        for chunk in re.split(r"^## +", body, flags=re.M)[1:]:
            head, _, rest = chunk.partition("\n")
            who = re.search(r"@(\w+)", head)
            steps.append({
                "title": re.sub(r"@\w+|\[approval\]", "", head, flags=re.I).strip(),
                "agent": who.group(1).lower() if who else None,
                "approval": "[approval]" in head.lower(),
                "instructions": rest.strip(),
            })
        procs[name] = {
            "name": name,
            "description": meta.get("description", ""),
            "owner": str(meta.get("owner", CHIEF)).lower(),
            "steps": steps,
        }
    return procs


def load_schedules():
    f = ROOT / "schedules.yaml"
    if not f.exists():
        return []
    return yaml.safe_load(f.read_text(encoding="utf-8")) or []


# ---------- memory ----------

def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, ts REAL, agent TEXT, role TEXT, content TEXT);
        CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, ts REAL, text TEXT);
        CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, ts REAL, procedure TEXT, step INTEGER,
                                        context TEXT, status TEXT);
    """)
    return c


def remember(text):
    with db() as c:
        c.execute("INSERT INTO facts(ts, text) VALUES(?, ?)", (time.time(), text.strip()))


def facts():
    with db() as c:
        return [(r["id"], r["text"]) for r in c.execute("SELECT id, text FROM facts ORDER BY id")]


def forget(fact_id):
    with db() as c:
        return c.execute("DELETE FROM facts WHERE id = ?", (fact_id,)).rowcount > 0


def _history(agent, limit=8):
    with db() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE agent = ? ORDER BY id DESC LIMIT ?", (agent, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save(agent, role, content):
    with db() as c:
        c.execute("INSERT INTO messages(ts, agent, role, content) VALUES(?, ?, ?, ?)",
                  (time.time(), agent, role, content))


# ---------- prompts ----------

def _cross_agent_summary():
    """Short summary of which agents have been active, for Vision's awareness."""
    try:
        with db() as c:
            rows = c.execute(
                "SELECT agent, COUNT(*) as cnt, MAX(ts) as last_ts "
                "FROM messages WHERE role='user' GROUP BY agent ORDER BY last_ts DESC"
            ).fetchall()
        if not rows:
            return "(no conversations yet)"
        parts = []
        for r in rows:
            last = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["last_ts"]))
            parts.append(f"- {r['agent'].title()}: {r['cnt']} user messages, last active {last}")
        return "\n".join(parts)
    except Exception:
        return "(unavailable)"


def _brain_context():
    """Load the brain index + about-me for agents to read before tasks."""
    parts = []
    index = ROOT / "brain" / "wiki" / "index.md"
    if index.exists():
        parts.append("# Brain index\n" + index.read_text(encoding="utf-8"))
    about = ROOT / "brain" / "wiki" / "about-me.md"
    if about.exists():
        parts.append("# About the founder\n" + about.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def system_for(agent, agents):
    company_file = ROOT / "company.md"
    company = company_file.read_text(encoding="utf-8") if company_file.exists() else "(not filled in yet)"
    team = "\n".join(f"- {a['name'].title()}: {a['title']}" for a in agents.values())
    known = "\n".join(f"- {t}" for _, t in facts()) or "(nothing saved yet)"
    brain = _brain_context()
    cross = _cross_agent_summary()
    return f"""You are {agent['name'].title()}, {agent['title']}.
You are one member of an AI team that runs the back office of a one-person startup. The founder is your boss
and the only human in the company. Your job is to take work off the founder's plate: finish tasks, don't
hand them back as homework.

{agent['prompt']}

# The team
{team}

# Team activity (who the founder has spoken with)
{cross}

# Company profile
{company}

# Things the founder asked the team to remember
{known}

# Knowledge base
{brain if brain else "(brain/wiki not filled in yet — ask the founder to fill in brain/wiki/about-me.md)"}

# Rules for every reply
- Reply in the language the founder used: English, Tamil, Hindi, or the same mix they wrote in.
- You are replying inside Telegram: plain text, short paragraphs, simple dashes for lists. No tables.
- Be brief. Lead with the result. Ask a question only when you cannot proceed without the answer.
- Never invent facts, numbers, links or results. If you could not do something, say so plainly.
- You have TOOL_CALL capability. When a task involves calling a tool, output TOOL_CALL: module.function(args) and it executes.
- For irreversible actions (posting to Instagram, sending WhatsApp messages), state what you are about to do,
  then do it. Do not hand tasks back as homework — finish them. Approval gates in procedures handle human sign-off."""


# ---------- routing ----------

def direct_address(text, agents):
    """'Friday, write a post' -> ('friday', 'write a post'). None if no agent is named first."""
    m = re.match(r"^\s*(?:hey|hi|ok|okay)?[\s,]*([A-Za-z]+)\b[\s,:!.\-]*(.*)$", text, flags=re.S | re.I)
    if m and m.group(1).lower() in agents and m.group(2).strip():
        return m.group(1).lower(), m.group(2).strip()
    return None


async def route(text, agents, procs):
    """Decide who handles a message. Returns ('agent', name, text) or ('procedure', name, text)."""
    named = direct_address(text, agents)
    if named and named[0] != CHIEF:
        agent_name, agent_text = named[0], named[1]
        # Check if the message should trigger a procedure owned by this agent
        agent_procs = {n: p for n, p in procs.items() if p.get("owner") == agent_name}
        if agent_procs:
            plist = "\n".join(f"- procedure:{p['name']} | {p['description']}" for p in agent_procs.values())
            answer = await llm.chat(
                f"The founder is talking to agent '{agent_name}'. "
                "If the message clearly requests one of the listed procedures, return 'procedure:<name>'. "
                f"Otherwise return 'agent:{agent_name}'. One item only, nothing else.\n\n"
                f"Procedures owned by {agent_name}:\n{plist}",
                [{"role": "user", "content": agent_text}],
            )
            m = re.search(r"(agent|procedure):\s*([a-z0-9_\-]+)", answer.lower())
            if m:
                kind, name = m.group(1), m.group(2)
                if kind == "procedure" and name in procs:
                    return "procedure", name, agent_text
        return "agent", agent_name, agent_text
    if named:
        text = named[1]

    roster = "\n".join(f"- agent:{a['name']} | {a['title']} | {a['handles']}" for a in agents.values())
    plist = "\n".join(f"- procedure:{p['name']} | {p['description']}" for p in procs.values()) or "(none)"
    answer = await llm.chat(
        "You are the dispatcher for a founder's AI team. Read the founder's message and choose who handles it. "
        "Choose a procedure only when the message clearly asks for that exact routine. "
        "For casual chat, personal matters or anything unclear, choose agent:vision. "
        "Answer with exactly one item from the lists, such as agent:friday or procedure:daily-brief. "
        "Nothing else.\n\n"
        f"Agents:\n{roster}\n\nProcedures:\n{plist}",
        [{"role": "user", "content": text}],
    )
    m = re.search(r"(agent|procedure):\s*([a-z0-9_\-]+)", answer.lower())
    if m:
        kind, name = m.group(1), m.group(2)
        if kind == "agent" and name in agents:
            return "agent", name, text
        if kind == "procedure" and name in procs:
            return "procedure", name, text
    return "agent", CHIEF, text


async def ask(agent_name, text, agents, keep=True, save_text=None):
    """Ask an agent. `save_text` overrides what gets stored in history (use original user text,
    not any prefixed/modified version sent to the LLM).
    Supports ReAct tool loop: if the reply contains TOOL_CALL: lines, executes them and feeds
    results back until the agent produces a final reply without tool calls (max 6 iterations)."""
    from .tools import TOOL_DESCRIPTIONS
    agent = agents[agent_name]
    # Inject tool descriptions into system prompt so agent knows what it can call
    system = system_for(agent, agents) + "\n\n" + TOOL_DESCRIPTIONS
    messages = (_history(agent_name) if keep else []) + [{"role": "user", "content": text}]

    final_reply = text  # fallback
    for _iteration in range(6):
        reply = await llm.chat(system, messages,
                               search=agent.get("search", False),
                               quality=agent.get("quality", False))
        # Check for TOOL_CALL lines
        tool_lines = [l.strip() for l in reply.splitlines() if l.strip().startswith(TOOL_CALL)]
        if not tool_lines:
            final_reply = reply
            break
        # Execute each tool call and collect results
        results = []
        for line in tool_lines:
            result = await _dispatch_tool(line)
            results.append(f"Tool result for `{line}`:\n{result}")
        # Feed results back as an assistant + user turn
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": "\n\n".join(results) + "\n\nPlease continue based on these tool results."})
    else:
        # Hit iteration limit — use last reply even if it had tool calls
        final_reply = reply

    if keep:
        _save(agent_name, "user", save_text if save_text is not None else text)
        _save(agent_name, "assistant", final_reply)
    return final_reply


# ---------- procedures ----------

ASK = "ASK_FOUNDER:"
TOOL_CALL = "TOOL_CALL:"


async def _dispatch_tool(line: str) -> str:
    """Execute a TOOL_CALL: line from a procedure step and return the result as text."""
    import re as _re
    m = _re.match(r"TOOL_CALL:\s*(\w+)\.(\w+)\((.*)?\)", line.strip(), _re.S)
    if not m:
        return f"(Could not parse tool call: {line})"
    module, func, args_raw = m.group(1), m.group(2), m.group(3)
    # Parse kwargs: key=<value>
    kwargs = {}
    for kv in _re.findall(r'(\w+)=(?:"([^"]*?)"|<([^>]*?)>|([^\s,)]+))', args_raw):
        key = kv[0]
        value = kv[1] or kv[2] or kv[3]
        kwargs[key] = value
    try:
        if module == "browser":
            mod = _browser()
        elif module == "instagram":
            mod = _instagram()
        elif module in ("computer", "video", "reddit"):
            # Route to host tools via HTTP
            t = _tools()
            fn_map = {
                "computer": {
                    "run": t.run_command,
                    "read_file": t.read_file,
                    "write_file": t.write_file,
                    "open": t.open_app,
                    "ls": t.list_dir,
                },
                "video": {
                    "create_reel": t.create_reel,
                    "upload_instagram": t.upload_instagram,
                },
                "reddit": {
                    "post": t.reddit_post,
                    "comment": t.reddit_comment,
                    "trending": t.reddit_trending,
                    "opportunities": t.reddit_opportunities,
                },
            }
            fn = fn_map.get(module, {}).get(func)
            if fn is None:
                return f"(Unknown function: {module}.{func})"
            import asyncio as _asyncio
            result = await fn(**kwargs) if _asyncio.iscoroutinefunction(fn) else fn(**kwargs)
            return json.dumps(result, ensure_ascii=False)
        else:
            return f"(Unknown module: {module})"
        fn = getattr(mod, func, None)
        if fn is None:
            return f"(Unknown function: {module}.{func})"
        import asyncio
        result = await fn(**kwargs) if asyncio.iscoroutinefunction(fn) else fn(**kwargs)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"(Tool call failed: {e})"


async def run_procedure(proc, agents, request="", run_id=None, answer=None):
    """Run a procedure step by step. Yields events:
    {'type': 'step', 'title', 'agent', 'output', 'n', 'total'}
    {'type': 'pause', 'run_id'}   -> waiting for the founder's approval before the next step
    {'type': 'ask', 'run_id', 'agent', 'question'} -> an agent is stuck and needs the founder's answer
    {'type': 'done'}
    Pass run_id to resume a paused run; pass answer as well to resume one that asked a question.
    """
    steps = proc["steps"]
    with db() as c:
        if run_id is None:
            ctx, step = {"request": request, "outputs": []}, 0
            run_id = c.execute(
                "INSERT INTO runs(ts, procedure, step, context, status) VALUES(?, ?, 0, ?, 'running')",
                (time.time(), proc["name"], json.dumps(ctx)),
            ).lastrowid
        else:
            row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row or row["status"] not in ("paused", "asking"):
                raise RuntimeError("That run is not waiting for you.")
            ctx, step = json.loads(row["context"]), row["step"]
            if row["status"] == "asking":
                ctx.setdefault("answers", []).append({"q": ctx.pop("question", ""), "a": answer or "(no answer)"})

    while step < len(steps):
        s = steps[step]
        who = s["agent"] if s["agent"] in agents else proc["owner"]
        if who not in agents:
            who = CHIEF
        prior = "\n\n".join(f"### {o['title']} (by {o['agent'].title()})\n{o['output']}" for o in ctx["outputs"])
        # Execute any TOOL_CALL lines in the step instructions first
        tool_results = []
        clean_instructions = []
        for line in s["instructions"].splitlines():
            if line.strip().startswith(TOOL_CALL):
                result = await _dispatch_tool(line.strip()[len(TOOL_CALL):].strip())
                tool_results.append(f"Tool result: {result}")
            else:
                clean_instructions.append(line)

        task = (
            f"You are running step {step + 1} of {len(steps)} of the procedure '{proc['name']}': {s['title']}\n\n"
            f"Founder's request: {ctx['request'] or '(no extra details)'}\n\n"
            f"Instructions for this step:\n{chr(10).join(clean_instructions)}\n\n"
            + (f"Tool results from this step:\n{chr(10).join(tool_results)}\n\n" if tool_results else "")
            + f"Work done in earlier steps:\n{prior or '(this is the first step)'}\n\n"
            + ("The founder's answers to questions asked during this run:\n"
               + "\n".join(f"Q: {x['q']}\nA: {x['a']}" for x in ctx["answers"]) + "\n\n"
               if ctx.get("answers") else "")
            + "Do this step now and output only its result. If, and only if, you cannot do the step without a "
            f"decision or a fact that only the founder has, output a single line starting with {ASK} followed "
            "by one clear question, and nothing else. Do not ask what you can reasonably decide yourself."
        )
        output = await ask(who, task, agents, keep=False)
        asked = re.search(rf"^\s*{ASK}\s*(.+)", output, flags=re.M)
        if asked and len(ctx.get("answers", [])) < 5:
            ctx["question"] = asked.group(1).strip()
            with db() as c:
                c.execute("UPDATE runs SET context = ?, status = 'asking' WHERE id = ?", (json.dumps(ctx), run_id))
            yield {"type": "ask", "run_id": run_id, "agent": who, "question": ctx["question"]}
            return
        ctx["outputs"].append({"title": s["title"], "agent": who, "output": output})
        step += 1
        pause = s["approval"] and step < len(steps)
        with db() as c:
            c.execute("UPDATE runs SET step = ?, context = ?, status = ? WHERE id = ?",
                      (step, json.dumps(ctx), "paused" if pause else "running", run_id))
        yield {"type": "step", "title": s["title"], "agent": who, "output": output, "n": step, "total": len(steps)}
        if pause:
            yield {"type": "pause", "run_id": run_id}
            return

    with db() as c:
        c.execute("UPDATE runs SET status = 'done' WHERE id = ?", (run_id,))
    yield {"type": "done"}


def stop_run(run_id):
    with db() as c:
        c.execute("UPDATE runs SET status = 'stopped' WHERE id = ?", (run_id,))


def run_procedure_name(run_id):
    with db() as c:
        row = c.execute("SELECT procedure FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row["procedure"] if row else None


def asking_run():
    """The most recent run that is waiting for the founder's answer, or None."""
    with db() as c:
        row = c.execute("SELECT id, procedure FROM runs WHERE status = 'asking' ORDER BY id DESC LIMIT 1").fetchone()
    return (row["id"], row["procedure"]) if row else None


def run_status(run_id):
    with db() as c:
        row = c.execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row["status"] if row else None
