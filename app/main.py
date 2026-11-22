"""Vision's front door: a private Telegram bot that only its owner can use."""
import datetime as dt
import logging
import os
from zoneinfo import ZoneInfo

from . import env  # noqa: F401  (must load before anything reads settings)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from . import core, llm
from .dashboard import start_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # keeps API keys and bot tokens out of the logs
log = logging.getLogger("vision")

OWNER = int(os.environ.get("OWNER_ID", "0") or 0)
TZ = ZoneInfo(os.environ.get("TZ", "Asia/Kolkata"))
DAYS = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

AGENTS = core.load_agents()
PROCS = core.load_procedures()
JOBS = None  # the job queue, set in main()
NAG_MINUTES = int(os.environ.get("NAG_MINUTES", "10") or 10)


def is_owner(update: Update):
    return OWNER and update.effective_user and update.effective_user.id == OWNER


async def send(bot, chat_id, text, **kw):
    text = text or "(empty reply)"
    for i in range(0, len(text), 4000):  # Telegram's limit is 4096 characters per message
        await bot.send_message(chat_id, text[i:i + 4000], **(kw if i + 4000 >= len(text) else {}))


async def nag(ctx: ContextTypes.DEFAULT_TYPE):
    """Keep reminding (and ringing, if set up) until the founder answers. Gives up after 3 reminders."""
    d = ctx.job.data
    if core.run_status(d["run_id"]) != "asking" or d["count"] >= 3:
        ctx.job.schedule_removal()
        return
    d["count"] += 1
    await send(ctx.bot, OWNER, f"Vision ▸ Still waiting on you ({d['count']}/3): {d['question']}\n"
                               "Reply with your answer, or /skip to cancel the task.")
    await llm.call_founder()


async def run_proc(bot, chat_id, name, request="", run_id=None, answer=None):
    proc = PROCS[name]
    async for ev in core.run_procedure(proc, AGENTS, request=request, run_id=run_id, answer=answer):
        if ev["type"] == "ask":
            await send(bot, chat_id, f"{ev['agent'].title()} needs you ▸ {ev['question']}\n\n"
                                     "Reply with your answer and the work continues. /skip cancels it.")
            await llm.call_founder()
            if JOBS:
                JOBS.run_repeating(nag, interval=NAG_MINUTES * 60, first=NAG_MINUTES * 60,
                                   data={"run_id": ev["run_id"], "question": ev["question"], "count": 0})
            return
        if ev["type"] == "step":
            await send(bot, chat_id, f"{ev['agent'].title()} ▸ {ev['title']} ({ev['n']}/{ev['total']})\n\n{ev['output']}")
        elif ev["type"] == "pause":
            buttons = InlineKeyboardMarkup([[
                InlineKeyboardButton("Approve, continue", callback_data=f"go:{ev['run_id']}"),
                InlineKeyboardButton("Stop", callback_data=f"stop:{ev['run_id']}"),
            ]])
            await send(bot, chat_id, f"Vision ▸ '{name}' is waiting for your approval before the next step.",
                       reply_markup=buttons)
        elif ev["type"] == "done":
            await send(bot, chat_id, f"Vision ▸ '{name}' finished.")


async def process(bot, chat_id, text):
    """Everything the founder says or schedules ends up here."""
    try:
        await bot.send_chat_action(chat_id, ChatAction.TYPING)
        waiting = core.asking_run()
        if waiting and waiting[1] in PROCS:  # this message is the answer an agent was waiting for
            await run_proc(bot, chat_id, waiting[1], run_id=waiting[0], answer=text)
            return
        kind, name, rest = await core.route(text, AGENTS, PROCS)
        if kind == "procedure":
            await send(bot, chat_id, f"Vision ▸ Starting '{name}'.")
            await run_proc(bot, chat_id, name, request=rest)
        else:
            reply = await core.ask(name, rest, AGENTS)
            await send(bot, chat_id, f"{name.title()} ▸ {reply}")
    except Exception as e:  # never fail silently
        log.exception("processing failed")
        await send(bot, chat_id, f"Vision ▸ Something broke and I could not finish that.\nReason: {e}")


# ---------- handlers ----------

async def whoami(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram user ID is {update.effective_user.id}")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    await update.message.reply_text(
        "Vision online.\n\n"
        "Just talk to me, or name a team member first: 'Friday, draft a post about ...'\n"
        "Voice notes work too, in English, Tamil or Hindi.\n\n"
        "/team - who does what\n/procedures - routines I can run\n/run <name> - run a routine\n"
        "/remember <fact> - save something for the whole team\n/facts - what is saved\n/forget <number>\n"
        "/skip - cancel a task that is waiting for your answer"
    )


