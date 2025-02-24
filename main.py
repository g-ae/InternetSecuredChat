import server_interaction
import window_interaction
import threading

if __name__ == '__main__':
    t = threading.Thread(target=window_interaction.load_window)
    t.start()

    server_interaction.open_connection()