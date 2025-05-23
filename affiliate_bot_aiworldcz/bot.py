from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
import sqlite3
from datetime import datetime
import logging
import os

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('affiliates.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        referred_by TEXT,
        joined_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Nastala chyba při zpracování požadavku. Zkuste to prosím znovu.")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ref = None
        if context.args and len(context.args) > 0:
            ref = context.args[0]
            
        user = update.effective_user
        user_id = user.id
        username = user.username or f"id{user_id}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check if user already exists
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        existing_user = c.fetchone()
        
        if not existing_user:
            c.execute(
                "INSERT INTO users (user_id, username, referred_by, joined_at) VALUES (?, ?, ?, ?)",
                (user_id, username, ref, now)
            )
            conn.commit()
            
            # Log successful referral if applicable
            if ref:
                logger.info(f"New user {username} joined via referral from {ref}")
        
        conn.close()
        
        # Personalized welcome message
        if existing_user:
            await update.message.reply_text(
                f"Vítej zpět, {username}! Použij /link pro získání tvého referral odkazu nebo /stats pro zobrazení statistik."
            )
        else:
            await update.message.reply_text(
                f"Ahoj {username}! " +
                (f"Byl jsi přiveden přes {ref}!" if ref else "Nikdo tě nepřivedl. Sdílej svůj odkaz dál!") +
                "\n\nPoužij /link pro získání tvého referral odkazu."
            )
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text("Něco se pokazilo při startu. Zkuste to prosím znovu.")

# /link command - generates referral link
async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        username = user.username or f"id{user.id}"
        
        # Create a clean username for the link (no special characters)
        clean_username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        link = f"https://t.me/aiworldcz?start={clean_username}"
        await update.message.reply_text(
            f"Tvůj referral odkaz: {link}\n\n"
            f"Sdílej ho a za každého nového člena, který se přes tvůj link napojí a koupí metodu tak získáš 40% z prodeje."
        )
    except Exception as e:
        logger.error(f"Error in link command: {e}")
        await update.message.reply_text("Chyba při generování odkazu.")

# /stats command - shows referred users
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        username = user.username or f"id{user.id}"
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT username, joined_at FROM users WHERE referred_by=?", (username,))
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            await update.message.reply_text(
                "Zatím jsi nepřivedl žádné uživatele.\n"
                "Použij /link pro získání tvého referall odkazu a začni ho sdílet!"
            )
        else:
            text = f"Přivedl jsi {len(rows)} uživatelů:\n\n"
            for row in rows:
                uname = row['username']
                joined = row['joined_at']
                text += f"• @{uname} – {joined}\n"
            
            await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await update.message.reply_text("Chyba při získávání statistik.")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Dostupné příkazy:\n\n"
        "/start - Začni používat bota\n"
        "/link - Získej svůj referall odkaz\n"
        "/stats - Zobraz statistiky tvých referralů\n"
        "/help - Zobraz tuto nápovědu"
    )
    await update.message.reply_text(help_text)

# Handle unknown commands
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Neznámý příkaz. Použij /help pro zobrazení dostupných příkazů."
    )

def main():
    # Initialize the database
    init_db()
    
    # Get token from environment variable or use a default (not recommended for production)
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        logger.error("No Telegram token provided")
        return
    
    # Build the application
    app = Application.builder().token(token).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_command))
    
    # Handle unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Run the bot
    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()