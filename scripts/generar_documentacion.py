"""Genera la documentación técnica del proyecto a partir del repositorio.

1. Diagramas de clases y paquetes extraídos del código fuente (pyreverse).
2. Diagramas UML del SRS y del SAD a partir de sus fuentes PlantUML (docs/diagramas).
3. Galería de diagramas para el manual (manual/diagramas.md).
4. Referencia de la API del código (pdoc).
5. Sitio web del manual técnico (MkDocs) en build/site.

Uso: python scripts/generar_documentacion.py   (requiere Java y la variable PLANTUML_JAR)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "build"
FUENTES_UML = RAIZ / "docs" / "diagramas"
DIAGRAMAS_CODIGO = BUILD / "diagramas_codigo"
MANUAL = RAIZ / "manual"
SALIDA_DIAGRAMAS = MANUAL / "diagramas"
JAR = os.environ.get("PLANTUML_JAR", str(RAIZ / "plantuml.jar"))

TITULOS = {
    "classes_MotorIntegridad": "Clases extraídas del código (pyreverse)",
    "packages_MotorIntegridad": "Paquetes y dependencias extraídos del código (pyreverse)",
    "srs_organigrama": "SRS · Organigrama de CloudNexus",
    "srs_proceso_actual": "SRS · Proceso actual",
    "srs_proceso_propuesto": "SRS · Proceso propuesto",
    "srs_paquetes": "SRS · Diagrama de paquetes",
    "srs_casos_uso": "SRS · Casos de uso",
    "srs_act_obj_escaneo": "SRS · Actividades con objetos: escaneo por lotes",
    "srs_act_obj_validacion": "SRS · Actividades con objetos: validación previa",
    "srs_sec_login": "SRS · Secuencia: iniciar sesión",
    "srs_sec_regla": "SRS · Secuencia: gestionar reglas",
    "srs_sec_validacion": "SRS · Secuencia: validar registro",
    "srs_sec_escaneo": "SRS · Secuencia: escaneo por lotes",
    "srs_clases": "SRS · Clases del dominio",
    "sad_4mas1": "SAD · Modelo de vistas 4+1",
    "sad_casos_uso": "SAD · Casos de uso por subsistema",
    "sad_subsistemas": "SAD · Subsistemas por capas",
    "sad_sec_escaneo": "SAD · Secuencia de diseño: escaneo por lotes",
    "sad_sec_conexion": "SAD · Secuencia de diseño: conexión cifrada",
    "sad_colaboracion": "SAD · Colaboración del escaneo",
    "sad_objetos": "SAD · Objetos con el conjunto de prueba",
    "sad_clases": "SAD · Clases de diseño",
    "sad_bd_relacional": "SAD · Modelo relacional (Supabase)",
    "sad_bd_nosql": "SAD · Modelo NoSQL y reglas de integridad",
    "sad_arq_paquetes": "SAD · Paquetes del repositorio",
    "sad_componentes": "SAD · Componentes",
    "sad_actividad": "SAD · Actividades del sistema",
    "sad_despliegue": "SAD · Despliegue",
}


def ejecutar(*cmd, cwd=RAIZ):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def diagramas_desde_codigo():
    DIAGRAMAS_CODIGO.mkdir(parents=True, exist_ok=True)
    ejecutar("pyreverse", "-o", "puml", "-p", "MotorIntegridad", "--colorized", "-d", DIAGRAMAS_CODIGO,
             "modelo", "controlador")


def renderizar_plantuml():
    if SALIDA_DIAGRAMAS.exists():
        shutil.rmtree(SALIDA_DIAGRAMAS)
    SALIDA_DIAGRAMAS.mkdir(parents=True)
    fuentes = sorted(FUENTES_UML.glob("*.puml")) + sorted(DIAGRAMAS_CODIGO.glob("*.puml"))
    for formato in ("-tpng", "-tsvg"):
        ejecutar("java", "-jar", JAR, "-charset", "UTF-8", formato, "-o", SALIDA_DIAGRAMAS, *fuentes)
    return fuentes


def galeria(fuentes):
    lineas = ["# Diagramas", "",
              "Diagramas generados automáticamente en cada *push*: los de clases y paquetes se extraen del código "
              "fuente con pyreverse y el resto se compila desde sus fuentes PlantUML en `docs/diagramas/`.", ""]
    for f in fuentes:
        nombre = f.stem
        titulo = TITULOS.get(nombre, nombre.replace("_", " ").capitalize())
        lineas += [f"## {titulo}", "", f"[![{titulo}](diagramas/{nombre}.png)](diagramas/{nombre}.svg)", "",
                   f"Fuente: `{f.relative_to(RAIZ).as_posix()}` · [SVG](diagramas/{nombre}.svg)", ""]
    (MANUAL / "diagramas.md").write_text("\n".join(lineas), encoding="utf-8")


def referencia_api():
    ejecutar(sys.executable, "-m", "pdoc", "modelo", "controlador", "-o", BUILD / "api", "--docformat", "google")


def sitio():
    ejecutar(sys.executable, "-m", "mkdocs", "build", "--clean", "-d", BUILD / "site")
    shutil.copytree(BUILD / "api", BUILD / "site" / "api", dirs_exist_ok=True)


if __name__ == "__main__":
    BUILD.mkdir(exist_ok=True)
    diagramas_desde_codigo()
    galeria(renderizar_plantuml())
    referencia_api()
    sitio()
    print("Documentación generada en", BUILD / "site")
