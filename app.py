import random
from flask import Flask, render_template, request, session, jsonify
from conexion import Conexion


 


class ParImpar:
    """Un número ingresado en el menú Par o impar."""

    def __init__(self, numero):
        self.numero = numero

    @property
    def tipo(self):
        return "par" if self.numero % 2 == 0 else "impar"

    def mensaje(self):
        return f"El número {self.numero} es {self.tipo}"


class TablaMultiplicar:
    """La tabla de multiplicar de un número."""

    def __init__(self, numero, hasta=10):
        self.numero = numero
        self.hasta = hasta

    def lineas(self):
        return [f"{self.numero} x {i} = {self.numero * i}"
                for i in range(1, self.hasta + 1)]


class JuegoSecreto:
    """Una partida del juego de adivinar el número."""

    MINIMO = 1
    MAXIMO = 100

    def __init__(self, secreto=None, intentos=None):
        self.secreto = secreto if secreto is not None else random.randint(self.MINIMO, self.MAXIMO)
        self.intentos = list(intentos or [])

    @property
    def acertado(self):
        return bool(self.intentos) and self.intentos[-1] == self.secreto

    def intentar(self, numero):
        """Registra el intento y devuelve la pista."""
        self.intentos.append(numero)
        if numero < self.secreto:
            return "El número secreto es MAYOR"
        if numero > self.secreto:
            return "El número secreto es MENOR"
        return f"¡Correcto! Lo lograste en {len(self.intentos)} intentos"

    def a_dict(self):
        """Para guardar la partida en la sesión del navegador."""
        return {"secreto": self.secreto, "intentos": self.intentos}


class Partida:
    """Una partida ganada, lista para entrar al ranking."""

    def __init__(self, nombre, intentos):
        self.nombre = (nombre or "").strip()[:60] or "Anónimo"
        self.intentos = list(intentos)

    @property
    def total_intentos(self):
        return len(self.intentos)

    @property
    def numeros_texto(self):
        return ", ".join(map(str, self.intentos))




FECHA = "to_char(fecha, 'YYYY-MM-DD HH24:MI:SS') AS fecha"


class Repositorio:
    """Clase base: todos los repositorios comparten la conexión."""

    def __init__(self, conexion):
        self.conexion = conexion

    def crear_tabla(self):
        raise NotImplementedError


class RepositorioParImpar(Repositorio):
    def crear_tabla(self):
        with self.conexion.abrir() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS par_impar (
                id SERIAL PRIMARY KEY,
                numero INTEGER NOT NULL,
                tipo VARCHAR(5) NOT NULL,
                fecha TIMESTAMP DEFAULT NOW()
            )""")

    def guardar(self, par_impar):
        with self.conexion.abrir() as con:
            con.execute("INSERT INTO par_impar (numero, tipo) VALUES (%s, %s)",
                        (par_impar.numero, par_impar.tipo))

    def listar(self):
        with self.conexion.abrir() as con:
            return con.execute(
                f"SELECT id, numero, tipo, {FECHA} FROM par_impar ORDER BY id DESC"
            ).fetchall()


class RepositorioMultiplicador(Repositorio):
    def crear_tabla(self):
        with self.conexion.abrir() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS multiplicador (
                id SERIAL PRIMARY KEY,
                numero INTEGER NOT NULL,
                fecha TIMESTAMP DEFAULT NOW()
            )""")

    def guardar(self, tabla):
        with self.conexion.abrir() as con:
            con.execute("INSERT INTO multiplicador (numero) VALUES (%s)", (tabla.numero,))


class RepositorioRanking(Repositorio):
    def crear_tabla(self):
        with self.conexion.abrir() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS ranking (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(60) NOT NULL,
                total_intentos INTEGER NOT NULL,
                numeros_intentados TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT NOW()
            )""")

    def guardar(self, partida):
        with self.conexion.abrir() as con:
            con.execute(
                "INSERT INTO ranking (nombre, total_intentos, numeros_intentados) "
                "VALUES (%s, %s, %s)",
                (partida.nombre, partida.total_intentos, partida.numeros_texto))

    def top(self, limite=10):
        with self.conexion.abrir() as con:
            return con.execute(
                "SELECT nombre, total_intentos, numeros_intentados FROM ranking "
                "ORDER BY total_intentos ASC, id ASC LIMIT %s", (limite,)
            ).fetchall()




app = Flask(__name__)
app.secret_key = "cambia-esta-clave"

conexion = Conexion()
repo_par_impar = RepositorioParImpar(conexion)
repo_multiplicador = RepositorioMultiplicador(conexion)
repo_ranking = RepositorioRanking(conexion)


def numero_de(req):
    try:
        return int((req.get_json() or {}).get("numero"))
    except (TypeError, ValueError):
        return None


def juego_actual():
    """Recupera la partida guardada en la sesión, o crea una nueva."""
    datos = session.get("juego")
    juego = JuegoSecreto(**datos) if datos else JuegoSecreto()
    session["juego"] = juego.a_dict()
    return juego


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Menú 1: Par o impar ----------
@app.route("/api/par_impar", methods=["GET", "POST"])
def api_par_impar():
    mensaje = None
    if request.method == "POST":
        n = numero_de(request)
        if n is None:
            return jsonify(error="Ingresa un número entero válido"), 400
        par_impar = ParImpar(n)
        repo_par_impar.guardar(par_impar)
        mensaje = par_impar.mensaje()
    return jsonify(mensaje=mensaje, filas=repo_par_impar.listar())


# ---------- Menú 2: Tabla de multiplicar ----------
@app.route("/api/multiplicador", methods=["POST"])
def api_multiplicador():
    n = numero_de(request)
    if n is None:
        return jsonify(error="Ingresa un número entero válido"), 400
    tabla = TablaMultiplicar(n)
    repo_multiplicador.guardar(tabla)
    return jsonify(tabla=tabla.lineas())


# ---------- Menú 3: Adivinar el número ----------
@app.route("/api/secreto/estado")
def api_secreto_estado():
    juego = juego_actual()
    return jsonify(intentos=juego.intentos, top=repo_ranking.top())


@app.route("/api/secreto/intentar", methods=["POST"])
def api_secreto_intentar():
    n = numero_de(request)
    if n is None:
        return jsonify(error="Ingresa un número válido"), 400
    juego = juego_actual()
    mensaje = juego.intentar(n)
    session["juego"] = juego.a_dict()
    return jsonify(mensaje=mensaje, gano=juego.acertado, intentos=juego.intentos)


@app.route("/api/secreto/guardar", methods=["POST"])
def api_secreto_guardar():
    juego = juego_actual()
    if juego.acertado:
        nombre = (request.get_json() or {}).get("nombre")
        repo_ranking.guardar(Partida(nombre, juego.intentos))
    session.pop("juego", None)
    return jsonify(top=repo_ranking.top())


@app.route("/api/secreto/nuevo", methods=["POST"])
def api_secreto_nuevo():
    session.pop("juego", None)
    juego_actual()
    return jsonify(top=repo_ranking.top())


if __name__ == "__main__":
    for repo in (repo_par_impar, repo_multiplicador, repo_ranking):
        repo.crear_tabla()
    app.run(debug=True)