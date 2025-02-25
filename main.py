import server_interaction
import window_interaction
import threading

if __name__ == '__main__':
    try:
        print("[CONNECTION] Opening...")
        t = threading.Thread(target=server_interaction.open_connection, daemon=True)
        t.start()

        print("[WINDOW]     Opening ...")
        window_interaction.load_window()  # Exécuter dans le thread principal

    except Exception as e:
        print(f"Erreur : {e}")
