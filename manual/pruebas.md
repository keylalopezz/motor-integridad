# Pruebas

## Pruebas unitarias

```bash
pytest
```

Las pruebas usan dobles de Supabase y de los motores, por lo que no necesitan credenciales ni conexión.

| Archivo | Qué comprueba |
|---|---|
| `tests/test_autenticacion.py` | Validación del usuario, duplicados sin distinguir mayúsculas, escape de comodines y login |
| `tests/test_redis_adapter.py` | Lectura de registros JSON y *hash*, y claves sin prefijo |
| `tests/test_verificador.py` | Las cuatro reglas, el reemplazo de violaciones, el manejo de errores y los campos nulos |

## Conjunto de datos de prueba

Cargado con `poblar_mongo.py`, `poblar_redis.py` y `poblar_cassandra.py`. Con las reglas del caso de estudio,
el escaneo por lotes debe detectar **7 anomalías**:

| Dato | Motor | Regla incumplida |
|---|---|---|
| U003 (sin email) | MongoDB | Esquema |
| U004 (email duplicado) | MongoDB | Unicidad |
| P102 (usuario U999 inexistente) | MongoDB | Integridad referencial |
| P102 (usuario U999 inexistente) | Redis | Integridad referencial |
| U001 (edad 28 frente a 29) | MongoDB ↔ Redis | Consistencia |
| PA3 (pedido inexistente) | Cassandra | Integridad referencial |
| PA4 (transacción duplicada) | Cassandra | Unicidad |
