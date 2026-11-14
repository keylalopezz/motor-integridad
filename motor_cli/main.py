"""Comando ``motor``: usa el Motor de Integridad desde la terminal o desde una automatización.

Comandos:

- ``validar``   valida registros JSON contra un esquema (sin cuenta) o contra tus reglas guardadas.
- ``reglas``    lista tus reglas de integridad activas.
- ``escanear``  ejecuta el escaneo por lotes de todas tus reglas sobre tus bases de datos.
- ``reporte``   exporta las anomalías ya registradas a Excel y/o a un Issue de GitHub.
- ``demo``      ejecuta el motor sobre el conjunto de prueba incluido (sin cuenta ni bases de datos).

Códigos de salida: 0 correcto · 1 registros inválidos o anomalías (con ``--estricto``) · 2 error de uso
o configuración · 3 error de conexión.
"""

import argparse
import getpass
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__

DATOS = Path(__file__).resolve().parent / "datos"

OK, INVALIDO, ERROR_USO, ERROR_CONEXION = 0, 1, 2, 3


class ErrorCLI(Exception):
    """Error que termina el comando con un mensaje y un código de salida."""

    def __init__(self, mensaje: str, codigo: int = ERROR_USO):
        super().__init__(mensaje)
        self.codigo = codigo


# --------------------------------------------------------------------------- utilidades

