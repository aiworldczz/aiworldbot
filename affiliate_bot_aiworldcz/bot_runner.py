import os
import sys
from bot import main

if __name__ == "__main__":
    try:
        print("Starting Telegram bot...")
        main()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running bot: {e}")
        sys.exit(1)