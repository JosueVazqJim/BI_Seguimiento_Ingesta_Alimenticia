import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from assets.db import Connection
from assets.graficas import Graphs
import dash_table
import numpy as np
import pandas as pd

dbc_css = ("https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.3.3/lux/bootstrap.min.css")

connection = Connection('root', 'Normita1230', 'proyectoFinal')
connection.connect()
graficos = Graphs()  # Instanciamos una vez aquí

PLAN_MAP = {
    1: "Plan Básico", 2: "Plan Medio", 3: "Plan Alto", 4: "Todos los planes"
}

plans = connection.fetchUniqueData('id_plan', 'cubo_dash_1')
plans.append(4)  # Agregar 'Todos los planes'

# Inicializar la aplicación Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css])

cubo_dash_1 = connection.fetchAllData('cubo_dash_1')
cubo_dash_2 = connection.fetchAllData('cubo_dash_2')
cubo_dash_3 = connection.fetchAllData('cubo_dash_3')
cubo_dash_4 = connection.fetchAllData('cubo_dash_4')
tabla= connection.tablaDesercion()
# Formato para el DataFrame
tabla['tasa_retencion'] = tabla['tasa_retencion'].round(2)
tabla['tasa_desercion'] = tabla['tasa_desercion'].round(2)

app.layout = html.Div([
    # Sidebar
    dbc.Row([
        dbc.Col([
            # Título y Dropdown para filtro
            html.Div([
                html.H3("Retención y deserción de pacientes", className="text-primary mb-4"),
            ], style={"padding": "20px"}),
            html.Div([
                dash_table.DataTable(
                    id='tabla',  
                    columns=[  # Definir las columnas de la tabla
                        {'name': col, 'id': col} for col in tabla.columns  # Usar las columnas del DataFrame
                    ],
                    data=tabla.to_dict('records'),  # Pasar los datos del DataFrame como registros
                    style_table={'height': '100%', 'overflowY': 'auto'},  # Permitir desplazamiento vertical
                    style_cell={  # Estilo para las celdas
                        'textAlign': 'center',
                        'padding': '10px',
                        'fontSize': '14px',  # Aumentar el tamaño de la fuente para mejor legibilidad
                        'fontFamily': 'Arial',
                        'border': '1px solid #ddd',
                        'minWidth': '100px',  # Asegurarse de que las celdas no se vean demasiado pequeñas
                        'backgroundColor': '#f9f9f9',  # Color de fondo de las celdas
                        'color': 'black'  # Color del texto
                    },
                    style_header={  # Estilo para los encabezados
                        'backgroundColor': '#3e3e3e',  # Color de fondo de la cabecera
                        'fontWeight': 'bold',
                        'textAlign': 'center',
                        'fontSize': '16px',  # Aumentar el tamaño del texto en los encabezados
                        'color': 'white'  # Color del texto en la cabecera
                    },
                    style_data={'whiteSpace': 'normal'},  # Permitir que el texto se ajuste en múltiples líneas si es necesario
                    style_data_conditional=[  # Estilo condicional para filas específicas
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#d2d1d1'  # Color alterno para filas impares
                        },
                        {
                            'if': {'row_index': 'even'},
                            'backgroundColor': '#ffffff'  # Color alterno para filas pares
                        }
                    ]
                )
            ], style={"background-color": "#f1f3f5", "margin-top": "20px"}),

            html.Div([
                        dcc.Graph(
                            id='grafico-calor1',  
                            config={'displayModeBar': False},
                            style={'height': '100%'}  
                        )
                    ], style={"height": "350px", "background-color": "#f1f3f5", "margin-top": "20px"}), 
        ], width=3, className="bg-body-tertiary text-light", style={"height-auto": "100vh", "padding": "20px"}),  

        dbc.Col([
            html.Div([
                # Espacio para los gráficos en fila
                dbc.Row([
                    dbc.Col(
                        html.Div([
                            dcc.Graph(
                                id='grafico-grande',  
                                config={'displayModeBar': False},
                                style={'height': '100%'}  
                            )
                        ], style={"height": "400px", "background-color": "#f1f3f5", "margin-top": "0px"}), 
                        width=12
                    ),
                ], className="my-4"),  
                html.Span("Filtrar por plan", className="text-primary mb-2", style={"margin-top": "0px"}), 

                dcc.Dropdown(
                    id='plan-dropdown',
                    options=[{'label': PLAN_MAP.get(plan, plan), 'value': plan} for plan in plans],
                    value=plans[3],  # Valor por defecto
                    placeholder="Selecciona un plan",
                    style={'width': '50%', 'margin-top': '10px'} 
                ),
                dbc.Row([
                    dbc.Col(
                        html.Div([
                            dcc.Graph(
                                id='grafica-frecuencia1',  
                                config={'displayModeBar': False},
                                style={'height': '100%'}  
                            )
                        ], style={"height": "350px", "background-color": "#f1f3f5", "margin-top": "20px"}), 
                        width=6
                    ),  
                    
                    dbc.Col(
                        html.Div([
                            dcc.Graph(
                                id='grafica-frecuencia2',  
                                config={'displayModeBar': False}, 
                                style={'height': '100%'}  
                            )
                        ], style={"height": "350px", "background-color": "#f1f3f5", "margin-top": "20px"}), 
                        width=6
                    ),
                ], className="my-4"),
            ], style={"padding-left": "20px", "padding-right": "20px", "overflow-y": "auto"})
        ], width=9, style={ "height": "100vh", "overflow-y": "auto"}, class_name="bg-light"),  

    ], style={'margin': '0', 'padding': '0', 'overflow-x': 'hidden'}),  

    # Almacenamiento de estado seleccionado
    dcc.Store(id='selected-plan', data='')  
], style={"overflow-x": "hidden", "height": "100vh", "margin": "0", "padding": "0"})  

