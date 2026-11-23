import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from scipy import stats

st.set_page_config(page_title='Sismos significativos 1965-2016', page_icon='🌎', layout='wide')
sns.set_theme(style='whitegrid', context='notebook')

ETIQUETAS_TIPO = {
    'Earthquake': 'Sismo natural',
    'Nuclear Explosion': 'Explosión nuclear',
    'Explosion': 'Explosión',
    'Rock Burst': 'Estallido de roca',
}
CLASES_PROF = ['Superficial (≤70 km)', 'Intermedia (70–300 km)', 'Profunda (>300 km)']
CLASES_MAG = ['Moderado (5.5–5.9)', 'Fuerte (6.0–6.9)', 'Mayor (7.0–7.9)', 'Gran (≥8.0)']
COLORES_PROF = ['#e76f51', '#2a9d8f', '#264653']


@st.cache_data
def cargar_datos(ruta='database.csv'):
    df = pd.read_csv(ruta)
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
    sin_fecha = df['Datetime'].isna()
    df.loc[sin_fecha, 'Datetime'] = (pd.to_datetime(df.loc[sin_fecha, 'Date'], errors='coerce', utc=True)
                                     .dt.tz_localize(None))
    df['Year'] = df['Datetime'].dt.year.astype(int)
    df['Tipo'] = df['Type'].map(ETIQUETAS_TIPO)
    df['Depth_Class'] = pd.cut(df['Depth'], bins=[-np.inf, 70, 300, np.inf], labels=CLASES_PROF)
    df['Magnitude_Class'] = pd.cut(df['Magnitude'], bins=[-np.inf, 6.0, 7.0, 8.0, np.inf],
                                   labels=CLASES_MAG, right=False)
    return df


def prueba_t(datos):
    sismo = datos.loc[datos['Type'] == 'Earthquake', 'Depth'].dropna()
    nuclear = datos.loc[datos['Type'] == 'Nuclear Explosion', 'Depth'].dropna()
    if len(sismo) < 2 or len(nuclear) < 2:
        return None
    t, p = stats.ttest_ind(sismo, nuclear, equal_var=False)
    n1, n2 = len(sismo), len(nuclear)
    sp = np.sqrt(((n1 - 1) * sismo.var() + (n2 - 1) * nuclear.var()) / (n1 + n2 - 2))
    d = (sismo.mean() - nuclear.mean()) / sp
    u, p_mw = stats.mannwhitneyu(sismo, nuclear, alternative='two-sided')
    return {'n1': n1, 'n2': n2, 'media1': sismo.mean(), 'media2': nuclear.mean(),
            'mediana1': sismo.median(), 'mediana2': nuclear.median(),
            't': t, 'p': p, 'd': d, 'u': u, 'p_mw': p_mw}


df = cargar_datos()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header('Filtros')
    st.caption('Todos los números y gráficos del tablero cambian según lo que elija aquí.')

    tipos = st.multiselect('Tipo de evento', options=list(ETIQUETAS_TIPO.values()),
                           default=list(ETIQUETAS_TIPO.values()))
    clases_prof = st.multiselect('Profundidad del evento', options=CLASES_PROF, default=CLASES_PROF)
    rango_mag = st.slider('Magnitud', min_value=5.5, max_value=9.1, value=(5.5, 9.1), step=0.1)
    rango_anio = st.slider('Años', min_value=int(df['Year'].min()), max_value=int(df['Year'].max()),
                           value=(int(df['Year'].min()), int(df['Year'].max())))

    st.divider()
    st.caption('Fuente: U.S. Geological Survey (USGS), *Significant Earthquakes, 1965–2016*, vía Kaggle.')

df_f = df[df['Tipo'].isin(tipos)
          & df['Depth_Class'].isin(clases_prof)
          & df['Magnitude'].between(*rango_mag)
          & df['Year'].between(*rango_anio)]

