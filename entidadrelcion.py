import sqlite3
import os
import sys

DB = "reservas.db"
RAPIDO = "--rapido" in sys.argv


def pausa():
    if not RAPIDO:
        input("\n   [Enter para continuar]\n")


def paso(n, titulo):
    print("\n" + "=" * 60)
    print(f" PASO {n}: {titulo}")
    print("=" * 60)


def mostrar(cur, sql, params=()):
    cur.execute(sql, params)
    filas = cur.fetchall()
    cols = [d[0] for d in cur.description]
    ancho = [max(len(str(c)), *(len(str(f[i])) for f in filas)) if filas else len(c)
             for i, c in enumerate(cols)]
    print("   " + " | ".join(c.ljust(ancho[i]) for i, c in enumerate(cols)))
    print("   " + "-+-".join("-" * a for a in ancho))
    for f in filas:
        print("   " + " | ".join(str(v).ljust(ancho[i]) for i, v in enumerate(f)))
    return filas


paso(1, "Crear la base de datos")
if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
cur = con.cursor()
print(f"   Base de datos creada: {DB}")
pausa()

paso(2, "Crear las tablas (Usuario, Mesa, Reserva)")
cur.executescript("""
CREATE TABLE Usuario (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          VARCHAR(60)  NOT NULL,
    apellido        VARCHAR(60)  NOT NULL,
    tipo_documento  VARCHAR(10)  NOT NULL,
    documento       VARCHAR(30)  NOT NULL UNIQUE,
    telefono        VARCHAR(20),
    email           VARCHAR(100),
    otro_contacto   VARCHAR(100),
    fecha_registro  DATE DEFAULT (DATE('now'))
);

CREATE TABLE Mesa (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_mesa   INT NOT NULL UNIQUE,
    capacidad     INT NOT NULL,
    ubicacion     VARCHAR(50),
    estado        VARCHAR(15) DEFAULT 'disponible',
    observaciones VARCHAR(150)
);

CREATE TABLE Reserva (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora   DATETIME NOT NULL,
    duracion_min INT DEFAULT 90,
    usuario_id   INT NOT NULL,
    mesa_id      INT NOT NULL,
    comensales   INT NOT NULL,
    estado       VARCHAR(15) DEFAULT 'pendiente',
    comentarios  VARCHAR(200),
    creada_en    DATETIME DEFAULT (DATETIME('now')),
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
    FOREIGN KEY (mesa_id)    REFERENCES Mesa(id)
);
""")
for (nombre,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
    print(f"   Tabla creada: {nombre}")
pausa()

paso(3, "Insertar usuarios")
cur.executemany(
    "INSERT INTO Usuario (nombre, apellido, tipo_documento, documento, telefono, email, otro_contacto) VALUES (?,?,?,?,?,?,?)",
    [
        ("Tomás", "Zabala", "CC", "1000000001", "3001112233", "tom@correo.com", "@tom"),
        ("Laura", "Gómez", "CC", "1000000002", "3012223344", "laura@correo.com", None),
        ("Carlos", "Pérez", "CE", "1000000003", "3023334455", "carlos@correo.com", "WhatsApp"),
    ],
)
mostrar(cur, "SELECT id, nombre, apellido, tipo_documento, documento, telefono FROM Usuario")
pausa()

paso(4, "Insertar mesas")
cur.executemany(
    "INSERT INTO Mesa (numero_mesa, capacidad, ubicacion, observaciones) VALUES (?,?,?,?)",
    [
        (1, 2, "Ventana", None),
        (2, 4, "Terraza", "Con sombrilla"),
        (3, 6, "Salón principal", None),
    ],
)
mostrar(cur, "SELECT * FROM Mesa")
pausa()

paso(5, "Insertar reservas (usan usuario_id y mesa_id = llaves foráneas)")
cur.executemany(
    "INSERT INTO Reserva (fecha_hora, duracion_min, usuario_id, mesa_id, comensales, estado, comentarios) VALUES (?,?,?,?,?,?,?)",
    [
        ("2026-10-25 19:00", 90, 1, 2, 4, "confirmada", "Cumpleaños"),
        ("2026-10-25 20:30", 60, 2, 1, 2, "pendiente", None),
        ("2026-10-26 13:00", 120, 1, 3, 6, "confirmada", "Almuerzo familiar"),
        ("2026-10-27 18:00", 90, 3, 2, 3, "cancelada", "Canceló por lluvia"),
    ],
)
mostrar(cur, "SELECT id, fecha_hora, usuario_id, mesa_id, comensales, estado FROM Reserva")
pausa()

paso(6, "Consulta con JOIN: reservas con nombre del usuario y número de mesa")
mostrar(cur, """
    SELECT r.id AS reserva,
           r.fecha_hora,
           u.nombre || ' ' || u.apellido AS usuario,
           m.numero_mesa AS mesa,
           m.ubicacion,
           r.comensales,
           r.estado
    FROM Reserva r
    JOIN Usuario u ON u.id = r.usuario_id
    JOIN Mesa    m ON m.id = r.mesa_id
    ORDER BY r.fecha_hora
""")
pausa()

paso(7, "Relación 1:N -> cuántas reservas tiene cada usuario")
mostrar(cur, """
    SELECT u.nombre || ' ' || u.apellido AS usuario, COUNT(r.id) AS total_reservas
    FROM Usuario u
    LEFT JOIN Reserva r ON r.usuario_id = u.id
    GROUP BY u.id
""")
pausa()

paso(8, "Probar la integridad: reservar con un usuario que NO existe")
try:
    cur.execute("INSERT INTO Reserva (fecha_hora, usuario_id, mesa_id, comensales) VALUES ('2026-11-01 19:00', 99, 1, 2)")
except sqlite3.IntegrityError as e:
    print(f"   Error esperado (la llave foránea protege los datos): {e}")

con.commit()
con.close()
print(f"\n   Listo. Se guardó todo en el archivo {DB}")