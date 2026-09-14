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

# questions.json load karo
with open("questions.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

QUESTIONS = DATA["questions"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Namaste! NEET Quiz Bot mein swagat.\n\n"
        "/quiz - Random NEET question\n"
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
    chapters_set = set(q["chapter"] for q in QUESTIONS)
    chapters_list = "\n".join(f"• {c}" for c in sorted(chapters_set))
    if len(chapters_list) > 4000:
        chapters_list = chapters_list[:4000] + "\n...(aur bhi hain)"
    await update.message.reply_text(f"Available Chapters:\n{chapters_list}")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not QUESTIONS:
        await update.message.reply_text("Question bank khaali hai.")
        return

    if context.args:
        chapter_name = " ".join(context.args).lower()
        filtered = [q for q in QUESTIONS if q.get("chapter", "").lower() == chapter_name]
        if not filtered:
            await update.message.reply_text(
                f"'{' '.join(context.args)}' chapter mein koi question nahi mila. /chapters se list dekho."
            )
            return
        q = random.choice(filtered)
    else:
        q = random.choice(QUESTIONS)

    options = q["options"]
    answer = q["answer"]

    await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=q["question"][:300],  # Telegram limit 300 chars
        options=[opt[:100] for opt in options],  # Telegram limit 100 chars per option
        type=Poll.QUIZ,
        correct_option_id=answer,
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
    
