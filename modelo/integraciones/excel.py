"""Integración con Microsoft Office: reporte de anomalías en un libro de Excel (.xlsx)."""

import io
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from ..descripcion_anomalias import TIPOS, describir, resumen_por_tipo

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_COLOR = "4F46E5"
_TITULO = Font(bold=True, size=16, color=_COLOR)
_CABECERA = Font(bold=True, color="FFFFFF")
_RELLENO = PatternFill("solid", fgColor=_COLOR)
_AJUSTE = Alignment(wrap_text=True, vertical="top")

COLUMNAS = ["N°", "Tipo", "Motores", "Colección", "Campo", "Registro", "Explicación",
            "Sugerencia de corrección", "Detectado en", "Dato afectado (JSON)"]
_ANCHOS = [6, 16, 20, 16, 14, 14, 55, 55, 22, 70]


def _info_regla(violacion: Dict[str, Any], reglas: Dict[str, Dict]) -> Dict[str, Any]:
    """Datos de la regla de una violación: del join de Supabase (``reglas``) o del mapa ``reglas``."""
    return violacion.get("reglas") or reglas.get(str(violacion.get("regla_id")), {}) or {}


def _filas(violaciones: List[Dict], reglas: Dict[str, Dict]) -> List[List[Any]]:
    """Convierte las violaciones en filas de la hoja de detalle."""
    filas = []
    for n, v in enumerate(violaciones, start=1):
        d = describir(v)
        regla = _info_regla(v, reglas)
        filas.append([
            n,
            TIPOS.get(d["tipo"], {}).get("titulo", d["tipo"]),
            d["motores"],
            regla.get("coleccion_origen", ""),
            regla.get("campo", ""),
            d["id"],
            d["explicacion"].replace("`", ""),
            d["sugerencia"],
            str(v.get("detectado_en") or ""),
            json.dumps(v.get("dato_afectado"), ensure_ascii=False, default=str),
        ])
    return filas


def _cabecera(hoja, fila: int, valores: Iterable[str]) -> None:
    """Escribe una fila de cabecera con el estilo del reporte."""
    for col, valor in enumerate(valores, start=1):
        celda = hoja.cell(row=fila, column=col, value=valor)
        celda.font, celda.fill = _CABECERA, _RELLENO


def _hoja_resumen(libro: Workbook, violaciones: List[Dict], usuario: str, origen: str, fecha: str) -> None:
    """Hoja con los totales por tipo de regla y por motor."""
    hoja = libro.active
    hoja.title = "Resumen"
    hoja["A1"] = "Reporte de anomalías de integridad"
    hoja["A1"].font = _TITULO
    datos = [("Usuario", usuario), ("Origen", origen), ("Generado (UTC)", fecha),
             ("Total de anomalías", len(violaciones))]
    for i, (clave, valor) in enumerate(datos, start=3):
        hoja.cell(row=i, column=1, value=clave).font = Font(bold=True)
        hoja.cell(row=i, column=2, value=valor)

    fila = 3 + len(datos) + 1
    _cabecera(hoja, fila, ["Tipo de regla", "Anomalías"])
    for tipo, cantidad in resumen_por_tipo(violaciones).items():
        fila += 1
        hoja.cell(row=fila, column=1, value=TIPOS.get(tipo, {}).get("titulo", tipo))
        hoja.cell(row=fila, column=2, value=cantidad)

    fila += 2
    _cabecera(hoja, fila, ["Motores involucrados", "Anomalías"])
    for motores, cantidad in Counter(str(v.get("motores_involucrados") or "N/D") for v in violaciones).most_common():
        fila += 1
        hoja.cell(row=fila, column=1, value=motores)
        hoja.cell(row=fila, column=2, value=cantidad)

    hoja.column_dimensions["A"].width = 26
    hoja.column_dimensions["B"].width = 34


def _hoja_detalle(libro: Workbook, violaciones: List[Dict], reglas: Dict[str, Dict]) -> None:
    """Hoja con una fila por anomalía, en formato de tabla de Excel con filtros."""
    hoja = libro.create_sheet("Anomalías")
    _cabecera(hoja, 1, COLUMNAS)
    for fila in _filas(violaciones, reglas):
        hoja.append(fila)
    for col, ancho in enumerate(_ANCHOS, start=1):
        hoja.column_dimensions[get_column_letter(col)].width = ancho
    for fila in hoja.iter_rows(min_row=2):
        for celda in fila:
            celda.alignment = _AJUSTE
    hoja.freeze_panes = "A2"
    if violaciones:
        rango = f"A1:{get_column_letter(len(COLUMNAS))}{len(violaciones) + 1}"
        tabla = Table(displayName="Anomalias", ref=rango)
        tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        hoja.add_table(tabla)


def generar_excel(violaciones: List[Dict], usuario: str = "", origen: str = "Motor de Integridad",
                  reglas: Optional[Dict[str, Dict]] = None) -> bytes:
    """Genera el libro de Excel del reporte y lo devuelve como bytes.

    ``violaciones`` son las filas de ``auditoria_violaciones`` o las devueltas por el escaneo;
    ``reglas`` (opcional) es un mapa ``{regla_id: regla}`` para completar colección y campo.
    """
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    libro = Workbook()
    _hoja_resumen(libro, violaciones, usuario, origen, fecha)
    _hoja_detalle(libro, violaciones, reglas or {})
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def guardar_excel(ruta: str, violaciones: List[Dict], **kwargs) -> str:
    """Genera el reporte y lo escribe en ``ruta``; devuelve la ruta."""
    with open(ruta, "wb") as archivo:
        archivo.write(generar_excel(violaciones, **kwargs))
    return ruta
