import subprocess
import threading
import time
import os
import psutil
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

API_BINARY = os.getenv("API_BINARY", "prebuilt/telegram-bot-api")  # Default path to the executable in prebuilt folder
BOT_SCRIPT = "bot.py"
# Use API ID/Hash from environment variables, falling back to hardcoded values if not set
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "YOUR_TELEGRAM_API_ID") # Get from .env or use placeholder
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "YOUR_TELEGRAM_API_HASH") # Get from .env or use placeholder

# Global process handles and shutdown event
api_proc = None
bot_proc = None
shutdown_event = threading.Event()

# Log memory usage
def log_memory_usage():
    process = psutil.Process()
    mem_info = process.memory_info()
    print(f"Memory usage: RSS={mem_info.rss / 1024 / 1024:.2f} MB, VMS={mem_info.vms / 1024 / 1024:.2f} MB")

# Gather system information
print("Gathering system information...")
commands = [
    ("System info (uname)", ["uname", "-a"]),
    ("OS info (/etc/os-release)", ["cat", "/etc/os-release"]),
    ("Fallback info (/proc/version)", ["cat", "/proc/version"]),
    ("Shell info (sh)", ["sh", "--version"]),
    ("Directory listing (/etc)", ["ls", "-l", "/etc"])
]
for desc, cmd in commands:
    print(f"\n{desc}:")
    try:
        result = subprocess.run(cmd, check=False, text=True, capture_output=True)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"Command failed with exit code {result.returncode}")
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Log initial memory usage
log_memory_usage()

# Ensure the binary is executable
try:
    os.chmod(API_BINARY, 0o755)
except OSError as e:
    print(f"Failed to set permissions on {API_BINARY}: {e}")

# Function to monitor process output
def monitor_process(proc, name):
    while proc.poll() is None:
        line = proc.stdout.readline().strip()
        if line:
            print(f"{name} Output: {line}")
    exit_code = proc.poll()
    print(f"{name} process exited with code: {exit_code}")
    return exit_code

# Function to start and monitor API server with restart logic
def run_api_server():
    global api_proc
    while not shutdown_event.is_set():
        print("\nStarting Telegram Bot API server...")
        try:
            api_proc = subprocess.Popen(
                [API_BINARY, "--api-id", TELEGRAM_API_ID, "--api-hash", TELEGRAM_API_HASH, "--http-port", "8081", "-v", "2"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            print("Telegram API server started.")
        except FileNotFoundError:
            print(f"Binary not found: {API_BINARY}")
            shutdown_event.set()  # Signal other threads to stop
            break
        except Exception as e:
            print(f"Failed to start API server: {e}")
            api_proc = None  # Ensure proc is None if start failed
            if not shutdown_event.is_set():
                print("Retrying API server start in 5 seconds...")
                time.sleep(5)
                continue  # Retry starting
            else:
                break  # Exit if shutdown requested

        exit_code = monitor_process(api_proc, "API")
        api_proc = None  # Process finished or terminated

        if shutdown_event.is_set():
            print("API server shutdown requested.")
            break

        if exit_code == 0 or exit_code == -15:  # Normal exit or SIGTERM
            print("API server stopped normally.")
            break  # Don't restart on normal exit

        print(f"API server crashed with code {exit_code}. Restarting in 5 seconds...")
        time.sleep(5)
    print("API server thread finished.")
    api_proc = None  # Ensure it's None on exit

# Function to start and monitor Bot script with restart logic
def run_bot_script():
    global bot_proc
    while not shutdown_event.is_set():
        print("\nStarting Bot script...")
        try:
            bot_proc = subprocess.Popen(
                ["python3", BOT_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            print("Bot script started.")
        except FileNotFoundError:
            print(f"Bot script not found: {BOT_SCRIPT}")
            shutdown_event.set()  # Signal other threads to stop
            break
        except Exception as e:
            print(f"Failed to start Bot script: {e}")
            bot_proc = None  # Ensure proc is None if start failed
            if not shutdown_event.is_set():
                print("Retrying Bot script start in 5 seconds...")
                time.sleep(5)
                continue  # Retry starting
            else:
                break  # Exit if shutdown requested

        exit_code = monitor_process(bot_proc, "Bot")
        bot_proc = None  # Process finished or terminated

        if shutdown_event.is_set():
            print("Bot script shutdown requested.")
            break

        if exit_code == 0 or exit_code == -15:  # Normal exit or SIGTERM
            print("Bot script stopped normally.")
            break  # Don't restart on normal exit

        print(f"Bot script crashed with code {exit_code}. Restarting in 5 seconds...")
        time.sleep(5)
    print("Bot script thread finished.")
    bot_proc = None  # Ensure it's None on exit

# Start monitoring threads
print("Starting monitoring threads...")
api_thread = threading.Thread(target=run_api_server)
bot_thread = threading.Thread(target=run_bot_script)  # Use the new function
api_thread.start()
bot_thread.start()

# Check if the server is alive with curl (with retries)
print("\nChecking server status with curl...")
for attempt in range(3):
    time.sleep(3)
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8081"],
            check=False,
            text=True,
            capture_output=True
        )
        if result.stdout:
            print(f"curl http://localhost:8081 (attempt {attempt + 1}) returned HTTP code: {result.stdout.strip()}")
            if result.stdout.strip() == "200":
                break
        if result.stderr:
            print(f"curl error: {result.stderr.strip()}")
        if result.returncode != 0:
            print(f"curl failed with exit code {result.returncode}")
    except FileNotFoundError:
        print("curl not found in the container")
        break
    except Exception as e:
        print(f"Unexpected error running curl: {e}")
        break

# Log memory usage after server and bot start
log_memory_usage()

try:
    # Keep main thread alive
    while api_thread.is_alive() or bot_thread.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    print("\nCtrl+C received. Stopping processes...")
    shutdown_event.set()  # Signal threads to stop looping and exit gracefully

    # Attempt to terminate processes directly if they are still running
    print("Terminating API process...")
    if api_proc and api_proc.poll() is None:
        try:
            api_proc.terminate()
            api_proc.wait(timeout=5)  # Wait for termination
        except subprocess.TimeoutExpired:
            print("API process did not terminate gracefully, killing.")
            api_proc.kill()
        except Exception as e:
            print(f"Error terminating API process: {e}")

    print("Terminating Bot process...")
    if bot_proc and bot_proc.poll() is None:
        try:
            bot_proc.terminate()
            bot_proc.wait(timeout=5)  # Wait for termination
        except subprocess.TimeoutExpired:
            print("Bot process did not terminate gracefully, killing.")
            bot_proc.kill()
        except Exception as e:
            print(f"Error terminating Bot process: {e}")

    # Wait for threads to finish
    print("Waiting for threads to join...")
    api_thread.join()
    bot_thread.join()
    print("All processes stopped.")

# Final memory usage log
log_memory_usage()
print("Script finished.")