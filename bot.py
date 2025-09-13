import discord
from discord.ext import commands
import os
import requests
from dotenv import load_dotenv
import telebot
import datetime

# Load environment variables from .env file
load_dotenv()

# Load word list from file
def load_wordlist(filename):
    with open(filename, 'r') as f:
        return [line.strip().lower() for line in f if line.strip()]

wordlist = load_wordlist('wordlist.txt')

# Load DM user IDs from file
def load_dm_users(filename):
    with open(filename, 'r') as f:
        return [int(line.strip()) for line in f if line.strip()]

dm_user_ids = load_dm_users('dm_users.txt')

# Set your bot token and channel IDs here
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SERVER_CHANNEL_ID = int(os.getenv('SERVER_CHANNEL_ID', '0'))
DM_USER_ID = int(os.getenv('DM_USER_ID', '0'))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

def send_telegram_message(text, chat_id=None):
    if not TELEGRAM_BOT_TOKEN:
        print('Telegram bot token not set.')
        return
    chat_id = chat_id or TELEGRAM_CHAT_ID
    if not chat_id:
        print('Telegram chat ID not set.')
        return
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f'Failed to send Telegram message: {response.text}')
    except Exception as e:
        print(f'Error sending Telegram message: {e}')

@bot.event
async def on_message(message):
    print(f'New message from {message.author} in channel {getattr(message.channel, "id", None)}: {message.content}')
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check specific server channels for each user
    for discord_id, channel_id in server_channel_map.items():
        if message.channel.id == channel_id:
            if any(word in message.content.lower() for word in wordlist):
                detected_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print('Captcha detected! Verify here: https://owobot.com/captcha')
                print(f'Time: {detected_time}')
                chat_id = notification_map.get(discord_id, TELEGRAM_CHAT_ID)
                print(f'Sending Telegram message to chat_id={chat_id}: Captcha detected! Verify here: https://owobot.com/captcha\nTime: {detected_time}')
                send_telegram_message(f'Captcha detected! Verify here: https://owobot.com/captcha\nTime: {detected_time}', chat_id)

    # Check DM channel for multiple users
    if isinstance(message.channel, discord.DMChannel) and message.author.id in dm_user_ids:
        if any(word in message.content.lower() for word in wordlist):
            detected_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print('Captcha detected!')
            print(f'Time: {detected_time}')
            chat_id = notification_map.get(message.author.id, TELEGRAM_CHAT_ID)
            print(f'Sending Telegram message to chat_id={chat_id}: Captcha detected!\nTime: {detected_time}')
            send_telegram_message(f'Captcha detected!\nTime: {detected_time}', chat_id)

    await bot.process_commands(message)

def load_notification_map(filename):
    mapping = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                discord_id, telegram_id = line.split(':', 1)
                mapping[int(discord_id)] = telegram_id
    return mapping

notification_map = load_notification_map('notification_map.txt')

def load_server_channel_map(filename):
    mapping = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                discord_id, channel_id = line.split(':', 1)
                mapping[int(discord_id)] = int(channel_id)
    return mapping

server_channel_map = load_server_channel_map('server_channels.txt')

# Setup Telegram registration bot
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Helper to add Discord user ID to dm_users.txt
def add_dm_user(discord_id):
    with open('dm_users.txt', 'a') as f:
        f.write(f'{discord_id}\n')

# Helper to add mapping to notification_map.txt
def add_notification_mapping(discord_id, telegram_chat_id):
    with open('notification_map.txt', 'a') as f:
        f.write(f'{discord_id}:{telegram_chat_id}\n')

@telegram_bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_bot.reply_to(message, "Welcome! Please register your Discord user ID using /register <Discord User ID>")

@telegram_bot.message_handler(commands=['register'])
def register_user(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            telegram_bot.reply_to(message, "Usage: /register <discord_user_id> <server_channel_id>")
            return
        discord_id = args[1]
        server_channel_id = args[2]
        if not discord_id.isdigit() or not server_channel_id.isdigit():
            telegram_bot.reply_to(message, "Invalid Discord user ID or server channel ID. Please enter numeric IDs.")
            return
        # Check if user already registered
        with open('dm_users.txt', 'r') as f:
            if discord_id in [line.strip() for line in f if line.strip()]:
                telegram_bot.reply_to(message, f"Discord ID {discord_id} is already registered.")
                return
        add_dm_user(discord_id)
        add_notification_mapping(discord_id, message.chat.id)
        # Store server channel mapping
        with open('server_channels.txt', 'a') as f:
            f.write(f'{discord_id}:{server_channel_id}\n')
        telegram_bot.reply_to(message, f"Registration successful! Discord ID {discord_id} is now linked to this Telegram chat and server channel {server_channel_id}.")
    except IndexError:
        telegram_bot.reply_to(message, "Usage: /register <discord_id> <server_channel_id>")

if __name__ == '__main__':
    import threading
    # Run both bots in parallel
    discord_thread = threading.Thread(target=lambda: bot.run(BOT_TOKEN))
    telegram_thread = threading.Thread(target=lambda: telegram_bot.polling())
    discord_thread.start()
    telegram_thread.start()
    discord_thread.join()
    telegram_thread.join()
