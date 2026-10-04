"""Capa de modelo: lógica de negocio, acceso a Supabase y adaptadores de los motores NoSQL."""

from .supabase_client import SupabaseClient
from .motor_reglas import MotorReglas
from .validador import Validador
from .verificador import VerificadorBatch
from .log_auditoria import LogAuditoria
