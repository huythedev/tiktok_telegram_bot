import logging
import os
from telegram import Update, error, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
import io

# Cấu hình logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env in the current directory
# Add override=True to prioritize .env variables over system variables
load_dotenv(override=True)

# Get environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

# Local Bot API server URL (with /bot prefix)
ENV_LOCAL_BOT_API_URL = os.getenv("LOCAL_BOT_API_URL")  # Read the specific variable from .env

# API TikWM endpoints và domain
TIKWM_API_URL = "https://www.tikwm.com/api/"
TIKWM_USER_INFO_URL = "https://www.tikwm.com/api/user/info/"
TIKWM_BASE_URL = "https://www.tikwm.com"

# Hàm ghép URL tương đối thành tuyệt đối
def make_absolute_url(relative_url):
    if relative_url.startswith('/'):
        return TIKWM_BASE_URL + relative_url
    return relative_url

# Hàm gọi API TikWM với retry logic
def call_tikwm_api(url, params, max_retries=3, timeout=30):
    default_params = {"count": 12, "cursor": 0, "web": 1}
    params = {**default_params, **params}
    logger.info(f"Calling TikWM API: {url} with params: {params}")
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    try:
        response = session.post(
            url,
            data=params,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"TikWM API response: {data}")
        return data
    except requests.exceptions.Timeout:
        logger.error("Request to TikWM timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling TikWM API: {str(e)}")
        return None

# Helper function to download content
def download_content(url, timeout=60):
    logger.info(f"Attempting to download content from: {url}")
    try:
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        content_type = response.headers.get('content-type')
        logger.info(f"Downloaded content with type: {content_type}")
        content = response.content
        logger.info(f"Successfully downloaded {len(content)} bytes.")
        return content
    except requests.exceptions.Timeout:
        logger.error(f"Timeout downloading content from {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading content from {url}: {str(e)}")
        return None

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào! Gửi link video TikTok để tải video không watermark.\n"
        "Các lệnh hỗ trợ:\n"
        "/getvideo <link> [hd/sd] - Tải video TikTok (HD hoặc SD)\n"
        "/sd <link> - Tải video chất lượng SD\n"
        "/mp3 <link> - Tải audio từ video"
    )

# Lệnh /getvideo
async def getvideo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng cung cấp link TikTok. Ví dụ: /getvideo https://www.tiktok.com/@user/video/123 hd")
        return
    url = context.args[0]
    quality = context.args[1].lower() if len(context.args) > 1 else "hd"
    if quality not in ["hd", "sd"]:
        await update.message.reply_text("Chất lượng không hợp lệ. Vui lòng chọn 'hd' hoặc 'sd'.")
        return
    await update.message.reply_text(f"Đang xử lý link (chất lượng {quality.upper()}), vui lòng chờ...")
    response = call_tikwm_api(TIKWM_API_URL, {"url": url, "hd": 1 if quality == "hd" else 0})
    if not response or response.get("code") != 0:
        await update.message.reply_text("Không thể lấy thông tin video. Vui lòng kiểm tra link!")
        return
    data = response["data"]
    video_url_key = "hdplay" if quality == "hd" else "play"
    relative_video_url = data.get(video_url_key)

    if not relative_video_url:
        await update.message.reply_text(f"Không tìm thấy link video chất lượng {quality.upper()}.")
        return

    video_url = make_absolute_url(relative_video_url)
    await update.message.reply_text(f"Đã lấy link, đang tải video ({quality.upper()})...")

    video_content = download_content(video_url)

    if video_content:
        try:
            await update.message.reply_video(
                video=InputFile(io.BytesIO(video_content), filename=f"tiktok_video_{data.get('id', 'unknown')}.mp4"),
                caption=f"Video TikTok ({quality.upper()}) via TikWM.",
                write_timeout=300
            )
        except error.TelegramError as e:
            logger.error(f"TelegramError sending video: {e}")
            if isinstance(e, error.TimedOut):
                await update.message.reply_text(f"Lỗi: Quá thời gian khi tải video lên Telegram ({len(video_content)/(1024*1024):.2f} MB).")
            elif "Request Entity Too Large" in str(e) or "FILE_TOO_LARGE" in str(e):
                 await update.message.reply_text(f"Lỗi: Video quá lớn để gửi qua Telegram ({len(video_content)/(1024*1024):.2f} MB).")
            else:
                 await update.message.reply_text(f"Lỗi khi gửi video: {e}")
        except Exception as e:
             logger.error(f"Unexpected error sending video: {e}")
             await update.message.reply_text("Lỗi không xác định khi gửi video.")
    else:
        await update.message.reply_text("Không thể tải nội dung video từ link đã lấy. Có thể link đã hết hạn hoặc có lỗi.")

