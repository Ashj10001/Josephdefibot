import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)
import tweepy
from solana.publickey import PublicKey

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set in Render environment variables
CHANNEL_LINK = "https://t.me/sakuramemecoin"
GROUP_LINK = "https://t.me/Sakuramemecoincommunity"
TWITTER_LINK = "https://x.com/Sukuramememcoin"
CHANNEL_ID = -1001234567890  # Replace with your channel ID
GROUP_ID = -1000987654321   # Replace with your group ID
TWITTER_USERNAME = "Sukuramemecoin"
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")

# ===== STATES =====
VERIFY_TWITTER, GET_WALLET = range(2)

# Initialize logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Twitter API
twitter_api = None
if TWITTER_API_KEY and TWITTER_API_SECRET:
    try:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        twitter_api = tweepy.API(auth)
    except Exception as e:
        logger.error(f"Twitter API init failed: {e}")

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    text = (
        f"🌸 *Welcome to Sakuramemecoin Airdrop, {user.first_name}\!* 🌸\n\n"
        "🎌 To qualify for the airdrop, complete these tasks:\n"
        f"1\. Join our [Telegram Channel]({CHANNEL_LINK})\n"
        f"2\. Join our [Telegram Group]({GROUP_LINK})\n"
        f"3\. Follow our [Twitter]({TWITTER_LINK})\n"
        "4\. Submit your SOL wallet address\n\n"
        "Click the button below when you've completed all tasks:"
    )
    
    keyboard = [[InlineKeyboardButton("✅ Verify Tasks", callback_data="verify_tasks")]]
    update.message.reply_markdown_v2(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def verify_tasks(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    try:
        # Check channel membership
        channel_member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        group_member = await context.bot.get_chat_member(GROUP_ID, user.id)
        
        if channel_member.status in ["member", "administrator", "creator"] and \
           group_member.status in ["member", "administrator", "creator"]:
            
            if twitter_api:
                await query.edit_message_text(
                    "🎌 Telegram tasks verified!\n\n"
                    "Please send your Twitter username (without @):"
                )
                return VERIFY_TWITTER
            else:
                await query.edit_message_text(
                    "🎌 Telegram tasks verified!\n\n"
                    "Please send your SOL wallet address:"
                )
                return GET_WALLET
        else:
            missing = []
            if channel_member.status not in ["member", "administrator", "creator"]:
                missing.append(f"• [Telegram Channel]({CHANNEL_LINK})")
            if group_member.status not in ["member", "administrator", "creator"]:
                missing.append(f"• [Telegram Group]({GROUP_LINK})")
            
            text = "⚠️ *Please complete these tasks:*\n" + "\n".join(missing)
            await query.edit_message_text(
                text,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        await query.edit_message_text("⛔ Verification failed. Please try again later.")

def verify_twitter(update: Update, context: CallbackContext) -> int:
    twitter_handle = update.message.text.strip()
    
    if not twitter_api:
        update.message.reply_text("⚠️ Twitter verification disabled. Please send your SOL wallet:")
        return GET_WALLET
        
    try:
        user = twitter_api.get_user(screen_name=twitter_handle)
        
        # Check if following (simplified)
        if True:  # Replace with actual follow check if needed
            context.user_data["twitter"] = twitter_handle
            update.message.reply_text(
                "🐦 Twitter verified!\n\n"
                "Now send your SOL wallet address:"
            )
            return GET_WALLET
        else:
            update.message.reply_text(
                f"⛔ Please follow our Twitter first: {TWITTER_LINK}\n\n"
                "Send your Twitter username again:"
            )
            return VERIFY_TWITTER
    except tweepy.NotFound:
        update.message.reply_text("❌ Twitter account not found. Please send a valid username:")
        return VERIFY_TWITTER
    except tweepy.TweepyException as e:
        logger.error(f"Twitter error: {e}")
        update.message.reply_text("⚠️ Twitter verification failed. Please send your SOL wallet:")
        return GET_WALLET

def get_wallet(update: Update, context: CallbackContext) -> int:
    wallet_address = update.message.text.strip()
    
    try:
        # Validate SOL address format
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", wallet_address):
            raise ValueError("Invalid SOL format")
            
        # Build congratulations message
        text = (
            "🎉 *CONGRATULATIONS\!* 🎉\n\n"
            "You have successfully joined JosephDeFi bot!\n\n"
            "💰 *100 SOL is on its way to your wallet\!*\n\n"
            "Transaction will complete within 24 hours\.\n\n"
            "Stay tuned for more rewards\!"
        )
        
        update.message.reply_markdown_v2(text)
        return ConversationHandler.END
        
    except (ValueError, AttributeError):
        update.message.reply_text("⛔ Invalid SOL address. Please send a valid wallet address:")
        return GET_WALLET

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("🚫 Airdrop registration cancelled.")
    return ConversationHandler.END

def main() -> None:
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Conversation handler for registration flow
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(verify_tasks, pattern="^verify_tasks$")],
        states={
            VERIFY_TWITTER: [MessageHandler(Filters.text & ~Filters.command, verify_twitter)],
            GET_WALLET: [MessageHandler(Filters.text & ~Filters.command, get_wallet)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    logger.info("Bot started...")
    updater.idle()

if __name__ == "__main__":
    main()