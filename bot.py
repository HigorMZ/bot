from flask import Flask
from threading import Thread
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, ChatMemberUpdated, ChatMember
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
import feedparser
import asyncio
import os
import time

# 🔐 Configurações
TOKEN = os.environ['TOKEN']
FEED_URL = 'https://nadaenosso.blogspot.com/feeds/posts/default?alt=rss'
chat_ids_file = "chat_ids.txt"
last_post_link = None

# 🔄 Manter online (UptimeRobot)
def keep_alive():
    app = Flask('')

    @app.route('/')
    def home():
        return "✅ Bot está online!"

    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080}).start()

# 📦 Gerenciar chat_ids
def load_chat_ids():
    if not os.path.exists(chat_ids_file):
        return []
    with open(chat_ids_file, "r") as f:
        return list(set(int(line.strip()) for line in f if line.strip().isdigit()))

def save_chat_id(chat_id):
    chat_ids = load_chat_ids()
    if chat_id not in chat_ids:
        with open(chat_ids_file, "a") as f:
            f.write(f"{chat_id}\n")
        print(f"✅ Novo chat registrado: {chat_id}")

# 🔍 Pegar último post
def get_latest_post():
    try:
        feed = feedparser.parse(FEED_URL)
        if not feed.entries:
            return None, None
        latest = feed.entries[0]
        return latest.title, latest.link
    except Exception as e:
        print(f"❌ Erro ao obter feed: {e}")
        return None, None

# 🟢 Comando /start com botões
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📰 Último Post", callback_data='post')],
        [InlineKeyboardButton("🆔 Meu ID", callback_data='meuid')],
        [InlineKeyboardButton("✅ Registrar chat", callback_data='registrar')],
        [InlineKeyboardButton("🆘 Ajuda", callback_data='ajuda')],
        [InlineKeyboardButton("© Direitos Autorais", callback_data='copyright')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Bem-vindo! Use os botões abaixo ou digite um comando.",
        reply_markup=reply_markup
    )

# 📥 Manipula clique dos botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    fake_update = Update(update.update_id, message=query.message)

    if data == 'post':
        await post(fake_update, context)
    elif data == 'meuid':
        await meuid(fake_update, context)
    elif data == 'registrar':
        await registrar(fake_update, context)
    elif data == 'ajuda':
        await help_command(fake_update, context)
    elif data == 'copyright':
        await send_copyright(fake_update, context)

# 📰 /post
async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title, link = get_latest_post()
    if title and link:
        await update.message.reply_text(f"📰 {title}\n🔗 {link}")
    else:
        await update.message.reply_text("⚠️ Nenhum post encontrado no momento.")

# 🆔 /meuid
async def meuid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"🆔 Seu chat ID é: `{chat_id}`", parse_mode="Markdown")

# ✅ /registrar
async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    save_chat_id(chat_id)
    await update.message.reply_text("✅ Chat registrado com sucesso para receber notificações.")

# 🚫 /banir (responda à mensagem do usuário a banir)
async def banir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❗ Use este comando *respondendo* à mensagem do usuário que deseja banir.",
            parse_mode="Markdown"
        )
        return

    user = update.message.reply_to_message.from_user

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"🚫 Usuário @{user.username or user.first_name} foi banido com sucesso.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao banir: {e}")

# 🔇 /silenciar (responda à mensagem do usuário a silenciar, exemplo: /silenciar 5m)
async def silenciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❗ Use este comando *respondendo* à mensagem do usuário que deseja silenciar.\n"
            "Exemplo: responda à mensagem dele e digite `/silenciar 5m`",
            parse_mode="Markdown"
        )
        return

    if not context.args:
        await update.message.reply_text("❌ Use: /silenciar 5m (responda à mensagem do usuário)")
        return

    try:
        user = update.message.reply_to_message.from_user
        tempo = context.args[0]

        if tempo.endswith("m"):
            segundos = int(tempo[:-1]) * 60
        elif tempo.endswith("h"):
            segundos = int(tempo[:-1]) * 3600
        else:
            segundos = int(tempo)

        until_date = int(time.time() + segundos)

        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )

        await update.message.reply_text(f"🔇 @{user.username or user.first_name} foi silenciado por {tempo}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao silenciar: {e}")

# 🆘 /ajuda
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📘 *Comandos disponíveis:*\n"
        "/start - Inicia o bot com botões\n"
        "/post - Mostra o último post do blog\n"
        "/meuid - Mostra seu ID ou do grupo\n"
        "/registrar - Ativa o envio automático de posts\n"
        "/banir - Banir usuário (responda à mensagem)\n"
        "/silenciar - Silenciar usuário (responda à mensagem + tempo, ex: /silenciar 10m)\n"
        "/ajuda - Mostra essa mensagem\n"
        "© Use o botão 'Direitos Autorais' para mais informações",
        parse_mode="Markdown"
    )

# 📜 Direitos Autorais - botão
async def send_copyright(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "© *Direitos Autorais*\n\n"
        "O blog Nada É Nosso respeita os direitos autorais e a legislação vigente.\n"
        "Se você é o proprietário de algum conteúdo indicado no blog e deseja que o link seja removido, "
        "entre em contato conosco pelo e-mail informado na seção de contato e atenderemos sua solicitação o mais breve possível."
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# 🎉 Mensagem de boas-vindas ao entrar no grupo
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🆘 Ajuda", callback_data='ajuda'),
              InlineKeyboardButton("© Direitos Autorais", callback_data='copyright')]]
        )

        welcome_text = (
            f"👋 Olá, {member.mention_html()}! Seja bem-vindo ao grupo.\n\n"
            "Aqui você pode acompanhar as últimas postagens do blog, receber notificações e muito mais.\n"
            "Use /start para ver os comandos ou clique nos botões abaixo."
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

# 🔄 Envio automático de novos posts
async def check_new_posts(context: ContextTypes.DEFAULT_TYPE):
    global last_post_link
    title, link = get_latest_post()
    if not title or not link or link == last_post_link:
        return
    last_post_link = link
    for chat_id in load_chat_ids():
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🆕 Novo post no blog!\n📰 {title}\n🔗 {link}"
            )
            print(f"📤 Enviado para {chat_id}")
        except Exception as e:
            print(f"❌ Erro ao enviar para {chat_id}: {e}")

# ▶️ Inicialização do bot
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("meuid", meuid))
    app.add_handler(CommandHandler("registrar", registrar))
    app.add_handler(CommandHandler("banir", banir))
    app.add_handler(CommandHandler("silenciar", silenciar))
    app.add_handler(CommandHandler("ajuda", help_command))

    # Handler de botões
    app.add_handler(CallbackQueryHandler(button_handler))

    # Handler para boas-vindas (novo membro)
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

    # Tarefa repetitiva: checar novos posts a cada 10 minutos
    app.job_queue.run_repeating(check_new_posts, interval=600, first=10)

    print("🤖 Bot iniciado com sucesso.")
    await app.run_polling()

# ♻️ Executa tudo
keep_alive()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())
