import threading
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6 import uic
import server_interaction
from signals import comm

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
        if self.listWidget_type.count() > 0:
            self.listWidget_type.setCurrentRow(0)

    def _connect_signals(self):
        # Slider
        self.sl_size.valueChanged.connect(self._update_size_label)

        # Buttons
        self.btn_connect.clicked.connect(self._connect_to_server)
        self.listWidget_type.itemSelectionChanged.connect(self._change_encoding_values)
        self.lineEdit_message.returnPressed.connect(self._send_message)
        self.btn_send.clicked.connect(self._send_task)

        # Plain Text
        comm.chat_message.connect(self._add_message)

    def _update_size_label(self, value):
        self.lbl_10.setText(str(value))

    def _connect_to_server(self):
        # Disconnect
        if server_interaction.connection_state == 1:
            self.btn_connect.setText("CONNECT")
            server_interaction.close_connection()
            self._add_message("<INFO> Disconnected from server")

        # Connect
        elif server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            global host, port
            host = self.lineEdit_address.text()
            port = int(self.lineEdit_port.text())
            server_interaction.stop_event.clear()  # Réinitialise l'Event
            t = threading.Thread(target=server_interaction.open_connection, daemon=True)
            t.start()
            self.btn_connect.setText("CONNECTING ...")
            self.btn_connect.setEnabled(False)

    def connected(self):
        if server_interaction.connection_state == 1:
            # connected successfully
            self._add_message("<INFO> Connected to server")
            self.btn_connect.setText("DISCONNECT")
        else:
            # Connection Error
            self._add_message("<INFO> Error while trying to connect to the server. Check it's address and try again !")
            self.btn_connect.setText("CONNECT")
        self.btn_connect.setEnabled(True)

    def _send_message(self):
        if server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            self._add_message("<INFO> Server not connected")
        else :
            msg = self.lineEdit_message.text()
            server_interaction.send_message(msg)
            self.lineEdit_message.clear()

    def _send_task(self):
        if server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            self._add_message("<INFO> Server not connected")
        else:
            encoding = "Aucun"
            if self.listWidget_type.currentItem(): encoding = self.listWidget_type.currentItem().text()

            size = str(self.sl_size.value())

            if (self.rd_btn_encode.isChecked()) : command = self.rd_btn_encode.text()
            else : command = self.rd_btn_decode.text()

            if encoding == "hash": msg = f"/task {encoding} {command}"
            else: msg = f"/task {encoding} {command} {size}"

            server_interaction.send_message(msg)

    def _add_message(self, text):
        self.plainTextEdit_chat.appendPlainText(text)

    def _change_encoding_values(self):
        match self.listWidget_type.currentItem().text():
            case "hash":
                self.rd_btn_encode.setEnabled(True)
                self.rd_btn_decode.setEnabled(True)
                self.rd_btn_encode.setText("verify")
                self.rd_btn_decode.setText("hash")
            case "DifHel":
                self.rd_btn_encode.setEnabled(False)
                self.rd_btn_decode.setEnabled(False)
            case _:
                self.rd_btn_encode.setEnabled(True)
                self.rd_btn_decode.setEnabled(True)
                self.rd_btn_encode.setText("encode")
                self.rd_btn_decode.setText("decode")

app = QApplication([])
window = ChatWindow()
host = ""
port = 0

def load_window():
    window.show()
    app.exec()
    server_interaction.close_connection()
