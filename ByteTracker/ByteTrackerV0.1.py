import sqlite3
import tkinter as tk
from tkinter import messagebox

# 1. Configuración de la Base de Datos
def conectar_db():
    conexion = sqlite3.connect("usuarios.db")
    cursor = conexion.cursor()
    # Crea la tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL
        )
    """)
    conexion.commit()
    conexion.close()

# 2. Función para guardar los datos del formulario
def guardar_datos():
    nombre = entry_nombre.get()
    correo = entry_correo.get()
    
    # Validar que los campos no estén vacíos
    if nombre == "" or correo == "":
        messagebox.showwarning("Advertencia", "Todos los campos son obligatorios")
        return

    # Conectar e insertar en la base de datos
    conexion = sqlite3.connect("usuarios.db")
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO usuarios (nombre, correo) VALUES (?, ?)", (nombre, correo))
    conexion.commit()
    conexion.close()
    
    # Limpiar los campos y avisar al usuario
    entry_nombre.delete(0, tk.END)
    entry_correo.delete(0, tk.END)
    messagebox.showinfo("Éxito", "Datos guardados correctamente")

# 3. Interfaz Gráfica con Tkinter
ventana = tk.Tk()
ventana.title("Formulario a SQLite")
ventana.geometry("300x200")

# Inicializar la base de datos al arrancar
conectar_db()

# Etiquetas y campos de entrada
tk.Label(ventana, text="Nombre:").pack(pady=5)
entry_nombre = tk.Entry(ventana)
entry_nombre.pack(pady=5)

tk.Label(ventana, text="Correo:").pack(pady=5)
entry_correo = tk.Entry(ventana)
entry_correo.pack(pady=5)

# Botón para enviar
btn_guardar = tk.Button(ventana, text="Guardar", command=guardar_datos)
btn_guardar.pack(pady=15)

ventana.mainloop()