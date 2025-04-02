import window_interaction

if __name__ == '__main__':
    try:
        window_interaction.load_window()
    except Exception as e:
        print(f"error : {e}")