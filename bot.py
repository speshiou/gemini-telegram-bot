import traceback
import logging
import html
import json

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from telegram import (
    BotCommand, 
    Update, 
)

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from telegram.constants import ParseMode

import google.generativeai as genai

import config
import gemini_utils

BOT_COMMANDS = [
    BotCommand("reset", "clear the chat history"),
]

genai.configure(api_key=config.GOOGLE_AI_API_KEY)

async def app_post_init(application: Application) -> None:
    # setup bot commands
    await application.bot.set_my_commands(BOT_COMMANDS)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hi! I'm an AI chatbot powered by Gemini Pro Vision model. Feel free to ask me anything.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # send typing action
    await update.effective_chat.send_action(action="typing")

    model = genai.GenerativeModel(gemini_utils.MODEL_GEMINI_PRO)
    message = update.message.text
    response = model.generate_content(message)
    await update.message.reply_text(response.text)

async def reset_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    if config.DEVELOPER_CHAT_ID:
        # Finally, send the message

        try:
            await context.bot.send_message(
                chat_id=config.DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Failed to send the bugreport: {e}")

def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(app_post_init)
        .build()
    )

    # add handlers
    if not config.ALLOWED_TELEGRAM_USERNAMES or len(config.ALLOWED_TELEGRAM_USERNAMES) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.ALLOWED_TELEGRAM_USERNAMES)

    application.add_handler(CommandHandler("start", start_handler, filters=user_filter))
    application.add_handler(CallbackQueryHandler(reset_command_handler, pattern="^reset"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handler))
    application.add_error_handler(error_handler)
    
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()