def _preparar_consola() -> None:
    """Salida en UTF-8 (la consola de Windows usa otra codificación por defecto)."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _cargar_env() -> None:
    """Lee el archivo ``.env`` del directorio actual (SUPABASE_URL, SUPABASE_KEY, ENCRYPTION_KEY...)."""
    try:
        from dotenv import find_dotenv, load_dotenv
        load_dotenv(find_dotenv(usecwd=True))
    except ImportError:
        pass


def _leer_json(ruta: str) -> Any:
    """Lee un archivo JSON (``-`` = entrada estándar) con mensajes de error claros."""
    try:
        if ruta == "-":
            return json.load(sys.stdin)
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        raise ErrorCLI(f"No existe el archivo {ruta}")
    except json.JSONDecodeError as e:
        raise ErrorCLI(f"{ruta} no es un JSON válido (línea {e.lineno}, columna {e.colno}): {e.msg}")


def _registros(datos: Any, ruta: str) -> List[Dict]:
    """Acepta un objeto JSON o una lista de objetos."""
    registros = datos if isinstance(datos, list) else [datos]
    if not registros or not all(isinstance(r, dict) for r in registros):
        raise ErrorCLI(f"{ruta} debe contener un objeto JSON o una lista de objetos.")
    return registros


def _recortar(valor: Any, ancho: int = 48) -> str:
    texto = str(valor).replace("\n", " ")
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def tabla(cabeceras: List[str], filas: List[List[Any]], ultima: int = 90) -> str:
    """Tabla de texto con columnas alineadas (la última columna admite textos más largos)."""
    celdas = [[_recortar(c, ultima if i == len(fila) - 1 else 48) for i, c in enumerate(fila)] for fila in filas]
    anchos = [max([len(h)] + [len(f[i]) for f in celdas]) for i, h in enumerate(cabeceras)]
    linea = lambda valores: "  ".join(v.ljust(anchos[i]) for i, v in enumerate(valores)).rstrip()
    return "\n".join([linea(cabeceras), linea(["-" * a for a in anchos])] + [linea(f) for f in celdas])


def _id(registro: Dict) -> str:
    from modelo.descripcion_anomalias import id_registro
    return id_registro(registro)


# --------------------------------------------------------------------------- sesión

def iniciar_sesion(args) -> str:
    """Autentica con el usuario de la aplicación y devuelve el nombre registrado."""
    from modelo.supabase_client import obtener_config
    if not (obtener_config("SUPABASE_URL") and obtener_config("SUPABASE_KEY")):
        raise ErrorCLI("Faltan SUPABASE_URL y SUPABASE_KEY: defínelos en un archivo .env o como variables de entorno.")
    usuario = args.usuario or os.environ.get("MOTOR_USUARIO")
    if not usuario:
        raise ErrorCLI("Indica tu usuario con --usuario o la variable MOTOR_USUARIO.")
    password = os.environ.get("MOTOR_PASSWORD")
    if not password:
        if not sys.stdin.isatty():
            raise ErrorCLI("Define la variable MOTOR_PASSWORD (la terminal no es interactiva).")
        password = getpass.getpass(f"Contraseña de {usuario}: ")

    from controlador.controlador_auth import ControladorAuth
    exito, mensaje, registrado = ControladorAuth().login(usuario, password)
    if not exito:
        raise ErrorCLI(mensaje, ERROR_CONEXION if "conectar" in mensaje.lower() else ERROR_USO)
    return registrado


def _metrica(usuario: Optional[str], accion: str, detalle: Dict) -> None:
    if usuario:
        from modelo.metricas_uso import MetricasUso
        MetricasUso(usuario).registrar(accion, {**detalle, "origen": "cli"})


# --------------------------------------------------------------------------- salida de anomalías

def _mapa_reglas(reglas: List[Dict]) -> Dict[str, Dict]:
    return {str(r.get("id")): r for r in reglas}


def informar(violaciones: List[Dict], errores: List[str], args, usuario: Optional[str], origen: str,
             reglas: Dict[str, Dict]) -> int:
    """Muestra las anomalías y, si se pidió, genera el Excel y crea el Issue de GitHub."""
    from modelo.descripcion_anomalias import TIPOS, describir, resumen_por_tipo

    if args.json:
        print(json.dumps({"anomalias": violaciones, "errores": errores,
                          "resumen": resumen_por_tipo(violaciones)}, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"\nAnomalías detectadas: {len(violaciones)}")
        print(tabla(["Tipo de regla", "Anomalías"],
                    [[TIPOS[t]["titulo"], n] for t, n in resumen_por_tipo(violaciones).items() if t in TIPOS]))
        if violaciones:
            filas = []
            for n, v in enumerate(violaciones, start=1):
                d = describir(v)
                regla = v.get("reglas") or reglas.get(str(v.get("regla_id")), {}) or {}
                filas.append([n, d["titulo"], d["motores"], regla.get("coleccion_origen", ""), d["id"],
                              d["explicacion"].replace("`", "")])
            print("\n" + tabla(["#", "Tipo", "Motores", "Colección", "Registro", "Explicación"], filas))
        for error in errores:
            print(f"⚠ Regla no evaluada: {error}", file=sys.stderr)

    if args.excel:
        from modelo.integraciones.excel import guardar_excel
        Path(args.excel).parent.mkdir(parents=True, exist_ok=True)
        guardar_excel(args.excel, violaciones, usuario=usuario or "demo", origen=origen, reglas=reglas)
        print(f"\n📊 Reporte Excel guardado en {args.excel}", file=sys.stderr if args.json else sys.stdout)
        _metrica(usuario, "reporte_excel", {"anomalias": len(violaciones)})

    if args.github_issue:
        from modelo.integraciones.github_issues import ErrorGitHub, configuracion_github, publicar_anomalias
        config = configuracion_github(usuario)
        if args.repo:
            token = (config or {}).get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
            config = {"GITHUB_TOKEN": token, "GITHUB_REPO": args.repo} if token else None
        try:
            issue = publicar_anomalias(violaciones, errores, usuario=usuario or "demo", origen=origen,
                                       reglas=reglas, config=config)
        except ErrorGitHub as e:
            raise ErrorCLI(f"GitHub: {e}", ERROR_CONEXION)
        print(f"🐙 Issue #{issue['numero']} creado: {issue['url']}", file=sys.stderr if args.json else sys.stdout)
        _metrica(usuario, "issue_github", {"anomalias": len(violaciones), "issue": issue["numero"]})

    return INVALIDO if args.estricto and (violaciones or errores) else OK


# --------------------------------------------------------------------------- comandos

def cmd_validar(args) -> int:
    registros = _registros(_leer_json(args.archivo), args.archivo)
    resultados = []
    if args.esquema:
        import jsonschema
        esquema = _leer_json(args.esquema)
        try:
            validador = jsonschema.validators.validator_for(esquema)(esquema)
            validador.check_schema(esquema)
        except jsonschema.exceptions.SchemaError as e:
            raise ErrorCLI(f"{args.esquema} no es un JSON Schema válido: {e.message}")
        for registro in registros:
            errores = sorted(validador.iter_errors(registro), key=lambda e: list(e.absolute_path))
            mensajes = [(".".join(map(str, e.absolute_path)) + ": " if e.absolute_path else "") + e.message for e in errores]
            resultados.append((registro, not mensajes, "; ".join(mensajes) or "Cumple el esquema."))
    elif args.motor and args.coleccion:
        usuario = iniciar_sesion(args)
        from controlador.controlador_verificacion import ControladorVerificacion
        controlador = ControladorVerificacion(usuario, origen="cli")
        for registro in registros:
            try:
                valido, mensaje = controlador.validar_insercion(args.motor, args.coleccion, registro)
            except ValueError as e:
                raise ErrorCLI(str(e))
            except Exception as e:
                raise ErrorCLI(f"No se pudo consultar {args.motor}: {type(e).__name__}: {e}", ERROR_CONEXION)
            resultados.append((registro, valido, mensaje))
    else:
        raise ErrorCLI("Indica --esquema ARCHIVO, o --motor y --coleccion para usar tus reglas guardadas.")

    if args.json:
        print(json.dumps([{"registro": _id(r), "valido": v, "mensaje": m} for r, v, m in resultados],
                         ensure_ascii=False, indent=2))
    else:
        for n, (registro, valido, mensaje) in enumerate(resultados, start=1):
            print(f"{'✅' if valido else '❌'} Registro {n} ({_id(registro)}): {'válido' if valido else 'inválido'} — {mensaje}")
        invalidos = sum(1 for _, v, _ in resultados if not v)
        print(f"\n{len(resultados) - invalidos} válido(s), {invalidos} inválido(s).")
    return OK if all(v for _, v, _ in resultados) else INVALIDO


def cmd_reglas(args) -> int:
    usuario = iniciar_sesion(args)
    from controlador.controlador_reglas import ControladorReglas
    reglas = ControladorReglas(usuario).obtener_reglas()
    if args.json:
        print(json.dumps(reglas, ensure_ascii=False, indent=2, default=str))
        return OK
    if not reglas:
        print("No tienes reglas activas. Créalas en la página «Reglas» de la aplicación.")
        return OK
    filas = [[str(r.get("id", ""))[:8], r.get("tipo"), f"{r.get('motor_origen')}.{r.get('coleccion_origen')}.{r.get('campo')}",
              f"{r.get('motor_destino')}.{r.get('coleccion_destino')}.{r.get('campo_destino')}" if r.get("motor_destino") else "-"]
             for r in reglas]
    print(tabla(["ID", "Tipo", "Origen (motor.colección.campo)", "Destino"], filas))
    print(f"\n{len(reglas)} regla(s) activa(s).")
    return OK


def cmd_escanear(args) -> int:
    usuario = iniciar_sesion(args)
    from controlador.controlador_reglas import ControladorReglas
    from controlador.controlador_verificacion import ControladorVerificacion
    reglas = _mapa_reglas(ControladorReglas(usuario).obtener_reglas())
    if not reglas:
        print("No tienes reglas activas que escanear.")
        return OK
    print(f"Escaneando {len(reglas)} regla(s) de {usuario}…", file=sys.stderr)
    violaciones, errores = ControladorVerificacion(usuario, origen="cli").ejecutar_verificacion_batch()
    return informar(violaciones, errores, args, usuario, "CLI · escaneo por lotes", reglas)


def cmd_reporte(args) -> int:
    usuario = iniciar_sesion(args)
    from controlador.controlador_reporte import ControladorReporte
    violaciones = ControladorReporte(usuario).obtener_violaciones()
    return informar(violaciones, [], args, usuario, "CLI · anomalías registradas", {})


class _ReglasFijas:
    """Fuente de reglas en memoria para ``motor demo``."""

    def __init__(self, reglas: List[Dict]):
        self.reglas = reglas

    def obtener_reglas(self, filtros: Optional[Dict] = None) -> List[Dict]:
        return list(self.reglas)


class _AuditoriaNula:
    """La demo no guarda violaciones en Supabase."""

    def limpiar_regla(self, regla_id: str) -> None:
        pass

    def registrar_violaciones(self, violaciones: List[Dict]) -> List[Dict]:
        return violaciones


def ejecutar_demo(ruta_datos: Path, ruta_reglas: Path):
    """Ejecuta el escaneo por lotes sobre datos y reglas en archivos JSON; devuelve (violaciones, errores, reglas)."""
    from modelo.adaptadores.memoria_adapter import cargar_motores
    from modelo.verificador import VerificadorBatch
    try:
        motores = cargar_motores(str(ruta_datos))
    except FileNotFoundError:
        raise ErrorCLI(f"No existe el archivo {ruta_datos}")
    reglas = _registros(_leer_json(str(ruta_reglas)), str(ruta_reglas))

    def fabrica(motor: str, _usuario: str):
        if motor not in motores:
            raise ValueError(f"El conjunto de datos no tiene el motor {motor}")
        return motores[motor]

    verificador = VerificadorBatch("demo", motor_reglas=_ReglasFijas(reglas), auditoria=_AuditoriaNula(),
                                   fabrica_adaptadores=fabrica)
    return verificador.ejecutar_verificacion(), verificador.errores, _mapa_reglas(reglas)


def cmd_demo(args) -> int:
    if not args.json:
        print("Conjunto de prueba: MongoDB (usuarios, pedidos), Redis (usuarios) y Cassandra (pagos).")
    violaciones, errores, reglas = ejecutar_demo(Path(args.datos), Path(args.reglas))
    if not args.json:
        print(f"Reglas evaluadas: {len(reglas)}")
    return informar(violaciones, errores, args, None, "CLI · demo con el conjunto de prueba", reglas)


# --------------------------------------------------------------------------- argumentos

EJEMPLOS = """ejemplos:
  motor demo                                         escaneo del conjunto de prueba (sin cuenta)
  motor demo --excel reporte.xlsx                    además genera el reporte Excel
  motor validar ejemplos/registro_invalido.json --esquema ejemplos/esquema_usuario.json
  motor validar registro.json --motor mongodb --coleccion usuarios --usuario ana
  motor reglas --usuario ana
  motor escanear --usuario ana --excel reporte.xlsx --github-issue
  motor reporte --usuario ana --excel anomalias.xlsx

