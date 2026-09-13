import json
import os
import random
import logging
from dotenv import load_dotenv
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crystalcoderz dataset load karo
with open("questions.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]

# A/B/C/D ko 0-3 index mein convert karo
LETTER_MAP = {"A": 0, "B": 1, "C": 2, "D": 3}


def convert_question(q):
    """Crystalcoderz format ko Telegram poll format mein badlo."""
    options_dict = q["options"]
    # options ko list banao A, B, C, D order mein
    options_list = [
        options_dict.get("A", ""),
        options_dict.get("B", ""),
        options_dict.get("C", ""),
        options_dict.get("D", "")
    ]
    # answer letter ko index mein badlo
    answer_index = LETTER_MAP.get(q["answer"].strip().upper(), 0)
    
    return {
        "question": q["question"],
        "options": options_list,
        "answer": answer_index,
        "chapter": q.get("chapter", "Unknown")
    }


# Saare questions convert karo shuru mein hi
CONVERTED = [convert_question(q) for q in QUESTIONS]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! NEET Quiz Bot mein swagat.\n\n"
        "/quiz - Random NEET Biology question\n"
        "/quiz <chapter> - Us chapter ka question\n"
        "/chapters - Saare chapters ki list\n"
        "/help - Madad"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/quiz - Random question\n"
        "/quiz The Living World - Chapter wise question\n"
        "/chapters - Chapter list\n\n"
        "Bot ko group mein Admin banao aur BotFather mein Group Privacy OFF karo."
    )


async def chapters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chapters_set = set(q["chapter"] for q in CONVERTED)
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    await update.message.reply_text(f"Available Chapters:\n{chapters_list}")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CONVERTED:
        await update.message.reply_text("Question bank khaali hai.")
        return

    # Agar chapter diya hai toh filter karo
    if context.args:
        chapter_name = " ".join(context.args)
        filtered = [q for q in CONVERTED if q["chapter"].lower() == chapter_name.lower()]
        if not filtered:
            await update.message.reply_text(f"'{chapter_name}' chapter mein koi question nahi mila. /chapters se list dekho.")
            return
        q = random.choice(filtered)
    else:
        q = random.choice(CONVERTED)

    await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=q["question"],
        options=q["options"],
        type=Poll.QUIZ,
        correct_option_id=q["answer"],
        is_anonymous=False,
    )


def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN environment variable set karo.")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("chapters", chapters))
    app.add_handler(CommandHandler("quiz", quiz))
    
    logger.info("Bot start ho raha hai...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
