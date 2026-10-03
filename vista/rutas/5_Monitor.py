import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modelo.gestor_conexiones import GestorConexiones
from modelo.adaptadores import get_adapter
from modelo.motor_reglas import MotorReglas
from datetime import datetime

usuario = st.session_state.get("usuario")
gestor = GestorConexiones(usuario)

st.title("🩺 Monitor y Observabilidad NoSQL")
st.markdown("Inspecciona la telemetría, salud, esquemas de tablas/colecciones y datos en vivo de tu base de datos conectada.")

col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    motor_monitor = st.selectbox("Motor a inspeccionar", ["mongodb", "redis", "cassandra"], key="monitor_motor")
with col_sel2:
    st.write("")
    st.write("")
    btn_inspeccionar = st.button("🔄 Ejecutar Diagnóstico Completo", type="primary", width="stretch")

if btn_inspeccionar:
    adapter = None
    try:
        if not gestor.obtener_conexion(motor_monitor):
            raise ValueError(f"No hay credenciales guardadas para {motor_monitor.upper()}. Configúralo en la sección de Conexiones primero.")
        with st.spinner(f"Conectando con {motor_monitor.upper()} y recopilando telemetría..."):
            adapter = get_adapter(motor_monitor, usuario)
            info = adapter.obtener_info_completa()
            st.session_state["monitor_resultado"] = {
                "motor": motor_monitor,
                "info": info,
                "revisado": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            }
            st.session_state.pop("monitor_error", None)
    except Exception as error:
        st.session_state["monitor_error"] = f"{type(error).__name__}: {error}"
        st.session_state.pop("monitor_resultado", None)
    finally:
        if adapter:
            try:
                adapter.cerrar()
            except Exception:
                pass

if st.session_state.get("monitor_error"):
    st.error(f"❌ Error al conectar con {motor_monitor.upper()}: {st.session_state.pop('monitor_error')}")

