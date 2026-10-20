import sqlite3
from datetime import datetime, timedelta

DB = "reservas.db"
con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
cur = con.cursor()
usuario_actual = None  # (id, nombre, apellido)


def crear_tablas():
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS Usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre VARCHAR(60) NOT NULL,
        apellido VARCHAR(60) NOT NULL,
        tipo_documento VARCHAR(10) NOT NULL,
        documento VARCHAR(30) NOT NULL UNIQUE,
        telefono VARCHAR(20),
        email VARCHAR(100),
        otro_contacto VARCHAR(100),
        fecha_registro DATE DEFAULT (DATE('now'))
    );
    CREATE TABLE IF NOT EXISTS Mesa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_mesa INT NOT NULL UNIQUE,
        capacidad INT NOT NULL,
        ubicacion VARCHAR(50),
        estado VARCHAR(15) DEFAULT 'disponible',
        observaciones VARCHAR(150)
    );
    CREATE TABLE IF NOT EXISTS Reserva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora DATETIME NOT NULL,
        duracion_min INT DEFAULT 90,
        usuario_id INT NOT NULL,
        mesa_id INT NOT NULL,
        comensales INT NOT NULL,
        estado VARCHAR(15) DEFAULT 'confirmada',
        comentarios VARCHAR(200),
        creada_en DATETIME DEFAULT (DATETIME('now')),
        FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
        FOREIGN KEY (mesa_id) REFERENCES Mesa(id)
    );
    """)
    if cur.execute("SELECT COUNT(*) FROM Mesa").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO Mesa (numero_mesa, capacidad, ubicacion, observaciones) VALUES (?,?,?,?)",
            [(1, 2, "Ventana", "nada"), (2, 4, "Terraza", "Con sombrilla"),
             (3, 4, "Salón principal", "nada"), (4, 6, "Salón principal", "Mesa grande")])
    con.commit()


def pedir(texto, obligatorio=True):
    while True:
        v = input(texto).strip()
        if v or not obligatorio:
            return v
        print("  Este dato es obligatorio.")


def pedir_entero(texto, minimo=1):
    while True:
        try:
            n = int(input(texto).strip())
            if n >= minimo:
                return n
        except ValueError:
            pass
        print(f"  Escribe un número entero (mínimo {minimo}).")


def crear_cuenta():
    print("\n--- CREAR CUENTA ---")
    nombre = pedir("Nombre: ")
    apellido = pedir("Apellido: ")
    tipo = pedir("Tipo de documento (CC/TI/CE/PAS): ").upper()
    documento = pedir("Número de documento: ")
    telefono = pedir("Teléfono: ")
    email = pedir("Email: ")
    otro = pedir("Otro contacto (opcional, Enter para omitir): ", False)
    try:
        cur.execute(
            "INSERT INTO Usuario (nombre, apellido, tipo_documento, documento, telefono, email, otro_contacto) "
            "VALUES (?,?,?,?,?,?,?)", (nombre, apellido, tipo, documento, telefono, email, otro or None))
        con.commit()
        print(f"\n✔ Cuenta creada. Ya puedes iniciar sesión con el documento {documento}.")
    except sqlite3.IntegrityError:
        print("\n✘ Ya existe una cuenta con ese documento.")


def iniciar_sesion():
    global usuario_actual
    print("\n--- INICIAR SESIÓN ---")
    documento = pedir("Número de documento: ")
    fila = cur.execute("SELECT id, nombre, apellido FROM Usuario WHERE documento = ?", (documento,)).fetchone()
    if fila:
        usuario_actual = fila
        print(f"\n✔ Bienvenido/a, {fila[1]} {fila[2]}.")
    else:
        print("\n✘ No existe una cuenta con ese documento. Usa la opción 1 para crearla.")


def llenar_formulario():
    if not usuario_actual:
        print("\n✘ Primero debes iniciar sesión (opción 2).")
        return
    print("\n--- FORMULARIO DE RESERVA ---")
    print("Mesas del restaurante:")
    for n, cap, ubi, obs in cur.execute(
            "SELECT numero_mesa, capacidad, ubicacion, observaciones FROM Mesa WHERE estado='disponible' ORDER BY numero_mesa"):
        print(f"  Mesa {n} | capacidad {cap} | {ubi} | {obs}")
    while True:
        try:
            inicio = datetime.strptime(pedir("Fecha y hora (AAAA-MM-DD HH:MM): "), "%Y-%m-%d %H:%M")
            if inicio < datetime.now():
                print("  La fecha debe ser futura.")
                continue
            break
        except ValueError:
            print("  Formato inválido. Ejemplo: 2026-10-25 19:00")
    duracion = pedir_entero("Duración en minutos (ej. 90): ", 30)
    comensales = pedir_entero("Número de comensales: ")
    while True:
        numero = pedir_entero("Número de mesa: ")
        mesa = cur.execute("SELECT id, capacidad FROM Mesa WHERE numero_mesa=? AND estado='disponible'", (numero,)).fetchone()
        if not mesa:
            print("  Esa mesa no existe.")
        elif comensales > mesa[1]:
            print(f"  La mesa {numero} solo tiene capacidad para {mesa[1]}.")
        else:
            break
    fin = inicio + timedelta(minutes=duracion)
    for f, d in cur.execute("SELECT fecha_hora, duracion_min FROM Reserva WHERE mesa_id=? AND estado!='cancelada'", (mesa[0],)):
        i2 = datetime.strptime(f, "%Y-%m-%d %H:%M")
        if inicio < i2 + timedelta(minutes=d) and i2 < fin:
            print("\n✘ Esa mesa ya está reservada en ese horario. Prueba otra mesa u otra hora.")
            return
    comentarios = pedir("Comentarios (opcional): ", False)
    cur.execute(
        "INSERT INTO Reserva (fecha_hora, duracion_min, usuario_id, mesa_id, comensales, comentarios) VALUES (?,?,?,?,?,?)",
        (inicio.strftime("%Y-%m-%d %H:%M"), duracion, usuario_actual[0], mesa[0], comensales, comentarios or None))
    con.commit()
    print("\n✔ Reserva creada correctamente.")


def ver_reservas():
    if not usuario_actual:
        print("\n✘ Primero debes iniciar sesión (opción 2).")
        return
    print("\n--- MIS RESERVAS ---")
    filas = cur.execute("""
        SELECT r.id, r.fecha_hora, m.numero_mesa, m.ubicacion, r.comensales, r.duracion_min, r.estado, r.comentarios
        FROM Reserva r JOIN Mesa m ON m.id = r.mesa_id
        WHERE r.usuario_id = ? ORDER BY r.fecha_hora""", (usuario_actual[0],)).fetchall()
    if not filas:
        print("Aún no tienes reservas.")
    for rid, fh, nm, ub, com, dur, est, cm in filas:
        print(f"Reserva #{rid}: {fh} | Mesa {nm} ({ub}) | {com} personas | {dur} min | {est}")
        if cm:
            print(f"   Comentarios: {cm}")


def cerrar_sesion():
    global usuario_actual
    if usuario_actual:
        print(f"\n✔ Sesión de {usuario_actual[1]} cerrada.")
        usuario_actual = None
    else:
        print("\nNo hay ninguna sesión abierta.")


def menu():
    crear_tablas()
    while True:
        sesion = f"{usuario_actual[1]} {usuario_actual[2]}" if usuario_actual else "sin sesión"
        print("\n" + "=" * 40)
        print(f"  SISTEMA DE RESERVA DE MESAS (Sesión: {sesion})")
        print("=" * 40)
        print("1. Crear Cuenta\n2. Iniciar Sesión\n3. Llenar Formulario de Reserva")
        print("4. Ver Mis Reservas\n5. Cerrar Sesión\n6. Salir")
        op = input("Seleccione una opción (1-6): ").strip()
        if op == "1": crear_cuenta()
        elif op == "2": iniciar_sesion()
        elif op == "3": llenar_formulario()
        elif op == "4": ver_reservas()
        elif op == "5": cerrar_sesion()
        elif op == "6":
            print("\nHasta luego.")
            con.close()
            break
        else:
            print("\n✘ Opción inválida. Elige un número del 1 al 6.")


menu()
