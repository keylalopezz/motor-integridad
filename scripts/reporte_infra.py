"""Genera los reportes de la infraestructura: pruebas de Terraform y costos.

Uso: python scripts/reporte_infra.py <salida_terraform_test.txt>
Escribe build/infra/reporte_pruebas.md y build/infra/reporte_costos.md.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "build", "infra")


def reporte_pruebas(texto: str) -> str:
    """Convierte la salida de ``terraform test -verbose`` en una tabla de pruebas superadas."""
    texto = re.sub(r"\x1b\[[0-9;]*m", "", texto)
    filas = re.findall(r'run "([^"]+)"\.\.\. (pass|fail|skip)', texto)
    resumen = re.search(r"(Success!|Failure!) (\d+) passed, (\d+) failed", texto)
    lineas = ["# Reporte de pruebas de infraestructura (Terraform)", "",
              f"- Fecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
              "- Archivo: `infra/tests/infraestructura.tftest.hcl` (proveedores simulados)",
              f"- Resultado: **{resumen.group(0) if resumen else 'sin resumen'}**", "",
              "| Prueba | Resultado |", "|---|---|"]
    lineas += [f"| {n} | {'✅ superada' if r == 'pass' else '❌ ' + r} |" for n, r in filas]
    return "\n".join(lineas) + "\n"


def reporte_costos() -> str:
    """Calcula el costo mensual y anual de la infraestructura a partir de ``infra/precios.json``."""
    with open(os.path.join(RAIZ, "infra", "precios.json"), encoding="utf-8") as f:
        datos = json.load(f)
    tc, servicios = datos["tipo_cambio_pen"], datos["servicios"]
    actual = sum(s["costo_usd"] for s in servicios)
    pago = sum(s["costo_pago_usd"] for s in servicios)
    lineas = ["# Reporte de costos de la infraestructura", "",
              f"- Fecha: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Tipo de cambio: S/ {tc:.2f} por USD", "",
              "| Servicio | Recurso Terraform | Plan | Límite | USD/mes | Plan de pago | USD/mes |",
              "|---|---|---|---|---:|---|---:|"]
    lineas += [f"| {s['servicio']} | `{s['recurso']}` | {s['plan']} | {s['limite']} | {s['costo_usd']:.2f} | "
               f"{s['plan_pago']} | {s['costo_pago_usd']:.2f} |" for s in servicios]
    lineas += ["", "| Escenario | USD/mes | S/ mes | S/ año |", "|---|---:|---:|---:|",
               f"| Actual (capas gratuitas) | {actual:.2f} | {actual * tc:.2f} | {actual * tc * 12:.2f} |",
               f"| Escalado a planes de pago | {pago:.2f} | {pago * tc:.2f} | {pago * tc * 12:.2f} |",
               "", "El costo de ambiente del FD01 (S/ 0.00) corresponde al escenario actual."]
    return "\n".join(lineas) + "\n"


def main() -> int:
    os.makedirs(SALIDA, exist_ok=True)
    texto = open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else ""
    pruebas, costos = reporte_pruebas(texto), reporte_costos()
    for nombre, contenido in (("reporte_pruebas.md", pruebas), ("reporte_costos.md", costos)):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as f:
            f.write(contenido)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(pruebas + "\n" + costos)
    print(pruebas + "\n" + costos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
