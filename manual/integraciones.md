# Integraciones, CLI y características no funcionales

El Motor de Integridad se integra con **tres herramientas externas**. Las tres usan el mismo modelo (`modelo/`) y
los mismos datos en la nube que la aplicación web:

| # | Herramienta | Qué hace | Dónde se usa |
|---|---|---|---|
| 1 | **CLI** (`motor`) | Valida registros y ejecuta escaneos desde la terminal o desde una automatización | Terminal, scripts, GitHub Actions |
| 2 | **Microsoft Office (Excel)** | Exporta el reporte de anomalías a un libro `.xlsx` con hoja de resumen y tabla filtrable | Página *Reportes*, `motor ... --excel` |
| 3 | **GitHub (Issues)** | Publica las anomalías de un escaneo como un Issue del repositorio | Página *Reportes*, página *Ejecución*, `motor ... --github-issue` |

```text
GitHub Actions (semanal o manual) ──► motor demo / motor escanear ──► reporte Excel (Office)
                                                                  └──► Issue con las anomalías (GitHub)
```

!!! tip "Cómo verificarlo sin cuentas"
    Ejecuta `motor demo` (ver abajo) o abre **Actions → Integraciones (CLI, Excel y GitHub) → Run workflow** en el
    repositorio: el flujo instala la CLI con `pip`, ejecuta el conjunto de prueba, guarda el Excel como artefacto y
    crea un Issue real en la pestaña **Issues** usando el token automático de GitHub Actions.

## 1. CLI `motor`

### Instalación

```bash
# Desde el repositorio publicado
pip install "git+https://github.com/keylalopezz/motor-integridad.git"

# O desde una copia local del repositorio
pip install .

motor --help
```

Sin instalar, desde la raíz del repositorio: `python -m motor_cli --help`.

### Comandos

| Comando | Qué hace | ¿Necesita cuenta? |
|---|---|---|
| `motor demo` | Escanea el conjunto de prueba de los informes (MongoDB, Redis y Cassandra simulados en memoria) con 7 reglas; detecta las 7 violaciones inyectadas | No |
| `motor validar ARCHIVO --esquema ESQUEMA` | Valida uno o varios registros JSON contra un JSON Schema | No |
| `motor validar ARCHIVO --motor M --coleccion C` | Valida con tus reglas de esquema y unicidad guardadas (simulador previo a la escritura) | Sí |
| `motor reglas` | Lista tus reglas activas | Sí |
| `motor escanear` | Escaneo por lotes de todas tus reglas sobre tus bases de datos (igual que «Iniciar Escaneo Profundo») | Sí |
| `motor reporte` | Muestra las anomalías ya registradas sin volver a escanear | Sí |

Opciones de `demo`, `escanear` y `reporte`:

| Opción | Efecto |
|---|---|
| `--excel archivo.xlsx` | Guarda el reporte en Excel (integración con Office) |
| `--github-issue` | Publica las anomalías como Issue de GitHub |
| `--repo propietario/repo` | Repositorio del Issue (por defecto, el configurado) |
| `--json` | Salida en JSON para otros programas |
| `--estricto` | Termina con código 1 si hay anomalías (para detener un pipeline de CI) |

Códigos de salida: `0` correcto · `1` registros inválidos o anomalías (con `--estricto`) · `2` error de uso o de
configuración · `3` error de conexión.

### Ejemplos

```bash
motor demo
motor demo --excel reporte_demo.xlsx

motor validar ejemplos/registro_valido.json   --esquema ejemplos/esquema_usuario.json   # ✅ código 0
motor validar ejemplos/registros_lote.json    --esquema ejemplos/esquema_usuario.json   # ❌ código 1
```

Salida de `motor validar ejemplos/registros_lote.json --esquema ejemplos/esquema_usuario.json`:

```text
✅ Registro 1 (U010): válido — Cumple el esquema.
❌ Registro 2 (U011): inválido — 'email' is a required property; edad: -5 is less than the minimum of 0; estado: 'suspendido' is not one of ['activo', 'inactivo']
❌ Registro 3 (U012): inválido — edad: 'veinte' is not of type 'integer'

1 válido(s), 2 inválido(s).
```

### Comandos con cuenta

