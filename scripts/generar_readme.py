"""Genera la documentación del README.md a partir del código y de los changelogs de Liquibase.

Secciones generadas (diagramas en Mermaid, que GitHub muestra como imagen):
  - Diccionario de datos (tablas de liquibase/changelog/*.sql y colecciones NoSQL del caso).
  - Diagrama entidad-relación.
  - Diagrama de clases (extraído con ``ast`` de modelo/ y controlador/).
  - Diagrama de componentes y diagrama de despliegue.

Solo se reemplaza el bloque entre los marcadores AUTO-DOC; el resto del README se conserva.
Uso: python scripts/generar_readme.py
"""
import ast
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
README = RAIZ / "README.md"
INICIO, FIN = "<!-- AUTO-DOC:INICIO -->", "<!-- AUTO-DOC:FIN -->"

DESCRIPCIONES = {
    "usuarios_sistema": "Cuentas de acceso a la plataforma",
    "reglas": "Reglas de integridad definidas por cada usuario",
    "auditoria_violaciones": "Anomalías detectadas por la validación y el escaneo batch",
    "conexiones_motores": "Credenciales cifradas de cada motor NoSQL por usuario",
    "eventos_uso": "Eventos de utilización del producto (dashboard de uso)",
    "id": "Identificador único",
    "usuario": "Nombre del usuario propietario",
    "password_hash": "Contraseña cifrada con bcrypt",
    "creado_en": "Fecha y hora de creación",
    "ultimo_acceso": "Última actividad del usuario",
    "tipo": "Tipo de regla: esquema, unicidad, referencial o consistencia",
    "motor_origen": "Motor donde se evalúa la regla",
    "coleccion_origen": "Colección, prefijo o tabla evaluada",
    "campo": "Campo evaluado o de cruce",
    "motor_destino": "Motor de referencia (reglas entre motores)",
    "coleccion_destino": "Colección de referencia",
    "campo_destino": "Campo de referencia",
    "schema": "JSON Schema de la regla de esquema",
    "regla_id": "Regla incumplida",
    "motores_involucrados": "Motores donde se detectó la anomalía",
    "dato_afectado": "Registro que incumple la regla",
    "detectado_en": "Fecha y hora de detección",
    "motor": "mongodb, redis o cassandra",
    "config": "Credenciales cifradas con Fernet",
    "actualizado_en": "Fecha de la última actualización",
    "accion": "login, registro, conexion, regla, validacion o escaneo",
    "detalle": "Datos adicionales del evento",
}

NOSQL = [
    ("MongoDB Atlas", "tienda.usuarios", "_id, nombre, email, edad", "Clientes de la tienda (caso de estudio)"),
    ("MongoDB Atlas", "tienda.pedidos", "_id, usuario_id, total, estado", "Pedidos; usuario_id → usuarios._id"),
    ("Upstash Redis", "usuarios:&lt;id&gt; / pedidos:&lt;id&gt;", "JSON o hash con los mismos campos", "Réplica en caché de usuarios y pedidos"),
    ("DataStax Astra", "tienda.pagos", "id, pedido_id, monto, transaccion", "Pagos; pedido_id → pedidos._id"),
]


def leer_tablas():
    """Extrae tablas, columnas y llaves foráneas de los changelogs SQL de Liquibase."""
    tablas = {}
    for archivo in sorted((RAIZ / "liquibase" / "changelog").glob("*.sql")):
        sql = archivo.read_text(encoding="utf-8")
        for nombre, cuerpo in re.findall(r"create table if not exists (\w+) \((.*?)\n\);", sql, re.S):
            columnas, pk_compuesta = [], []
            for linea in [l.strip().rstrip(",") for l in cuerpo.strip().splitlines()]:
                if linea.startswith("primary key"):
                    pk_compuesta = [c.strip() for c in linea[linea.index("(") + 1:-1].split(",")]
                    continue
                partes = linea.split()
                restricciones = " ".join(partes[2:])
                ref = re.search(r"references (\w+)\((\w+)\)", linea)
                columnas.append({"nombre": partes[0], "tipo": partes[1], "restr": restricciones,
                                 "pk": "primary key" in linea, "fk": ref.groups() if ref else None})
            for c in columnas:
                c["pk"] = c["pk"] or c["nombre"] in pk_compuesta
            tablas[nombre] = columnas
    return tablas


