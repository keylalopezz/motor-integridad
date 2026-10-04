"""Copia de seguridad de la base de control (Supabase) y de los motores NoSQL configurados.

Lee SUPABASE_URL, SUPABASE_KEY y ENCRYPTION_KEY del entorno. El archivo resultante se
cifra con Fernet (ENCRYPTION_KEY) porque contiene datos y credenciales.

Uso:
    python scripts/respaldo.py                       # genera build/respaldo/*.zip.enc y el reporte
    python scripts/respaldo.py --descifrar ARCHIVO   # recupera el .zip para restaurar
"""
import hashlib
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
SALIDA = os.path.join(RAIZ, "build", "respaldo")
TABLAS = ["usuarios_sistema", "reglas", "auditoria_violaciones", "conexiones_motores", "eventos_uso"]


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(os.environ["ENCRYPTION_KEY"].encode("utf-8"))


def _json(datos) -> bytes:
    return json.dumps(datos, ensure_ascii=False, indent=1, default=str).encode("utf-8")


def respaldar_supabase(cliente, zf, filas):
    """Exporta cada tabla de Supabase a ``supabase/<tabla>.json``."""
    for tabla in TABLAS:
        inicio = time.time()
        try:
            datos, desde = [], 0
            while True:
                lote = cliente.table(tabla).select("*").range(desde, desde + 999).execute().data or []
                datos += lote
                if len(lote) < 1000:
                    break
                desde += 1000
            zf.writestr(f"supabase/{tabla}.json", _json(datos))
            filas.append(("Supabase", tabla, len(datos), "OK", time.time() - inicio))
        except Exception as e:
            filas.append(("Supabase", tabla, 0, f"Error: {type(e).__name__}", time.time() - inicio))


def respaldar_motores(cliente, zf, filas):
    """Exporta todos los recursos de los motores NoSQL guardados por cada usuario."""
    from modelo.adaptadores import get_adapter
    conexiones = cliente.table("conexiones_motores").select("usuario, motor").execute().data or []
    for c in conexiones:
        usuario, motor = c["usuario"], c["motor"]
        adaptador = None
        try:
            adaptador = get_adapter(motor, usuario)
            for recurso in adaptador.listar_recursos():
                inicio = time.time()
                nombre = recurso["nombre"]
                datos = adaptador.obtener_todos(nombre)
                zf.writestr(f"{motor}/{usuario}/{nombre}.json", _json(datos))
                filas.append((f"{motor.capitalize()} ({usuario})", nombre, len(datos), "OK", time.time() - inicio))
        except Exception as e:
            filas.append((f"{motor.capitalize()} ({usuario})", "-", 0, f"Error: {type(e).__name__}", 0))
        finally:
            if adaptador:
                adaptador.cerrar()


def escribir_reporte(filas, archivo, tamano, sha, duracion) -> bool:
    """Genera ``reporte_respaldo.md``, lo agrega al resumen de GitHub Actions e indica si todo salió bien."""
    ok = sum(1 for f in filas if f[3] == "OK")
    lineas = [
        "# Reporte de copia de seguridad", "",
        f"- Fecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Archivo: `{archivo}` ({tamano / 1024:.1f} KB, cifrado con Fernet)",
        f"- SHA-256: `{sha}`",
        f"- Recursos respaldados: {ok} de {len(filas)} · Registros: {sum(f[2] for f in filas)} · Duración: {duracion:.1f} s",
        "", "| Origen | Recurso | Registros | Estado | Tiempo (s) |", "|---|---|---:|---|---:|",
    ]
    lineas += [f"| {o} | {r} | {n} | {e} | {t:.2f} |" for o, r, n, e, t in filas]
    lineas += ["", "Restauración: descargar el artefacto y ejecutar "
               "`python scripts/respaldo.py --descifrar <archivo>.zip.enc` con la misma ENCRYPTION_KEY."]
    texto = "\n".join(lineas) + "\n"
    with open(os.path.join(SALIDA, "reporte_respaldo.md"), "w", encoding="utf-8") as f:
        f.write(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto)
    print(texto)
    return ok == len(filas)


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--descifrar":
        destino = sys.argv[2].removesuffix(".enc")
        with open(sys.argv[2], "rb") as f, open(destino, "wb") as g:
            g.write(_fernet().decrypt(f.read()))
        print(f"Respaldo descifrado en {destino}")
        return 0

    os.makedirs(SALIDA, exist_ok=True)
    faltan = [v for v in ("SUPABASE_URL", "SUPABASE_KEY", "ENCRYPTION_KEY") if not os.environ.get(v)]
    if faltan:
        print(f"::warning::Respaldo omitido: faltan los secretos {', '.join(faltan)}.")
        with open(os.path.join(SALIDA, "reporte_respaldo.md"), "w", encoding="utf-8") as f:
            f.write(f"# Reporte de copia de seguridad\n\nOmitido: faltan los secretos {', '.join(faltan)}.\n")
        return 0

    from modelo.supabase_client import SupabaseClient
    cliente = SupabaseClient().get_client()
    inicio = time.time()
    filas, buffer = [], io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        respaldar_supabase(cliente, zf, filas)
        respaldar_motores(cliente, zf, filas)
    cifrado = _fernet().encrypt(buffer.getvalue())
    archivo = f"respaldo_{datetime.now(timezone.utc):%Y%m%d_%H%M}.zip.enc"
    with open(os.path.join(SALIDA, archivo), "wb") as f:
        f.write(cifrado)
    completo = escribir_reporte(filas, archivo, len(cifrado), hashlib.sha256(cifrado).hexdigest(), time.time() - inicio)
    return 0 if completo else 1


if __name__ == "__main__":
    sys.exit(main())
