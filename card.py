import plotly.graph_objects as go
from dash import dcc, html


def criar_figura_indicador(valor: float, referencia: float = 50000) -> go.Figure:
    """Cria a figura Plotly usada pelo card de indicador."""
    valor = 0 if valor is None else valor

    figura = go.Figure(
        go.Indicator(
            mode="number+delta",
            value=valor,
            number={
                "prefix": "R$ ",
                "valueformat": ",.2f",
                "font": {"size": 55, "color": "#0f172a"},
            },
            delta={
                "reference": referencia,
                "relative": True,
                "valueformat": ".1%",
            },
            title={
                "text": "Faturamento mensal",
                "font": {"size": 24},
            },
        )
    )

    figura.update_layout(
        height=280,
        margin={"l": 30, "r": 30, "t": 70, "b": 30},
        paper_bgcolor="white",
    )

    return figura


def criar_card_indicador(
    valor_inicial: float = 65000,
    referencia: float = 50000,
) -> html.Div:
    """Retorna o card Dash completo, pronto para inclusão no layout."""
    return html.Div(
        style={
            "backgroundColor": "white",
            "padding": "25px",
            "borderRadius": "15px",
            "boxShadow": "0 4px 15px rgba(0, 0, 0, 0.08)",
        },
        children=[
            dcc.Graph(
                id="indicador-faturamento",
                figure=criar_figura_indicador(valor_inicial, referencia),
                config={"displayModeBar": False},
            )
        ],
    )
