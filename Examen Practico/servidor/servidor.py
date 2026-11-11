import os
import socket
import threading

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
# 0.0.0.0 = escuchar en todas las interfaces. Es necesario dentro de Docker,
# porque si se usa 127.0.0.1 el puerto publicado no recibiría conexiones
# desde la computadora anfitriona.
HOST = os.environ.get("CHAT_HOST", "0.0.0.0")
PORT = int(os.environ.get("CHAT_PORT", "5000"))
CODIFICACION = "utf-8"

# Identidades permitidas: solo existen dos clientes en el chat.
NOMBRES_VALIDOS = ("CLIENTE 1 ", "CLIENTE 2 ")

# Texto que se muestra como "prompt" en la terminal del servidor.
PROMPT = "[SERVIDOR]> "


# el arreglo de clientes se protege con un candado (Lock) para evitar condiciones de carrera.
clientes = {}
candado_clientes = threading.Lock()

# Candado para que dos hilos no impriman en pantalla al mismo tiempo.
candado_pantalla = threading.Lock()

# Evento que indica que el servidor se está apagando.
apagando = threading.Event()


def mostrar(texto):
    """Imprime un mensaje en la consola del servidor sin romper el prompt.

    "Este comando \\r\\033[K" lleva el cursor al inicio de la línea y la borra; luego se
    imprime el mensaje y se vuelve a dibujar el prompt para seguir escribiendo.
    """
    with candado_pantalla:
        print(f"\r\033[K{texto}\n{PROMPT}", end="", flush=True)


def enviar(conexion, texto):
    """Envía una línea de texto a un socket (agrega el salto de línea)."""
    conexion.sendall((texto + "\n").encode(CODIFICACION))


def difundir(texto, excluir=None):
    """Envía un mensaje a todos los clientes conectados.

    excluir: nombre del cliente que no debe recibirlo 
    """
    # Se copia la lista de destinos dentro del candado y se envía fuera de él,
    # para no bloquear a otros hilos mientras se escribe en la red.
    with candado_clientes:
        destinos = [s for nombre, s in clientes.items() if nombre != excluir]
    for conexion in destinos:
        try:
            enviar(conexion, texto)
        except OSError:
            # Si un cliente se cayó, su propio hilo se encargará de limpiarlo.
            pass


def atender_cliente(conexion, direccion):
    """Hilo dedicado a un cliente: lo identifica y reenvía sus mensajes."""
    canal = conexion.makefile("r", encoding=CODIFICACION, newline="\n")
    nombre = None
    registrado = False
    try:
        # 1) Identificación: la primera línea que envía el cliente es su nombre.
        nombre = canal.readline().strip().upper()

        with candado_clientes:
            if nombre not in NOMBRES_VALIDOS:
                error = f"Identidad no válida. Use {' o '.join(NOMBRES_VALIDOS)}"
            elif nombre in clientes:
                error = f"{nombre} ya está conectado"
            else:
                clientes[nombre] = conexion  # se registra el cliente
                registrado = True
                error = None

        if error:
            enviar(conexion, f"ERROR:{error}")
            mostrar(f"[SERVIDOR]: Conexión rechazada desde {direccion}: {error}")
            return

        # 2) Se confirma la conexión y se avisa a todos.
        enviar(conexion, "OK")
        aviso = f"[SERVIDOR]: {nombre} se ha unido al chat"
        mostrar(f"{aviso} (desde {direccion[0]}:{direccion[1]})")
        difundir(aviso, excluir=nombre)

        # 3) Bucle de recepción: cada línea recibida es un mensaje de chat.
        for linea in canal:
            mensaje = linea.rstrip("\r\n")
            if mensaje == "/salir":
                break
            if not mensaje.strip():
                continue  # se ignoran mensajes vacíos
            texto = f"[{nombre}]: {mensaje}"
            mostrar(texto)                    # se muestra en el servidor
            difundir(texto, excluir=nombre)   # y se reenvía al otro cliente
    except (OSError, UnicodeDecodeError):
        pass  # conexión perdida de forma abrupta
    finally:
        # 4) Limpieza: se elimina al cliente del diccionario y se cierra el socket.
        if registrado:
            with candado_clientes:
                if clientes.get(nombre) is conexion:
                    del clientes[nombre]
        try:
            conexion.close()
        except OSError:
            pass
        if registrado and not apagando.is_set():
            aviso = f"[SERVIDOR]: {nombre} ha salido del chat"
            mostrar(aviso)
            difundir(aviso)


def aceptar_conexiones(servidor):
    """Hilo que espera conexiones nuevas y lanza un hilo por cada cliente."""
    while not apagando.is_set():
        try:
            conexion, direccion = servidor.accept()
        except OSError:
            break  # el socket del servidor fue cerrado
        hilo = threading.Thread(
            target=atender_cliente, args=(conexion, direccion), daemon=True
        )
        hilo.start()


def apagar_servidor(servidor):
    """Avisa a los clientes, cierra todas las conexiones y el socket servidor."""
    apagando.set()
    difundir("[SERVIDOR]: El servidor se ha cerrado")
    with candado_clientes:
        conexiones = list(clientes.values())
        clientes.clear()
    for conexion in conexiones:
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()
    servidor.close()
    print("\nServidor detenido.")


def main():
    # Socket TCP/IPv4
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permite reutilizar el puerto inmediatamente tras reiniciar el servidor.
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(len(NOMBRES_VALIDOS))

    print("=== SERVIDOR DE CHAT ===")
    print(f"Escuchando en {HOST}:{PORT}")
    print("Escriba un mensaje para enviarlo a todos los clientes.")
    print("Comandos: /clientes (ver conectados), /salir (apagar servidor)\n")

    # Hilo que acepta clientes en segundo plano.
    threading.Thread(target=aceptar_conexiones, args=(servidor,), daemon=True).start()

    # Hilo principal: lee el teclado del servidor y envía a todos los clientes.
    try:
        while True:
            with candado_pantalla:
                print(PROMPT, end="", flush=True)
            mensaje = input()
            if mensaje == "/salir":
                break
            if mensaje == "/clientes":
                with candado_clientes:
                    conectados = ", ".join(clientes) or "ninguno"
                with candado_pantalla:
                    print(f"Clientes conectados: {conectados}")
                continue
            if not mensaje.strip():
                continue
            difundir(f"[SERVIDOR]: {mensaje}")
    except EOFError:
       
        print("\n(Sin entrada de teclado: el servidor solo reenviará mensajes)")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    except KeyboardInterrupt:
        pass
    finally:
        apagar_servidor(servidor)


if __name__ == "__main__":
    main()
