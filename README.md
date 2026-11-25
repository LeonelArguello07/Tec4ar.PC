# TEC4AR – Administrador de infraestructura

Sistema de escritorio para documentar y gestionar los equipos informáticos, las redes y subredes y los espacios de trabajo de una institución escolar.

## Problemática

Las redes informáticas de la escuela no están documentadas. No existe un registro centralizado que indique qué equipos hay, dónde están, qué IP fija tiene cada uno ni a qué subred pertenecen. Esto provoca:

- **Conflictos de IP**: sin registro de asignaciones es fácil repetir una dirección.
- **Diagnóstico lento**: ante una falla no se sabe qué equipo es ni dónde está.
- **Dependencia de personas**: si quien conoce la red se va, el conocimiento se pierde.
- **Sin trazabilidad**: no hay registro de cambios, traslados ni reparaciones.
- **Inventario desactualizado**: dificulta planificar mantenimiento, ampliaciones o compras.

## Solución

Un sistema liviano que centraliza la información de equipos (switches, computadoras, servidores), redes/subredes y laboratorios, pensado para el contexto escolar, a diferencia de las herramientas empresariales, que suelen ser complejas y costosas.

## Funcionalidades actuales — V0.5

- Árbol jerárquico de **redes, subredes y dispositivos**, con estado indicado por color (Conectado, Desconectado y Mantenimiento).
- Alta, edición, renombrado y eliminación de redes, subredes y dispositivos, con eliminación en cascada de los elementos dependientes.
- Ficha de cada dispositivo: nombre, tipo, IP, MAC, estado, fabricante, modelo, ubicación, sistema operativo y descripción.
- **Planificación IPv4/CIDR por red o subred**: al ingresar una dirección con prefijo (por ejemplo, `192.168.1.77/24`) muestra la dirección de red, máscara, primera y última IP asignables, broadcast y rango. La planificación se guarda en la columna `cidr`.
- **Cambios pendientes**: las operaciones de alta, edición, renombrado, eliminación, importación y planificación quedan en espera. **Aplicar cambios** presenta el detalle y pide confirmación; **Descartar cambios** revierte las operaciones. Al cerrar o cambiar de base, se puede aplicar, descartar o cancelar.
- **Importación desde otra base SQLite**: valida el esquema mínimo, incorpora las redes/subredes y dispositivos, omite dispositivos duplicados (misma red, nombre e IP) y no modifica el archivo de origen. La importación también queda pendiente hasta aplicar los cambios.
- **Cambio de base activa**: se puede abrir la base seleccionada como espacio de trabajo o importar su contenido a la base actual.
- **Modo manual**: permite salir de la base activa y empezar con una estructura vacía en memoria, crear una red principal y guardarla como una base SQLite nueva.
- Logo TEC4AR y botón para alternar entre modo claro y oscuro.
- Carga automática de datos de ejemplo si la base inicial está vacía.
- Migración de bases anteriores: agrega las columnas que falten para descripción, jerarquía (`parent_id`), planificación (`cidr`) y atributos opcionales de dispositivos.

## Tecnologías

- Python 3
- SQLite (`sqlite3`) e `ipaddress` de la biblioteca estándar
- Tkinter y [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) para la interfaz

## Requisitos e instalación

```bash
python -m pip install customtkinter
```

Tkinter y sqlite3 vienen incluidos con la instalación estándar de Python.

## Uso

Desde la carpeta del repositorio:

```powershell
cd ByteTracker
python ByteTrackerV0.5.py
```

La aplicación utiliza `Ejemplo.db` en el directorio desde el que se inicia. Si la base está vacía, carga datos de ejemplo.

1. Seleccioná una red o subred en el panel izquierdo para consultar o editar su información.
2. Usá **＋ Agregar** para crear subredes o añadir dispositivos; para comenzar con una estructura vacía, elegí **Salir de la base de datos** y luego **Crear red principal**.
3. Para planificar una red, ingresá su IPv4/CIDR y pulsá **Guardar planificación**. El cálculo se actualiza mientras escribís.
4. Para importar, elegí un archivo `.db` con **Examinar...** y pulsá **Cargar dispositivos desde SQLite**. Si querés trabajar directamente sobre ese archivo, usá **Abrir selección como base activa**.
5. En modo manual, elegí **Guardar manual como nueva base** para indicar el destino. El archivo se crea cuando confirmás **Aplicar cambios**.
6. Revisá el contador y usá **Aplicar cambios** para confirmar el resumen, o **Descartar cambios** para revertirlos.
7. El botón **☀ Claro / ☾ Oscuro** alterna el tema de la interfaz.

## Modelo de datos

```text
redes (id, nombre, descripcion, parent_id → redes.id, cidr)
dispositivos (id, red_id → redes.id, nombre, tipo, ip, mac, estado,
              fabricante, modelo, ubicacion, sistema, descripcion)
```

- Una red puede tener muchas subredes mediante la relación recursiva `parent_id`.
- Una red o subred puede contener muchos dispositivos; cada dispositivo pertenece a una sola red.
- `cidr` almacena la planificación IPv4 de cada red o subred, por ejemplo `192.168.1.0/24`.

## Compatibilidad SQLite

Al abrir una base existente, TEC4AR conserva sus registros y añade las columnas nuevas que falten. Para importar bases antiguas se requieren las tablas `redes` y `dispositivos` y sus columnas esenciales (`id`, `nombre`, `red_id` en dispositivos). Los campos opcionales ausentes se completan con valores vacíos o predeterminados; las columnas `parent_id` y `cidr`, si están presentes, se conservan al importar.

## Próximos pasos

- [ ] Historial de eventos por dispositivo (cambios, traslados, reparaciones y reemplazos).
- [ ] Configuración de gateway y validación de IPs dentro del rango de la subred.
- [ ] Detección de direcciones IP duplicadas entre dispositivos.
- [ ] Tabla de laboratorios/espacios con código de red.
- [ ] Copias de seguridad de la base y manual de uso.

## Equipo

| Integrante | Rol |
|---|---|
| Leonel Argüello | Desarrollador principal |
| Braian Salto | Desarrollador secundario |

## Destinatarios

Encargados de informática y administradores de red de escuelas técnicas y secundarias con laboratorios y redes sin documentar.