resultado = st.session_state.get("monitor_resultado")
if resultado and resultado["motor"] == motor_monitor:
    info = resultado["info"]
    latencia = info.get("latencia_ms", 0)
    estado = info.get("estado", "Disponible")
    
    # 1. TARJETAS DE CABECERA (KPIs EJECUTIVOS)
    with st.container(border=True):
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        with kpi1:
            st.metric("Estado de Conexión", f"🟢 {estado}")
            st.caption("Conexión en tiempo real")
            
        with kpi2:
            lat_badge = "⚡ Óptima" if latencia < 60 else ("🟡 Aceptable" if latencia < 200 else "🐢 Alta")
            st.metric("Latencia Ping", f"{latencia} ms", delta=lat_badge, delta_color="normal" if latencia < 100 else "inverse")
            st.caption(f"Última revisión: {resultado['revisado'][:19]}")
            
        with kpi3:
            version_srv = info.get("servidor", {}).get("version", "N/D")
            st.metric("Versión del Motor", f"v{version_srv}" if version_srv != "N/D" else "Activo")
            target_name = info.get("database") or info.get("keyspace") or info.get("host") or "N/D"
            st.caption(f"Workspace: `{target_name}`")
            
        with kpi4:
            if motor_monitor == "mongodb":
                num_recursos = len(info.get("colecciones", []))
                st.metric("Colecciones", f"{num_recursos}")
                tam_mb = info.get("estadisticas", {}).get("tamano_almacenamiento_mb", 0)
                st.caption(f"Almacenamiento: {tam_mb} MB")
            elif motor_monitor == "redis":
                num_recursos = len(info.get("recursos", []))
                st.metric("Namespaces / Prefijos", f"{num_recursos}")
                mem_usada = info.get("memoria", {}).get("usada_humana", "N/D")
                # Proveedores serverless como Upstash no reportan la memoria real (devuelven 0B)
                if str(mem_usada).replace(".", "").replace("0", "") in ("B", ""):
                    mem_usada = "no reportada por el proveedor"
                st.caption(f"Memoria RAM: {mem_usada}")
            else:
                num_recursos = len(info.get("tablas", []))
                st.metric("Tablas CQL", f"{num_recursos}")
                st.caption(f"Keyspace: `{info.get('keyspace', 'N/D')}`")

    # 2. PESTAÑAS DE INSPECCIÓN PROFUNDA
    tab_esquemas, tab_explorador, tab_telemetria, tab_reglas = st.tabs([
        "🗂️ Estructura & Esquemas",
        "🔍 Explorador de Datos",
        "⚙️ Telemetría del Servidor",
        "🛡️ Políticas Activas"
    ])

    # --- TAB 1: ESTRUCTURA Y ESQUEMAS DE TABLAS/COLECCIONES ---
    with tab_esquemas:
        if motor_monitor == "mongodb":
            colecciones = info.get("colecciones", [])
            if not colecciones:
                st.info("No se encontraron colecciones creadas en esta base de datos de MongoDB.")
            else:
                st.subheader(f"Colecciones Detectadas ({len(colecciones)})")
                nombres_cols = [c["nombre"] for c in colecciones]
                col_sel = st.selectbox("Selecciona una colección para inspeccionar su estructura:", nombres_cols, key="sel_col_mongo")
                col_actual = next((c for c in colecciones if c["nombre"] == col_sel), None)
                
                if col_actual:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        docs_val = col_actual.get("registros")
                        st.metric("Documentos Estimados", f"{docs_val}" if docs_val is not None else "No disponible")
                    with c2:
                        st.metric("Campos Inferred", f"{len(col_actual.get('campos', []))}")
                    with c3:
                        st.metric("Índices Activos", f"{len(col_actual.get('indices', []))}")

                    st.markdown("#### 🧬 Inferencia de Esquema (Tipos de Datos de Documentos)")
                    campos = col_actual.get("campos", [])
                    if campos:
                        st.dataframe(
                            [{"Campo / Atributo": c["campo"], "Tipo de Dato Detectado": c["tipo"]} for c in campos],
                            width="stretch",
                            hide_index=True
                        )
                    else:
                        st.caption("La colección está vacía o no tiene documentos para inferir tipos.")

                    st.markdown("#### ⚡ Índices en la Colección")
                    indices = col_actual.get("indices", [])
                    if indices:
                        st.dataframe(
                            [{"Nombre de Índice": idx["nombre"], "Claves / Campos": idx["campos"], "Restricción Única": idx["unico"]} for idx in indices],
                            width="stretch",
                            hide_index=True
                        )
                    else:
                        st.caption("No se detectaron índices adicionales.")

        elif motor_monitor == "redis":
            recursos = info.get("recursos", [])
            if not recursos:
                st.info("No se encontraron claves o prefijos en esta base de datos Redis.")
            else:
                st.subheader("Desglose de Claves por Prefijo / Namespace")
                st.dataframe(
                    [
                        {
                            "Namespace / Prefijo": r["nombre"],
                            "Total de Claves": r["registros"],
                            "Estructuras de Datos": ", ".join(r.get("tipos", ["string"])),
                            "Claves de Muestra": ", ".join(r.get("claves_ejemplo", [])[:3])
                        }
                        for r in recursos
                    ],
                    width="stretch",
                    hide_index=True
                )

        elif motor_monitor == "cassandra":
            tablas = info.get("tablas", [])
            if not tablas:
                st.info("No se encontraron tablas creadas en este keyspace de Cassandra.")
            else:
                st.subheader(f"Tablas CQL ({len(tablas)})")
                nombres_tablas = [t["nombre"] for t in tablas]
                tabla_sel = st.selectbox("Selecciona una tabla para ver su esquema CQL:", nombres_tablas, key="sel_tabla_cass")
                t_actual = next((t for t in tablas if t["nombre"] == tabla_sel), None)
                
                if t_actual:
                    cols_cass = t_actual.get("columnas", [])
                    if cols_cass:
                        st.markdown(f"#### 📐 Esquema de Columnas de `{tabla_sel}`")
                        st.dataframe(
                            [{"Columna": c["columna"], "Tipo CQL": c["tipo"], "Rol / Restricción": c["rol"]} for c in cols_cass],
                            width="stretch",
                            hide_index=True
                        )

    # --- TAB 2: EXPLORADOR DE DATOS EN VIVO ---
    with tab_explorador:
        st.subheader("Visualizador de Registros en Vivo")
        lista_nombres = []
        if motor_monitor == "mongodb":
            lista_nombres = [c["nombre"] for c in info.get("colecciones", [])]
        elif motor_monitor == "redis":
            lista_nombres = [r["nombre"] for r in info.get("recursos", [])]
        elif motor_monitor == "cassandra":
            lista_nombres = [t["nombre"] for t in info.get("tablas", [])]

        if not lista_nombres:
            st.info("No hay tablas o colecciones disponibles para explorar.")
        else:
            col_exp1, col_exp2, col_exp3 = st.columns([2, 1, 1])
            with col_exp1:
                item_seleccionado = st.selectbox("Elemento a explorar", lista_nombres, key=f"explorar_{motor_monitor}")
            with col_exp2:
                limite_filas = st.selectbox("Cantidad de filas", [10, 25, 50, 100], index=0, key=f"limite_{motor_monitor}")
            with col_exp3:
                modo_vista = st.radio("Formato", ["Tabla", "JSON"], horizontal=True, key=f"modo_{motor_monitor}")

            if st.button("📥 Consultar Muestra de Registros", key=f"btn_muestra_{motor_monitor}"):
                adapter_muestra = None
                try:
                    adapter_muestra = get_adapter(motor_monitor, usuario)
                    muestra_datos = adapter_muestra.obtener_muestra(item_seleccionado, int(limite_filas))
                    st.session_state["datos_explorador"] = (motor_monitor, item_seleccionado, muestra_datos)
                except Exception as err:
                    st.error(f"Error al leer datos: {err}")
                finally:
                    if adapter_muestra:
                        try:
                            adapter_muestra.cerrar()
                        except Exception:
                            pass

            datos_actuales = st.session_state.get("datos_explorador")
            if datos_actuales and datos_actuales[:2] == (motor_monitor, item_seleccionado):
                registros = datos_actuales[2]
                st.caption(f"Mostrando {len(registros)} registros de `{item_seleccionado}`:")
                if not registros:
                    st.warning("La colección/tabla seleccionada no contiene registros actualmente.")
                else:
                    if modo_vista == "Tabla":
                        st.dataframe(registros, width="stretch", hide_index=True)
                    else:
                        st.json(registros)

    # --- TAB 3: TELEMETRÍA DEL SERVIDOR ---
    with tab_telemetria:
        st.subheader("Parámetros y Estadísticas del Servidor")
        if motor_monitor == "mongodb":
            stats = info.get("estadisticas", {})
            srv = info.get("servidor", {})
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.markdown("##### 📦 Métricas de Capacidad")
                    st.markdown(f"**Tamaño de Datos:** `{stats.get('tamano_datos_mb', 'N/D')} MB`")
                    st.markdown(f"**Almacenamiento en Disco:** `{stats.get('tamano_almacenamiento_mb', 'N/D')} MB`")
                    st.markdown(f"**Tamaño de Índices:** `{stats.get('tamano_indices_mb', 'N/D')} MB`")
                    st.markdown(f"**Promedio por Objeto:** `{stats.get('tamano_promedio_objeto_kb', 'N/D')} KB`")
            with c2:
                with st.container(border=True):
                    st.markdown("##### ⚙️ Información de Build")
                    st.markdown(f"**Versión MongoDB:** `{srv.get('version', 'N/D')}`")
                    st.markdown(f"**Git Commit:** `{srv.get('git_version', 'N/D')}`")
                    st.markdown(f"**Max Wire Version:** `{srv.get('max_wire_version', 'N/D')}`")
                    st.markdown(f"**Arquitectura:** `{srv.get('bits', 64)} bits`")

        elif motor_monitor == "redis":
            mem = info.get("memoria", {})
            stats = info.get("estadisticas", {})
            srv = info.get("servidor", {})
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.markdown("##### 🧠 Memoria & Desalojo")
                    st.markdown(f"**Memoria Usada:** `{mem.get('usada_humana', 'N/D')}`")
                    st.markdown(f"**Pico de Memoria:** `{mem.get('pico_humana', 'N/D')}`")
                    st.markdown(f"**Ratio de Fragmentación:** `{mem.get('fragmentacion', 'N/D')}`")
                    st.markdown(f"**Política de Evicción:** `{mem.get('politica_eviccion', 'N/D')}`")
            with c2:
                with st.container(border=True):
                    st.markdown("##### 📈 Rendimiento & Clientes")
                    st.markdown(f"**Clientes Conectados:** `{stats.get('clientes_conectados', 0)}`")
                    st.markdown(f"**Comandos Procesados:** `{stats.get('comandos_procesados', 0):,}`")
                    st.markdown(f"**Conexiones Totales:** `{stats.get('conexiones_totales', 0):,}`")
                    st.markdown(f"**Tiempo de Actividad (Uptime):** `{srv.get('uptime_dias', 0)} días`")

        elif motor_monitor == "cassandra":
            cluster = info.get("cluster", {})
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.markdown("##### 🏛️ Clúster & Particionado")
                    st.markdown(f"**Nombre del Clúster:** `{cluster.get('nombre', 'N/D')}`")
                    st.markdown(f"**Particionador:** `{cluster.get('particionador', 'N/D')}`")
                    st.markdown(f"**Keyspace Activo:** `{info.get('keyspace', 'N/D')}`")
            with c2:
                with st.container(border=True):
                    st.markdown("##### 🌐 Nodos de Contacto")
                    nodos = cluster.get("nodos", [])
                    if nodos:
                        for n in nodos:
                            st.markdown(f"📍 `{n}`")
                    else:
                        st.caption("No se pudieron enumerar nodos individuales.")

    # --- TAB 4: REGLAS ASOCIADAS AL MOTOR ---
    with tab_reglas:
        try:
            reglas = [r for r in MotorReglas(usuario).obtener_reglas() if r.get("motor_origen") == motor_monitor or r.get("motor_destino") == motor_monitor]
            st.subheader(f"Reglas de Integridad Vinculadas ({len(reglas)})")
            if reglas:
                filas_reglas = []
                for r in reglas:
                    tipo_regla = r.get("tipo", "")
                    campo_mostrar = r.get("campo") or "—"
                    if tipo_regla == "esquema":
                        campo_mostrar = "(Documento completo / JSON Schema)"
                    
                    filas_reglas.append({
                        "Tipo de Regla": tipo_regla.upper(),
                        "Origen": f"{r.get('motor_origen')}.{r.get('coleccion_origen')}",
                        "Campo Origen": campo_mostrar,
                        "Destino": f"{r.get('motor_destino')}.{r.get('coleccion_destino')}" if r.get("motor_destino") else "— (Local)",
                        "Campo Destino": r.get("campo_destino") or "—",
                        "Fecha de Creación": r.get("creado_en", "")[:19]
                    })
                st.dataframe(filas_reglas, width="stretch", hide_index=True)
            else:
                st.info("No hay reglas de integridad configuradas actualmente para este motor.")
        except Exception as error:
            st.warning(f"No se pudieron cargar las reglas: {error}")