def diccionario(tablas) -> str:
    """Tablas Markdown del diccionario de datos."""
    partes = ["### Diccionario de datos", "", "**Base de control (Supabase / PostgreSQL)**", ""]
    for tabla, columnas in tablas.items():
        partes += [f"#### `{tabla}`", "", DESCRIPCIONES.get(tabla, ""), "",
                   "| Columna | Tipo | Llave | Restricciones | Descripción |", "|---|---|---|---|---|"]
        for c in columnas:
            llave = "PK" if c["pk"] else ("FK → " + ".".join(c["fk"]) if c["fk"] else "")
            restr = re.sub(r"references \w+\(\w+\)", "", c["restr"]).replace("primary key", "").strip()
            partes.append(f"| `{c['nombre']}` | {c['tipo']} | {llave} | {restr.replace('|', '/')} | "
                          f"{DESCRIPCIONES.get(c['nombre'], '')} |")
        partes.append("")
    partes += ["**Motores NoSQL validados (caso de estudio)**", "",
               "| Motor | Colección / clave | Campos | Descripción |", "|---|---|---|---|"]
    partes += [f"| {m} | `{c}` | {f} | {d} |" for m, c, f, d in NOSQL]
    return "\n".join(partes)


def diagrama_er(tablas) -> str:
    """Diagrama entidad-relación en Mermaid."""
    lineas = ["### Diagrama entidad-relación", "", "```mermaid", "erDiagram"]
    for tabla, columnas in tablas.items():
        lineas.append(f"    {tabla} {{")
        for c in columnas:
            marca = " PK" if c["pk"] else (" FK" if c["fk"] else "")
            lineas.append(f"        {c['tipo'].split('(')[0]} {c['nombre']}{marca}")
        lineas.append("    }")
    for tabla, columnas in tablas.items():
        for c in columnas:
            if c["fk"]:
                lineas.append(f'    {c["fk"][0]} ||--o{{ {tabla} : "{c["nombre"]}"')
    lineas += ['    mongodb_usuarios ||--o{ mongodb_pedidos : "usuario_id"',
               '    mongodb_pedidos ||--o{ cassandra_pagos : "pedido_id"',
               '    mongodb_usuarios ||--|| redis_usuarios : "consistencia"', "```"]
    return "\n".join(lineas)


def diagrama_clases() -> str:
    """Diagrama de clases en Mermaid obtenido del código fuente."""
    lineas = ["### Diagrama de clases", "", "```mermaid", "classDiagram"]
    relaciones = []
    for archivo in sorted(list((RAIZ / "modelo").rglob("*.py")) + list((RAIZ / "controlador").glob("*.py"))):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in [n for n in arbol.body if isinstance(n, ast.ClassDef)]:
            lineas.append(f"    class {nodo.name} {{")
            atributos = set()
            for f in [n for n in nodo.body if isinstance(n, ast.FunctionDef)]:
                if f.name == "__init__":
                    for a in ast.walk(f):
                        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "self" \
                                and isinstance(a.ctx, ast.Store):
                            atributos.add(a.attr)
                        if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id[:1].isupper():
                            relaciones.append(f"    {nodo.name} --> {a.func.id}")
            lineas += [f"        -{a}" for a in sorted(atributos)]
            for f in [n for n in nodo.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]:
                args = ", ".join(a.arg for a in f.args.args if a.arg != "self")
                lineas.append(f"        +{f.name}({args})")
            lineas.append("    }")
            for base in nodo.bases:
                if isinstance(base, ast.Name) and base.id not in ("object",):
                    relaciones.append(f"    {base.id} <|-- {nodo.name}")
    lineas += sorted(set(r for r in relaciones if "SupabaseClient" not in r or "-->" in r)) + ["```"]
    return "\n".join(lineas)


