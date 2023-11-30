import dash
from dash import dcc, html
from django_plotly_dash import DjangoDash

app = DjangoDash("SimpleExample")  # replaces dash.Dash

app.layout = html.Div(
    [
        dcc.RadioItems(
            id="dropdown-color",
            options=[
                {"label": c, "value": c.lower()} for c in ["Red", "Green", "Blue"]
            ],
            value="red",
        ),
        html.Div(id="output-color"),
        dcc.RadioItems(
            id="dropdown-size",
            options=[
                {"label": i, "value": j}
                for i, j in [("L", "large"), ("M", "medium"), ("S", "small")]
            ],
            value="medium",
        ),
        html.Div(id="output-size"),
        dcc.Graph(
            figure={
                "data": [
                    {"x": [1, 2, 3], "y": [4, 1, 2], "type": "bar", "name": "SF"},
                    {"x": [1, 2, 3], "y": [2, 4, 5], "type": "bar", "name": "Montréal"},
                ],
                "layout": {"title": "Dash Data Visualization"},
            }
        ),
    ]
)


@app.callback(
    dash.dependencies.Output("output-color", "children"),
    [dash.dependencies.Input("dropdown-color", "value")],
)
def callback_color(dropdown_value):
    return "The selected color is %s." % dropdown_value


@app.callback(
    dash.dependencies.Output("output-size", "children"),
    [
        dash.dependencies.Input("dropdown-color", "value"),
        dash.dependencies.Input("dropdown-size", "value"),
    ],
)
def callback_size(dropdown_color, dropdown_size):
    val = "The chosen T-shirt is a %s %s one." % (dropdown_size, dropdown_color)
    return val
