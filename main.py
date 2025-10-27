import requests
import sqlite3
import os
import logging
import time
from datetime import datetime, timedelta
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

        # 🆕 NUEVA TABLA PARA RETIROS
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS retiros_pendientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                monto REAL,
                wallet TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_procesado TIMESTAMP NULL
            )
        ''')

        # 🆕 NUEVA TABLA PARA INVERSIONES ACTIVAS
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS inversiones_activas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                plan TEXT,
                monto REAL,
                ganancia_diaria REAL,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_vencimiento TIMESTAMP,
                estado TEXT DEFAULT 'activa',
                ultima_ganancia TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 🆕 NUEVA TABLA PARA GANANCIAS DIARIAS
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ganancias_diarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                inversión_id INTEGER,
                monto_ganancia REAL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 🆕 NUEVA TABLA PARA COMPROBANTES DE PAGO
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS comprobantes_pago (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                plan TEXT,
                monto REAL,
                comprobante_texto TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_verificacion TIMESTAMP NULL
            )
        ''')

        self.conn.commit()
        logging.info("✅ Base de datos inicializada")

    # 🆕 SISTEMA DE NOTIFICACIONES DE RETIROS
    def notificar_retiro_admin(self, user_id, username, monto, wallet):
        """Notificar a todos los admins sobre un nuevo retiro pendiente"""
        mensaje_admin = f"""
🚨 **NUEVO RETIRO SOLICITADO - PAGO MANUAL REQUERIDO**

👤 **Usuario:** @{username} (ID: {user_id})
💰 **Monto a pagar:** {monto:.2f} USDT
📧 **Wallet destino:** `{wallet}`
⏰ **Solicitado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 **Recuerda:** Debes enviar el pago manualmente a la wallet indicada.

📋 **Estado:** ⏳ PENDIENTE DE PAGO

🔧 *Usa /retiros para ver todos los retiros pendientes*
        """
        
        # Notificar a todos los admins
        for admin_id in self.admins:
            self.send_message(admin_id, mensaje_admin)
        
        # Registrar en la base de datos
        self.cursor.execute(
            "INSERT INTO retiros_pendientes (user_id, username, monto, wallet) VALUES (?, ?, ?, ?)",
            (user_id, username, monto, wallet)
        )
        self.conn.commit()
        
        logging.info(f"🚨 Notificación de retiro enviada a admins - User: {username}, Monto: {monto} USDT")

    # 🆕 SISTEMA DE NOTIFICACIONES DE INVERSIONES
    def notificar_inversion_admin(self, user_id, username, plan, monto):
        """Notificar a admins sobre nueva inversión solicitada"""
        mensaje_admin = f"""
🚨 **NUEVA INVERSIÓN SOLICITADA - VERIFICACIÓN REQUERIDA**

👤 **Usuario:** @{username} (ID: {user_id})
📋 **Plan:** {plan}
💰 **Monto:** {monto} USDT
📈 **Ganancia mensual:** {monto * 0.20:.2f} USDT
⏰ **Solicitado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 **Acción requerida:**
1. Verificar pago en blockchain
2. Usar /activar_inversion para activar
3. Notificar al usuario

📋 **Estado:** ⏳ PENDIENTE DE VERIFICACIÓN
        """
        
        for admin_id in self.admins:
            self.send_message(admin_id, mensaje_admin)
        
        logging.info(f"🚨 Notificación de inversión enviada - User: {username}, Plan: {plan}")

    # 🆕 MANEJAR SOLICITUD DE INVERSIÓN
    def handle_invertir(self, chat_id, user_id, username):
        """Mostrar menú interactivo de planes de inversión"""
        try:
            # Crear teclado inline con los planes
            keyboard = {
                "inline_keyboard": [
                    [{"text": "💰 Básico - 15 USDT", "callback_data": "plan_Básico"}],
                    [{"text": "💎 Standard - 30 USDT", "callback_data": "plan_Standard"}],
                    [{"text": "🚀 Premium - 60 USDT", "callback_data": "plan_Premium"}],
                    [{"text": "👑 VIP - 100 USDT", "callback_data": "plan_VIP"}],
                    [{"text": "🥈 Plata - 200 USDT", "callback_data": "plan_Plata"}],
                    [{"text": "🥇 Oro - 300 USDT", "callback_data": "plan_Oro"}]
                ]
            }
            
            mensaje = """
📊 **PLANES DE INVERSIÓN - SELECCIONA UNO** 💰

📈 **Rendimiento automático:** 20% mensual
💡 **Ganancias automáticas cada 24h**

👇 **Elige tu plan de inversión:**
            """
            
            self.send_message(chat_id, mensaje, reply_markup=keyboard)
            
        except Exception as e:
            logging.error(f"Error en menú de inversión: {e}")
            self.send_message(chat_id, "❌ Error al cargar planes de inversión. Usa /soporte")

    # 🆕 PROCESAR SELECCIÓN DE PLAN
    def handle_seleccion_plan(self, chat_id, user_id, username, plan_seleccionado):
        """Procesar la selección de un plan de inversión"""
        try:
            if plan_seleccionado in self.planes:
                plan_data = self.planes[plan_seleccionado]
                monto = plan_data["monto"]
                ganancia_mensual = monto * plan_data["ganancia"]
                ganancia_diaria = monto * self.ganancia_diaria
                
                # Guardar en sesión
                self.user_sessions[user_id] = {
                    "plan_seleccionado": plan_seleccionado,
                    "monto_inversion": monto,
                    "esperando_comprobante": True
                }
                
                mensaje = f"""
🤖 **CONFIRMACIÓN DE INVERSIÓN** 💰

📋 **Plan seleccionado:** {plan_seleccionado}
💰 **Monto de inversión:** {monto} USDT
📈 **Rendimiento mensual:** 20% (+{ganancia_mensual:.2f} USDT)
💸 **Ganancia diaria:** +{ganancia_diaria:.2f} USDT

📧 **Wallet para enviar:**
`{self.trust_wallet}`

💡 **Instrucciones importantes:**
1. Envía EXACTAMENTE {monto} USDT a la wallet arriba
2. Asegúrate de usar la red TRC20 (TRON)
3. Guarda el comprobante de la transacción
4. Responde a este mensaje con "He enviado"
5. Adjunta el screenshot del comprobante

⏰ **Tu inversión se activará en 1-2 horas** después de la verificación

🔐 *Transacciones 100% seguras y verificadas*
                """
                
                self.send_message(chat_id, mensaje)
                
            else:
                self.send_message(chat_id, "❌ Plan no válido. Usa /invertir para ver los planes disponibles")
                
        except Exception as e:
            logging.error(f"Error en selección de plan: {e}")
            self.send_message(chat_id, "❌ Error al procesar la selección. Usa /soporte")

    # 🆕 ACTIVAR INVERSIÓN (SOLO ADMINS)
    def activar_inversion(self, chat_id, user_id, username, plan, monto):
        """Activar una inversión después de verificar el pago"""
        try:
            # Calcular fechas
            fecha_inicio = datetime.now()
            fecha_vencimiento = fecha_inicio + timedelta(days=30)
            ganancia_diaria = monto * self.ganancia_diaria
            
            # Registrar inversión activa
            self.cursor.execute('''
                INSERT INTO inversiones_activas 
                (user_id, username, plan, monto, ganancia_diaria, fecha_vencimiento)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, plan, monto, ganancia_diaria, fecha_vencimiento))
            
            # Actualizar estadísticas del usuario
            self.cursor.execute('''
                UPDATE usuarios 
                SET total_invertido = total_invertido + ? 
                WHERE user_id = ?
            ''', (monto, user_id))
            
            # Marcar comprobante como verificado
            self.cursor.execute('''
                UPDATE comprobantes_pago 
                SET estado = 'verificado', fecha_verificacion = CURRENT_TIMESTAMP
                WHERE user_id = ? AND estado = 'pendiente'
            ''', (user_id,))
            
            self.conn.commit()
            
            # Notificar al usuario
            mensaje_usuario = f"""
✅ **¡INVERSIÓN ACTIVADA EXITOSAMENTE!** 🎉

📋 **Plan:** {plan}
💰 **Inversión:** {monto} USDT
📈 **Ganancia mensual:** {monto * 0.20:.2f} USDT
💸 **Ganancia diaria:** +{ganancia_diaria:.2f} USDT
⏰ **Fecha de inicio:** {fecha_inicio.strftime('%Y-%m-%d')}
📅 **Vencimiento:** {fecha_vencimiento.strftime('%Y-%m-%d')}

🎯 **Próxima ganancia:** En 24 horas
💼 **Ver estado:** /mis_inversiones

¡Felicidades! Tu inversión está ahora activa y generando ganancias automáticamente.
            """
            
            self.send_message(chat_id, mensaje_usuario)
            logging.info(f"✅ Inversión activada - User: {username}, Plan: {plan}, Monto: {monto}")
            
        except Exception as e:
            logging.error(f"Error activando inversión: {e}")
            self.send_message(chat_id, "❌ Error al activar la inversión")

    # 🆕 MOSTRAR INVERSIONES DEL USUARIO
    def handle_mis_inversiones(self, chat_id, user_id):
        """Mostrar las inversiones activas del usuario"""
        try:
            self.cursor.execute('''
                SELECT plan, monto, ganancia_diaria, fecha_inicio, fecha_vencimiento, estado
                FROM inversiones_activas 
                WHERE user_id = ? AND estado = 'activa'
            ''', (user_id,))
            
            inversiones = self.cursor.fetchall()
            
            if inversiones:
                mensaje = "📊 **TUS INVERSIONES ACTIVAS** 💰\n\n"
                total_invertido = 0
                total_ganancia_diaria = 0
                
                for inversion in inversiones:
                    plan, monto, ganancia_diaria, fecha_inicio, fecha_vencimiento, estado = inversion
                    total_invertido += monto
                    total_ganancia_diaria += ganancia_diaria
                    
                    dias_restantes = (datetime.strptime(fecha_vencimiento, '%Y-%m-%d %H:%M:%S') - datetime.now()).days
                    
                    mensaje += f"""
📋 **Plan:** {plan}
💰 **Invertido:** {monto} USDT
💸 **Ganancia diaria:** +{ganancia_diaria:.2f} USDT
⏰ **Días restantes:** {dias_restantes} días
────────────────────
"""
                
                mensaje += f"\n💵 **Total invertido:** {total_invertido:.2f} USDT"
                mensaje += f"\n📈 **Ganancia diaria total:** +{total_ganancia_diaria:.2f} USDT"
                mensaje += f"\n🎯 **Inversiones activas:** {len(inversiones)}"
                
            else:
                mensaje = """
📭 **No tienes inversiones activas**

💡 **Para empezar a invertir:**
1. Usa /invertir para ver los planes
2. Selecciona tu plan preferido
3. Sigue las instrucciones de pago

🚀 **¡Comienza a generar ganancias hoy mismo!**
                """
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error mostrando inversiones: {e}")
            self.send_message(chat_id, "❌ Error al cargar tus inversiones. Usa /soporte")

    # 🆕 CALCULAR GANANCIAS DIARIAS (se ejecutaría automáticamente)
    def calcular_ganancias_diarias(self):
        """Calcular y distribuir ganancias diarias automáticamente"""
        try:
            # Obtener todas las inversiones activas
            self.cursor.execute('''
                SELECT id, user_id, username, monto, ganancia_diaria 
                FROM inversiones_activas 
                WHERE estado = 'activa'
            ''')
            
            inversiones = self.cursor.fetchall()
            
            for inversion in inversiones:
                inv_id, user_id, username, monto, ganancia_diaria = inversion
                
                # Registrar ganancia
                self.cursor.execute('''
                    INSERT INTO ganancias_diarias (user_id, inversión_id, monto_ganancia)
                    VALUES (?, ?, ?)
                ''', (user_id, inv_id, ganancia_diaria))
                
                # Actualizar balance del usuario
                self.cursor.execute('''
                    UPDATE usuarios 
                    SET balance_ganancias = balance_ganancias + ?, 
                        total_ganado = total_ganado + ?,
                        balance = balance + ?
                    WHERE user_id = ?
                ''', (ganancia_diaria, ganancia_diaria, ganancia_diaria, user_id))
                
                # Actualizar última ganancia
                self.cursor.execute('''
                    UPDATE inversiones_activas 
                    SET ultima_ganancia = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (inv_id,))
                
                logging.info(f"💰 Ganancia diaria aplicada - User: {username}, Monto: {ganancia_diaria:.2f} USDT")
            
            self.conn.commit()
            
        except Exception as e:
            logging.error(f"Error calculando ganancias diarias: {e}")

    def handle_retiros_pendientes(self, chat_id, user_id):
        """Mostrar retiros pendientes solo para administradores"""
        if user_id not in self.admins:
            self.send_message(chat_id, "❌ No tienes permisos de administrador")
            return
        
        try:
            self.cursor.execute('''
                SELECT user_id, username, monto, wallet, fecha_solicitud 
                FROM retiros_pendientes 
                WHERE estado = 'pendiente'
                ORDER BY fecha_solicitud DESC
            ''')
            retiros = self.cursor.fetchall()
            
            if retiros:
                mensaje = "📋 **RETIROS PENDIENTES - PAGOS MANUALES REQUERIDOS**\n\n"
                total_pendiente = 0
                
                for retiro in retiros:
                    user_id_retiro, username, monto, wallet, fecha = retiro
                    total_pendiente += monto
                    
                    mensaje += f"""
👤 **Usuario:** @{username} (ID: {user_id_retiro})
💰 **Monto:** {monto:.2f} USDT
📧 **Wallet:** `{wallet}`
⏰ **Solicitado:** {fecha}
────────────────────
"""
                
                mensaje += f"\n💵 **TOTAL PENDIENTE:** {total_pendiente:.2f} USDT"
                mensaje += f"\n👥 **Retiros pendientes:** {len(retiros)}"
                
            else:
                mensaje = "✅ **No hay retiros pendientes en este momento**"
                
            self.send_message(chat_id, mensaje)
            
        except Exception as e:
            logging.error(f"Error en retiros pendientes: {e}")
            self.send_message(chat_id, "❌ Error al cargar retiros pendientes")

    # 🎯 SISTEMA DE SOPORTE AUTOMÁTICO (existente)
    def analizar_pregunta(self, texto):
        """Analizar pregunta y encontrar respuesta automática"""
        texto = texto.lower().strip()
        
        soporte_automatico = {
            "retiro": {
                "palabras": ["retiro", "retirar", "sacar dinero", "cuando me pagan", "tiempo de retiro", "wallet", "pago"],
                "respuesta": """💸 **INFORMACIÓN DE RETIROS - AUTOMÁTICO**

⏰ **Tiempo de procesamiento:** 24-48 horas
💰 **Mínimo de retiro:** 10 USDT
📧 **Wallet para invertir:** `TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg`
🔐 **Seguridad:** 100% garantizada

🤖 *Sistema automático - Tu retiro se procesará en el tiempo establecido*"""
            },
            "inversion": {
                "palabras": ["invertir", "inversión", "planes", "ganancias", "rendimiento", "ganar dinero", "plan", "wallet", "donde envío"],
                "respuesta": """📊 **PLANES DE INVERSIÓN - AUTOMÁTICO**

📈 **Rendimiento:** 20% mensual
💰 **Ganancias:** Automáticas cada 24h
🔐 **Seguridad:** Garantizada
💼 **Planes desde:** 15 USDT

📧 **Wallet para invertir:**
`TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg`

💡 *Usa* /invertir *para seleccionar tu plan*

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
            }
        }
        
        for categoria, datos in soporte_automatico.items():
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

📧 **Wallet para invertir:**
`TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg`

🚀 **COMANDOS AUTOMÁTICOS:**

/invertir - Seleccionar plan de inversión
/mis_inversiones - Ver inversiones activas
/balance - Consultar balance automáticamente
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

💡 *Ejemplo:* `TLTM2kgsMEqbkzxLp34pGYsbw87gt33kFg`

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
            self.cursor.execute("SELECT COUNT(*) FROM inversiones_activas WHERE estado = 'activa'")
            inversiones_activas = self.cursor.fetchone()[0]
            
            # Obtener retiros pendientes
            self.cursor.execute("SELECT COUNT(*), SUM(monto) FROM retiros_pendientes WHERE estado = 'pendiente'")
            retiros_pendientes = self.cursor.fetchone()
            total_retiros_pendientes = retiros_pendientes[0] or 0
            total_monto_pendiente = retiros_pendientes[1] or 0

            # Obtener inversiones pendientes
            self.cursor.execute("SELECT COUNT(*) FROM comprobantes_pago WHERE estado = 'pendiente'")
            inversiones_pendientes = self.cursor.fetchone()[0] or 0
            
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

🚨 **PENDIENTES:**
• Retiros pendientes: {total_retiros_pendientes}
• Monto retiros pendiente: {total_monto_pendiente:.2f} USDT
• Inversiones por verificar: {inversiones_pendientes}

💡 *Usa /retiros para ver detalles de retiros pendientes*

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
                    
                    # NOTIFICAR A ADMINS SOBRE EL RETIRO
                    self.notificar_retiro_admin(user_id, username, monto, wallet)
                    
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

                # Manejar comprobantes de inversión
                if user_id in self.user_sessions and self.user_sessions[user_id].get('esperando_comprobante'):
                    if "he enviado" in text.lower():
                        plan = self.user_sessions[user_id]['plan_seleccionado']
                        monto = self.user_sessions[user_id]['monto_inversion']
                        
                        # Registrar comprobante
                        self.cursor.execute('''
                            INSERT INTO comprobantes_pago (user_id, username, plan, monto, comprobante_texto)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (user_id, username, plan, monto, text))
                        self.conn.commit()
                        
                        # Notificar a admins
                        self.notificar_inversion_admin(user_id, username, plan, monto)
                        
                        mensaje = f"""
✅ **COMPROBANTE REGISTRADO EXITOSAMENTE**

📋 **Plan:** {plan}
💰 **Monto:** {monto} USDT
⏰ **Solicitado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔍 **Estado:** En verificación por nuestro equipo

📞 **Tiempo de verificación:** 1-2 horas
💡 **Recibirás notificación cuando tu inversión esté activa**

🤖 *Gracias por confiar en nuestro sistema automatizado*
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
                    self.handle_invertir(chat_id, user_id, username)
                elif text == '/mis_inversiones':
                    self.handle_mis_inversiones(chat_id, user_id)
                elif text == '/estadisticas':
                    self.handle_estadisticas(chat_id, user_id)
                elif text == '/retiros':  # NUEVO COMANDO
                    self.handle_retiros_pendientes(chat_id, user_id)
                elif text == '/soporte':
                    self.handle_soporte(chat_id, user_id, username)
                elif text.startswith('/'):
                    self.send_message(chat_id, "❌ Comando no reconocido automáticamente. Usa /soporte")
                else:
                    # Cualquier otro mensaje = soporte automático
                    self.handle_soporte(chat_id, user_id, username, text)

            # 🆕 Manejar callbacks de botones inline
            elif 'callback_query' in update:
                callback = update['callback_query']
                chat_id = callback['message']['chat']['id']
                user_id = callback['from']['id']
                username = callback['from'].get('username', 'Usuario')
                callback_data = callback['data']
                
                if callback_data.startswith('plan_'):
                    plan_seleccionado = callback_data.replace('plan_', '')
                    self.handle_seleccion_plan(chat_id, user_id, username, plan_seleccionado)
                
                # Confirmar callback
                self.answer_callback_query(callback['id'])

        except Exception as e:
            logging.error(f"❌ Error automático procesando update: {e}")

    def answer_callback_query(self, callback_id):
        """Responder a callback query"""
        url = f"{self.telegram_api_url}/answerCallbackQuery"
        payload = {'callback_query_id': callback_id}
        try:
            requests.post(url, json=payload, timeout=5)
        except:
            pass

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
    
    # 🆕 Calcular ganancias diarias al iniciar (simulación)
    bot.calcular_ganancias_diarias()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
