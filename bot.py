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
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === BRANDING CONFIG ===
BRAND_NAME = "SPARTA NEETQUIZ"
BRAND_TAGLINE = "India ka sabse tez NEET quiz bot"
# =======================

# === MOTIVATIONAL QUOTES ===
QUOTES = [
    "🌟 *Shabash!* Consistency hi success ki chaabi hai. Aise hi lagay raho!",
    "🔥 *Kya baat!* Aaj ka mehnat kal ka selection hai. Keep going!",
    "💪 *Excellent!* NEET ka topper banna hai toh aise hi practice karo!",
    "🎯 *Perfect!* Har sahi answer tumhe selection ke aur kareeb le jata hai.",
    "🚀 *Zabardast!* Doctor banne ka sapna aise hi poora hoga!",
    "⭐ *Great job!* Sachin Tendulkar bhi daily practice se legend bana tha.",
    "🏆 *Superb!* Aaj ka effort, kal ki success. Aise hi ladte raho!",
    "🧠 *Smart move!* Concept clear, answer correct. Yehi formula hai!",
    "💡 *Right answer!* NEET crack karne ke liye aise hi focus chahiye!",
    "🎓 *Well done!* Doctor banna mushkil hai, lekin tum kar sakte ho!",
    "🌱 *Good!* Chhote-chhote steps se hi bada safar tay hota hai.",
    "⚡ *Fast and correct!* Yehi speed NEET exam mein kaam aayegi!",
]
# ==========================

# === questions.json load ===
with open("questions.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]

# === Active quiz sessions (group_id -> True) ===
ACTIVE_SESSIONS = set()

# === Poll ID -> question data mapping ===
POLL_TRACKER = {}
# =============================================


# === HTTP Server (Render health check ke liye) ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')

    def log_message(self, format, *args):
        pass


def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"HTTP server port {port} pe chal raha hai")
    server.serve_forever()
# ================================================


def clean_text(text):
    """LaTeX symbols aur HTML tags hata do."""
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\$[^$]*\$', '', text)
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎯 *{BRAND_NAME}* mein aapka swagat!\n"
        f"_{BRAND_TAGLINE}_\n\n"
        "📖 *Commands:*\n"
        "▫️ /quiz - 1 random question\n"
        "▫️ /quiz100 - 100 questions (30 sec gap)\n"
        "▫️ /quiz <chapter> - Chapter wise 1 question\n"
        "▫️ /quiz100 <chapter> - Chapter wise 100 questions\n"
        "▫️ /stop - Chalu quiz rok do\n"
        "▫️ /chapters - Saare chapters ki list\n"
        "▫️ /help - Madad\n\n"
        f"📚 Powered by {BRAND_NAME}",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n"
        "/quiz - 1 question\n"
        "/quiz100 - 100 questions (30 sec gap)\n"
        "/quiz The Living World - Chapter wise 1 question\n"
        "/quiz100 The Living World - Chapter wise 100 questions\n"
        "/stop - Chalu quiz rok do\n"
        "/chapters - Chapter list",
        parse_mode="Markdown"
    )


async def chapters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chapters_set = set(q.get("chapter", "Unknown") for q in QUESTIONS)
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"
    await update.message.reply_text(
        f"📚 *Available Chapters:*\n\n{chapters_list}",
        parse_mode="Markdown"
    )


async def send_one_quiz(chat_id, context, q):
    """Ek question bhejo aur poll ID track karo."""
    options = [clean_text(o)[:100] for o in q["options"]]

    if len(options) != 4 or any(not o for o in options):
        return False

    question_text = clean_text(q["question"])[:300]
    if not question_text:
        return False

    answer = q.get("answer", 0)
    if not isinstance(answer, int) or answer < 0 or answer > 3:
        return False

    try:
        msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"🎯 {question_text}",
            options=options,
            type=Poll.QUIZ,
            correct_option_id=answer,
            is_anonymous=False,
        )
        POLL_TRACKER[msg.poll.id] = {
            "chat_id": chat_id,
            "correct_option_id": answer,
        }
        return True
    except Exception as e:
        logger.error(f"Poll send error: {e}")
        return False


