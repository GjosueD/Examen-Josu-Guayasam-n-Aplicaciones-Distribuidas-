"""
CLIENTE 1 del chat.

Ejecutar en una terminal de VS Code simpre y cuando este corriendo el servidor en Docker. 
"""

from chat_cliente import iniciar_cliente

if __name__ == "__main__":
    # La identidad "CLIENTE 1 " se envía al servidor al conectarse, así
    # todos los participantes ven sus mensajes como "[CLIENTE 1]: ..."
    iniciar_cliente("CLIENTE 1 ")

