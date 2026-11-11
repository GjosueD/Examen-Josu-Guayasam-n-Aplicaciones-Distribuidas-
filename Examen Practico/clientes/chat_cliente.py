import os
import socket
import threading

# Dirección del servidor. Como el contenedor publica el puerto 5000 en la
# computadora anfitriona, los clientes se conectan a 127.0.0.1:5000.
# Se puede cambiar con variables de entorno CHAT_HOST / CHAT_PORT.
HOST = os.environ.get("CHAT_HOST", "127.0.0.1")
PORT = int(os.environ.get("CHAT_PORT", "5000"))
CODIFICACION = "utf-8"

# Activa los códigos de escape ANSI en la consola de Windows (para poder
# borrar la línea del prompt al recibir mensajes). En Linux/Mac no hace nada.
os.system("")


def iniciar_cliente(nombre):
    """Ejecuta un cliente de chat con la identidad predeterminada """
    prompt = f"[{nombre}]> "
    candado_pantalla = threading.Lock()   # evita que dos hilos impriman a la vez, se hace el uso del lock 
    saliendo = threading.Event()          # indica que el usuario pidió salir

    def mostrar(texto):
        """Imprime un mensaje recibido sin romper lo que el usuario escribe.

        "Este comando \\r\\033[K "
        "borra la línea del prompt, se imprime el mensaje y se
        vuelve a dibujar el prompt debajo.
        """
        with candado_pantalla:
            print(f"\r\033[K{texto}\n{prompt}", end="", flush=True)

    def enviar(texto):
        """Envía una línea de texto al servidor."""
        cliente.sendall((texto + "\n").encode(CODIFICACION))

    #Conexión al servidor
    print(f"=== {nombre} ===")
    print(f"Conectando al servidor {HOST}:{PORT} ...")
    try:
        cliente = socket.create_connection((HOST, PORT), timeout=5)
        cliente.settimeout(None)  # una vez conectado, lecturas sin límite de tiempo
    except OSError as error:
        print(f"No se pudo conectar al servidor: {error}")
        print("¿Está corriendo el contenedor? -> docker compose up -d --build")
        return

    # Canal de lectura por líneas sobre el socket.
    canal = cliente.makefile("r", encoding=CODIFICACION, newline="\n")

    # Identificar a los clientes
    try:
        enviar(nombre)
        respuesta = canal.readline().strip()
    except OSError as error:
        print(f"Error durante la identificación: {error}")
        cliente.close()
        return

    if respuesta != "OK":
        motivo = respuesta.removeprefix("ERROR:") or "el servidor cerró la conexión"
        print(f"Conexión rechazada: {motivo}")
        cliente.close()
        return

    print("Conectado. Escriba sus mensajes y presione Enter. /salir para terminar.\n")


    def recibir_mensajes():
        """Hilo que escucha al servidor y muestra cada mensaje que llega."""
        try:
            for linea in canal:
                mostrar(linea.rstrip("\r\n"))
        except (OSError, UnicodeDecodeError):
            pass
        # Si se llega aquí sin que el usuario haya escrito /salir,
        # significa que el servidor cerró la conexión.
        if not saliendo.is_set():
            with candado_pantalla:
                print("\r\033[KConexión con el servidor finalizada.", flush=True)
            try:
                cliente.close()
            except OSError:
                pass
            # Termina el programa aunque el hilo principal esté esperando input().
            os._exit(0)

    threading.Thread(target=recibir_mensajes, daemon=True).start()

    # --------------------------------------------- hilo principal: enviar texto
    try:
        while True:
            with candado_pantalla:
                print(prompt, end="", flush=True)
            mensaje = input()
            if mensaje == "/salir":
                break
            if not mensaje.strip():
                continue  # no se envían mensajes vacíos
            enviar(mensaje)
    except (EOFError, KeyboardInterrupt, OSError):
        pass
    finally:
        # Desconexión ordenada: se avisa al servidor y se cierra el socket.
        saliendo.set()
        try:
            enviar("/salir")
            cliente.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        cliente.close()
        print(f"\n{nombre} desconectado.")