@app.callback(
    Output('selected-plan', 'data'),
    Input('plan-dropdown', 'value')  
)
def update_selected_plan(selected_plan):
    return selected_plan

@app.callback(
    Output('grafica-frecuencia1', 'figure'),
    Output('grafica-frecuencia2', 'figure'),
    Output('grafico-calor1', 'figure'),
    Output('grafico-grande', 'figure'),
    Input('plan-dropdown', 'value')  
)
def update_graph(plan):
    if plan == 4:  # Si se selecciona 'Todos los planes'
        fig_freq1 = graphConsultasFrecuenciaTodosPlanes(cubo_dash_1, 'num_consulta', 'conteo_total', 'Distribución de frecuencias para Todos los Planes', ["#636EFA", "#FF7F0E", "#2CA02C"], 'Consulta', 'Frecuencia')
        fig_freq2 = graphConsultasFrecuenciaTodosPlanes(cubo_dash_2, 'num_consulta', 'conteo_total', 'Frecuencia de desecion por consulta', ["#636EFA", "#FF7F0E", "#2CA02C"], 'Consulta', 'Frecuencia')
    else:
        fig_freq1 = graphConsultasFrecuencia(plan, cubo_dash_1, 'num_consulta', 'conteo_total', 'Distribución de frecuencias por Consulta para Diferentes Planes', "#636EFA", 'Consulta', 'Frecuencia')
        fig_freq2 = graphConsultasFrecuencia(plan, cubo_dash_2, 'num_consulta', 'conteo_total', 'Frecuencia de desercion por consulta', "#FF7F0E", 'Consulta', 'Frecuencia')

    fig_calor = scatter(cubo_dash_3, "Pacientes Totales vs Tasa de Deserción", "Rango calorico", "Tasa de Deserción (%")
    fig_grande = graphTazaDeserciones(cubo_dash_4, 'Evolución de la Deserción Mensual por Año', ["#9500f6", "#00f604"], 'Meses', 'Numero de pacientes Inactivos')
    
    return fig_freq1, fig_freq2, fig_calor, fig_grande


def graphConsultasFrecuencia(plan, df, x_col, y_col, title, color, label_x, label_y):
    nuevo = df[df['id_plan'] == plan]
    nuevo_contado = nuevo.groupby(x_col).agg(
        conteo_total=('conteo', 'sum')).reset_index()
    fig = graficos.createLineGraph(nuevo_contado, x_col, [y_col], title, [color], label_x, label_y)
    return fig

def graphConsultasFrecuenciaTodosPlanes(df, x_col, y_col, title, color_list, label_x, label_y):
    nuevo = df[df['id_plan'] != 4]
    nuevo_contado = nuevo.groupby(['id_plan', x_col]).agg(
        conteo_total=('conteo', 'sum')).reset_index()
    fig = graficos.createLineGraphPorPlanes(nuevo_contado, x_col, y_col, title, color_list, label_x, label_y)
    
    return fig

def scatter(df, title, label_x, label_y):
    # Filtramos las columnas necesarias
    print(df)  # Solo para verificar que los datos son correctos
    df_filtered = df[['id_rango', 'id_plan', 'tasa_desercion']]
    
    # Creamos el gráfico de dispersión usando `createScatter`
    fig = graficos.createScatter(
        data=df_filtered, 
        title=title, 
        x_label=label_x, 
        y_label=label_y
    )
    return fig

def graphTazaDeserciones(df, title, color_list, label_x, label_y):
    # Convertir las fechas a formato datetime
    # Filtrar pacientes inactivos
    df['fecha_ultima_consulta'] = pd.to_datetime(df['fecha_ultima_consulta'])
    df_inactivos = df[df['activo'] == 0]

    ##muestra la fecha mas reciente
    print("sjdoashukhsdfoihsdfoihio")
    print(df_inactivos['fecha_ultima_consulta'].max())

    # Extraer el año y mes de la columna 'fecha_ultima_consulta'
    df_inactivos['año'] = df_inactivos['fecha_ultima_consulta'].dt.year
    df_inactivos['mes'] = df_inactivos['fecha_ultima_consulta'].dt.month
    print(df_inactivos)

    # Agrupar los pacientes inactivos por año y mes, contando las deserciones
    desercion_mensual = df_inactivos.groupby(['año', 'mes']).size().reset_index(name='desercion')

    # Crear el gráfico de líneas usando el método previamente definido
    fig = graficos.createLineGraphDesercion(desercion_mensual, title, color_list, label_x, label_y)

    return fig

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
