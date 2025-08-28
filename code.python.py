import asyncio
import logging
import sqlite3
import re
from datetime import datetime
from pyrogram import Client, filters, types
from pyrogram.errors import (
    SessionPasswordNeeded, PhoneCodeInvalid,
    PhoneCodeExpired, ApiIdInvalid, PhoneNumberInvalid
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, status TEXT, delay INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS accounts
                 (user_id INTEGER, session_string TEXT, phone TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (user_id INTEGER, message_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (user_id INTEGER, group_id INTEGER, group_name TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_sessions
                 (user_id INTEGER, api_id INTEGER, api_hash TEXT, phone_number TEXT,
                  phone_code_hash TEXT, session_string TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()

init_db()

# Bot configuration - Using the provided token
BOT_TOKEN = "8392760740:AAGcb92lYemFInk67GaYxX1J0xNR6GUbRe8"

# Initialize the bot with proper configuration
app = Client(
    "kuro_adbot_bot",
    bot_token=BOT_TOKEN,
    api_id=2040,  # Using a generic API ID for bot client
    api_hash="b18441a1ff607e10a989891a5462e627"  # Using a generic API HASH for bot client
)

# Default user settings
DEFAULT_DELAY = 10  # 10 minutes as default
BRANDING_TEXT = "—via KuroSamaAdsBot"

# Helper functions for database operations
def get_user(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id, status, delay) VALUES (?, ?, ?)",
              (user_id, "OFF", DEFAULT_DELAY))
    conn.commit()
    conn.close()

def update_user_status(user_id, status):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET status = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def update_user_delay(user_id, delay):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET delay = ? WHERE user_id = ?", (delay, user_id))
    conn.commit()
    conn.close()

def get_user_delay(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT delay FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_DELAY

def get_user_status(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "OFF"

def add_account(user_id, session_string, phone):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("INSERT INTO accounts (user_id, session_string, phone) VALUES (?, ?, ?)",
              (user_id, session_string, phone))
    conn.commit()
    conn.close()

def get_accounts(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT phone FROM accounts WHERE user_id = ?", (user_id,))
    accounts = [row[0] for row in c.fetchall()]
    conn.close()
    return accounts

def add_message(user_id, message_text):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO messages (user_id, message_text) VALUES (?, ?)",
              (user_id, message_text))
    conn.commit()
    conn.close()

def get_message(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT message_text FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def clear_groups(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("DELETE FROM groups WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_group(user_id, group_id, group_name):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO groups (user_id, group_id, group_name) VALUES (?, ?, ?)",
              (user_id, group_id, group_name))
    conn.commit()
    conn.close()

def get_groups(user_id):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT group_id, group_name FROM groups WHERE user_id = ?", (user_id,))
    groups = c.fetchall()
    conn.close()
    return groups

def save_user_session(user_id, api_id, api_hash, phone_number, phone_code_hash=None, session_string=None):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()

    if session_string:
        # Update existing session with session_string
        c.execute("UPDATE user_sessions SET session_string = ? WHERE user_id = ? AND phone_number = ?",
                 (session_string, user_id, phone_number))
    elif phone_code_hash:
        # Update existing session with phone_code_hash
        c.execute("UPDATE user_sessions SET phone_code_hash = ? WHERE user_id = ? AND phone_number = ?",
                 (phone_code_hash, user_id, phone_number))
    else:
        # Insert new session or replace if user_id, api_id, api_hash, phone_number combination exists
        c.execute("INSERT OR REPLACE INTO user_sessions (user_id, api_id, api_hash, phone_number) VALUES (?, ?, ?, ?)",
                 (user_id, api_id, api_hash, phone_number))

    conn.commit()
    conn.close()

def get_user_session(user_id, phone_number):
    conn = sqlite3.connect('kuro_adbot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM user_sessions WHERE user_id = ? AND phone_number = ?", (user_id, phone_number))
    session = c.fetchone()
    conn.close()
    return session

# State management for user interactions
user_states = {} # This will now also store the Pyrogram Client object

# Function to add branding to user profile
async def add_branding_to_profile(user_client):
    try:
        # Get current user info
        me = await user_client.get_me()

        # Add branding to last name if not already present
        new_last_name = me.last_name or ""
        if BRANDING_TEXT not in new_last_name:
            new_last_name = f"{new_last_name} {BRANDING_TEXT}".strip()

        # Add branding to bio if not already present
        # FIX: Use me.bio directly, no need for get_users
        new_bio = me.bio or ""
        if BRANDING_TEXT not in new_bio:
            new_bio = f"{new_bio} {BRANDING_TEXT}".strip()

        # Update profile with branding
        await user_client.update_profile(
            last_name=new_last_name,
            bio=new_bio
        )
        return True
    except Exception as e:
        logger.error(f"Error adding branding to profile: {e}")
        return False

# Function to check if user has branding
async def check_branding(user_client):
    try:
        me = await user_client.get_me()
        # FIX: Use me.bio directly, no need for get_users
        has_last_name_branding = me.last_name and BRANDING_TEXT in me.last_name
        has_bio_branding = me.bio and BRANDING_TEXT in me.bio

        return has_last_name_branding and has_bio_branding
    except Exception as e:
        logger.error(f"Error checking branding: {e}")
        return False

# Function to automatically fetch groups
async def fetch_user_groups(user_client, user_id):
    try:
        clear_groups(user_id)  # Clear existing groups

        group_count = 0
        async for dialog in user_client.get_dialogs():
            if dialog.chat.type in ["group", "supergroup", "channel"]:
                # FIX: Removed incorrect channel permission check.
                # Sending will be attempted, and errors handled by send_ads.
                add_group(user_id, dialog.chat.id, dialog.chat.title)
                group_count += 1

        return group_count
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        return 0

# Function to fetch saved messages
async def fetch_saved_messages(user_client, user_id):
    try:
        # Get the most recent message from saved messages
        async for message in user_client.get_chat_history("me", limit=1):
            if message.text:
                add_message(user_id, message.text)
                return message.text

        return None
    except Exception as e:
        logger.error(f"Error fetching saved messages: {e}")
        return None

# Function to send ads to all groups
async def send_ads(user_id, user_client):
    try:
        # Check if user has branding
        if not await check_branding(user_client):
            await add_branding_to_profile(user_client)

        # Get the message to send
        message_text = get_message(user_id)
        if not message_text:
            logger.error(f"No message found for user {user_id}")
            return False

        # Get all groups
        groups = get_groups(user_id)
        if not groups:
            logger.error(f"No groups found for user {user_id}")
            return False

        # Get delay time
        delay = get_user_delay(user_id) * 60  # Convert to seconds

        success_count = 0
        for group_id, group_name in groups:
            try:
                # Send message to group
                await user_client.send_message(group_id, message_text)
                success_count += 1
                logger.info(f"Sent message to {group_name}")

                # Wait for the specified delay
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Error sending to {group_name}: {e}")
                continue

        logger.info(f"Sent ads to {success_count}/{len(groups)} groups")
        return success_count > 0

    except Exception as e:
        logger.error(f"Error in send_ads: {e}")
        return False

# Command handlers
@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id

    # Create user if not exists
    if not get_user(user_id):
        create_user(user_id)

    # Main menu
    delay = get_user_delay(user_id)
    status = get_user_status(user_id)
    status_text = "ON 🟢" if status == "ON" else "OFF 🔴"

    keyboard = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton("👤 Accounts", callback_data="accounts"),
         types.InlineKeyboardButton(f"⏰ Delay: {delay}m", callback_data="delay")],
        [types.InlineKeyboardButton("📋 Auto Groups", callback_data="auto_groups"),
         types.InlineKeyboardButton("💬 Auto Message", callback_data="auto_message")],
        [types.InlineKeyboardButton("⚙️ Admin", callback_data="admin"),
         types.InlineKeyboardButton(f"Status: {status_text.split()[0]}", callback_data="toggle_status")]
    ])

    await message.reply_text(
        f"🌟 **KuroSamaAdsBot** [Free]\n"
        f"📊 1,474 monthly users\n\n"
        f"👋 Hi {message.from_user.first_name}, I am your all-in-one AdBot to help you spread your ads easily, safely, and automatically!\n\n"
        f"📈 Status: {status_text}\n\n"
        f"🔧 Use the options below to control the bot and start sending ads.",
        reply_markup=keyboard
    )

@app.on_callback_query()
async def handle_callback(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "accounts":
        accounts = get_accounts(user_id)
        accounts_text = "\n".join([f"• {acc}" for acc in accounts]) if accounts else "📭 No accounts added yet."

        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("➕ Add account", callback_data="add_account")],
            [types.InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])

        await callback_query.message.edit_text(
            f"**👤 Account Management**\n\n"
            f"*Manage your Telegram accounts here:*\n\n"
            f"{accounts_text}",
            reply_markup=keyboard
        )

    elif data == "add_account":
        user_states[user_id] = {"state": "awaiting_api_id"} # Initialize state for user
        await callback_query.message.edit_text(
            "🔐 **Add Account**\n\n"
            "To add an account, please provide your API credentials:\n\n"
            "1. Go to https://my.telegram.org/apps\n"
            "2. Create a new application and get API_ID and API_HASH\n\n"
            "📥 Please send your API_ID:",
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("🔙 Back", callback_data="accounts")]
            ])
        )

    elif data == "delay":
        current_delay = get_user_delay(user_id)
        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("3 MIN", callback_data="delay_3"),
             types.InlineKeyboardButton("5 MIN", callback_data="delay_5")],
            [types.InlineKeyboardButton("7 MIN", callback_data="delay_7"),
             types.InlineKeyboardButton("10 MIN", callback_data="delay_10")],
            [types.InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])

        await callback_query.message.edit_text(
            f"⏰ **Delay Settings**\n\n"
            f"Current delay: {current_delay} minutes\n\n"
            "Select a new delay option:",
            reply_markup=keyboard
        )

    elif data.startswith("delay_"):
        delay_time = int(data.split("_")[1])
        update_user_delay(user_id, delay_time)

        # Update main menu
        status = get_user_status(user_id)
        status_text = "ON 🟢" if status == "ON" else "OFF 🔴"

        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("👤 Accounts", callback_data="accounts"),
             types.InlineKeyboardButton(f"⏰ Delay: {delay_time}m", callback_data="delay")],
            [types.InlineKeyboardButton("📋 Auto Groups", callback_data="auto_groups"),
             types.InlineKeyboardButton("💬 Auto Message", callback_data="auto_message")],
            [types.InlineKeyboardButton("⚙️ Admin", callback_data="admin"),
             types.InlineKeyboardButton(f"Status: {status_text.split()[0]}", callback_data="toggle_status")]
        ])

        await callback_query.message.edit_text(
            f"✅ Delay updated to {delay_time} minutes\n\n"
            f"🌟 **KuroSamaAdsBot** [Free]\n"
            f"📊 1,474 monthly users\n\n"
            f"👋 Hi {callback_query.from_user.first_name}, I am your all-in-one AdBot to help you spread your ads easily, safely, and automatically!\n\n"
            f"📈 Status: {status_text}\n\n"
            f"🔧 Use the options below to control the bot and start sending ads.",
            reply_markup=keyboard
        )

    elif data == "auto_groups":
        accounts = get_accounts(user_id)
        if not accounts:
            await callback_query.answer("❌ You need to add an account first!", show_alert=True)
            return

        await callback_query.message.edit_text(
            "🔄 **Auto Groups**\n\n"
            "Groups will be automatically fetched from your account when you start advertising.\n\n"
            "The bot will send messages to all groups/channels you are admin in.",
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    elif data == "auto_message":
        accounts = get_accounts(user_id)
        if not accounts:
            await callback_query.answer("❌ You need to add an account first!", show_alert=True)
            return

        await callback_query.message.edit_text(
            "💬 **Auto Message**\n\n"
            "The bot will automatically use the most recent message from your 'Saved Messages' folder.\n\n"
            "Make sure to save the message you want to send to your Saved Messages!",
            reply_markup=types.InlineKeyboardMarkup([
                [types.InlineKeyboardButton("🔙 Back", callback_data="back_main")]
            ])
        )

    elif data == "admin":
        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("📞 Contact Admin", url="https://t.me/AccSellerTGWP")],
            [types.InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ])

        await callback_query.message.edit_text(
            "⚙️ **Admin Panel**\n\n"
            "For support or premium features, contact our admin:\n\n"
            "📞 @AccSellerTGWP",
            reply_markup=keyboard
        )

    elif data == "toggle_status":
        current_status = get_user_status(user_id)
        new_status = "OFF" if current_status == "ON" else "ON"
        update_user_status(user_id, new_status)

        status_text = "ON 🟢" if new_status == "ON" else "OFF 🔴"
        await callback_query.answer(f"Status changed to {new_status}")

        # If status is ON, start the advertising process
        if new_status == "ON":
            accounts = get_accounts(user_id)
            if not accounts:
                await callback_query.answer("❌ You need to add an account first!", show_alert=True)
                update_user_status(user_id, "OFF") # Revert status if no accounts
                return

            # Start the advertising process in the background
            asyncio.create_task(start_advertising(user_id))

        # Update main menu
        delay = get_user_delay(user_id)
        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("👤 Accounts", callback_data="accounts"),
             types.InlineKeyboardButton(f"⏰ Delay: {delay}m", callback_data="delay")],
            [types.InlineKeyboardButton("📋 Auto Groups", callback_data="auto_groups"),
             types.InlineKeyboardButton("💬 Auto Message", callback_data="auto_message")],
            [types.InlineKeyboardButton("⚙️ Admin", callback_data="admin"),
             types.InlineKeyboardButton(f"Status: {status_text.split()[0]}", callback_data="toggle_status")]
        ])

        await callback_query.message.edit_text(
            f"🌟 **KuroSamaAdsBot** [Free]\n"
            f"📊 1,474 monthly users\n\n"
            f"👋 Hi {callback_query.from_user.first_name}, I am your all-in-one AdBot to help you spread your ads easily, safely, and automatically!\n\n"
            f"📈 Status: {status_text}\n\n"
            f"🔧 Use the options below to control the bot and start sending ads.",
            reply_markup=keyboard
        )

    elif data == "back_main":
        delay = get_user_delay(user_id)
        status = get_user_status(user_id)
        status_text = "ON 🟢" if status == "ON" else "OFF 🔴"

        keyboard = types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("👤 Accounts", callback_data="accounts"),
             types.InlineKeyboardButton(f"⏰ Delay: {delay}m", callback_data="delay")],
            [types.InlineKeyboardButton("📋 Auto Groups", callback_data="auto_groups"),
             types.InlineKeyboardButton("💬 Auto Message", callback_data="auto_message")],
            [types.InlineKeyboardButton("⚙️ Admin", callback_data="admin"),
             types.InlineKeyboardButton(f"Status: {status_text.split()[0]}", callback_data="toggle_status")]
        ])

        await callback_query.message.edit_text(
            f"🌟 **KuroSamaAdsBot** [Free]\n"
            f"📊 1,474 monthly users\n\n"
            f"👋 Hi {callback_query.from_user.first_name}, I am your all-in-one AdBot to help you spread your ads easily, safely, and automatically!\n\n"
            f"📈 Status: {status_text}\n\n"
            f"🔧 Use the options below to control the bot and start sending ads.",
            reply_markup=keyboard
        )

