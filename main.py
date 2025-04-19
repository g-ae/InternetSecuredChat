import window_interaction

if __name__ == '__main__':
    """
    Main entry point for the application.
    Starts the GUI window and handles uncaught exceptions.
    """

    try:
        window_interaction.load_window()
    except Exception as e:
        print(f"error : {e}")
