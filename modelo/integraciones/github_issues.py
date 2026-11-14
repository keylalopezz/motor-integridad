"""Integración con GitHub: publica las anomalías de un escaneo como un Issue del repositorio.

Usa la API REST de GitHub (``POST /repos/{owner}/{repo}/issues``) con un token:

- en GitHub Actions, el ``GITHUB_TOKEN`` automático del flujo (variables ``GITHUB_TOKEN`` y
  ``GITHUB_REPOSITORY``), sin configurar nada más;
- en la aplicación web o la CLI, el token y el repositorio que cada usuario guarda cifrados en
  «Bases de Datos → GitHub» (un *fine-grained token* con permiso *Issues: Read and write*).
"""

import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..descripcion_anomalias import TIPOS, describir, resumen_por_tipo
from ..registro_logs import obtener_logger

log = obtener_logger("github")

API = "https://api.github.com"
REPO_VALIDO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
MAX_FILAS = 50
ETIQUETAS = ["integridad-de-datos"]


class ErrorGitHub(Exception):
    """Error al comunicarse con GitHub, con un mensaje comprensible para el usuario."""

    def __init__(self, mensaje: str, codigo: Optional[int] = None):
        super().__init__(mensaje)
        self.codigo = codigo


def _mensaje_error(codigo: int, repo: str) -> str:
    """Traduce el código HTTP de la API de GitHub a un mensaje en español."""
    return {
        401: "El token de GitHub no es válido o expiró.",
        403: f"El token no tiene permiso para crear Issues en {repo} (se requiere «Issues: Read and write»).",
        404: f"No se encontró el repositorio {repo} o el token no tiene acceso a él.",
        410: f"El repositorio {repo} tiene los Issues desactivados (Settings → Features → Issues).",
        422: "GitHub rechazó los datos del Issue.",
    }.get(codigo, f"GitHub respondió con el código HTTP {codigo}.")


