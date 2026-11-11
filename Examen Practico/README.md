# Chat en tiempo real — Python, Sockets, Hilos y Docker

Examen práctico de **Aplicaciones Distribuidas**.

Es una aplicación de chat en tiempo real con **tres participantes**:

| Participante | Dónde se ejecuta | Qué hace |
|---|---|---|
| **SERVIDOR** | Contenedor **Docker** (Docker Compose) | Acepta conexiones, envía sus propios mensajes y reenvía los mensajes entre los clientes |
| **CLIENTE 1  ** | Terminal de VS Code | Envía y recibe mensajes |
| **CLIENTE 2  ** | Otra terminal de VS Code | Envía y recibe mensajes |

Ejemplo de salida:

```
[CLIENTE 1  ]: Hola a todos
[SERVIDOR]: Hola cliente 1
[CLIENTE 2  ]: Buenos días
[CLIENTE 1  ]: ¿Cómo están?
[CLIENTE 2  ]: Todo bien
```

---

## Estructura del proyecto

```
Examen Practico/
├── docker-compose.yml      # Levanta el servidor en Docker y publica el puerto 5000
├── servidor/
│   ├── Dockerfile          # Imagen python:3.12-slim que ejecuta servidor.py
│   └── servidor.py         # Servidor TCP multihilo
├── clientes/
│   ├── chat_cliente.py     # Lógica común de los clientes (conexión + hilos)
│   ├── cliente1.py         # Ejecuta el cliente con la identidad "CLIENTE 1"
│   └── cliente2.py         # Ejecuta el cliente con la identidad "CLIENTE 2"
└── README.md
```

Solo se usa la **librería estándar de Python** (`socket`, `threading`, `os`), así que no hay que instalar dependencias.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y **en ejecución**.
- Python 3.9 o superior en la computadora anfitriona (para los clientes).
- Visual Studio Code

---

## Cómo ejecutar la aplicación

Abra la carpeta `Examen Practico` en VS Code. Se necesitan **3 terminales** 

### 1) Terminal 1 — Iniciar el SERVIDOR en Docker

```bash
docker compose up -d --build
```

Esto construye la imagen, crea el contenedor `chat-servidor` y publica el puerto **5000** del contenedor en el puerto **5000** de la computadora.

Compruebe que está corriendo:

```bash
docker ps
```

Para **ver y escribir** en la consola del servidor, conéctese al contenedor:

```bash
docker attach chat-servidor
```

> Si no se ve el prompt  `[SERVIDOR]>` en la terminal , presione **Enter** una vez.
> Todo lo que escriba aquí se envía a **ambos clientes** como `[SERVIDOR]: ...`.

### 2) Terminal 2 — Iniciar CLIENTE 1

```bash
python clientes/cliente1.py
```

### 3) Terminal 3 — Iniciar CLIENTE 2

```bash
python clientes/cliente2.py
```

> En Windows, si `python` no funciona, use `py clientes/cliente1.py` y `py clientes/cliente2.py`.

¡Listo! Ya puede escribir desde cualquiera de las tres terminales en cualquier momento.

### Detener la aplicación

- En cada cliente escriba `/salir` (o presione `Ctrl + C`).
- En la consola del servidor escriba `/salir` (o presione `Ctrl + C`); el contenedor se detiene.
- Para eliminar el contenedor y la red creados por Docker Compose:

```bash
docker compose down
```

### Alternativa: servidor interactivo en un solo comando

En lugar de `up -d` + `attach`, puede ejecutar el servidor directamente en primer plano:

```bash
docker compose run --rm --service-ports servidor
```

---

## Comandos disponibles

| Dónde | Comando | Acción |
|---|---|---|
| Servidor | *cualquier texto* | Envía `[SERVIDOR]: texto` a ambos clientes |
| Servidor | `/clientes` | Muestra qué clientes están conectados |
| Servidor | `/salir` | Apaga el servidor y avisa a los clientes |
| Cliente | *cualquier texto* | Envía `[CLIENTE N]: texto` al servidor y al otro cliente |
| Cliente | `/salir` | Se desconecta del chat |

---

## Pruebas de funcionamiento 

1. **Iniciar el servidor en Docker:** `docker compose up -d --build` y luego `docker attach chat-servidor`.
   Se ve `=== SERVIDOR DE CHAT === / Escuchando en 0.0.0.0:5000`.
2. **Conectar Cliente 1:** `python clientes/cliente1.py` → el servidor muestra
   `[SERVIDOR]: CLIENTE 1  se ha unido al chat`.
