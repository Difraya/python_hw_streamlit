import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests

def get_weather(city, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    else:
        return None

def is_normal(city, curr_temp, df_for_city, season):
    subset = df_for_city[df_for_city['season'] == season]
    if len(subset) > 0:
        avg_temp = subset['avg_temperature'].iloc[0]
        std_temp = subset['std_temperature'].iloc[0]
        lower = avg_temp - 2 * std_temp
        upper = avg_temp + 2 * std_temp
        if lower <= curr_temp <= upper:
            return "В норме"
        else:
            return "Аномальная"
    else:
        return "Нет данных для сезона"

def check_anomaly_temp(city, df_for_city, api_key):
    season = "winter"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    resp = requests.get(url)
    if resp.status_code == 200:
        data_json = resp.json()
        curr_temp = data_json['main']['temp']
        result = is_normal(city, curr_temp, df_for_city, season)
        return f"Температура в {city}: {curr_temp}°C — {result}"
    else:
        return "Ошибка при запросе данных"

def main():
    st.title("Прогноз погоды")

    uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        st.write("Превью данных:")
        st.dataframe(data.sample(5))
    else:
        st.write("Пожалуйста, загрузите CSV-файл.")
        return

    city = st.selectbox("Выберите город", data['city'].unique())
    api_key = st.text_input("Введите ваш API-ключ")

    if api_key:
        if st.button("Получить текущую погоду"):
            weather = get_weather(city, api_key)
            if weather and weather.get("cod") == 401:
                st.error(f"Ошибка: {weather['message']}")
            elif weather:
                st.success(f"Температура в {city}: {weather['main']['temp']}°C")
            else:
                st.error("Ошибка при запросе данных")
    else:
        st.write("Пожалуйста, введите ваш API-ключ")

    data_for_city = data[data['city'] == city].copy()
    st.header(f'Описательная статистика для города {city}')
    if st.checkbox("Показать описательную статистику"):
        st.write(data_for_city.describe())

    st.header("Визуализация данных")
    if len(data_for_city) > 0:
        st.subheader("Гистограмма")
        column = st.selectbox("Выберите колонку для гистограммы", data_for_city.columns)
        bins = st.slider("Количество интервалов (bins)", 5, 50, 10)
        fig, ax = plt.subplots()
        ax.hist(data_for_city[column], bins=bins, color='skyblue', edgecolor='black')
        st.pyplot(fig)

        st.subheader("Временной ряд температур с выделением аномалий")
        data_for_city = data_for_city.sort_values(by=["season", "timestamp"])
        data_for_city["temperature_30d_avg"] = data_for_city.groupby("season")["temperature"] \
            .rolling(window=30, min_periods=1).mean().reset_index(level=[0,1], drop=True)
        data_for_city['avg_temperature'] = data_for_city.groupby("season")["temperature"].transform('mean')
        data_for_city['std_temperature'] = data_for_city.groupby("season")["temperature"].transform('std')
        data_for_city['lower'] = data_for_city['avg_temperature'] - 2 * data_for_city['std_temperature']
        data_for_city['upper'] = data_for_city['avg_temperature'] + 2 * data_for_city['std_temperature']
        data_for_city['anomaly'] = (data_for_city['temperature'] < data_for_city['lower']) | \
                                   (data_for_city['temperature'] > data_for_city['upper'])

        fig, ax = plt.subplots(figsize=(12, 6))
        for seas in data_for_city['season'].unique():
            season_data = data_for_city[data_for_city['season'] == seas]
            ax.plot(season_data['timestamp'], season_data['temperature'], label=f'{seas}', alpha=0.7)
            ax.scatter(
                season_data[season_data['anomaly']]['timestamp'],
                season_data[season_data['anomaly']]['temperature'],
                color='red', label=f'Аномалии {seas}', zorder=5
            )
        ax.set_title("Временной ряд температур с выделением аномалий")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Температура (°C)")
        ax.legend()
        st.pyplot(fig)

        st.subheader("Сезонные профили с указанием среднего и стандартного отклонения")
        season_profiles = data_for_city.groupby('season').agg(
            avg_temperature=('temperature', 'mean'),
            std_temperature=('temperature', 'std')
        ).reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(
            season_profiles['season'],
            season_profiles['avg_temperature'],
            yerr=season_profiles['std_temperature'],
            capsize=5, color='skyblue', alpha=0.8
        )
        ax.set_title("Сезонные профили с указанием среднего и стандартного отклонения")
        ax.set_xlabel("Сезон")
        ax.set_ylabel("Средняя температура (°C)")
        st.pyplot(fig)

        if api_key:
            if st.button("Проверить аномалию сейчас"):
                res_anomaly = check_anomaly_temp(city, data_for_city, api_key)
                st.write(res_anomaly)

if __name__ == "__main__":
    main()