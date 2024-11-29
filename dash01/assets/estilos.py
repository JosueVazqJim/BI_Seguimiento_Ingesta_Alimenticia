# estilos.py
import plotly.graph_objs as go

def aplicar_estilos(fig, title):
    fig.update_layout(
        title=title,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='rgba(255, 255, 255, 1)', 
        plot_bgcolor='rgba(240, 240, 240, 1)',  
        font=dict(color='black'),
    )
    return fig

