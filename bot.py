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

# === CONFIG ===
BRAND_NAME = "SPARTA NEETQUIZ"
BRAND_TAGLINE = "India ka sabse tez NEET quiz bot"
GAP_SECONDS = 15
MAX_QUESTIONS = 100
# ==============

# === 50 GENERAL MOTIVATIONAL QUOTES ===
QUOTES = [
    "🌟 *Shabash!* Consistency hi success ki chaabi hai. Aise hi lagay raho!",
    "🔥 *Kya baat!* Aaj ki mehnat kal ka selection hai. Keep going!",
    "💪 *Excellent!* Topper banna hai toh aise hi practice karo!",
    "🎯 *Perfect!* Har sahi answer tumhe selection ke aur kareeb le jata hai.",
    "🚀 *Zabardast!* Sapna aise hi poora hota hai!",
    "⭐ *Great job!* Legend bhi daily practice se hi banta hai.",
    "🏆 *Superb!* Aaj ka effort, kal ki success. Aise hi ladte raho!",
    "🧠 *Smart move!* Concept clear, answer correct. Yehi formula hai!",
    "💡 *Right answer!* Aise hi focus chahiye!",
    "🎓 *Well done!* Manzil mushkil hai, lekin tum kar sakte ho!",
    "🌱 *Good!* Chhote-chhote steps se hi bada safar tay hota hai.",
    "⚡ *Fast and correct!* Yehi speed exam mein kaam aayegi!",
    "🔥 *Aag laga di!* Aise hi consistent raho, selection pakka hai!",
    "💎 *Heera ho tum!* Mehnat se hi chamakta hai asli talent.",
    "🦁 *Sher ho tum!* Exam hall mein bhi aise hi dahaadna!",
    "🌟 *Brilliant!* Aaj ka hard work kal ki seat banega!",
    "🎖️ *Champion!* Har din practice karo, rank apne aap aayegi!",
    "🚀 *Rocket speed!* Aise hi solve karte raho, time bachega!",
    "💯 *Perfect score!* Concept crystal clear hai, aur kya chahiye!",
    "🎯 *Target hit!* Aise hi accuracy build karo!",
    "🔥 *Josh high!* Ye energy exam tak banaye rakho!",
    "💪 *Mental power!* Aise hi focus karo, distraction bhaga do!",
    "🌟 *Star ho tum!* Topper banne ka sapna sach hoga!",
    "📚 *Padhai ka josh!* Aise hi hours badhao, success milegi!",
    "⏰ *Time master!* Speed aur accuracy dono perfect!",
    "🧠 *Sharp mind!* Aise hi tricky questions solve karte raho!",
    "🏅 *Medal jeeta!* Har correct answer ek medal hai!",
    "🚀 *Sky is limit!* Aise hi practice karo, kuch bhi possible hai!",
    "💡 *Idea guru!* Concept clear, answer correct, aur kya!",
    "🎓 *Future topper!* Aise hi lagay raho!",
    "🌈 *Colourful mind!* Har chapter ka rang alag, aise hi samjho!",
    "🍀 *Lucky bhi, smart bhi!* Mehnat se hi luck banate ho!",
    "🔥 *Blazing speed!* Aise hi solve karo, time kam nahi padega!",
    "💥 *Dhamaka!* Answer correct, mind sharp!",
    "🎯 *Bull's eye!* Perfect aim, perfect answer!",
    "🏆 *Winner ho!* Aise hi lade raho, trophy tumhari hai!",
    "🌟 *Rising star!* Har din better ban rahe ho!",
    "💪 *Iron will!* Consistency hi asli power hai!",
    "🚀 *Success ke raaste pe!* Aise hi chalo, manzil door nahi!",
    "🧠 *Mastermind!* Aise hi socho, aise hi solve karo!",
    "💎 *Diamond ban rahe ho!* Pressure se hi diamond banta hai!",
    "🔥 *Fire hai tum mein!* Aise hi jalte raho, success milegi!",
    "🎖️ *Topper material!* Aise hi lagay raho, rank aayegi!",
    "🌈 *Umeed ki kiran!* Har answer ek step hai selection ke taraf!",
    "💯 *Perfect!* Aise hi chalo, selection hoga!",
    "⭐ *Shining star!* Tumhari mehnat rang laayegi!",
    "🎯 *On target!* Aise hi karte raho, rank apne aap aayegi!",
    "💪 *Unstoppable!* Koi tumhe rok nahi sakta!",
    "🌟 *Boss ho tum!* Aise hi dominate karo!",
    "🔥 *Full josh!* Mehnat ka fal zaroor milega!",
]
# =======================================

