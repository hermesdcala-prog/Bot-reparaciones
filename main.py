import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)

# Configuración de registro
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURACIÓN DE TUS DATOS INTEGRADOS ---
TOKEN = "8679138341:AAHb_IGSw6ObklEM-_8a6VFG0tip0QDYDDU"
ADMIN_ID = 653054958

# Estados para la conversación de agregar datos (Admin)
MARCA, MODELO, PROBLEMA, SOLUCION_TEXTO, SOLUCION_FOTO = range(5)

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('reparaciones.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS marcas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS modelos (id INTEGER PRIMARY KEY AUTOINCREMENT, marca_id INTEGER, nombre TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS problemas (id INTEGER PRIMARY KEY AUTOINCREMENT, modelo_id INTEGER, titulo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS soluciones (id INTEGER PRIMARY KEY AUTOINCREMENT, problema_id INTEGER, texto TEXT, photo_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- NAVEGACIÓN Y CONSULTA (USUARIOS) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('reparaciones.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM marcas")
    marcas = cursor.fetchall()
    conn.close()

    if not marcas:
        msg = "🛠️ **Base de datos vacía.**\n\nComo eres el administrador, envía /agregar para registrar la primera solución."
        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
        return

    keyboard = [[InlineKeyboardButton(m[1], callback_data=f"marca_{m[0]}")] for m in marcas]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📱 **Selecciona la marca del equipo:**"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def user_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    action = data[0]
    
    conn = sqlite3.connect('reparaciones.db')
    cursor = conn.cursor()

    if action == "marca":
        marca_id = data[1]
        cursor.execute("SELECT id, nombre FROM modelos WHERE marca_id = ?", (marca_id,))
        modelos = cursor.fetchall()
        keyboard = [[InlineKeyboardButton(m[1], callback_data=f"modelo_{m[0]}")] for m in modelos]
        keyboard.append([InlineKeyboardButton("⬅️ Volver a Marcas", callback_data="volver_marcas")])
        await query.edit_message_text("📐 **Selecciona el modelo:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "modelo":
        modelo_id = data[1]
        cursor.execute("SELECT id, titulo FROM problemas WHERE modelo_id = ?", (modelo_id,))
        problemas = cursor.fetchall()
        keyboard = [[InlineKeyboardButton(p[1], callback_data=f"prob_{p[0]}")] for p in problemas]
        keyboard.append([InlineKeyboardButton("⬅️ Volver a Marcas", callback_data="volver_marcas")])
        await query.edit_message_text("⚠️ **Selecciona la falla registrada:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "prob":
        prob_id = data[1]
        cursor.execute("SELECT texto, photo_id FROM soluciones WHERE problema_id = ?", (prob_id,))
        solucion = cursor.fetchone()
        
        keyboard = [[InlineKeyboardButton("⬅️ Inicio", callback_data="volver_marcas")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if solucion:
            texto, photo_id = solucion[0], solucion[1]
            if photo_id:
                await query.message.reply_photo(photo=photo_id, caption=f"🛠 **Solución:**\n\n{texto}", parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await query.edit_message_text(f"🛠 **Solución:**\n\n{texto}", parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await query.edit_message_text("No hay solución registrada aún.", reply_markup=reply_markup)

    elif action == "volver" and data[1] == "marcas":
        conn.close()
        await start(update, context)
        return

    conn.close()

# --- PANEL DE ADMINISTRACIÓN (CARGA DE DATOS) ---
async def agregar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ No tienes permisos de administrador.")
        return ConversationHandler.END

    await update.message.reply_text("➕ **Carga de Datos**\nEscribe el nombre de la **MARCA** (ej: Samsung, Xiaomi, Apple):")
    return MARCA

async def recibir_marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['marca'] = update.message.text.strip()
    await update.message.reply_text(f"Marca: **{context.user_data['marca']}**\n\nAhora escribe el **MODELO** (ej: Redmi Note 10, Galaxy A12):", parse_mode="Markdown")
    return MODELO

async def recibir_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['modelo'] = update.message.text.strip()
    await update.message.reply_text(f"Modelo: **{context.user_data['modelo']}**\n\nEscribe el título de la **FALLA / PROBLEMA** (ej: No carga / Corto en VBUS / Sin imagen):", parse_mode="Markdown")
    return PROBLEMA

async def recibir_problema(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['problema'] = update.message.text.strip()
    await update.message.reply_text("Escribe la **EXPLICACIÓN / SOLUCIÓN** en texto (puedes incluir mediciones, valores o jumpers):", parse_mode="Markdown")
    return SOLUCION_TEXTO

async def recibir_solucion_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['solucion_texto'] = update.message.text.strip()
    await update.message.reply_text(
        "📷 Envía una **FOTO / ESQUEMÁTICO** para la solución.\n(O envía la palabra `omitir` si solo deseas guardar texto):"
    )
    return SOLUCION_FOTO

async def recibir_solucion_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.lower() == 'omitir':
        photo_id = None
    else:
        await update.message.reply_text("Por favor envía una imagen válida o escribe `omitir`.")
        return SOLUCION_FOTO

    conn = sqlite3.connect('reparaciones.db')
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO marcas (nombre) VALUES (?)", (context.user_data['marca'],))
    cursor.execute("SELECT id FROM marcas WHERE nombre = ?", (context.user_data['marca'],))
    marca_id = cursor.fetchone()[0]

    cursor.execute("INSERT INTO modelos (marca_id, nombre) VALUES (?, ?)", (marca_id, context.user_data['modelo']))
    modelo_id = cursor.lastrowid

    cursor.execute("INSERT INTO problemas (modelo_id, titulo) VALUES (?, ?)", (modelo_id, context.user_data['problema']))
    problema_id = cursor.lastrowid

    cursor.execute("INSERT INTO soluciones (problema_id, texto, photo_id) VALUES (?, ?, ?)", 
                   (problema_id, context.user_data['solucion_texto'], photo_id))

    conn.commit()
    conn.close()

    await update.message.reply_text("✅ **¡Solución guardada exitosamente en la base de datos!**\n\nUsa /start para consultar o /agregar para ingresar otra.")
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proceso cancelado.")
    return ConversationHandler.END

# --- INICIALIZACIÓN DEL BOT ---
def main():
    app = Application.builder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('agregar', agregar_start)],
        states={
            MARCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_marca)],
            MODELO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_modelo)],
            PROBLEMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_problema)],
            SOLUCION_TEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_solucion_texto)],
            SOLUCION_FOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), recibir_solucion_foto)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conv)
    app.add_handler(CallbackQueryHandler(user_navigation))

    print("Bot encendido y escuchando...")
    app.run_polling()

if __name__ == '__main__':
    main()
  
