    import asyncio
import json
import os
import random
import logging
import threading
import re
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
MAX_QUESTIONS = 100

# === SUBJECT WISE TIMING ===
SUBJECT_TIMING = {
    "Biology":   {"gap": 15, "poll_time": 15},
    "Chemistry": {"gap": 40, "poll_time": 40},
    "Physics":   {"gap": 20, "poll_time": 20},
}
DEFAULT_TIMING = {"gap": 20, "poll_time": 20}

# === THREAD IDs (per group, subject wise) ===
# None = General topic
THREAD_IDS = {
    -1004395462386: {
        "Chemistry": 2563,    # Chemistry → topic 2563
        "Biology": None,      # Biology → General
        "Physics": None,      # Physics → General
    },
}

# Fallback (jab group-specific entry na ho)
DEFAULT_THREAD_IDS = {
    "Physics": None,
    "Chemistry": None,
    "Biology": None,
}
# ================================

# === PROGRESS BAR ANIMATION STYLES ===
PROGRESS_STYLES = {
    "Biology":   {"emoji": "🧬", "color": "🟩", "empty": "⬜", "label": "Biology"},
    "Chemistry": {"emoji": "⚗️", "color": "🟧", "empty": "⬜", "label": "Chemistry"},
    "Physics":   {"emoji": "⚛️", "color": "🟦", "empty": "⬜", "label": "Physics"},
    "All":       {"emoji": "📚", "color": "🟪", "empty": "⬜", "label": "Chapters"},
}

# === 50 MOTIVATIONAL QUOTES ===
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

# === QUESTIONS LOAD ===
QUESTIONS = []

try:
    with open("questions.json", "r", encoding="utf-8") as f:
        bio_data = json.load(f)
        for q in bio_data["questions"]:
            q["subject"] = "Biology"
        QUESTIONS.extend(bio_data["questions"])
    logger.info(f"Biology: {len(bio_data['questions'])} questions loaded")
except Exception as e:
    logger.error(f"questions.json load error: {e}")

try:
    with open("chemistry.json", "r", encoding="utf-8") as f:
        chem_data = json.load(f)
        for q in chem_data["questions"]:
            q["subject"] = "Chemistry"
        QUESTIONS.extend(chem_data["questions"])
    logger.info(f"Chemistry: {len(chem_data['questions'])} questions loaded")
except Exception as e:
    logger.error(f"chemistry.json load error: {e}")

logger.info(f"TOTAL: {len(QUESTIONS)} questions loaded")
# =============================================

# === Active quiz sessions ===
ACTIVE_SESSIONS = {}
POLL_TRACKER = {}
# =========================================


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


def get_timing(subject):
    return SUBJECT_TIMING.get(subject, DEFAULT_TIMING)


def get_thread_id(chat_id, subject):
    """Per-group thread ID do; warna default."""
    group_threads = THREAD_IDS.get(chat_id, {})
    if subject in group_threads:
        return group_threads[subject]
    return DEFAULT_THREAD_IDS.get(subject, None)