class IntegracionGitHub:
    """Cliente mínimo de la API de GitHub para un repositorio ``owner/repo``."""

    def __init__(self, token: str, repo: str, api: str = API, timeout: float = 20):
        repo = (repo or "").strip().removeprefix("https://github.com/").strip("/")
        if not REPO_VALIDO.fullmatch(repo):
            raise ErrorGitHub("El repositorio debe tener el formato propietario/nombre (por ejemplo, keylalopezz/motor-integridad).")
        if not token:
            raise ErrorGitHub("Falta el token de GitHub.")
        self.token, self.repo, self.api, self.timeout = token.strip(), repo, api.rstrip("/"), timeout

    def _peticion(self, metodo: str, ruta: str, cuerpo: Optional[Dict] = None) -> Dict[str, Any]:
        """Envía la petición a la API y devuelve el JSON de respuesta."""
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        req = urllib.request.Request(f"{self.api}{ruta}", data=datos, method=metodo, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "motor-integridad",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raise ErrorGitHub(_mensaje_error(e.code, self.repo), e.code) from e
        except urllib.error.URLError as e:
            raise ErrorGitHub(f"No se pudo conectar con GitHub: {e.reason}") from e

    def verificar(self) -> Dict[str, Any]:
        """Comprueba el token y el repositorio; devuelve ``nombre``, ``url`` e ``issues`` (activados o no)."""
        datos = self._peticion("GET", f"/repos/{self.repo}")
        return {"nombre": datos.get("full_name", self.repo), "url": datos.get("html_url", ""),
                "issues": bool(datos.get("has_issues", True))}

    def crear_issue(self, titulo: str, cuerpo: str, etiquetas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Crea el Issue y devuelve su ``numero`` y ``url``."""
        issue = {"title": titulo, "body": cuerpo, "labels": etiquetas or ETIQUETAS}
        try:
            datos = self._peticion("POST", f"/repos/{self.repo}/issues", issue)
        except ErrorGitHub as e:
            if e.codigo != 422:
                raise
            # Sin permiso para crear la etiqueta: se publica el Issue sin etiquetas
            issue.pop("labels")
            datos = self._peticion("POST", f"/repos/{self.repo}/issues", issue)
        log.info("Issue #%s creado en %s", datos.get("number"), self.repo)
        return {"numero": datos.get("number"), "url": datos.get("html_url", "")}


def _celda(texto: Any) -> str:
    """Escapa un valor para una celda de tabla Markdown."""
    return str(texto).replace("|", "\\|").replace("\n", " ")


def construir_issue(violaciones: List[Dict], errores: Optional[List[str]] = None, usuario: str = "",
                    origen: str = "Motor de Integridad", reglas: Optional[Dict[str, Dict]] = None) -> Tuple[str, str]:
    """Arma el título y el cuerpo (Markdown) del Issue con el resumen y el detalle de las anomalías."""
    errores, reglas = errores or [], reglas or {}
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    titulo = (f"⚠️ {len(violaciones)} anomalía(s) de integridad detectadas · {fecha} UTC" if violaciones
              else f"✅ Escaneo sin anomalías · {fecha} UTC")

    lineas = [f"Reporte generado automáticamente por el **Motor de Integridad Multibase NoSQL** ({origen}).", "",
              f"- **Usuario:** `{usuario or 'N/D'}`", f"- **Fecha:** {fecha} UTC",
              f"- **Anomalías:** {len(violaciones)}", f"- **Reglas que no se pudieron evaluar:** {len(errores)}", "",
              "### Resumen por tipo de regla", "", "| Tipo | Anomalías |", "|---|---:|"]
    lineas += [f"| {TIPOS[t]['icono']} {TIPOS[t]['titulo']} | {n} |" for t, n in resumen_por_tipo(violaciones).items() if t in TIPOS]

    motores = Counter(str(v.get("motores_involucrados") or "N/D") for v in violaciones)
    if motores:
        lineas += ["", "### Motores involucrados", "", "| Motores | Anomalías |", "|---|---:|"]
        lineas += [f"| {_celda(m)} | {n} |" for m, n in motores.most_common()]

    if violaciones:
        lineas += ["", "### Detalle", "", "| # | Tipo | Motores | Colección | Registro | Sugerencia |", "|---:|---|---|---|---|---|"]
        for n, v in enumerate(violaciones[:MAX_FILAS], start=1):
            d = describir(v)
            regla = v.get("reglas") or reglas.get(str(v.get("regla_id")), {}) or {}
            lineas.append(f"| {n} | {d['icono']} {_celda(d['titulo'])} | {_celda(d['motores'])} | "
                          f"{_celda(regla.get('coleccion_origen', ''))} | `{_celda(d['id'])}` | {_celda(d['sugerencia'])} |")
        if len(violaciones) > MAX_FILAS:
            lineas += ["", f"> Se muestran {MAX_FILAS} de {len(violaciones)} anomalías. "
                           "El detalle completo está en el reporte Excel del Motor de Integridad."]
    if errores:
        lineas += ["", "### Reglas no evaluadas", ""] + [f"- {_celda(e)}" for e in errores]
    lineas += ["", "---", "_Cierra este Issue cuando las anomalías estén corregidas y un nuevo escaneo lo confirme._"]
    return titulo, "\n".join(lineas)


def configuracion_github(usuario: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Token y repositorio a usar: los de GitHub Actions si existen, si no los guardados por ``usuario``."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if token and repo:
        return {"GITHUB_TOKEN": token, "GITHUB_REPO": repo}
    if usuario:
        from ..gestor_conexiones import GestorConexiones
        config = GestorConexiones(usuario).obtener_conexion("github")
        if config and config.get("GITHUB_TOKEN") and config.get("GITHUB_REPO"):
            return config
    return None


def publicar_anomalias(violaciones: List[Dict], errores: Optional[List[str]] = None, usuario: str = "",
                       origen: str = "Motor de Integridad", reglas: Optional[Dict[str, Dict]] = None,
                       config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Crea el Issue con las anomalías usando ``config`` o la configuración disponible para ``usuario``."""
    config = config or configuracion_github(usuario)
    if not config:
        raise ErrorGitHub("GitHub no está configurado: guarda el token y el repositorio en «Bases de Datos → GitHub».")
    titulo, cuerpo = construir_issue(violaciones, errores, usuario, origen, reglas)
    return IntegracionGitHub(config["GITHUB_TOKEN"], config["GITHUB_REPO"]).crear_issue(titulo, cuerpo)