3. **Conectar Cliente 2:** `python clientes/cliente2.py` → el servidor y el Cliente 1 muestran
   `[SERVIDOR]: CLIENTE 2  se ha unido al chat`.
4. **Enviar mensajes:**
   - Desde el servidor escriba `Hola cliente 1` → **ambos** clientes reciben `[SERVIDOR]: Hola cliente 1`.
   - Desde el Cliente 1 escriba `Hola a todos` → el servidor y el Cliente 2 reciben `[CLIENTE 1  ]: Hola a todos`.
   - Desde el Cliente 2 escriba `Buenos días` → el servidor y el Cliente 1 reciben `[CLIENTE 2  ]: Buenos días`.
5. **Sin turnos:** escriba varios mensajes seguidos desde un mismo participante, o desde los tres
   en cualquier orden: todos llegan al instante, nadie tiene que esperar a que el otro responda.

Extra: si se intenta abrir un segundo `cliente1.py` mientras el primero sigue conectado, el
servidor lo rechaza con `CLIENTE 1  ya está conectado` (identificación única de participantes).

---

## Cómo funciona

```
 Computadora host                        Contenedor Docker
┌──────────────────────────────┐   puerto     ┌─────────────────────────────┐
│ Terminal 2: cliente1.py ─────┼──► 5000 ───► │ servidor.py (0.0.0.0:5000)  │
│ Terminal 3: cliente2.py ─────┼──►      ───► │  ├─ hilo aceptador          │
│                              │              │  ├─ hilo por CLIENTE 1      │
│ Terminal 1: docker attach ───┼── teclado ─► │  ├─ hilo por CLIENTE 2      │
└──────────────────────────────┘              │  └─ hilo principal (input)  │
                                              └─────────────────────────────┘
```

### Servidor (`servidor/servidor.py`)

- Crea un socket TCP y escucha en `0.0.0.0:5000` (necesario para que Docker reciba conexiones de fuera del contenedor).
- **Hilo aceptador:** espera conexiones con `accept()` y crea **un hilo por cada cliente**.
- **Hilo de cada cliente:** lee la identidad, la valida y luego lee sus mensajes; cada mensaje se muestra en el servidor y se **difunde** al otro cliente con el formato `[CLIENTE N]: mensaje`.
- **Hilo principal:** lee el teclado del servidor y envía `[SERVIDOR]: mensaje` a todos los clientes.
- Un diccionario `{nombre: socket}` protegido con `threading.Lock` guarda los clientes conectados.

### Clientes (`clientes/`)

- Se conectan a `127.0.0.1:5000` (el puerto publicado por Docker).
- **Hilo receptor:** escucha continuamente al servidor y muestra cada mensaje en cuanto llega.
- **Hilo principal:** lee el teclado y envía los mensajes.
- Al tener recepción y envío en hilos separados, se puede escribir y recibir **al mismo tiempo, sin turnos**.

### Protocolo de comunicación

Texto UTF-8, **un mensaje por línea** (terminado en `\n`):

1. El cliente envía su identidad: `CLIENTE 1` o `CLIENTE 2  `.
2. El servidor responde `OK`, o `ERROR:<motivo>` (identidad inválida o ya conectada).
3. Después, cada línea es un mensaje de chat. `/salir` cierra la conexión.

### Configuración opcional

Variables de entorno (valores por defecto entre paréntesis):

| Variable | Servidor | Clientes |
|---|---|---|
| `CHAT_HOST` | IP donde escucha (`0.0.0.0`) | IP del servidor (`127.0.0.1`) |
| `CHAT_PORT` | Puerto (`5000`) | Puerto (`5000`) |

Ejemplo para conectar un cliente a un servidor en otra computadora de la red (PowerShell):

```powershell
$env:CHAT_HOST="192.168.1.50"; python clientes/cliente1.py
```

---

## Solución de problemas

| Problema | Solución |
|---|---|
| `No se pudo conectar al servidor` | Verifique que Docker Desktop está abierto y que `docker ps` muestra `chat-servidor`. |
| `port is already allocated` | Otro programa usa el puerto 5000. Cierre ese programa o cambie `"5000:5000"` por `"5050:5000"` en `docker-compose.yml` y ejecute los clientes con `CHAT_PORT=5050`. |
| No veo el prompt del servidor tras `docker attach` | Presione **Enter**. Los mensajes anteriores se pueden ver con `docker logs chat-servidor`. |
| `CLIENTE 1 ya está conectado` | Ya hay una terminal ejecutando ese cliente; ciérrela con `/salir`. |

