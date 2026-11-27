import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import telebot
from telebot import types

# ================== CONFIGURATION ==================
BOT_TOKEN = "9079668622:AAF8jxYFndoKDao4U7jNWcRlhRhGjhjWJlM"
BOT_USERNAME = "HodamaEwaa01Bot"          # '@' නැතුව
STORAGE_GROUP_ID = -5226449370              # Videos දාන group ID එක
UPDATE_CHANNEL_ID = -1005989625595          # Alert msg යවන channel ID එක

FIREBASE_DB_URL = "https://bot-blogger-91e08-default-rtdb.firebaseio.com"

IMGBB_API_KEY = "b6583ee2ba41977b23dac3ea95a28f7d"

GMAIL_ADDRESS = "chathumaldevinda15@gmail.com"
GMAIL_APP_PASSWORD = "dtxagmiwgmkfllhn"
BLOGGER_SECRET_EMAIL = "chathumaldevinda15.vidpost9842@blogger.com"

BLOG_URL = "https://sitenewphotohub.blogspot.com/"
# ===================================================

bot = telebot.TeleBot(BOT_TOKEN)


def _db_url(path: str) -> str:
    base = FIREBASE_DB_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}.json"


def get_next_vid_id() -> str:
    try:
        resp = requests.get(_db_url("videos"), timeout=15)
        data = resp.json()
        if isinstance(data, dict):
            # පවතින v<number> IDs බලා ඊළඟ අංකය ගන්නවා (delete කළත් duplicate නොවෙන්න)
            max_num = 0
            for key in data.keys():
                if isinstance(key, str) and key.startswith("v") and key[1:].isdigit():
                    num = int(key[1:])
                    if num > max_num:
                        max_num = num
            return f"v{max_num + 1}"
    except Exception as e:
        print("Firebase ID generation error:", e)
    return "v1"


def save_video(vid_id: str, file_id: str, title: str, thumb_url: str | None) -> None:
    payload = {
        "file_id": file_id,
        "title": title,
        "thumb_url": thumb_url,
    }
    resp = requests.put(_db_url(f"videos/{vid_id}"), json=payload, timeout=15)
    resp.raise_for_status()


def get_video(vid_id: str):
    try:
        resp = requests.get(_db_url(f"videos/{vid_id}"), timeout=15)
        data = resp.json()
        if isinstance(data, dict) and data.get("file_id"):
            return (
                data.get("file_id"),
                data.get("title", ""),
                data.get("thumb_url"),
            )
    except Exception as e:
        print("Firebase read error:", e)
    return None


def upload_thumb_to_imgbb(file_id: str) -> str | None:
    if not IMGBB_API_KEY or IMGBB_API_KEY == "YOUR_IMGBB_API_KEY":
        return None
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB_API_KEY},
            files={"image": ("thumb.jpg", downloaded, "image/jpeg")},
            timeout=30,
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]["url"]
        else:
            print("ImgBB API response error:", data)
    except Exception as e:
        print("ImgBB upload error:", e)
    return None


def send_blogger_post(title: str, bot_link: str, thumb_url: str | None = None) -> None:
    img_html = (
        f'<div style="margin:18px 0;border-radius:12px;overflow:hidden;border:1px solid #27272a;background:#09090b;">'
        f'<img src="{thumb_url}" alt="{title}" style="display:block;width:100%;max-height:420px;object-fit:cover;" />'
        f'</div>'
        if thumb_url
        else ""
    )

    html_body = f"""
    <div style="max-width:640px;margin:20px auto;padding:24px;background:#111114;color:#f4f4f5;border:1px solid #27272a;border-radius:16px;font-family:'Segoe UI',Arial,sans-serif;">
        <div style="display:inline-block;padding:4px 10px;font-size:12px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;color:#fb7185;background:rgba(225,29,72,0.14);border:1px solid rgba(225,29,72,0.35);border-radius:999px;">
            New Video Release
        </div>
        <h2 style="margin:12px 0 6px;font-size:22px;line-height:1.35;color:#ffffff;">
            {title}
        </h2>
        <p style="margin:0 0 14px;font-size:14px;line-height:1.6;color:#a1a1aa;">
            පහළ 4-Step Unlock Box එක සම්පූර්ණ කර Telegram video link එක ලබාගන්න.
        </p>
        {img_html}
        <div style="margin-top:16px;text-align:center;">
            <a href="{bot_link}" target="_blank" rel="noopener noreferrer"
               style="display:inline-block;width:100%;max-width:320px;box-sizing:border-box;padding:13px 22px;background:#e11d48;color:#ffffff;text-decoration:none;border-radius:10px;font-size:15px;font-weight:700;text-align:center;">
                ▶ Get Video on Telegram
            </a>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = title
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = BLOGGER_SECRET_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    app_pw = GMAIL_APP_PASSWORD.replace(" ", "")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(GMAIL_ADDRESS, app_pw)
            server.sendmail(GMAIL_ADDRESS, BLOGGER_SECRET_EMAIL, msg.as_string())
    except smtplib.SMTPServerDisconnected:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_ADDRESS, app_pw)
            server.sendmail(GMAIL_ADDRESS, BLOGGER_SECRET_EMAIL, msg.as_string())


@bot.message_handler(commands=["start"])
def handle_start(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2:
        vid_id = parts[1].strip()
        record = get_video(vid_id)
        if record:
            file_id, title, _ = record
            bot.send_video(message.chat.id, file_id, caption=title)
            return
        else:
            bot.send_message(message.chat.id, "මේ video link එක හමු නොවුණා හෝ කල් ඉකුත් වෙලා.")
            return

    bot.send_message(
        message.chat.id,
        "ආයුබෝවන්! අලුත් videos බලන්න අපේ channel එක සහ website එක check කරන්න.",
    )


@bot.message_handler(content_types=["video"])
def handle_group_video(message):
    if message.chat.id != STORAGE_GROUP_ID:
        return

    video = message.video
    title = (message.caption or "").strip() or f"Video Post ({video.file_unique_id})"
    vid_id = get_next_vid_id()
    bot_link = f"https://t.me/{BOT_USERNAME}?start={vid_id}"

    thumb_url = None
    if video.thumbnail:
        thumb_url = upload_thumb_to_imgbb(video.thumbnail.file_id)
    else:
        print("Warning: message.video.thumbnail is None")

    try:
        save_video(vid_id, video.file_id, title, thumb_url)
    except Exception as e:
        print("Firebase save error:", e)
        bot.reply_to(message, "❌ Firebase එකට save කරද්දී error එකක් ආවා.")
        return

    try:
        send_blogger_post(title, bot_link, thumb_url)
    except Exception as e:
        print("Blogger email error:", e)

    channel_text = (
        f"🆕 <b>අලුත් Post එකක් add වුණා!</b>\n\n"
        f"📌 <b>{title}</b>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🌐 Open Blogger Post", url=BLOG_URL),
    )

    try:
        if thumb_url:
            bot.send_photo(
                UPDATE_CHANNEL_ID,
                thumb_url,
                caption=channel_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
        else:
            bot.send_message(
                UPDATE_CHANNEL_ID,
                channel_text,
                parse_mode="HTML",
                reply_markup=markup,
            )
    except Exception as e:
        print("Channel post error:", e)

    bot.reply_to(message, f"✅ Process වුණා! ID: <code>{vid_id}</code>", parse_mode="HTML")


if __name__ == "__main__":
    print("Bot is running with Firebase Realtime Database...")
    bot.infinity_polling(skip_pending=True)
