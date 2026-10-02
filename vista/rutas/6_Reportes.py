import streamlit as st
import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_reporte import ControladorReporte
from modelo.gestor_conexiones import GestorConexiones

st.title("📄 Reporte de Anomalías y Sugerencias")
st.markdown("Revisa en detalle cada una de las violaciones detectadas por el sistema y descubre cómo corregirlas.")

usuario = st.session_state.get("usuario")
controlador = ControladorReporte(usuario)
violaciones = controlador.obtener_violaciones()

gestor = GestorConexiones(usuario)

# Pequeño resumen de BDs escaneadas
motores_conectados = gestor.motores_configurados()

if motores_conectados:
    st.info(f"Bases de datos auditadas en tu último escaneo profundo: **{', '.join(motores_conectados).title()}**")

if not violaciones:
    st.success("🎉 ¡Excelente! No se ha detectado ninguna anomalía. Tus datos están completamente íntegros.")
else:
    st.warning(f"⚠️ Se detectaron {len(violaciones)} anomalía(s) en tu sistema.")
    
    # Exportar reporte en PDF
    def generar_pdf(violaciones):
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=16)
        pdf.cell(0, 10, "Reporte de Auditoria de Integridad", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        for idx, v in enumerate(violaciones):
            pdf.set_font("helvetica", "B", size=12)
            pdf.cell(0, 10, f"Anomalia #{idx+1} - {str(v.get('tipo', 'Desconocido')).upper()}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", size=10)
            
            pdf.multi_cell(0, 8, f"Regla ID: {v.get('regla_id')}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 8, f"Motores: {v.get('motores_involucrados')}", new_x="LMARGIN", new_y="NEXT")
            
            # Limpiar el dict a string y evitar caracteres que rompan el PDF
            dato_str = str(v.get('dato_afectado', {})).encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, f"Dato Afectado: {dato_str}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(5)
            
        return bytes(pdf.output())
    
    st.download_button(
        label="📥 Descargar Reporte PDF",
        data=generar_pdf(violaciones),
        file_name='reporte_anomalias.pdf',
        mime='application/pdf',
        use_container_width=True
    )
    
    st.divider()

    for idx, v in enumerate(violaciones):
        tipo = v.get('tipo', 'desconocido')
        motores = v.get('motores_involucrados', 'N/D')
        dato = v.get('dato_afectado', {})
        id_doc = dato.get('_id', 'Desconocido')
        
        # Lógica de explicación y sugerencia
        if tipo == "esquema":
            icono = "📐"
            color = "blue"
            explicacion = f"El documento con ID `{id_doc}` no cumple con el esquema JSON estricto requerido. Faltan campos obligatorios o los tipos de datos (string, int) no coinciden."
            sugerencia = "Actualiza el registro añadiendo los campos faltantes o corrigiendo el tipo de dato para que coincida con la estructura esperada."
        elif tipo == "unicidad":
            icono = "👯"
            color = "green"
            explicacion = f"Se detectó un valor duplicado en un campo que debería ser único para el documento `{id_doc}`."
            sugerencia = "Identifica y elimina el registro duplicado, o modifica el valor del campo para que sea verdaderamente único en toda la colección."
        elif tipo == "referencial":
            icono = "🔗"
            color = "orange"
            explicacion = f"El registro `{id_doc}` es huérfano. Hace referencia a un ID externo que NO EXISTE en la base de datos de destino."
            sugerencia = "Asegúrate de que el documento padre/destino exista antes de insertar la referencia, o elimina este documento huérfano para mantener la integridad relacional."
        elif tipo == "consistencia":
            icono = "⚖️"
            color = "red"
            explicacion = f"Desincronización detectada en el registro `{id_doc}` entre las bases de datos {motores}."
            sugerencia = "Fuerza una sincronización o elige cuál de las dos bases de datos tiene la fuente de verdad absoluta para sobreescribir la otra."
        else:
            icono = "⚠️"
            color = "gray"
            explicacion = "Anomalía genérica detectada."
            sugerencia = "Revisa manualmente el registro en la base de datos."

        with st.expander(f"{icono} Anomalía de {tipo.upper()} en {motores} | Registro: {id_doc}"):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("#### 🚨 ¿Qué pasó?")
                st.error(explicacion)
                st.markdown("#### 💡 Sugerencia de Corrección")
                st.success(sugerencia)
            with c2:
                st.markdown("#### 📦 Documento Problemático")
                st.json(dato)
