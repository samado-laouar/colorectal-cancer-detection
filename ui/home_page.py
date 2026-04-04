from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt


class HomePage(QWidget):
    def __init__(self, navigator):
        """
        navigator: the AppWindow (QStackedWidget) that controls page switching
        """
        super().__init__()
        self.navigator = navigator
        self.apply_style()
        self.setup_ui()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                color: #1e293b;
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QFrame#navCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
            }
            QFrame#navCard:hover {
                border-color: #3b82f6;
                background-color: #f0f7ff;
            }
            QPushButton#cardBtn {
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 0;
            }
        """)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 60, 60, 60)
        root.setSpacing(0)

        # Header
        brand = QLabel("ColonScan")
        brand.setStyleSheet("""
            font-size: 36px; font-weight: 800; color: #1e293b; letter-spacing: -1px;
        """)
        brand.setAlignment(Qt.AlignCenter)

        tagline = QLabel("AI-Powered Pathology Analysis Platform")
        tagline.setStyleSheet("""
            font-size: 13px; color: #94a3b8; font-weight: 500; letter-spacing: 2px;
        """)
        tagline.setAlignment(Qt.AlignCenter)

        root.addStretch(1)
        root.addWidget(brand)
        root.addSpacing(8)
        root.addWidget(tagline)
        root.addSpacing(60)

        # Cards row
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(32)
        cards_layout.setAlignment(Qt.AlignCenter)
        cards_layout.addWidget(self._make_card(
            icon="🔬",
            title="Histology Images Processing",
            description="AI-based classification\nPathologique / Non Pathologique",
            slot=self.navigator.go_histology
        ))
        cards_layout.addWidget(self._make_card(
            icon="🧫",
            title="IHC Images Processing",
            description="Tissue contour detection\n& DAB stain extraction",
            slot=self.navigator.go_ihc
        ))
        root.addLayout(cards_layout)

        root.addStretch(2)

        footer = QLabel("v1.0.0  ·  ColonScan")
        footer.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

    def _make_card(self, icon, title, description, slot):
        card = QFrame()
        card.setObjectName("navCard")
        card.setFixedSize(280, 200)
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 32px; background: transparent; border: none;")

        title_lbl = QLabel(title)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet("""
            font-size: 15px; font-weight: 700; color: #1e293b;
            background: transparent; border: none;
        """)

        desc_lbl = QLabel(description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("""
            font-size: 11px; color: #94a3b8;
            background: transparent; border: none;
        """)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()

        # Make entire card clickable
        card.mousePressEvent = lambda event: slot()

        return card