# === questions.json load ===
with open("questions.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]

# === Active quiz sessions (per group) ===
ACTIVE_SESSIONS = set()
POLL_TRACKER = {}

# === THREAD ID MAP (baad mein update karenge) ===
# Example:
# THREAD_IDS = {
#     "Biology": 45,
#     "Chemistry": 46,
#     "Physics": 47,
# }
THREAD_IDS = {}
# =============================================


# === HTTP Server (Render health check) ===
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
# ==========================================


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
        "▫️ `/quiz 10` - 10 questions\n"
        "▫️ `/quiz 50` - 50 questions\n"
        "▫️ `/quiz 100` - 100 questions\n"
        "▫️ `/quiz 20 The Living World` - Chapter wise\n"
        "▫️ `/stop` - Quiz rok do\n"
        "▫️ `/chapters` - Chapter list\n"
        "▫️ `/help` - Madad\n\n"
        f"⏱️ Har question ke beech {GAP_SECONDS} second ka gap\n"
        f"📚 Powered by {BRAND_NAME}",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "*Basic:*\n"
        "`/quiz 10` - 10 questions\n"
        "`/quiz 50` - 50 questions\n"
        "`/quiz 100` - 100 questions\n\n"
        "*Chapter wise:*\n"
        "`/quiz 20 The Living World`\n"
        "`/quiz 50 Plant Kingdom`\n\n"
        "*Others:*\n"
        "`/chapters` - Saare chapters\n"
        "`/stop` - Quiz rok do\n"
        "`/getids` - Topic ID pata karo\n\n"
        f"⏱️ Har question ke beech {GAP_SECONDS} second ka gap",
        parse_mode="Markdown"
    )


