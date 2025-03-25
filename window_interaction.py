import threading
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6 import uic
import server_interaction

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/InternetSecuredChat_V1.ui", self)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        # Disable focus on chat zone
        self.plainTextEdit_chat.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Init the display of the size label
        self._update_size_label(self.sl_size.value())

        # Select the first encode by default
        if self.listWidget_encode.count() > 0:
            self.listWidget_encode.setCurrentRow(0)

    def _connect_signals(self):
        # Slider
        self.sl_size.valueChanged.connect(self._update_size_label)

        # Buttons
        self.btn_connect.clicked.connect(self._connect_to_server)
        self.lineEdit_message.returnPressed.connect(self._send_message)
        self.btn_send.clicked.connect(self._send_task)

    def _update_size_label(self, value):
        self.lbl_10.setText(str(value))

    def _connect_to_server(self):
        if server_interaction.connection_state == 1:
            self.btn_connect.setText("CONNECT")
            server_interaction.close_connection()

        elif server_interaction.connection_state == -1:
            global host, port
            host = self.lineEdit_address.text()
            port = int(self.lineEdit_port.text())
            server_interaction.stop_event.clear()  # Réinitialise l'Event
            t = threading.Thread(target=server_interaction.open_connection, daemon=True)
            t.start()
            self.btn_connect.setText("DISCONNECT")

    def _send_message(self):
        if server_interaction.connection_state == -1 :
            self._add_message("<INFO> Server not connected")
        else :
            msg = self.lineEdit_message.text()
            server_interaction.send_message(msg)
            self.lineEdit_message.clear()

    def _send_task(self):
        if server_interaction.connection_state == -1:
            self._add_message("<INFO> Server not connected")
        else:
            encoding = "Aucun"
            if self.listWidget_encode.currentItem():
                encoding = self.listWidget_encode.currentItem().text()

            # Récupère la taille
            size = str(self.sl_size.value())

            msg = f"/task {encoding} encode {size}"
            server_interaction.send_message(msg)

    def _add_message(self, text):
        self.plainTextEdit_chat.appendPlainText(text)

app = QApplication([])
window = ChatWindow()
host = ""
port = 0

def load_window():
    window.show()
    app.exec()
    server_interaction.close_connection()

def add_message(text):
    window._add_message(text)
    return