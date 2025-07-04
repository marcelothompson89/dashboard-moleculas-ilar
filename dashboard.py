import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Moléculas Farmacéuticas",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para cargar datos desde Excel
@st.cache_data
def load_data_from_excel(file_path):
    """Cargar datos desde el archivo Excel"""
    try:
        # Intentar cargar el archivo Excel - usar la hoja en inglés por defecto
        df = pd.read_excel(file_path, sheet_name="Base en inglés")
        return df
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo Excel: {e}")
        return pd.DataFrame()

# Función para crear filtros en la barra lateral
def create_filters(df):
    st.sidebar.header("🔍 Filtros de Consulta")
    
    # Filtro por región (columna: "Region")
    if 'Region' in df.columns:
        regiones = sorted(df['Region'].dropna().unique())
        selected_regions = st.sidebar.multiselect("Región", regiones, key="region_filter")
    else:
        selected_regions = []
    
    # Filtrar países basado en regiones seleccionadas (columna: "Country")
    if selected_regions and 'Country' in df.columns:
        df_filtered = df[df['Region'].isin(selected_regions)]
        paises = sorted(df_filtered['Country'].dropna().unique())
    elif 'Country' in df.columns:
        paises = sorted(df['Country'].dropna().unique())
    else:
        paises = []
    
    selected_countries = st.sidebar.multiselect("País", paises, key="country_filter")
    
    # Filtro por molécula (columna: "Molecule")
    if 'Molecule' in df.columns:
        moleculas = sorted(df['Molecule'].dropna().unique())
        selected_molecules = st.sidebar.multiselect("Molécula", moleculas, key="molecule_filter")
    else:
        selected_molecules = []
    
    # Filtro RX/OTC (columna: "RX-OTC - Molecule")
    rx_otc_column = "RX-OTC - Molecule"
    if rx_otc_column in df.columns:
        rx_otc_values = df[rx_otc_column].dropna().unique()
        selected_rx_otc = st.sidebar.multiselect("RX/OTC", rx_otc_values, key="rx_otc_filter")
    else:
        selected_rx_otc = []
        rx_otc_column = None
    
    # Filtro por corporación (columna: "Corporation")
    corp_column = "Corporation"
    if corp_column in df.columns:
        corporaciones = sorted(df[corp_column].dropna().unique())
        selected_corporations = st.sidebar.multiselect("Corporación", corporaciones, key="corp_filter")
    else:
        selected_corporations = []
        corp_column = None
    
    # Filtro por año (columna: "Suma de Molecule Launch Year")
    year_column = "Suma de Molecule Launch Year"
    if year_column in df.columns:
        years = pd.to_numeric(df[year_column], errors='coerce').dropna()
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
    else:
        year_range = (2000, 2025)
        year_column = None
    
    # Botón para limpiar filtros
    if st.sidebar.button("🗑️ Limpiar Filtros", use_container_width=True):
        for key in ['region_filter', 'country_filter', 'molecule_filter', 
                   'rx_otc_filter', 'corp_filter']:
            if key in st.session_state:
                st.session_state[key] = []
        st.rerun()
    
    return {
        'regions': selected_regions,
        'countries': selected_countries,
        'molecules': selected_molecules,
        'rx_otc': selected_rx_otc,
        'corporations': selected_corporations,
        'year_range': year_range,
        'rx_otc_column': rx_otc_column,
        'corp_column': corp_column,
        'year_column': year_column
    }

# Función para aplicar filtros
def apply_filters(df, filters):
    filtered_df = df.copy()
    
    if filters['regions'] and 'Region' in df.columns:
        filtered_df = filtered_df[filtered_df['Region'].isin(filters['regions'])]
    
    if filters['countries'] and 'Country' in df.columns:
        filtered_df = filtered_df[filtered_df['Country'].isin(filters['countries'])]
    
    if filters['molecules'] and 'Molecule' in df.columns:
        filtered_df = filtered_df[filtered_df['Molecule'].isin(filters['molecules'])]
    
    if filters['rx_otc'] and filters['rx_otc_column']:
        filtered_df = filtered_df[filtered_df[filters['rx_otc_column']].isin(filters['rx_otc'])]
    
    if filters['corporations'] and filters['corp_column']:
        filtered_df = filtered_df[filtered_df[filters['corp_column']].isin(filters['corporations'])]
    
    if filters['year_column']:
        year_values = pd.to_numeric(filtered_df[filters['year_column']], errors='coerce')
        filtered_df = filtered_df[
            (year_values >= filters['year_range'][0]) &
            (year_values <= filters['year_range'][1])
        ]
    
    return filtered_df

