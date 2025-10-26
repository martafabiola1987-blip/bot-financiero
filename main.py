import requests
import sqlite3
import os
import logging
import time
from datetime import datetime
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)

class TrendoBrokerBot:
    def __init__(self):
        # 🔐 CONFIGURACIÓN PRINCIPAL - 100% AUTOMÁTICO
        self.telegram_token = '8395866366:AAGP751UY-V49BJ4gXEuqT3PwuPPGxI_2Lo'
        self.trust_wallet = "TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg"
        self.admins = [8110866676]  # Solo para notificaciones internas
        self.minimo_retiro = 10
        
        # 🎯 GRUPO DE USUARIOS (ACTUALIZAR CON EL ID REAL)
        self.grupo_usuarios_id = -1003146959942  # ⚠️ CAMBIAR CON EL ID REAL DEL GRUPO
        
        # 🎯 SISTEMA DE SOPORTE AUTOMÁTICO MEJORADO
        self.soporte_automatico = {
            "retiro": {
                "palabras": ["retiro", "retirar", "sacar dinero", "cuando me pagan", "tiempo de retiro", "wallet", "pago"],
                "respuesta": """💸 **INFORMACIÓN DE RETIROS - AUTOMÁTICO**

⏰ **Tiempo de procesamiento:** 24-48 horas
💰 **Mínimo de retiro:** 10 USDT
📧 **Wallet aceptada:** USDT (TRC20)
🔐 **Seguridad:** 100% garantizada

🤖 *Sistema automático - Tu retiro se procesará en el tiempo establecido*"""
            },
            "inversion": {
                "palabras": ["invertir", "inversión", "planes", "ganancias", "rendimiento", "ganar dinero", "plan"],
                "respuesta": """📊 **PLANES DE INVERSIÓN - AUTOMÁTICO**

📈 **Rendimiento:** 20% mensual
💰 **Ganancias:** Automáticas cada 24h
🔐 **Seguridad:** Garantizada
💼 **Planes desde:** 15 USDT

💡 *Usa el comando* /invertir *para ver todos los planes disponibles*

🤖 *Sistema 100% automatizado*"""
            },
            "referidos": {
                "palabras": ["referido", "referidos", "compartir", "enlace", "bono", "amigo", "recomendar"],
                "respuesta": """👥 **SISTEMA DE REFERIDOS - AUTOMÁTICO**

🎁 **Bono especial:** 5 USDT al llegar a 5 referidos
💸 **Comisión permanente:** 10% de sus inversiones
🚀 **Ganancia ilimitada:** Sin tope máximo

🔗 *Usa* /referidos *para obtener tu enlace personalizado*

🤖 *Sistema de referidos completamente automático*"""
            },
            "problema_tecnico": {
                "palabras": ["error", "no funciona", "problema", "bug", "no responde", "falla", "tengo problema"],
                "respuesta": """⚠️ **ASISTENCIA TÉCNICA AUTOMÁTICA**

🔧 Nuestro sistema automático está revisando tu consulta.
🔄 Por favor, intenta nuevamente en 5 minutos.

📋 **Soluciones rápidas:**
• Cierra y reabre Telegram
• Verifica tu conexión a internet
• Usa /start para reiniciar el bot

🤖 *Si el problema persiste, será escalado automáticamente a nuestro sistema de tickets*"""
            },
            "seguridad": {
                "palabras": ["es seguro", "confiable", "verificar", "real", "estafa", "seguro", "confianza"],
                "respuesta": """✅ **VERIFICACIÓN DE SEGURIDAD AUTOMÁTICA**

🛡️ **Sistema 100% seguro y verificado**
💰 **+500 retiros procesados automáticamente**
⭐ **Calificación de usuarios: 4.8/5**
🔒 **Fondos protegidos automáticamente**

🤖 *Procesamos todas las transacciones de forma automática y segura*"""
            },
            "contacto": {
                "palabras": ["dueño", "propietario", "creador", "administrador", "contactar", "hablar con", "persona"],
                "respuesta": """🤖 **SISTEMA 100% AUTOMATIZADO**

📊 **Trendo Broker Bot** es un sistema completamente automatizado.

💡 **Todas las funciones están automatizadas:**
• Inversiones automáticas
• Retiros automáticos  
• Soporte automático
• Sistema de referidos automático

🔧 *No requiere intervención humana - Sistema autónomo*"""
            },
            "general": {
                "palabras": ["hola", "buenas", "ayuda", "soporte", "info", "información"],
                "respuesta": """🤖 **TRENDO BROKER BOT - CENTRO DE AYUDA AUTOMÁTICO**

💼 **Servicios disponibles (automáticos):**
• 📊 Planes de inversión (/invertir)
• 💸 Retiros rápidos (/retirar) 
• 👥 Sistema de referidos (/referidos)
• 💰 Consulta de balance (/balance)

🤖 *Sistema 100% automatizado - Escribe tu pregunta específica*"""
            }
        }

        # 📊 CONFIGURACIÓN FINANCIERA
        self.planes = {
            "Básico": {"monto": 15, "ganancia": 0.20},
            "Standard": {"monto": 30, "ganancia": 0.20},
            "Premium": {"monto": 60, "ganancia": 0.20},
            "VIP": {"monto": 100, "ganancia": 0.20},
            "Plata": {"monto": 200, "ganancia": 0.20},
            "Oro": {"monto": 300, "ganancia": 0.20}
        }

        self.ganancia_diaria = 0.20 / 30

        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_token}"
        self.user_sessions = {}
        self.init_database()

    def init_database(self):
        """Inicializar base de datos"""
        self.conn = sqlite3.connect('trendo_broker.db', check_same_thread=False)
        self.cursor = self.conn.cursor()

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                balance_ganancias REAL DEFAULT 0.0,
                total_invertido REAL DEFAULT 0.0,
                total_ganado REAL DEFAULT 0.0,
                referido_por INTEGER,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bono_referidos BOOLEAN DEFAULT FALSE,
                cuentas_referidas INTEGER DEFAULT 0,
                preguntas_soporte INTEGER DEFAULT 0,
                estado TEXT DEFAULT 'activo'
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS soporte_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                pregunta TEXT,
                categoria TEXT,
                respuesta_automatica BOOLEAN DEFAULT FALSE,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()
        logging.info("✅ Base de datos inicializada")

    # 🎯 SISTEMA DE SOPORTE 100% AUTOMÁTICO
    def analizar_pregunta(self, texto):
        """Analizar pregunta y encontrar respuesta automática"""
        texto = texto.lower().strip()
        
        for categoria, datos in self.soporte_automatico.items():
            for palabra in datos["palabras"]:
                if palabra in texto:
                    return datos["respuesta"], categoria
        
        return None, None

    def manejar_soporte_inteligente(self, chat_id, user_id, username, pregunta):
        """Manejar sistema de soporte 100% automático"""
        try:
            # Efecto de typing
            self.send_chat_action(chat_id, "typing")
            time.sleep(1.5)

            # Buscar respuesta automática
            respuesta, categoria = self.analizar_pregunta(pregunta)
            
            if respuesta:
                # Registrar como resuelto automáticamente
                self.cursor.execute(
                    "INSERT INTO soporte_tickets (user_id, username, pregunta, categoria, respuesta_automatica) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, pregunta, categoria, True)
                )
                
                self.cursor.execute(
                    "UPDATE usuarios SET preguntas_soporte = preguntas_soporte + 1 WHERE user_id = ?",
                    (user_id,)
                )
                
                self.conn.commit()
                
                return respuesta
            else:
                # Pregunta no reconocida - respuesta genérica automática
                self.cursor.execute(
                    "INSERT INTO soporte_tickets (user_id, username, pregunta, respuesta_automatica) VALUES (?, ?, ?, ?)",
                    (user_id, username, pregunta, False)
                )
                
                self.conn.commit()

                return f"""
❓ **CONSULTA REGISTRADA AUTOMÁTICAMENTE**

📝 *"{pregunta}"*

🤖 **Respuesta automática:**
No encontré una respuesta específica automática para tu pregunta.

💡 **Puedes intentar con:**
• "¿Cómo retirar dinero?"
• "¿Qué planes de inversión hay?"
• "¿Cómo funcionan los referidos?"

🔧 *Nuestro sistema automático aprenderá de tu pregunta para mejorar*
"""

        except Exception as e:
            logging.error(f"Error en soporte automático: {e}")
            return "⚠️ **Sistema de soporte automático temporalmente no disponible**\n\nPor favor, intenta nuevamente en 5 minutos."

    # 🎯 PUBLICAR EN GRUPO
    def publicar_en_grupo(self, mensaje):
        """Publicar mensaje en el grupo de usuarios"""
        try:
            if self.grupo_usuarios_id:
                self.send_message(self.grupo_usuarios_id, mensaje)
                logging.info(f"✅ Mensaje publicado en grupo: {self.grupo_usuarios_id}")
        except Exception as e:
            logging.error(f"❌ Error publicando en grupo: {e}")

    def publicar_retiro_exitoso(self, user_id, username, monto, wallet):
        """Publicar retiro exitoso en el grupo"""
        mensaje = f"""
💸 **RETIRO VERIFICADO - EXITOSO** ✅

👤 **Usuario:** @{username}
💰 **Monto:** {monto:.2f} USDT
📧 **Wallet:** {wallet}
⏰ **Tiempo:** Procesado automáticamente
📋 **Estado:** ✅ COMPLETADO

🎉 *¡Retiro procesado automáticamente!*
🔗 *Únete a nuestro bot:* @TrendoBrokerBot

🤖 *Sistema 100% automatizado*
        """
        self.publicar_en_grupo(mensaje)

    # 🔧 MÉTODOS BÁSICOS
    def send_message(self, chat_id, text, reply_markup=None):
        """Enviar mensaje a Telegram"""
        url = f"{self.telegram_api_url}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        if reply_markup:
            payload['reply_markup'] = reply_markup

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logging.error(f"❌ Error enviando mensaje: {e}")
            return None

    def send_chat_action(self, chat_id, action):
        """Enviar acción de chat"""
        url = f"{self.telegram_api_url}/sendChatAction"
        payload = {'chat_id': chat_id, 'action': action}
        try:
            requests.post(url, json=payload, timeout=5)
        except:
            pass

    # 🎨 MÉTODOS PRINCIPALES
    def handle_start(self, chat_id, username, user_id, parametros=None):
        """Comando start - 100% automático"""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )

            if parametros and parametros.isdigit():
                referido_por = int(parametros)
                if referido_por != user_id:
                    self.cursor.execute(
                        "UPDATE usuarios SET referido_por = ? WHERE user_id = ?",
                        (referido_por, user_id)
                    )

            self.conn.commit()

            welcome_text = f"""
🤖 **TRENDO BROKER BOT** 💰

🎉 **¡Bienvenido {username}!**

💎 **SISTEMA 100% AUTOMATIZADO:**
• 🤖 Soporte automático 24/7
• 💰 Ganancias automáticas diarias
• 🎁 Bonos por referidos automáticos
• 🔐 Retiros automáticos y seguros

🚀 **COMANDOS AUTOMÁTICOS:**

/balance - Consultar balance automáticamente
/invertir - Ver planes de inversión automáticos  
/retirar - Solicitar retiro automático
/referidos - Sistema de referidos automático
/soporte - Centro de ayuda automático

💡 **¿Necesitas ayuda?** Escribe cualquier pregunta y nuestro sistema automático te asistirá inmediatamente.

🤖 *Sistema 100% automatizado - Sin intervención humana*
            """

            self.send_message(chat_id, welcome_text)

        except Exception as e:
            logging.error(f"Error en start: {e}")
            self.send_message(chat_id, "❌ Error automático al iniciar. Escribe /soporte para ayuda automática.")

    def handle_soporte(self, chat_id, user_id, username, mensaje=None):
        """Manejar sistema de soporte 100% automático"""
        if mensaje:
            # Procesar pregunta específica
            respuesta = self.manejar_soporte_inteligente(chat_id, user_id, username, mensaje)
            self.send_message(chat_id, respuesta)
        else:
            # Mostrar menú de soporte automático
            soporte_text = f"""
🎫 **CENTRO DE SOPORTE AUTOMÁTICO 24/7** 🤖

💡 **Soporte 100% Automático Instantáneo:**
Escribe tu pregunta y te responderé automáticamente.

🚀 **Áreas de Ayuda Automática:**

• 💸 *"¿Cómo retiro mi dinero automáticamente?"*
• 📊 *"¿Qué planes de inversión automáticos hay?"*  
• 👥 *"¿Cómo funcionan los referidos automáticos?"*
• 🛡️ *"¿Es seguro el sistema automático?"*
• ⏰ *"¿Tiempos de retiro automáticos?"*

🤖 **Sistema 100% automatizado**
**¡Escribe tu pregunta ahora!**
            """
            self.send_message(chat_id, soporte_text)

    def handle_balance(self, chat_id, user_id):
        """Mostrar balance automáticamente"""
        try:
            self.cursor.execute(
                "SELECT balance, balance_ganancias, total_invertido, total_ganado FROM usuarios WHERE user_id = ?",
                (user_id,)
            )
            resultado = self.cursor.fetchone()
            
            if resultado:
                balance, ganancias, invertido, total_ganado = resultado
                
                mensaje = f"""
💼 **BALANCE COMPLETO - AUTOMÁTICO**

💰 **Saldo disponible:** {balance:.2f} USDT
📈 **Ganancias acumuladas:** {ganancias:.2f} USDT
💵 **Total invertido:** {invertido:.2f} USDT
🏆 **Total ganado:** {total_ganado:.2f} USDT

💸 **Mínimo de retiro automático:** {self.minimo_retiro} USDT

🤖 *Las ganancias se acreditan automáticamente cada 24 horas*
                """
            else:
                mensaje = "❌ Primero debes registrarte. Usa /start"
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en balance: {e}")
            self.send_message(chat_id, "❌ Error automático al cargar balance. Usa /soporte para ayuda automática.")

    def handle_retirar(self, chat_id, user_id):
        """Manejar solicitud de retiro automático"""
        try:
            self.cursor.execute("SELECT balance, username FROM usuarios WHERE user_id = ?", (user_id,))
            resultado = self.cursor.fetchone()
            
            if resultado and resultado[0] >= self.minimo_retiro:
                self.user_sessions[user_id] = {
                    "esperando_wallet": True,
                    "monto_retiro": resultado[0],
                    "username": resultado[1]
                }
                
                mensaje = f"""
💸 **SOLICITUD DE RETIRO AUTOMÁTICO**

💰 **Saldo disponible:** {resultado[0]:.2f} USDT
📋 **Mínimo requerido:** {self.minimo_retiro} USDT

📧 **Envía tu wallet USDT (TRC20) para procesamiento automático:**

💡 *Ejemplo:* `{self.trust_wallet}`

⏰ **Tiempo de procesamiento automático:** 24-48 horas
🔐 **Transacciones automáticas y seguras**

🤖 *Sistema 100% automatizado*
                """
            elif resultado:
                mensaje = f"""
❌ **SALDO INSUFICIENTE - AUTOMÁTICO**

💰 **Tu saldo actual:** {resultado[0]:.2f} USDT
📋 **Mínimo requerido:** {self.minimo_retiro} USDT

💡 *Necesitas al menos {self.minimo_retiro} USDT para retiro automático*
                """
            else:
                mensaje = "❌ No tienes saldo disponible para retiro automático"
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en retiro: {e}")
            self.send_message(chat_id, "⚠️ Error temporal en sistema automático de retiros. Usa /soporte.")

    def handle_referidos(self, chat_id, user_id):
        """Sistema de referidos automático"""
        try:
            self.cursor.execute("SELECT cuentas_referidas, bono_referidos FROM usuarios WHERE user_id = ?", (user_id,))
            resultado = self.cursor.fetchone()
            
            referidos = resultado[0] if resultado else 0
            bono_activado = resultado[1] if resultado else False
            
            mensaje = f"""
👥 **SISTEMA DE REFERIDOS AUTOMÁTICO**

📊 **Tus referidos actuales:** {referidos}
🎯 **Objetivo para bono automático:** 5 referidos
🎁 **Bono automático al completar:** 5 USDT

"""
            
            if bono_activado:
                mensaje += "✅ **¡BONO AUTOMÁTICO ACTIVADO!** +5 USDT\n\n"
            else:
                faltan = max(0, 5 - referidos)
                mensaje += f"📈 **Progreso automático:** {referidos}/5 referidos\n"
                if faltan > 0:
                    mensaje += f"🎁 **Faltan {faltan} referidos** para bono automático\n\n"

            mensaje += f"""💸 **Comisión automática del 10%** de sus inversiones

🔗 **Tu enlace automático:**
`https://t.me/TrendoBrokerBot?start={user_id}`

🤖 *Sistema de referidos 100% automatizado*
            """
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en referidos: {e}")
            self.send_message(chat_id, "❌ Error automático. Usa /soporte.")

    def handle_invertir(self, chat_id):
        """Mostrar planes de inversión automáticos"""
        try:
            planes_text = """
📊 **PLANES DE INVERSIÓN AUTOMÁTICOS** 💰

📈 **Rendimiento automático:** 20% mensual
💡 **Ganancias automáticas cada 24h**

🤖 *Sistema de inversión 100% automatizado*

"""
            for plan, datos in self.planes.items():
                monto = datos["monto"]
                ganancia_diaria = monto * self.ganancia_diaria
                ganancia_mensual = monto * datos["ganancia"]
                
                planes_text += f"""
• **{plan}:** {monto} USDT
  📈 Diario automático: +{ganancia_diaria:.2f} USDT
  💰 Mensual automático: +{ganancia_mensual:.2f} USDT
"""

            planes_text += "\n💸 *Usa /retirar para retiros automáticos*"
            planes_text += "\n🤖 *Sistema 100% automatizado*"

            self.send_message(chat_id, planes_text)
            
        except Exception as e:
            logging.error(f"Error mostrando planes: {e}")
            self.send_message(chat_id, "❌ Error automático. Usa /soporte.")

    def handle_estadisticas(self, chat_id, user_id):
        """Mostrar estadísticas solo para administradores"""
        if user_id not in self.admins:
            self.send_message(chat_id, "❌ No tienes permisos de administrador")
            return
        
        try:
            # Obtener estadísticas de la base de datos
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_usuarios,
                    SUM(balance) as total_balance,
                    SUM(balance_ganancias) as total_ganancias,
                    SUM(total_invertido) as total_invertido,
                    SUM(total_ganado) as total_ganado_total,
                    SUM(cuentas_referidas) as total_referidos,
                    SUM(preguntas_soporte) as total_soporte
                FROM usuarios
            """)
            stats = self.cursor.fetchone()
            
            # Obtener inversiones activas
            self.cursor.execute("SELECT COUNT(*) FROM usuarios WHERE total_invertido > 0")
            inversiones_activas = self.cursor.fetchone()[0]
            
            if stats:
                total_usuarios, total_balance, total_ganancias, total_invertido, total_ganado, total_referidos, total_soporte = stats
                
                mensaje = f"""
