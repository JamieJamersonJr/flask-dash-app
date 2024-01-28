# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3 as sql3
from datetime import date, datetime, timedelta

CONFIG = {'Database':None}


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def query_db(query):
    if CONFIG["Database"] == None:
        return
    db = sql3.connect(CONFIG["Database"])
    db.row_factory = make_dicts

    cur = db.cursor()
    cur.execute(query)
    result = list(cur)
    db.close()
    return result

def unix_to_datestring(unix, format = "%d/%m/%Y"):
    return datetime.fromtimestamp(int(unix)).strftime(format)

def datestring_to_unix(date_string, format = "%d/%m/%Y"):
    if date_string == None:
        return None
    date_format = format
    print(f"Converting datestring: {date_string} of format: {date_format} to datetime object")
    dt_object = datetime.strptime(date_string, date_format)
    print(f"datetime object: {dt_object}")
    unix_timestamp = int(dt_object.timestamp())
    return unix_timestamp

def getSamples(year = None):
    query_data = query_db('select date, p5_count, p05_count, location from Samples ORDER BY date ASC')
    dataDict = {'data':[],'p5':[],'p05':[], 'posizione':[]}
    # i = 0
    for row in query_data:
        if year != None:
            from_date = int(datetime(year-1, 5, 1).timestamp())
            to_date = int(datetime(year, 4, 30).timestamp())

            if row['date'] < from_date or row['date'] > to_date:
                # print('skipped')
                continue
        dataDict['data'].append(unix_to_datestring(row['date']))
        dataDict['p5'].append(row['p5_count'])
        dataDict['p05'].append(row['p05_count'])
        dataDict['posizione'].append(row['location'])
        # i += 1
    # print(f"ITERATOR: {i}")
    return pd.DataFrame(data = dataDict)

PRECALCULATED_STATISTICS = {'mean_p5':None, 'mean_p05':None, 'stdDev_p5':None,
                            'stdDev_p05':None, 'ucl_p5':None, 'ucl_p05':None,
                            'limit_p5':None, 'limit_p05':None, 'fiscal_years': None}
def get_fiscal_year(date):
    if date.month >= 5:
        return date.year + 1
    else:
        return date.year
def get_fiscal_year_from_string(str, format = "%Y-%m-%d"):
    _date = datetime.strptime(str, format)
    if _date.month >= 5:
        return _date.year + 1
    else:
        return _date.year



def make_dash(server, database_path):
    CONFIG["Database"] = database_path
    # Incorporate data
    df = getSamples()
    # Calcoli statistici
    PRECALCULATED_STATISTICS["mean_p5"] = df['p5'].mean()
    PRECALCULATED_STATISTICS["mean_p05"] = df['p05'].mean()
    PRECALCULATED_STATISTICS["stdDev_p5"] = df['p5'].std()
    PRECALCULATED_STATISTICS["stdDev_p05"] = df['p05'].std()
    PRECALCULATED_STATISTICS["ucl_p5"] = round(PRECALCULATED_STATISTICS["mean_p5"] + (3 * PRECALCULATED_STATISTICS["stdDev_p5"]), 2)
    PRECALCULATED_STATISTICS["ucl_p05"] = round(PRECALCULATED_STATISTICS["mean_p05"] + (3 * PRECALCULATED_STATISTICS["stdDev_p05"]), 2)
    PRECALCULATED_STATISTICS["limit_p5"] = 29300
    PRECALCULATED_STATISTICS["limit_p05"] = 3520000

    PRECALCULATED_STATISTICS["fiscal_years"] = df['data'].apply(lambda x: get_fiscal_year_from_string(x, "%d/%m/%Y"))
    PRECALCULATED_STATISTICS["fiscal_years"] = list(set(PRECALCULATED_STATISTICS["fiscal_years"]))
    PRECALCULATED_STATISTICS["fiscal_years"].sort(reverse=True)
    print(PRECALCULATED_STATISTICS["fiscal_years"])
    return Dash(
        server=server,
        url_base_pathname='/dash/'
    )



