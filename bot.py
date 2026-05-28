import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== КОНФИГ ==========
BOT_TOKEN = "8523439003:AAGPCiIrAeEZP1CkuVEV4y_HrTSakOcfJwo"
ALLOWED_CHAT_ID = 7013338924
API_KEY = "vCorochTBYCcWcB4bhH6VNT3B0lOA519jkavsRbElZg"
API_URL = "https://tvyze.co/api/v1/stats"
# ============================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_allowed(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    return user_id == ALLOWED_CHAT_ID


def fetch_stats(period: str) -> dict | None:
    try:
        resp = requests.get(
            API_URL,
            params={"period": period},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Ошибка API: {e}")
        return None


def esc(text: str) -> str:
    """Экранирует спецсимволы для MarkdownV2"""
    if not text:
        return ""
    special = r"\_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


def get_activity_emoji(last_activity: str | None) -> str:
    if not last_activity:
        return "💤"
    try:
        last = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
        diff_minutes = (datetime.now() - last).total_seconds() / 60
        if diff_minutes < 10:
            return "🟢"
        elif diff_minutes < 60:
            return "🟡"
        else:
            return "🔴"
    except Exception:
        return "⚪"


def get_success_bar(success: int, total: int) -> str:
    if total == 0:
        return "░░░░░░░░░░ 0%"
    percent = success / total * 100
    filled = int(percent / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{bar} {percent:.0f}%"


def format_stats(data: dict, period: str) -> str:
    period_names = {
        "hour": "⏰ Час",
        "day": "📅 День",
        "week": "📆 Неделя",
        "month": "🗓 Месяц"
    }
    period_label = period_names.get(period, period)
    now = datetime.now().strftime("%d\\.%m\\.%Y %H:%M")

    members = data.get("members", [])
    total = data.get("total", {})
    total_success = total.get("success", 0)
    total_error = total.get("error", 0)
    total_all = total_success + total_error
    team = esc(str(data.get("team", "—")))
    period_start = esc(str(data.get("period_start", "—")))

    active_members = [m for m in members if m.get("success", 0) > 0 or m.get("error", 0) > 0]
    inactive_members = [m for m in members if m.get("success", 0) == 0 and m.get("error", 0) == 0]
    active_members.sort(key=lambda x: x.get("success", 0), reverse=True)

    lines = [
        "╔══════════════════════════╗",
        "║  📊  СТАТИСТИКА TVYZE    ║",
        "╚══════════════════════════╝",
        "",
        f"👥 Команда: *{team}*",
        f"🕐 Период: *{esc(period_label)}*",
        f"📆 Старт: `{period_start}`",
        f"🔄 Обновлено: `{now}`",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📦 *ИТОГО*",
        f"  ✅ Успешно: *{total_success}*",
        f"  ❌ Ошибок: *{total_error}*",
        f"  📊 Всего: *{total_all}*",
        f"  `{get_success_bar(total_success, total_all)}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if active_members:
        lines.append(f"🔥 *АКТИВНЫЕ \\({len(active_members)}\\)*")
        lines.append("")
        for i, m in enumerate(active_members, 1):
            username = esc(m.get("username", "unknown"))
            full_name = esc(m.get("full_name", "—"))
            success = m.get("success", 0)
            error = m.get("error", 0)
            last_activity = m.get("last_activity")
            member_total = success + error
            activity_emoji = get_activity_emoji(last_activity)

            if last_activity:
                try:
                    la = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
                    last_str = esc(la.strftime("%H:%M:%S"))
                except Exception:
                    last_str = esc(last_activity)
            else:
                last_str = "нет данных"

            lines.append(f"{activity_emoji} *{i}\\. {full_name}*")
            lines.append(f"  👤 @{username}")
            lines.append(f"  ✅ {success}  ❌ {error}  📊 {member_total}")
            lines.append(f"  `{get_success_bar(success, member_total)}`")
            lines.append(f"  🕐 {last_str}")
            lines.append("")

    if inactive_members:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💤 *НЕАКТИВНЫЕ \\({len(inactive_members)}\\)*")
        lines.append("")
        chunks = [inactive_members[i:i+3] for i in range(0, len(inactive_members), 3)]
        for chunk in chunks:
            row = "  " + "   ".join([f"💤 @{esc(m.get('username', '?'))}" for m in chunk])
            lines.append(row)

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🟢 \\< 10 мин  🟡 \\< 1 часа  🔴 давно  💤 нет активности")

    return "\n".join(lines)


def get_main_keyboard(current_period: str = "day"):
    periods = {
        "hour": "⏰ Час",
        "day": "📅 День",
        "week": "📆 Неделя",
        "month": "🗓 Месяц",
    }
    row1 = []
    row2 = []
    for i, (p, label) in enumerate(periods.items()):
        btn_label = f"✔️ {label}" if p == current_period else label
        btn = InlineKeyboardButton(btn_label, callback_data=f"stats_{p}")
        if i < 2:
            row1.append(btn)
        else:
            row2.append(btn)

    keyboard = [
        row1,
        row2,
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    await update.message.reply_text(
        "👋 *Привет\\! Я бот статистики Tvyze\\.*\n\n"
        "Выбери период для просмотра статистики:",
        parse_mode="MarkdownV2",
        reply_markup=get_main_keyboard()
    )


async def send_stats(query, context, period: str):
    await query.edit_message_text("⏳ Загружаю статистику\\.\\.\\.  ", parse_mode="MarkdownV2", reply_markup=None)

    stats = fetch_stats(period)

    if stats is None:
        await query.edit_message_text(
            "❌ *Ошибка получения данных\\.*\n\nПроверь API или попробуй позже\\.",
            parse_mode="MarkdownV2",
            reply_markup=get_main_keyboard(period)
        )
        return

    if "members" not in stats:
        await query.edit_message_text(
            "⚠️ *Период не поддерживается API\\.*\n\nПопробуй другой период\\.",
            parse_mode="MarkdownV2",
            reply_markup=get_main_keyboard(period)
        )
        return

    text = format_stats(stats, period)

    if len(text) > 4096:
        text = text[:4090] + "\n✂️\\.\\.\\."

    await query.edit_message_text(
        text,
        parse_mode="MarkdownV2",
        reply_markup=get_main_keyboard(period)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return

    data = query.data

    period_map = {
        "stats_hour": "hour",
        "stats_day": "day",
        "stats_week": "week",
        "stats_month": "month",
    }

    if data in period_map:
        period = period_map[data]
        context.user_data["last_period"] = period
    elif data == "refresh":
        period = context.user_data.get("last_period", "day")
    else:
        return

    await send_stats(query, context, period)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    args = context.args
    period = args[0] if args and args[0] in ["hour", "day", "week", "month"] else "day"
    context.user_data["last_period"] = period

    msg = await update.message.reply_text("⏳ Загружаю статистику...")
    stats = fetch_stats(period)

    if stats is None or "members" not in stats:
        await msg.edit_text(
            "❌ Ошибка получения данных или период не поддерживается\\.",
            parse_mode="MarkdownV2",
            reply_markup=get_main_keyboard(period)
        )
        return

    text = format_stats(stats, period)
    if len(text) > 4096:
        text = text[:4090] + "\n✂️\\.\\.\\."

    await msg.edit_text(text, parse_mode="MarkdownV2", reply_markup=get_main_keyboard(period))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