# Function to handle the advertising process
async def start_advertising(user_id):
    user_client = None # Initialize user_client to None
    try:
        # Get user session
        accounts = get_accounts(user_id)
        if not accounts:
            logger.error(f"No accounts found for user {user_id}")
            update_user_status(user_id, "OFF") # Turn off status if no accounts
            return

        # For simplicity, using the first account
        phone_number = accounts[0]
        session_data = get_user_session(user_id, phone_number)

        if not session_data or not session_data[5]:  # session_string is at index 5
            logger.error(f"No session found for user {user_id} with phone {phone_number}")
            update_user_status(user_id, "OFF") # Turn off status if no valid session
            return

        # Create a client for the user account
        user_client = Client(
            name=f"user_{user_id}_{phone_number}",
            api_id=session_data[1],  # api_id is at index 1
            api_hash=session_data[2],  # api_hash is at index 2
            session_string=session_data[5]  # session_string is at index 5
        )

        await user_client.start()

        # Add branding to profile
        await add_branding_to_profile(user_client)

        # Fetch groups automatically
        group_count = await fetch_user_groups(user_client, user_id)
        logger.info(f"Fetched {group_count} groups for user {user_id}")

        # Fetch saved message automatically
        message = await fetch_saved_messages(user_client, user_id)

        if not message:
            logger.error(f"No saved message found for user {user_id}")
            await user_client.stop()
            update_user_status(user_id, "OFF") # Turn off status if no message
            return

        # Send ads in a loop while status is ON
        while get_user_status(user_id) == "ON":
            success = await send_ads(user_id, user_client)
            if not success:
                logger.warning(f"Failed to send ads for user {user_id} in this cycle. Retrying in next cycle.")
                # Do not break here, allow retries unless a critical error occurs
            
            # Wait for the next cycle
            delay = get_user_delay(user_id) * 60  # Convert to seconds
            await asyncio.sleep(delay)

    except Exception as e:
        logger.error(f"Error in start_advertising for user {user_id}: {e}")
        update_user_status(user_id, "OFF") # Turn off status on critical error
    finally:
        if user_client and user_client.is_connected:
            await user_client.stop() # Ensure client is stopped

