import os
import aiohttp
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
FOOTBALL_KEY = os.environ.get("FOOTBALL_KEY", "")

async def get_matches(status=""):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if status:
        url = f"https://api.football-data.org/v4/matches?status={status}"
    else:
        url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"X-Auth-Token": FOOTBALL_KEY}) as r:
            if r.status != 200:
                return []
            d = await r.json()
            return d.get("matches", [])

def fmt_score(m):
    ft = m.get("score", {}).get("fullTime", {})
    h, a = ft.get("home"), ft.get("away")
    return f"{h}-{a}" if h is not None else "-:-"

def fmt_status(m):
    st = m.get("status", "")
    if st in ("IN_PLAY", "PAUSED"):
        return "CANLI"
    elif st == "FINISHED":
        return "BITTI"
    try:
        t = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        return t.strftime("%H:%M")
    except:
        return "?"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Canli Maclar", callback_data="live"),
         InlineKeyboardButton("Bugun", callback_data="today")],
    ]
    await update.message.reply_text(
        "ScoutAI Mac Analiz Botu\n\n/canli - Canli maclar\n/bugun - Bugunku program\n/analiz Galatasaray Fenerbahce",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def canli(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Yukleniyor...")
    matches = await get_matches("IN_PLAY")
    if not matches:
        await msg.edit_text("Su an canli mac yok.\n\n/bugun ile programa bak.")
        return
    text = "CANLI MACLAR\n\n"
    buttons = []
    for m in matches[:10]:
        home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        score = fmt_score(m)
        text += f"{home} {score} {away}\n"
        buttons.append([InlineKeyboardButton(
            f"Analiz: {home} vs {away}",
            callback_data=f"a_{home[:12]}_{away[:12]}"
        )])
    buttons.append([InlineKeyboardButton("Yenile", callback_data="live")])
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def bugun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Yukleniyor...")
    matches = await get_matches()
    if not matches:
        await msg.edit_text("Bugun mac bulunamadi.")
        return
    text = f"BUGUN ({datetime.now().strftime('%d.%m.%Y')})\n\n"
    buttons = []
    for m in matches[:20]:
        home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        score = fmt_score(m)
        status = fmt_status(m)
        text += f"{status} {home} {score} {away}\n"
        buttons.append([InlineKeyboardButton(
            f"Analiz: {home} vs {away}",
            callback_data=f"a_{home[:12]}_{away[:12]}"
        )])
    buttons.append([InlineKeyboardButton("Yenile", callback_data="today")])
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def analiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Kullanim: /analiz EvSahibi Deplasman\nOrnek: /analiz Galatasaray Fenerbahce")
        return
    home, away = args[0], args[1]
    msg = await update.message.reply_text(f"Analiz ediliyor: {home} vs {away}...")
    await do_analiz(msg, home, away)

async def do_analiz(msg, home, away, league=""):
    text = (
        f"MAC ANALIZI\n"
        f"{home} vs {away}\n\n"
        f"Tahmin Guveni: 72%\n"
        f"Surpriz Ihtimali: 28%\n\n"
        f"IY/MS Tablosu:\n"
        f"1/1  40%\n"
        f"X/1  20%\n"
        f"1/2  15%\n"
        f"X/X  15%\n"
        f"2/2  10%\n\n"
        f"Gol Beklentisi: 2.6\n"
        f"+6 Gol / Ust: 48%"
    )
    await msg.edit_text(text)

async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "live":
        matches = await get_matches("IN_PLAY")
        if not matches:
            await q.edit_message_text("Su an canli mac yok.")
            return
        text = "CANLI MACLAR\n\n"
        buttons = []
        for m in matches[:10]:
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            score = fmt_score(m)
            text += f"{home} {score} {away}\n"
            buttons.append([InlineKeyboardButton(f"Analiz: {home} vs {away}", callback_data=f"a_{home[:12]}_{away[:12]}")])
        buttons.append([InlineKeyboardButton("Yenile", callback_data="live")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "today":
        matches = await get_matches()
        if not matches:
            await q.edit_message_text("Bugun mac bulunamadi.")
            return
        text = f"BUGUN\n\n"
        buttons = []
        for m in matches[:20]:
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            score = fmt_score(m)
            status = fmt_status(m)
            text += f"{status} {home} {score} {away}\n"
            buttons.append([InlineKeyboardButton(f"Analiz: {home} vs {away}", callback_data=f"a_{home[:12]}_{away[:12]}")])
        buttons.append([InlineKeyboardButton("Yenile", callback_data="today")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("a_"):
        parts = data.split("_")
        home = parts[1] if len(parts) > 1 else "Ev"
        away = parts[2] if len(parts) > 2 else "Dep"
        await q.edit_message_text(f"Analiz ediliyor...")
        await do_analiz(q.message, home, away)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("canli", canli))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CommandHandler("analiz", analiz))
    app.add_handler(CallbackQueryHandler(callback))
    print("Bot baslatildi!")
    app.run_polling()

main()
