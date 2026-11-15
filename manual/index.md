# Motor de Integridad Multibase NoSQL

Aplicación web que impone reglas de **esquema**, **unicidad**, **integridad referencial** y **consistencia** sobre
bases de datos NoSQL que no las soportan de forma nativa: **MongoDB**, **Redis** y **Apache Cassandra**.

- **Aplicación desplegada:** <https://motor-integridad.streamlit.app/>
- **Curso:** Base de Datos II · Universidad Privada de Tacna · 2026-II
- **Equipo (Datastack):** Keyla Noelia Lopez Ojeda y Adrian Fabricio Salas Acuña
- **Cliente (caso de estudio):** CloudNexus S.A.C.

!!! info "Documentación generada automáticamente"
    Este sitio se construye en cada *push* a la rama `main` mediante GitHub Actions: se ejecutan las pruebas,
    se generan los diagramas UML desde el código y desde sus fuentes PlantUML, se extrae la referencia de la API
    con pdoc y se publica el manual con MkDocs.

## Contenido

| Sección | Descripción |
|---|---|
| [Arquitectura](arquitectura.md) | Capas, componentes, modelo de datos y decisiones de diseño |
| [Instalación y configuración](instalacion.md) | Requisitos, variables de entorno, Supabase y ejecución local |
| [Despliegue y automatización](despliegue.md) | Streamlit Community Cloud y el flujo de GitHub Actions |
| [Pruebas](pruebas.md) | Pruebas unitarias y conjunto de datos de prueba |
| [Integraciones y CLI](integraciones.md) | CLI `motor`, reporte Excel (Office), Issues de GitHub, sesiones, caché, logs y telemetría |
| [Manual de usuario](usuario.md) | Uso de cada módulo de la aplicación |
| [Diagramas](diagramas.md) | Diagramas UML del SRS y del SAD, y los extraídos del código |
| [Referencia del código](api/index.html) | Clases, métodos y propiedades de `modelo` (incluidos adaptadores e integraciones), `controlador` y `motor_cli` |

## Informes del proyecto

Los informes de la Semana 1, FD01 (Factibilidad), FD02 (Visión), FD03 (SRS), FD04 (SAD), FD05 (Informe Final),
el Diccionario de Datos y el Estándar de Programación se encuentran en la carpeta `docs/informes/` del
repositorio, en formato Word y PDF. Las versiones de la Unidad 1 se conservan en `docs/informes/unidad1/`.