# ---------------- Encabezado ----------------
st.title('Sismos significativos en el mundo, 1965–2016')
st.markdown('Tablero interactivo construido sobre el análisis exploratorio del catálogo de sismos de magnitud '
            '5.5 o mayor del Servicio Geológico de Estados Unidos (USGS). Muestra **dónde**, **cuándo**, '
            '**qué tan fuertes** y **a qué profundidad** ocurrieron los sismos más importantes en 52 años.')

if df_f.empty:
    st.warning('Ningún registro cumple los filtros seleccionados. Amplíe el rango de magnitud o de años, '
               'o seleccione más tipos de evento.')
    st.stop()

tab_exp, tab_vis, tab_est, tab_hal = st.tabs(['Exploración de datos', 'Visualizaciones',
                                              'Validación estadística', 'Hallazgos'])

# ---------------- Exploración de datos ----------------
with tab_exp:
    st.subheader('Resumen de los registros seleccionados')
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric('Registros', f'{len(df_f):,}'.replace(',', ' '),
              delta=f'{len(df_f) / len(df) * 100:.1f} % del total', delta_color='off')
    c2.metric('Magnitud media', f'{df_f["Magnitude"].mean():.2f}')
    c3.metric('Desv. estándar magnitud', f'{df_f["Magnitude"].std():.2f}' if len(df_f) > 1 else 'n/d')
    c4.metric('Profundidad media', f'{df_f["Depth"].mean():.1f} km')
    c5.metric('Desv. estándar profundidad', f'{df_f["Depth"].std():.1f} km' if len(df_f) > 1 else 'n/d')

    st.caption('La desviación estándar indica qué tan dispersos están los valores alrededor del promedio: '
               'entre más alta, más diferentes son los eventos entre sí.')

    tabla = (df_f[['Datetime', 'Tipo', 'Latitude', 'Longitude', 'Magnitude', 'Magnitude Type',
                   'Depth', 'Depth_Class', 'Magnitude_Class']]
             .rename(columns={'Datetime': 'Fecha y hora (UTC)', 'Latitude': 'Latitud',
                              'Longitude': 'Longitud', 'Magnitude': 'Magnitud',
                              'Magnitude Type': 'Tipo de magnitud', 'Depth': 'Profundidad (km)',
                              'Depth_Class': 'Clase de profundidad', 'Magnitude_Class': 'Clase de magnitud'})
             .sort_values('Fecha y hora (UTC)'))
    st.dataframe(tabla, width='stretch', hide_index=True, height=420)

    with st.expander('Ver estadísticas descriptivas de magnitud y profundidad'):
        desc = df_f[['Magnitude', 'Depth']].describe().T
        desc['CV (%)'] = desc['std'] / desc['mean'] * 100
        desc.index = ['Magnitud', 'Profundidad (km)']
        st.dataframe(desc.round(2), width='stretch')

