# graficas.py
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import seaborn as sns
import matplotlib.pyplot as plt


PLAN_MAP = {
    1: "Plan Básico", 2: "Plan Medio", 3: "Plan Alto", 4: "Todos los planes"
}

class Graphs():
    def __init__(self):
        pass
    
    import plotly.graph_objects as go

    def createLineGraph(self, data, x_col, y_cols, title, color_list, label_x, label_y):
        # Crear la figura del gráfico de líneas
        fig = go.Figure()

        # Iterar sobre las columnas en y_cols (lista de columnas de Y) y agregar cada línea
        for i, y_col in enumerate(y_cols):
            # Agregar una línea para cada serie de datos
            fig.add_trace(go.Scatter(
                x=data[x_col],
                y=data[y_col],
                mode='lines+markers',  # Línea con puntos
                line=dict(color=color_list[i] if i < len(color_list) else 'black'),  # Color de la línea
                marker=dict(color=color_list[i] if i < len(color_list) else 'black'),  # Color de los puntos
                name=y_col  # Usar el nombre de la columna como la leyenda
            ))

        # Añadir etiquetas y título
        fig.update_layout(
            title=title,
            xaxis_title=label_x,
            yaxis_title=label_y
        )
        
        # Retornar el gráfico de líneas
        return fig
    
    def createLineGraphDesercion(self, data, title, color_list, label_x, label_y):
        # Crear la figura del gráfico de líneas
        fig = go.Figure()

        # Obtener todos los años únicos en el DataFrame
        años_unicos = data['año'].unique()

        # Iterar sobre cada año para crear una línea para cada uno
        for i, año in enumerate(años_unicos):
            # Filtrar los datos para el año específico
            df_año = data[data['año'] == año]
            
            # Crear la línea para ese año
            fig.add_trace(go.Scatter(
                x=df_año['mes'],  # Meses
                y=df_año['desercion'],  # Número de deserciones
                mode='lines+markers',  # Línea con puntos
                name=str(año),  # Usar el año como la leyenda
                line=dict(color=color_list[i] if i < len(color_list) else 'black'),  # Color de la línea
                marker=dict(color=color_list[i] if i < len(color_list) else 'black'),  # Color de los puntos
            ))

        # Añadir título y etiquetas
        fig.update_layout(
            title=title,
            xaxis_title=label_x,
            yaxis_title=label_y,
            xaxis=dict(
                tickmode='array', 
                tickvals=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],  # Meses 1 a 12
                ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            ),
            legend_title="Año"
        )
        
        # Retornar el gráfico de líneas
        return fig

    def createLineGraphPorPlanes(self, data, x_col, y_col, title, color_list, label_x, label_y):
        # Crear la figura del gráfico de líneas
        fig = go.Figure()

        # Filtrar los datos por cada plan y agregar una línea para cada uno
        for plan in [1, 2, 3]:  # Planes básico, medio, alto
            plan_data = data[data['id_plan'] == plan]
            plan_name = PLAN_MAP.get(plan, "Desconocido")
            fig.add_trace(go.Scatter(
                x=plan_data[x_col],
                y=plan_data[y_col],
                mode='lines+markers',  # Línea con puntos
                line=dict(color=color_list[plan-1]),  # Colores diferentes para cada plan
                marker=dict(color=color_list[plan-1]),
                name=plan_name  # Usar el nombre del plan como leyenda
            ))

        # Añadir etiquetas y título
        fig.update_layout(
            title=title,
            xaxis_title=label_x,
            yaxis_title=label_y
        )
        
        # Retornar el gráfico de líneas
        return fig
    
    def createBarGraph(self, data, x_col, y_cols, title, color_list, label_x, label_y):
        # Crear la figura del gráfico de barras
        fig = go.Figure()

        # Iterar sobre las columnas en y_cols (lista de columnas de Y) y agregar cada barra
        for i, y_col in enumerate(y_cols):
            # Agregar una barra para cada serie de datos
            fig.add_trace(go.Bar(
                x=data[x_col],
                y=data[y_col],
                name=y_col,  # Usar el nombre de la columna como la leyenda
                marker=dict(color=color_list[i] if i < len(color_list) else 'blue')  # Color de las barras
            ))

        # Añadir etiquetas y título
        fig.update_layout(
            title=title,
            xaxis_title=label_x,
            yaxis_title=label_y,
            barmode='group'  # Permite ver las barras agrupadas (puedes usar 'stack' si prefieres apiladas)
        )
        
        # Retornar el gráfico de barras
        return fig
    
    def createScatter(self, data, title, x_label, y_label):
        # Crear la figura del gráfico de dispersión usando Plotly
        fig = go.Figure()

        # Añadir trazas para cada `id_plan`
        for plan in data['id_plan'].unique():
            subset = data[data['id_plan'] == plan]
            fig.add_trace(go.Scatter(
                x=subset['id_rango'],          # Eje X: id_rango
                y=subset['tasa_desercion'],    # Eje Y: Tasa de Deserción
                mode='markers',                # Modo: Puntos
                name=f'Plan {plan}',           # Nombre de la serie
                marker=dict(size=10, line=dict(width=1))  # Opcional: Configurar marcador
            ))

        # Configurar diseño del gráfico
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            showlegend=True,  # Mostrar leyenda
            template='plotly' # Plantilla visual
        )

        return fig

    

