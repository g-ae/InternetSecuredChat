from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
import server_interaction

text_area = ""
message = ""

def load_window():
    app = QApplication([])
    global text_area
    text_area = QPlainTextEdit()
    text_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    global message
    message = QLineEdit()
    layout = QVBoxLayout()
    layout.addWidget(text_area)
    layout.addWidget(message)
    window = QWidget()
    window.setLayout(layout)
    window.show()
    def send_message():
        server_interaction.send_message(message.text())

    # Signals:
    message.returnPressed.connect(send_message)

    # Wait for server connection
    while server_interaction.connection_state == -1:
        pass

    # If connection couldn't be established
    if server_interaction.connection_state == 0:
        print("[Window] Connection failed, window will not open.")
        exit(1)

    # Connection established, show window
    out_code = app.exec()

    server_interaction.close_connection()

    exit(out_code)

def add_message(text):
    global message
    message.setText("")
    global text_area
    text_area.appendPlainText(text)
    return