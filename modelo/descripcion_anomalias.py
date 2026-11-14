"""Explicación y sugerencia de corrección de cada anomalía.

Lógica compartida por la página Reportes, el reporte Excel, los Issues de GitHub y la CLI.
"""

from typing import Any, Dict

TIPOS = {
    "esquema": {
        "icono": "📐",
        "titulo": "Esquema",
        "explicacion": "El registro `{id}` no cumple el JSON Schema de la regla: faltan campos obligatorios "
                       "o los tipos de dato no coinciden.",
        "sugerencia": "Añade los campos faltantes o corrige el tipo de dato para que coincida con el esquema.",
    },
    "unicidad": {
        "icono": "👯",
        "titulo": "Unicidad",
        "explicacion": "El registro `{id}` repite un valor que debería ser único en la colección.",
        "sugerencia": "Elimina el registro duplicado o cambia el valor del campo para que sea único.",
    },
    "referencial": {
        "icono": "🔗",
        "titulo": "Integridad referencial",
        "explicacion": "El registro `{id}` es huérfano: referencia un valor que no existe en la colección de destino.",
        "sugerencia": "Crea el registro de destino antes de referenciarlo o elimina el registro huérfano.",
    },
    "consistencia": {
        "icono": "⚖️",
        "titulo": "Consistencia",
        "explicacion": "El registro `{id}` está desincronizado entre {motores}.",
        "sugerencia": "Define cuál motor es la fuente de verdad y sincroniza la réplica con sus valores.",
    },
}

_GENERICO = {
    "icono": "⚠️",
    "titulo": "Anomalía",
    "explicacion": "Anomalía detectada en el registro `{id}`.",
    "sugerencia": "Revisa manualmente el registro en la base de datos.",
}


def id_registro(dato: Any) -> str:
    """Devuelve el identificador legible del registro afectado (``_id`` o ``id``)."""
    if isinstance(dato, dict):
        for campo in ("_id", "id"):
            if dato.get(campo) is not None:
                return str(dato[campo])
    return "Desconocido"


def describir(violacion: Dict[str, Any]) -> Dict[str, str]:
    """Devuelve ``icono``, ``titulo``, ``id``, ``motores``, ``explicacion`` y ``sugerencia`` de una violación."""
    tipo = str(violacion.get("tipo") or "")
    plantilla = TIPOS.get(tipo, _GENERICO)
    ident = id_registro(violacion.get("dato_afectado"))
    motores = str(violacion.get("motores_involucrados") or "N/D")
    return {
        "tipo": tipo or "desconocido",
        "icono": plantilla["icono"],
        "titulo": plantilla["titulo"],
        "id": ident,
        "motores": motores,
        "explicacion": plantilla["explicacion"].format(id=ident, motores=motores),
        "sugerencia": plantilla["sugerencia"],
    }


def resumen_por_tipo(violaciones) -> Dict[str, int]:
    """Cuenta las violaciones por tipo de regla (orden: esquema, unicidad, referencial, consistencia)."""
    conteo = {tipo: 0 for tipo in TIPOS}
    for v in violaciones:
        tipo = v.get("tipo") or "desconocido"
        conteo[tipo] = conteo.get(tipo, 0) + 1
    return conteo