def clean_text(text):
    """HTML tags, LaTeX aur extra spaces hata do."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\$[^$]*\$', '', text)
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def matches_filter(q, filter_text):
    filter_lower = filter_text.lower().strip()
    subject = q.get("subject", "").lower()
    chapter = q.get("chapter", "").lower()
    if filter_lower in subject:
        return True
    if filter_lower in chapter:
        return True
    return False


# ==== PROGRESS BAR ANIMATION ====

def build_progress_bar(percent, style, total_blocks=12):
    """Left-to-right fill hone wala progress bar."""
    filled = int((percent / 100) * total_blocks)
    empty = total_blocks - filled
    bar = style["color"] * filled + style["empty"] * empty

    if percent < 25:
        mood = "⏳"
    elif percent < 50:
        mood = "🔃"
    elif percent < 75:
        mood = "⚡"
    elif percent < 100:
        mood = "🚀"
    else:
        mood = "✅"

    return (
        f"{style['emoji']} <b>Loading {style['label']}...</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{mood} {bar} <b>{percent}%</b>\n"
        f"━━━━━━━━━━━━━━━"
    )


async def animate_loading(context, chat_id, thread_id, style_key, duration=2.5):
    """Loading animation message jo left->right fill hota hai."""
    style = PROGRESS_STYLES.get(style_key, PROGRESS_STYLES["All"])

    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=build_progress_bar(0, style),
            parse_mode="HTML",
            message_thread_id=thread_id,
        )
    except Exception as e:
        logger.warning(f"Loading msg fail: {e}")
        return None

    steps = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    delay = duration / len(steps)

    for pct in steps[1:]:
        await asyncio.sleep(delay)
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.message_id,
                text=build_progress_bar(pct, style),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.debug(f"Progress edit skip: {e}")

    await asyncio.sleep(0.4)

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
    except Exception:
        pass

    return msg


# ==== COMMAND HANDLERS ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎯 *{BRAND_NAME}* mein aapka swagat!\n"
        f"_{BRAND_TAGLINE}_\n\n"
        "📖 *Commands:*\n"
        "▫️ `/quiz 10` - 10 random questions\n"
        "▫️ `/quiz 10 mole` - Chapter wise quiz\n"
        "▫️ `/quiz 10 chemistry` - Chemistry questions\n"
        "▫️ `/quiz 10 biology` - Biology questions\n"
        "▫️ `/biology` - Biology chapters\n"
        "▫️ `/chemistry` - Chemistry chapters\n"
        "▫️ `/chapters` - All chapters\n"
        "▫️ `/stop` - Quiz rok do\n"
        "▫️ `/timing` - Subject timing\n"
        "▫️ `/help` - Madad\n\n"
        "⏱️ *Timing:*\n"
        "🧬 Biology: 15 sec\n"
        "⚗️ Chemistry: 40 sec\n\n"
        f"📚 Powered by {BRAND_NAME}",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n\n"
        "*Quiz commands:*\n"
        "`/quiz 10` - 10 random questions\n"
        "`/quiz 10 chemistry` - 10 Chemistry questions\n"
        "`/quiz 10 biology` - 10 Biology questions\n"
        "`/quiz 10 mole` - 10 questions mole chapter se\n"
        "`/quiz 50` - 50 questions\n\n"
        "*Chapter lists:*\n"
        "`/biology` - Biology chapters\n"
        "`/chemistry` - Chemistry chapters\n"
        "`/chapters` - Saare chapters\n\n"
        "*Others:*\n"
        "`/stop` - Quiz rok do\n"
        "`/timing` - Timing dekho\n\n"
        "✨ Chapter list load hote waqt *progress bar animation* dikhega!",
        parse_mode="Markdown"
    )


async def chapters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """All chapters - with loading animation."""
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    asyncio.create_task(
        animate_loading(context, chat_id, thread_id, "All", duration=2.5)
    )
    await asyncio.sleep(2.6)

    chapters_set = set(q.get("chapter", "Unknown") for q in QUESTIONS)
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"

    await update.message.reply_text(
        f"📚 *All Chapters:*\n\n{chapters_list}\n\n"
        f"📝 *Quiz ke liye:* `/quiz 10 chapter name`",
        parse_mode="Markdown"
    )


async def biology_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Biology command - sirf chapter list dikhaye."""
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    # Animation
    asyncio.create_task(
        animate_loading(context, chat_id, thread_id, "Biology", duration=2.5)
    )
    await asyncio.sleep(2.6)

    chapters_set = set(
        q.get("chapter", "Unknown")
        for q in QUESTIONS if q.get("subject") == "Biology"
    )
    if not chapters_set:
        await update.message.reply_text("❌ Biology ke questions nahi mile.")
        return
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"

    await update.message.reply_text(
        f"🧬 *Biology Chapters:*\n\n{chapters_list}\n\n"
        f"📝 *Quiz ke liye:* `/quiz 10` (random)\n"
        f"📖 *Chapter wise:* `/quiz 10 chapter name`\n"
        f"⏱️ Biology: 15 sec per question",
        parse_mode="Markdown"
    )


