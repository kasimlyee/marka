from PySide6.QtGui import QPalette, QColor

class Theme:
    def __init__(self):
        """
        Initialize the Theme instance with predefined QColor objects for
        various UI elements, including primary, secondary, accent, background,
        error, success, and warning colors.
        """

        self.primary = QColor("#1D3557")
        self.secondary = QColor("#2A9D8F")
        self.accent = QColor("#F4A261")
        self.background = QColor("#F1FAEE")
        self.error = QColor("#E63946")
        self.success = QColor("#10B981")
        self.warning = QColor("#F59E0B")
        
    def apply_to_widget(self, widget):
        """
        Applies the theme to the given widget.

        This function sets the following colors:

        - Window: background
        - WindowText: primary
        - Base: white
        - AlternateBase: background
        - ToolTipBase: primary
        - ToolTipText: white
        - Text: primary
        - Button: secondary
        - ButtonText: white
        - BrightText: white
        - Highlight: secondary
        - HighlightedText: white
        """
        palette = widget.palette()
        palette.setColor(QPalette.Window, self.background)
        palette.setColor(QPalette.WindowText, self.primary)
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, self.background)
        palette.setColor(QPalette.ToolTipBase, self.primary)
        palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Text, self.primary)
        palette.setColor(QPalette.Button, self.secondary)
        palette.setColor(QPalette.ButtonText, QColor("#FFFFFF"))
        palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        palette.setColor(QPalette.Highlight, self.secondary)
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        widget.setPalette(palette)
