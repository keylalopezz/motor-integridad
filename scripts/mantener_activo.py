"""Mantiene activos los servicios de capa gratuita que se suspenden por inactividad.

Lo ejecuta el flujo ``mantener-activo.yml`` cada pocas horas:

1. Supabase: consulta la tabla ``usuarios_sistema`` (los proyectos gratuitos se pausan tras ~7 días).
2. MongoDB Atlas, Upstash Redis y DataStax Astra: ``verificar_salud`` (ping) con las conexiones guardadas
   (cifradas) del usuario ``MOTOR_USUARIO``, o de todos los usuarios si no se indica. Reintenta para dar
   tiempo a que un motor hibernado se reanude.
3. Aplicación en Streamlit Community Cloud: la abre con un navegador sin interfaz (Playwright) y, si
   está dormida, pulsa el botón para despertarla.

Escribe ``build/mantener_activo/reporte.md`` y termina con código 1 si algún servicio falló, para que
GitHub notifique por correo y se pueda reactivar desde su panel.

Variables: SUPABASE_URL, SUPABASE_KEY, ENCRYPTION_KEY, MOTOR_USUARIO (opcional), APP_URL.
"""

import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable, List, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
SALIDA = os.path.join(RAIZ, "build", "mantener_activo")
APP_URL = os.environ.get("APP_URL", "https://motor-integridad.streamlit.app")
BOTON_DESPERTAR = "get this app back up"

Fila = Tuple[str, str, str, float]  # servicio, estado, detalle, milisegundos


def con_reintentos(funcion: Callable[[], str], intentos: int = 3, espera: float = 20) -> Tuple[bool, str, float]:
    """Ejecuta ``funcion`` hasta ``intentos`` veces; devuelve (correcto, detalle, milisegundos)."""
    ultimo = ""
    for intento in range(1, intentos + 1):
        inicio = time.perf_counter()
        try:
            detalle = funcion()
            return True, detalle, round((time.perf_counter() - inicio) * 1000, 1)
        except Exception as e:  # noqa: BLE001 - se informa cualquier fallo del proveedor
            ultimo = f"{type(e).__name__}: {e}"[:200]
            if intento < intentos:
                time.sleep(espera)
    return False, ultimo, 0.0


def revisar_bases(usuario_objetivo: str) -> List[Fila]:
    """Consulta Supabase y hace ping a cada motor NoSQL configurado."""
    from modelo.supabase_client import SupabaseClient
    from modelo.gestor_conexiones import MOTORES_NOSQL
    filas: List[Fila] = []
    cliente = SupabaseClient().get_client()
    if cliente is None:
        return [("Supabase", "❌ error", "No se pudo crear el cliente (revisa SUPABASE_URL y SUPABASE_KEY)", 0.0)]

    ok, detalle, ms = con_reintentos(
        lambda: f"{len(cliente.table('usuarios_sistema').select('id').limit(1).execute().data)} fila(s) leída(s)")
    filas.append(("Supabase", "✅ activo" if ok else "❌ error", detalle, ms))
    if not ok:
        return filas

    consulta = cliente.table("conexiones_motores").select("usuario, motor")
    if usuario_objetivo:
        consulta = consulta.eq("usuario", usuario_objetivo)
    conexiones = [c for c in consulta.execute().data or [] if c["motor"] in MOTORES_NOSQL]
    if not conexiones:
        filas.append(("Motores NoSQL", "⚠️ sin conexiones", f"No hay conexiones guardadas para {usuario_objetivo or 'ningún usuario'}", 0.0))

    from modelo.adaptadores import get_adapter

    def ping(motor: str, usuario: str) -> str:
        adaptador = get_adapter(motor, usuario)
        try:
            salud = adaptador.verificar_salud()
            return f"{salud.get('estado')} · {salud.get('detalle')}"
        finally:
            adaptador.cerrar()

    for c in conexiones:
        ok, detalle, ms = con_reintentos(lambda c=c: ping(c["motor"], c["usuario"]))
        filas.append((f"{c['motor'].capitalize()} ({c['usuario']})", "✅ activo" if ok else "❌ error", detalle, ms))
    return filas


def despertar_app(url: str) -> Fila:
    """Abre la app con Playwright y pulsa «Yes, get this app back up!» si Streamlit la durmió."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ("Aplicación web", "⚠️ omitido", "Playwright no está instalado", 0.0)
    inicio = time.perf_counter()
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page()
            pagina.goto(url, wait_until="domcontentloaded", timeout=90_000)
            pagina.wait_for_timeout(8_000)
            boton = pagina.get_by_role("button", name=BOTON_DESPERTAR, exact=False)
            if boton.count():
                boton.first.click()
                pagina.wait_for_timeout(60_000)  # la app tarda alrededor de un minuto en arrancar
                estado = "✅ despertada"
                detalle = "Estaba dormida: se pulsó el botón de reactivación"
            else:
                estado, detalle = "✅ activa", "Respondió sin estar dormida"
            if pagina.get_by_role("button", name=BOTON_DESPERTAR, exact=False).count():
                estado, detalle = "❌ error", "Sigue dormida después de pulsar el botón"
            navegador.close()
        return ("Aplicación web", estado, detalle, round((time.perf_counter() - inicio) * 1000, 1))
    except Exception as e:  # noqa: BLE001
        return ("Aplicación web", "❌ error", f"{type(e).__name__}: {e}"[:200], 0.0)


def escribir_reporte(filas: List[Fila]) -> str:
    """Reporte Markdown con el estado de cada servicio."""
    lineas = ["# Mantener activos los servicios", "",
              f"- Fecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", f"- Aplicación: {APP_URL}", "",
              "| Servicio | Estado | Detalle | ms |", "|---|---|---|---:|"]
    lineas += [f"| {s} | {e} | {d.replace('|', '/')} | {ms} |" for s, e, d, ms in filas]
    return "\n".join(lineas) + "\n"


def main() -> int:
    filas: List[Fila] = []
    faltan = [v for v in ("SUPABASE_URL", "SUPABASE_KEY", "ENCRYPTION_KEY") if not os.environ.get(v)]
    if faltan:
        filas.append(("Bases de datos", "⚠️ omitido", f"Faltan los secretos {', '.join(faltan)}", 0.0))
    else:
        filas += revisar_bases(os.environ.get("MOTOR_USUARIO", "").strip())
    if "--sin-app" not in sys.argv:
        filas.append(despertar_app(APP_URL))

    reporte = escribir_reporte(filas)
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "reporte.md"), "w", encoding="utf-8") as f:
        f.write(reporte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(reporte)
    print(reporte)
    fallos = [s for s, e, _, _ in filas if e.startswith("❌")]
    for servicio in fallos:
        print(f"::error title=Servicio inactivo::{servicio} no respondió; reactívalo desde el panel del proveedor.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
