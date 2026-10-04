# Arquitectura

El sistema sigue el patrón **Modelo-Vista-Controlador** organizado en capas, con una **capa de adaptadores** que
ofrece una interfaz común para los tres motores NoSQL y un **plano de control** en Supabase.

![Subsistemas por capas](diagramas/sad_subsistemas.png)

## Capas

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Presentación | `vista/` | Aplicación Streamlit (`app.py`, `login.py` y las páginas de `vista/rutas/`) |
| Control | `controlador/` | Orquesta las peticiones de la vista hacia el modelo |
| Negocio | `modelo/` | Autenticación, motor de reglas, validador, verificador por lotes, auditoría y conexiones |
| Integración | `modelo/adaptadores/` | `MongoAdapter`, `RedisAdapter` y `CassandraAdapter` implementan la interfaz `Adaptador` |
| Servicios externos | — | Supabase (PostgreSQL) y los motores en MongoDB Atlas, Upstash y DataStax Astra |

## Componentes principales

- **`SupabaseClient`** (singleton): única conexión al plano de control; lee la configuración de `.env` o de
  `st.secrets`.
- **`GestorConexiones`**: guarda y lee las credenciales de cada motor por usuario, **cifradas con Fernet**
  (`ENCRYPTION_KEY`).
- **`get_adapter(motor, usuario)`**: fábrica que descifra las credenciales y crea el adaptador del motor.
- **`MotorReglas`**: CRUD de reglas en la tabla `reglas`.
- **`Validador`**: valida un registro antes de escribirlo contra las reglas de esquema (JSON Schema) y unicidad.
- **`VerificadorBatch`**: escaneo por lotes; evalúa las cuatro reglas, reutiliza una conexión por motor y, si una
  regla falla, conserva sus violaciones anteriores y continúa con las demás.
- **`LogAuditoria`**: reemplaza y consulta las violaciones de cada regla en `auditoria_violaciones`.

![Componentes](diagramas/sad_componentes.png)

## Modelo de datos del plano de control

Cuatro tablas en Supabase con RLS activado y eliminación en cascada:

![Modelo relacional](diagramas/sad_bd_relacional.png)

## Flujo del escaneo por lotes

![Secuencia del escaneo](diagramas/sad_sec_escaneo.png)

## Despliegue

![Despliegue](diagramas/sad_despliegue.png)

## Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Patrón Adaptador | Aplicar las mismas reglas a los tres motores y agregar motores sin tocar el motor de reglas |
| Supabase como plano de control | PostgreSQL gestionado, RLS y plan gratuito |
| Cifrado Fernet de credenciales | Cifrado autenticado simple; la clave vive solo en los secretos de despliegue |
| bcrypt para contraseñas | Hash adaptable y resistente a fuerza bruta |
| Streamlit Community Cloud | Despliegue gratuito y automático desde GitHub |