# ---------------- Visualizaciones ----------------
with tab_vis:
    st.subheader('Gráficos del análisis exploratorio')
    st.caption('Gráficos de la Parte 3 de la Tarea 3, recalculados con los filtros activos.')

    col_a, col_b = st.columns(2)

    with col_a:
        conteo = df_f['Magnitude Type'].value_counts().head(10)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.barplot(x=conteo.values, y=conteo.index, hue=conteo.index, palette='viridis', legend=False, ax=ax)
        for i, v in enumerate(conteo.values):
            ax.text(v, i, f' {v:,}', va='center', fontsize=9)
        ax.set_xlim(0, conteo.max() * 1.15)
        ax.set_title('Eventos por tipo de magnitud (10 más frecuentes)')
        ax.set_xlabel('Número de eventos')
        ax.set_ylabel('Tipo de magnitud')
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    with col_b:
        presentes = [c for c in CLASES_PROF if c in df_f['Depth_Class'].unique()]
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.violinplot(data=df_f, x='Depth_Class', y='Magnitude', hue='Depth_Class', order=presentes,
                       hue_order=presentes, palette='Set2', inner='quartile', cut=0, legend=False, ax=ax)
        n_clase = df_f['Depth_Class'].value_counts().reindex(presentes)
        ax.set_xticks(range(len(presentes)))
        ax.set_xticklabels([f'{c}\n(n = {n:,})' for c, n in n_clase.items()], fontsize=9)
        ax.set_title('Magnitud según la profundidad del sismo')
        ax.set_xlabel('Clase de profundidad')
        ax.set_ylabel('Magnitud')
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
    sns.boxplot(x=df_f['Magnitude'], color='#f4a261',
                flierprops=dict(marker='o', markersize=3, alpha=0.4), ax=axes[0])
    axes[0].set_title('Distribución de la magnitud')
    axes[0].set_xlabel('Magnitud')
    sns.boxplot(x=df_f['Depth'], color='#2a9d8f',
                flierprops=dict(marker='o', markersize=3, alpha=0.4), ax=axes[1])
    axes[1].set_title('Distribución de la profundidad')
    axes[1].set_xlabel('Profundidad (km)')
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    por_tipo = df_f.groupby(['Year', 'Tipo']).size().unstack(fill_value=0)
    mag_anual = df_f.groupby('Year')['Magnitude'].agg(['mean', 'max'])
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    for tipo, color in [('Sismo natural', 'tab:blue'), ('Explosión nuclear', 'tab:red')]:
        if tipo in por_tipo.columns:
            axes[0].plot(por_tipo.index, por_tipo[tipo], marker='o', ms=3, color=color, label=tipo)
    axes[0].set_title('Eventos registrados por año según tipo de evento')
    axes[0].set_ylabel('Eventos por año')
    if axes[0].get_legend_handles_labels()[0]:
        axes[0].legend(title='Tipo de evento')
    axes[1].plot(mag_anual.index, mag_anual['max'], color='tab:purple', marker='o', ms=3,
                 label='Magnitud máxima del año')
    axes[1].plot(mag_anual.index, mag_anual['mean'], color='tab:green', marker='s', ms=3,
                 label='Magnitud promedio del año')
    axes[1].set_title('Magnitud máxima y promedio por año')
    axes[1].set_xlabel('Año')
    axes[1].set_ylabel('Magnitud')
    axes[1].legend()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 6.5))
    sns.scatterplot(data=df_f, x='Longitude', y='Latitude', size='Magnitude', sizes=(4, 130),
                    hue='Depth_Class', hue_order=CLASES_PROF, palette=COLORES_PROF,
                    alpha=0.55, edgecolor=None, ax=ax)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_title('Epicentros (tamaño = magnitud, color = clase de profundidad)')
    ax.set_xlabel('Longitud (°)')
    ax.set_ylabel('Latitud (°)')
    ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', title='Profundidad / Magnitud', fontsize=9)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

