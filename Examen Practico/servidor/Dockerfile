# Imagen ligera oficial de Python
FROM python:3.12-slim

# Muestra los print() al instante (sin buffer), útil para ver los logs del chat
ENV PYTHONUNBUFFERED=1

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copia el código del servidor (solo usa la librería estándar, no hay dependencias)
COPY servidor.py .

# Puerto en el que escucha el servidor de chat
EXPOSE 5000

# Comando que se ejecuta al iniciar el contenedor
CMD ["python", "servidor.py"]

