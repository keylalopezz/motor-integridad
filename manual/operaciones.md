# Operaciones automatizadas

Todas las automatizaciones están en `.github/workflows/` y se ejecutan con GitHub Actions. Cada una deja
su reporte en el resumen de la ejecución (*Summary*) y como artefacto descargable.

## Infraestructura con Terraform (`infraestructura.yml`)

La carpeta `infra/` describe la infraestructura del proyecto en capas gratuitas: proyecto de Supabase,
clúster M0 de MongoDB Atlas (con usuario y lista de acceso), base de Upstash Redis y base de DataStax Astra.

| Paso | Resultado |
|---|---|
| `terraform fmt`, `init`, `validate` | Formato y sintaxis correctos |
| `terraform test` | Pruebas de `infra/tests/` con proveedores simulados → **reporte de pruebas** |
| `scripts/reporte_infra.py` | **Reporte de costos** a partir de `infra/precios.json` |
| `plan` / `apply` (manual) | Aprovisionamiento real con los secretos de cada proveedor |

## Objetos de la base de datos con Liquibase (`liquibase.yml`)

El changelog `liquibase/db.changelog-master.yaml` crea las tablas, la seguridad RLS, los índices y la tabla
`eventos_uso`. Se aplica primero en un PostgreSQL temporal y, si existen los secretos `LIQUIBASE_URL`,
`LIQUIBASE_USERNAME` y `LIQUIBASE_PASSWORD`, en Supabase. El reporte incluye `status`, `update` e `history`.

Para Supabase se usa la cadena del *Session pooler* (Project Settings → Database), en formato JDBC:
`jdbc:postgresql://aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require`, con el usuario
`postgres.<id-del-proyecto>`.

## Copias de seguridad (`respaldo.yml`)

- **Frecuencia:** completa cada domingo a las 06:00 UTC y a pedido (*Run workflow*).
- **Alcance:** las tablas de Supabase y todas las colecciones, prefijos y tablas de los motores guardados.
- **Protección:** el archivo se cifra con Fernet (`ENCRYPTION_KEY`) y se guarda 30 días como artefacto.
- **Reporte:** registros por recurso, tamaño, SHA-256 y duración.
- **Restauración:** `python scripts/respaldo.py --descifrar respaldo_AAAAMMDD_HHMM.zip.enc`.

## Release y despliegue (`release.yml`)

Al publicar una etiqueta `vX.Y.Z` (o con *Run workflow*): pruebas → Release de GitHub con el paquete de
la aplicación → migración con Liquibase → verificación de la app desplegada en Streamlit Community Cloud.

## Documentación del README (`readme.yml`)

`scripts/generar_readme.py` regenera en el README el diccionario de datos y los diagramas entidad-relación,
de clases, de componentes y de despliegue cada vez que cambia el código o el esquema.
