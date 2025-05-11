#!/usr/bin/env python3
# bot.py

import os
import tempfile
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)
from merge_fit_gpx import merge

# состояния разговора
FIT, GPX = range(2)

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Привет! Пришлите сначала FIT-файл тренировки."
    )
    return FIT

def receive_fit(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc.file_name.lower().endswith('.fit'):
        update.message.reply_text(
            "Это не .fit файл. Пожалуйста, пришлите именно FIT-файл."
        )
        return FIT

    file = doc.get_file()
    tmp = tempfile.NamedTemporaryFile(suffix=".fit", delete=False)
    file.download(custom_path=tmp.name)
    context.user_data['fit'] = tmp.name

    update.message.reply_text("Получил FIT. Теперь пришлите GPX-трек.")
    return GPX

def receive_gpx(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc.file_name.lower().endswith('.gpx'):
        update.message.reply_text(
            "Это не .gpx файл. Пожалуйста, пришлите именно GPX-трек."
        )
        return GPX

    file = doc.get_file()
    tmp = tempfile.NamedTemporaryFile(suffix=".gpx", delete=False)
    file.download(custom_path=tmp.name)
    context.user_data['gpx'] = tmp.name

    out_path = tempfile.NamedTemporaryFile(suffix=".gpx", delete=False).name
    try:
        fit_duration, gpx_duration = merge(
            context.user_data['fit'],
            context.user_data['gpx'],
            out_path
        )
        with open(out_path, 'rb') as f:
            update.message.reply_document(f, filename="merged.gpx")
    except Exception as e:
        update.message.reply_text(f"Ошибка при объединении: {e}")

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("Ошибка: не задана переменная окружения TELEGRAM_TOKEN", flush=True)
        return

    updater = Updater(token)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIT:  [MessageHandler(Filters.document, receive_fit)],
            GPX:  [MessageHandler(Filters.document, receive_gpx)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