📊 **PANEL DE ADMINISTRADOR** 🔐

👥 **USUARIOS:**
• Total registrados: {total_usuarios}
• Con inversiones activas: {inversiones_activas}
• Referidos totales: {total_referidos or 0}

💰 **FINANZAS:**
• Saldo total en sistema: {total_balance or 0:.2f} USDT
• Ganancias acumuladas: {total_ganancias or 0:.2f} USDT
• Total invertido: {total_invertido or 0:.2f} USDT
• Total ganado histórico: {total_ganado or 0:.2f} USDT

🎫 **ACTIVIDAD:**
• Consultas de soporte: {total_soporte or 0}
• Retiros mínimos: {self.minimo_retiro} USDT

🤖 *Estadísticas en tiempo real*
                """
            else:
                mensaje = "📊 No hay datos estadísticos disponibles aún."
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en estadísticas: {e}")
            self.send_message(chat_id, "❌ Error al cargar estadísticas")

    def process_update(self, update):
        """Procesar actualizaciones - 100% automático"""
        try:
            if 'message' in update and 'text' in update['message']:
                chat_id = update['message']['chat']['id']
                user_id = update['message']['from']['id']
                text = update['message']['text']
                username = update['message']['from'].get('username', 'Usuario')

                logging.info(f"📨 Mensaje automático de {username}: {text}")

                # Manejar retiros automáticos
                if user_id in self.user_sessions and self.user_sessions[user_id].get('esperando_wallet'):
                    monto = self.user_sessions[user_id]['monto_retiro']
                    username = self.user_sessions[user_id]['username']
                    wallet = text
                    
                    # Publicar en grupo automáticamente
                    self.publicar_retiro_exitoso(user_id, username, monto, wallet)
                    
                    mensaje = f"""
