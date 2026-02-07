import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    CallbackQueryHandler,
    ConversationHandler
)
from yt_dlp import YoutubeDL

# --- RENDER KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIG ---
TOKEN = '8403074672:AAF2LtFG571mt-lY1VcVtHOCtYMSof5aLmg'
CHOOSING, DOWNLOADING = range(2)

U_WAVE = "\U0001F44B"
U_VIDEO = "\U0001F3AC"
U_MUSIC = "\U0001F3B5"
U_PHOTO = "\U0001F4F8"
U_LINK = "\U0001F517"
U_WAIT = "\U000023F3"
U_CHECK = "\U00002705"
U_ERROR = "\U0000274C"
U_ROCKET = "\U0001F680"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"{U_VIDEO} Video (No Logo)", callback_data='video')],
        [InlineKeyboardButton(f"{U_MUSIC} Music (MP3)", callback_data='music')],
        [InlineKeyboardButton(f"{U_PHOTO} Photos (Album)", callback_data='photo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"{U_WAVE} **TikTok Downloader**\nဘာကို ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ? အရင်ရွေးပေးပါဗျာ။"
    
    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return CHOOSING

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['choice'] = query.data
    await query.edit_message_text(f"{U_ROCKET} **Selected: {query.data.upper()}**\n{U_LINK} TikTok Link ကို ပို့ပေးပါဗျာ။", parse_mode='Markdown')
    return DOWNLOADING

async def download_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    choice = context.user_data.get('choice')

    if "tiktok.com" not in url:
        await update.message.reply_text(f"{U_ERROR} Link မှားနေပါတယ်။")
        return DOWNLOADING

    status_msg = await update.message.reply_text(f"{U_WAIT} ဒေါင်းလုဒ်ဆွဲနေပါပြီ...")

    try:
        # ပုံအတွက် သီးသန့်စစ်ဆေးခြင်း
        if choice == 'photo':
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                image_urls = []
                if 'entries' in info:
                    image_urls = [e['url'] for e in info['entries'] if 'url' in e]
                elif info.get('thumbnails'):
                    image_urls = [info['thumbnails'][-1]['url']]

                if image_urls:
                    media_group = [InputMediaPhoto(media=img_url) for img_url in image_urls[:10]]
                    await update.message.reply_media_group(media=media_group)
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("ပုံရှာမတွေ့ပါ")
            return await start(update, context)

        # Video နှင့် Music အတွက်
        ydl_opts = {
            'format': 'best', # အဆင်ပြေဆုံး format ကို ယူရန်
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

            if choice == 'video':
                await update.message.reply_video(video=open(file_path, 'rb'), caption=f"{U_CHECK} Done!")
            
            elif choice == 'music':
                # အသံဖိုင်အဖြစ် ပြောင်းလဲခြင်း
                audio_path = file_path.rsplit('.', 1)[0] + ".mp3"
                os.rename(file_path, audio_path)
                await update.message.reply_audio(audio=open(audio_path, 'rb'), caption=f"{U_MUSIC} Done!")
                file_path = audio_path

            if os.path.exists(file_path): os.remove(file_path)
            await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"{U_ERROR} အမှားအယွင်း ရှိပါသည်- ဗီဒီယိုက Private ဖြစ်နေနိုင်သလို Link မမှန်တာလည်း ဖြစ်နိုင်ပါတယ်။")
    
    return await start(update, context)

def main():
    if not os.path.exists('downloads'): os.makedirs('downloads')
    threading.Thread(target=run_web, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_click)],
            DOWNLOADING: [MessageHandler(filters.TEXT & ~filters.COMMAND, download_process)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()