Los comandos con cuenta leen SUPABASE_URL, SUPABASE_KEY y ENCRYPTION_KEY del archivo .env y la
contraseña de MOTOR_PASSWORD (o la piden en la terminal). Más ayuda: motor <comando> --help"""


def crear_parser() -> argparse.ArgumentParser:
    """Define los comandos y opciones de la CLI."""
    formato = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        prog="motor", formatter_class=formato, epilog=EJEMPLOS,
        description="Motor de Integridad Multibase NoSQL: valida y escanea reglas de esquema, unicidad, "
                    "integridad referencial y consistencia sobre MongoDB, Redis y Cassandra.")
    parser.add_argument("--version", action="version", version=f"motor {__version__}")
    sub = parser.add_subparsers(dest="comando", metavar="COMANDO", title="comandos")

    cuenta = argparse.ArgumentParser(add_help=False)
    cuenta.add_argument("--usuario", "-u", help="usuario de la aplicación (o variable MOTOR_USUARIO)")

    json_ = argparse.ArgumentParser(add_help=False)
    json_.add_argument("--json", action="store_true", help="salida en formato JSON (para scripts)")

    salidas = argparse.ArgumentParser(add_help=False)
    salidas.add_argument("--excel", metavar="ARCHIVO.xlsx", help="guarda el reporte de anomalías en Excel (Office)")
    salidas.add_argument("--github-issue", action="store_true", help="publica las anomalías como un Issue de GitHub")
    salidas.add_argument("--repo", metavar="PROPIETARIO/REPO", help="repositorio del Issue (por defecto, el configurado)")
    salidas.add_argument("--estricto", action="store_true", help="termina con código 1 si hay anomalías (útil en CI)")

    p = sub.add_parser("validar", parents=[cuenta, json_], formatter_class=formato,
                       help="valida registros JSON antes de escribirlos",
                       description="Valida uno o varios registros (objeto JSON o lista) contra un JSON Schema en "
                                   "archivo, o contra tus reglas de esquema y unicidad guardadas para una colección.",
                       epilog="ejemplos:\n  motor validar ejemplos/registro_valido.json --esquema ejemplos/esquema_usuario.json\n"
                              "  motor validar ejemplos/registros_lote.json --esquema ejemplos/esquema_usuario.json\n"
                              "  motor validar registro.json --motor mongodb --coleccion usuarios --usuario ana")
    p.add_argument("archivo", help="archivo JSON con el registro o la lista de registros (- = entrada estándar)")
    p.add_argument("--esquema", "-e", metavar="ARCHIVO", help="JSON Schema a aplicar (no necesita cuenta)")
    p.add_argument("--motor", "-m", choices=["mongodb", "redis", "cassandra"], help="motor de tus reglas guardadas")
    p.add_argument("--coleccion", "-c", help="colección, prefijo de claves o tabla de tus reglas guardadas")
    p.set_defaults(funcion=cmd_validar)

    p = sub.add_parser("reglas", parents=[cuenta, json_], help="lista tus reglas activas",
                       description="Lista las reglas de integridad activas de tu cuenta.")
    p.set_defaults(funcion=cmd_reglas)

    p = sub.add_parser("escanear", parents=[cuenta, json_, salidas], formatter_class=formato,
                       help="escaneo por lotes de tus bases de datos",
                       description="Evalúa todas tus reglas sobre los datos almacenados en tus motores, registra las "
                                   "anomalías en la auditoría (igual que «Iniciar Escaneo Profundo») y opcionalmente "
                                   "genera el Excel y el Issue de GitHub.",
                       epilog="ejemplo:\n  motor escanear --usuario ana --excel reporte.xlsx --github-issue")
    p.set_defaults(funcion=cmd_escanear)

    p = sub.add_parser("reporte", parents=[cuenta, json_, salidas], formatter_class=formato,
                       help="exporta las anomalías ya registradas",
                       description="Muestra las anomalías registradas en tu auditoría sin volver a escanear, y "
                                   "opcionalmente las exporta a Excel o a un Issue de GitHub.",
                       epilog="ejemplo:\n  motor reporte --usuario ana --excel anomalias.xlsx")
    p.set_defaults(funcion=cmd_reporte)

    p = sub.add_parser("demo", parents=[json_, salidas], formatter_class=formato,
                       help="escaneo del conjunto de prueba (sin cuenta)",
                       description="Ejecuta el motor de reglas sobre el conjunto de prueba de los informes (usuarios, "
                                   "pedidos y pagos en MongoDB, Redis y Cassandra simulados en memoria) con 7 reglas "
                                   "que cubren los cuatro tipos. No necesita cuenta ni conexión a bases de datos.",
                       epilog="ejemplos:\n  motor demo\n  motor demo --excel reporte_demo.xlsx\n"
                              "  motor demo --datos mis_datos.json --reglas mis_reglas.json")
    p.add_argument("--datos", default=str(DATOS / "demo_datos.json"), help="JSON {motor: {coleccion: [registros]}}")
    p.add_argument("--reglas", default=str(DATOS / "demo_reglas.json"), help="JSON con la lista de reglas")
    p.set_defaults(funcion=cmd_demo)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada del comando ``motor``."""
    _preparar_consola()
    _cargar_env()
    from modelo.registro_logs import nivel_consola
    nivel_consola(logging.WARNING)

    parser = crear_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "funcion", None):
        parser.print_help()
        return ERROR_USO
    try:
        return args.funcion(args)
    except ErrorCLI as e:
        print(f"Error: {e}", file=sys.stderr)
        return e.codigo
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return ERROR_USO
