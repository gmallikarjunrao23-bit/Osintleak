"""
OSINT 100X — Telegram Bot
python-telegram-bot 21.x
Run alongside the web app — reads same Railway env vars, no .env needed.
"""
from __future__ import annotations

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

from app import create_app
from app.services.osint import search as osint_search

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

flask_app = create_app()


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    site = flask_app.config["SITE_NAME"]
    dev  = flask_app.config["DEVELOPER"]
    await update.message.reply_text(
        f"🔍 *{site} — 100X ULTIMATE*\n\n"
        f"Query 500+ breach databases instantly.\n\n"
        f"*Commands:*\n"
        f"/search `<phone>` — Search by phone\n"
        f"/profile — Account info\n"
        f"/billing — Upgrade plan\n"
        f"/help — Help\n\n"
        f"Built by {dev}",
        parse_mode="Markdown"
    )


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /search `<phone>`\nExample: /search 918887882236",
            parse_mode="Markdown"
        )
        return

    query = " ".join(ctx.args).strip()
    msg = await update.message.reply_text(f"🔍 Querying *{query}*...", parse_mode="Markdown")

    with flask_app.app_context():
        result = osint_search(query)

    if not result["ok"] or result["total_records"] == 0:
        await msg.edit_text(f"❌ No records found for `{query}`", parse_mode="Markdown")
        return

    intel = result["intel"]
    lines = [f"✅ *Results for* `{query}`\n"]
    lines.append(f"📊 Sources: `{result['total_sources']}` | Records: `{result['total_records']}`\n")

    if intel.get("names"):
        lines.append("👤 *Names:*\n" + "\n".join(f"  `{v}`" for v in intel["names"][:3]))
    if intel.get("emails"):
        lines.append("📧 *Emails:*\n" + "\n".join(f"  `{v}`" for v in intel["emails"][:3]))
    if intel.get("phones"):
        p = [x for x in intel["phones"] if x != result["number"]][:3]
        if p:
            lines.append("📱 *Phones:*\n" + "\n".join(f"  `{v}`" for v in p))
    if intel.get("ips"):
        lines.append("🌐 *IPs:*\n" + "\n".join(f"  `{v}`" for v in intel["ips"][:2]))
    if intel.get("countries"):
        lines.append("🌍 *Country:* " + ", ".join(intel["countries"][:2]))
    if intel.get("addresses"):
        lines.append("📍 *Address:* `" + intel["addresses"][0][:80] + "`")

    lines.append(f"\n⏱ `{result['response_time']:.3f}s`")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")


async def cmd_billing(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    upi  = flask_app.config["UPI_ID"]
    bank = flask_app.config["BANK_NAME"]
    site = flask_app.config["SITE_NAME"]
    await update.message.reply_text(
        f"💳 *{site} — Plans*\n\n"
        f"👑 Premium — ₹99/mo — 100 searches/day\n"
        f"⚡ Pro — ₹299/mo — Unlimited\n"
        f"🏢 Enterprise — ₹999/mo — Unlimited\n\n"
        f"Pay to UPI: `{upi}`\n"
        f"Bank: {bank}\n\n"
        f"Submit txn ID on web dashboard → Billing.",
        parse_mode="Markdown"
    )


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👤 *Profile*\n\nCheck your full profile on the web dashboard.",
        parse_mode="Markdown"
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🆘 *Help*\n\n"
        "/search `<number>` — Query by phone\n"
        "/billing — Plans & UPI payment\n"
        "/profile — Account info\n\n"
        "Send any phone number directly to search.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    if text.lstrip("+").replace(" ", "").isdigit():
        ctx.args = [text]
        await cmd_search(update, ctx)
    else:
        await update.message.reply_text("Send a phone number or use /help.")


def run_bot() -> None:
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        log.error("BOT_TOKEN not set in environment.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("search",  cmd_search))
    app.add_handler(CommandHandler("billing", cmd_billing))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Telegram bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