async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jab koi sahi answer de, usse tag karo + motivational quote bhejo."""
    answer = update.poll_answer
    poll_id = answer.poll_id
    user = answer.user
    chosen = answer.option_ids[0] if answer.option_ids else None

    poll_data = POLL_TRACKER.get(poll_id)
    if not poll_data:
        return

    correct = poll_data["correct_option_id"]

    if chosen == correct:
        name = user.first_name or "Student"
        # Clickable mention
        if user.username:
            mention = f'<a href="tg://user?id={user.id}">@{user.username}</a>'
        else:
            mention = f'<a href="tg://user?id={user.id}">{name}</a>'

        quote = random.choice(QUOTES)

        try:
            await context.bot.send_message(
                chat_id=poll_data["chat_id"],
                text=f"{quote}\n\n— {mention} ✅",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Correct answer msg error: {e}")


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

    for _ in range(5):
        q = random.choice(pool)
        if await send_one_quiz(update.effective_chat.id, context, q):
            return

    await update.message.reply_text("Question bhejne mein problem aayi. Dobara try karo.")


async def quiz100(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """100 questions, har ek ke beech 30 second gap."""
    if not QUESTIONS:
        await update.message.reply_text("Question bank khaali hai.")
        return

    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_SESSIONS:
        await update.message.reply_text(
            "⚠️ Ek quiz session pehle se chal raha hai.\n"
            "Rokne ke liye /stop bhejo."
        )
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

    total = 100
    gap = 30

    ACTIVE_SESSIONS.add(chat_id)

    await update.message.reply_text(
        f"🎯 *{BRAND_NAME}*\n\n"
        f"📝 {total} questions aa rahe hain...\n"
        f"⏱️ Har question ke beech {gap} second ka gap hoga.\n"
        f"🛑 Rokne ke liye /stop bhejo.\n\n"
        f"Apne answers ready rakho! 💪",
        parse_mode="Markdown"
    )

    sent = 0
    attempts = 0
    used = set()

    while sent < total and attempts < total * 5:
        if chat_id not in ACTIVE_SESSIONS:
            await update.message.reply_text(
                f"🛑 Quiz rok diya gaya.\n"
                f"📊 Total {sent} questions bheje gaye the.\n\n"
                f"Dobara shuru karne ke liye /quiz100 bhejo."
            )
            return

        q = random.choice(pool)
        qid = id(q)
        attempts += 1

        if qid in used:
            continue
        used.add(qid)

        if await send_one_quiz(chat_id, context, q):
            sent += 1
            if sent < total:
                for _ in range(gap):
                    if chat_id not in ACTIVE_SESSIONS:
                        await update.message.reply_text(
                            f"🛑 Quiz rok diya gaya.\n"
                            f"📊 Total {sent} questions bheje gaye the.\n\n"
                            f"Dobara shuru karne ke liye /quiz100 bhejo."
                        )
                        return
                    await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.5)

    ACTIVE_SESSIONS.discard(chat_id)

    await update.message.reply_text(
        f"✅ *Quiz Complete!*\n\n"
        f"📊 Total {sent} questions bheje gaye.\n"
        f"🔁 Aur practice ke liye /quiz100 bhejo\n\n"
        f"📚 Powered by {BRAND_NAME}",
        parse_mode="Markdown"
    )


async def stop_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chalu quiz session ko rok do."""
    chat_id = update.effective_chat.id
    if chat_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.discard(chat_id)
        await update.message.reply_text(
            f"🛑 *Quiz session rok diya gaya.*\n\n"
            f"Dobara shuru karne ke liye /quiz100 bhejo.\n\n"
            f"📚 Powered by {BRAND_NAME}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ Koi active quiz session nahi chal raha.\n"
            "Start karne ke liye /quiz100 bhejo."
        )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable set karo.")

    # HTTP server background thread mein (Render health check ke liye)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("chapters", chapters))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("quiz100", quiz100))
    app.add_handler(CommandHandler("stop", stop_quiz))
    app.add_handler(PollAnswerHandler(poll_answer_handler))

    logger.info("Bot start ho raha hai...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
