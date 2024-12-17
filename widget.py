import sys
import asyncio
from PySide6.QtWidgets import QMainWindow, QApplication, QTableView, QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PySide6.QtCore import QTimer,  QThread, Signal, QObject

from tradingview_ta import TA_Handler, Interval, Exchange


class Worker(QObject):
    result = Signal(object)  # Сигнал для передачи результатов в основной поток

    def __init__(self, parent=None):
        super().__init__(parent)

    def get_analysis_result(self, row_key, _screener, _exchange, column_value):
        """Синхронная операция, выполняется в другом потоке"""
        _handler = TA_Handler(
            symbol=row_key,
            screener=_screener,
            exchange=_exchange,
            interval=column_value
        )

        result = _handler.get_analysis().summary
        return result

    async def async_get_analysis_result(self, row_key, _screener, _exchange, column_value):
        """Обертка для синхронного кода через asyncio.to_thread"""
        return await asyncio.to_thread(self.get_analysis_result, row_key, _screener, _exchange, column_value)

    async def run_task(self, row_key, column):
        """Основная асинхронная задача для обработки валютных пар и интервалов"""
        # print(f"Starting task for {row_key}...")  # Печать для отладки
        self._screener = 'forex'
        self._exchange = "FX_IDC"
        tasks = []  # Список для хранения асинхронных задач

        try:
            # Перебираем все интервалы (колонки)
            for column_key, value in column.items():
                # Получаем значение интервала
                column_value = getattr(Interval, column_key)

                # Добавляем задачу для получения анализа в список задач
                tasks.append(self.async_get_analysis_result(
                    row_key, self._screener, self._exchange, column_value))

            # Выполняем все задачи параллельно и ждем их завершения
            results = await asyncio.gather(*tasks)

            # Обработка полученных результатов
            result_data = {
                "row_key": row_key,
                "column": {}  # Формируем пустой словарь для столбцов
            }

            for column_key, result in zip(column.keys(), results):

                result_data["column"][column_key] = result['RECOMMENDATION']

            # Отправляем результат через сигнал
            self.result.emit(result_data)  # Отправка данных в основной поток

        except Exception as e:
            # Обработка ошибок
            print(f"Ошибка: {e}")


class AsyncWorkerThread(QThread):
    def __init__(self, parent=None, matrix_data=None):
        super().__init__(parent)
        self.matrix_data = matrix_data  # Храним matrix_data
        self.worker = Worker(parent=self)  # Создаем объект Worker
        # Подключаем сигнал результата
        self.worker.result.connect(self.on_result)
        self.loop = None  # Цикл событий будет инициализирован позже

    def run(self):
        """Запуск нового цикла событий для асинхронных задач"""
        self.loop = asyncio.new_event_loop()  # Создаем новый цикл событий
        # Устанавливаем цикл событий для текущего потока
        asyncio.set_event_loop(self.loop)

        # Формируем список задач
        tasks = self.create_tasks()

        # Запуск всех задач и ожидание их завершения

        self.loop.run_until_complete(self.run_async_tasks(tasks))

    def create_tasks(self):
        """Создание списка задач для обработки данных"""
        rows = list(self.matrix_data.keys())
        tasks = []  # Список для хранения задач

        for row_key in rows:
            # Создаем задачу для каждой строки
            task = self.loop.create_task(self.worker.run_task(
                row_key, self.matrix_data[row_key]))
            tasks.append(task)  # Добавляем задачу в список

        return tasks

    async def run_async_tasks(self, tasks):
        """Запуск всех задач параллельно и ожидание их завершения"""
        await asyncio.gather(*tasks)

    def on_result(self, result):
        """Обработка полученных результатов в основном потоке"""

        self.parent().on_result(result)  # Отправка результата в родительский класс


class WorkerThread(QThread):
    # Сигнал должен быть определён с типом данных, которые вы хотите передавать.
    # Предположим, что `self.matrix_data` - это словарь.
    result = Signal(dict)  # Тип сигнала: передаём словарь

    def __init__(self,  row_key, column, parent=None):
        super().__init__(parent)

        self._screener = 'forex'
        self._exchange = "FX_IDC"

        #  тут у нас ключ  а в колонках интервалы

        self.row_key = row_key
        self.column = column

    def run(self):
        try:
            # Перебираем все строки (валютные пары)

            for column_key, value in self.column.items():
                # Печатаем комбинацию валютной пары и интервала с значением
                column_value = getattr(Interval, column_key)

                _handler = TA_Handler(
                    symbol=self.row_key,
                    screener=self._screener,
                    exchange=self._exchange,
                    interval=column_value
                )
                result = _handler.get_analysis().summary

                self.column[column_key] = result['RECOMMENDATION']

            self.result.emit(self.column)

        except Exception as e:
            # Обработка ошибок
            print(f"Ошибка: {e}")

        # self.result.emit()


class MatrixViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        tiker_array = []
        tiker_array.append('AUDCAD')
        tiker_array.append('AUDCHF')
        tiker_array.append('AUDJPY')
        tiker_array.append('AUDUSD')
        tiker_array.append('CADCHF')
        tiker_array.append('CADJPY')
        tiker_array.append('CHFJPY')
        tiker_array.append('EURAUD')
        tiker_array.append('EURCAD')
        tiker_array.append('EURCHF')
        tiker_array.append('EURGBP')
        tiker_array.append('EURJPY')
        tiker_array.append('EURUSD')
        tiker_array.append('GBPAUD')
        tiker_array.append('GBPCAD')
        tiker_array.append('GBPCHF')
        tiker_array.append('GBPJPY')
        tiker_array.append('GBPUSD')
        tiker_array.append('USDCAD')
        tiker_array.append('USDCHF')
        tiker_array.append('USDJPY')

        matrix = {}

        for i, value_tiker in enumerate(tiker_array):
            matrix[value_tiker] = {}
            counter = 0
            for j, value in Interval.__dict__.items():
                column_name = j  # Имя столбца
                if not column_name.startswith("__"):
                    if counter >= 8:
                        break
                    # Пример значения, вы можете задать свои вычисления
                    counter += 1
                    matrix[value_tiker][column_name] = 0

        self.matrix_data = matrix  # Данные матрицы

        # # Инициализируем model

        self.model = QStandardItemModel()  # Это пример использования QStandardItemModel
        self.table_view = QTableView(self)
        self.table_view.setModel(self.model)
        self.table_view.resizeColumnsToContents()
        # Настройка окна
        self.setWindowTitle("Matrix Viewer")
        self.setGeometry(100, 100, 900, 700)  # Размер окна 900x700

        # Создаем основной виджет
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Используем QVBoxLayout для размещения QTableView
        layout = QVBoxLayout()
        layout.addWidget(self.table_view)

        # Устанавливаем layout для центрального виджета
        central_widget.setLayout(layout)

        # Убедитесь, что таблица будет растягиваться с окном
        self.table_view.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.worker = None  # Поток еще не запущен
        self.timer = QTimer(self)

        self.worker_thread = AsyncWorkerThread(self, self.matrix_data)

        self.timer.timeout.connect(self.start_worker)
        self.timer.start(10000)  # Период 10 секунда

        self.worker_threads = []

        self.update_model()

    def start_worker(self):

        self.worker_thread.start()  # Запуск потока

    def on_result(self, result):

        # Распаковка словаря
        # Извлекаем значение по ключу 'row_key'
        row_key = result.get("row_key")
        # Извлекаем значение по ключу 'column'
        input_column = result.get("column")

        # Перебор словаря
        counter = 0
        counter_strong = 0
        # индекс строки не меняется
        row_index = list(self.matrix_data.keys()).index(row_key)

        for column, value in input_column.items():
            self.matrix_data[row_key][column] = value

            # Находим индексы строки и столбца

            column_index = list(self.matrix_data[row_key].keys()).index(column)

            # Обновляем значение в модели
            item = QStandardItem(str(value))
            self.model.setItem(row_index, column_index, item)

            if value == 'STRONG_SELL':
                counter -= 1
                counter_strong -= 1
                # Красный цвет для 'STRONG_SELL'
                item.setBackground(QColor(220, 20, 60))
            elif value == 'SELL':
                counter -= 1
                # Красный LightSalmon
                item.setBackground(QColor(255, 160, 122))

            elif value == 'STRONG_BUY':
                counter += 1
                counter_strong += 1
                # Зеленый цвет для 'STRONG_BUY'
                item.setBackground(QColor(50, 205, 50))

            elif value == 'BUY':
                counter += 1
                # Зеленый LightGreen
                item.setBackground(QColor(144, 238, 144))

            else:
                # Белый цвет для всех остальных значений
                counter = 0
                item.setBackground(QColor(255, 255, 255))

        # Установка жирного шрифта для строки
        self.setBoldFontForRow(row_index, counter, counter_strong)
        # Обновление отображения
        self.table_view.viewport().update()

    def setBoldFontForRow(self, row_index, counter, counter_strong):
        """Метод для установки жирного шрифта в зависимости от условий"""
        font = QFont()

        # Если counter >= 7 или <= -7, делаем шрифт жирным
        if counter >= 8 or counter <= -8:
            if counter_strong >= 5 or counter_strong <= -5:
                font.setBold(True)
                # Устанавливаем увеличенный размер шрифта
                font.setPointSize(14)
        else:
            font.setBold(False)
            font.setPointSize(10)   # Размер по умолчанию

        # Устанавливаем шрифт для всей строки
        for column_index in range(self.model.columnCount()):
            item = self.model.item(row_index, column_index)
            if item:
                item.setFont(font)

    def update_model(self):
        """
        Обновление модели данных в таблице.
        Перезаполняем таблицу новыми данными.
        """
        self.rows = list(self.matrix_data.keys())  # Валютные пары (строки)
        # Интервалы (столбцы)
        self.columns = list(next(iter(self.matrix_data.values())).keys())

        # Обновляем модель
        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.columns)
        self.model.setVerticalHeaderLabels(self.rows)

        self.table_view.resizeColumnsToContents()


if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = MatrixViewer()
    window.show()  # Показываем окно
    sys.exit(app.exec())  # Запуск цикла обработки событий
