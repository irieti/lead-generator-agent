import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8601204708:AAG80XnYxmMNDMfBqvGXTHumnA6Z1CrnDpk"
CHAT_ID = "7663182669"

LEAD = "Alex Morgan, Head of Growth at GrowthLab — 14-person agency, 25h/week on manual outreach"

DRAFTED_EMAIL = """To: alex.morgan@growthlab.io
Subject: Re: AI automation for your outreach

Hi Alex,

25 hours a week on manual outreach is exactly the kind of problem I solve — I build multi-agent systems that handle prospecting, personalization, and follow-ups autonomously, with you approving before anything sends.

Happy to show you a live demo this week. What does your calendar look like Thursday or Friday?"""

MESSAGE = (
    f"Agent ready to send — awaiting approval\n"
    f"─────────────────────\n"
    f"Lead: {LEAD}\n"
    f"─────────────────────\n"
    f"Drafted email:\n\n"
    f"{DRAFTED_EMAIL}\n"
    f"─────────────────────\n"
    f"Send this email?"
)

pending: asyncio.Future | None = None


async def send_approval():
    global pending

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Send", callback_data="send"),
        InlineKeyboardButton("Reject", callback_data="reject"),
    ]])

    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=MESSAGE,
        reply_markup=keyboard,
    )
    print("Approval request sent. Waiting for response...")

    loop = asyncio.get_event_loop()
    pending = loop.create_future()
    return await asyncio.wait_for(pending, timeout=300)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pending
    query = update.callback_query
    await query.answer()

    action = query.data
    await query.edit_message_reply_markup(reply_markup=None)

    if action == "send":
        await query.message.reply_text("Email sent. Lead logged to CRM.")
    else:
        await query.message.reply_text("Rejected. Lead logged, email discarded.")

    print(f"\nDecision: {action.upper()}")

    if pending and not pending.done():
        pending.set_result(action)


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(callback_handler))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    result = await send_approval()
    if result == "send":
        print("Sending email via Gmail...")
        print("Logging lead to Google Sheets...")
    else:
        print("Email discarded. Lead logged as rejected.")

    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