async def getids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Topic/Thread ID pata karne ke liye test command."""
    chat = update.effective_chat
    msg = update.effective_message
    thread_id = msg.message_thread_id if msg.message_thread_id else "None"
    await update.message.reply_text(
        f"Chat ID: `{chat.id}`\n"
        f"Chat Type: `{chat.type}`\n"
        f"Thread ID: `{thread_id}`\n"
        f"Is Forum: `{chat.is_forum}`",
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


async def send_one_quiz(chat_id, context, q, thread_id=None):
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
            message_thread_id=thread_id,
        )
        POLL_TRACKER[msg.poll.id] = {
            "chat_id": chat_id,
            "correct_option_id": answer,
            "thread_id": thread_id,
        }
        return True
    except Exception as e:
        logger.error(f"Poll send error: {e}")
        return False


async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Jab koi sahi answer de, tag karo + motivational quote bhejo."""
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
        if user.username:
            mention = f'<a href="tg://user?id={user.id}">@{user.username}</a>'
        else:
            mention = f'<a href="tg://user?id={user.id}">{name}</a>'

        quote = random.choice(QUOTES)

        try:
            await context.bot.send_message(
                chat_id=poll_data["chat_id"],
                text=f"{quote}\n\n— {mention} ✅",
                parse_mode="HTML",
                message_thread_id=poll_data.get("thread_id"),
            )
        except Exception as e:
            logger.warning(f"Correct answer msg skip: {e}")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage:
      /quiz <number>            -> itne questions (1-100)
      /quiz <number> <chapter>  -> chapter wise
    """
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

    # Thread ID nikalo (agar group mein topics enabled hain)
    thread_id = None
    if update.effective_chat.is_forum:
        thread_id = update.effective_message.message_thread_id
        # General topic ka ID 1 hota hai, uske liye None bhejo
        if thread_id == 1:
            thread_id = None

    args = context.args or []
    count = 1
    chapter_filter = None

    if args:
        if args[0].isdigit():
            count = int(args[0])
            if len(args) > 1:
                chapter_filter = " ".join(args[1:]).lower()
        else:
            chapter_filter = " ".join(args).lower()

    if count < 1:
        count = 1
    if count > MAX_QUESTIONS:
        await update.message.reply_text(
            f"⚠️ Maximum {MAX_QUESTIONS} questions ek baar mein.\n"
            f"{MAX_QUESTIONS} set kar diya."
        )
        count = MAX_QUESTIONS

    if chapter_filter:
        pool = [q for q in QUESTIONS if q.get("chapter", "").lower() == chapter_filter]
        if not pool:
            await update.message.reply_text(
                f"❌ '{chapter_filter}' chapter mein koi question nahi mila.\n"
                f"/chapters se list dekho."
            )
            return
    else:
        pool = QUESTIONS

    # 1 question ke liye session start nahi karo
    if count == 1:
        for _ in range(5):
            q = random.choice(pool)
            if await send_one_quiz(chat_id, context, q, thread_id=thread_id):
                return
        await update.message.reply_text("Question bhejne mein problem aayi.")
        return

    ACTIVE_SESSIONS.add(chat_id)
    chapter_msg = f"📖 Chapter: {chapter_filter.title()}\n" if chapter_filter else ""

    await update.message.reply_text(
        f"🎯 *{BRAND_NAME}*\n\n"
        f"{chapter_msg}"
        f"📝 {count} questions aa rahe hain...\n"
        f"⏱️ Har question ke beech {GAP_SECONDS} second ka gap.\n"
        f"🛑 Rokne ke liye /stop bhejo.\n\n"
        f"Apne answers ready rakho! 💪",
        parse_mode="Markdown",
        message_thread_id=thread_id,
    )

    sent = 0
    attempts = 0
    used = set()

    while sent < count and attempts < count * 5:
        if chat_id not in ACTIVE_SESSIONS:
            await update.message.reply_text(
                f"🛑 Quiz rok diya gaya.\n"
                f"📊 Total {sent} questions bheje gaye the.\n\n"
                f"Dobara shuru karne ke liye `/quiz {count}` bhejo.",
                parse_mode="Markdown",
                message_thread_id=thread_id,
            )
            return

        q = random.choice(pool)
        qid = id(q)
        attempts += 1

        if qid in used:
            continue
        used.add(qid)

        if await send_one_quiz(chat_id, context, q, thread_id=thread_id):
            sent += 1
            if sent < count:
                for _ in range(GAP_SECONDS):
                    if chat_id not in ACTIVE_SESSIONS:
                        await update.message.reply_text(
                            f"🛑 Quiz rok diya gaya.\n"
                            f"📊 Total {sent} questions bheje gaye the.\n\n"
                            f"Dobara shuru karne ke liye `/quiz {count}` bhejo.",
                            parse_mode="Markdown",
                            message_thread_id=thread_id,
                        )
                        return
                    await asyncio.sleep(1)
        else:
            await asyncio.sleep(0.5)

    ACTIVE_SESSIONS.discard(chat_id)

    await update.message.reply_text(
        f"✅ *Quiz Complete!*\n\n"
        f"📊 Total {sent} questions bheje gaye.\n"
        f"🔁 Aur practice ke liye `/quiz {count}` bhejo\n\n"
        f"📚 Powered by {BRAND_NAME}",
        parse_mode="Markdown",
        message_thread_id=thread_id,
    )


async def stop_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chalu quiz session ko rok do."""
    chat_id = update.effective_chat.id

    thread_id = None
    if update.effective_chat.is_forum:
        thread_id = update.effective_message.message_thread_id
        if thread_id == 1:
            thread_id = None

    if chat_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.discard(chat_id)
        await update.message.reply_text(
            f"🛑 *Quiz session rok diya gaya.*\n\n"
            f"Dobara shuru karne ke liye `/quiz 10` bhejo.\n\n"
            f"📚 Powered by {BRAND_NAME}",
            parse_mode="Markdown",
            message_thread_id=thread_id,
        )
    else:
        await update.message.reply_text(
            "⚠️ Koi active quiz session nahi chal raha.\n"
            "Start karne ke liye `/quiz 10` bhejo.",
            parse_mode="Markdown",
            message_thread_id=thread_id,
        )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable set karo.")

    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("chapters", chapters))
    app.add_handler(CommandHandler("getids", getids))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("stop", stop_quiz))
    app.add_handler(PollAnswerHandler(poll_answer_handler))

    logger.info("Bot start ho raha hai...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
