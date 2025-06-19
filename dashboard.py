import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
import os
from datetime import datetime
import hashlib
import jwt
from dotenv import load_dotenv
import io

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Moléculas Farmacéuticas",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar límites de Streamlit para mostrar más datos
st._config.set_option('dataFrame.maxRows', None)  # Sin límite de filas
st._config.set_option('dataFrame.maxColumns', None)  # Sin límite de columnas

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")

# Cliente de Supabase
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase_client = init_supabase()

# Funciones de utilidad
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except:
        return None

def create_token(username):
    return jwt.encode({
        'user': username,
        'exp': datetime.utcnow().timestamp() + 3600  # 1 hora
    }, SECRET_KEY, algorithm='HS256')

# Función para cargar datos
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data():
    try:
        # Método 1: Usar count para obtener el total y luego paginar
        count_response = supabase_client.table('moleculas_esp').select('*', count='exact').execute()
        total_count = count_response.count
        
        if total_count <= 1000:
            # Si hay menos de 1000 registros, obtener todos de una vez
            response = supabase_client.table('moleculas_esp').select('*').execute()
            return pd.DataFrame(response.data)
        else:
            # Si hay más de 1000 registros, obtener por páginas
            all_data = []
            page_size = 1000
            
            for offset in range(0, total_count, page_size):
                response = supabase_client.table('moleculas_esp').select('*').range(offset, offset + page_size - 1).execute()
                all_data.extend(response.data)
                
                # Mostrar progreso
                progress = min((offset + page_size) / total_count, 1.0)
                if 'progress_bar' not in st.session_state:
                    st.session_state.progress_bar = st.progress(0)
                st.session_state.progress_bar.progress(progress)
            
            # Limpiar barra de progreso
            if 'progress_bar' in st.session_state:
                st.session_state.progress_bar.empty()
                del st.session_state.progress_bar
            
            return pd.DataFrame(all_data)
            
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# Función alternativa para cargar datos (si el método anterior no funciona)
@st.cache_data(ttl=300)
def load_data_alternative():
    try:
        # Método alternativo: usar limit con un número muy alto
        response = supabase_client.table('moleculas_esp').select('*').limit(100000).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error cargando datos con método alternativo: {e}")
        return pd.DataFrame()

# Función de autenticación
def authenticate_user(username, password):
    # Aquí deberías implementar tu lógica de autenticación real
    # Por simplicidad, uso credenciales hardcodeadas
    if username == "admin" and password == "admin123":
        return True
    return False

# Función de login
def login_page():
    st.title("🔐 Acceso al Dashboard de Moléculas")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
            submit_button = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit_button:
                if authenticate_user(username, password):
                    token = create_token(username)
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.token = token
                    st.success("¡Login exitoso!")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

# Función para crear filtros en la barra lateral
def create_filters(df):
    st.sidebar.header("🔍 Filtros de Consulta")
    
    # Filtro por región
    regiones = sorted(df['Región'].dropna().unique())
    selected_regions = st.sidebar.multiselect("Región", regiones, key="region_filter")
    
    # Filtrar países basado en regiones seleccionadas
    if selected_regions:
        df_filtered = df[df['Región'].isin(selected_regions)]
        paises = sorted(df_filtered['País'].dropna().unique())
    else:
        paises = sorted(df['País'].dropna().unique())
    
    selected_countries = st.sidebar.multiselect("País", paises, key="country_filter")
    
    # Filtro por molécula
    moleculas = sorted(df['Molécula'].dropna().unique())
    selected_molecules = st.sidebar.multiselect("Molécula", moleculas, key="molecule_filter")
    
    # Filtro RX/OTC
    rx_otc_options = ['RX', 'OTC']
    selected_rx_otc = st.sidebar.multiselect("RX/OTC", rx_otc_options, key="rx_otc_filter")
    
    # Filtro por corporación
    corporaciones = sorted(df['Corporacion'].dropna().unique())
    selected_corporations = st.sidebar.multiselect("Corporación", corporaciones, key="corp_filter")
    
    # Filtro por año
    years = df['Año de Lanzamiento Molécula'].dropna()
    if len(years) > 0:
        min_year, max_year = int(years.min()), int(years.max())
        year_range = st.sidebar.slider(
            "Rango de Años de Lanzamiento",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            key="year_range"
        )
    else:
        year_range = (2000, 2025)
    
    # Botones de control
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🗑️ Limpiar Filtros", use_container_width=True):
            for key in ['region_filter', 'country_filter', 'molecule_filter', 
                       'rx_otc_filter', 'corp_filter']:
                if key in st.session_state:
                    st.session_state[key] = []
            st.rerun()
    
    with col2:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.token = None
            st.rerun()
    
    return {
        'regions': selected_regions,
        'countries': selected_countries,
        'molecules': selected_molecules,
        'rx_otc': selected_rx_otc,
        'corporations': selected_corporations,
        'year_range': year_range
    }