async def chemistry_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chemistry command - sirf chapter list dikhaye."""
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id

    asyncio.create_task(
        animate_loading(context, chat_id, thread_id, "Chemistry", duration=2.5)
    )
    await asyncio.sleep(2.6)

    chapters_set = set(
        q.get("chapter", "Unknown")
        for q in QUESTIONS if q.get("subject") == "Chemistry"
    )
    if not chapters_set:
        await update.message.reply_text("❌ Chemistry ke questions nahi mile.")
        return
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"

    await update.message.reply_text(
        f"⚗️ *Chemistry Chapters:*\n\n{chapters_list}\n\n"
        f"📝 *Quiz ke liye:* `/quiz 10` (random)\n"
        f"📖 *Chapter wise:* `/quiz 10 chapter name`\n"
        f"⏱️ Chemistry: 40 sec per question",
        parse_mode="Markdown"
    )


async def timing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "⏱️ *Subject-wise Timing:*\n\n"
    for subj, t in SUBJECT_TIMING.items():
        msg += f"• *{subj}:* {t['poll_time']} sec\n"
    msg += "\n📊 Poll ke saath circular timer dikhega!"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ==== QUIZ LOGIC ====

async def send_one_quiz(chat_id, context, q):
    options = [clean_text(o)[:100] for o in q["options"]]

    if len(options) != 4 or any(not o for o in options):
        return False

    question_text = clean_text(q["question"])[:300]
    if not question_text:
        return False

    answer = q.get("answer", 0)
    if not isinstance(answer, int) or answer < 0 or answer > 3:
        return False

    subject = q.get("subject", "Biology")
    thread_id = get_thread_id(chat_id, subject)
    timing = get_timing(subject)
    poll_time = timing["poll_time"]

    try:
        msg = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"🎯 {question_text}",
            options=options,
            type=Poll.QUIZ,
            correct_option_id=answer,
            is_anonymous=False,
            open_period=poll_time,
            message_thread_id=thread_id,
        )
        POLL_TRACKER[msg.poll.id] = {
            "chat_id": chat_id,
            "correct_option_id": answer,
            "thread_id": thread_id,
        }
        logger.info(f"Poll sent: {subject} | timer: {poll_time}s | thread: {thread_id}")
        return True
    except Exception as e:
        logger.error(f"Poll send error: {e}")
        return False


async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    args = context.args or []
    count = 1
    filter_text = None

    if args:
        if args[0].isdigit():
            count = int(args[0])
            if len(args) > 1:
                filter_text = " ".join(args[1:]).strip()
        else:
            filter_text = " ".join(args).strip()

    if count < 1:
        count = 1
    if count > MAX_QUESTIONS:
        count = MAX_QUESTIONS

    if filter_text:
        pool = [q for q in QUESTIONS if matches_filter(q, filter_text)]
        if not pool:
            await update.message.reply_text(
                f"❌ '{filter_text}' se koi question nahi mila.\n"
                f"/chapters se list dekho."
            )
            return
    else:
        pool = QUESTIONS

    if count == 1:
        for _ in range(5):
            q = random.choice(pool)
            if await send_one_quiz(chat_id, context, q):
                return
        await update.message.reply_text("Question bhejne mein problem aayi.")
        return

    await _start_quiz_session(update, context, pool, count, filter_text)


async def _start_quiz_session(update, context, pool, count, filter_text=None):
    chat_id = update.effective_chat.id

    if chat_id in ACTIVE_SESSIONS:
        await update.message.reply_text(
            "⚠️ Ek quiz session pehle se chal raha hai.\n"
            "Rokne ke liye /stop bhejo."
        )
        return

    ACTIVE_SESSIONS[chat_id] = True
    filter_msg = f"📖 {filter_text.title()}\n" if filter_text else ""

    await update.message.reply_text(
        f"🎯 *{BRAND_NAME}*\n\n"
        f"{filter_msg}"
        f"📝 {count} questions aa rahe hain...\n"
        f"⏱️ Subject ke hisaab se timer lagega.\n"
        f"🛑 Rokne ke liye /stop bhejo.\n\n"
        f"Apne answers ready rakho! 💪",
        parse_mode="Markdown"
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
                parse_mode="Markdown"
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
            if sent < count:
                subject = q.get("subject", "Biology")
                gap = get_timing(subject)["gap"]
                logger.info(f"Waiting {gap}s before next question...")
                for _ in range(gap):
                    if chat_id not in ACTIVE_SESSIONS:
                        await update.message.reply_text(
                            f"🛑 Quiz rok diya gaya.\n"
                         
