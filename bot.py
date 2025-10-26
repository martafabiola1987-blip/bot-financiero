import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional
import json

class BotFinanciero:
    def __init__(self):
        self.transacciones = []
        self.categorias = {
            'ingresos': ['salario', 'freelance', 'inversiones', 'otros_ingresos'],
            'gastos': ['alimentacion', 'transporte', 'vivienda', 'entretenimiento', 'salud', 'educacion', 'otros_gastos']
        }
        self.presupuestos = {}
    
    def agregar_transaccion(self, monto: float, tipo: str, categoria: str, descripcion: str = ""):
        """Agrega una nueva transacción"""
        if tipo not in ['ingreso', 'gasto']:
            raise ValueError("El tipo debe ser 'ingreso' o 'gasto'")
        
        transaccion = {
            'fecha': datetime.now(),
            'monto': abs(monto) if tipo == 'ingreso' else -abs(monto),
            'tipo': tipo,
            'categoria': categoria,
            'descripcion': descripcion
        }
        
        self.transacciones.append(transaccion)
        print(f"Transacción agregada: {tipo} de ${abs(monto)} en {categoria}")
    
    def obtener_balance_actual(self) -> float:
        """Calcula el balance actual"""
        return sum(trans['monto'] for trans in self.transacciones)
    
    def obtener_resumen_por_categoria(self, tipo: str = None) -> Dict:
        """Obtiene un resumen de transacciones por categoría"""
        resumen = {}
        
        for trans in self.transacciones:
            if tipo and trans['tipo'] != tipo:
                continue
                
            categoria = trans['categoria']
            if categoria not in resumen:
                resumen[categoria] = 0
            resumen[categoria] += trans['monto']
        
        return resumen
    
    def establecer_presupuesto(self, categoria: str, monto: float):
        """Establece un presupuesto para una categoría"""
        self.presupuestos[categoria] = monto
        print(f"Presupuesto de ${monto} establecido para {categoria}")
    
    def analizar_presupuestos(self):
        """Analiza el cumplimiento de los presupuestos"""
        gastos_por_categoria = self.obtener_resumen_por_categoria('gasto')
        
        print("\n--- ANÁLISIS DE PRESUPUESTOS ---")
        for categoria, presupuesto in self.presupuestos.items():
            gasto_actual = abs(gastos_por_categoria.get(categoria, 0))
            porcentaje = (gasto_actual / presupuesto) * 100 if presupuesto > 0 else 0
            
            print(f"{categoria}: ${gasto_actual} / ${presupuesto} ({porcentaje:.1f}%)")
            
            if porcentaje > 100:
                print(f"  ⚠️  EXCEDIDO por {porcentaje - 100:.1f}%")
            elif porcentaje > 80:
                print(f"  ⚠️  Cerca del límite")
            else:
                print(f"  ✅ Dentro del presupuesto")
    
    def generar_reporte_mensual(self, mes: int = None, año: int = None):
        """Genera un reporte mensual"""
        if mes is None:
            mes = datetime.now().month
        if año is None:
            año = datetime.now().year
        
        transacciones_mes = [
            trans for trans in self.transacciones
            if trans['fecha'].month == mes and trans['fecha'].year == año
        ]
        
        if not transacciones_mes:
            print(f"No hay transacciones para {mes}/{año}")
            return
        
        ingresos = sum(trans['monto'] for trans in transacciones_mes if trans['monto'] > 0)
        gastos = sum(trans['monto'] for trans in transacciones_mes if trans['monto'] < 0)
        balance = ingresos + gastos
        
        print(f"\n--- REPORTE MENSUAL {mes}/{año} ---")
        print(f"Ingresos: ${ingresos:.2f}")
        print(f"Gastos: ${abs(gastos):.2f}")
        print(f"Balance: ${balance:.2f}")
        print(f"Ratio Ahorro: {(balance/ingresos*100 if ingresos > 0 else 0):.1f}%")
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas generales"""
        if not self.transacciones:
            print("No hay transacciones registradas")
            return
        
        balance = self.obtener_balance_actual()
        total_ingresos = sum(trans['monto'] for trans in self.transacciones if trans['monto'] > 0)
        total_gastos = sum(trans['monto'] for trans in self.transacciones if trans['monto'] < 0)
        
        print("\n--- ESTADÍSTICAS GENERALES ---")
        print(f"Balance actual: ${balance:.2f}")
        print(f"Total ingresos: ${total_ingresos:.2f}")
        print(f"Total gastos: ${abs(total_gastos):.2f}")
        print(f"Número de transacciones: {len(self.transacciones)}")
        
        # Resumen por categoría
        resumen_gastos = self.obtener_resumen_por_categoria('gasto')
        if resumen_gastos:
            print("\n--- GASTOS POR CATEGORÍA ---")
            for categoria, monto in resumen_gastos.items():
                print(f"  {categoria}: ${abs(monto):.2f}")

def main():
    bot = BotFinanciero()
    
    while True:
        print("\n🤖 BOT FINANCIERO")
        print("1. Agregar transacción")
        print("2. Ver balance actual")
        print("3. Establecer presupuesto")
        print("4. Analizar presupuestos")
        print("5. Generar reporte mensual")
        print("6. Ver estadísticas")
        print("7. Salir")
        
        opcion = input("\nSelecciona una opción: ")
        
        if opcion == '1':
            try:
                monto = float(input("Monto: "))
                tipo = input("Tipo (ingreso/gasto): ").lower()
                categoria = input("Categoría: ")
                descripcion = input("Descripción (opcional): ")
                bot.agregar_transaccion(monto, tipo, categoria, descripcion)
            except ValueError as e:
                print(f"Error: {e}")
        
        elif opcion == '2':
            balance = bot.obtener_balance_actual()
            print(f"Balance actual: ${balance:.2f}")
        
        elif opcion == '3':
            categoria = input("Categoría: ")
            try:
                monto = float(input("Presupuesto mensual: "))
                bot.establecer_presupuesto(categoria, monto)
            except ValueError:
                print("Monto inválido")
        
        elif opcion == '4':
            bot.analizar_presupuestos()
        
        elif opcion == '5':
            try:
                mes = input("Mes (1-12, Enter para actual): ")
                año = input("Año (Enter para actual): ")
                mes = int(mes) if mes else None
                año = int(año) if año else None
                bot.generar_reporte_mensual(mes, año)
            except ValueError:
                print("Mes o año inválido")
        
        elif opcion == '6':
            bot.mostrar_estadisticas()
        
        elif opcion == '7':
            print("¡Hasta luego! 💰")
            break
        
        else:
            print("Opción inválida")

if __name__ == "__main__":
    main()