def make_layout():
    return html.Div([
    dcc.Dropdown(PRECALCULATED_STATISTICS["fiscal_years"], PRECALCULATED_STATISTICS["fiscal_years"][0], id='year-dropdown'),
    # dcc.DatePickerRange(
    #     id='date-picker-range',
    #     min_date_allowed=date(1971, 1, 1),
    #     max_date_allowed=date(2100, 1, 1),
    #     initial_visible_month=date(datetime.now().year, 1, 1),
    #     end_date=date(2024, 1, 1),
    #     month_format="YYYY/MM/DD",
    #     display_format="YYYY/MM/DD"
    # ),
    dcc.Graph(figure={}, id='p5-graph'),
    html.Br(),
    dcc.Graph(figure={}, id='p05-graph')
])

def define_callbacks():
    @callback(
        Output(component_id='p5-graph', component_property='figure'),

        Input('year-dropdown', 'value')
    )
    def update_graph(selected_year = None):
        
        # if start_date != None:
        #     converted_start_date = datetime.strptime(start_date, "%Y-%m-%d")
        #     converted_end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(year = get_fiscal_year(converted_start_date))

        #     converted_start_date = converted_start_date.strftime("%Y-%m-%d")
        #     converted_end_date = converted_end_date.strftime("%Y-%m-%d")

        #     print(f"START DATE: {converted_start_date} END DATE: {converted_end_date}")

        #     df = getSamples(datestring_to_unix(start_date, "%Y-%m-%d"), datestring_to_unix(converted_end_date, "%Y-%m-%d"))


        # else:
        #     df = getSamples(datestring_to_unix(start_date, "%Y-%m-%d"), datestring_to_unix(end_date, "%Y-%m-%d"))
        print(selected_year)
        if selected_year != None:
            df = getSamples(selected_year)
        else:
            df = getSamples()

        PRECALCULATED_STATISTICS["mean_p5"] = df['p5'].mean()
        PRECALCULATED_STATISTICS["mean_p05"] = df['p05'].mean()
        PRECALCULATED_STATISTICS["stdDev_p5"] = df['p5'].std()
        PRECALCULATED_STATISTICS["stdDev_p05"] = df['p05'].std()
        PRECALCULATED_STATISTICS["ucl_p5"] = round(PRECALCULATED_STATISTICS["mean_p5"] + (3 * PRECALCULATED_STATISTICS["stdDev_p5"]), 2)
        PRECALCULATED_STATISTICS["ucl_p05"] = round(PRECALCULATED_STATISTICS["mean_p05"] + (3 * PRECALCULATED_STATISTICS["stdDev_p05"]), 2)
        PRECALCULATED_STATISTICS["limit_p5"] = 29300
        PRECALCULATED_STATISTICS["limit_p05"] = 3520000

        PRECALCULATED_STATISTICS["fiscal_years"] = df['data'].apply(lambda x: get_fiscal_year_from_string(x, "%d/%m/%Y"))
        PRECALCULATED_STATISTICS["fiscal_years"] = list(set(PRECALCULATED_STATISTICS["fiscal_years"]))
        PRECALCULATED_STATISTICS["fiscal_years"].sort(reverse=True)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        # Creazione del grafico a linee interattivo con Plotly Express
        fig = px.line(
            df,
            x="data",
            y="p5",
            labels={"p5": "N° particelle di diametro ≥ 5 μm"},
            title="Carta di Controllo per particelle di diametro ≥ 5 μm",
        )

        # Aggiungi le linee orizzontali per i limiti
        fig.add_shape(
            dict(
                type="line",
                x0=df["data"].min(),
                x1=df["data"].max(),
                y0=PRECALCULATED_STATISTICS["limit_p5"],
                y1=PRECALCULATED_STATISTICS["limit_p5"],
                line=dict(color="green", dash="dash"),
                name="Action level",
            )
        )
        fig.add_shape(
            dict(
                type="line",
                x0=df["data"].min(),
                x1=df["data"].max(),
                y0=PRECALCULATED_STATISTICS["ucl_p5"],
                y1=PRECALCULATED_STATISTICS["ucl_p5"],
                line=dict(color="red", dash="dash"),
                name="Alert level",
            )
        )

        # Aggiungi le annotazioni per la legenda
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name=f"Mean: {PRECALCULATED_STATISTICS['mean_p5']:.2f}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name=f"Std Dev: {PRECALCULATED_STATISTICS['stdDev_p5']:.2f}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name=f"Limit: {PRECALCULATED_STATISTICS['limit_p5']}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name=f"Alert: {PRECALCULATED_STATISTICS['ucl_p5']}",
            )
        )
        # Trova gli outlier e aggiungi i punti all'istogramma
        outlier = df["p5"] > PRECALCULATED_STATISTICS["ucl_p5"]
        fig.add_trace(
            go.Scatter(
                x=df.loc[outlier, "data"],
                y=df.loc[outlier, "p5"],
                mode="markers",
                marker=dict(color="red"),
                name="Outlier",
            )
        )

        # Aggiungi le etichette per gli outlier
        for i, txt in enumerate(df.loc[outlier, "p5"]):
            posizione = df.loc[outlier, "posizione"].iloc[i]
            fig.add_annotation(
                x=df.loc[outlier, "data"].iloc[i],
                y=txt,
                text=f"Pos {posizione}\n{txt:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
            )

        # Aggiungi le etichette degli assi e mostra il grafico
        fig.update_layout(
            xaxis_title="Data",
            yaxis_title="N° particelle di diametro ≥ 5 μm",
            xaxis=dict(tickangle=45),
            showlegend=True,
        )
        # fig.show()
        return fig




