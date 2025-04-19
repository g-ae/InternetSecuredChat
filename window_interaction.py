import threading
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6 import uic
import server_interaction
from signals import comm

class ChatWindow(QMainWindow):
    """
    Main application window for the encrypted chat application.
    Inherits from QMainWindow to create the GUI interface.
    """

    def __init__(self):
        """
        Initialize the chat window and set up the UI components.
        """
        super().__init__()
        uic.loadUi("ui/InternetSecuredChat_V1.ui", self)
        self._setup_ui()
        self._connect_signals()
        self._connect_to_server()

    def _setup_ui(self):
        """
        Configure initial UI components state and appearance.
        """
        # Disable focus on chat zone
        self.plainTextEdit_chat.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Initialize the display of the size label
        self._update_size_label(self.sl_size.value())

        # Select the first encode type by default
        if self.listWidget_type.count() > 0:
            self.listWidget_type.setCurrentRow(0)

    def _connect_signals(self):
        """
        Connect UI elements to their corresponding event handlers.
        """
        # Slider connections
        self.sl_size.valueChanged.connect(self._update_size_label)

        # Button connections
        self.btn_connect.clicked.connect(self._connect_to_server)
        self.listWidget_type.itemSelectionChanged.connect(self._change_encoding_values)
        self.lineEdit_message.returnPressed.connect(self._send_message)
        self.btn_send.clicked.connect(self._send_task)

        # Text display connections
        comm.chat_message.connect(self._add_message)
        comm.decoded_message.connect(self._add_decoded)

    def _update_size_label(self, value):
        """
        Update the size indicator label with the current slider value.

        Args:
            value (int): The current value of the slider
        """
        self.lbl_10.setText(str(value))

    def _connect_to_server(self):
        """
        Handle connection/disconnection to the chat server.
        Toggles between connecting and disconnecting based on current connection state.
        """
        # Disconnect if already connected
        if server_interaction.connection_state == 1:
            self.btn_connect.setText("CONNECT")
            server_interaction.close_connection()
            self._add_message("<INFO> Disconnected from server")

        # Connect if not connected or connection failed
        elif server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            global host, port
            host = self.lineEdit_address.text()
            port = int(self.lineEdit_port.text())
            server_interaction.stop_event.clear()  # Reset the Event
            t = threading.Thread(target=server_interaction.open_connection, daemon=True)
            t.start()
            self.btn_connect.setText("CONNECTING ...")
            self.btn_connect.setEnabled(False)

    def connected(self):
        """
        Update UI after connection attempt completes.
        Called by server_interaction module when connection state changes.
        """
        if server_interaction.connection_state == 1:
            # Connected successfully
            self._add_message("<INFO> Connected to server")
            self.btn_connect.setText("DISCONNECT")
        else:
            # Connection Error
            self._add_message("<INFO> Error while trying to connect to the server. Check it's address and try again !")
            self.btn_connect.setText("CONNECT")
        self.btn_connect.setEnabled(True)

    def _send_message(self):
        """
        Send a regular text message to the server.
        Checks if connected before attempting to send.
        """
        if server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            self._add_message("<INFO> Server not connected")
        else:
            msg = self.lineEdit_message.text()
            server_interaction.send_message(msg)
            self.lineEdit_message.clear()

    def _send_task(self):
        """
        Send a task command to the server based on the selected encoding type and parameters.
        Tasks include encode/decode operations with various cryptographic algorithms.
        """
        if server_interaction.connection_state == -1 or server_interaction.connection_state == 0:
            self._add_message("<INFO> Server not connected")
        else:
            encoding = "Aucun"
            if self.listWidget_type.currentItem(): encoding = self.listWidget_type.currentItem().text()

            size = str(self.sl_size.value())

            if (self.rd_btn_encode.isChecked()):
                command = self.rd_btn_encode.text()
            else:
                command = self.rd_btn_decode.text()

            if encoding == "hash":
                msg = f"/task {encoding} {command}"
            elif encoding == "DifHel":
                msg = f"/task {encoding}"
            else:
                msg = f"/task {encoding} {command} {size}"

            server_interaction.send_message(msg)

    def _add_message(self, text):
        """
        Add a message to the main chat display.

        Args:
            text (str): Message text to display
        """
        self.plainTextEdit_chat.appendPlainText(text)

    def _add_decoded(self, text):
        """
        Add a message to the decoded messages display area.

        Args:
            text (str): Decoded message text to display
        """
        self.plainTextEdit_decoded.appendPlainText(text)

    def _change_encoding_values(self):
        """
        Update UI elements based on the selected encoding type.
        Different encoding methods require different UI controls.
        """
        match self.listWidget_type.currentItem().text():
            case "hash":
                # Enable/Disable radio buttons and size selector
                self.rd_btn_encode.setEnabled(True)
                self.rd_btn_decode.setEnabled(True)
                self.sl_size.setEnabled(False)
                self.rd_btn_encode.setText("verify")
                self.rd_btn_decode.setText("hash")
            case "DifHel":
                self.rd_btn_encode.setEnabled(False)
                self.rd_btn_decode.setEnabled(False)
                self.sl_size.setEnabled(False)
            case _:
                self.rd_btn_encode.setEnabled(True)
                self.rd_btn_decode.setEnabled(True)
                self.sl_size.setEnabled(True)
                self.rd_btn_encode.setText("encode")
                self.rd_btn_decode.setText("decode")

    def _get_encoding_values(self):
        """
        Get the currently selected encoding type and size parameter.

        Returns:
            tuple: (encoding_type, size_value)
        """
        return (self.listWidget_type.currentItem().text(), self.sl_size.value())

    def _clear_chat(self):
        """
        Clear both chat display areas (main chat and decoded messages).
        """
        self.plainTextEdit_chat.clear()
        self.plainTextEdit_decoded.clear()

app = QApplication([])
window = ChatWindow()
host = "vlbelintrocrypto.hevs.ch"  # Default server host
port = 6000  # Default server port

def load_window():
    """
    Initialize and display the application window.
    Handles cleanup on application exit.
    """
    window.show()
    app.exec()
    server_interaction.close_connection()
