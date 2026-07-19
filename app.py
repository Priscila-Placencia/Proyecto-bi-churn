import streamlit as st
import pandas as pd
import sqlite3
import joblib
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="SGCV E-Commerce", page_icon="🛒", layout="wide")

# --- CARGA DE DATOS Y MODELO (se cachea para que no recargue cada vez) ---
@st.cache_resource
def cargar_datos():
    conn = sqlite3.connect('app_bi.db')
    usuarios = pd.read_sql_query("SELECT * FROM Dim_Usuario", conn)
    categorias = pd.read_sql_query("SELECT * FROM Resumen_Categoria", conn)
    muestra = pd.read_sql_query("SELECT * FROM Muestra_Eventos", conn)
    conn.close()
    modelo = joblib.load('modelo_churn.pkl')
    features = joblib.load('features.pkl')
    return usuarios, categorias, muestra, modelo, features

usuarios, categorias, muestra, modelo, features = cargar_datos()

# --- MENÚ LATERAL ---
st.sidebar.title("🛒 Retención E-Commerce")
pagina = st.sidebar.radio("Navegación", [
    "📊 Dashboard General",
    "🔮 Predicción de Churn",
    "🗄️ Explorar Base de Datos"
])

# ============================================================
# PÁGINA 1: DASHBOARD GENERAL (con filtros interactivos)
# ============================================================
if pagina == "📊 Dashboard General":
    st.title("Dashboard de Business Intelligence")
    st.caption("Retención de clientes y comportamiento de compra — E-Commerce")

    # --- FILTROS ---
    col1, col2 = st.columns(2)
    with col1:
        categorias_disponibles = categorias['categoria_principal'].unique().tolist()
        filtro_categoria = st.multiselect(
            "Filtrar por categoría", categorias_disponibles, default=categorias_disponibles
        )
    with col2:
        filtro_evento = st.multiselect(
            "Tipo de evento", ['view', 'cart', 'purchase'], default=['view', 'cart', 'purchase']
        )

    datos_filtrados = categorias[
        (categorias['categoria_principal'].isin(filtro_categoria)) &
        (categorias['event_type'].isin(filtro_evento))
    ]

    # --- KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Usuarios analizados", f"{len(usuarios):,}")
    k2.metric("Tasa de churn", f"{usuarios['churn'].mean()*100:.1f}%")
    k3.metric("Total eventos (filtrado)", f"{datos_filtrados['total'].sum():,.0f}")
    k4.metric("Ingresos (filtrado)", f"${datos_filtrados['ingresos'].sum():,.0f}")

    st.divider()

    # --- GRÁFICOS ---
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.bar(
            datos_filtrados.groupby('categoria_principal')['total'].sum().reset_index(),
            x='categoria_principal', y='total',
            title="Eventos por categoría", color='categoria_principal'
        )
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.pie(
            usuarios, names='churn',
            title="Distribución de Churn (1 = Abandona, 0 = Se queda)"
        )
        st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.bar(
        datos_filtrados[datos_filtrados['event_type']=='purchase'].sort_values('ingresos', ascending=False),
        x='categoria_principal', y='ingresos',
        title="Ingresos por categoría", color='categoria_principal'
    )
    st.plotly_chart(fig3, use_container_width=True)

# ============================================================
# PÁGINA 2: PREDICCIÓN DE CHURN
# ============================================================
elif pagina == "🔮 Predicción de Churn":
    st.title("Predicción de Riesgo de Churn")
    st.caption("Selecciona un cliente existente o simula uno nuevo")

    modo = st.radio("¿Qué quieres predecir?", ["Cliente existente", "Simular cliente nuevo"])

    if modo == "Cliente existente":
        id_usuario = st.selectbox("Selecciona un usuario", usuarios['user_id'].unique())
        fila = usuarios[usuarios['user_id'] == id_usuario][features]
        real = usuarios[usuarios['user_id'] == id_usuario]['churn'].values[0]

        proba = modelo.predict_proba(fila)[0][1]
        st.metric("Probabilidad de Churn", f"{proba*100:.1f}%")
        st.write(f"**Churn real registrado:** {'Sí abandonó' if real==1 else 'Se mantuvo activo'}")
        st.dataframe(fila)

    else:
        st.write("Ingresa los datos del cliente simulado:")
        entrada = {}
        cols = st.columns(3)
        for i, feat in enumerate(features):
            with cols[i % 3]:
                entrada[feat] = st.number_input(feat, value=float(usuarios[feat].median()))

        if st.button("Predecir churn"):
            df_entrada = pd.DataFrame([entrada])
            proba = modelo.predict_proba(df_entrada)[0][1]
            st.metric("Probabilidad de Churn", f"{proba*100:.1f}%")
            if proba > 0.5:
                st.error("⚠️ Cliente en riesgo de abandono")
            else:
                st.success("✅ Cliente probablemente se mantendrá activo")

# ============================================================
# PÁGINA 3: EXPLORAR BASE DE DATOS
# ============================================================
elif pagina == "🗄️ Explorar Base de Datos":
    st.title("Base de Datos del Sistema")
    st.caption("Muestra de la tabla de hechos y dimensiones")

    tabla = st.selectbox("Selecciona una tabla", ["Dim_Usuario", "Resumen_Categoria", "Muestra_Eventos"])
    if tabla == "Dim_Usuario":
        st.dataframe(usuarios)
    elif tabla == "Resumen_Categoria":
        st.dataframe(categorias)
    else:
        st.dataframe(muestra)