def diagrama_componentes() -> str:
    """Diagrama de componentes en Mermaid a partir de las páginas y paquetes del proyecto."""
    paginas = sorted(p.stem.split("_", 1)[1] for p in (RAIZ / "vista" / "rutas").glob("*.py"))
    nodos = "\n".join(f"        P{i}[{p}]" for i, p in enumerate(paginas))
    return f"""### Diagrama de componentes

```mermaid
flowchart LR
    subgraph Vista["vista (Streamlit)"]
        APP[app.py / login.py]
{nodos}
    end
    subgraph Controlador["controlador"]
        CA[ControladorAuth]
        CR[ControladorReglas]
        CV[ControladorVerificacion]
        CP[ControladorReporte]
    end
    subgraph Modelo["modelo"]
        AU[Autenticacion]
        MR[MotorReglas]
        VA[Validador]
        VB[VerificadorBatch]
        LA[LogAuditoria]
        MU[MetricasUso]
        GC[GestorConexiones]
        AD[[Adaptadores Mongo / Redis / Cassandra]]
        SC[SupabaseClient]
    end
    Vista --> Controlador
    CA --> AU
    CR --> MR
    CV --> VA & VB
    CP --> LA
    Controlador --> MU
    VB --> AD
    VA --> AD
    AD --> GC
    AU & MR & LA & MU & GC --> SC
    SC --> SUPA[(Supabase)]
    AD --> MDB[(MongoDB Atlas)] & RDS[(Upstash Redis)] & CAS[(Astra Cassandra)]
```"""


def diagrama_despliegue() -> str:
    """Diagrama de despliegue en Mermaid."""
    return """### Diagrama de despliegue

```mermaid
flowchart TB
    U([Navegador del usuario]) -- HTTPS --> ST
    subgraph GH["GitHub"]
        REPO[Repositorio git]
        GA[GitHub Actions: pruebas, Terraform, Liquibase, respaldos, release, documentación]
        GP[GitHub Pages: manual técnico]
    end
    subgraph SC["Streamlit Community Cloud"]
        ST[App Streamlit · Python 3.12]
    end
    REPO -- push main --> ST
    REPO --> GA --> GP
    ST -- HTTPS / PostgREST --> SUPA[(Supabase PostgreSQL)]
    ST -- TLS / SRV --> MDB[(MongoDB Atlas M0)]
    ST -- TLS --> RDS[(Upstash Redis)]
    ST -- Secure Connect Bundle --> CAS[(DataStax Astra DB)]
    GA -- Terraform --> MDB & RDS & CAS & SUPA
    GA -- Liquibase --> SUPA
```"""


def main():
    tablas = leer_tablas()
    bloque = "\n\n".join([
        "## Documentación generada automáticamente",
        "> Sección generada por `scripts/generar_readme.py` (GitHub Actions). No editar a mano.",
        diccionario(tablas), diagrama_er(tablas), diagrama_clases(), diagrama_componentes(), diagrama_despliegue(),
    ])
    texto = README.read_text(encoding="utf-8") if README.exists() else ""
    nuevo = f"{INICIO}\n{bloque}\n{FIN}"
    if INICIO in texto and FIN in texto:
        texto = texto[:texto.index(INICIO)] + nuevo + texto[texto.index(FIN) + len(FIN):]
    else:
        texto = texto.rstrip() + "\n\n" + nuevo + "\n"
    README.write_text(texto, encoding="utf-8", newline="\n")
    print(f"README.md actualizado: {len(tablas)} tablas documentadas")


if __name__ == "__main__":
    main()
