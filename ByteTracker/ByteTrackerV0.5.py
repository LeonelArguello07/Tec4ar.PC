import sqlite3
import os
import ipaddress
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk


# =========================================================
# CONFIGURACIÓN Y BASE DE DATOS
# =========================================================

DB_NAME = "Ejemplo.db"
ruta_base_activa = os.path.abspath(DB_NAME)
ruta_base_nueva_pendiente = None
cambios_pendientes = []

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
            cidr TEXT DEFAULT '',
            FOREIGN KEY (parent_id) REFERENCES redes(id) ON DELETE CASCADE
        )
    """)

    # Migración para bases de datos creadas con una versión anterior.
    columnas = {
        fila[1] for fila in cursor.execute("PRAGMA table_info(redes)").fetchall()
    }
    migraciones_redes = {
        "descripcion": "TEXT DEFAULT ''",
        "parent_id": "INTEGER REFERENCES redes(id) ON DELETE CASCADE",
        "cidr": "TEXT DEFAULT ''",
    }
    for columna, definicion in migraciones_redes.items():
        if columna not in columnas:
            cursor.execute(
                f'ALTER TABLE redes ADD COLUMN "{columna}" {definicion}'
            )

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

    columnas_dispositivos = {
        fila[1] for fila in cursor.execute(
            "PRAGMA table_info(dispositivos)"
        ).fetchall()
    }
    migraciones_dispositivos = {
        "tipo": "TEXT DEFAULT ''",
        "ip": "TEXT DEFAULT ''",
        "mac": "TEXT DEFAULT ''",
        "estado": "TEXT DEFAULT 'Desconocido'",
        "fabricante": "TEXT DEFAULT ''",
        "modelo": "TEXT DEFAULT ''",
        "ubicacion": "TEXT DEFAULT ''",
        "sistema": "TEXT DEFAULT ''",
        "descripcion": "TEXT DEFAULT ''",
    }
    for columna, definicion in migraciones_dispositivos.items():
        if columna not in columnas_dispositivos:
            cursor.execute(
                f'ALTER TABLE dispositivos ADD COLUMN "{columna}" {definicion}'
            )


    conexion.commit()


def registrar_cambio(descripcion):
    cambios_pendientes.append(descripcion)
    actualizar_estado_cambios()


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
        SELECT id, nombre, descripcion, parent_id, cidr
        FROM redes
        ORDER BY nombre COLLATE NOCASE
    """).fetchall()


def obtener_red(red_id):
    return cursor.execute("""
        SELECT id, nombre, descripcion, parent_id, cidr
        FROM redes
        WHERE id = ?
    """, (red_id,)).fetchone()


def crear_red(nombre, descripcion="", parent_id=None):
    cursor.execute("""
        INSERT INTO redes (nombre, descripcion, parent_id, cidr)
        VALUES (?, ?, ?, '')
    """, (nombre, descripcion, parent_id))
    padre = obtener_red(parent_id) if parent_id else None
    registrar_cambio(
        f"Crear red principal '{nombre}'" if not parent_id else
        f"Crear subred '{nombre}' dentro de '{padre[1] if padre else 'red superior'}'"
    )
    return cursor.lastrowid


def renombrar_red(red_id, nuevo_nombre):
    anterior = obtener_red(red_id)
    if not anterior or anterior[1] == nuevo_nombre:
        return
    cursor.execute(
        "UPDATE redes SET nombre = ? WHERE id = ?",
        (nuevo_nombre, red_id)
    )
    registrar_cambio(f"Renombrar red '{anterior[1]}' a '{nuevo_nombre}'")


def actualizar_plan_red(red_id, cidr):
    red = obtener_red(red_id)
    if not red:
        return
    nuevo_cidr = ipaddress.IPv4Network(cidr, strict=False).with_prefixlen
    if (red[4] or "") == nuevo_cidr:
        return
    cursor.execute("UPDATE redes SET cidr = ? WHERE id = ?", (nuevo_cidr, red_id))
    registrar_cambio(
        f"Actualizar planificación de '{red[1]}': {red[4] or 'sin CIDR'} → {nuevo_cidr}"
    )


