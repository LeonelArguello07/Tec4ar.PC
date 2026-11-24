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

## Funcionalidades actuales

- Árbol jerárquico de **redes, subredes y dispositivos**, con estado indicado por color (Conectado, Desconectado, Mantenimiento).
- Alta, edición, renombrado y eliminación de redes, subredes y dispositivos.
- Ficha de cada dispositivo: nombre, tipo, IP, MAC, estado, fabricante, modelo, ubicación, sistema operativo y descripción.
- Eliminación en cascada: al borrar una red se borran sus subredes y dispositivos.
- **Importación desde otra base SQLite**:
  - Valida que la base tenga las tablas y columnas requeridas.
  - Incorpora las redes/subredes necesarias y los dispositivos.
  - Omite dispositivos duplicados (misma red, nombre e IP).
  - Es transaccional: si algo falla, se revierte todo.
  - No modifica el archivo de origen.
- Carga automática de datos de ejemplo si la base está vacía.
- Migración automática de bases creadas con versiones anteriores (columna `parent_id`).

## Tecnologías

- Python 3
- SQLite (`sqlite3`)
- Tkinter y [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) para la interfaz

## Requisitos e instalación

```bash
pip install customtkinter
```

Tkinter y sqlite3 vienen incluidos con la instalación estándar de Python.

## Uso

```bash
python Testgpt_sin_carga_archivos.py
```

Al iniciar, la aplicación crea (si no existe) la base `Ejemplo.db` en el directorio de ejecución.

1. Seleccioná una red o subred en el panel izquierdo.
2. Usá **＋ Agregar** para crear una subred o añadir un dispositivo.
3. Seleccioná un dispositivo y presioná **Editar características** para modificarlo.
4. Usá **✎ Renombrar** o **Eliminar** según necesites.
5. Para importar, elegí un archivo `.db` con **Examinar...** y luego **Cargar dispositivos desde SQLite**.

## Modelo de datos

```
redes (id, nombre, descripcion, parent_id → redes.id)
dispositivos (id, red_id → redes.id, nombre, tipo, ip, mac, estado,
              fabricante, modelo, ubicacion, sistema, descripcion)
```

- Una red puede tener muchas subredes (relación recursiva mediante `parent_id`).
- Una red/subred tiene muchos dispositivos y cada dispositivo pertenece a una sola red.

## Próximos pasos

Según el diseño del proyecto, queda pendiente:

- [ ] **Historial** de eventos por dispositivo (cambios, traslados, reparaciones, reemplazos).
- [ ] Datos de direccionamiento de subredes: rango de IP, máscara, gateway y broadcast.
- [ ] Validación de IP dentro del rango de la subred y detección de duplicados.
- [ ] Tabla de **laboratorios/espacios** con código de red.
- [ ] Copias de seguridad de la base y manual de uso.

## Equipo

| Integrante | Rol |
|---|---|
| Leonel Argüello | Desarrollador principal |
| Braian Salto | Desarrollador secundario |

## Destinatarios

Encargados de informática y administradores de red de escuelas técnicas y secundarias con laboratorios y redes sin documentar.