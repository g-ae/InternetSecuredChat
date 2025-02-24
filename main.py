import server_interaction
import window_interaction
import threading

if __name__ == '__main__':
    try:
        print("Ouverture de la connexion au serveur...")
        t = threading.Thread(target=server_interaction.open_connection, daemon=True)
        t.start()

        print("Démarrage de la fenêtre...")
        window_interaction.load_window()  # Exécuter dans le thread principal

    except Exception as e:
        print(f"Erreur : {e}")
