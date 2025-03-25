import window_interaction

if __name__ == '__main__':
    try:
        print("[WINDOW]     Opening ...")
        window_interaction.load_window()

    except Exception as e:
        print(f"Erreur : {e}")