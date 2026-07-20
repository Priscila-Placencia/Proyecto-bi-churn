import streamlit as st
import pandas as pd
import sqlite3
import joblib
import plotly.express as px

# TRADUCCIONES
TRADUCCION_CATEGORIA = {
    "electronics": "Electrónica",
    "appliances": "Electrodomésticos",
    "computers": "Computadoras",
    "apparel": "Ropa",
    "furniture": "Muebles",
    "auto": "Automotriz",
    "construction": "Construcción",
    "kids": "Niños",
    "accessories": "Accesorios",
    "sport": "Deportes",
    "medicine": "Medicina",
    "stationery": "Papelería",
    "country_yard": "Jardín",
    "desconocido": "Sin categoría"
}

TRADUCCION_EVENTO = {
    "view": "Vista",
    "cart": "Carrito",
    "purchase": "Compra"
}

TRADUCCION_FEATURES = {
    'total_eventos': 'Total de eventos',
    'n_vistas': 'Vistas',
    'n_carritos': 'Carritos',
    'n_compras': 'Compras',
    'precio_promedio': 'Precio promedio',
    'precio_total_gastado': 'Total gastado',
    'categorias_distintas': 'Categorías exploradas',
    'tasa_conversion': 'Tasa de conversión',
    'duracion_actividad_dias': 'Días de actividad',
    'recencia_dias': 'Días sin actividad',
    'n_sesiones': 'Número de sesiones'
}

st.set_page_config(page_title="SGCV E-Commerce BI", layout="wide")

# LOGIN SIMPLE
USUARIOS = {"admin": "admin123", "profesor": "epn2026"}

if "logueado" not in st.session_state:
    st.session_state.logueado = False

if not st.session_state.logueado:
    st.title("🛒 SGCV — Sistema de Gestión de BI E-Commerce")
    st.subheader("Iniciar sesión")
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario in USUARIOS and USUARIOS[usuario] == clave:
            st.session_state.logueado = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# CARGA DE DATOS Y MODELO
@st.cache_resource
def cargar_datos():
    conn = sqlite3.connect('app_bi.db')
    usuarios = pd.read_sql_query("SELECT * FROM Dim_Usuario", conn)
    categorias = pd.read_sql_query("SELECT * FROM Resumen_Categoria", conn)
    muestra = pd.read_sql_query("SELECT * FROM Muestra_Eventos", conn)
    detallado = pd.read_sql_query("SELECT * FROM Resumen_Detallado", conn)
    conn.close()
    modelo = joblib.load('modelo_churn.pkl')
    features = joblib.load('features.pkl')
    detallado['fecha'] = pd.to_datetime(detallado['fecha'])
    return usuarios, categorias, muestra, detallado, modelo, features

usuarios, categorias, muestra, detallado, modelo, features = cargar_datos()

# Aplicamos traducción a las columnas (creamos columnas nuevas en español para mostrar)
detallado['categoria_es'] = detallado['categoria_principal'].map(TRADUCCION_CATEGORIA).fillna(detallado['categoria_principal'])
detallado['evento_es'] = detallado['event_type'].map(TRADUCCION_EVENTO).fillna(detallado['event_type'])
categorias['categoria_es'] = categorias['categoria_principal'].map(TRADUCCION_CATEGORIA).fillna(categorias['categoria_principal'])
categorias['evento_es'] = categorias['event_type'].map(TRADUCCION_EVENTO).fillna(categorias['event_type'])
muestra['evento_es'] = muestra['event_type'].map(TRADUCCION_EVENTO).fillna(muestra['event_type'])

# Traducción de la categoría favorita de cada usuario (para que el pastel de churn reaccione a los filtros)
if 'categoria_favorita' in usuarios.columns:
    usuarios['categoria_favorita_es'] = usuarios['categoria_favorita'].map(TRADUCCION_CATEGORIA).fillna(usuarios['categoria_favorita'])
else:
    usuarios['categoria_favorita_es'] = "Sin categoría"

# Etiquetas amigables para seleccionar clientes sin mostrar el user_id real
lista_usuarios_ids = usuarios['user_id'].tolist()
etiquetas_clientes = [f"Cliente {i+1}" for i in range(len(lista_usuarios_ids))]