# ---------------- Validación estadística ----------------
with tab_est:
    st.subheader('¿Los sismos naturales y las explosiones nucleares ocurren a profundidades distintas?')
    st.markdown('En la Tarea 3 se comparó la profundidad de los sismos naturales con la de las explosiones '
                'nucleares de prueba para saber si la diferencia es real o si pudo darse por casualidad.')

    res = prueba_t(df_f)
    if res is None:
        st.info('Con los filtros actuales no hay suficientes sismos naturales y explosiones nucleares para '
                'hacer la comparación. Incluya ambos tipos de evento y años anteriores a 1980, que es cuando '
                'aparecen las explosiones en el catálogo.')
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric('Profundidad promedio, sismos naturales', f'{res["media1"]:.1f} km',
                  help=f'{res["n1"]:,} eventos')
        c2.metric('Profundidad promedio, explosiones nucleares', f'{res["media2"]:.1f} km',
                  help=f'{res["n2"]:,} eventos')
        c3.metric('Diferencia', f'{res["media1"] - res["media2"]:.1f} km')

        col_g, _ = st.columns([3, 2])
        fig, ax = plt.subplots(figsize=(7, 2.6))
        comp = pd.DataFrame({'Tipo de evento': ['Sismos naturales', 'Explosiones nucleares'],
                             'Profundidad promedio (km)': [res['media1'], res['media2']]})
        sns.barplot(data=comp, x='Profundidad promedio (km)', y='Tipo de evento', hue='Tipo de evento',
                    palette=['#264653', '#e76f51'], legend=False, ax=ax)
        ax.set_title('¿A qué profundidad ocurre cada tipo de evento, en promedio?')
        ax.set_ylabel('')
        fig.tight_layout()
        col_g.pyplot(fig)
        plt.close(fig)

        if res['p'] < 0.05:
            st.success(
                f'**Conclusión:** la diferencia es real y no se explica por casualidad. Los sismos naturales '
                f'se originan en promedio a {res["media1"]:.0f} km bajo la superficie, mientras que las '
                f'explosiones nucleares se registran prácticamente en la superficie ({res["media2"]:.1f} km). '
                f'Es decir, la profundidad sirve como señal para distinguir un sismo de origen natural de una '
                f'explosión provocada por el ser humano.')
        else:
            st.warning('**Conclusión:** con los registros seleccionados no hay pruebas suficientes para afirmar '
                       'que la profundidad sea distinta entre ambos tipos de evento.')

        st.caption('Esta comparación muestra que los dos grupos son diferentes, pero no explica por sí sola la '
                   'causa. La razón está en el origen físico de cada evento: los sismos nacen del movimiento de '
                   'las placas a decenas o cientos de kilómetros, y las pruebas nucleares se hacían cerca de la '
                   'superficie.')

        with st.expander('Detalle técnico de la prueba (para quien lo necesite)'):
            st.markdown(
                f'- Prueba *t* de Welch para dos muestras independientes, α = 0.05\n'
                f'- t = {res["t"]:.2f}; p = {res["p"]:.2e}\n'
                f'- Tamaño del efecto (d de Cohen) = {res["d"]:.2f}\n'
                f'- Prueba de respaldo no paramétrica (Mann-Whitney): U = {res["u"]:,.0f}; p = {res["p_mw"]:.2e}\n'
                f'- n sismos naturales = {res["n1"]:,}; n explosiones nucleares = {res["n2"]:,}\n'
                f'- Medianas: {res["mediana1"]:.1f} km y {res["mediana2"]:.1f} km')

