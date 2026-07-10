from telegram import Update
from zoneinfo import ZoneInfo
from telegram.ext import CallbackQueryHandler, ContextTypes

from database.admins import is_admin
from database.payments import update_payment_status
from database.subscriptions import get_subscription
from services.subscription_service import (
    activate_subscription,
    extend_subscription,
)
from services.channel_service import grant_channel_access


async def safe_edit(query, text: str):
    try:
        await query.edit_message_caption(caption=text)
    except Exception:
        try:
            await query.edit_message_text(text)
        except Exception:
            pass


def format_ist(dt):
    return dt.astimezone(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d-%m-%Y %I:%M:%S %p IST")


async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_admin(query.from_user.id):
        await safe_edit(query, "❌ Not authorized")
        return

    try:
        data = query.data.split("_")

        user_id = int(data[1])
        duration_minutes = int(data[2])
        plan_name = data[3]

        plan_days = duration_minutes // 1440 if duration_minutes % 1440 == 0 else 0

        await update_payment_status(
            user_id=user_id,
            status="approved",
            admin_id=query.from_user.id,
        )

        subscription = await get_subscription(user_id)

        if subscription and subscription.get("active"):
            expiry = await extend_subscription(
                user_id=user_id,
                plan_days=plan_days,
                duration_minutes=duration_minutes,
            )
            action = "renewed"
        else:
            expiry = await activate_subscription(
                user_id=user_id,
                plan_name=plan_name,
                plan_days=plan_days,
                duration_minutes=duration_minutes,
            )
            action = "activated"

        expiry_ist = format_ist(expiry)

        await grant_channel_access(user_id)

        await safe_edit(
            query,
            f"✅ Payment Approved\n\n"
            f"User: {user_id}\n"
            f"Plan: {plan_name}\n"
            f"Expiry: {expiry_ist}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 Payment Approved!\n\n"
                f"Plan: {plan_name}\n"
                f"Subscription {action}.\n"
                f"Expiry: {expiry_ist}"
            ),
        )

    except Exception as e:
        await safe_edit(query, f"❌ Error\n\n{e}")


async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await is_admin(query.from_user.id):
        await safe_edit(query, "❌ Not authorized")
        return

    try:
        user_id = int(query.data.split("_")[1])

        await update_payment_status(
            user_id=user_id,
            status="rejected",
            admin_id=query.from_user.id,
        )

        await safe_edit(query, "❌ Payment Rejected")

        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Your payment was rejected.",
        )

    except Exception as e:
        await safe_edit(query, str(e))


def payment_approval_handlers():
    return [
        CallbackQueryHandler(
            approve_payment,
            pattern=r"^approve_",
        ),
        CallbackQueryHandler(
            reject_payment,
            pattern=r"^reject_",
        ),
    ]