# Función para aplicar filtros
def apply_filters(df, filters):
    filtered_df = df.copy()
    
    if filters['regions']:
        filtered_df = filtered_df[filtered_df['Región'].isin(filters['regions'])]
    
    if filters['countries']:
        filtered_df = filtered_df[filtered_df['País'].isin(filters['countries'])]
    
    if filters['molecules']:
        filtered_df = filtered_df[filtered_df['Molécula'].isin(filters['molecules'])]
    
    if filters['rx_otc']:
        filtered_df = filtered_df[filtered_df['RX-OTC - Molécula'].isin(filters['rx_otc'])]
    
    if filters['corporations']:
        filtered_df = filtered_df[filtered_df['Corporacion'].isin(filters['corporations'])]
    
    filtered_df = filtered_df[
        (filtered_df['Año de Lanzamiento Molécula'] >= filters['year_range'][0]) &
        (filtered_df['Año de Lanzamiento Molécula'] <= filters['year_range'][1])
    ]
    
    return filtered_df

# Funciones para crear cada pestaña
def create_resumen_tab(df):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    # Métricas generales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Productos", f"{len(df):,}")
    
    with col2:
        st.metric("Moléculas Únicas", f"{df['Molécula'].nunique():,}")
    
    with col3:
        st.metric("Países", f"{df['País'].nunique():,}")
    
    with col4:
        st.metric("Corporaciones", f"{df['Corporacion'].nunique():,}")
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pie = px.pie(
            df, 
            names='RX-OTC - Molécula', 
            title='Distribución RX vs OTC',
            color_discrete_map={'RX': '#ff7f0e', 'OTC': '#1f77b4'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        fig_hist = px.histogram(
            df, 
            x='Año de Lanzamiento Molécula', 
            title='Lanzamientos por Año',
            nbins=20
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    # Gráfico de países
    top_countries = df.groupby('País').size().sort_values(ascending=False).head(10)
    fig_countries = px.bar(
        x=top_countries.index,
        y=top_countries.values,
        title='Top 10 Países por Número de Productos',
        labels={'x': 'País', 'y': 'Número de Productos'}
    )
    st.plotly_chart(fig_countries, use_container_width=True)

def create_pais_tab(df):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_treemap = px.treemap(
            df,
            path=['Región', 'País'],
            title='Distribución de Productos por Región y País'
        )
        st.plotly_chart(fig_treemap, use_container_width=True)
    
    with col2:
        country_rx_otc = df.groupby(['País', 'RX-OTC - Molécula']).size().reset_index(name='count')
        fig_bar = px.bar(
            country_rx_otc,
            x='País',
            y='count',
            color='RX-OTC - Molécula',
            title='RX vs OTC por País'
        )
        fig_bar.update_xaxes(tickangle=45)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Tabla de análisis por país
    st.subheader("📊 Análisis por País")
    country_analysis = df.groupby('País').agg({
        'Molécula': 'nunique',
        'Producto': 'nunique', 
        'Corporacion': 'nunique',
        'Año de Lanzamiento Molécula': 'mean'
    }).round(1).reset_index()
    
    country_analysis.columns = ['País', 'Moléculas', 'Productos', 'Corporaciones', 'Año Promedio']
    st.dataframe(country_analysis, use_container_width=True)

def create_moleculas_tab(df):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    # Timeline de moléculas
    fig_timeline = px.scatter(
        df,
        x='Año de Lanzamiento Molécula',
        y='Molécula',
        color='RX-OTC - Molécula',
        title='Timeline de Lanzamiento de Moléculas',
        height=600
    )
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top Moléculas por Número de Productos")
        top_molecules = df.groupby('Molécula').size().sort_values(ascending=False).head(15)
        fig_molecules = px.bar(
            x=top_molecules.values,
            y=top_molecules.index,
            orientation='h',
            title='Moléculas más Utilizadas'
        )
        st.plotly_chart(fig_molecules, use_container_width=True)
    
    with col2:
        st.subheader("🏥 Distribución por ATC1")
        fig_atc = px.pie(
            df,
            names='ATC 1',
            title='Distribución por Categoría ATC1'
        )
        st.plotly_chart(fig_atc, use_container_width=True)

def create_corporaciones_tab(df):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    corp_summary = df.groupby('Corporacion').agg({
        'Molécula': 'nunique',
        'País': 'nunique',
        'Producto': 'nunique'
    }).reset_index()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_scatter = px.scatter(
            corp_summary,
            x='Molécula',
            y='País',
            size='Producto',
            hover_name='Corporacion',
            title='Corporaciones: Moléculas vs Países (tamaño = productos)',
            labels={'Molécula': 'Número de Moléculas', 'País': 'Número de Países'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        top_corps = corp_summary.sort_values('Producto', ascending=False).head(10)
        fig_corps = px.bar(
            top_corps,
            x='Corporacion',
            y='Producto',
            title='Top 10 Corporaciones por Productos'
        )
        fig_corps.update_xaxes(tickangle=45)
        st.plotly_chart(fig_corps, use_container_width=True)
    
    # Tabla comparativa
    st.subheader("🏢 Comparación Detallada de Corporaciones")
    corp_summary_sorted = corp_summary.sort_values('Producto', ascending=False)
    st.dataframe(corp_summary_sorted, use_container_width=True)

def create_tabla_tab(df):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    st.subheader(f"📋 Datos Filtrados ({len(df)} registros)")
    
    # Opción para exportar
    if st.button("📥 Exportar a Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Datos', index=False)
        
        st.download_button(
            label="⬇️ Descargar Excel",
            data=output.getvalue(),
            file_name=f"datos_moleculas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Mostrar tabla con paginación personalizada
    st.write(f"**Total de registros:** {len(df)}")
    
    # Opciones de paginación
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        registros_por_pagina = st.selectbox(
            "Registros por página:",
            [50, 100, 500, 1000, "Todos"],
            index=3
        )
    
    with col2:
        if registros_por_pagina != "Todos":
            total_paginas = (len(df) - 1) // registros_por_pagina + 1
            pagina_actual = st.number_input(
                f"Página (1-{total_paginas}):",
                min_value=1,
                max_value=total_paginas,
                value=1
            )
        else:
            pagina_actual = 1
            total_paginas = 1
    
    # Mostrar datos según paginación
    if registros_por_pagina == "Todos":
        df_display = df
        st.info(f"Mostrando todos los {len(df)} registros")
    else:
        inicio = (pagina_actual - 1) * registros_por_pagina
        fin = min(inicio + registros_por_pagina, len(df))
        df_display = df.iloc[inicio:fin]
        st.info(f"Mostrando registros {inicio + 1} a {fin} de {len(df)} totales")
    
    # Mostrar tabla
    st.dataframe(
        df_display, 
        use_container_width=True, 
        height=600,
        column_config={
            col: st.column_config.TextColumn(width="medium") 
            for col in df_display.columns
        }
    )

# Función principal del dashboard
def main_dashboard():
    st.title("💊 Dashboard de Moléculas Farmacéuticas")
    st.markdown("---")
    
    # Mostrar selector de método de carga (para debugging)
    with st.expander("🔧 Configuración de Carga de Datos"):
        metodo_carga = st.radio(
            "Método de carga:",
            ["Automático (con paginación)", "Límite alto (100k)", "Diagnóstico"],
            index=0
        )
    
    # Cargar datos según el método seleccionado
    if metodo_carga == "Automático (con paginación)":
        df = load_data()
    elif metodo_carga == "Límite alto (100k)":
        df = load_data_alternative()
    else:  # Diagnóstico
        st.info("🔍 Ejecutando diagnóstico de la base de datos...")
        try:
            # Obtener count exacto
            count_response = supabase_client.table('moleculas_esp').select('*', count='exact').execute()
            total_count = count_response.count
            st.success(f"📊 Total de registros en la base: **{total_count:,}**")
            
            # Obtener muestra
            sample_response = supabase_client.table('moleculas_esp').select('*').limit(10).execute()
            st.info(f"📋 Columnas disponibles: {list(pd.DataFrame(sample_response.data).columns) if sample_response.data else 'No hay datos'}")
            
            # Cargar con el método automático
            df = load_data()
            
        except Exception as e:
            st.error(f"❌ Error en diagnóstico: {e}")
            df = pd.DataFrame()
    
    if df.empty:
        st.error("No se pudieron cargar los datos.")
        return
    
    # Crear filtros
    filters = create_filters(df)
    
    # Aplicar filtros
    filtered_df = apply_filters(df, filters)
    
    # Mostrar información del dataset filtrado
    st.info(f"📊 Mostrando {len(filtered_df):,} registros de {len(df):,} totales")
    
    # Crear pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Resumen General", 
        "🌍 Análisis por País", 
        "🧬 Moléculas y Productos", 
        "🏢 Comparación Corporaciones", 
        "📊 Tabla de Datos"
    ])
    
    with tab1:
        create_resumen_tab(filtered_df)
    
    with tab2:
        create_pais_tab(filtered_df)
    
    with tab3:
        create_moleculas_tab(filtered_df)
    
    with tab4:
        create_corporaciones_tab(filtered_df)
    
    with tab5:
        create_tabla_tab(filtered_df)

# Aplicación principal
def main():
    # Inicializar estado de sesión
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Verificar autenticación
    if not st.session_state.authenticated:
        login_page()
    else:
        # Verificar token si existe
        if 'token' in st.session_state:
            if not verify_token(st.session_state.token):
                st.session_state.authenticated = False
                st.error("Sesión expirada. Por favor, inicia sesión nuevamente.")
                st.rerun()
        
        main_dashboard()

if __name__ == "__main__":
    main()