# ---------------- Hallazgos ----------------
with tab_hal:
    st.subheader('Lo que dicen los datos, en palabras sencillas')

    st.markdown('### ¿Qué analicé?')
    st.markdown(
        'Un registro de **23 412 sismos fuertes** (magnitud 5.5 o más) ocurridos en todo el mundo entre 1965 y '
        '2016, publicado por el Servicio Geológico de Estados Unidos. Cada registro indica cuándo y dónde '
        'ocurrió el evento, qué tan fuerte fue y a qué profundidad se originó. El registro también incluye 180 '
        'eventos que no son sismos naturales, casi todos explosiones nucleares de prueba.')

    st.markdown('### ¿Qué encontré?')
    st.markdown(
        '1. **La gran mayoría de los sismos fuertes son del escalón más bajo.** Siete de cada diez están entre '
        '5.5 y 5.9. En 52 años solo hubo 40 sismos de magnitud 8 o más.\n'
        '2. **Ocho de cada diez sismos se originan cerca de la superficie**, a menos de 70 km de profundidad.\n'
        '3. **Los sismos no se reparten al azar.** Se concentran en franjas bien definidas: el llamado Cinturón '
        'de Fuego, que rodea el océano Pacífico e incluye la costa pacífica y los Andes de Suramérica, y una '
        'franja que va del Mediterráneo hasta Indonesia.\n'
        '4. **Cada año se registran más sismos.** Se pasó de unos 240 por año en 1965 a entre 450 y 550 en los '
        'años recientes.\n'
        '5. **Las explosiones nucleares ocurren en la superficie y los sismos naturales mucho más abajo**, a 71 km '
        'en promedio. Esta diferencia es clara y no es fruto de la casualidad.\n'
        '6. **Entre más estaciones registran la profundidad de un sismo, más estaciones suelen registrar también '
        'su magnitud.** Las dos cifras suben juntas porque ambas dependen de cuántas estaciones de medición había '
        'cerca del evento, no porque una produzca la otra. Este dato solo existe para una pequeña parte de los '
        'sismos, los más recientes y mejor monitoreados.')

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        clases = df_f['Magnitude_Class'].value_counts().reindex(CLASES_MAG).fillna(0)
        nombres = ['Moderados\n(5.5 a 5.9)', 'Fuertes\n(6 a 6.9)', 'Muy fuertes\n(7 a 7.9)', 'Grandes\n(8 o más)']
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sns.barplot(x=nombres, y=clases.values, hue=nombres, palette='YlOrRd', legend=False, ax=ax)
        for i, v in enumerate(clases.values):
            ax.text(i, v, f'{int(v):,}'.replace(',', ' '), ha='center', va='bottom', fontsize=10)
        ax.set_title('¿Qué tan fuertes son los sismos registrados?')
        ax.set_xlabel('')
        ax.set_ylabel('Cantidad de sismos')
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    with col_h2:
        anual = df_f[df_f['Type'] == 'Earthquake'].groupby('Year').size()
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(anual.index, anual.values, marker='o', ms=3, color='tab:blue', label='Sismos de cada año')
        if len(anual) >= 5:
            ax.plot(anual.index, anual.rolling(5, center=True).mean(), lw=2.5, color='tab:orange',
                    label='Promedio de cada 5 años')
        ax.set_title('¿Cuántos sismos fuertes se registran cada año?')
        ax.set_xlabel('Año')
        ax.set_ylabel('Cantidad de sismos')
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    st.markdown('### ¿Qué significa?')
    st.markdown(
        '1. Los sismos moderados son los que más se repiten, así que son el escenario que hay que esperar con '
        'mayor frecuencia. Los grandes son raros, pero causan los daños más graves y deben tenerse en cuenta como '
        'el caso extremo.\n'
        '2. Un sismo cercano a la superficie sacude con más fuerza el terreno y las construcciones que uno '
        'profundo de la misma magnitud. Como la mayoría son superficiales, el riesgo para viviendas, puentes y '
        'vías es alto.\n'
        '3. El riesgo está concentrado en ciertas regiones. Colombia está dentro del Cinturón de Fuego, por lo '
        'que hace parte de las zonas más expuestas del planeta.\n'
        '4. El aumento de sismos por año no quiere decir que la Tierra tiemble más. Lo más probable es que '
        'refleje que con los años se instalaron más y mejores estaciones de medición, que detectan eventos que '
        'antes no quedaban registrados.\n'
        '5. La profundidad sirve para distinguir un sismo natural de una explosión hecha por el ser humano.\n'
        '6. Que dos cifras suban juntas no prueba que una cause la otra. Esta relación habla de qué tan bien '
        'equipada estaba la red de medición, no de cómo es el sismo, y no sirve para hacer predicciones sobre '
        'los sismos en general.')

    st.markdown('### ¿Qué se recomendaría?')
    st.markdown(
        '- Exigir y revisar el cumplimiento de las normas de construcción sismorresistente, con prioridad en '
        'las zonas del Cinturón de Fuego.\n'
        '- Diseñar los planes de emergencia pensando en sismos superficiales, que son los más frecuentes y los '
        'que más sacuden el terreno.\n'
        '- No usar el conteo anual de sismos para afirmar que la actividad sísmica va en aumento; para comparar '
        'épocas conviene usar periodos con una cobertura de estaciones parecida.\n'
        '- Separar las explosiones y otros eventos artificiales antes de cualquier estudio sobre sismos naturales.\n'
        '- Al revisar cifras que se mueven juntas, preguntar siempre qué hay detrás antes de tomar decisiones '
        'con base en esa relación.')

    st.divider()
    st.caption('Elaborado por Hermes Santiago Reyes Bermúdez · Programación para el Análisis de Datos '
               '(203008069A_2204), grupo 31 · Universidad Nacional Abierta y a Distancia (UNAD) · 2026')
