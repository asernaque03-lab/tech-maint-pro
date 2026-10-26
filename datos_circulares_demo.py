import sqlite3
from datetime import datetime, timedelta

# Ruta de la base de datos (debe estar en la misma carpeta)
DB_PATH = "techmaintpro.db"

# Datos de demostración para Impacto Circular
# Cada tupla representa una intervención de mantenimiento
datos_demo = [
    # (ot_id, asset_name, component, decision, result, mass_conserved_kg, mass_discarded_kg, 
    #  costo_reparacion_eur, costo_reemplazo_nuevo_eur, co2_evitado_kg, 
    #  vida_util_extendida_horas, disponibilidad_post_reparacion_pct, recorded_date)
    
    ("OT-20261020-P1", "Bomba de vacio BV-01", "Rodamiento SKF 6205", "Reparacion", "Reparado", 
     8.5, 0.3, 250, 1500, 12.5, 2000, 95.0, "2026-10-20 10:30:00"),
    
    ("OT-20261018-P2", "Motor CAT 3408 MD-01", "Filtro de aceite", "Reemplazo Parcial", "Reutilizado", 
     2.1, 0.8, 80, 450, 3.2, 500, 98.0, "2026-10-18 14:15:00"),
    
    ("OT-20261015-P1", "Compresor Leroi CA-01", "Correa de transmision", "Reparacion", "Reparado", 
     5.2, 0.1, 180, 800, 8.7, 1500, 92.0, "2026-10-15 09:00:00"),
    
    ("OT-20261012-P0", "Bomba de vacio BV-01", "Sello mecanico", "Reemplazo Total", "Reemplazado", 
     0.0, 3.5, 0, 2200, 0.0, 0, 100.0, "2026-10-12 16:45:00"),
    
    ("OT-20261010-P1", "Motor CAT 3408 MD-01", "Inyector de combustible", "Reparacion", "Reparado", 
     12.8, 0.5, 450, 3200, 18.3, 3000, 96.0, "2026-10-10 11:20:00"),
    
    ("OT-20261008-P2", "Compresor Leroi CA-01", "Filtro de aire", "Reemplazo Parcial", "Reutilizado", 
     1.5, 0.4, 60, 320, 2.1, 400, 97.0, "2026-10-08 08:30:00"),
    
    ("OT-20261005-P1", "Bomba de vacio BV-01", "Eje principal", "Reparacion", "Reparado", 
     15.3, 0.2, 680, 4500, 22.5, 4000, 94.0, "2026-10-05 13:00:00"),
    
    ("OT-20261002-P0", "Motor CAT 3408 MD-01", "Turbo compresor", "Reemplazo Total", "Reemplazado", 
     0.0, 18.5, 0, 8500, 0.0, 0, 100.0, "2026-10-02 15:30:00"),
]

def poblar_datos_circulares():
    """Inserta datos de demostración en la tabla circular_interventions"""
    
    print("Conectando a la base de datos...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar que la tabla existe
    try:
        c.execute("SELECT COUNT(*) FROM circular_interventions")
        count = c.fetchone()[0]
        print(f"La tabla tiene {count} registros actuales")
        
        # Opcional: Limpiar datos existentes (descomenta si quieres empezar limpio)
        # c.execute("DELETE FROM circular_interventions")
        # print("Datos anteriores eliminados")
        
    except sqlite3.OperationalError:
        print("ERROR: La tabla circular_interventions no existe")
        print("Ejecuta primero la aplicación para crear la base de datos")
        conn.close()
        return False
    
    # Insertar cada registro
    print("\nInsertando datos de demostración...")
    for i, row in enumerate(datos_demo, 1):
        try:
            c.execute("""INSERT INTO circular_interventions 
                (ot_id, asset_name, component, decision, result, 
                 mass_conserved_kg, mass_discarded_kg, 
                 costo_reparacion_eur, costo_reemplazo_nuevo_eur, 
                 co2_evitado_kg, vida_util_extendida_horas, 
                 disponibilidad_post_reparacion_pct, recorded_date, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*row, "Dario Minan"))
            print(f"  [{i}/{len(datos_demo)}] Insertado: {row[0]} - {row[2]}")
        except Exception as e:
            print(f"  [{i}/{len(datos_demo)}] ERROR: {e}")
    
    # Confirmar cambios
    conn.commit()
    
    # Verificar inserción
    c.execute("SELECT COUNT(*) FROM circular_interventions")
    total = c.fetchone()[0]
    print(f"\nTotal de registros en la tabla: {total}")
    
    # Mostrar resumen
    c.execute("""SELECT 
        SUM(mass_conserved_kg) as total_conservado,
        SUM(mass_discarded_kg) as total_descartado,
        SUM(co2_evitado_kg) as total_co2,
        SUM(costo_reemplazo_nuevo_eur - costo_reparacion_eur) as ahorro_total
        FROM circular_interventions""")
    
    resumen = c.fetchone()
    print(f"\nResumen de Impacto Circular:")
    print(f"  Masa conservada: {resumen[0]:.1f} kg")
    print(f"  Masa descartada: {resumen[1]:.1f} kg")
    print(f"  CO2 evitado: {resumen[2]:.1f} kg")
    print(f"  Ahorro total: EUR {resumen[3]:,.0f}")
    
    conn.close()
    print("\nProceso completado exitosamente!")
    return True

if __name__ == "__main__":
    poblar_datos_circulares()