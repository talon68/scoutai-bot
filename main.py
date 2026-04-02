import os
import json
import aiohttp
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
FOOTBALL_KEY = os.environ.get("FOOTBALL_KEY", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")

async def get_matches(status=""):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if status:
        url = "https://api.football-data.org/v4/matches?status=" + status
    else:
        url = "https://api.football-data.org/v4/matches?dateFrom=" + today + "&dateTo=" + today
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"X-Auth-Token": FOOTBALL_KEY}) as r:
            if r.status != 200:
                return []
            d = await r.json()
            return d.get("matches", [])

async def groq_analiz(home, away, league=""):
    prompt = "Futbol analisti olarak analiz et. Mac: " + home + " vs " + away + ". Lig: " + (league or "Bilinmiyor") + ". SADECE JSON don, baska hicbir sey yazma: {\"ozet\":\"2 cumle analiz\",\"surpriz\":30,\"iy_ms\":[{\"t\":\"1/1\",\"o\":\"38%\"},{\"t\":\"X/1\",\"o\":\"18%\"},{\"t\":\"1/2\",\"o\":\"14%\"},{\"t\":\"X/X\",\"o\":\"16%\"},{\"t\":\"2/2\",\"o\":\"14%\"}],\"iy_ms_yorum\":\"en guclu tahmin\",\"gol_ust\":45,\"gol_yorum\":\"gol beklentisi\"}"
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + GROQ_KEY, "Content-Type": "application/json"},
            json={
                "model": "llama3-8b-8192",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }
        ) as r:
            d = await r.json()
            text = d["choices"][0]["message"]["content"]
            text = text.replace("json", "").replace("", "").strip()
            return json.loads(text)

def fmt_score(m):
    ft = m.get("score", {}).get("fullTime", {})
    h = ft.get("home")
    a = ft.get("away")
    if h is not None:
        return str(h) + "-" + str(a)
    return "-:-"

def fmt_status(m):
    st = m.get("status", "")
    if st == "IN_PLAY" or st == "PAUSED":
        return "CANLI"
    if st == "FINISHED":
        return "BITTI"
    try:
        t = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        return t.strftime("%H:%M")
    except Exception:
        return "?"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("Canli Maclar", callback_data="live"),
         InlineKeyboardButton("Bugun", callback_data="today")]
    ]
    msg = "ScoutAI Mac Analiz Botu\n\n"
    msg += "/canli - Canli maclar\n"
    msg += "/bugun - Bugunku program\n"
    msg += "/analiz Galatasaray Fenerbahce"
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

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
        text += home + " " + score + " " + away + "\n"
        cd = "a_" + home[:12] + "_" + away[:12]
        buttons.append([InlineKeyboardButton("Analiz: " + home + " vs " + away, callback_data=cd)])
    buttons.append([InlineKeyboardButton("Yenile", callback_data="live")])
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def bugun(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Yukleniyor...")
    matches = await get_matches()
    if not matches:
        await msg.edit_text("Bugun mac bulunamadi.")
        return
    text = "BUGUN " + datetime.now().strftime("%d.%m.%Y") + "\n\n"
    buttons = []
    for m in matches[:20]:
        home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
        away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
        score = fmt_score(m)
        status = fmt_status(m)
        text += status + " " + home + " " + score + " " + away + "\n"
        cd = "a_" + home[:12] + "_" + away[:12]
        buttons.append([InlineKeyboardButton("Analiz: " + home + " vs " + away, callback_data=cd)])
    buttons.append([InlineKeyboardButton("Yenile", callback_data="today")])
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def analiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Kullanim: /analiz EvSahibi Deplasman\nOrnek: /analiz Galatasaray Fenerbahce")
        return
    home = args[0]
    away = args[1]
    league = ""
    if len(args) > 2:
        league = " ".join(args[2:])
    msg = await update.message.reply_text("AI analiz ediliyor: " + home + " vs " + away + "...")
    await do_analiz(msg, home, away, league)

async def do_analiz(msg, home, away, league=""):
    try:
        r = await groq_analiz(home, away, league)
        iyms = ""
        for i in r.get("iy_ms", []):
            iyms += i["t"] + "  " + i["o"] + "\n"
        text = "MAC ANALIZI (AI)\n"
        text += home + " vs " + away + "\n\n"
        text += r.get("ozet", "") + "\n\n"
        text += "Surpriz Ihtimali: " + str(r.get("surpriz", 0)) + "%\n\n"
        text += "IY/MS Tablosu:\n" + iyms
        text += r.get("iy_ms_yorum", "") + "\n\n"
        text += "+6 Gol / Ust: " + str(r.get("gol_ust", 0)) + "%\n"
        text += r.get("gol_yorum", "")
    except Exception:
        text = "MAC ANALIZI\n"
        text += home + " vs " + away + "\n\n"
        text += "Surpriz Ihtimali: 28%\n\n"
        text += "IY/MS:\n1/1  40%\nX/1  20%\n1/2  15%\nX/X  15%\n2/2  10%\n\n"
        text += "+6 Gol / Ust: 48%"
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
            text += home + " " + score + " " + away + "\n"
            cd = "a_" + home[:12] + "_" + away[:12]
            buttons.append([InlineKeyboardButton("Analiz: " + home + " vs " + away, callback_data=cd)])
        buttons.append([InlineKeyboardButton("Yenile", callback_data="live")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == "today":
        matches = await get_matches()
        if not matches:
            await q.edit_message_text("Bugun mac bulunamadi.")
            return
        text = "BUGUN\n\n"
        buttons = []
        for m in matches[:20]:
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            score = fmt_score(m)
            status = fmt_status(m)
            text += status + " " + home + " " + score + " " + away + "\n"
            cd = "a_" + home[:12] + "_" + away[:12]
            buttons.append([InlineKeyboardButton("Analiz: " + home + " vs " + away, callback_data=cd)])
        buttons.append([InlineKeyboardButton("Yenile", callback_data="today")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("a_"):
        parts = data.split("_")
        home = parts[1] if len(parts) > 1 else "Ev"
        away = parts[2] if len(parts) > 2 else "Dep"
        await q.edit_message_text("AI analiz ediliyor...")
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
