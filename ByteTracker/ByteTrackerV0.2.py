import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk


# =========================================================
# CONFIGURACIÓN Y BASE DE DATOS
# =========================================================

DB_NAME = "Ejemplo.db"

conexion = sqlite3.connect(DB_NAME)
conexion.execute("PRAGMA foreign_keys = ON")
cursor = conexion.cursor()


def inicializar_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS redes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT DEFAULT '',
            parent_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES redes(id) ON DELETE CASCADE
        )
    """)

    # Migración para bases de datos creadas con una versión anterior.
    columnas = [
        fila[1] for fila in cursor.execute("PRAGMA table_info(redes)").fetchall()
    ]
    if "parent_id" not in columnas:
        cursor.execute("""
            ALTER TABLE redes
            ADD COLUMN parent_id INTEGER REFERENCES redes(id) ON DELETE CASCADE
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispositivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            red_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            tipo TEXT DEFAULT '',
            ip TEXT DEFAULT '',
            mac TEXT DEFAULT '',
            estado TEXT DEFAULT 'Desconocido',
            fabricante TEXT DEFAULT '',
            modelo TEXT DEFAULT '',
            ubicacion TEXT DEFAULT '',
            sistema TEXT DEFAULT '',
            descripcion TEXT DEFAULT '',
            FOREIGN KEY (red_id) REFERENCES redes(id) ON DELETE CASCADE
        )
    """)

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


def cargar_datos_demo():
    cantidad = cursor.execute("SELECT COUNT(*) FROM redes").fetchone()[0]

    if cantidad == 0:
        cursor.execute(
            "INSERT INTO redes (nombre, descripcion) VALUES (?, ?)",
            ("Red principal", "Red de infraestructura principal")
        )
        red_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO redes (nombre, descripcion, parent_id) VALUES (?, ?, ?)",
            ("Sala de servidores", "Infraestructura del centro de datos", red_id)
        )
        subred_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO dispositivos
            (red_id, nombre, tipo, ip, estado, fabricante, modelo, ubicacion, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            subred_id, "Servidor principal", "Servidor", "192.168.1.10",
            "Conectado", "Dell", "PowerEdge", "Rack 01",
            "Servidor principal de la infraestructura"
        ))

        cursor.execute("""
            INSERT INTO dispositivos
            (red_id, nombre, tipo, ip, estado, fabricante, modelo, ubicacion, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            red_id, "Router principal", "Router", "192.168.1.1",
            "Conectado", "Cisco", "ISR", "Rack 01",
            "Router de la red principal"
        ))

    conexion.commit()


# =========================================================
# OPERACIONES DE REDES Y SUBREDES
# =========================================================

def obtener_redes():
    return cursor.execute("""
        SELECT id, nombre, descripcion, parent_id
        FROM redes
        ORDER BY nombre COLLATE NOCASE
    """).fetchall()


def obtener_red(red_id):
    return cursor.execute("""
        SELECT id, nombre, descripcion, parent_id
        FROM redes
        WHERE id = ?
    """, (red_id,)).fetchone()


def crear_red(nombre, descripcion="", parent_id=None):
    cursor.execute("""
        INSERT INTO redes (nombre, descripcion, parent_id)
        VALUES (?, ?, ?)
    """, (nombre, descripcion, parent_id))
    conexion.commit()
    return cursor.lastrowid


def renombrar_red(red_id, nuevo_nombre):
    cursor.execute(
        "UPDATE redes SET nombre = ? WHERE id = ?",
        (nuevo_nombre, red_id)
    )
    conexion.commit()


def eliminar_red(red_id):
    # Las claves foráneas eliminan automáticamente sus subredes
    # y los dispositivos asociados.
    cursor.execute("DELETE FROM redes WHERE id = ?", (red_id,))
    conexion.commit()


# =========================================================
# OPERACIONES DE DISPOSITIVOS
# =========================================================

CAMPOS_DISPOSITIVO = [
    ("nombre", "Nombre"),
    ("tipo", "Tipo"),
    ("ip", "Dirección IP"),
    ("mac", "Dirección MAC"),
    ("estado", "Estado"),
    ("fabricante", "Fabricante"),
    ("modelo", "Modelo"),
    ("ubicacion", "Ubicación"),
    ("sistema", "Sistema operativo"),
    ("descripcion", "Descripción"),
]