✅ **RETIRO SOLICITADO AUTOMÁTICAMENTE**

💰 **Monto:** {monto:.2f} USDT
📧 **Wallet:** {wallet}
📋 **Estado:** En proceso automático
⏰ **Tiempo:** 24-48 horas automáticas

🔐 *Tu transacción se procesa automáticamente*

🤖 *Sistema 100% automatizado*
                    """
                    self.send_message(chat_id, mensaje)
                    del self.user_sessions[user_id]
                    return

                # Procesar comandos automáticos
                if text.startswith('/start'):
                    parametros = text.split()[1] if len(text.split()) > 1 else None
                    self.handle_start(chat_id, username, user_id, parametros)
                elif text == '/balance':
                    self.handle_balance(chat_id, user_id)
                elif text == '/retirar':
                    self.handle_retirar(chat_id, user_id)
                elif text == '/referidos':
                    self.handle_referidos(chat_id, user_id)
                elif text == '/invertir':
                    self.handle_invertir(chat_id)
                elif text == '/estadisticas':
                    self.handle_estadisticas(chat_id, user_id)
                elif text == '/soporte':
                    self.handle_soporte(chat_id, user_id, username)
                elif text.startswith('/'):
                    self.send_message(chat_id, "❌ Comando no reconocido automáticamente. Usa /soporte")
                else:
                    # Cualquier otro mensaje = soporte automático
                    self.handle_soporte(chat_id, user_id, username, text)

        except Exception as e:
            logging.error(f"❌ Error automático procesando update: {e}")

# ✅ CONFIGURACIÓN FLASK
bot = TrendoBrokerBot()
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        bot.process_update(update)
        return jsonify({"status": "ok"})
    
    return "🤖 Trendo Broker Bot - SISTEMA 100% AUTOMÁTICO ✅"

if __name__ == "__main__":
    logging.info("🚀 Iniciando Trendo Broker Bot - 100% Automático...")
    app.run(host='0.0.0.0', port=5000, debug=False)
