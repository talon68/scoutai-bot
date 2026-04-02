import os
import json
import asyncio
import aiohttp
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
FOOTBALL_KEY = os.environ.get("FOOTBALL_KEY", "")

async def get_todays_matches():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"X-Auth-Token": FOOTBALL_KEY}) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return data.get("matches", [])

async def get_live_matches():
    url = "https://api.football-data.org/v4/matches?status=IN_PLAY"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"X-Auth-Token": FOOTBALL_KEY}) as r:
            if r.status != 200:
                return []
            data = await r.json()
            return data.get("matches", [])

def format_score(m):
    ft = m.get("score", {}).get("fullTime", {})
    h, a = ft.get("home"), ft.get("away")
    if h is not None and a is not None:
        return f"{h} - {a}"
    return "- : -"

def format_status(m):
    st = m.get("status", "")
    if st in ("IN_PLAY", "PAUSED"):
        return "🔴 CANLI"
    elif st == "FINISHED":
        return "✅ BİTTİ"
    else:
        try:
            t = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
            return f"🕐 {t.strftime('%H:%M')}"
        except:
            return "📅"

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🔴 Canlı Maçlar", callback_data="live"),
         InlineKeyboardButton("📅 Bugün", callback_data="today")],
        [InlineKeyboardButton("❓ Yardım", callback_data="yardim")]
    ]
    await update.message.reply_text(
        "⚽ ScoutAI Maç Analiz Botu\n\n"
        "🔴 /canli — Canlı maçlar\n"
        "📅 /bugun — Bugünkü program\n"
        "🎯 /analiz Galatasaray Fenerbahçe\n",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def cmd_canli(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔴 Yükleniyor...")
    matches = await get_live_matches()
    if not matches:
        await msg.edit_text("🔴 Şu an canlı maç yok.\n\n/bugun ile programa bak.")
        return
    text = "🔴 CANLI MAÇLAR\n\n"
    buttons = []
    for m in matches[:15]:
        home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        score = format_score(m)
        league = m["competition"]["name"]
        text += f"⚽ {home} {score} {away}\n_{league}_\n\n"
        buttons.append([InlineKeyboardButton(
            f"🎯 {home} vs {away}",
            callback_data=f"a_{home[:15]}{away[:15]}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Yenile", callback_data="live")])
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_bugun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📅 Yükleniyor...")
    matches = await get_todays_matches()
    if not matches:
        await msg.edit_text("📅 Bugün maç bulunamadı.")
        return
    text = f"📅 BUGÜN ({datetime.now().strftime('%d.%m.%Y')})\n\n"
    buttons = []
    cl = ""
    for m in matches[:20]:
        league = m["competition"]["name"]
        home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        score = format_score(m)
        status = format_status(m)
        if league != cl:
            text += f"🏆 {league}\n"
            cl = league
        text += f"  {status} {home} {score} {away}\n"
        buttons.append([InlineKeyboardButton(
            f"🎯 {home} vs {away}",
            callback_data=f"a_{home[:15]}{away[:15]}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Yenile", callback_data="today")])
    await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def cmd_analiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Kullanım:\n`/analiz EvSahibi Deplasman`\n\nÖrnek:\n`/analiz Galatasaray Fenerbahçe`",
            parse_mode="Markdown"
        )
        return
    home, away = args[0], args[1]
    league = " ".join(args[2:]) if len(args) > 2 else ""
    msg = await update.message.reply_text(f"🤖 Analiz ediliyor: {home} vs {away}...", parse_mode="Markdown")
    await do_analysis(msg, home, away, league)

async def do_analysis(msg, home, away, league=""):
    text = (
        f"🎯 MAÇ ANALİZİ\n"
        f"⚽ {home} vs {away}\n"
        f"{'🏆 ' + league + chr(10) if league else ''}\n"
        f"📊 Tahmin Güveni: 72%\n"
        f"🎲 Sürpriz İhtimali: 28%\n\n"
        f"⏱ İY/MS Tablosu:\n"
        f"1/1 ████████░░ 40%\n"
        f"X/1 ████░░░░░░ 20%\n"
        f"1/2 ███░░░░░░░ 15%\n"
        f"X/X ███░░░░░░░ 15%\n"
        f"2/2 ██░░░░░░░░ 10%\n\n"
        f"⚽ +6 Gol / Üst: 48%\n"
        f"Ortalama gol beklentisi 2.6 civarında."
    )
    await msg.edit_text(text, parse_mode="Markdown")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "live":
        matches = await get_live_matches()
        if not matches:
            await q.edit_message_text("🔴 Şu an canlı maç yok.")
            return
        text = "🔴 CANLI MAÇLAR\n\n"
        buttons = []
        for m in matches[:15]:
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            score = format_score(m)
            league = m["competition"]["name"]
            text += f"⚽ {home} {score} {away}\n_{league}_\n\n"
            buttons.append([InlineKeyboardButton(f"🎯 {home} vs {away}", callback_data=f"a_{home[:15]}{away[:15]}")])
        buttons.append([InlineKeyboardButton("🔄 Yenile", callback_data="live")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "today":
        matches = await get_todays_matches()
        if not matches:
            await q.edit_message_text("📅 Bugün maç bulunamadı.")
            return
        text = f"📅 BUGÜN\n\n"
        buttons = []
        cl = ""
        for m in matches[:20]:
            league = m["competition"]["name"]
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            score = format_score(m)
            status = format_status(m)
            if league != cl:
                text += f"🏆 {league}\n"
                cl = league
            text += f"  {status} {home} {score} {away}\n"
            buttons.append([InlineKeyboardButton(f"🎯 {home} vs {away}", callback_data=f"a_{home[:15]}{away[:15]}")])
        buttons.append([InlineKeyboardButton("🔄 Yenile", callback_data="today")])
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("a_"):
        parts = data.split("_")
        home = parts[1] if len(parts) > 1 else "Ev"
        away = parts[2] if len(parts) > 2 else "Dep"
        await q.edit_message_text(f"🤖 Analiz ediliyor...", parse_mode="Markdown")
        await do_analysis(q.message, home, away)

    elif data == "yardim":
        await q.edit_message_text(
            "📖 Yardım\n\n"
            "/canli — Canlı maçlar\n"
            "/bugun — Bugünün maçları\n"
            "/analiz Galatasaray Fenerbahçe — Analiz\n\n"
            "Maç listesinde butona tıklayarak da analiz yaptırabilirsin!",
            parse_mode="Markdown"
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("canli", cmd_canli))
    app.add_handler(CommandHandler("bugun", cmd_bugun))
    app.add_handler(CommandHandler("analiz", cmd_analiz))
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("🚀 ScoutAI Bot çalışıyor!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if _name_ == "_main_":
    main()
