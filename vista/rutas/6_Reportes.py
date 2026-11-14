import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modelo.descripcion_anomalias import describir
from modelo.integraciones.excel import MIME_XLSX, generar_excel
from modelo.integraciones.github_issues import ErrorGitHub, publicar_anomalias
from modelo.metricas_uso import MetricasUso
from vista import cache

st.title("📄 Reporte de Anomalías y Sugerencias")
st.markdown("Revisa en detalle cada una de las violaciones detectadas por el sistema y descubre cómo corregirlas.")

usuario = st.session_state.get("usuario")
try:
    violaciones = cache.violaciones(usuario)
    motores_conectados = cache.motores(usuario)
    repo_github = cache.github_configurado(usuario)
except Exception as e:
    st.error(f"❌ No se pudieron cargar los datos desde Supabase: {type(e).__name__}. Intenta recargar en unos segundos.")
    st.stop()

if motores_conectados:
    st.info(f"Bases de datos auditadas en tu último escaneo profundo: **{', '.join(motores_conectados).title()}**")

if "reporte_aviso" in st.session_state:
    st.success(st.session_state.pop("reporte_aviso"))


def generar_pdf(violaciones):
    """Reporte PDF con una sección por anomalía."""
    from fpdf import FPDF
    latin = lambda texto: str(texto).encode('latin-1', 'replace').decode('latin-1')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=16)
    pdf.cell(0, 10, "Reporte de Auditoria de Integridad", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    for idx, v in enumerate(violaciones):
        d = describir(v)
        pdf.set_font("helvetica", "B", size=12)
        pdf.cell(0, 10, latin(f"Anomalia #{idx + 1} - {d['titulo'].upper()} | Registro {d['id']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", size=10)
        pdf.multi_cell(0, 8, latin(f"Motores: {d['motores']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 8, latin(f"Que paso: {d['explicacion'].replace('`', '')}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 8, latin(f"Sugerencia: {d['sugerencia']}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 8, latin(f"Dato afectado: {v.get('dato_afectado', {})}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
    return bytes(pdf.output())


if not violaciones:
    st.success("🎉 ¡Excelente! No se ha detectado ninguna anomalía. Tus datos están completamente íntegros.")
else:
    st.warning(f"⚠️ Se detectaron {len(violaciones)} anomalía(s) en tu sistema.")

    st.markdown("#### Exportar e integrar")
    b1, b2, b3 = st.columns(3)
    if b1.download_button("📥 Descargar Reporte PDF", data=generar_pdf(violaciones), file_name="reporte_anomalias.pdf",
                          mime="application/pdf", width="stretch"):
        MetricasUso(usuario).registrar("reporte_pdf", {"anomalias": len(violaciones)})
    if b2.download_button("📊 Descargar Excel (Office)", data=generar_excel(violaciones, usuario=usuario, origen="Aplicación web"),
                          file_name="reporte_anomalias.xlsx", mime=MIME_XLSX, width="stretch"):
        MetricasUso(usuario).registrar("reporte_excel", {"anomalias": len(violaciones)})
    if repo_github:
        if b3.button(f"🐙 Crear Issue en {repo_github}", width="stretch"):
            try:
                with st.spinner("Publicando las anomalías en GitHub..."):
                    issue = publicar_anomalias(violaciones, usuario=usuario, origen="Aplicación web")
                MetricasUso(usuario).registrar("issue_github", {"anomalias": len(violaciones), "issue": issue["numero"]})
                cache.invalidar()
                st.session_state["reporte_aviso"] = f"✅ Issue #{issue['numero']} creado en GitHub: {issue['url']}"
                st.rerun()
            except ErrorGitHub as e:
                st.error(f"❌ {e}")
    else:
        b3.button("🐙 Crear Issue en GitHub", width="stretch", disabled=True,
                  help="Configura tu token y repositorio en «Bases de Datos → GitHub (integración)».")

    st.divider()

    for v in violaciones:
        d = describir(v)
        with st.expander(f"{d['icono']} Anomalía de {d['tipo'].upper()} en {d['motores']} | Registro: {d['id']}"):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("#### 🚨 ¿Qué pasó?")
                st.error(d["explicacion"])
                st.markdown("#### 💡 Sugerencia de Corrección")
                st.success(d["sugerencia"])
            with c2:
                st.markdown("#### 📦 Documento Problemático")
                st.json(v.get("dato_afectado") or {})