async def team(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_owner(update):
        await send(ctx.bot, update.effective_chat.id,
                   "\n".join(f"{a['name'].title()} - {a['title']}" for a in AGENTS.values()))


async def procedures(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_owner(update):
        await send(ctx.bot, update.effective_chat.id,
                   "\n".join(f"{p['name']} - {p['description']}" for p in PROCS.values()) or "No procedures yet.")


async def run_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if not ctx.args or ctx.args[0].lower() not in PROCS:
        await update.message.reply_text("Usage: /run <name>. See /procedures for the names.")
        return
    try:
        await run_proc(ctx.bot, update.effective_chat.id, ctx.args[0].lower(), request=" ".join(ctx.args[1:]))
    except Exception as e:
        log.exception("procedure failed")
        await send(ctx.bot, update.effective_chat.id, f"Vision ▸ The procedure stopped with an error: {e}")


async def remember(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /remember <fact>")
        return
    core.remember(" ".join(ctx.args))
    await update.message.reply_text("Saved. The whole team will keep it in mind.")


async def facts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_owner(update):
        await send(ctx.bot, update.effective_chat.id,
                   "\n".join(f"{i}. {t}" for i, t in core.facts()) or "Nothing saved yet.")


async def forget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    ok = ctx.args and ctx.args[0].isdigit() and core.forget(int(ctx.args[0]))
    await update.message.reply_text("Forgotten." if ok else "Usage: /forget <number from /facts>")


async def skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    waiting = core.asking_run()
    if waiting:
        core.stop_run(waiting[0])
    await update.message.reply_text(f"Cancelled '{waiting[1]}'." if waiting else "Nothing is waiting on you.")


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if is_owner(update):
        await process(ctx.bot, update.effective_chat.id, update.message.text)


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return
    chat_id = update.effective_chat.id
    try:
        voice = update.message.voice or update.message.audio
        f = await voice.get_file()
        text = await llm.transcribe(bytes(await f.download_as_bytearray()), voice.mime_type or "audio/ogg")
    except Exception as e:
        log.exception("voice failed")
        await send(ctx.bot, chat_id, f"Vision ▸ I could not understand that voice note. Reason: {e}")
        return
    await send(ctx.bot, chat_id, f"Heard: {text}")
    await process(ctx.bot, chat_id, text)


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_owner(update):
        return
    await q.answer()
    action, run_id = q.data.split(":")
    run_id = int(run_id)
    await q.edit_message_reply_markup(None)
    name = core.run_procedure_name(run_id)
    if action == "stop" or name not in PROCS:
        core.stop_run(run_id)
        await send(ctx.bot, q.message.chat_id, "Vision ▸ Stopped.")
        return
    try:
        await run_proc(ctx.bot, q.message.chat_id, name, run_id=run_id)
    except Exception as e:
        log.exception("resume failed")
        await send(ctx.bot, q.message.chat_id, f"Vision ▸ Could not continue: {e}")


async def scheduled(ctx: ContextTypes.DEFAULT_TYPE):
    job = ctx.job.data
    do = job["do"].strip()
    if do.startswith("procedure:") and do.split(":", 1)[1] in PROCS:
        try:
            await run_proc(ctx.bot, OWNER, do.split(":", 1)[1], request=f"Scheduled run: {job.get('name', '')}")
        except Exception as e:
            await send(ctx.bot, OWNER, f"Vision ▸ Scheduled task '{job.get('name')}' failed: {e}")
    else:
        await process(ctx.bot, OWNER, do)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing in .env")
    if not OWNER:
        log.warning("OWNER_ID is not set. Send /whoami to the bot, put the number in .env, then restart.")

    app = Application.builder().token(token).build()
    global JOBS
    JOBS = app.job_queue
    app.add_handler(CommandHandler("whoami", whoami))
    for name, fn in [("start", start), ("team", team), ("procedures", procedures), ("run", run_cmd),
                     ("remember", remember), ("facts", facts), ("forget", forget), ("skip", skip)]:
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    if OWNER:
        for job in core.load_schedules():
            hh, mm = str(job["time"]).split(":")
            days = tuple(DAYS[d.lower()[:3]] for d in job.get("days", DAYS))
            app.job_queue.run_daily(scheduled, dt.time(int(hh), int(mm), tzinfo=TZ), days=days,
                                    data=job, name=job.get("name"))
            log.info("scheduled '%s' at %s", job.get("name"), job["time"])

    # Start the local web dashboard
    port = start_dashboard()
    log.info("Dashboard running at http://localhost:%d", port)

    log.info("Vision is online with %d agents and %d procedures", len(AGENTS), len(PROCS))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
