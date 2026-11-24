import sqlite3
import datetime
import customtkinter as ctk

# --- Base de datos ---
conexion = sqlite3.connect("Ejemplo.db")
cursor = conexion.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS archivos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    ruta TEXT NOT NULL,
    fecha TEXT NOT NULL,
    usuario TEXT NOT NULL
)
""")
conexion.commit()

# --- Funciones faltantes implementadas ---
def adjuntar_archivo(nombre: str, ruta: str, usuario: str) -> bool:
    """
    Inserta un registro en la tabla 'archivos'.
    Devuelve True si la inserción fue exitosa, False en caso contrario.
    """
    if not nombre or not ruta or not usuario:
        return False
    try:
        fecha = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
        cursor.execute(
            "INSERT INTO archivos (nombre, ruta, fecha, usuario) VALUES (?, ?, ?, ?)",
            (nombre, ruta, fecha, usuario)
        )
        conexion.commit()
        return True
    except Exception:
        return False

def buscar_archivo(nombre_parcial: str):
    """
    Busca archivos cuyo nombre contenga 'nombre_parcial' (insensible a mayúsculas).
    Devuelve una lista de tuplas (id, nombre, ruta, fecha, usuario).
    Si nombre_parcial está vacío, devuelve todos los registros.
    """
    try:
        if nombre_parcial:
            like_pattern = f"%{nombre_parcial}%"
            cursor.execute(
                "SELECT id, nombre, ruta, fecha, usuario FROM archivos WHERE nombre LIKE ? COLLATE NOCASE",
                (like_pattern,)
            )
        else:
            cursor.execute("SELECT id, nombre, ruta, fecha, usuario FROM archivos")
        return cursor.fetchall()
    except Exception:
        return []

# --- Interfaz gráfica ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ventana = ctk.CTk()
ventana.title("Data Center Manager")
ventana.geometry("600x400")

# --- Entradas ---
entrada_nombre = ctk.CTkEntry(ventana, placeholder_text="Nombre del archivo")
entrada_nombre.pack(pady=10)

entrada_ruta = ctk.CTkEntry(ventana, placeholder_text="Ruta del archivo")
entrada_ruta.pack(pady=10)

entrada_usuario = ctk.CTkEntry(ventana, placeholder_text="Usuario")
entrada_usuario.pack(pady=10)

# Contenedor para mensajes/resultados (evita apilar etiquetas indefinidamente)
frame_resultados = ctk.CTkScrollableFrame(ventana, width=560, height=180)
frame_resultados.pack(pady=10)

def limpiar_resultados():
    for widget in frame_resultados.winfo_children():
        widget.destroy()

# --- Botones ---
def accion_adjuntar():
    limpiar_resultados()
    nombre = entrada_nombre.get().strip()
    ruta = entrada_ruta.get().strip()
    usuario = entrada_usuario.get().strip()
    if adjuntar_archivo(nombre, ruta, usuario):
        ctk.CTkLabel(frame_resultados, text="✓ Archivo adjuntado", text_color="green").pack(anchor="w", pady=2)
        # Opcional: limpiar entradas tras adjuntar
        entrada_nombre.delete(0, "end")
        entrada_ruta.delete(0, "end")
        entrada_usuario.delete(0, "end")
    else:
        ctk.CTkLabel(frame_resultados, text="❌ Error al adjuntar (campos vacíos o fallo)", text_color="red").pack(anchor="w", pady=2)

btn_adjuntar = ctk.CTkButton(ventana, text="Adjuntar", command=accion_adjuntar)
btn_adjuntar.pack(pady=6)

def accion_buscar():
    limpiar_resultados()
    nombre_buscar = entrada_nombre.get().strip()
    resultados = buscar_archivo(nombre_buscar)
    if not resultados:
        ctk.CTkLabel(frame_resultados, text="No se encontraron resultados.").pack(anchor="w", pady=2)
        return
    for r in resultados:
        # r = (id, nombre, ruta, fecha, usuario)
        texto = f"ID {r[0]} - {r[1]} - {r[2]} - {r[3]} - {r[4]}"
        ctk.CTkLabel(frame_resultados, text=texto).pack(anchor="w", pady=2)

btn_buscar = ctk.CTkButton(ventana, text="Buscar", command=accion_buscar)
btn_buscar.pack(pady=6)

ventana.mainloop()

# Cerrar conexión al terminar (no se alcanzará hasta cerrar la ventana)
conexion.close()