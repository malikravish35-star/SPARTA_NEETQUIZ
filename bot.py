import asyncio
import json
import os
import random
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# === FIX: Python 3.14 event loop issue ===
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
# =========================================

from dotenv import load_dotenv
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === questions.json load ===
with open("questions.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]


# === HTTP Server (Render health check ke liye) ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

    def log_message(self, format, *args):
        pass  # Render logs clean rakhne ke liye


def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"HTTP server port {port} pe chal raha hai")
    server.serve_forever()
# ================================================


def clean_text(text):
    """LaTeX symbols aur HTML tags hata do."""
    import re
    text = re.sub(r'<[^>]+>', '', text)               # HTML tags
    text = re.sub(r'\$[^$]*\$', '', text)              # $...$ math
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)   # \mathrm{...} etc
    text = re.sub(r'\\[a-zA-Z]+', '', text)            # \alpha etc
    text = re.sub(r'\s+', ' ', text)                   # extra spaces
    return text.strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! NEET Quiz Bot mein swagat.\n\n"
        "/quiz - 1 random question\n"
        "/quiz10 - 10 questions ek saath\n"
        "/quiz <chapter> - Us chapter ka question\n"
        "/quiz10 <chapter> - Us chapter ke 10 questions\n"
        "/chapters - Saare chapters ki list\n"
        "/help - Madad"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/quiz - 1 question\n"
        "/quiz10 - 10 questions\n"
        "/quiz The Living World - Chapter wise 1 question\n"
        "/quiz10 The Living World - Chapter wise 10 questions\n"
        "/chapters - Chapter list"
    )


async def chapters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chapters_set = set(q.get("chapter", "Unknown") for q in QUESTIONS)
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"
    await update.message.reply_text(f"Available Chapters:\n{chapters_list}")


async def send_one_quiz(chat_id, context, q):
    """Ek question bhejo. True return karo agar successful."""
    options = [clean_text(o)[:100] for o in q["options"]]

    # Agar koi option khaali ho gaya cleaning ke baad, skip
    if len(options) != 4 or any(not o for o in options):
        return False

    question_text = clean_text(q["question"])[:300]
    if not question_text:
        return False

    # Answer index 0-3 range mein hona chahiye
    answer = q.get("answer", 0)
    if not isinstance(answer, int) or answer < 0 or answer > 3:
        return False

    try:
        await context.bot.send_poll(
            chat_id=chat_id,
            question=question_text,
            options=options,
            type=Poll.QUIZ,
            correct_option_id=answer,
            is_anonymous=False,
        )
        return True
    except Exception as e:
        logger.error(f"Poll send error: {e}")
        return False


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """1 question bhejo."""
    if not QUESTIONS:
        await update.message.reply_text("Question bank khaali hai.")
        return

    if context.args:
        chapter_name = " ".join(context.args).lower()
        pool = [q for q in QUESTIONS if q.get("chapter", "").lower() == chapter_name]
        if not pool:
            await update.message.reply_text(
                f"'{' '.join(context.args)}' chapter mein koi question nahi mila. /chapters se list dekho."
            )
            return
    else:
        pool = QUESTIONS

    # 5 attempts — kuch questions cleaning ke baad invalid ho sakte hain
    for _ in range(5):
        q = random.choice(pool)
        if await send_one_quiz(update.effective_chat.id, context, q):
            return

    await update.message.reply_text("Question bhejne mein problem aayi. Dobara try karo.")


async def quiz10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """10 questions ek saath bhejo."""
    if not QUESTIONS:
        await update.message.reply_text("Question bank khaali hai.")
        return

    if context.args:
        chapter_name = " ".join(context.args).lower()
        pool = [q for q in QUESTIONS if q.get("chapter", "").lower() == chapter_name]
        if not pool:
            await update.message.reply_text(
                f"'{' '.join(context.args)}' chapter mein koi question nahi mila."
            )
            return
    else:
        pool = QUESTIONS

    await update.message.reply_text("10 questions bhej raha hoon...")

    sent = 0
    attempts = 0
    used = set()

    while sent < 10 and attempts < 50:
        q = random.choice(pool)
        qid = id(q)
        attempts += 1

        if qid in used:
            continue
        used.add(qid)

        if await send_one_quiz(update.effective_chat.id, context, q):
            sent += 1
            await asyncio.sleep(0.5)  # Telegram rate limit se bachne ke liye

    if sent < 10:
        await update.message.reply_text(
            f"Sirf {sent} questions bhej paya. Dobara /quiz10 try karo."
        )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable set karo.")

    # HTTP server background thread mein chalao (Render health check)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Telegram bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("chapters", chapters))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("quiz10", quiz10))

    logger.info("Bot start ho raha hai...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
