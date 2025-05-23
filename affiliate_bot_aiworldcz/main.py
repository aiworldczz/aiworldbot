import os
import sqlite3
import threading
import subprocess
import signal
import logging
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Global variables to track the bot subprocess
bot_process = None
bot_status = "stopped"
bot_log = []
max_log_entries = 100

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('affiliates.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# Initialize database if it doesn't exist
def init_db():
    try:
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
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

# Start the Telegram bot as a subprocess
def start_bot():
    global bot_process, bot_status, bot_log
    
    token = os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        return False, "No Telegram token provided"
    
    try:
        # Use subprocess to run the bot in the background
        cmd = ["python", "bot_runner.py"]
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Start a thread to read bot output
        def read_output():
            global bot_log
            for line in iter(bot_process.stdout.readline, ''):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"[{timestamp}] {line.strip()}"
                bot_log.append(log_entry)
                # Keep log at a reasonable size
                if len(bot_log) > max_log_entries:
                    bot_log = bot_log[-max_log_entries:]
                logger.debug(f"Bot output: {line.strip()}")
        
        threading.Thread(target=read_output, daemon=True).start()
        
        bot_status = "running"
        return True, "Bot started successfully"
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False, f"Error starting bot: {e}"

# Stop the Telegram bot
def stop_bot():
    global bot_process, bot_status
    
    if bot_process is None:
        return True, "Bot not running"
    
    try:
        # Send SIGTERM to the bot process
        bot_process.terminate()
        
        # Wait for the process to terminate (with timeout)
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # If timeout expired, force kill
            bot_process.kill()
            bot_process.wait()
        
        bot_process = None
        bot_status = "stopped"
        return True, "Bot stopped successfully"
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return False, f"Error stopping bot: {e}"

@app.route('/')
def index():
    return render_template('index.html', 
                           bot_status=bot_status, 
                           token=os.environ.get("TELEGRAM_TOKEN", ""))

@app.route('/stats')
def stats():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get total users
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        
        # Get recent users
        c.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT 10")
        recent_users = c.fetchall()
        
        # Get top referrers
        c.execute("""
            SELECT referred_by, COUNT(*) as count 
            FROM users 
            WHERE referred_by IS NOT NULL 
            GROUP BY referred_by 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_referrers = c.fetchall()
        
        conn.close()
        
        return render_template('stats.html', 
                              total_users=total_users,
                              recent_users=recent_users,
                              top_referrers=top_referrers,
                              bot_status=bot_status)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        flash(f"Error fetching stats: {e}", "danger")
        return render_template('stats.html', 
                              total_users=0,
                              recent_users=[],
                              top_referrers=[],
                              bot_status=bot_status)

@app.route('/referrals')
def referrals():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        per_page = 15
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Build query based on search parameter
        query_params = []
        if search:
            search_query = f"WHERE username LIKE ? OR referred_by LIKE ?"
            query_params = [f'%{search}%', f'%{search}%']
        else:
            search_query = ""
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM users {search_query}"
        c.execute(count_query, query_params)
        total_count = c.fetchone()[0]
        total_pages = (total_count + per_page - 1) // per_page
        
        # Adjust page if out of bounds
        if page < 1:
            page = 1
        elif page > total_pages and total_pages > 0:
            page = total_pages
            
        # Get paginated user data
        offset = (page - 1) * per_page
        user_query = f"""
            SELECT * FROM users 
            {search_query}
            ORDER BY joined_at DESC 
            LIMIT ? OFFSET ?
        """
        c.execute(user_query, query_params + [per_page, offset])
        users = c.fetchall()
        
        # Get top referrers
        c.execute("""
            SELECT referred_by, COUNT(*) as count 
            FROM users 
            WHERE referred_by IS NOT NULL 
            GROUP BY referred_by 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_referrers = c.fetchall()
        
        # Get max referral count for progress bar
        max_referrals = 1  # Default to 1 to avoid division by zero
        if top_referrers:
            max_referrals = max(referrer['count'] for referrer in top_referrers)
            
        # Get referral timeline (simplified for demo)
        c.execute("""
            SELECT substr(joined_at, 1, 10) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN referred_by IS NOT NULL THEN 1 ELSE 0 END) as referred
            FROM users
            GROUP BY substr(joined_at, 1, 10)
            ORDER BY date DESC
            LIMIT 7
        """)
        referral_dates = c.fetchall()
        
        conn.close()
        
        return render_template('referrals.html',
                              users=users,
                              top_referrers=top_referrers,
                              referral_dates=referral_dates,
                              max_referrals=max_referrals,
                              page=page,
                              total_pages=total_pages,
                              search=search,
                              bot_status=bot_status)
    except Exception as e:
        logger.error(f"Error fetching referrals: {e}")
        flash(f"Error fetching referrals: {e}", "danger")
        return render_template('referrals.html',
                              users=[],
                              top_referrers=[],
                              referral_dates=[],
                              max_referrals=1,
                              page=1,
                              total_pages=1,
                              search='',
                              bot_status=bot_status)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        token = request.form.get('token', '')
        
        # Set the token as an environment variable
        os.environ["TELEGRAM_TOKEN"] = token
        flash("Settings updated successfully", "success")
        
        # Restart the bot if it's already running
        if bot_status == "running":
            stop_bot()
            time.sleep(1)  # Short delay to ensure proper shutdown
            start_bot()
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html', 
                           token=os.environ.get("TELEGRAM_TOKEN", ""),
                           bot_status=bot_status)

@app.route('/api/start_bot', methods=['POST'])
def api_start_bot():
    success, message = start_bot()
    return jsonify({"success": success, "message": message, "status": bot_status})

@app.route('/api/stop_bot', methods=['POST'])
def api_stop_bot():
    success, message = stop_bot()
    return jsonify({"success": success, "message": message, "status": bot_status})

@app.route('/api/bot_status', methods=['GET'])
def api_bot_status():
    return jsonify({"status": bot_status, "log": bot_log[-20:]})

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Make sure the bot is stopped when the app starts
    if bot_process is not None:
        stop_bot()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)