def eliminar_red(red_id):
    red = obtener_red(red_id)
    if not red:
        return
    cantidad_redes, cantidad_dispositivos = cursor.execute("""
        WITH RECURSIVE arbol(id) AS (
            SELECT id FROM redes WHERE id = ?
            UNION
            SELECT redes.id FROM redes JOIN arbol ON redes.parent_id = arbol.id
        )
        SELECT (SELECT COUNT(*) FROM arbol),
               (SELECT COUNT(*) FROM dispositivos
                WHERE red_id IN (SELECT id FROM arbol))
    """, (red_id,)).fetchone()
    # Las claves foráneas eliminan automáticamente sus subredes
    # y los dispositivos asociados.
    cursor.execute("DELETE FROM redes WHERE id = ?", (red_id,))
    registrar_cambio(
        f"Eliminar '{red[1]}' y {max(0, cantidad_redes - 1)} subred(es), "
        f"{cantidad_dispositivos} dispositivo(s) asociado(s)"
    )


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
    red = obtener_red(red_id)
    registrar_cambio(
        f"Añadir '{datos['nombre']}' ({datos['tipo'] or 'sin tipo'}"
        + (f", IP {datos['ip']}" if datos['ip'] else "")
        + f") a '{red[1] if red else 'red'}'"
    )
    return cursor.lastrowid


def actualizar_dispositivo(dispositivo_id, datos):
    anterior = obtener_dispositivo(dispositivo_id)
    if not anterior:
        return
    campos = (
        ("nombre", 2, "nombre"),
        ("tipo", 3, "tipo"),
        ("ip", 4, "IP"),
        ("mac", 5, "MAC"),
        ("estado", 6, "estado"),
        ("fabricante", 7, "fabricante"),
        ("modelo", 8, "modelo"),
        ("ubicacion", 9, "ubicación"),
        ("sistema", 10, "sistema"),
        ("descripcion", 11, "descripción"),
    )
    diferencias = [
        f"{etiqueta}: {anterior[indice] or 'vacío'} → {datos[campo] or 'vacío'}"
        for campo, indice, etiqueta in campos
        if (anterior[indice] or "") != (datos[campo] or "")
    ]
    if not diferencias:
        return
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
    registrar_cambio(
        f"Actualizar dispositivo '{anterior[2]}': " + "; ".join(diferencias)
    )


def eliminar_dispositivo(dispositivo_id):
    anterior = obtener_dispositivo(dispositivo_id)
    cursor.execute(
        "DELETE FROM dispositivos WHERE id = ?",
        (dispositivo_id,)
    )
    if anterior:
        registrar_cambio(f"Eliminar dispositivo '{anterior[2]}'")


# =========================================================
# IMPORTACIÓN DE DISPOSITIVOS DESDE OTRA BASE SQLITE
# =========================================================

