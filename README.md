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

## Funcionalidades actuales — V0.6

- Inicio en **modo manual vacío**: la aplicación no abre ni crea una base SQLite al arrancar; mantiene el espacio de trabajo en memoria hasta que se abra una base existente o se guarde una nueva.
- Árbol jerárquico de **redes, subredes y dispositivos**, con estado indicado por color (Conectado, Desconectado y Mantenimiento).
- Alta, edición, renombrado y eliminación de redes, subredes y máquinas, con eliminación en cascada de los elementos dependientes.
- Planificación IPv4/CIDR por red o subred: dirección de red, máscara, primera y última IP asignables, broadcast y rango.
- Pestaña **Inventario** con nombre lógico, tipo, IP, MAC, vista previa de características, fabricante, estado, ubicación y red/subred.
- Acciones de **Detalle**, **Editar** y **Clonar máquina** desde el inventario. La clonación copia la ficha técnica, pero deja IP y MAC vacías y el estado como Desconocido para evitar identidades duplicadas. No clona discos ni instala sistemas operativos.
- El tipo de dispositivo se elige desde un combo con opciones sugeridas (y permite escribir otro tipo); fabricante y características se pueden completar libremente.
- **Cambios pendientes**: altas, ediciones, renombrados, eliminaciones, importaciones y planificaciones se confirman con **Aplicar cambios** o se revierten con **Descartar cambios**. Al cerrar o cambiar de base se ofrece aplicar, descartar o cancelar.
- Importación desde otra base SQLite sin modificar el origen, con omisión de dispositivos duplicados. También se puede abrir la base elegida como espacio de trabajo activo.
- Guardado del modo manual como una nueva base SQLite. El archivo se crea cuando se aplican los cambios.
- Logo TEC4AR y botón para alternar entre modo claro y oscuro.
- Migración de bases anteriores: agrega columnas faltantes para descripción, jerarquía (`parent_id`), planificación (`cidr`) y atributos opcionales de dispositivos.
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
python ByteTrackerV0.6.py
```

La aplicación abre en modo manual y vacío. No crea ni selecciona `Ejemplo.db` automáticamente.

1. Elegí **Crear red principal** y luego agregá subredes y máquinas desde **＋ Agregar**.
2. Abrí **Inventario** para consultar máquinas, editar su ficha o usar **Detalle**.
3. Para una máquina nueva basada en otra, seleccioná la máquina original y pulsá **Clonar máquina**. Se copian tipo, fabricante, modelo, ubicación y características; completá un nombre, una IP y una MAC propios antes de crear el registro.
4. En el formulario, seleccioná el tipo desde el combo o escribí otro. Las características/detalles siguen siendo texto libre.
5. Para usar una base existente, elegí el archivo con **Examinar...** y pulsá **Abrir selección como base activa**. Para incorporar sus registros al espacio actual, elegí **Cargar dispositivos desde SQLite**.
6. Para guardar el trabajo manual, elegí **Guardar manual como nueva base** y después **Aplicar cambios**. Revisá el resumen y confirmá; **Descartar cambios** revierte lo pendiente.
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
| Leonel Argüello | Desarrollador principal / Scrum master|
| Braian Salto | Desarrollador secundario |
| Alejo Miguel | Soporte Tecnico|
| Damian Gonzales | Analista |

## Destinatarios

Encargados de informática y administradores de red de escuelas técnicas y secundarias con laboratorios y redes sin documentar.
