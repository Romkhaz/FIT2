import os
import tempfile
from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
)
from merge_fit_gpx import merge

# Состояния ожидания файлов
FIT, GPX = range(2)

def start(update: Update, ctx: CallbackContext):
    update.message.reply_text(
        "Привет! Пришлите сначала FIT-файл тренировки."
    )
    return FIT

def receive_fit(update: Update, ctx: CallbackContext):
    f = update.message.document.get_file()
    tmp = tempfile.NamedTemporaryFile(suffix=".fit", delete=False)
    f.download(custom_path=tmp.name)
    ctx.user_data['fit'] = tmp.name
    update.message.reply_text("Получил FIT. Теперь пришлите GPX-трек.")
    return GPX

def receive_gpx(update: Update, ctx: CallbackContext):
    g = update.message.document.get_file()
    tmp = tempfile.NamedTemporaryFile(suffix=".gpx", delete=False)
    g.download(custom_path=tmp.name)
    ctx.user_data['gpx'] = tmp.name

    out_path = tempfile.NamedTemporaryFile(suffix=".gpx", delete=False).name
    try:
        merge(ctx.user_data['fit'], ctx.user_data['gpx'], out_path)
        with open(out_path, 'rb') as f:
            update.message.reply_document(f, filename="merged.gpx")
    except Exception as e:
        update.message.reply_text(f"Ошибка при объединении: {e}")
    return ConversationHandler.END

def cancel(update: Update, ctx: CallbackContext):
    update.message.reply_text("Отменено.")
    return ConversationHandler.END

def main():
    token = os.environ['TELEGRAM_TOKEN']
    updater = Updater(token)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIT: [MessageHandler(Filters.document.mime_type("application/octet-stream"), receive_fit)],
            GPX: [MessageHandler(Filters.document.mime_type("application/gpx+xml"), receive_gpx)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(conv)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
