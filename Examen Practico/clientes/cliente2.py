"""
CLIENTE 2 del chat.

Ejecutar en otra terminal de VS Code simpre y cuando este corriendo el servidor en Docker.
"""

from chat_cliente import iniciar_cliente

if __name__ == "__main__":
    # La identidad "CLIENTE 2 " se envía al servidor al conectarse, así
    # todos los participantes ven sus mensajes como "[CLIENTE 2 : Daniel ]: ..."
    iniciar_cliente("CLIENTE 2 ")
    