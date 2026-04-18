class DashboardShutdownController:
    def __init__(self, save_before_quit=None, quit_app=None):
        self.save_before_quit = save_before_quit or (lambda: None)
        self.quit_app = quit_app or self._default_quit_app

    @staticmethod
    def _default_quit_app():
        from PyQt6.QtWidgets import QApplication

        QApplication.quit()

    def execute(self):
        self.save_before_quit()
        self.quit_app()
