# Motor de Integridad Multibase NoSQL

Este proyecto es un **Motor de Integridad** dinámico y versátil que permite imponer reglas de integridad (esquema, unicidad, referencial y consistencia) sobre múltiples bases de datos NoSQL que no soportan estas restricciones nativamente (MongoDB, Redis, Cassandra).

A diferencia de sistemas estáticos, este motor está diseñado para ser **agnóstico de infraestructura**: los usuarios pueden conectar dinámicamente sus propias bases de datos NoSQL alojadas en la nube (ej. MongoDB Atlas, Upstash, Datastax Astra) directamente desde la interfaz de usuario, haciendo de este sistema una herramienta versátil y lista para producción.

## Arquitectura

El sistema sigue el patrón **MVC (Modelo-Vista-Controlador)**:

- **Vista**: Aplicación interactiva construida en **Streamlit**. Permite a los usuarios iniciar sesión, configurar las credenciales de sus bases de datos en la nube, definir reglas y visualizar el tablero de violaciones.
- **Modelo**: Contiene el motor de reglas, el validador, verificador batch, el registro de auditoría y los adaptadores de conexión a los motores NoSQL.
- **Controlador**: Orquesta las peticiones de la Vista interactuando con el Modelo.
- **Control-plane**: Utiliza **Supabase** (PostgreSQL) para almacenar la configuración de conexiones de los usuarios, las reglas de integridad y el historial de auditoría de manera centralizada.

## Funcionalidades Principales

1. **Configuración Dinámica (Cloud-Native)**: Conecta tus propias bases de datos MongoDB, Redis y Cassandra desde la interfaz web, sin necesidad de tocar código ni archivos de configuración locales.
2. **Validación de Esquema**: Rechaza documentos que no cumplan con el JSON Schema estipulado.
3. **Control de Unicidad**: Evita datos duplicados en colecciones NoSQL.
4. **Integridad Referencial Inter-Base**: Asegura que una referencia en un motor (ej. Cassandra) exista en otro motor (ej. MongoDB).
5. **Consistencia de Datos**: Detecta desincronizaciones entre datos replicados en distintos motores.
6. **Dashboard de Auditoría**: Visualiza todas las violaciones de integridad detectadas en tiempo real.

## Requisitos Previos

- Python 3.11+
- Proyecto en [Supabase](https://supabase.com/) (para el control-plane).

## Configuración e Instalación

### 1. Clonar e Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Supabase

1. Crea un proyecto en Supabase.
2. Ejecuta el script `supabase_schema.sql` en el SQL Editor de tu proyecto en Supabase para crear las tablas necesarias (`reglas`, `auditoria_violaciones`, `conexiones_motores`, `usuarios_sistema`).
   - Si tu proyecto ya tiene datos, ejecuta en su lugar `supabase_migracion_seguridad.sql` (activa RLS sin borrar nada).
3. Renombra `.env.example` a `.env` y completa:

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=tu_service_role_key   # Project Settings > API > service_role
ENCRYPTION_KEY=clave_fernet         # cifra las credenciales de los motores
```

Genera la `ENCRYPTION_KEY` con:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Ejecutar la Aplicación

Inicia la interfaz de usuario con Streamlit:

```bash
streamlit run vista/app.py
```

### 4. Pruebas

```bash
pytest
```

### 5. Verificar conexiones

```bash
python verificar_conexiones.py            # Supabase, ENCRYPTION_KEY y motores con credenciales en .env
python verificar_conexiones.py <usuario>  # motores que ese usuario guardó en la app
```

## Despliegue en Streamlit Community Cloud

1. Sube el proyecto a un repositorio de GitHub (el `.gitignore` excluye `.env`).
2. En [share.streamlit.io](https://share.streamlit.io) pulsa **Create app** y elige el repositorio.
3. **Main file path:** `vista/app.py`. En *Advanced settings* elige Python 3.12.
4. En **Secrets** pega el contenido de `.streamlit/secrets.toml.example` con tus valores reales.
5. Deploy. Las bases MongoDB Atlas / Upstash / Astra deben aceptar conexiones desde cualquier IP (`0.0.0.0/0`).

## Uso del Sistema

1. **Autenticación**: Inicia sesión en la aplicación web.
2. **Conexiones**: Ve a la pestaña de "Conexiones" y registra las URIs/credenciales de tus bases de datos NoSQL alojadas en la nube.
3. **Reglas**: Define reglas de esquema, unicidad, o referenciales entre las bases configuradas.
4. **Verificación**: Ejecuta el validador para detectar inconsistencias en tus datos en la nube.
5. **Dashboard**: Revisa el reporte de las violaciones de integridad detectadas.

## Estructura del Proyecto

```text
motor-integridad/
├── .env                # Credenciales del control-plane (Supabase)
├── requirements.txt    # Dependencias del proyecto
├── supabase_schema.sql # Esquema SQL para inicializar Supabase
├── supabase_migracion_seguridad.sql # Activa RLS en proyectos existentes
├── tests/              # Pruebas unitarias (pytest)
├── README.md           # Documentación del proyecto
├── modelo/             # Lógica de negocio, adaptadores y motor
├── controlador/        # Orquestadores entre Vista y Modelo
└── vista/              # Interfaz gráfica en Streamlit
```