import os
import subprocess
import sys

def main():
    """
    Запуск приложения мониторинга сигналов.
    Этот скрипт запускает приложение Streamlit, которое автоматически
    запускает генератор данных.
    """
    print("Запуск приложения мониторинга сигналов...")
    
    # Определяем путь к app.py
    app_path = os.path.join(os.path.dirname(__file__), "src", "app.py")
    
    # Проверяем, существует ли файл
    if not os.path.exists(app_path):
        print(f"Ошибка: файл {app_path} не найден.")
        sys.exit(1)
    
    try:
        # Запускаем Streamlit-приложение
        subprocess.run(["streamlit", "run", app_path], check=True)
    except FileNotFoundError:
        print("Ошибка: не удалось запустить Streamlit. Убедитесь, что он установлен.")
        print("Вы можете установить зависимости, выполнив: pip install -r requirements.txt")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при запуске приложения: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nПриложение остановлено пользователем.")

if __name__ == "__main__":
    main()