# def update_graph(start_date = None, end_date = None):
#     if start_date != None:
#         fiscalyear.setup_fiscal_calendar(start_month=5) 
#         New_CF_Date = datetime.strptime(start_date, "%Y-%m-%d")
#         fiscal_date = fiscalyear.FiscalDate(New_CF_Date.year, New_CF_Date.month, New_CF_Date.day)
#         print(fiscal_date)
#         print(fiscal_date.fiscal_year)
#         fiscal_end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(year=fiscal_date.fiscal_year).strftime('%Y-%m-%d')
#         print(f"BALLS: {fiscal_end_date}")
#         df = getSamples(datestring_to_unix(start_date, "%Y-%m-%d"), datestring_to_unix(fiscal_end_date, "%Y-%m-%d"))
#     else:
#         df = getSamples(datestring_to_unix(start_date, "%Y-%m-%d"), datestring_to_unix(end_date, "%Y-%m-%d"))
#     df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
#     # Creazione del grafico a linee interattivo con Plotly Express
#     fig = px.line(
#         df,
#         x="data",
#         y="p5",
#         labels={"p5": "N° particelle di diametro ≥ 5 μm"},
#         title="Carta di Controllo per particelle di diametro ≥ 5 μm",
#     )

#     # Aggiungi le linee orizzontali per i limiti
#     fig.add_shape(
#         dict(
#             type="line",
#             x0=df["data"].min(),
#             x1=df["data"].max(),
#             y0=limit_p5,
#             y1=limit_p5,
#             line=dict(color="green", dash="dash"),
#             name="Action level",
#         )
#     )
#     fig.add_shape(
#         dict(
#             type="line",
#             x0=df["data"].min(),
#             x1=df["data"].max(),
#             y0=ucl_p5,
#             y1=ucl_p5,
#             line=dict(color="red", dash="dash"),
#             name="Alert level",
#         )
#     )

#     # Aggiungi le annotazioni per la legenda
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Mean: {mean_p5:.2f}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Std Dev: {stdDev_p5:.2f}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Limit: {limit_p5}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Alert: {ucl_p5}",
#         )
#     )
#     # Trova gli outlier e aggiungi i punti all'istogramma
#     outlier = df["p5"] > ucl_p5
#     fig.add_trace(
#         go.Scatter(
#             x=df.loc[outlier, "data"],
#             y=df.loc[outlier, "p5"],
#             mode="markers",
#             marker=dict(color="red"),
#             name="Outlier",
#         )
#     )