def obtener_dispositivos(red_id):
    return cursor.execute("""
        SELECT id, nombre, tipo, estado
        FROM dispositivos
        WHERE red_id = ?
        ORDER BY nombre COLLATE NOCASE
    """, (red_id,)).fetchall()


def obtener_dispositivo(dispositivo_id):
    return cursor.execute("""
        SELECT id, red_id, nombre, tipo, ip, mac, estado,
               fabricante, modelo, ubicacion, sistema, descripcion
        FROM dispositivos
        WHERE id = ?
    """, (dispositivo_id,)).fetchone()


def crear_dispositivo(red_id, datos):
    cursor.execute("""
        INSERT INTO dispositivos (
            red_id, nombre, tipo, ip, mac, estado,
            fabricante, modelo, ubicacion, sistema, descripcion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        red_id,
        datos["nombre"],
        datos["tipo"],
        datos["ip"],
        datos["mac"],
        datos["estado"],
        datos["fabricante"],
        datos["modelo"],
        datos["ubicacion"],
        datos["sistema"],
        datos["descripcion"],
    ))
    conexion.commit()
    return cursor.lastrowid


def actualizar_dispositivo(dispositivo_id, datos):
    cursor.execute("""
        UPDATE dispositivos
        SET nombre = ?, tipo = ?, ip = ?, mac = ?, estado = ?,
            fabricante = ?, modelo = ?, ubicacion = ?,
            sistema = ?, descripcion = ?
        WHERE id = ?
    """, (
        datos["nombre"],
        datos["tipo"],
        datos["ip"],
        datos["mac"],
        datos["estado"],
        datos["fabricante"],
        datos["modelo"],
        datos["ubicacion"],
        datos["sistema"],
        datos["descripcion"],
        dispositivo_id
    ))
    conexion.commit()


def eliminar_dispositivo(dispositivo_id):
    cursor.execute(
        "DELETE FROM dispositivos WHERE id = ?",
        (dispositivo_id,)
    )
    conexion.commit()


# =========================================================
# FUNCIONES ORIGINALES DE ARCHIVOS
# =========================================================

def adjuntar_archivo(nombre, ruta, usuario):
    if not nombre or not ruta or not usuario:
        return False

    try:
        fecha = datetime.datetime.now().isoformat(
            sep=" ", timespec="seconds"
        )
        cursor.execute("""
            INSERT INTO archivos (nombre, ruta, fecha, usuario)
            VALUES (?, ?, ?, ?)
        """, (nombre, ruta, fecha, usuario))
        conexion.commit()
        return True
    except sqlite3.Error:
        return False


def buscar_archivo(nombre_parcial=""):
    try:
        if nombre_parcial:
            return cursor.execute("""
                SELECT id, nombre, ruta, fecha, usuario
                FROM archivos
                WHERE nombre LIKE ? COLLATE NOCASE
                ORDER BY id DESC
            """, (f"%{nombre_parcial}%",)).fetchall()

        return cursor.execute("""
            SELECT id, nombre, ruta, fecha, usuario
            FROM archivos
            ORDER BY id DESC
        """).fetchall()

    except sqlite3.Error:
        return []


# =========================================================
# INICIALIZACIÓN DE LA INTERFAZ
# =========================================================

inicializar_db()
cargar_datos_demo()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ventana = ctk.CTk()
ventana.title("TEC4AR - Administrador de infraestructura")
ventana.geometry("1150x720")
ventana.minsize(900, 600)

ventana.grid_rowconfigure(0, weight=1)
ventana.grid_columnconfigure(0, weight=1)

pestanas = ctk.CTkTabview(ventana)
pestanas.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

pestanas.add("Infraestructura")
pestanas.add("Archivos")

tab_infra = pestanas.tab("Infraestructura")
tab_archivos = pestanas.tab("Archivos")

tab_infra.grid_rowconfigure(0, weight=1)
tab_infra.grid_columnconfigure(1, weight=1)


# =========================================================
# PANEL LATERAL
# =========================================================

lateral = ctk.CTkFrame(tab_infra, width=310, corner_radius=10)
lateral.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
lateral.grid_propagate(False)
lateral.grid_rowconfigure(1, weight=1)
lateral.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(
    lateral,
    text="REDES Y DISPOSITIVOS",
    font=ctk.CTkFont(size=17, weight="bold")
).grid(row=0, column=0, padx=12, pady=(15, 10), sticky="w")

# Treeview de Tkinter integrado con CustomTkinter.
estilo = ttk.Style()
estilo.theme_use("default")
estilo.configure(
    "Treeview",
    background="#242424",
    foreground="white",
    fieldbackground="#242424",
    borderwidth=0,
    rowheight=29,
    font=("Segoe UI", 10)
)
estilo.configure(
    "Treeview.Heading",
    background="#333333",
    foreground="white",
    font=("Segoe UI", 10, "bold")
)
estilo.map(
    "Treeview",
    background=[("selected", "#1f6aa5")],
    foreground=[("selected", "white")]
)

frame_arbol = ctk.CTkFrame(lateral, fg_color="transparent")
frame_arbol.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
frame_arbol.grid_rowconfigure(0, weight=1)
frame_arbol.grid_columnconfigure(0, weight=1)

arbol = ttk.Treeview(
    frame_arbol,
    columns=("tipo",),
    show="tree",
    selectmode="browse"
)
arbol.grid(row=0, column=0, sticky="nsew")

scroll_arbol = ttk.Scrollbar(
    frame_arbol,
    orient="vertical",
    command=arbol.yview
)
scroll_arbol.grid(row=0, column=1, sticky="ns")
arbol.configure(yscrollcommand=scroll_arbol.set)

arbol.tag_configure("Conectado", foreground="#5bd18b")
arbol.tag_configure("Desconectado", foreground="#ff7777")
arbol.tag_configure("Mantenimiento", foreground="#f2c14e")


# =========================================================
# PANEL CENTRAL
# =========================================================

central = ctk.CTkFrame(tab_infra, corner_radius=10)
central.grid(row=0, column=1, sticky="nsew")
central.grid_rowconfigure(1, weight=1)
central.grid_columnconfigure(0, weight=1)

titulo_central = ctk.CTkLabel(
    central,
    text="Seleccioná una red o dispositivo",
    font=ctk.CTkFont(size=22, weight="bold")
)
titulo_central.grid(row=0, column=0, sticky="w", padx=22, pady=(20, 10))

contenido = ctk.CTkScrollableFrame(central, fg_color="transparent")
contenido.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
contenido.grid_columnconfigure(0, weight=1)


def limpiar_contenido():
    for widget in contenido.winfo_children():
        widget.destroy()


def mostrar_mensaje(texto):
    limpiar_contenido()
    ctk.CTkLabel(
        contenido,
        text=texto,
        font=ctk.CTkFont(size=15),
        wraplength=650,
        justify="left"
    ).pack(anchor="w", padx=12, pady=12)


# =========================================================
# CONSTRUCCIÓN DINÁMICA DEL ÁRBOL
# =========================================================

elementos_arbol = {}


def recargar_arbol(seleccionar=None):
    arbol.delete(*arbol.get_children())
    elementos_arbol.clear()

    redes = obtener_redes()
    redes_por_padre = {}

    for red in redes:
        redes_por_padre.setdefault(red[3], []).append(red)

    def agregar_nivel(parent_id, nodo_padre=None):
        for red in redes_por_padre.get(parent_id, []):
            red_id, nombre, descripcion, padre = red
            iid = f"red_{red_id}"

            arbol.insert(
                nodo_padre,
                "end",
                iid,
                text=f"📁 {nombre}",
                open=True
            )

            elementos_arbol[iid] = {
                "tipo": "red",
                "id": red_id
            }

            # Agregar subredes
            agregar_nivel(red_id, iid)

            # Agregar dispositivos
            dispositivos = cursor.execute("""
                SELECT id, nombre, estado
                FROM dispositivos
                WHERE red_id = ?
                ORDER BY nombre COLLATE NOCASE
            """, (red_id,)).fetchall()

            for dispositivo_id, nombre_disp, estado in dispositivos:
                disp_iid = f"dispositivo_{dispositivo_id}"

                arbol.insert(
                    iid,
                    "end",
                    disp_iid,
                    text=f"🖥 {nombre_disp}",
                    tags=(estado,)
                )

                elementos_arbol[disp_iid] = {
                    "tipo": "dispositivo",
                    "id": dispositivo_id
                }

    agregar_nivel(None)

    if seleccionar and seleccionar in elementos_arbol:
        arbol.selection_set(seleccionar)
        arbol.focus(seleccionar)
        arbol.see(seleccionar)


# =========================================================
# VISUALIZACIÓN DE REDES Y DISPOSITIVOS
# =========================================================

def mostrar_red(red_id):
    red = obtener_red(red_id)

    if not red:
        mostrar_mensaje("No se encontró la red seleccionada.")
        return

    _, nombre, descripcion, parent_id = red

    titulo_central.configure(text=nombre)
    limpiar_contenido()

    ctk.CTkLabel(
        contenido,
        text="Información de la red",
        font=ctk.CTkFont(size=18, weight="bold")
    ).pack(anchor="w", padx=10, pady=(8, 12))

    ctk.CTkLabel(
        contenido,
        text=f"Nombre: {nombre}",
        font=ctk.CTkFont(size=14)
    ).pack(anchor="w", padx=10, pady=5)

    ctk.CTkLabel(
        contenido,
        text=f"Descripción: {descripcion or 'Sin descripción'}",
        font=ctk.CTkFont(size=14),
        wraplength=650,
        justify="left"
    ).pack(anchor="w", padx=10, pady=5)

    if parent_id:
        padre = obtener_red(parent_id)
        nombre_padre = padre[1] if padre else "No disponible"
        ctk.CTkLabel(
            contenido,
            text=f"Red superior: {nombre_padre}",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", padx=10, pady=5)

    subredes = cursor.execute("""
        SELECT nombre FROM redes
        WHERE parent_id = ?
        ORDER BY nombre COLLATE NOCASE
    """, (red_id,)).fetchall()

    dispositivos = obtener_dispositivos(red_id)

    ctk.CTkLabel(
        contenido,
        text=f"Subredes: {len(subredes)}",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=10, pady=(18, 5))

    for subred in subredes:
        ctk.CTkLabel(
            contenido,
            text=f"📁 {subred[0]}"
        ).pack(anchor="w", padx=25, pady=2)

    ctk.CTkLabel(
        contenido,
        text=f"Dispositivos: {len(dispositivos)}",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=10, pady=(18, 5))

    for dispositivo in dispositivos:
        _, nombre_disp, tipo, estado = dispositivo
        ctk.CTkLabel(
            contenido,
            text=f"🖥 {nombre_disp}  |  {tipo or 'Sin tipo'}  |  {estado}"
        ).pack(anchor="w", padx=25, pady=2)


def mostrar_dispositivo(dispositivo_id):
    dispositivo = obtener_dispositivo(dispositivo_id)

    if not dispositivo:
        mostrar_mensaje("No se encontró el dispositivo seleccionado.")
        return

    (
        id_disp, red_id, nombre, tipo, ip, mac, estado,
        fabricante, modelo, ubicacion, sistema, descripcion
    ) = dispositivo

    titulo_central.configure(text=nombre)
    limpiar_contenido()

    ctk.CTkLabel(
        contenido,
        text="Características del dispositivo",
        font=ctk.CTkFont(size=18, weight="bold")
    ).pack(anchor="w", padx=10, pady=(8, 15))

    datos = [
        ("Nombre", nombre),
        ("Tipo", tipo),
        ("Dirección IP", ip),
        ("Dirección MAC", mac),
        ("Estado", estado),
        ("Fabricante", fabricante),
        ("Modelo", modelo),
        ("Ubicación", ubicacion),
        ("Sistema operativo", sistema),
        ("Descripción", descripcion),
    ]

    for etiqueta, valor in datos:
        fila = ctk.CTkFrame(contenido, fg_color="transparent")
        fila.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(
            fila,
            text=f"{etiqueta}:",
            width=150,
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            fila,
            text=valor or "Sin información",
            anchor="w",
            justify="left",
            wraplength=430
        ).pack(side="left", fill="x", expand=True, padx=5)

    ctk.CTkButton(
        contenido,
        text="Editar características",
        command=lambda: editar_dispositivo(id_disp)
    ).pack(anchor="w", padx=12, pady=20)


def seleccionar_elemento(event=None):
    seleccion = arbol.selection()

    if not seleccion:
        return

    iid = seleccion[0]
    info = elementos_arbol.get(iid)

    if not info:
        return

    if info["tipo"] == "red":
        mostrar_red(info["id"])
    else:
        mostrar_dispositivo(info["id"])


arbol.bind("<<TreeviewSelect>>", seleccionar_elemento)


# =========================================================
# FORMULARIO DE DISPOSITIVOS
# =========================================================

def formulario_dispositivo(red_id, dispositivo_id=None):
    existente = (
        obtener_dispositivo(dispositivo_id)
        if dispositivo_id else None
    )

    dialogo = ctk.CTkToplevel(ventana)
    dialogo.title(
        "Editar dispositivo" if existente else "Añadir dispositivo"
    )
    dialogo.geometry("520x690")
    dialogo.transient(ventana)
    dialogo.grab_set()
    dialogo.grid_columnconfigure(1, weight=1)

    entradas = {}

    valores = {}
    if existente:
        valores = {
            "nombre": existente[2],
            "tipo": existente[3],
            "ip": existente[4],
            "mac": existente[5],
            "estado": existente[6],
            "fabricante": existente[7],
            "modelo": existente[8],
            "ubicacion": existente[9],
            "sistema": existente[10],
            "descripcion": existente[11],
        }

    ctk.CTkLabel(
        dialogo,
        text="Datos del dispositivo",
        font=ctk.CTkFont(size=20, weight="bold")
    ).grid(row=0, column=0, columnspan=2, padx=15, pady=15)

    for indice, (campo, etiqueta) in enumerate(CAMPOS_DISPOSITIVO, start=1):
        ctk.CTkLabel(
            dialogo,
            text=etiqueta
        ).grid(row=indice, column=0, sticky="w", padx=15, pady=6)

        if campo == "estado":
            entrada = ctk.CTkOptionMenu(
                dialogo,
                values=[
                    "Conectado",
                    "Desconectado",
                    "Mantenimiento",
                    "Desconocido"
                ]
            )
            entrada.set(valores.get(campo, "Desconocido"))
        elif campo == "descripcion":
            entrada = ctk.CTkTextbox(dialogo, height=75)
            entrada.insert("1.0", valores.get(campo, ""))
        else:
            entrada = ctk.CTkEntry(dialogo)
            entrada.insert(0, valores.get(campo, ""))

        entrada.grid(
            row=indice,
            column=1,
            sticky="ew",
            padx=15,
            pady=5
        )
        entradas[campo] = entrada

    def guardar():
        datos = {}

        for campo, entrada in entradas.items():
            if campo == "descripcion":
                datos[campo] = entrada.get("1.0", "end").strip()
            else:
                datos[campo] = entrada.get().strip()

        if not datos["nombre"]:
            messagebox.showwarning(
                "Dato obligatorio",
                "El dispositivo debe tener un nombre.",
                parent=dialogo
            )
            return

        if existente:
            actualizar_dispositivo(dispositivo_id, datos)
            id_guardado = dispositivo_id
        else:
            id_guardado = crear_dispositivo(red_id, datos)

        dialogo.destroy()
        recargar_arbol(f"dispositivo_{id_guardado}")
        mostrar_dispositivo(id_guardado)

    ctk.CTkButton(
        dialogo,
        text="Guardar",
        command=guardar
    ).grid(row=len(CAMPOS_DISPOSITIVO) + 1, column=0,
           columnspan=2, pady=18)


def editar_dispositivo(dispositivo_id):
    dispositivo = obtener_dispositivo(dispositivo_id)
    if dispositivo:
        formulario_dispositivo(
            dispositivo[1],
            dispositivo_id=dispositivo_id
        )


# =========================================================
# FORMULARIO DE SUBREDES
# =========================================================

def formulario_subred(parent_id):
    dialogo = ctk.CTkToplevel(ventana)
    dialogo.title("Crear subred")
    dialogo.geometry("400x260")
    dialogo.transient(ventana)
    dialogo.grab_set()

    ctk.CTkLabel(
        dialogo,
        text="Nueva subred",
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=(20, 12))

    entrada_nombre = ctk.CTkEntry(
        dialogo,
        placeholder_text="Nombre de la subred",
        width=300
    )
    entrada_nombre.pack(pady=8)

    entrada_descripcion = ctk.CTkEntry(
        dialogo,
        placeholder_text="Descripción (opcional)",
        width=300
    )
    entrada_descripcion.pack(pady=8)

    def guardar():
        nombre = entrada_nombre.get().strip()
        descripcion = entrada_descripcion.get().strip()

        if not nombre:
            messagebox.showwarning(
                "Dato obligatorio",
                "Ingresá un nombre para la subred.",
                parent=dialogo
            )
            return

        nuevo_id = crear_red(nombre, descripcion, parent_id)
        dialogo.destroy()
        recargar_arbol(f"red_{nuevo_id}")
        mostrar_red(nuevo_id)

    ctk.CTkButton(
        dialogo,
        text="Crear subred",
        command=guardar
    ).pack(pady=18)


# =========================================================
# SELECTOR PARA AGREGAR ELEMENTOS
# =========================================================

def abrir_selector_agregar():
    seleccion = arbol.selection()

    if not seleccion:
        messagebox.showinfo(
            "Seleccionar red",
            "Primero seleccioná una red o subred en el panel izquierdo."
        )
        return

    info = elementos_arbol.get(seleccion[0])

    if not info or info["tipo"] != "red":
        messagebox.showwarning(
            "Selección incorrecta",
            "Para agregar elementos, seleccioná una red o subred."
        )
        return

    red_id = info["id"]

    selector = ctk.CTkToplevel(ventana)
    selector.title("Agregar elemento")
    selector.geometry("360x240")
    selector.transient(ventana)
    selector.grab_set()

    ctk.CTkLabel(
        selector,
        text="¿Qué querés agregar?",
        font=ctk.CTkFont(size=19, weight="bold")
    ).pack(pady=(25, 18))

    ctk.CTkButton(
        selector,
        text="📁 Crear subred",
        width=230,
        height=40,
        command=lambda: (
            selector.destroy(),
            formulario_subred(red_id)
        )
    ).pack(pady=8)

    ctk.CTkButton(
        selector,
        text="🖥 Añadir dispositivo",
        width=230,
        height=40,
        command=lambda: (
            selector.destroy(),
            formulario_dispositivo(red_id)
        )
    ).pack(pady=8)


# =========================================================
# RENOMBRAR REDES Y SUBREDES
# =========================================================

def editar_nombre_red():
    seleccion = arbol.selection()

    if not seleccion:
        messagebox.showinfo(
            "Seleccionar red",
            "Seleccioná una red o subred para renombrarla."
        )
        return

    info = elementos_arbol.get(seleccion[0])

    if not info or info["tipo"] != "red":
        messagebox.showwarning(
            "Selección incorrecta",
            "Solo se pueden renombrar redes y subredes."
        )
        return

    red = obtener_red(info["id"])
    if not red:
        return

    dialogo = ctk.CTkInputDialog(
        text="Ingresá el nuevo nombre:",
        title="Renombrar red"
    )
    nuevo_nombre = dialogo.get_input()

    if nuevo_nombre is None:
        return

    nuevo_nombre = nuevo_nombre.strip()

    if not nuevo_nombre:
        messagebox.showwarning(
            "Nombre inválido",
            "El nombre no puede estar vacío."
        )
        return

    renombrar_red(info["id"], nuevo_nombre)
    recargar_arbol(seleccion[0])
    mostrar_red(info["id"])


# =========================================================
# ELIMINAR REDES, SUBREDES Y DISPOSITIVOS
# =========================================================

def eliminar_elemento():
    seleccion = arbol.selection()

    if not seleccion:
        messagebox.showinfo(
            "Seleccionar elemento",
            "Seleccioná una red, subred o dispositivo."
        )
        return

    iid = seleccion[0]
    info = elementos_arbol.get(iid)

    if not info:
        return

    if info["tipo"] == "red":
        red = obtener_red(info["id"])
        if not red:
            return

        confirmar = messagebox.askyesno(
            "Eliminar red",
            f"¿Eliminar '{red[1]}'?\n\n"
            "También se eliminarán todas sus subredes "
            "y los dispositivos que contengan."
        )

        if confirmar:
            eliminar_red(info["id"])
            recargar_arbol()
            mostrar_mensaje("La red fue eliminada.")

    else:
        dispositivo = obtener_dispositivo(info["id"])
        if not dispositivo:
            return

        confirmar = messagebox.askyesno(
            "Eliminar dispositivo",
            f"¿Eliminar el dispositivo '{dispositivo[2]}'?"
        )

        if confirmar:
            eliminar_dispositivo(info["id"])
            recargar_arbol()
            mostrar_mensaje("El dispositivo fue eliminado.")


# =========================================================
# BOTONES DEL PANEL LATERAL
# =========================================================

botonera = ctk.CTkFrame(lateral, fg_color="transparent")
botonera.grid(row=2, column=0, sticky="ew", padx=8, pady=12)
botonera.grid_columnconfigure((0, 1), weight=1)

ctk.CTkButton(
    botonera,
    text="＋ Agregar",
    command=abrir_selector_agregar
).grid(row=0, column=0, sticky="ew", padx=4, pady=4)

ctk.CTkButton(
    botonera,
    text="✎ Renombrar",
    command=editar_nombre_red
).grid(row=0, column=1, sticky="ew", padx=4, pady=4)

ctk.CTkButton(
    botonera,
    text="Eliminar",
    fg_color="#9b3030",
    hover_color="#752424",
    command=eliminar_elemento
).grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=4)


# =========================================================
# PESTAÑA DE ARCHIVOS
# =========================================================

tab_archivos.grid_columnconfigure(0, weight=1)
tab_archivos.grid_rowconfigure(2, weight=1)

ctk.CTkLabel(
    tab_archivos,
    text="Administración de archivos",
    font=ctk.CTkFont(size=22, weight="bold")
).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")

form_archivos = ctk.CTkFrame(tab_archivos)
form_archivos.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
form_archivos.grid_columnconfigure(1, weight=1)

entrada_nombre = ctk.CTkEntry(
    form_archivos,
    placeholder_text="Nombre del archivo"
)
entrada_nombre.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

entrada_ruta = ctk.CTkEntry(
    form_archivos,
    placeholder_text="Ruta del archivo"
)
entrada_ruta.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

entrada_usuario = ctk.CTkEntry(
    form_archivos,
    placeholder_text="Usuario"
)
entrada_usuario.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

frame_resultados = ctk.CTkScrollableFrame(
    tab_archivos,
    label_text="Resultados"
)
frame_resultados.grid(
    row=2, column=0, sticky="nsew", padx=12, pady=8
)


def limpiar_resultados():
    for widget in frame_resultados.winfo_children():
        widget.destroy()


def accion_adjuntar():
    nombre = entrada_nombre.get().strip()
    ruta = entrada_ruta.get().strip()
    usuario = entrada_usuario.get().strip()

    if adjuntar_archivo(nombre, ruta, usuario):
        messagebox.showinfo(
            "Archivo adjuntado",
            "El archivo se registró correctamente."
        )
        entrada_nombre.delete(0, "end")
        entrada_ruta.delete(0, "end")
        entrada_usuario.delete(0, "end")
        accion_buscar()
    else:
        messagebox.showerror(
            "Error",
            "No se pudo adjuntar el archivo. Revisá los campos."
        )


def accion_buscar():
    limpiar_resultados()

    nombre_buscar = entrada_nombre.get().strip()
    resultados = buscar_archivo(nombre_buscar)

    if not resultados:
        ctk.CTkLabel(
            frame_resultados,
            text="No se encontraron resultados."
        ).pack(anchor="w", padx=8, pady=8)
        return

    for registro in resultados:
        id_archivo, nombre, ruta, fecha, usuario = registro

        texto = (
            f"ID: {id_archivo}  |  {nombre}\n"
            f"Ruta: {ruta}\n"
            f"Fecha: {fecha}  |  Usuario: {usuario}"
        )

        ctk.CTkLabel(
            frame_resultados,
            text=texto,
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=8, pady=6)


botones_archivos = ctk.CTkFrame(
    form_archivos,
    fg_color="transparent"
)
botones_archivos.grid(
    row=1, column=0, columnspan=3, pady=(0, 8)
)

ctk.CTkButton(
    botones_archivos,
    text="Adjuntar archivo",
    command=accion_adjuntar
).pack(side="left", padx=6)

ctk.CTkButton(
    botones_archivos,
    text="Buscar archivos",
    command=accion_buscar
).pack(side="left", padx=6)


# =========================================================
# ARRANQUE Y CIERRE
# =========================================================

recargar_arbol()
accion_buscar()


def cerrar_aplicacion():
    try:
        conexion.commit()
        conexion.close()
    finally:
        ventana.destroy()


ventana.protocol("WM_DELETE_WINDOW", cerrar_aplicacion)
ventana.mainloop()