import sqlite3
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
# IMPORTACIÓN DE DISPOSITIVOS DESDE OTRA BASE SQLITE
# =========================================================

ESQUEMA_COMPATIBLE = {
    "redes": {"id", "nombre", "descripcion", "parent_id"},
    "dispositivos": {
        "id", "red_id", "nombre", "tipo", "ip", "mac", "estado",
        "fabricante", "modelo", "ubicacion", "sistema", "descripcion"
    },
}


def validar_base_compatible(ruta_db):
    """Exige redes y dispositivos con sus columnas; ignora tablas adicionales antiguas."""
    db_origen = sqlite3.connect(ruta_db)
    try:
        tablas = {
            fila[0] for fila in db_origen.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """).fetchall()
        }

        tablas_esperadas = set(ESQUEMA_COMPATIBLE)
        faltantes = tablas_esperadas - tablas
        if faltantes:
            return False, (
                "El modelo de tablas no coincide; faltan: "
                + ", ".join(sorted(faltantes)) + "."
            )

        for tabla, columnas_esperadas in ESQUEMA_COMPATIBLE.items():
            columnas_reales = {
                fila[1] for fila in db_origen.execute(
                    f'PRAGMA table_info("{tabla}")'
                ).fetchall()
            }
            faltan = columnas_esperadas - columnas_reales
            if faltan:
                return False, (
                    f"La tabla '{tabla}' no contiene las columnas requeridas: "
                    + ", ".join(sorted(faltan)) + "."
                )

        # Comprobar que las relaciones de redes y dispositivos sean utilizables.
        redes_invalidas = db_origen.execute("""
            SELECT COUNT(*) FROM dispositivos d
            LEFT JOIN redes r ON r.id = d.red_id
            WHERE r.id IS NULL
        """).fetchone()[0]
        if redes_invalidas:
            return False, (
                f"La base contiene {redes_invalidas} dispositivo(s) "
                "sin una red asociada válida."
            )

        return True, "Base de datos compatible."
    except sqlite3.DatabaseError as error:
        return False, f"No se pudo leer la base SQLite: {error}"
    finally:
        db_origen.close()


def importar_dispositivos_desde_db(ruta_db):
    """Importa redes/subredes necesarias y dispositivos; no modifica el archivo origen."""
    compatible, mensaje = validar_base_compatible(ruta_db)
    if not compatible:
        raise ValueError(mensaje)

    db_origen = sqlite3.connect(ruta_db)
    db_origen.row_factory = sqlite3.Row
    redes_importadas = 0
    dispositivos_importados = 0
    dispositivos_omitidos = 0

    try:
        redes_origen = db_origen.execute("""
            SELECT id, nombre, descripcion, parent_id
            FROM redes ORDER BY id
        """).fetchall()
        dispositivos_origen = db_origen.execute("""
            SELECT id, red_id, nombre, tipo, ip, mac, estado,
                   fabricante, modelo, ubicacion, sistema, descripcion
            FROM dispositivos ORDER BY id
        """).fetchall()

        mapa_redes = {}
        pendientes = list(redes_origen)

        # Toda la importación se confirma junta: si algo falla, se revierte.
        conexion.execute("BEGIN")
        while pendientes:
            avance = False
            for red in pendientes[:]:
                origen_id = red["id"]
                padre_origen = red["parent_id"]
                if padre_origen is not None and padre_origen not in mapa_redes:
                    continue

                padre_destino = (
                    mapa_redes[padre_origen]
                    if padre_origen is not None else None
                )

                existente = cursor.execute("""
                    SELECT id FROM redes
                    WHERE nombre = ? COLLATE NOCASE
                      AND parent_id IS ?
                    LIMIT 1
                """, (red["nombre"], padre_destino)).fetchone()

                if existente:
                    destino_id = existente[0]
                else:
                    cursor.execute("""
                        INSERT INTO redes (nombre, descripcion, parent_id)
                        VALUES (?, ?, ?)
                    """, (red["nombre"], red["descripcion"] or "", padre_destino))
                    destino_id = cursor.lastrowid
                    redes_importadas += 1

                mapa_redes[origen_id] = destino_id
                pendientes.remove(red)
                avance = True

            if not avance:
                raise ValueError(
                    "La estructura de redes de la base de origen contiene "
                    "referencias circulares o subredes sin una red superior válida."
                )

        for dispositivo in dispositivos_origen:
            red_destino = mapa_redes.get(dispositivo["red_id"])
            if red_destino is None:
                raise ValueError(
                    f"No se pudo asociar la red del dispositivo '{dispositivo['nombre']}'."
                )

            # Evita duplicar dispositivos que ya estén en la misma red.
            duplicado = cursor.execute("""
                SELECT id FROM dispositivos
                WHERE red_id = ?
                  AND nombre = ? COLLATE NOCASE
                  AND COALESCE(ip, '') = COALESCE(?, '')
                LIMIT 1
            """, (red_destino, dispositivo["nombre"], dispositivo["ip"])).fetchone()

            if duplicado:
                dispositivos_omitidos += 1
                continue

            cursor.execute("""
                INSERT INTO dispositivos (
                    red_id, nombre, tipo, ip, mac, estado,
                    fabricante, modelo, ubicacion, sistema, descripcion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                red_destino,
                dispositivo["nombre"],
                dispositivo["tipo"] or "",
                dispositivo["ip"] or "",
                dispositivo["mac"] or "",
                dispositivo["estado"] or "Desconocido",
                dispositivo["fabricante"] or "",
                dispositivo["modelo"] or "",
                dispositivo["ubicacion"] or "",
                dispositivo["sistema"] or "",
                dispositivo["descripcion"] or "",
            ))
            dispositivos_importados += 1

        conexion.commit()
        return {
            "redes": redes_importadas,
            "dispositivos": dispositivos_importados,
            "omitidos": dispositivos_omitidos,
        }
    except Exception:
        conexion.rollback()
        raise
    finally:
        db_origen.close()


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
tab_infra = pestanas.tab("Infraestructura")

