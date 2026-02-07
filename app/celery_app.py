from celery import Celery



from celery import Celery

def create_celery_app():
    # Создаем экземпляр
    instance = Celery(
        "decisionshub",
        broker="redis://127.0.0.1:6379/0",
        backend="redis://127.0.0.1:6379/0",
        include=["app.utilits"]  # Путь к  задачи
    )

    # Применяем настройки
    instance.conf.update(
        task_track_started=True, #вкл статус старт для задач
        broker_connection_retry_on_startup=True, #повторяет подкл
        worker_prefetch_multiplier=1  # Важно для стабильности на Windows
    )
    return instance

# Создаем объект, который будем импортировать в main и воркер
celery_app = create_celery_app()