# MENÚ LATERAL
st.sidebar.title("Retención E-Commerce")
st.sidebar.caption("Sesión activa")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.logueado = False
    st.rerun()

pagina = st.sidebar.radio("Navegación", [
    "Dashboard General",
    "Predicción de Churn",
    "Explorar Base de Datos"
])

# PÁGINA 1: DASHBOARD GENERAL
if pagina == "Dashboard General":
    st.title("Dashboard de Business Intelligence")
    st.caption("Filtra por fecha, categoría, marca y tipo de evento")

    # FILTROS (sin opción manual "Todos" -> usamos el "Select all" nativo de Streamlit)
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        rango_fecha = st.date_input(
            "Rango de fechas",
            value=(detallado['fecha'].min(), detallado['fecha'].max()),
            min_value=detallado['fecha'].min(),
            max_value=detallado['fecha'].max()
        )
    with f2:
        opciones_categoria = sorted(detallado['categoria_es'].unique().tolist())
        seleccion_categoria = st.multiselect("Categoría", opciones_categoria, default=[])
        filtro_categoria_es = opciones_categoria if len(seleccion_categoria) == 0 else seleccion_categoria
    with f3:
        opciones_marca = sorted(detallado['brand'].unique().tolist())
        seleccion_marca = st.multiselect("Marca", opciones_marca, default=[])
        filtro_marca = opciones_marca if len(seleccion_marca) == 0 else seleccion_marca
    with f4:
        opciones_evento = ["Vista", "Carrito", "Compra"]
        seleccion_evento = st.multiselect("Tipo de evento", opciones_evento, default=[])
        filtro_evento_es = opciones_evento if len(seleccion_evento) == 0 else seleccion_evento

    # Aplicamos filtros
    if len(rango_fecha) == 2:
        mask_fecha = (detallado['fecha'] >= pd.to_datetime(rango_fecha[0])) & \
                     (detallado['fecha'] <= pd.to_datetime(rango_fecha[1]))
    else:
        mask_fecha = pd.Series(True, index=detallado.index)

    datos_filtrados = detallado[
        mask_fecha &
        (detallado['categoria_es'].isin(filtro_categoria_es)) &
        (detallado['brand'].isin(filtro_marca)) &
        (detallado['evento_es'].isin(filtro_evento_es))
    ]

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Usuarios analizados", f"{len(usuarios):,}")
    k2.metric("Tasa de churn", f"{usuarios['churn'].mean()*100:.1f}%")
    k3.metric("Eventos (filtrado)", f"{datos_filtrados['total_eventos'].sum():,.0f}")
    k4.metric("Ingresos (filtrado)", f"${datos_filtrados['ingresos'].sum():,.0f}")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.line(
            datos_filtrados.groupby('fecha')['total_eventos'].sum().reset_index(),
            x='fecha', y='total_eventos', title="Eventos por día (filtrado)"
        )
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.bar(
            datos_filtrados.groupby('categoria_es')['total_eventos'].sum().reset_index(),
            x='categoria_es', y='total_eventos', title="Eventos por categoría", color='categoria_es'
        )
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig3 = px.bar(
            datos_filtrados.groupby('brand')['ingresos'].sum().reset_index().sort_values('ingresos', ascending=False),
            x='brand', y='ingresos', title="Ingresos por marca"
        )
        st.plotly_chart(fig3, use_container_width=True)
    with c4:
        # Pastel de churn ahora SÍ reacciona al filtro de categoría (usa la categoría favorita de cada usuario)
        usuarios_filtrados_pie = usuarios[usuarios['categoria_favorita_es'].isin(filtro_categoria_es)]
        if len(usuarios_filtrados_pie) == 0:
            st.info("No hay usuarios cuya categoría favorita coincida con el filtro seleccionado.")
        else:
            fig4 = px.pie(
                usuarios_filtrados_pie,
                names=usuarios_filtrados_pie['churn'].map({0: "Se mantiene activo", 1: "Abandona (churn)"}),
                title="Distribución de churn (según categoría seleccionada)"
            )
            st.plotly_chart(fig4, use_container_width=True)