# Lệnh /sd
async def sd_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng cung cấp link TikTok. Ví dụ: /sd https://www.tiktok.com/@user/video/123")
        return
    url = context.args[0]
    await update.message.reply_text("Đang xử lý link (chất lượng SD), vui lòng chờ...")
    response = call_tikwm_api(TIKWM_API_URL, {"url": url, "hd": 0})
    if not response or response.get("code") != 0:
        await update.message.reply_text("Không thể lấy thông tin video. Vui lòng kiểm tra link!")
        return
    data = response["data"]
    relative_video_url = data.get("play")

    if not relative_video_url:
        await update.message.reply_text("Không tìm thấy link video chất lượng SD.")
        return

    video_url = make_absolute_url(relative_video_url)
    await update.message.reply_text("Đã lấy link, đang tải video (SD)...")

    video_content = download_content(video_url)

    if video_content:
        try:
            await update.message.reply_video(
                video=InputFile(io.BytesIO(video_content), filename=f"tiktok_video_{data.get('id', 'unknown')}_sd.mp4"),
                caption="Video TikTok (SD) via TikWM.",
                write_timeout=300
            )
        except error.TelegramError as e:
            logger.error(f"TelegramError sending SD video: {e}")
            if isinstance(e, error.TimedOut):
                await update.message.reply_text(f"Lỗi: Quá thời gian khi tải video lên Telegram ({len(video_content)/(1024*1024):.2f} MB).")
            elif "Request Entity Too Large" in str(e) or "FILE_TOO_LARGE" in str(e):
                 await update.message.reply_text(f"Lỗi: Video quá lớn để gửi qua Telegram ({len(video_content)/(1024*1024):.2f} MB).")
            else:
                 await update.message.reply_text(f"Lỗi khi gửi video: {e}")
        except Exception as e:
             logger.error(f"Unexpected error sending SD video: {e}")
             await update.message.reply_text("Lỗi không xác định khi gửi video.")
    else:
        await update.message.reply_text("Không thể tải nội dung video (SD) từ link đã lấy.")

# Lệnh /mp3
async def mp3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Vui lòng cung cấp link TikTok. Ví dụ: /mp3 https://www.tiktok.com/@user/video/123")
        return
    url = context.args[0]
    await update.message.reply_text("Đang xử lý audio, vui lòng chờ...")
    response = call_tikwm_api(TIKWM_API_URL, {"url": url, "music": 1})
    if not response or response.get("code") != 0:
        await update.message.reply_text("Không thể tải audio. Vui lòng kiểm tra link!")
        return
    data = response["data"]
    audio_url = make_absolute_url(data.get("music"))
    if audio_url:
        try:
            await update.message.reply_audio(audio=audio_url, caption="Audio from TikTok via TikWM.")
        except error.TelegramError as e:
            logger.error(f"TelegramError sending audio: {e}")
            await update.message.reply_text(f"Lỗi khi gửi audio: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending audio: {e}")
            await update.message.reply_text("Lỗi không xác định khi gửi audio.")
    else:
        await update.message.reply_text("Không thể tải audio. Vui lòng kiểm tra link!")

