import traceback
import logging
import html
import json
from pathlib import Path

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
import telegram_utils
from datastore import Datastore

BOT_COMMANDS = [
    BotCommand("reset", "clear the chat history"),
]

genai.configure(api_key=config.GOOGLE_AI_API_KEY)

datastore: Datastore = Datastore()

async def app_post_init(application: Application) -> None:
    # setup bot commands
    await application.bot.set_my_commands(BOT_COMMANDS)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    datastore.upsert_chat(chat_id=update.effective_chat.id)
    await update.message.reply_text("Hi! I'm an AI chatbot powered by Gemini Pro Vision model. Feel free to ask me anything.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    datastore.upsert_chat(chat_id=update.effective_chat.id)
    # send typing action
    await update.effective_chat.send_action(action="typing")

    model_name = gemini_utils.MODEL_GEMINI_PRO
    photo_path: Path = None
    new_message = update.message.text

    # when replying to a photo
    if update.effective_message.reply_to_message and update.effective_message.reply_to_message.photo:
        # download the photo to the tmp dir
        photo_size = telegram_utils.get_largest_photo_size(update.effective_message.reply_to_message.photo)
        photo_file = await context.bot.get_file(photo_size.file_id)
        photo_path = Path('/tmp/images').joinpath(photo_file.file_unique_id)
        if not photo_path.exists():
            await photo_file.download_to_drive(photo_path)
        # Telegram always compresses photos to the jpeg format
        img = {
            'mime_type': 'image/jpeg',
            'data': photo_path.read_bytes()
        }
        content = [new_message, img]
        # switch to the vision model to handle the image
        model_name = gemini_utils.MODEL_GEMINI_PRO_VISION
    else:
        content = new_message

    # fetch the chat history
    chat_history = datastore.get_chat_history(chat_id=update.effective_chat.id)
    history = gemini_utils.build_history(raw_history=chat_history)

    model = genai.GenerativeModel(model_name)
    # load the chat history
    chat = model.start_chat(history=history)
    new_model_message = ""
    try:
        response = await chat.send_message_async(content, stream=True)
        placeholder = await update.message.reply_text("...")
        # stream the response
        async for chunk in response:
            new_model_message += chunk.text
            await placeholder.edit_text(new_model_message)
    except Exception as e:
        logger.error(f"Exception: {e}")
    finally:
        if new_model_message:
            # persist chat history
            datastore.push_chat_history(
                chat_id=update.effective_chat.id, 
                user_message=new_message,
                model_message=new_model_message,
                num_max_history=config.CHAT_HISTORY_LIMIT if len(chat_history) + 1 >= config.CHAT_HISTORY_LIMIT else -1
            )

async def reset_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    datastore.upsert_chat(chat_id=update.effective_chat.id)
    if update.callback_query:
        query = update.callback_query
        await query.answer()

    datastore.clear_chat_history(chat_id=update.effective_chat.id)
    await update.message.reply_text("Cleared chat history!")

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
    application.add_handler(CommandHandler("reset", reset_command_handler, filters=user_filter))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handler))
    application.add_error_handler(error_handler)
    
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()