# Despliegue y automatización

El proyecto se publica y documenta de forma automática a partir del repositorio git.

```text
git push (main) ──┬──► Streamlit Community Cloud ──► https://motor-integridad.streamlit.app/
                  └──► GitHub Actions ──► pruebas ► diagramas ► API ► manual ──► GitHub Pages / artefacto
```

## Aplicación en Streamlit Community Cloud

1. En [share.streamlit.io](https://share.streamlit.io) se crea la app desde el repositorio (rama `main`).
2. **Main file path:** `vista/app.py` · **Python:** 3.12.
3. En **Secrets** se pegan `SUPABASE_URL`, `SUPABASE_KEY` y `ENCRYPTION_KEY`
   (plantilla en `.streamlit/secrets.toml.example`).
4. Cada *push* a `main` redespliega la aplicación automáticamente.

Los servicios de MongoDB Atlas, Upstash y DataStax Astra deben aceptar conexiones desde cualquier IP
(`0.0.0.0/0`), porque Streamlit Cloud no tiene una IP fija.

## Flujo de GitHub Actions

Archivo: `.github/workflows/documentacion.yml`. Se ejecuta en cada *push* a `main` y manualmente
(*Run workflow*).

| Paso | Herramienta | Resultado |
|---|---|---|
| Pruebas unitarias | pytest | Falla el flujo si alguna prueba no pasa |
| Diagramas desde el código | pyreverse (pylint) | `classes_MotorIntegridad` y `packages_MotorIntegridad` |
| Diagramas UML del SRS y SAD | PlantUML + Graphviz | PNG y SVG de `docs/diagramas/*.puml` |
| Referencia de la API | pdoc | HTML de los paquetes `modelo` y `controlador` |
| Manual técnico y de usuario | MkDocs Material | Sitio web en `build/site` |
| Publicación | GitHub Pages / artefacto | Sitio público y ZIP descargable `documentacion-tecnica` |

El script `scripts/generar_documentacion.py` realiza la generación y puede ejecutarse también en local
(requiere Java, Graphviz, `plantuml.jar` y `pip install -r requirements-docs.txt`).

## Habilitar GitHub Pages (una sola vez)

En el repositorio: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Si Pages no está
disponible (por ejemplo, en repositorios privados sin plan que lo permita), la documentación igual queda en la
pestaña **Actions → (ejecución) → Artifacts → documentacion-tecnica**.