# Xử lý khi người dùng gửi link TikTok trực tiếp (tải video HD)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and ("tiktok.com" in text) and not text.startswith(('/start', '/getvideo', '/sd', '/mp3')):
        await update.message.reply_text("Đang xử lý link (chất lượng HD), vui lòng chờ...")
        response = call_tikwm_api(TIKWM_API_URL, {"url": text, "hd": 1})
        if not response or response.get("code") != 0:
            await update.message.reply_text("Không thể lấy thông tin video. Vui lòng kiểm tra link!")
            return
        data = response["data"]
        relative_video_url = data.get("hdplay")

        if not relative_video_url:
            await update.message.reply_text("Không tìm thấy link video chất lượng HD.")
            return

        video_url = make_absolute_url(relative_video_url)
        await update.message.reply_text("Đã lấy link, đang tải video (HD)...")

        video_content = download_content(video_url)

        if video_content:
            try:
                await update.message.reply_video(
                    video=InputFile(io.BytesIO(video_content), filename=f"tiktok_video_{data.get('id', 'unknown')}_hd.mp4"),
                    caption="Video TikTok (HD) via TikWM.",
                    write_timeout=300
                )
            except error.TelegramError as e:
                logger.error(f"TelegramError sending HD video (direct link): {e}")
                if isinstance(e, error.TimedOut):
                    await update.message.reply_text(f"Lỗi: Quá thời gian khi tải video lên Telegram ({len(video_content)/(1024*1024):.2f} MB).")
                elif "Request Entity Too Large" in str(e) or "FILE_TOO_LARGE" in str(e):
                    await update.message.reply_text(f"Lỗi: Video quá lớn để gửi qua Telegram ({len(video_content)/(1024*1024):.2f} MB).")
                else:
                    await update.message.reply_text(f"Lỗi khi gửi video: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending HD video (direct link): {e}")
                await update.message.reply_text("Lỗi không xác định khi gửi video.")
        else:
            await update.message.reply_text("Không thể tải nội dung video (HD) từ link đã lấy.")

# Hàm xử lý lỗi
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")
    if update and update.message:
        await update.message.reply_text("Có lỗi xảy ra. Vui lòng thử lại sau!")

# Hàm chính để chạy bot
def main():
    # Kiểm tra biến môi trường
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, TELEGRAM_API_HASH]):
        logger.error("Missing required environment variables. Please check .env file or system environment.")
        logger.error(f"TELEGRAM_BOT_TOKEN: {'Set' if TELEGRAM_BOT_TOKEN else 'Not Set'}")
        logger.error(f"TELEGRAM_API_ID: {'Set' if TELEGRAM_API_ID else 'Not Set'}")
        logger.error(f"TELEGRAM_API_HASH: {'Set' if TELEGRAM_API_HASH else 'Not Set'}")
        return

    # Determine and log the Bot API URL source
    if ENV_LOCAL_BOT_API_URL:
        api_url_to_use = ENV_LOCAL_BOT_API_URL
        logger.info(f"Using Local API URL from LOCAL_BOT_API_URL in .env: {api_url_to_use}")
    else:
        api_url_to_use = "https://api.telegram.org/bot"
        logger.info(f"LOCAL_BOT_API_URL not set in .env, using default Telegram API: {api_url_to_use}")

    logger.info(f"Using Bot Token: {TELEGRAM_BOT_TOKEN[:10]}... (masked)")

    # Khởi tạo ứng dụng với determined API URL
    logger.info(f"Attempting to initialize application with API URL: {api_url_to_use}")
    try:
        application_builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
        if ENV_LOCAL_BOT_API_URL:
            application_builder = application_builder.base_url(api_url_to_use)

        application = application_builder.build()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Failed to build application with API URL '{api_url_to_use}': {e}")
        return

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getvideo", getvideo_command))
    application.add_handler(CommandHandler("sd", sd_command))
    application.add_handler(CommandHandler("mp3", mp3_command))
    application.add_handler(MessageHandler(filters.Text() & ~filters.Command(), handle_message))
    application.add_error_handler(error_handler)

    logger.info("Bot initialization sequence starting...")
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except error.InvalidToken as e:
        logger.error(f"Invalid Token Error: {e}")
        logger.error(f"The token was rejected by the server at '{api_url_to_use}'.")
        if ENV_LOCAL_BOT_API_URL:
            logger.error("If using Local API: Ensure your local Telegram Bot API server is running correctly.")
            logger.error(f"Verify it was started with the correct --api-id='{TELEGRAM_API_ID}' and --api-hash='{TELEGRAM_API_HASH}'.")
            logger.error("Check the local server's logs for more details.")
        else:
            logger.error("Ensure the BOT_TOKEN is correct and active.")
    except Exception as e:
        logger.error(f"An error occurred while running the bot: {e}")
        logger.error(f"Check network connectivity to '{api_url_to_use}' and server status/logs if applicable.")

if __name__ == '__main__':
    main()