# Función para la pestaña de resumen
def create_resumen_tab(df, filters):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    # Métricas generales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Productos", f"{len(df):,}")
    
    with col2:
        if 'Molecule' in df.columns:
            st.metric("Moléculas Únicas", f"{df['Molecule'].nunique():,}")
        else:
            st.metric("Moléculas Únicas", "N/A")
    
    with col3:
        if 'Country' in df.columns:
            st.metric("Países", f"{df['Country'].nunique():,}")
        else:
            st.metric("Países", "N/A")
    
    with col4:
        if filters['corp_column']:
            st.metric("Corporaciones", f"{df[filters['corp_column']].nunique():,}")
        else:
            st.metric("Corporaciones", "N/A")
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        if filters['rx_otc_column']:
            rx_otc_counts = df[filters['rx_otc_column']].value_counts()
            fig_pie = px.pie(
                values=rx_otc_counts.values,
                names=rx_otc_counts.index,
                title='Distribución RX vs OTC'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Columna RX/OTC no encontrada")
    
    with col2:
        if filters['year_column']:
            year_data = pd.to_numeric(df[filters['year_column']], errors='coerce').dropna()
            fig_hist = px.histogram(
                x=year_data,
                title='Lanzamientos por Año',
                nbins=20
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("Columna de año no encontrada")
    
    # Gráfico de países
    if 'Country' in df.columns:
        top_countries = df.groupby('Country').size().sort_values(ascending=False).head(10)
        fig_countries = px.bar(
            x=top_countries.index,
            y=top_countries.values,
            title='Top 10 Países por Número de Productos',
            labels={'x': 'País', 'y': 'Número de Productos'}
        )
        fig_countries.update_xaxes(tickangle=45)
        st.plotly_chart(fig_countries, use_container_width=True)

# Función para la pestaña de países
def create_pais_tab(df, filters):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    if 'Country' not in df.columns:
        st.warning("Columna 'Country' no encontrada en los datos.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if 'Region' in df.columns:
            # Crear datos para treemap
            treemap_data = df.groupby(['Region', 'Country']).size().reset_index(name='count')
            fig_treemap = px.treemap(
                treemap_data,
                path=['Region', 'Country'],
                values='count',
                title='Distribución de Productos por Región y País'
            )
            st.plotly_chart(fig_treemap, use_container_width=True)
        else:
            st.info("Columna 'Region' no encontrada")
    
    with col2:
        if filters['rx_otc_column']:
            country_rx_otc = df.groupby(['Country', filters['rx_otc_column']]).size().reset_index(name='count')
            fig_bar = px.bar(
                country_rx_otc,
                x='Country',
                y='count',
                color=filters['rx_otc_column'],
                title='RX vs OTC por País'
            )
            fig_bar.update_xaxes(tickangle=45)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Columna RX/OTC no encontrada")
    
    # Tabla de análisis por país
    st.subheader("📊 Análisis por País")
    
    # Preparar datos para la tabla usando el formato correcto de agg
    agg_dict = {}
    if 'Molecule' in df.columns:
        agg_dict['Molecule'] = 'nunique'
    if 'Product' in df.columns:
        agg_dict['Product'] = 'nunique'
    if filters['corp_column']:
        agg_dict[filters['corp_column']] = 'nunique'
    
    # Agregar conteo total
    country_analysis = df.groupby('Country').agg(agg_dict)
    country_analysis['Total_Registros'] = df.groupby('Country').size()
    
    # Renombrar columnas para mejor presentación
    column_rename = {}
    if 'Molecule' in country_analysis.columns:
        column_rename['Molecule'] = 'Moléculas_Únicas'
    if 'Product' in country_analysis.columns:
        column_rename['Product'] = 'Productos_Únicos'
    if filters['corp_column'] and filters['corp_column'] in country_analysis.columns:
        column_rename[filters['corp_column']] = 'Corporaciones_Únicas'
    
    country_analysis = country_analysis.rename(columns=column_rename).reset_index()
    
    if filters['year_column']:
        avg_years = df.groupby('Country')[filters['year_column']].apply(
            lambda x: pd.to_numeric(x, errors='coerce').mean()
        ).round(1)
        country_analysis['Año_Promedio_Lanzamiento'] = country_analysis['Country'].map(avg_years)
    
    # Ordenar por total de registros
    country_analysis = country_analysis.sort_values('Total_Registros', ascending=False)
    st.dataframe(country_analysis, use_container_width=True)

# Función para la pestaña de moléculas
def create_moleculas_tab(df, filters):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    if 'Molecule' not in df.columns:
        st.warning("Columna 'Molecule' no encontrada en los datos.")
        return
    
    # Timeline de moléculas
    if filters['year_column']:
        timeline_data = df.copy()
        timeline_data[filters['year_column']] = pd.to_numeric(timeline_data[filters['year_column']], errors='coerce')
        timeline_data = timeline_data.dropna(subset=[filters['year_column']])
        
        # Tomar una muestra para mejor visualización
        if len(timeline_data) > 1000:
            timeline_data = timeline_data.sample(n=1000, random_state=42)
        
        fig_timeline = px.scatter(
            timeline_data,
            x=filters['year_column'],
            y='Molecule',
            color=filters['rx_otc_column'] if filters['rx_otc_column'] else None,
            title='Timeline de Lanzamiento de Moléculas (muestra)',
            height=600
        )
        fig_timeline.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top Moléculas por Número de Productos")
        top_molecules = df.groupby('Molecule').size().sort_values(ascending=False).head(15)
        fig_molecules = px.bar(
            x=top_molecules.values,
            y=top_molecules.index,
            orientation='h',
            title='Moléculas más Utilizadas'
        )
        fig_molecules.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_molecules, use_container_width=True)
    
    with col2:
        # Distribución por ATC1
        if 'ATC1' in df.columns:
            st.subheader("🏥 Distribución por ATC1")
            atc_counts = df['ATC1'].value_counts()
            fig_atc = px.pie(
                values=atc_counts.values,
                names=atc_counts.index,
                title='Distribución por ATC1'
            )
            st.plotly_chart(fig_atc, use_container_width=True)
        else:
            st.info("Columna ATC1 no encontrada")

# Función para la pestaña de corporaciones
def create_corporaciones_tab(df, filters):
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return
    
    if not filters['corp_column']:
        st.warning("Columna de corporación no encontrada en los datos.")
        return
    
    # Preparar datos de agregación usando el formato correcto
    agg_dict = {}
    if 'Molecule' in df.columns:
        agg_dict['Molecule'] = 'nunique'
    if 'Country' in df.columns:
        agg_dict['Country'] = 'nunique'
    if 'Product' in df.columns:
        agg_dict['Product'] = 'nunique'
    
    corp_summary = df.groupby(filters['corp_column']).agg(agg_dict)
    corp_summary['Registros_Totales'] = df.groupby(filters['corp_column']).size()
    
    # Renombrar columnas para mejor presentación
    column_rename = {}
    if 'Molecule' in corp_summary.columns:
        column_rename['Molecule'] = 'Moléculas'
    if 'Country' in corp_summary.columns:
        column_rename['Country'] = 'Países'
    if 'Product' in corp_summary.columns:
        column_rename['Product'] = 'Productos'
    
    corp_summary = corp_summary.rename(columns=column_rename).reset_index()
    corp_summary = corp_summary.sort_values('Registros_Totales', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if 'Moléculas' in corp_summary.columns and 'Países' in corp_summary.columns:
            fig_scatter = px.scatter(
                corp_summary.head(20),  # Top 20 para mejor visualización
                x='Moléculas',
                y='Países',
                size='Registros_Totales',
                hover_name=filters['corp_column'],
                title='Top 20 Corporaciones: Moléculas vs Países (tamaño = registros totales)',
                labels={'Moléculas': 'Número de Moléculas', 'Países': 'Número de Países'}
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        top_corps = corp_summary.head(10)
        fig_corps = px.bar(
            top_corps,
            x=filters['corp_column'],
            y='Registros_Totales',
            title='Top 10 Corporaciones por Registros'
        )
        fig_corps.update_xaxes(tickangle=45)
        st.plotly_chart(fig_corps, use_container_width=True)
    
    # Tabla comparativa
    st.subheader("🏢 Comparación Detallada de Corporaciones")
    st.dataframe(corp_summary, use_container_width=True)

# Función para la pestaña de tabla
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
    
    # Mostrar información sobre las columnas
    st.write(f"**Total de registros:** {len(df)}")
    st.write(f"**Columnas disponibles:** {', '.join(df.columns)}")
    
    # Opciones de paginación
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        registros_por_pagina = st.selectbox(
            "Registros por página:",
            [50, 100, 500, 1000, "Todos"],
            index=1
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
    st.dataframe(df_display, use_container_width=True, height=600)

# Función principal
def main():
    st.title("💊 Dashboard de Moléculas Farmacéuticas")
    st.markdown("---")
    
    # Selector de archivo
    st.sidebar.header("📁 Archivo de Datos")
    
    # Opción para seleccionar hoja del Excel
    sheet_option = st.sidebar.selectbox(
        "Seleccionar hoja:",
        ["Base en inglés", "Base en español"],
        index=0
    )
    
    # Opción 1: Usar archivo por defecto
    use_default_file = st.sidebar.checkbox("Usar archivo por defecto", value=True)
    
    if use_default_file:
        file_path = "Version final Extracto base de datos Mar 2023.xlsx"
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_option)
            st.sidebar.success(f"✅ Archivo cargado: {sheet_option}")
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
            df = pd.DataFrame()
    else:
        # Opción 2: Cargar archivo personalizado
        uploaded_file = st.sidebar.file_uploader(
            "Cargar archivo Excel",
            type=['xlsx', 'xls'],
            help="Sube tu archivo Excel con los datos de moléculas"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, sheet_name=sheet_option)
                st.sidebar.success("✅ Archivo cargado exitosamente")
            except Exception as e:
                st.sidebar.error(f"❌ Error: {e}")
                df = pd.DataFrame()
        else:
            st.sidebar.warning("⚠️ Por favor, sube un archivo Excel")
            df = pd.DataFrame()
    
    if df.empty:
        st.warning("📄 No hay datos para mostrar. Asegúrate de que el archivo Excel esté disponible.")
        st.info("💡 **Instrucciones:**")
        st.info("- Coloca el archivo 'Version final Extracto base de datos Mar 2023.xlsx' en el mismo directorio que este script")
        st.info("- O desmarca la opción 'Usar archivo por defecto' y sube tu propio archivo Excel")
        return
    
    # Mostrar información del dataset
    st.success(f"✅ Datos cargados exitosamente: {len(df):,} registros, {len(df.columns)} columnas")
    
    # Mostrar columnas disponibles para debug
    with st.expander("🔍 Ver columnas disponibles"):
        st.write("**Columnas en el dataset:**")
        for i, col in enumerate(df.columns, 1):
            st.write(f"{i}. {col}")
    
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
        create_resumen_tab(filtered_df, filters)
    
    with tab2:
        create_pais_tab(filtered_df, filters)
    
    with tab3:
        create_moleculas_tab(filtered_df, filters)
    
    with tab4:
        create_corporaciones_tab(filtered_df, filters)
    
    with tab5:
        create_tabla_tab(filtered_df)

if __name__ == "__main__":
    main()