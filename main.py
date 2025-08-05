import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from qt_material import apply_stylesheet
from app.main_window import MainWindow
from app.models.data_models import NotificationType
from utils.logger import setup_logging

logger = setup_logging(__name__)


def main():
    """Main application entry point"""
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Marka Report Card System")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Marka Educational Solutions")
        
        # Apply material design theme
        try:
            apply_stylesheet(app, theme='light_blue.xml')
        except Exception as e:
            logger.warning(f"Failed to apply material theme: {e}")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        # Show welcome notification after a short delay
        QTimer.singleShot(1000, lambda: window.notification_manager.show(
            "Welcome to Marka Report Card System Enterprise Edition!",
            NotificationType.SUCCESS,
            4000
        ))
        
        # Run application
        return app.exec()
        
    except Exception as e:
        logger.critical(f"Critical error starting application: {e}")
        if 'app' in locals():
            QMessageBox.critical(None, "Critical Error", f"Failed to start application:\n{e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())