tab_infra.grid_rowconfigure(0, weight=1)
tab_infra.grid_columnconfigure(1, weight=1)


# =========================================================
# PANEL LATERAL
# =========================================================

lateral = ctk.CTkFrame(tab_infra, width=310, corner_radius=10)
lateral.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
lateral.grid_propagate(False)
lateral.grid_rowconfigure(2, weight=1)
lateral.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(
    lateral,
    text="REDES Y DISPOSITIVOS",
    font=ctk.CTkFont(size=17, weight="bold")
).grid(row=0, column=0, padx=12, pady=(15, 8), sticky="w")

# Selector de base SQLite: queda por encima del árbol de redes.
frame_importacion = ctk.CTkFrame(lateral, fg_color="transparent")
frame_importacion.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
frame_importacion.grid_columnconfigure(0, weight=1)

ruta_db_seleccionada = tk.StringVar(value="")
entrada_db = ctk.CTkEntry(
    frame_importacion,
    textvariable=ruta_db_seleccionada,
    placeholder_text="Seleccionar base SQLite (.db)",
    state="readonly"
)
entrada_db.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=3)


def seleccionar_base_sqlite():
    ruta = filedialog.askopenfilename(
        title="Seleccionar base de datos SQLite",
        filetypes=[
            ("Bases de datos SQLite", "*.db *.sqlite *.sqlite3"),
            ("Todos los archivos", "*.*")
        ]
    )
    if ruta:
        ruta_db_seleccionada.set(ruta)


def confirmar_importacion_dispositivos():
    ruta = ruta_db_seleccionada.get().strip()
    if not ruta:
        messagebox.showwarning(
            "Seleccionar archivo",
            "Primero seleccioná una base de datos SQLite (.db).",
            parent=ventana
        )
        return

    compatible, mensaje = validar_base_compatible(ruta)
    if not compatible:
        messagebox.showerror(
            "Base incompatible",
            "No se puede importar esta base de datos.\n\n" + mensaje,
            parent=ventana
        )
        return

    confirmar = messagebox.askyesno(
        "Confirmar carga de dispositivos",
        "La base seleccionada tiene las tablas y columnas requeridas.\n\n"
        "Se incorporarán sus redes/subredes necesarias y sus dispositivos "
        "a la base actual. Los dispositivos que ya existan en la misma red "
        "con el mismo nombre e IP se omitirán.\n\n"
        "La base de origen no será modificada. ¿Deseás continuar?",
        parent=ventana
    )
    if not confirmar:
        return

    try:
        resultado = importar_dispositivos_desde_db(ruta)
        recargar_arbol()
        messagebox.showinfo(
            "Importación completada",
            "La carga finalizó correctamente.\n\n"
            f"Redes/subredes nuevas: {resultado['redes']}\n"
            f"Dispositivos importados: {resultado['dispositivos']}\n"
            f"Dispositivos omitidos por duplicación: {resultado['omitidos']}",
            parent=ventana
        )
    except (sqlite3.Error, ValueError, OSError) as error:
        messagebox.showerror(
            "Error de importación",
            f"No se pudo completar la carga.\n\n{error}",
            parent=ventana
        )


ctk.CTkButton(
    frame_importacion,
    text="Examinar...",
    width=90,
    command=seleccionar_base_sqlite
).grid(row=0, column=1, padx=(0, 0), pady=3)

ctk.CTkButton(
    frame_importacion,
    text="Cargar dispositivos desde SQLite",
    command=confirmar_importacion_dispositivos,
    height=30
).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 2))

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
frame_arbol.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
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
central.grid_columnconfigure(1, weight=0)

titulo_central = ctk.CTkLabel(
    central,
    text="Seleccioná una red o dispositivo",
    font=ctk.CTkFont(size=22, weight="bold")
)
titulo_central.grid(row=0, column=0, sticky="w", padx=(22, 10), pady=(20, 10))

# Identifica la base de datos activa de la aplicación (no el archivo importado).
nombre_base_activa = os.path.basename(os.path.abspath(DB_NAME))
etiqueta_base_activa = ctk.CTkLabel(
    central,
    text=f"Base de datos: {nombre_base_activa}",
    font=ctk.CTkFont(size=12, weight="bold"),
    text_color="#9FA8B3"
)
etiqueta_base_activa.grid(
    row=0, column=1, sticky="e", padx=(8, 18), pady=(20, 10)
)

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

            # Tkinter requiere una cadena vacía para los nodos raíz;
            # pasar None puede provocar TclError en algunas versiones.
            arbol.insert(
                nodo_padre if nodo_padre is not None else "",
                "end",
                iid=iid,
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
                    iid=disp_iid,
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
botonera.grid(row=3, column=0, sticky="ew", padx=8, pady=12)
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
# ARRANQUE Y CIERRE
# =========================================================

recargar_arbol()


def cerrar_aplicacion():
    try:
        conexion.commit()
        conexion.close()
    finally:
        ventana.destroy()


ventana.protocol("WM_DELETE_WINDOW", cerrar_aplicacion)
ventana.mainloop()