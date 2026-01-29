import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# admin_message_id -> user_id
admin_msg_to_user = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напишите заявку — я передам администратору. Ответ придёт сюда.")

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # админские сообщения сюда не отправляем (их обработает admin_reply)
    if update.effective_user and update.effective_user.id == ADMIN_ID:
        return

    user = update.effective_user

    header = f"Заявка от {user.full_name} (id={user.id}, @{user.username or '—'}):"
    h = await context.bot.send_message(chat_id=ADMIN_ID, text=header)

    # копируем само сообщение (текст/фото/файл и т.д.)
    copied = await update.message.copy(chat_id=ADMIN_ID)

    # админ может отвечать реплаем на header или на copied — сохраняем оба
    admin_msg_to_user[h.message_id] = user.id
    admin_msg_to_user[copied.message_id] = user.id

    await update.message.reply_text("Заявка отправлена. Ожидайте ответ.")

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь реплаем на сообщение заявки, чтобы я понял, кому отправлять.")
        return

    replied_id = update.message.reply_to_message.message_id
    user_id = admin_msg_to_user.get(replied_id)

    if not user_id:
        await update.message.reply_text("Не нашёл получателя. Ответь реплаем на header/сообщение заявки, которое прислал бот.")
        return

    # отправляем пользователю текст ответа админа
    if update.message.text:
        await context.bot.send_message(chat_id=user_id, text=update.message.text)
    else:
        # если админ прислал не текст (фото/файл) — тоже отправим копией
        await update.message.copy(chat_id=user_id)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")
    if ADMIN_ID == 0:
        raise RuntimeError("ADMIN_ID is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # Ответы админа (в ЛС боту) — только если это reply
    app.add_handler(MessageHandler(filters.User(ADMIN_ID) & filters.ALL, admin_reply))

    # Заявки от пользователей
    app.add_handler(MessageHandler(~filters.User(ADMIN_ID) & filters.ALL, forward_to_admin))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
