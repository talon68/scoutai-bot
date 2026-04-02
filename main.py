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
    url = f"https://api.football-data.org/v4/matches?status={status}" if status else f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={today}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers={"X-Auth-Token": FOOTBALL_KEY}) as r:
            if r.status != 200:
                return []
            d = await r.json()
            return d.get("matches", [])

async def groq_analiz(home, away, league=""):
    prompt = f"""Futbol mac analisti olarak su maci analiz et:
Mac: {home} vs {away}
Lig: {league or 'Bilinmiyor'}

SADECE JSON don:
{{"ozet":"2 cumle analiz","surpriz":30,"iy_ms":[{{"t":"1/1","o":"38%"}},{{"t":"X/1","o":"18%"}},{{"t":"1/2","o":"14%"}},{{"t":"X/X","o":"16%"}},{{"t":"2/2","o":"14%"}}],"iy_ms_yorum":"en guclu tahmin","gol_ust":45,"gol_yorum":"gol beklentisi"}}"""

    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama3-8b-8192", "max_tokens": 500,
                  "messages": [{"role": "user", "content": prompt}]}
        ) as r:
            d = await r.json()
            text = d["choices"][0]["message"]["content"]
            clean = text.replace("json", "").replace("", "").strip()
            return json.loads(clean)

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
    kb = [[InlineKeyboardButton("Canli Maclar", callback_data="live"),
           InlineKeyboardButton("Bugun", callback_data="today")]]
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
        buttons.append([InlineKeyboardButton(f"Analiz: {home} vs {away}", callback_data=f"a_{home[:12]}_{away[:12]}")])
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
        buttons.append([InlineKeyboardButton(f"Analiz: {home} vs {away}", callback_data=f"a_{home[:12]}_{away[:12]}")])
    buttons.append([InlineKeyboardButton("Yenile", callback_data="today")])
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

async def analiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Kullanim: /analiz EvSahibi Deplasman\nOrnek: /analiz Galatasaray Fenerbahce")
        return
    home, away = args[0], args[1]
    league = " ".join(args[2:]) if len(args) > 2 else ""
    msg = await update.message.reply_text(f"AI analiz ediliyor: {home} vs {away}...")
    await do_analiz(msg, home, away, league)

async def do_analiz(msg, home, away, league=""):
    try:
        r = await groq_analiz(home, away, league)
        iyms = "\n".join([f"{i['t']}  {i['o']}" for i in r.get("iy_ms", [])])
        text = (
            f"MAC ANALIZI (AI)\n"
            f"{home} vs {away}\n\n"
            f"{r.get('ozet', '')}\n\n"
            f"Surpriz Ihtimali: {r.get('surpriz', 0)}%\n\n"
            f"IY/MS Tablosu:\n{iyms}\
