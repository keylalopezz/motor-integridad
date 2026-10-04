"""Validación previa a la escritura (simulador pre-escritura)."""

from typing import Dict, Any, Tuple
import jsonschema
from .motor_reglas import MotorReglas
from .adaptadores import get_adapter

class Validador:
    """Comprueba un registro contra las reglas de esquema y unicidad antes de escribirlo."""
    def __init__(self, usuario: str):
        """Crea el validador para ``usuario``."""
        self.usuario = usuario
        self.motor_reglas = MotorReglas(usuario)

    def validar_registro(self, motor: str, coleccion: str, registro: Dict[str, Any]) -> Tuple[bool, str]:
        """Valida ``registro`` para ``motor`` y ``coleccion``; devuelve ``(valido, mensaje)``."""
        filtros = {
            'motor_origen': motor,
            'coleccion_origen': coleccion
        }
        reglas = self.motor_reglas.obtener_reglas(filtros)
        
        for regla in reglas:
            if regla['tipo'] == 'esquema':
                schema = regla.get('schema')
                if schema:
                    try:
                        jsonschema.validate(instance=registro, schema=schema)
                    except jsonschema.exceptions.ValidationError as e:
                        return False, f"Error de esquema: {e.message}"
            
            elif regla['tipo'] == 'unicidad':
                campo = regla.get('campo')
                if campo and registro.get(campo) is not None:
                    valor = registro[campo]
                    adaptador = get_adapter(motor, self.usuario)
                    try:
                        duplicados = adaptador.contar_duplicados(coleccion, campo, valor)
                    finally:
                        adaptador.cerrar()
                    if duplicados > 0:
                        return False, f"Error de unicidad: el valor '{valor}' en el campo '{campo}' ya existe."
        
        return True, "Validacion exitosa."
