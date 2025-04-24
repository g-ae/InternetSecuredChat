from PyQt6.QtCore import pyqtSignal, QObject

class Communicator(QObject):
    """
    Signal communication class for transmitting events between threads in the application.
    Inherits from QObject to use Qt's signal system.
    """

    chat_message = pyqtSignal(str)      # Signal for sending chat messages to the UI
    decoded_message = pyqtSignal(str)   # Signal for sending decoded messages to the UI

comm = Communicator()   # Global communicator instance for use across modules