Leen la configuración del archivo `.env` del directorio actual (o de variables de entorno):

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=...
ENCRYPTION_KEY=...
MOTOR_USUARIO=tu_usuario      # opcional: también se puede usar --usuario
MOTOR_PASSWORD=...            # opcional: si falta, la CLI la pide sin mostrarla
```

```bash
motor reglas --usuario ana
motor validar registro.json --motor mongodb --coleccion usuarios --usuario ana
motor escanear --usuario ana --excel reporte.xlsx --github-issue
```

Las acciones de la CLI se registran en la telemetría con `origen = cli` y aparecen en el Dashboard.

## 2. Microsoft Office: reporte Excel

El libro `reporte_anomalias.xlsx` (`modelo/integraciones/excel.py`, biblioteca openpyxl) contiene:

- **Resumen:** usuario, origen, fecha y total; anomalías por tipo de regla y por motores involucrados.
- **Anomalías:** una fila por anomalía (tipo, motores, colección, campo, registro, explicación, sugerencia de
  corrección, fecha y el dato afectado en JSON) como **tabla de Excel con filtros**.

Se descarga desde **Reportes → 📊 Descargar Excel (Office)** o con `--excel` en la CLI.

## 3. GitHub: Issues de anomalías

`modelo/integraciones/github_issues.py` usa la API REST de GitHub (`POST /repos/{owner}/{repo}/issues`). El Issue
incluye el resumen por tipo y por motor, la tabla de anomalías (hasta 50) con su sugerencia, y las reglas que no
se pudieron evaluar. Lleva la etiqueta `integridad-de-datos`.

| Contexto | Token y repositorio |
|---|---|
| GitHub Actions | `GITHUB_TOKEN` automático del flujo y `GITHUB_REPOSITORY` (sin configuración) |
| Aplicación web y CLI | Los guardados por el usuario en **Bases de Datos → GitHub (integración)**, cifrados con Fernet |

Para crear el token: *GitHub → Settings → Developer settings → Fine-grained tokens*, con acceso al repositorio y
permiso **Issues: Read and write**.

## 4. Características no funcionales

| Característica | Implementación | Dónde verlo |
|---|---|---|
| **Sesiones** | `st.session_state` por usuario; expiran tras `SESION_MINUTOS` (30) sin actividad; inicio, cierre y expiración se registran con su duración | Barra lateral (tiempo de sesión), Dashboard |
| **Historiales** | Auditoría de violaciones (`auditoria_violaciones`) e historial de escaneos con origen, anomalías y duración (`eventos_uso`) | Reportes, Ejecución → *Historial de escaneos* |
| **Caché** | `st.cache_data` (60 s, por usuario) para reglas, anomalías, conexiones y métricas; se invalida al crear, eliminar o escanear. La actividad de «Comunidad» se escribe como máximo una vez por minuto | `vista/cache.py` |
| **Logs** | Módulo `logging` (`modelo/registro_logs.py`): consola, archivo rotativo `logs/motor.log` y búfer en memoria; nivel con `LOG_LEVEL` | Monitor → *Logs de tu actividad* |
| **Telemetría** | Tabla `eventos_uso`: cada acción con su detalle (duración en ms, origen web/CLI, anomalías por tipo) | Dashboard → *Utilización del producto* y *Telemetría de rendimiento* |

## 5. Disponibilidad: servicios siempre activos

Los planes gratuitos suspenden los servicios sin uso (Supabase se pausa a los ~7 días, Astra hiberna y Streamlit
duerme la app). El flujo **Mantener activos los servicios** (`mantener-activo.yml`, cada 4 horas) ejecuta
`scripts/mantener_activo.py`, que:

1. consulta Supabase;
2. hace *ping* a MongoDB Atlas, Upstash Redis y DataStax Astra con las conexiones guardadas de `MOTOR_USUARIO`
   (con reintentos para dar tiempo a que un motor se reanude);
3. abre la aplicación con un navegador sin interfaz y pulsa **«Yes, get this app back up!»** si estaba dormida.

Si un servicio no responde, el flujo falla y GitHub avisa por correo para reactivarlo desde el panel del proveedor.

!!! note "Si la aplicación aparece dormida"
    Pulsa **«Yes, get this app back up!»** en <https://motor-integridad.streamlit.app/>; vuelve a estar disponible en
    aproximadamente un minuto.