# Handle incoming messages for account setup
@app.on_message(filters.private & ~filters.command("start"))
async def handle_message(client, message):
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state_data = user_states[user_id]
    state = state_data.get("state")
    user_client = state_data.get("client") # Retrieve the client if it exists

    try:
        if state == "awaiting_api_id":
            try:
                api_id = int(message.text)
                state_data["api_id"] = api_id
                state_data["state"] = "awaiting_api_hash"
                await message.reply_text("✅ API_ID received. Now please send your API_HASH:")
            except ValueError:
                await message.reply_text("❌ Invalid API_ID. Please enter a valid number:")

        elif state == "awaiting_api_hash":
            api_hash = message.text
            state_data["api_hash"] = api_hash
            state_data["state"] = "awaiting_phone"

            await message.reply_text("✅ API_HASH received. Now please send your phone number (with country code, e.g., +1234567890):")

        elif state == "awaiting_phone":
            phone_number = message.text
            state_data["phone_number"] = phone_number

            # Create a client for the user and store it in state
            user_client = Client(
                name=f"user_{user_id}_{phone_number}",
                api_id=state_data["api_id"],
                api_hash=state_data["api_hash"],
                in_memory=True # Use in_memory session for auth flow
            )
            state_data["client"] = user_client # Store the client instance

            await user_client.connect() # Connect the client

            # Save the initial session info (api_id, api_hash, phone_number)
            save_user_session(user_id, state_data["api_id"], state_data["api_hash"], phone_number)

            try:
                # Send code request
                sent_code = await user_client.send_code(phone_number)
                state_data["phone_code_hash"] = sent_code.phone_code_hash
                state_data["state"] = "awaiting_code"

                await message.reply_text("✅ Verification code sent. Please enter the code you received:")

            except PhoneNumberInvalid:
                await message.reply_text("❌ Invalid phone number. Please try again with a valid phone number:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id] # Clean up state
            except ApiIdInvalid:
                await message.reply_text("❌ Invalid API_ID or API_HASH. Please start over with /start:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id] # Clean up state
            except Exception as e:
                logger.error(f"Error sending code for user {user_id}: {e}")
                await message.reply_text(f"❌ Error: {e}. Please try again with /start:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id]

        elif state == "awaiting_code":
            code = message.text

            if not user_client or not user_client.is_connected:
                await message.reply_text("❌ Session error or client not connected. Please start over with /start:")
                if user_id in user_states: del user_states[user_id]
                return

            try:
                # Sign in with the code
                await user_client.sign_in(
                    phone_number=state_data.get('phone_number', ''),
                    phone_code_hash=state_data["phone_code_hash"],
                    phone_code=code
                )

                # Get session string
                session_string = await user_client.export_session_string()

                # Save session string
                save_user_session(
                    user_id,
                    state_data["api_id"],
                    state_data["api_hash"],
                    state_data.get('phone_number', ''),
                    session_string=session_string
                )

                # Add account to database
                add_account(user_id, session_string, state_data.get('phone_number', ''))

                # Add branding to profile
                await add_branding_to_profile(user_client)

                await message.reply_text("✅ Account added successfully! You can now use the bot.")

                # Clean up
                await user_client.disconnect() # Disconnect after successful auth
                del user_states[user_id]

            except PhoneCodeInvalid:
                await message.reply_text("❌ Invalid code. Please enter the correct code:")
            except PhoneCodeExpired:
                await message.reply_text("❌ Code expired. Please start over with /start:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id]
            except SessionPasswordNeeded:
                state_data["state"] = "awaiting_password"
                await message.reply_text("🔒 Two-step verification is enabled. Please enter your password:")
                # DO NOT disconnect here, client needs to remain connected for password check
            except Exception as e:
                logger.error(f"Error signing in for user {user_id}: {e}")
                await message.reply_text(f"❌ Error: {e}. Please try again with /start:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id]

        elif state == "awaiting_password":
            password = message.text

            if not user_client or not user_client.is_connected:
                await message.reply_text("❌ Session error or client not connected. Please start over with /start:")
                if user_id in user_states: del user_states[user_id]
                return

            try:
                # Check password
                await user_client.check_password(password)

                # Get session string
                session_string = await user_client.export_session_string()

                # Save session string
                save_user_session(
                    user_id,
                    state_data["api_id"],
                    state_data["api_hash"],
                    state_data.get('phone_number', ''),
                    session_string=session_string
                )

                # Add account to database
                add_account(user_id, session_string, state_data.get('phone_number', ''))

                # Add branding to profile
                await add_branding_to_profile(user_client)

                await message.reply_text("✅ Account added successfully! You can now use the bot.")

                # Clean up
                await user_client.disconnect() # Disconnect after successful auth
                del user_states[user_id]

            except Exception as e:
                logger.error(f"Error checking password for user {user_id}: {e}")
                await message.reply_text(f"❌ Error: {e}. Please try again with /start:")
                await user_client.disconnect() # Disconnect on error
                del user_states[user_id]
    except Exception as e:
        logger.error(f"Unhandled error in handle_message for user {user_id}: {e}")
        # Ensure client is disconnected and state cleaned up on any unhandled error
        if user_client and user_client.is_connected:
            await user_client.disconnect()
        if user_id in user_states:
            del user_states[user_id]
        await message.reply_text("An unexpected error occurred during account setup. Please try again with /start.")


# Start the bot
async def main():
    await app.start()
    print("KuroSamaAdsBot started successfully!")
    await app.idle()

if __name__ == "__main__":
    print("Starting KuroSamaAdsBot...")
    # Install TgCrypto for better performance if available
    try:
        import tgcrypto
        print("TgCrypto found! Using optimized encryption.")
    except ImportError:
        print("TgCrypto not found. Using slower encryption. Install with: pip install TgCrypto")

    # Run the bot
    asyncio.run(main())
