import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import time
from datetime import datetime, timedelta
import sys
import threading

# Добавляем директорию src в путь для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_generator import SensorDataGenerator

# Настройка страницы
st.set_page_config(
    page_title="Система мониторинга сигналов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Глобальные переменные
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
REFRESH_INTERVAL = 5  # секунды

# Словарь цветов для статусов
STATUS_COLORS = {
    "normal": "#2ecc71",
    "warning": "#f39c12",
    "critical": "#e74c3c"
}

# Словарь русских названий и более дружественных названий для типов датчиков
SENSOR_TYPE_NAMES = {
    "temperature": "Температура",
    "humidity": "Влажность",
    "pressure": "Давление",
    "vibration": "Вибрация",
    "noise": "Уровень шума",
    "power": "Потребление энергии"
}

# Функции для работы с данными
def get_current_data():
    """Получение текущих данных всех датчиков"""
    current_data_path = os.path.join(DATA_PATH, "current_data.json")
    if not os.path.exists(current_data_path):
        return []
    
    try:
        with open(current_data_path, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def get_device_history(device_id, hours=1):
    """Получение исторических данных для устройства за указанное количество часов"""
    now = datetime.now()
    history_data = []
    
    # Проверяем файлы истории за текущий и предыдущий день (если запрашиваем данные, захватывающие предыдущий день)
    date_list = [now.strftime('%Y%m%d')]
    if hours > 24 or now.hour < hours:
        yesterday = now - timedelta(days=1)
        date_list.append(yesterday.strftime('%Y%m%d'))
    
    for date_str in date_list:
        history_path = os.path.join(DATA_PATH, f"history_{date_str}.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as file:
                    all_history = json.load(file)
                    
                    # Фильтрация по устройству и времени
                    earliest_timestamp = (now - timedelta(hours=hours)).timestamp()
                    device_history = [
                        record for record in all_history 
                        if record["device_id"] == device_id and record["timestamp"] >= earliest_timestamp
                    ]
                    history_data.extend(device_history)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    # Сортировка по времени
    history_data.sort(key=lambda x: x["timestamp"])
    return history_data

def get_all_alerts(hours=24):
    """Получение всех оповещений за указанное количество часов"""
    now = datetime.now()
    alerts = []
    
    # Проверяем файлы истории за нужные дни
    date_list = [now.strftime('%Y%m%d')]
    if hours > 24:
        days_needed = hours // 24 + 1
        for i in range(1, days_needed):
            prev_day = now - timedelta(days=i)
            date_list.append(prev_day.strftime('%Y%m%d'))
    
    for date_str in date_list:
        history_path = os.path.join(DATA_PATH, f"history_{date_str}.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as file:
                    all_history = json.load(file)
                    
                    # Фильтрация по статусу и времени
                    earliest_timestamp = (now - timedelta(hours=hours)).timestamp()
                    alerts_list = [
                        record for record in all_history 
                        if record["status"] != "normal" and record["timestamp"] >= earliest_timestamp
                    ]
                    alerts.extend(alerts_list)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
    
    # Сортировка по времени (от новых к старым)
    alerts.sort(key=lambda x: x["timestamp"], reverse=True)
    return alerts

def format_timestamp(timestamp):
    """Преобразование UNIX-времени в человекочитаемый формат"""
    return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M:%S')

# Функции для визуализации
def create_gauge_chart(value, title, unit, min_val, max_val, threshold_warning, threshold_critical, status):
    """Создание индикатора в виде спидометра"""
    color = STATUS_COLORS[status]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': "#FFFFFF"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [min_val, threshold_warning[0]], 'color': 'rgba(255, 255, 0, 0.1)'},
                {'range': [threshold_warning[0], threshold_warning[1]], 'color': 'rgba(0, 255, 0, 0.3)'},
                {'range': [threshold_warning[1], max_val], 'color': 'rgba(255, 0, 0, 0.1)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 3},
                'thickness': 0.75,
                'value': threshold_critical[1] if value < threshold_critical[1] else threshold_critical[0]
            }
        },
        number={'suffix': f" {unit}", 'font': {'size': 20, 'color': color}}
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    
    return fig

def create_time_series_chart(history_data, title, unit):
    """Создание графика изменения показаний во времени"""
    if not history_data:
        return go.Figure()
    
    # Преобразование данных в DataFrame
    df = pd.DataFrame(history_data)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    # Создание графика с Plotly
    fig = px.line(
        df, 
        x='datetime', 
        y='value',
        title=title,
        labels={'value': f'Значение ({unit})', 'datetime': 'Время'},
        color_discrete_sequence=['#1f77b4']
    )
    
    # Добавление меток для аномалий
    warning_points = df[df['status'] == 'warning']
    critical_points = df[df['status'] == 'critical']
    
    if not warning_points.empty:
        fig.add_trace(
            go.Scatter(
                x=warning_points['datetime'],
                y=warning_points['value'],
                mode='markers',
                marker=dict(color=STATUS_COLORS['warning'], size=10, symbol='circle'),
                name='Предупреждение'
            )
        )
    
    if not critical_points.empty:
        fig.add_trace(
            go.Scatter(
                x=critical_points['datetime'],
                y=critical_points['value'],
                mode='markers',
                marker=dict(color=STATUS_COLORS['critical'], size=12, symbol='circle-x'),
                name='Критическое'
            )
        )
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig

# Инициализация состояния приложения
def init_app_state():
    # Инициализация генератора данных, если это первый запуск
    if 'generator' not in st.session_state:
        st.session_state.generator = SensorDataGenerator(data_path=DATA_PATH)
        st.session_state.generator.start()
    
    if 'alert_count' not in st.session_state:
        st.session_state.alert_count = 0
    
    if 'threshold_settings' not in st.session_state:
        st.session_state.threshold_settings = {
            "temperature": {"normal": (15.0, 30.0), "warning": (10.0, 35.0)},
            "humidity": {"normal": (30.0, 60.0), "warning": (20.0, 70.0)},
            "pressure": {"normal": (99.0, 103.0), "warning": (98.0, 104.0)},
            "vibration": {"normal": (5.0, 25.0), "warning": (2.0, 35.0)},
            "noise": {"normal": (50.0, 75.0), "warning": (45.0, 85.0)},
            "power": {"normal": (1.0, 4.0), "warning": (0.5, 5.0)}
        }

# Компоненты интерфейса




def render_dashboard(current_data):
    """Рендеринг главной панели мониторинга"""
    st.header("Текущие показания датчиков")
    
    if not current_data:
        st.warning("Нет данных с датчиков. Убедитесь, что генератор данных запущен.")
        return
    
    # Группировка устройств по типу
    device_by_type = {}
    for device_data in current_data:
        sensor_type = device_data["type"]
        if sensor_type not in device_by_type:
            device_by_type[sensor_type] = []
        device_by_type[sensor_type].append(device_data)
    
    # Создание вкладок для каждого типа датчиков
    tabs = st.tabs([SENSOR_TYPE_NAMES[sensor_type] for sensor_type in device_by_type.keys()])
    
    for i, (sensor_type, tab) in enumerate(zip(device_by_type.keys(), tabs)):
        with tab:
            devices = device_by_type[sensor_type]
            cols = st.columns(min(len(devices), 3))  # Максимум 3 колонки для лучшего отображения
            
            for j, device in enumerate(devices):
                col_idx = j % len(cols)  # Распределяем устройства по доступным колонкам
                with cols[col_idx]:
                    threshold_settings = st.session_state.threshold_settings[sensor_type]
                    normal_range = threshold_settings["normal"]
                    warning_range = threshold_settings["warning"]
                    
                    # Определение мин и макс значений для датчика
                    min_val = warning_range[0] - (warning_range[1] - warning_range[0]) * 0.2
                    max_val = warning_range[1] + (warning_range[1] - warning_range[0]) * 0.2
                    
                    fig = create_gauge_chart(
                        value=device["value"],
                        title=f"{device['device_id']}",
                        unit=device["unit"],
                        min_val=min_val,
                        max_val=max_val,
                        threshold_warning=normal_range,
                        threshold_critical=warning_range,
                        status=device["status"]
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    status_text = {
                        "normal": "Норма",
                        "warning": "Предупреждение",
                        "critical": "Критическое"
                    }
                    
                    st.markdown(
                        f"""
                        <div style='text-align: center;'>
                            <span style='color: {STATUS_COLORS[device["status"]]}; font-weight: bold;'>
                                {status_text[device["status"]]}
                            </span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

def render_device_details(time_window):
    """Рендеринг детальной информации об устройствах"""
    st.header("Подробная информация об устройствах")
    
    # Конвертация временного окна в часы
    hours_mapping = {
        "Последний час": 1,
        "Последние 6 часов": 6,
        "Последние 12 часов": 12,
        "Последние 24 часа": 24,
        "Последние 7 дней": 24 * 7
    }
    hours = hours_mapping[time_window]
    
    # Получение текущих данных
    current_data = get_current_data()
    if not current_data:
        st.warning("Нет данных с датчиков. Убедитесь, что генератор данных запущен.")
        return
    
    # Создание выпадающего списка с устройствами
    device_options = [f"{d['device_id']} ({SENSOR_TYPE_NAMES[d['type']]})" for d in current_data]
    selected_device_index = st.selectbox("Выберите устройство", options=range(len(device_options)), format_func=lambda x: device_options[x])
    
    selected_device = current_data[selected_device_index]
    device_id = selected_device["device_id"]
    device_type = selected_device["type"]
    device_unit = selected_device["unit"]
    
    # Получение исторических данных
    history_data = get_device_history(device_id, hours)
    
    # Отображение текущих показаний
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Текущее значение", 
            value=f"{selected_device['value']} {device_unit}",
            delta=None
        )
    
    with col2:
        threshold_settings = st.session_state.threshold_settings[device_type]
        st.metric(
            label="Нормальный диапазон", 
            value=f"{threshold_settings['normal'][0]} - {threshold_settings['normal'][1]} {device_unit}"
        )
    
    with col3:
        last_update_time = format_timestamp(selected_device["timestamp"])
        st.metric(label="Последнее обновление", value=last_update_time)
    
    # График изменения показаний
    st.subheader(f"График изменения показаний за {time_window.lower()}")
    fig = create_time_series_chart(
        history_data, 
        f"{SENSOR_TYPE_NAMES[device_type]} - {device_id}",
        device_unit
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Статистика по устройству
    st.subheader("Статистика")
    
    if history_data:
        df = pd.DataFrame(history_data)
        values = df['value']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Среднее значение", f"{values.mean():.2f} {device_unit}")
        with col2:
            st.metric("Минимум", f"{values.min():.2f} {device_unit}")
        with col3:
            st.metric("Максимум", f"{values.max():.2f} {device_unit}")
        with col4:
            st.metric("Стандартное отклонение", f"{values.std():.2f} {device_unit}")
            
        # Количество аномалий
        warnings_count = len(df[df['status'] == 'warning'])
        critical_count = len(df[df['status'] == 'critical'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Предупреждения", warnings_count)
        with col2:
            st.metric("Критические ситуации", critical_count)
    else:
        st.info(f"Нет исторических данных для {device_id} за выбранный период.")

def render_alerts(time_window):
    """Рендеринг страницы оповещений"""
    st.header("Журнал оповещений")
    
    # Конвертация временного окна в часы
    hours_mapping = {
        "Последний час": 1,
        "Последние 6 часов": 6,
        "Последние 12 часов": 12,
        "Последние 24 часа": 24,
        "Последние 7 дней": 24 * 7
    }
    hours = hours_mapping[time_window]
    
    # Получение оповещений
    alerts = get_all_alerts(hours)
    
    if not alerts:
        st.success("Нет оповещений за выбранный период.")
        return
    
    # Подсчет количества оповещений
    warning_count = len([a for a in alerts if a['status'] == 'warning'])
    critical_count = len([a for a in alerts if a['status'] == 'critical'])
    
    # Отображение статистики
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего оповещений", len(alerts))
    with col2:
        st.metric("Предупреждения", warning_count)
    with col3:
        st.metric("Критические", critical_count)
    
    # Фильтр оповещений
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_status = st.multiselect(
            "Фильтр по статусу",
            options=["warning", "critical"],
            default=["warning", "critical"],
            format_func=lambda x: "Предупреждение" if x == "warning" else "Критическое"
        )
    
    with filter_col2:
        device_types = list(set([a["type"] for a in alerts]))
        filter_types = st.multiselect(
            "Фильтр по типу устройства",
            options=device_types,
            default=device_types,
            format_func=lambda x: SENSOR_TYPE_NAMES[x]
        )
    
    # Применение фильтров
    filtered_alerts = [
        a for a in alerts 
        if a["status"] in filter_status and a["type"] in filter_types
    ]
    
    # Создание таблицы оповещений
    if filtered_alerts:
        alert_data = []
        for alert in filtered_alerts:
            alert_data.append({
                "Время": format_timestamp(alert["timestamp"]),
                "Устройство": alert["device_id"],
                "Тип": SENSOR_TYPE_NAMES[alert["type"]],
                "Значение": f"{alert['value']} {alert['unit']}",
                "Статус": "Предупреждение" if alert["status"] == "warning" else "Критическое"
            })
        
        df = pd.DataFrame(alert_data)
        
        # Применение стилей к таблице
        def highlight_status(val):
            if val == "Предупреждение":
                return f'background-color: {STATUS_COLORS["warning"]}; color: white'
            elif val == "Критическое":
                return f'background-color: {STATUS_COLORS["critical"]}; color: white'
            return ''
        
        styled_df = df.style.applymap(
            highlight_status, 
            subset=['Статус']
        )
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("Нет оповещений, соответствующих выбранным фильтрам.")

def render_settings():
    """Рендеринг страницы настроек"""
    st.header("Настройки пороговых значений")
    
    thresholds_changed = False
    
    for sensor_type, display_name in SENSOR_TYPE_NAMES.items():
        st.subheader(display_name)
        
        current_settings = st.session_state.threshold_settings[sensor_type]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Нормальный диапазон**")
            normal_min, normal_max = st.slider(
                f"Нормальный диапазон для {display_name}",
                min_value=0.0,
                max_value=150.0,
                value=(current_settings["normal"][0], current_settings["normal"][1]),
                step=0.5,
                key=f"normal_{sensor_type}"
            )
        
        with col2:
            st.markdown("**Диапазон предупреждений**")
            warning_min, warning_max = st.slider(
                f"Диапазон предупреждений для {display_name}",
                min_value=0.0,
                max_value=150.0,
                value=(current_settings["warning"][0], current_settings["warning"][1]),
                step=0.5,
                key=f"warning_{sensor_type}"
            )
        
        # Проверка на изменения пороговых значений
        if (normal_min, normal_max) != current_settings["normal"] or (warning_min, warning_max) != current_settings["warning"]:
            st.session_state.threshold_settings[sensor_type] = {
                "normal": (normal_min, normal_max),
                "warning": (warning_min, warning_max)
            }
            thresholds_changed = True
        
        st.markdown("<hr>", unsafe_allow_html=True)
    
    if thresholds_changed:
        st.success("Пороговые значения обновлены!")
    
    st.subheader("Другие настройки")
    
    # Очистка исторических данных
    if st.button("Очистить исторические данные"):
        # Получаем список файлов в директории данных
        for file in os.listdir(DATA_PATH):
            if file.startswith("history_"):
                file_path = os.path.join(DATA_PATH, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    st.error(f"Ошибка при удалении файла {file}: {e}")
        
        st.success("Исторические данные очищены")

# Функция для отображения всплывающих уведомлений об аномалиях
def show_alert_notifications(current_data):
    if not current_data:
        return
    
    # Проверяем статусы датчиков
    warning_alerts = [d for d in current_data if d["status"] == "warning"]
    critical_alerts = [d for d in current_data if d["status"] == "critical"]
    
    # Инициализируем счетчики в session_state, если их еще нет
    if 'warning_count' not in st.session_state:
        st.session_state.warning_count = 0
    if 'critical_count' not in st.session_state:
        st.session_state.critical_count = 0
    if 'shown_alerts' not in st.session_state:
        st.session_state.shown_alerts = set()
    
    # Показываем всплывающие уведомления для новых критических оповещений
    for alert in critical_alerts:
        alert_id = f"{alert['device_id']}_{alert['timestamp']}"
        if alert_id not in st.session_state.shown_alerts:
            st.session_state.shown_alerts.add(alert_id)
            
            # Используем toast для всплывающих уведомлений
            st.toast(
                f"⚠️ КРИТИЧЕСКОЕ: {SENSOR_TYPE_NAMES[alert['type']]} ({alert['device_id']}) - {alert['value']} {alert['unit']}",
                icon="⛔"  # Иконка для критического уведомления
            )
            
            # Также показываем обычное предупреждение вверху страницы
            st.warning(f"⛔ Критическая аномалия обнаружена: {SENSOR_TYPE_NAMES[alert['type']]} ({alert['device_id']}) - {alert['value']} {alert['unit']}")
    
    # Показываем всплывающие уведомления для новых предупреждений
    for alert in warning_alerts:
        alert_id = f"{alert['device_id']}_{alert['timestamp']}"
        if alert_id not in st.session_state.shown_alerts:
            st.session_state.shown_alerts.add(alert_id)
            
            # Только всплывающее уведомление для предупреждений
            st.toast(
                f"⚠️ ПРЕДУПРЕЖДЕНИЕ: {SENSOR_TYPE_NAMES[alert['type']]} ({alert['device_id']}) - {alert['value']} {alert['unit']}",
                icon="⚠️"  # Иконка для предупреждения
            )
    
    # Обновляем счетчики
    if len(critical_alerts) > st.session_state.critical_count:
        st.session_state.critical_count = len(critical_alerts)
    
    if len(warning_alerts) > st.session_state.warning_count:
        st.session_state.warning_count = len(warning_alerts)
    
    # Очищаем старые оповещения (чтобы не хранить слишком много идентификаторов)
    if len(st.session_state.shown_alerts) > 100:
        st.session_state.shown_alerts = set(list(st.session_state.shown_alerts)[-50:])

# Основная функция приложения
def main():
    # Инициализация состояния приложения
    init_app_state()
    
    # Настройка макета страницы с использованием колонок
    col1, col2 = st.columns([1, 4])
    
    # Боковая панель в левой колонке
    with col1:
        st.header("Настройки")
        
        # Секция обновления данных
        st.subheader("Обновление данных")
        auto_refresh = st.checkbox("Автоматическое обновление", value=True)
        
        refresh_interval = st.slider(
            "Интервал обновления (секунды)", 
            min_value=5, 
            max_value=60, 
            value=REFRESH_INTERVAL,
            step=5
        )
        
        if st.button("Обновить сейчас"):
            st.rerun()
        
        # Секция временного интервала для графиков
        st.subheader("Временной интервал")
        time_window = st.selectbox(
            "Показать данные за:",
            options=[
                "Последний час", 
                "Последние 6 часов", 
                "Последние 12 часов",
                "Последние 24 часа", 
                "Последние 7 дней"
            ],
            index=0
        )
        
        # Секция для админов (скрыта в данной версии)
        # if st.checkbox("Показать инструменты администратора", value=False):
        #    st.header("Тестовая аномалия")
        #    test_device = st.selectbox(
        #        "Устройство",
        #        options=[f"{sensor_type}_{i:02d}" for sensor_type in SENSOR_TYPE_NAMES.keys() for i in range(1, 4)]
        #    )
        #    
        #    test_value = st.number_input(
        #        "Значение",
        #        min_value=0.0,
        #        max_value=150.0,
        #        value=50.0,
        #        step=1.0
        #    )
        #    
        #    test_duration = st.slider(
        #        "Продолжительность (сек)",
        #        min_value=10,
        #        max_value=120,
        #        value=30,
        #        step=10
        #    )
        #    
        #    if st.button("Добавить аномалию"):
        #        st.session_state.generator.add_manual_anomaly(test_device, test_value, test_duration)
        #        st.success(f"Аномалия добавлена для устройства {test_device} на {test_duration} секунд")
        
        # Информация о последнем обновлении
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(f"**Последнее обновление:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Основной контент в правой колонке
    with col2:
        # Заголовок и описание
        st.markdown(
            """
            <h1 style='text-align: center;'>Система мониторинга сигналов</h1>
            <p style='text-align: center;'>Мониторинг и анализ показаний датчиков в реальном времени</p>
            <hr>
            """, 
            unsafe_allow_html=True
        )
        
        # Получаем текущие данные
        current_data = get_current_data()
        
        # Показываем уведомления об аномалиях
        show_alert_notifications(current_data)
        
        # Основные табы приложения
        tab1, tab2, tab3, tab4 = st.tabs(["Панель мониторинга", "Подробная информация", "Оповещения", "Настройки"])
        
        with tab1:
            render_dashboard(current_data)
        
        with tab2:
            render_device_details(time_window)
        
        with tab3:
            render_alerts(time_window)
        
        with tab4:
            render_settings()
    
    # Автоматическое обновление
    if auto_refresh:
        time.sleep(0.1)  # Небольшая задержка для корректного рендеринга
        st.rerun()

if __name__ == "__main__":
    main()
