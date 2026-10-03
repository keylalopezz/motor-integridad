import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modelo import verificador as mod


class AdaptadorFalso:
    def __init__(self, datos):
        self.datos = datos

    def obtener_todos(self, coleccion):
        return [dict(r) for r in self.datos.get(coleccion, [])]

    def cerrar(self):
        pass


USUARIOS = [
    {"_id": "U001", "email": "ana@email.com", "edad": 28},
    {"_id": "U002", "email": "carlos@email.com", "edad": 35},
    {"_id": "U003", "edad": 40},
    {"_id": "U004", "email": "ana@email.com", "edad": 22},
]
PEDIDOS = [
    {"_id": "P100", "usuario_id": "U001"},
    {"_id": "P102", "usuario_id": "U999"},
]
REDIS_USUARIOS = [
    {"_id": "U001", "email": "ana@email.com", "edad": 29},
    {"_id": "U002", "email": "carlos@email.com", "edad": 35},
]

MOTORES = {
    "mongodb": AdaptadorFalso({"usuarios": USUARIOS, "pedidos": PEDIDOS}),
    "redis": AdaptadorFalso({"usuarios": REDIS_USUARIOS}),
}


def ejecutar(reglas):
    with patch.object(mod, "MotorReglas") as mr, patch.object(mod, "LogAuditoria") as la, \
            patch.object(mod, "get_adapter", side_effect=lambda motor, usuario: MOTORES[motor]):
        mr.return_value.obtener_reglas.return_value = reglas
        v = mod.VerificadorBatch("test")
        resultado = v.ejecutar_verificacion()
        return resultado, v.errores, la.return_value


def regla(tipo, **kw):
    base = {"id": tipo, "tipo": tipo, "motor_origen": "mongodb", "coleccion_origen": "usuarios", "campo": "_id"}
    return {**base, **kw}


def test_esquema_detecta_documento_sin_email():
    schema = {"type": "object", "required": ["email"]}
    res, errores, _ = ejecutar([regla("esquema", schema=schema)])
    assert errores == []
    assert [v["dato_afectado"]["_id"] for v in res] == ["U003"]


def test_unicidad_detecta_duplicado():
    res, _, _ = ejecutar([regla("unicidad", campo="email")])
    assert [v["dato_afectado"]["_id"] for v in res] == ["U004"]


def test_referencial_detecta_huerfano():
    r = regla("referencial", coleccion_origen="pedidos", campo="usuario_id",
              motor_destino="mongodb", coleccion_destino="usuarios", campo_destino="_id")
    res, _, _ = ejecutar([r])
    assert [v["dato_afectado"]["_id"] for v in res] == ["P102"]


def test_consistencia_detecta_ausentes_y_divergentes():
    r = regla("consistencia", motor_destino="redis", coleccion_destino="usuarios", campo_destino="_id")
    res, _, _ = ejecutar([r])
    por_id = {v["dato_afectado"]["_id"]: v["dato_afectado"] for v in res}
    assert set(por_id) == {"U001", "U003", "U004"}
    assert por_id["U001"]["diferencias"] == {"edad": {"origen": 28, "destino": 29}}


def test_reescaneo_limpia_violaciones_previas():
    _, _, auditoria = ejecutar([regla("unicidad", campo="email")])
    auditoria.limpiar_regla.assert_called_once_with("unicidad")
    auditoria.registrar_violaciones.assert_called_once()


def test_error_de_motor_se_reporta_y_no_borra_historial():
    r = regla("esquema", motor_origen="cassandra", schema={"type": "object"})
    res, errores, auditoria = ejecutar([r])
    assert res == [] and len(errores) == 1
    auditoria.limpiar_regla.assert_not_called()


def test_campos_nulos_no_cuentan_como_duplicados_ni_huerfanos():
    # Cassandra devuelve todas las columnas, con None en las vacias
    pagos = [
        {"id": "PA1", "transaccion": None, "pedido_id": None},
        {"id": "PA2", "transaccion": None, "pedido_id": None},
        {"id": "PA3", "transaccion": "TX1", "pedido_id": "P100"},
    ]
    MOTORES["cassandra"] = AdaptadorFalso({"pagos": pagos})
    try:
        reglas = [
            regla("unicidad", motor_origen="cassandra", coleccion_origen="pagos", campo="transaccion"),
            regla("referencial", motor_origen="cassandra", coleccion_origen="pagos", campo="pedido_id",
                  motor_destino="mongodb", coleccion_destino="pedidos", campo_destino="_id"),
        ]
        res, errores, _ = ejecutar(reglas)
    finally:
        del MOTORES["cassandra"]
    assert errores == [] and res == []
