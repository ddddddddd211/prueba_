import psycopg
from psycopg.rows import dict_row

# Cambia estos datos por los tuyos
HOST = "localhost"
PUERTO = 2020
BASE = "menus_db"
USUARIO = "postgres"
CLAVE = "123"


class Conexion:
    """Guarda los datos de conexión y abre conexiones a PostgreSQL."""

    def __init__(self, host=HOST, puerto=PUERTO, base=BASE, usuario=USUARIO, clave=CLAVE):
        self.host = host
        self.puerto = puerto
        self.base = base
        self.usuario = usuario
        self.clave = clave

    def abrir(self):
        """Devuelve una conexión nueva (las filas llegan como diccionarios)."""
        return psycopg.connect(
            host=self.host, port=self.puerto, dbname=self.base,
            user=self.usuario, password=self.clave, row_factory=dict_row,
        )