from PyQt6.QtCore import pyqtSignal, QObject

class Communicator(QObject):
    chat_message = pyqtSignal(str)

comm = Communicator()
