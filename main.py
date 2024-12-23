import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, ALL
import plotly.express as px
import pandas as pd
from accuweather import get_location_key_name, get_conditions_by_key, get_forecast, get_coordinates
import folium
from folium import IFrame

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, prevent_initial_callbacks='initial_duplicate')

app.layout = html.Div(
    children=[
        html.H1("Прогноз погоды по маршруту и сравнение между городами", style={'textAlign': 'center'}),

            # Hidden API Key Input for flexibility
        dcc.Input(id="api-key", type="text", placeholder="Введите API ключ AccuWeather", style={'display': 'none'}, value='tHFH4XKTyk07NEzXehomY5Ru7Vh3wZeI'),

        # City input forms
        html.Div(id='city-input-container', children=[
            html.Div([
                html.Label("Первый город:"),
                dcc.Input(id="namecity1", type="text", placeholder="Москва"),
            ], style={'margin-bottom': '20px'}),

            html.Div([
                html.Label("Второй город:"),
                dcc.Input(id="namecity2", type="text", placeholder="Казань"),
            ], style={'margin-bottom': '20px'}),

            # Кнопка добавления промежуточных остановок
            html.Button('Добавить остановку', id='add-stop', n_clicks=0),
            html.Div(id='intermediate-stops-container')
        ]),

        html.I('К сожалению, в бесплатной версии AccuWeatherAPI доступно получение прогноза погоды только на 5 дней.'
               '',
                style={'textAlign': 'center', 'margin-top': '20px'}),

        # Submit button for comparison
        html.Div(html.Button('Сравнить', id='submit-val', n_clicks=0),
                 style={'textAlign': 'center', 'margin-top': '20px'}),

        # Output area for comparison
        html.H3(id="weather-output", style={'textAlign': 'center'}),

        # Graph area for comparison
        html.Div([
            dcc.Graph(id="temp-graph", style={'display': 'inline-block', 'width': '48%'}),
            dcc.Graph(id="humidity-graph", style={'display': 'inline-block', 'width': '48%'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'margin-top': '20px'}),

        html.Div([
            dcc.Graph(id="wind-graph", style={'display': 'inline-block', 'width': '48%'}),
            dcc.Graph(id="rain-graph", style={'display': 'inline-block', 'width': '48%'}),
        ], style={'display': 'flex', 'justify-content': 'space-between', 'margin-top': '20px'}),

        html.I('Используем столбчатые диаграммы для сравнения значений между городами', style={'textAlign': 'center', 'margin-top': '20px'}),

        html.H3('Прогноз погоды', style={'textAlign': 'center'}),

        # Графики прогноза по дням для всех городов
        html.Div(id='forecast-graphs-container', style={'margin-top': '40px'}),

        html.H3('Интерактивная карта поездки', style={'textAlign': 'center'}),

        html.Div(id='map-container', style={'margin-top': '40px'}),

        # Store number of stops
        dcc.Store(id='num-stops', data=0)
    ]
)


# Callback for adding intermediate stops
@app.callback(
    Output('intermediate-stops-container', 'children'),
    Output('num-stops', 'data'),
    Input('add-stop', 'n_clicks'),
    State('num-stops', 'data')
)
def add_stop_fields(n_clicks, num_stops):
    if n_clicks == 0:
        return None, 0
    stops = num_stops + 1
    stop_fields = [
        html.Div([
            html.Label(f"Остановка {i + 1}:"),
            dcc.Input(id={'type': 'namecity', 'index': i}, type="text", placeholder=f"Город {i + 1}"),
        ], style={'margin-bottom': '20px'}) for i in range(stops)
    ]
    return stop_fields, stops


# Callback to update weather output and graphs for comparison
@app.callback(
    [
        Output('weather-output', 'children'),
        Output('temp-graph', 'figure'),
        Output('humidity-graph', 'figure'),
        Output('wind-graph', 'figure'),
        Output('rain-graph', 'figure'),
        Output('forecast-graphs-container', 'children'),
    ],
    Input('submit-val', 'n_clicks'),
    [
        State('namecity1', 'value'),
        State('namecity2', 'value'),
        State({'type': 'namecity', 'index': ALL}, 'value'),
        State({'type': 'mode', 'index': ALL}, 'value'),
        State('api-key', 'value'),
    ]
)
def update_output(n_clicks, namecity1, namecity2, intermediate_cities, intermediate_modes, api_key):
    if n_clicks == 0 or not api_key:
        return "", {}, {}, {}, {}, ""

    # Collect all cities and modes
    all_cities = [namecity1] + intermediate_cities + [namecity2]
    weather_data = []

    for city in all_cities:
        try:
            location_key, localized_name = get_location_key_name(api_key, city)
            conditions = get_conditions_by_key(api_key, location_key)
            weather_data.append({
                'City': localized_name,
                'Temperature': conditions['temperature'],
                'Humidity': conditions['humidity'],
                'Wind Speed': conditions['wind_speed'],
                'Rain Probability': conditions['precipitation_probability']
            })
        except Exception as e:
            return f"Ошибка для города {city}: {str(e)}", {}, {}, {}, {}, ""

    df = pd.DataFrame(weather_data)
    temp_fig = px.bar(df, x='City', y='Temperature', title="Температура (°C)")
    humidity_fig = px.bar(df, x='City', y='Humidity', title="Влажность (%)")
    wind_fig = px.bar(df, x='City', y='Wind Speed', title="Скорость ветра (км/ч)")
    rain_fig = px.bar(df, x='City', y='Rain Probability', title="Вероятность осадков (%)")

    output_text = f"Сравнение погоды для: {' - '.join([data['City'] for data in weather_data])}"

    forecast_data = []

    for city in all_cities:
        try:
            location_key, localized_name = get_location_key_name(api_key, city)
            city_forecast = get_forecast(api_key, location_key, days=5)
            for day in city_forecast:
                day['city'] = localized_name
            forecast_data.extend(city_forecast)
        except Exception as e:
            return [html.Div(f"Ошибка для города {city}: {str(e)}")]


    df = pd.DataFrame(forecast_data)
    try:
        # Построение графиков для каждого параметра
        graphs = []
        graphs.append(dcc.Graph(
            figure=px.line(df, x='date', y='max_temp', color='city', title="Макс. температура по дням (°C)")
        ))
        graphs.append(dcc.Graph(
            figure=px.line(df, x='date', y='min_temp', color='city', title="Мин. температура по дням (°C)")
        ))
        graphs.append(dcc.Graph(
            figure=px.line(df, x='date', y='precipitation_probability', color='city', title="Вероятность осадков (%)")
        ))
        graphs.append(dcc.Graph(
            figure=px.line(df, x='date', y='wind_speed', color='city', title="Скорость ветра (км/ч)")
        ))
    except Exception as e:
        return [html.Div(f"Ошибка для города {city}: {str(e)}")]

    return output_text, temp_fig, humidity_fig, wind_fig, rain_fig, graphs


@app.callback(
    Output('map-container', 'children'),
    Input('submit-val', 'n_clicks'),
    [
        State('namecity1', 'value'),
        State('namecity2', 'value'),
        State({'type': 'namecity', 'index': ALL}, 'value'),
        State('api-key', 'value')
    ]
)
def update_map(n_clicks, start_city, end_city, intermediate_cities, api_key):
    if n_clicks == 0:
        return []

    all_cities = [start_city] + intermediate_cities + [end_city]
    map_center = (55.751244, 37.618423)  # Москва, можно настроить в зависимости от городов
    m = folium.Map(location=map_center, zoom_start=5)

    # Обработка каждого города и добавление прогноза
    for city in all_cities:
        try:
            location_key, localized_name = get_location_key_name(api_key, city)
            city_forecast = get_forecast(api_key, location_key, days=5)
            city_coord = get_coordinates(api_key, location_key)
            coordinates = (float(city_coord[0]), float(city_coord[1]))

            # Создаем контент для всплывающего окна
            forecast_html = "<h4>Прогноз погоды</h4>"
            for day in city_forecast:
                forecast_html += f"<b>{day['date']}</b><br>"
                forecast_html += f"Макс. температура: {day['max_temp']} °C<br>"
                forecast_html += f"Мин. температура: {day['min_temp']} °C<br>"
                forecast_html += f"Вероятность осадков: {day['precipitation_probability']}%<br>"
                forecast_html += f"Скорость ветра: {day['wind_speed']} км/ч<br><br>"

            iframe = IFrame(forecast_html, width=200, height=200)
            popup = folium.Popup(iframe, max_width=200)

            # Добавляем метку на карту
            folium.Marker(
                location=coordinates,
                popup=popup,
                tooltip=localized_name
            ).add_to(m)

        except Exception as e:
            raise
            return [html.Div(f"Ошибка для города {city}: {str(e)}")]

    map_html = m._repr_html_()

    return html.Iframe(srcDoc=map_html, width="100%", height="500px")

if __name__ == '__main__':
    app.run(debug=True)
