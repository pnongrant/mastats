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


def format_number(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n) if n is not None else "—"


def format_stats(data: dict, period: str) -> str:
    period_names = {
        "hour": "⏰ Час",
        "day": "📅 День",
        "week": "📆 Неделя",
        "month": "🗓 Месяц"
    }
    period_label = period_names.get(period, period)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    lines = [
        f"╔══════════════════════════╗",
        f"║  📊 СТАТИСТИКА TVYZE     ║",
        f"╚══════════════════════════╝",
        f"",
        f"🕐 Период: *{period_label}*",
        f"🔄 Обновлено: `{now}`",
        f"",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if isinstance(data, dict):
        emoji_map = {
            "views": "👁 Просмотры",
            "visitors": "👤 Посетители",
            "unique_visitors": "🧑 Уник. посетители",
            "clicks": "🖱 Клики",
            "revenue": "💰 Доход",
            "impressions": "📢 Показы",
            "ctr": "🎯 CTR",
            "conversions": "✅ Конверсии",
            "sessions": "🔗 Сессии",
            "bounce_rate": "↩️ Отказы",
            "avg_session": "⏱ Ср. сессия",
            "pageviews": "📄 Страниц",
            "events": "⚡ События",
            "signups": "📝 Регистрации",
            "purchases": "🛒 Покупки",
            "total": "📦 Всего",
            "count": "🔢 Количество",
        }

        found_any = False
        for key, value in data.items():
            if isinstance(value, (int, float, str)):
                label = emoji_map.get(key, f"▪️ {key.replace('_', ' ').capitalize()}")
                if isinstance(value, float):
                    if "rate" in key or "ctr" in key:
                        formatted = f"{value:.2f}%"
                    else:
                        formatted = f"{value:.2f}"
                elif isinstance(value, int):
                    formatted = format_number(value)
                else:
                    formatted = str(value)

                lines.append(f"{label}: *{formatted}*")
                found_any = True

        if not found_any:
            lines.append("⚠️ Нет данных для отображения")

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"")
                lines.append(f"📌 *{key.replace('_', ' ').upper()}*")
                for sub_key, sub_val in value.items():
                    if isinstance(sub_val, (int, float, str)):
                        label = emoji_map.get(sub_key, f"  ▫️ {sub_key.replace('_', ' ').capitalize()}")
                        lines.append(f"  {label}: *{sub_val}*")
    else:
        lines.append(f"📦 Данные: `{str(data)[:500]}`")

    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⏰ Час", callback_data="stats_hour"),
            InlineKeyboardButton("📅 День", callback_data="stats_day"),
        ],
        [
            InlineKeyboardButton("📆 Неделя", callback_data="stats_week"),
            InlineKeyboardButton("🗓 Месяц", callback_data="stats_month"),
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="refresh"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    await update.message.reply_text(
        "👋 *Привет! Я бот статистики Tvyze.*\n\n"
        "Выбери период для просмотра статистики:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(update):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return

    data = query.data

    if data == "stats_hour":
        period = "hour"
    elif data == "stats_day":
        period = "day"
    elif data == "stats_week":
        period = "week"
    elif data == "stats_month":
        period = "month"
    elif data == "refresh":
        period = context.user_data.get("last_period", "day")
    else:
        return

    context.user_data["last_period"] = period

    await query.edit_message_text(
        "⏳ Загружаю статистику...",
        reply_markup=None
    )

    stats = fetch_stats(period)

    if stats is None:
        await query.edit_message_text(
            "❌ *Ошибка получения данных.*\n\nПроверь API или попробуй позже.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    text = format_stats(stats, period)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    args = context.args
    period = args[0] if args and args[0] in ["hour", "day", "week", "month"] else "day"

    msg = await update.message.reply_text("⏳ Загружаю статистику...")

    stats = fetch_stats(period)
    if stats is None:
        await msg.edit_text("❌ Ошибка получения данных.")
        return

    text = format_stats(stats, period)
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
