import json
from typing import List, Dict, Any
import jsonschema
from .motor_reglas import MotorReglas
from .adaptadores import get_adapter
from .log_auditoria import LogAuditoria


def _clave(valor: Any) -> str:
    """Representacion estable de un valor para indexarlo (sirve para listas/dicts y tipos no hashables)."""
    return json.dumps(valor, sort_keys=True, default=str)


def _tiene_valor(registro: Dict, campo: str) -> bool:
    """Cassandra devuelve todas las columnas aunque esten vacias (None): un campo nulo no cuenta como valor."""
    return registro.get(campo) is not None


class VerificadorBatch:
    def __init__(self, usuario: str):
        self.usuario = usuario
        self.motor_reglas = MotorReglas(usuario)
        self.auditoria = LogAuditoria(usuario)
        self.errores: List[str] = []
        self._adaptadores: Dict[str, Any] = {}

    def _adaptador(self, motor: str):
        # Reutiliza una conexion por motor durante todo el escaneo
        if motor not in self._adaptadores:
            self._adaptadores[motor] = get_adapter(motor, self.usuario)
        return self._adaptadores[motor]

    def _cerrar_adaptadores(self) -> None:
        for adp in self._adaptadores.values():
            try:
                adp.cerrar()
            except Exception:
                pass
        self._adaptadores = {}

    def ejecutar_verificacion(self) -> List[Dict]:
        reglas = self.motor_reglas.obtener_reglas()
        violaciones_detectadas = []
        self.errores = []
        verificadores = {
            'referencial': self._verificar_referencial,
            'consistencia': self._verificar_consistencia,
            'esquema': self._verificar_esquema,
            'unicidad': self._verificar_unicidad,
        }

        try:
            for regla in reglas:
                verificar = verificadores.get(regla['tipo'])
                if not verificar:
                    continue
                descripcion = f"{regla['tipo']} en {regla.get('motor_origen')}.{regla.get('coleccion_origen')}"
                try:
                    violaciones = verificar(regla)
                except Exception as e:
                    # Si la regla no se pudo evaluar se conservan sus violaciones anteriores
                    self.errores.append(f"Regla {descripcion}: {type(e).__name__}: {e}")
                    continue
                self.auditoria.limpiar_regla(regla['id'])
                self.auditoria.registrar_violaciones(violaciones)
                violaciones_detectadas.extend(violaciones)
        finally:
            self._cerrar_adaptadores()

        return violaciones_detectadas

    def _violacion(self, regla: Dict, motores: str, dato: Dict) -> Dict:
        return {
            "regla_id": regla['id'],
            "tipo": regla['tipo'],
            "motores_involucrados": motores,
            "dato_afectado": dato
        }

    def _verificar_referencial(self, regla: Dict) -> List[Dict]:
        motor_origen = regla['motor_origen']
        motor_destino = regla['motor_destino']
        campo_origen = regla['campo']
        campo_destino = regla['campo_destino']
        if not (motor_destino and regla.get('coleccion_destino') and campo_destino):
            raise ValueError("La regla referencial necesita motor, coleccion y campo de destino.")

        registros_origen = self._adaptador(motor_origen).obtener_todos(regla['coleccion_origen'])
        registros_destino = self._adaptador(motor_destino).obtener_todos(regla['coleccion_destino'])
        existentes = {_clave(r[campo_destino]) for r in registros_destino if _tiene_valor(r, campo_destino)}

        motores = f"{motor_origen},{motor_destino}"
        return [
            self._violacion(regla, motores, registro)
            for registro in registros_origen
            if _tiene_valor(registro, campo_origen) and _clave(registro[campo_origen]) not in existentes
        ]

    def _verificar_consistencia(self, regla: Dict) -> List[Dict]:
        """Los registros replicados en dos motores (enlazados por campo -> campo_destino) deben coincidir
        en todos los atributos que comparten. Detecta registros ausentes y valores divergentes."""
        motor_origen = regla['motor_origen']
        motor_destino = regla['motor_destino']
        campo_origen = regla['campo']
        campo_destino = regla['campo_destino']
        if not (motor_destino and regla.get('coleccion_destino') and campo_destino):
            raise ValueError("La regla de consistencia necesita motor, coleccion y campo de destino.")

        registros_origen = self._adaptador(motor_origen).obtener_todos(regla['coleccion_origen'])
        registros_destino = self._adaptador(motor_destino).obtener_todos(regla['coleccion_destino'])
        indice_destino = {_clave(r[campo_destino]): r for r in registros_destino if _tiene_valor(r, campo_destino)}

        motores = f"{motor_origen},{motor_destino}"
        ignorar = {'_id', campo_origen, campo_destino}
        violaciones = []
        for registro in registros_origen:
            if not _tiene_valor(registro, campo_origen):
                continue
            valor = registro[campo_origen]
            replica = indice_destino.get(_clave(valor))
            if replica is None:
                violaciones.append(self._violacion(regla, motores, {
                    "_id": registro.get('_id', valor),
                    "motivo": f"Registro ausente en {motor_destino}.{regla['coleccion_destino']}",
                    "origen": registro
                }))
                continue

            diferencias = {
                k: {"origen": registro[k], "destino": replica[k]}
                for k in registro.keys() & replica.keys()
                if k not in ignorar and _clave(registro[k]) != _clave(replica[k])
            }
            if diferencias:
                violaciones.append(self._violacion(regla, motores, {
                    "_id": registro.get('_id', valor),
                    "motivo": "Valores divergentes entre motores",
                    "diferencias": diferencias,
                    "origen": registro,
                    "destino": replica
                }))
        return violaciones

    def _verificar_esquema(self, regla: Dict) -> List[Dict]:
        motor_origen = regla.get('motor_origen')
        coleccion_origen = regla.get('coleccion_origen')
        schema = regla.get('schema') or {}
        if not motor_origen or not coleccion_origen or not schema:
            return []

        validador = jsonschema.validators.validator_for(schema)(schema)
        violaciones = []
        for registro in self._adaptador(motor_origen).obtener_todos(coleccion_origen):
            errores = [e.message for e in validador.iter_errors(registro)]
            if errores:
                violaciones.append(self._violacion(regla, motor_origen, {**registro, "_errores_esquema": errores}))
        return violaciones

    def _verificar_unicidad(self, regla: Dict) -> List[Dict]:
        motor_origen = regla.get('motor_origen')
        coleccion_origen = regla.get('coleccion_origen')
        campo = regla.get('campo')
        if not motor_origen or not coleccion_origen or not campo:
            return []

        valores_vistos: Dict[str, List[Dict]] = {}
        for registro in self._adaptador(motor_origen).obtener_todos(coleccion_origen):
            if _tiene_valor(registro, campo):
                valores_vistos.setdefault(_clave(registro[campo]), []).append(registro)

        return [
            self._violacion(regla, motor_origen, registro)
            for registros in valores_vistos.values() if len(registros) > 1
            for registro in registros[1:]
        ]