ESQUEMA_COMPATIBLE = {
    "redes": {"id", "nombre"},
    "dispositivos": {"id", "red_id", "nombre"},
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
        columnas_red = {
            fila[1] for fila in db_origen.execute('PRAGMA table_info("redes")')
        }
        columnas_dispositivo = {
            fila[1] for fila in db_origen.execute('PRAGMA table_info("dispositivos")')
        }

        def seleccionar_columna(columnas, nombre, valor_predeterminado="''"):
            if nombre in columnas:
                return f'"{nombre}" AS "{nombre}"'
            return f'{valor_predeterminado} AS "{nombre}"'

        redes_origen = db_origen.execute("""
            SELECT id, nombre,
                   {descripcion}, {parent_id}, {cidr}
            FROM redes ORDER BY id
        """.format(
            descripcion=seleccionar_columna(columnas_red, "descripcion"),
            parent_id=seleccionar_columna(columnas_red, "parent_id", "NULL"),
            cidr=seleccionar_columna(columnas_red, "cidr"),
        )).fetchall()
        dispositivos_origen = db_origen.execute("""
            SELECT id, red_id, nombre,
                   {tipo}, {ip}, {mac}, {estado}, {fabricante}, {modelo},
                   {ubicacion}, {sistema}, {descripcion}
            FROM dispositivos ORDER BY id
        """.format(**{
            campo: seleccionar_columna(
                columnas_dispositivo,
                campo,
                "'Desconocido'" if campo == "estado" else "''"
            )
            for campo in (
                "tipo", "ip", "mac", "estado", "fabricante", "modelo",
                "ubicacion", "sistema", "descripcion"
            )
        })).fetchall()

        mapa_redes = {}
        pendientes = list(redes_origen)

        # Mantener una transacción exterior evita que RELEASE confirme la carga.
        if not conexion.in_transaction:
            conexion.execute("BEGIN")
        # El punto de guardado permite deshacer solo la importación si falla.
        conexion.execute("SAVEPOINT importar_dispositivos")
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
                        INSERT INTO redes (nombre, descripcion, parent_id, cidr)
                        VALUES (?, ?, ?, ?)
                    """, (
                        red["nombre"], red["descripcion"] or "", padre_destino,
                        red["cidr"] or ""
                    ))
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

        conexion.execute("RELEASE SAVEPOINT importar_dispositivos")
        if redes_importadas or dispositivos_importados:
            registrar_cambio(
                f"Importar desde '{os.path.basename(ruta_db)}': "
                f"{redes_importadas} red(es), {dispositivos_importados} dispositivo(s); "
                f"{dispositivos_omitidos} duplicado(s) omitido(s)"
            )
        return {
            "redes": redes_importadas,
            "dispositivos": dispositivos_importados,
            "omitidos": dispositivos_omitidos,
        }
    except Exception:
        try:
            conexion.execute("ROLLBACK TO SAVEPOINT importar_dispositivos")
            conexion.execute("RELEASE SAVEPOINT importar_dispositivos")
        except sqlite3.Error:
            pass
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

ventana.grid_rowconfigure(1, weight=1)
ventana.grid_columnconfigure(0, weight=1)

encabezado = ctk.CTkFrame(ventana, fg_color="transparent")
encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(10, 0))
encabezado.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(
    encabezado,
    text="◈  TEC4AR",
    font=ctk.CTkFont(size=21, weight="bold")
).grid(row=0, column=0, sticky="w")

modo_oscuro = True


def alternar_tema():
    global modo_oscuro
    modo_oscuro = not modo_oscuro
    ctk.set_appearance_mode("dark" if modo_oscuro else "light")
    boton_tema.configure(text="☀ Claro" if modo_oscuro else "☾ Oscuro")
    if "estilo" in globals():
        fondo = "#242424" if modo_oscuro else "#f2f2f2"
        texto = "white" if modo_oscuro else "#222222"
        cabecera = "#333333" if modo_oscuro else "#dddddd"
        estilo.configure(
            "Treeview",
            background=fondo,
            foreground=texto,
            fieldbackground=fondo
        )
        estilo.configure(
            "Treeview.Heading",
            background=cabecera,
            foreground=texto
        )


boton_tema = ctk.CTkButton(
    encabezado,
    text="☀ Claro",
    width=90,
    height=30,
    command=alternar_tema
)
boton_tema.grid(row=0, column=1, sticky="e", padx=(8, 0), pady=2)

pestanas = ctk.CTkTabview(ventana)
pestanas.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)

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


def abrir_base_seleccionada():
    global conexion, cursor, ruta_base_activa, ruta_base_nueva_pendiente
    ruta = ruta_db_seleccionada.get().strip()
    if not ruta:
        messagebox.showinfo(
            "Seleccionar base",
            "Elegí primero un archivo SQLite.",
            parent=ventana
        )
        return
    ruta = os.path.abspath(ruta)
    if ruta_base_activa and ruta.lower() == ruta_base_activa.lower():
        messagebox.showinfo(
            "Base ya activa",
            "Esa base ya es la base de trabajo activa.",
            parent=ventana
        )
        return
    compatible, mensaje = validar_base_compatible(ruta)
    if not compatible:
        messagebox.showerror("Base incompatible", mensaje, parent=ventana)
        return
    if not resolver_cambios_antes_de_salir("cambiar de base de datos"):
        return

    conexion_anterior = conexion
    cursor_anterior = cursor
    conexion_nueva = sqlite3.connect(ruta)
    conexion_nueva.execute("PRAGMA foreign_keys = ON")
    conexion = conexion_nueva
    cursor = conexion.cursor()
    try:
        inicializar_db()
    except sqlite3.Error as error:
        conexion.close()
        conexion = conexion_anterior
        cursor = cursor_anterior
        messagebox.showerror(
            "No se pudo abrir la base",
            f"No se pudo preparar la base seleccionada.\n\n{error}",
            parent=ventana
        )
        return
    conexion_anterior.close()
    ruta_base_activa = ruta
    cambios_pendientes.clear()
    ruta_base_nueva_pendiente = None
    refrescar_base_activa()


def salir_de_base_activa():
    global conexion, cursor, ruta_base_activa, ruta_base_nueva_pendiente
    if not resolver_cambios_antes_de_salir("iniciar una red manual vacía"):
        return
    conexion.close()
    conexion = sqlite3.connect(":memory:")
    conexion.execute("PRAGMA foreign_keys = ON")
    cursor = conexion.cursor()
    ruta_base_activa = None
    ruta_base_nueva_pendiente = None
    cambios_pendientes.clear()
    ruta_db_seleccionada.set("")
    inicializar_db()
    refrescar_base_activa()


def guardar_como_nueva_base():
    global ruta_base_nueva_pendiente
    if ruta_base_activa:
        messagebox.showinfo(
            "Modo manual",
            "Para crear una base nueva desde cero, primero salí de la base activa.",
            parent=ventana
        )
        return
    ruta = filedialog.asksaveasfilename(
        title="Guardar infraestructura como nueva base",
        defaultextension=".db",
        filetypes=[("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
    )
    if not ruta:
        return
    ruta = os.path.abspath(ruta)
    if os.path.exists(ruta):
        messagebox.showwarning(
            "El archivo ya existe",
            "Para proteger los datos existentes, elegí un nombre nuevo.",
            parent=ventana
        )
        return
    ruta_base_nueva_pendiente = ruta
    actualizar_estado_cambios()


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
            "Importación preparada",
            "La carga quedó pendiente de aplicación.\n\n"
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

ctk.CTkButton(
    frame_importacion,
    text="Abrir selección como base activa",
    command=lambda: abrir_base_seleccionada(),
    height=28
).grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)

ctk.CTkButton(
    frame_importacion,
    text="Salir de la base de datos",
    command=lambda: salir_de_base_activa(),
    height=28
).grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)

ctk.CTkButton(
    frame_importacion,
    text="Guardar manual como nueva base",
    command=lambda: guardar_como_nueva_base(),
    height=28
).grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)

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

pie_cambios = ctk.CTkFrame(central, fg_color="transparent")
pie_cambios.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 12))
pie_cambios.grid_columnconfigure(0, weight=1)

etiqueta_cambios = ctk.CTkLabel(
    pie_cambios,
    text="Sin cambios pendientes",
    anchor="w",
    text_color="#9FA8B3"
)
etiqueta_cambios.grid(row=0, column=0, sticky="w", padx=5)

boton_descartar = ctk.CTkButton(
    pie_cambios,
    text="Descartar cambios",
    width=145,
    fg_color="#555555",
    hover_color="#414141",
    command=lambda: descartar_cambios()
)
boton_descartar.grid(row=0, column=1, padx=4)

boton_aplicar = ctk.CTkButton(
    pie_cambios,
    text="Aplicar cambios",
    width=145,
    command=lambda: aplicar_cambios()
)
boton_aplicar.grid(row=0, column=2, padx=(4, 0))


def resumen_cambios_pendientes():
    resumen = list(cambios_pendientes)
    if ruta_base_nueva_pendiente:
        resumen.append(
            f"Crear una nueva base SQLite en: {ruta_base_nueva_pendiente}"
        )
    return resumen


def actualizar_estado_cambios():
    resumen = resumen_cambios_pendientes()
    etiqueta_cambios.configure(
        text=(f"{len(resumen)} cambio(s) pendiente(s)" if resumen
              else "Sin cambios pendientes")
    )
    estado = "normal" if resumen else "disabled"
    boton_aplicar.configure(state=estado)
    boton_descartar.configure(state=estado)


def refrescar_base_activa():
    nombre = (
        os.path.basename(ruta_base_activa)
        if ruta_base_activa else "Modo manual (sin guardar)"
    )
    etiqueta_base_activa.configure(text=f"Base de datos: {nombre}")
    recargar_arbol()
    if not obtener_redes():
        mostrar_inicio_vacio()
    else:
        titulo_central.configure(text="Seleccioná una red o dispositivo")
        limpiar_contenido()
        ctk.CTkLabel(
            contenido,
            text="Seleccioná un elemento del árbol para ver su información.",
            font=ctk.CTkFont(size=15)
        ).pack(anchor="w", padx=12, pady=12)
    actualizar_estado_cambios()


def descartar_cambios():
    global ruta_base_nueva_pendiente
    if not resumen_cambios_pendientes():
        return
    if not messagebox.askyesno(
        "Descartar cambios",
        "Se descartarán todas las modificaciones pendientes. ¿Continuar?",
        parent=ventana
    ):
        return
    conexion.rollback()
    cambios_pendientes.clear()
    ruta_base_nueva_pendiente = None
    refrescar_base_activa()


def aplicar_cambios(pedir_confirmacion=True):
    global conexion, cursor, ruta_base_activa, ruta_base_nueva_pendiente
    resumen = resumen_cambios_pendientes()
    if not resumen:
        return True
    if not ruta_base_activa and not ruta_base_nueva_pendiente:
        messagebox.showwarning(
            "Guardar como nueva base",
            "Estás en modo manual. Elegí dónde guardar la nueva base antes de aplicar los cambios.",
            parent=ventana
        )
        return False

    detalle = "Se aplicarán estos cambios:\n\n" + "\n".join(
        f"• {cambio}" for cambio in resumen
    )
    if pedir_confirmacion and not messagebox.askyesno(
        "Confirmar cambios",
        detalle + "\n\n¿Deseás guardar todo ahora?",
        parent=ventana
    ):
        return False

    try:
        if ruta_base_nueva_pendiente:
            destino = ruta_base_nueva_pendiente
            if os.path.exists(destino):
                messagebox.showerror(
                    "El archivo ya existe",
                    "Elegí un nombre que no esté en uso para preservar las bases existentes.",
                    parent=ventana
                )
                return False
            conexion.commit()
            descriptor = os.open(
                destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
            os.close(descriptor)
            db_destino = None
            try:
                db_destino = sqlite3.connect(destino)
                conexion.backup(db_destino)
                db_destino.execute("PRAGMA foreign_keys = ON")
            except Exception:
                if db_destino is not None:
                    db_destino.close()
                try:
                    os.remove(destino)
                except OSError:
                    pass
                raise
            conexion.close()
            conexion = db_destino
            cursor = conexion.cursor()
            ruta_base_activa = os.path.abspath(destino)
            ruta_base_nueva_pendiente = None
        else:
            conexion.commit()
        cambios_pendientes.clear()
        refrescar_base_activa()
        return True
    except (sqlite3.Error, OSError) as error:
        messagebox.showerror(
            "No se pudieron aplicar los cambios",
            f"La base conserva los cambios pendientes para volver a intentarlo.\n\n{error}",
            parent=ventana
        )
        return False


def resolver_cambios_antes_de_salir(motivo):
    global ruta_base_nueva_pendiente
    if not resumen_cambios_pendientes():
        return True
    decision = messagebox.askyesnocancel(
        "Cambios sin aplicar",
        f"Hay cambios pendientes antes de {motivo}.\n\n"
        "Sí: revisar y aplicar.\nNo: descartar.\nCancelar: continuar trabajando.",
        parent=ventana
    )
    if decision is None:
        return False
    if decision:
        return aplicar_cambios()
    if messagebox.askyesno(
        "Confirmar descarte",
        "¿Descartar los cambios pendientes y continuar?",
        parent=ventana
    ):
        conexion.rollback()
        cambios_pendientes.clear()
        ruta_base_nueva_pendiente = None
        actualizar_estado_cambios()
        return True
    return False


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


def mostrar_inicio_vacio():
    titulo_central.configure(text="Modo manual vacío")
    limpiar_contenido()
    ctk.CTkLabel(
        contenido,
        text="No hay redes cargadas. Creá una red principal para comenzar.",
        font=ctk.CTkFont(size=15),
        wraplength=650,
        justify="left"
    ).pack(anchor="w", padx=12, pady=(16, 8))
    ctk.CTkButton(
        contenido,
        text="＋ Crear red principal",
        command=lambda: formulario_subred(None),
        width=210
    ).pack(anchor="w", padx=12, pady=8)


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
            red_id, nombre, descripcion, padre, cidr = red
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

def calcular_datos_planificacion(cidr):
    red = ipaddress.IPv4Network(cidr.strip(), strict=False)
    if red.prefixlen <= 30:
        primera = red.network_address + 1
        ultima = red.broadcast_address - 1
    elif red.prefixlen == 31:
        primera, ultima = red.network_address, red.broadcast_address
    else:
        primera = ultima = red.network_address
    return {
        "cidr": red.with_prefixlen,
        "red": str(red.network_address),
        "mascara": str(red.netmask),
        "primera": str(primera),
        "ultima": str(ultima),
        "broadcast": str(red.broadcast_address),
        "rango": f"{primera} – {ultima}",
    }


def mostrar_red(red_id):
    red = obtener_red(red_id)

    if not red:
        mostrar_mensaje("No se encontró la red seleccionada.")
        return

    _, nombre, descripcion, parent_id, cidr = red

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

    ctk.CTkLabel(
        contenido,
        text="Planificación IPv4",
        font=ctk.CTkFont(size=17, weight="bold")
    ).pack(anchor="w", padx=10, pady=(18, 6))

    ctk.CTkLabel(
        contenido,
        text="IPv4/CIDR (por ejemplo, 192.168.1.0/24)",
        anchor="w"
    ).pack(anchor="w", padx=10)
    entrada_cidr = ctk.CTkEntry(
        contenido,
        placeholder_text="Dirección IPv4/prefijo",
        width=260
    )
    entrada_cidr.pack(anchor="w", padx=10, pady=(3, 7))
    entrada_cidr.insert(0, cidr or "")

    resultado_plan = ctk.CTkLabel(
        contenido,
        text="Ingresá una dirección IPv4 con prefijo CIDR.",
        anchor="w",
        justify="left"
    )
    resultado_plan.pack(anchor="w", padx=10, pady=4)

    def actualizar_vista_plan(event=None):
        try:
            datos = calcular_datos_planificacion(entrada_cidr.get())
            resultado_plan.configure(
                text=(
                    f"Nombre de red / dirección de red: {datos['red']}\n"
                    f"Máscara: {datos['mascara']}\n"
                    f"Primera IP asignable: {datos['primera']}\n"
                    f"Última IP asignable: {datos['ultima']}\n"
                    f"Broadcast: {datos['broadcast']}\n"
                    f"Rango asignable: {datos['rango']}"
                )
            )
        except (ValueError, ipaddress.AddressValueError):
            resultado_plan.configure(
                text="CIDR inválido. Usá una IPv4, por ejemplo 10.0.0.0/24."
            )

    def guardar_plan():
        try:
            datos = calcular_datos_planificacion(entrada_cidr.get())
        except ValueError:
            messagebox.showwarning(
                "CIDR inválido",
                "Ingresá una dirección IPv4 válida con prefijo CIDR.",
                parent=ventana
            )
            return
        actualizar_plan_red(red_id, datos["cidr"])
        mostrar_red(red_id)

    entrada_cidr.bind("<KeyRelease>", actualizar_vista_plan)
    actualizar_vista_plan()
    ctk.CTkButton(
        contenido,
        text="Guardar planificación",
        width=185,
        command=guardar_plan
    ).pack(anchor="w", padx=10, pady=(3, 8))

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
    es_principal = parent_id is None
    dialogo.title("Crear red principal" if es_principal else "Crear subred")
    dialogo.geometry("400x260")
    dialogo.transient(ventana)
    dialogo.grab_set()

    ctk.CTkLabel(
        dialogo,
        text="Nueva red principal" if es_principal else "Nueva subred",
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=(20, 12))

    entrada_nombre = ctk.CTkEntry(
        dialogo,
        placeholder_text="Nombre de la red" if es_principal else "Nombre de la subred",
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
        text="Crear red principal" if es_principal else "Crear subred",
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
actualizar_estado_cambios()


def cerrar_aplicacion():
    if not resolver_cambios_antes_de_salir("cerrar la aplicación"):
        return
    conexion.close()
    ventana.destroy()


ventana.protocol("WM_DELETE_WINDOW", cerrar_aplicacion)
ventana.mainloop()
