import os
import sys
import traceback

sys.path.append(os.path.abspath('.'))
from modelo.verificador import VerificadorBatch
from modelo.motor_reglas import MotorReglas

print("Testing VerificadorBatch for Fabrizio")
vb = VerificadorBatch("Fabrizio")
try:
    res = vb.ejecutar_verificacion()
    print(f"Total violaciones encontradas en ejecucion estandar: {len(res)}")
    for v in res:
        print(v)
except Exception as e:
    traceback.print_exc()