# PÁGINA 2: PREDICCIÓN DE CHURN
elif pagina == "Predicción de Churn":
    st.title("Predicción de Riesgo de Churn")
    modo = st.radio("¿Qué quieres predecir?", ["Cliente existente", "Simular cliente nuevo"])

    if modo == "Cliente existente":
        seleccion = st.selectbox("Selecciona un cliente", etiquetas_clientes)
        idx = etiquetas_clientes.index(seleccion)
        id_usuario_real = lista_usuarios_ids[idx]

        fila = usuarios[usuarios['user_id'] == id_usuario_real][features]
        real = usuarios[usuarios['user_id'] == id_usuario_real]['churn'].values[0]

        proba = modelo.predict_proba(fila)[0][1]
        st.metric("Probabilidad de Churn", f"{proba*100:.1f}%")
        st.write(f"**Estado real registrado:** {'Abandonó (churn)' if real == 1 else 'Se mantuvo activo'}")

        fila_amigable = fila.rename(columns=TRADUCCION_FEATURES)
        st.dataframe(fila_amigable, hide_index=True)
    else:
        entrada = {}
        cols = st.columns(3)
        for i, feat in enumerate(features):
            with cols[i % 3]:
                etiqueta = TRADUCCION_FEATURES.get(feat, feat)
                entrada[feat] = st.number_input(etiqueta, value=float(usuarios[feat].median()))
        if st.button("Predecir churn"):
            df_entrada = pd.DataFrame([entrada])
            proba = modelo.predict_proba(df_entrada)[0][1]
            st.metric("Probabilidad de Churn", f"{proba*100:.1f}%")
            if proba > 0.5:
                st.error("Cliente en riesgo de abandono")
            else:
                st.success("Cliente probablemente se mantendrá activo")

# PÁGINA 3: EXPLORAR BASE DE DATOS
elif pagina == "Explorar Base de Datos":
    st.title("Consultas de la Base de Datos")
    st.caption("Elige qué quieres consultar")

    pregunta = st.selectbox("¿Qué deseas consultar?", [
        "¿Cuántos usuarios hay y cuántos están en riesgo de churn?",
        "¿Qué categoría genera más ingresos?",
        "¿Qué marca es la más vista/comprada?",
        "¿Cómo se distribuyen los eventos por día?"
    ])

    if pregunta == "¿Cuántos usuarios hay y cuántos están en riesgo de churn?":
        c1, c2 = st.columns(2)
        c1.metric("Total de usuarios analizados", f"{len(usuarios):,}")
        c2.metric("Usuarios en riesgo de churn", f"{(usuarios['churn'] == 1).sum():,}")
        fig = px.pie(
            usuarios,
            names=usuarios['churn'].map({0: "Se mantiene activo", 1: "Abandona (churn)"}),
            title="Distribución de clientes"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif pregunta == "¿Qué categoría genera más ingresos?":
        resumen = categorias[categorias['event_type'] == 'purchase'].groupby('categoria_es')['ingresos'].sum().sort_values(ascending=False).reset_index()
        st.dataframe(resumen.rename(columns={'categoria_es': 'Categoría', 'ingresos': 'Ingresos ($)'}), hide_index=True)
        fig = px.bar(resumen, x='categoria_es', y='ingresos', title="Ingresos por categoría")
        st.plotly_chart(fig, use_container_width=True)

    elif pregunta == "¿Qué marca es la más vista/comprada?":
        resumen = detallado.groupby('brand')['total_eventos'].sum().sort_values(ascending=False).head(10).reset_index()
        st.dataframe(resumen.rename(columns={'brand': 'Marca', 'total_eventos': 'Total de eventos'}), hide_index=True)
        fig = px.bar(resumen, x='brand', y='total_eventos', title="Top 10 marcas por actividad")
        st.plotly_chart(fig, use_container_width=True)

    else:
        resumen = detallado.groupby('fecha')['total_eventos'].sum().reset_index()
        fig = px.line(resumen, x='fecha', y='total_eventos', title="Eventos por día (todo noviembre)")
        st.plotly_chart(fig, use_container_width=True)
