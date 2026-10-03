import streamlit as st
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from controlador.controlador_reglas import ControladorReglas

st.title("⚡ Reglas de Integridad")
st.markdown("Define las restricciones estructurales, referenciales y de unicidad de tus bases de datos NoSQL.")

usuario = st.session_state.get("usuario")
controlador = ControladorReglas(usuario)

# Los mensajes se guardan en sesion para que sobrevivan al st.rerun()
if "reglas_aviso" in st.session_state:
    st.success(st.session_state.pop("reglas_aviso"))

tab1, tab2 = st.tabs(["📋 Reglas Activas", "➕ Crear Nueva Regla"])

with tab1:
    try:
        reglas = controlador.obtener_reglas()
        if reglas:
            for r in reglas:
                tipo_color = {"esquema": "blue", "unicidad": "green", "referencial": "orange", "consistencia": "red"}.get(r['tipo'], "gray")
                with st.expander(f"📌 {r['tipo'].upper()} | {r['motor_origen']} ({r['coleccion_origen']})"):
                    st.markdown(f"**Campo afectado:** `{r['campo']}`")
                    if r.get('motor_destino'):
                        st.markdown(f"**Referencia:** `{r['motor_destino']}.{r['coleccion_destino']} ({r['campo_destino']})`")
                    if r.get('schema'):
                        st.json(r['schema'])
                    
                    if st.button("🗑️ Eliminar", key=f"del_{r['id']}"):
                        controlador.eliminar_regla(r['id'])
                        st.session_state["reglas_aviso"] = "🗑️ Regla eliminada."
                        st.rerun()
        else:
            st.info("💡 No hay reglas definidas en este workspace.")
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    with st.container(border=True):
        st.subheader("Configurador de Regla")
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Comportamiento de la regla", ["esquema", "unicidad", "referencial", "consistencia"])
            motor_origen = st.selectbox("Motor Origen", ["mongodb", "redis", "cassandra"])
        with col2:
            coleccion_origen = st.text_input("Colección / Tabla")
            if tipo == "esquema":
                st.caption("ℹ️ Las reglas de esquema evalúan el documento completo contra el JSON Schema.")
                campo = "(documento)"
            else:
                campo = st.text_input("Campo a evaluar", placeholder="ej. email o user_id")

        motor_destino, coleccion_destino, campo_destino = "", "", ""
        schema = {}

        if tipo in ["referencial", "consistencia"]:
            st.markdown("#### Destino (Cross-Database)")
            c1, c2, c3 = st.columns(3)
            motor_destino = c1.selectbox("Motor Destino", ["mongodb", "redis", "cassandra"])
            coleccion_destino = c2.text_input("Colección Destino")
            campo_destino = c3.text_input("Campo de cruce")
        elif tipo == "esquema":
            schema_str = st.text_area("JSON Schema Validator", value='{\n  "type": "object",\n  "properties": {}\n}', height=150)
            try:
                schema = json.loads(schema_str)
            except:
                st.error("JSON inválido")

        if tipo == "consistencia":
            st.caption("ℹ️ Consistencia: los registros enlazados por *campo* ↔ *campo de cruce* deben existir en ambos motores y coincidir en los atributos que comparten.")

        if st.button("Guardar Política", type="primary", width="stretch"):
            faltantes = [nombre for nombre, valor in [("Colección / Tabla", coleccion_origen), ("Campo a evaluar", campo)] if not valor]
            if tipo in ["referencial", "consistencia"]:
                faltantes += [nombre for nombre, valor in [("Colección Destino", coleccion_destino), ("Campo de cruce", campo_destino)] if not valor]
            if faltantes:
                st.error(f"❌ Completa: {', '.join(faltantes)}")
                st.stop()
            if tipo == "esquema" and not schema:
                st.error("❌ El JSON Schema es inválido o está vacío.")
                st.stop()
            nueva_regla = {
                "tipo": tipo,
                "motor_origen": motor_origen,
                "coleccion_origen": coleccion_origen,
                "campo": campo,
                "motor_destino": motor_destino if motor_destino else None,
                "coleccion_destino": coleccion_destino if coleccion_destino else None,
                "campo_destino": campo_destino if campo_destino else None,
                "schema": schema if tipo == "esquema" else None
            }
            campos_clave = ["tipo", "motor_origen", "coleccion_origen", "campo", "motor_destino", "coleccion_destino", "campo_destino"]
            try:
                duplicada = any(
                    all(r.get(k) == nueva_regla[k] for k in campos_clave) and (tipo != "esquema" or r.get("schema") == schema)
                    for r in controlador.obtener_reglas()
                )
                if duplicada:
                    st.warning("⚠️ Ya existe una regla idéntica. No se guardó de nuevo.")
                else:
                    controlador.crear_regla(nueva_regla)
                    st.session_state["reglas_aviso"] = f"✅ Política de {tipo} guardada sobre {motor_origen}.{coleccion_origen}."
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")
