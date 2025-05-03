**Note:** This project has primarily been tested on Linux (specifically the environment where the `prebuilt/telegram-bot-api` binary runs). While it might work on other operating systems (like Windows or macOS) if you provide the correct `telegram-bot-api` binary, full compatibility is not guaranteed. If you encounter issues on other OSes or wish to see official support, please open an issue or consider contributing!

# TikTok Video Downloader Bot

A Telegram bot designed to download TikTok videos without watermarks, utilizing the TikWM API. It can also download audio tracks and fetch basic user information.

## Features

*   Download TikTok videos in HD or SD quality without watermarks.
*   Extract and download the audio track from a TikTok video.
*   Retrieve basic profile information for a TikTok user.
*   Handles direct TikTok links sent to the bot (defaults to HD download).
*   Supports using a local Telegram Bot API server for increased reliability and **file size limits (up to 2GB)**.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/huythedev/tiktok_telegram_bot
    cd tiktok_telegram_bot
    ```

2.  **Create a `.env` file:**
    Copy the `.env_example` file to `.env` in the project's root directory and add your Telegram API credentials:
    ```bash
    cp .env_example .env
    # Now edit the .env file
    ```
    ```dotenv
    # Contents of .env
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_API_ID="YOUR_TELEGRAM_API_ID" # Needed for local API server
    TELEGRAM_API_HASH="YOUR_TELEGRAM_API_HASH" # Needed for local API server

    # Optional: If using a local Telegram Bot API server, uncomment and set the URL
    # LOCAL_BOT_API_URL="http://localhost:8081/bot"

    # Optional: Path to the local Telegram Bot API server binary (if different from default)
    # API_BINARY="path/to/your/telegram-bot-api"
    ```
    *   Replace `"YOUR_TELEGRAM_BOT_TOKEN"` with the token obtained from BotFather.
    *   Replace `"YOUR_TELEGRAM_API_ID"` and `"YOUR_TELEGRAM_API_HASH"` with your credentials from [my.telegram.org](https://my.telegram.org/apps). These are needed *only* if you plan to run the local Bot API server using `start.py`.
    *   If you want to use a local Telegram Bot API server (recommended for stability and larger file uploads), uncomment `LOCAL_BOT_API_URL` and ensure it points to your running server (default is `http://localhost:8081/bot`).
    *   The `API_BINARY` variable points to the location of the Telegram Bot API server executable used by `start.py`. The default assumes it's in the `prebuilt` directory.

3.  **Install dependencies:**
    Make sure you have Python 3.8+ installed. Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

4.  **(Optional) Obtain Local Telegram Bot API Server:**
    To run the local server using `start.py`, you need the `telegram-bot-api` binary. Place the executable in the `prebuilt` directory (or update the `API_BINARY` path in `.env`). Ensure the binary is executable (e.g., `chmod +x prebuilt/telegram-bot-api` on Linux/macOS).

    *   **Linux (x86_64):** Download the latest prebuilt binary from [huythedev/telegram-bot-api-prebuilt_for-linux](https://github.com/huythedev/telegram-bot-api-prebuilt_for-linux/releases/latest).
    *   **Windows:** Download the latest prebuilt binary from [std-microblock/tg-botapi-build](https://github.com/std-microblock/tg-botapi-build/releases/latest).
    *   **macOS:** Download the latest prebuilt binary from [huythedev/telegram-bot-api-prebuilt_for-macos](https://github.com/huythedev/telegram-bot-api-prebuilt_for-macos/releases/latest).
    *   **Other Architectures or Untrusted Builds:** You will need to build the binary yourself. Follow the official build instructions: [https://tdlib.github.io/telegram-bot-api/build.html](https://tdlib.github.io/telegram-bot-api/build.html).

    **Important:** After downloading *any* prebuilt binary (from the links above or if you build it yourself), ensure it's placed in the correct location. By default, the `start.py` script looks for `prebuilt/telegram-bot-api`. If you place it elsewhere or name it differently, you **must** update the `API_BINARY` variable in your `.env` file accordingly. Also, remember to make the downloaded binary executable (e.g., `chmod +x prebuilt/telegram-bot-api` or `chmod +x path/to/your/binary`).

5.  **Run the bot:**

    *   **Option A: Using Telegram's public API servers (Simpler, smaller file limits):**
        ```bash
        python bot.py
        ```
        *(Make sure `LOCAL_BOT_API_URL` is commented out or removed in your `.env` file)*

    *   **Option B: Using a local Telegram Bot API server (Recommended, 2GB file limit):**
        This script starts both the local API server and the bot script, monitoring and restarting them if they crash.
        ```bash
        python start.py
        ```
        *(Make sure `LOCAL_BOT_API_URL` is uncommented and correctly set in your `.env` file. Also ensure `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set.)*

## Usage

Interact with the bot on Telegram using the following commands:

*   `/start`: Displays a welcome message and lists available commands.
*   `/getvideo <tiktok_link> [hd/sd]`: Downloads the video from the link. Defaults to `hd` if quality is not specified.
    *   Example HD: `/getvideo https://www.tiktok.com/@user/video/123 hd`
    *   Example SD: `/getvideo https://www.tiktok.com/@user/video/123 sd`
    *   Example (default HD): `/getvideo https://www.tiktok.com/@user/video/123`
*   `/sd <tiktok_link>`: Shortcut to download the video in SD quality.
    *   Example: `/sd https://www.tiktok.com/@user/video/123`
*   `/mp3 <tiktok_link>`: Downloads the audio track from the video.
    *   Example: `/mp3 https://www.tiktok.com/@user/video/123`

You can also simply send a TikTok video link directly to the bot, and it will attempt to download the HD version.

## Note

*   This bot relies on the third-party TikWM API (`https://www.tikwm.com`). Its functionality depends on the availability and terms of service of this API.
*   Using a local Telegram Bot API server significantly increases the maximum file size the bot can send (from 50MB to 2GB).

## Contact

For quick support or questions, you can reach out on Discord: https://discord.com/users/929735117117730828
