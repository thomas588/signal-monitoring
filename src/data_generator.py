import json
import random
import time
import threading
import os
from datetime import datetime
import math

class SensorDataGenerator:
    """
    Класс для эмуляции работы IoT-датчиков и генерации данных.
    """
    
    def __init__(self, data_path="../data"):
        """
        Инициализация генератора данных.
        
        Args:
            data_path (str): Путь к директории для сохранения данных
        """
        self.data_path = data_path
        self.ensure_data_dir()
        
        # Настройки базовых значений для различных типов датчиков
        self.sensor_configs = {
            "temperature": {
                "base_value": 22.0,
                "unit": "°C",
                "normal_range": (15.0, 30.0),
                "warning_range": (10.0, 35.0),
                "variance": 0.5,
                "trend_amplitude": 5.0,
                "trend_period": 3600,  # период в секундах (1 час)
            },
            "humidity": {
                "base_value": 45.0,
                "unit": "%",
                "normal_range": (30.0, 60.0),
                "warning_range": (20.0, 70.0),
                "variance": 2.0,
                "trend_amplitude": 15.0,
                "trend_period": 7200,  # период в секундах (2 часа)
            },
            "pressure": {
                "base_value": 101.3,
                "unit": "кПа",
                "normal_range": (99.0, 103.0),
                "warning_range": (98.0, 104.0),
                "variance": 0.2,
                "trend_amplitude": 1.0,
                "trend_period": 10800,  # период в секундах (3 часа)
            },
            "vibration": {
                "base_value": 15.0,
                "unit": "Гц",
                "normal_range": (5.0, 25.0),
                "warning_range": (2.0, 35.0),
                "variance": 1.0,
                "trend_amplitude": 3.0,
                "trend_period": 1800,  # период в секундах (30 минут)
            },
            "noise": {
                "base_value": 65.0,
                "unit": "дБ",
                "normal_range": (50.0, 75.0),
                "warning_range": (45.0, 85.0),
                "variance": 2.0,
                "trend_amplitude": 10.0,
                "trend_period": 900,  # период в секундах (15 минут)
            },
            "power": {
                "base_value": 2.5,
                "unit": "кВт·ч",
                "normal_range": (1.0, 4.0),
                "warning_range": (0.5, 5.0),
                "variance": 0.3,
                "trend_amplitude": 1.5,
                "trend_period": 3600,  # период в секундах (1 час)
            }
        }
        
        # Для каждого типа датчика создать несколько устройств
        self.devices = []
        for sensor_type in self.sensor_configs:
            for i in range(1, 4):  # Создаем 3 устройства каждого типа
                device_id = f"{sensor_type}_{i:02d}"
                self.devices.append({
                    "device_id": device_id,
                    "type": sensor_type
                })
        
        self.running = False
        self.thread = None
        self.anomaly_probability = 0.01  # 1% вероятность аномалии
        self.manual_anomalies = {}  # Для ручного внесения аномалий
    
    def ensure_data_dir(self):
        """Убедиться, что директория для данных существует"""
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
    
    def generate_value(self, device, timestamp):
        """
        Генерация значения датчика с учетом настроек, трендов и аномалий.
        
        Args:
            device (dict): Информация об устройстве
            timestamp (float): Временная метка
            
        Returns:
            tuple: (значение, статус)
        """
        sensor_type = device["type"]
        config = self.sensor_configs[sensor_type]
        
        # Проверка на ручные аномалии
        if device["device_id"] in self.manual_anomalies:
            anomaly = self.manual_anomalies[device["device_id"]]
            if anomaly["end_time"] >= timestamp:
                return anomaly["value"], "critical"
            else:
                # Удаляем истекшую аномалию
                del self.manual_anomalies[device["device_id"]]
        
        # Вычисление значения с учетом тренда
        trend_component = config["trend_amplitude"] * math.sin(
            2 * math.pi * timestamp / config["trend_period"]
        )
        
        # Случайное отклонение (Гауссово распределение)
        random_component = random.gauss(0, config["variance"])
        
        # Определение финального значения
        value = config["base_value"] + trend_component + random_component
        
        # Случайная аномалия
        if random.random() < self.anomaly_probability:
            # Значительное отклонение от нормы
            direction = 1 if random.random() > 0.5 else -1
            anomaly_magnitude = (config["normal_range"][1] - config["normal_range"][0]) * random.uniform(1.2, 1.5)
            value = value + direction * anomaly_magnitude
        
        # Определение статуса
        status = "normal"
        if value < config["normal_range"][0] or value > config["normal_range"][1]:
            status = "warning"
        if value < config["warning_range"][0] or value > config["warning_range"][1]:
            status = "critical"
        
        return round(value, 2), status
    
    def add_manual_anomaly(self, device_id, value, duration=60):
        """
        Добавить ручную аномалию для устройства.
        
        Args:
            device_id (str): ID устройства
            value (float): Аномальное значение
            duration (int): Продолжительность аномалии в секундах
        """
        self.manual_anomalies[device_id] = {
            "value": value,
            "end_time": time.time() + duration
        }
    
    def generate_data(self):
        """Генерация и сохранение данных для всех устройств"""
        while self.running:
            timestamp = time.time()
            current_time = datetime.fromtimestamp(timestamp)
            
            data_batch = []
            
            for device in self.devices:
                value, status = self.generate_value(device, timestamp)
                
                sensor_data = {
                    "device_id": device["device_id"],
                    "type": device["type"],
                    "value": value,
                    "unit": self.sensor_configs[device["type"]]["unit"],
                    "timestamp": timestamp,
                    "status": status
                }
                data_batch.append(sensor_data)
                
                # Сохранение в отдельный файл для каждого устройства
                device_file_path = os.path.join(self.data_path, f"{device['device_id']}.json")
                self.save_device_data(device_file_path, sensor_data)
            
            # Сохранение текущих данных всех устройств в единый файл
            current_data_path = os.path.join(self.data_path, "current_data.json")
            with open(current_data_path, 'w') as file:
                json.dump(data_batch, file, indent=2)
            
            # Сохранение исторических данных
            history_path = os.path.join(self.data_path, f"history_{current_time.strftime('%Y%m%d')}.json")
            self.save_history_data(history_path, data_batch)
            
            # Задержка перед следующей генерацией
            time.sleep(5)  # обновление каждые 5 секунд
    
    def save_device_data(self, file_path, data):
        """
        Сохранение последних данных устройства.
        
        Args:
            file_path (str): Путь к файлу устройства
            data (dict): Данные датчика
        """
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=2)
    
    def save_history_data(self, file_path, data_batch):
        """
        Добавление данных в исторический файл.
        
        Args:
            file_path (str): Путь к файлу истории
            data_batch (list): Список данных со всех устройств
        """
        history_data = []
        
        # Если файл существует, загружаем его содержимое
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                try:
                    history_data = json.load(file)
                except json.JSONDecodeError:
                    history_data = []
        
        # Добавляем новые данные
        history_data.extend(data_batch)
        
        # Ограничиваем размер файла (хранение за последние 24 часа)
        # 24 часа * 60 минут * 60 секунд / 5 секунд * кол-во устройств
        max_records = int(24 * 60 * 60 / 5 * len(self.devices))
        if len(history_data) > max_records:
            history_data = history_data[-max_records:]
        
        # Сохраняем обновленную историю
        with open(file_path, 'w') as file:
            json.dump(history_data, file, indent=2)
    
    def start(self):
        """Запуск генератора данных в отдельном потоке"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.generate_data)
            self.thread.daemon = True
            self.thread.start()
            print("Генератор данных запущен")
    
    def stop(self):
        """Остановка генератора данных"""
        if self.running:
            self.running = False
            self.thread.join()
            print("Генератор данных остановлен")


if __name__ == "__main__":
    # Тестовый запуск генератора
    generator = SensorDataGenerator()
    generator.start()
    
    try:
        # Добавление тестовой аномалии через 15 секунд
        time.sleep(15)
        generator.add_manual_anomaly("temperature_01", 45.0, duration=20)
        print("Добавлена тестовая аномалия")
        
        # Позволяем генератору работать некоторое время
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        generator.stop()