#     # Aggiungi le etichette per gli outlier
#     for i, txt in enumerate(df.loc[outlier, "p5"]):
#         posizione = df.loc[outlier, "posizione"].iloc[i]
#         fig.add_annotation(
#             x=df.loc[outlier, "data"].iloc[i],
#             y=txt,
#             text=f"Pos {posizione}\n{txt:.2f}",
#             showarrow=True,
#             arrowhead=2,
#             arrowcolor="red",
#         )

#     # Aggiungi le etichette degli assi e mostra il grafico
#     fig.update_layout(
#         xaxis_title="Data",
#         yaxis_title="N° particelle di diametro ≥ 5 μm",
#         xaxis=dict(tickangle=45),
#         showlegend=True,
#     )
#     # fig.show()
#     return fig


# @callback(
#     Output(component_id='p05-graph', component_property='figure'),
#     [Input('date-picker-range', 'start_date'),
#     Input('date-picker-range', 'end_date')]
# )
# def update_graph(start_date = None, end_date = None):
#     # Conversione della colonna 'data' in formato datetime
#     df["data"] = pd.to_datetime(df["data"])
#     # Creazione del grafico a linee interattivo con Plotly Express
#     fig = px.line(
#         df,
#         x="data",
#         y="p05",
#         labels={"p05": "N° particelle di diametro ≥ 0,5 μm"},
#         title="Carta di Controllo per particelle di diametro ≥ 0,5 μm",
#     )

#     # Aggiungi le linee orizzontali per i limiti
#     fig.add_shape(
#         dict(
#             type="line",
#             x0=df["data"].min(),
#             x1=df["data"].max(),
#             y0=limit_p05,
#             y1=limit_p05,
#             line=dict(color="green", dash="dash"),
#             name="Action level",
#         )
#     )
#     fig.add_shape(
#         dict(
#             type="line",
#             x0=df["data"].min(),
#             x1=df["data"].max(),
#             y0=ucl_p05,
#             y1=ucl_p05,
#             line=dict(color="red", dash="dash"),
#             name="Alert level",
#         )
#     )

#     # Aggiungi le annotazioni per la legenda
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Mean: {mean_p05:.2f}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Std Dev: {stdDev_p05:.2f}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Limit: {limit_p05}",
#         )
#     )
#     fig.add_trace(
#         go.Scatter(
#             x=[None],
#             y=[None],
#             mode="markers",
#             marker=dict(color="rgba(0,0,0,0)"),
#             showlegend=True,
#             name=f"Alert: {ucl_p05}",
#         )
#     )
#     # Trova gli outlier e aggiungi i punti all'istogramma
#     outlier = df["p05"] > ucl_p05
#     fig.add_trace(
#         go.Scatter(
#             x=df.loc[outlier, "data"],
#             y=df.loc[outlier, "p05"],
#             mode="markers",
#             marker=dict(color="red"),
#             name="Outlier",
#         )
#     )

#     # Aggiungi le etichette per gli outlier
#     for i, txt in enumerate(df.loc[outlier, "p05"]):
#         posizione = df.loc[outlier, "posizione"].iloc[i]
#         fig.add_annotation(
#             x=df.loc[outlier, "data"].iloc[i],
#             y=txt,
#             text=f"Pos {posizione}\n{txt:.2f}",
#             showarrow=True,
#             arrowhead=2,
#             arrowcolor="red",
#         )

#     # Aggiungi le etichette degli assi e mostra il grafico
#     fig.update_layout(
#         xaxis_title="Data",
#         yaxis_title="N° particelle di diametro ≥ 0,5 μm",
#         xaxis=dict(tickangle=45),
#         showlegend=True,
#     )
#     return fig




# # Run the app
# if __name__ == '__main__':
#     app.run(debug=True)
