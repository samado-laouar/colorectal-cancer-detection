from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QFrame,
    QSizePolicy
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal
import pandas as pd
import os
from services.predictor import Predictor


class PredictionThread(QThread):
    prediction_complete = Signal(str)
    prediction_error = Signal(str)

    def __init__(self, predictor, image_path):
        super().__init__()
        self.predictor = predictor
        self.image_path = image_path

    def run(self):
        try:
            result = self.predictor.predict(self.image_path)
            self.prediction_complete.emit(result)
        except Exception as e:
            self.prediction_error.emit(str(e))


class StatusBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(60)
        self._set_idle()

    def _set_idle(self):
        self.setText("Awaiting Analysis")
        self.setStyleSheet("""
            QLabel {
                color: #94a3b8; background-color: #f8fafc;
                border: 1px solid #e2e8f0; border-radius: 12px;
                font-size: 15px; font-weight: 600; padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_processing(self, msg="Processing..."):
        self.setText(f"⟳  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #0284c7; background-color: #f0f9ff;
                border: 1px solid #7dd3fc; border-radius: 12px;
                font-size: 15px; font-weight: 600; padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_error(self, msg):
        self.setText(f"✕  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #dc2626; background-color: #fef2f2;
                border: 1px solid #fca5a5; border-radius: 12px;
                font-size: 15px; font-weight: 600; padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_warning(self, msg):
        self.setText(f"⚠  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #b45309; background-color: #fffbeb;
                border: 1px solid #fcd34d; border-radius: 12px;
                font-size: 15px; font-weight: 600; padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_pathologic(self):
        self.setText("⬤  PATHOLOGIQUE\nCancer Detected")
        self.setStyleSheet("""
            QLabel {
                color: #b91c1c; background-color: #fef2f2;
                border: 2px solid #ef4444; border-radius: 12px;
                font-size: 18px; font-weight: 700; padding: 16px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_normal(self):
        self.setText("⬤  NORMAL\nNo Cancer Detected")
        self.setStyleSheet("""
            QLabel {
                color: #15803d; background-color: #f0fdf4;
                border: 2px solid #22c55e; border-radius: 12px;
                font-size: 18px; font-weight: 700; padding: 16px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)


class HistologyWindow(QWidget):
    def __init__(self, navigator):
        super().__init__()
        self.navigator = navigator
        self.selected_image_path = None
        self.prediction_thread = None
        self.predictor = Predictor("model/colon_cancer_model.h5")
        self.apply_style()
        self.setup_ui()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc; color: #1e293b;
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }
            QFrame#sidebar { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
            QFrame#imageFrame {
                background-color: #ffffff; border: 2px dashed #cbd5e1; border-radius: 16px;
            }
            QFrame#imageFrame:hover { border-color: #3b82f6; background-color: #f0f7ff; }
            QPushButton {
                background-color: #eff6ff; color: #2563eb;
                border: 1px solid #bfdbfe; border-radius: 8px;
                padding: 10px 18px; font-size: 13px; font-weight: 600; min-height: 38px;
            }
            QPushButton:hover { background-color: #dbeafe; border-color: #3b82f6; }
            QPushButton:pressed { background-color: #bfdbfe; }
            QPushButton:disabled { background-color: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#importBtn { background-color: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
            QPushButton#importBtn:hover { background-color: #f1f5f9; color: #1e293b; border-color: #94a3b8; }
            QPushButton#predictBtn { background-color: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
            QPushButton#predictBtn:hover { background-color: #dcfce7; border-color: #4ade80; }
            QPushButton#predictBtn:disabled { background-color: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#backBtn {
                background-color: #f8fafc; color: #64748b; border: 1px solid #e2e8f0;
                font-size: 12px; min-height: 32px; padding: 6px 14px;
            }
            QPushButton#backBtn:hover { background-color: #f1f5f9; color: #1e293b; border-color: #94a3b8; }
        """)

    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 32, 24, 24)
        sidebar_layout.setSpacing(0)

        back_btn = QPushButton("← Back to Home")
        back_btn.setObjectName("backBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.navigator.go_home)  # instant switch, no rebuild
        sidebar_layout.addWidget(back_btn)
        sidebar_layout.addSpacing(20)

        brand_label = QLabel("ColonScan")
        brand_label.setStyleSheet("font-size: 22px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px;")
        tagline = QLabel("Histology Analysis")
        tagline.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500; letter-spacing: 2px; margin-bottom: 32px;")
        sidebar_layout.addWidget(brand_label)
        sidebar_layout.addWidget(tagline)

        def make_divider():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: #f1f5f9; margin: 12px 0;")
            return line

        def section_label(text):
            lbl = QLabel(text.upper())
            lbl.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 700; letter-spacing: 2px; margin-top: 20px; margin-bottom: 8px;")
            return lbl

        sidebar_layout.addWidget(section_label("Image"))
        self.import_button = QPushButton("  ⊕  Import Image")
        self.import_button.setObjectName("importBtn")
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.clicked.connect(self.load_image)
        sidebar_layout.addWidget(self.import_button)

        self.file_name_label = QLabel("No file selected")
        self.file_name_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 6px 2px; font-family: 'Consolas', monospace;")
        self.file_name_label.setWordWrap(True)
        sidebar_layout.addWidget(self.file_name_label)

        sidebar_layout.addWidget(make_divider())
        sidebar_layout.addWidget(section_label("Actions"))

        self.predict_button = QPushButton("  ◈  Analyze")
        self.predict_button.setObjectName("predictBtn")
        self.predict_button.setCursor(Qt.PointingHandCursor)
        self.predict_button.clicked.connect(self.run_prediction)
        self.predict_button.setEnabled(False)
        sidebar_layout.addWidget(self.predict_button)

        sidebar_layout.addStretch()
        version_lbl = QLabel("v1.0.0  ·  ColonScan")
        version_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        sidebar_layout.addWidget(version_lbl)
        root.addWidget(sidebar)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        page_title = QLabel("Histology Analysis")
        page_title.setStyleSheet("font-size: 26px; font-weight: 700; color: #1e293b; letter-spacing: -0.5px;")
        page_subtitle = QLabel("Upload a histology image for AI-based cancer classification")
        page_subtitle.setStyleSheet("font-size: 13px; color: #94a3b8; padding-top: 4px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(page_title)
        title_col.addWidget(page_subtitle)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #0284c7; font-size: 13px; font-weight: 600; font-family: 'Consolas', monospace;")
        self.loading_label.setVisible(False)
        header_layout.addWidget(self.loading_label)
        content_layout.addLayout(header_layout)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(20)

        image_panel = QFrame()
        image_panel.setObjectName("imageFrame")
        image_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        image_panel_layout = QVBoxLayout(image_panel)
        image_panel_layout.setContentsMargins(20, 20, 20, 20)
        img_header = QLabel("Image Preview")
        img_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 2px; margin-bottom: 8px;")
        image_panel_layout.addWidget(img_header)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setText(
            "<span style='color:#cbd5e1; font-size:15px; font-family:Segoe UI;'>"
            "⊕ No image selected<br>"
            "<span style='font-size:11px; color:#e2e8f0;'>Click Import Image to begin</span></span>"
        )
        self.image_label.setTextFormat(Qt.RichText)
        image_panel_layout.addWidget(self.image_label)
        panels_layout.addWidget(image_panel, stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        status_header = QLabel("RESULT")
        status_header.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 2px;")
        right_col.addWidget(status_header)
        self.status_badge = StatusBadge()
        right_col.addWidget(self.status_badge)
        right_col.addStretch()
        panels_layout.addLayout(right_col, stretch=2)
        content_layout.addLayout(panels_layout)
        root.addWidget(content_area)

    def set_buttons_enabled(self, enabled: bool):
        self.import_button.setEnabled(enabled)
        self.predict_button.setEnabled(enabled and self.selected_image_path is not None)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Histology Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.selected_image_path = file_path
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setTextFormat(Qt.PlainText)
            self.file_name_label.setText(os.path.basename(file_path))
            self.status_badge.set_warning("Image loaded — click Analyze to classify")
            self.predict_button.setEnabled(True)
            self.loading_label.setVisible(False)

    def _display_image(self, path):
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def run_prediction(self):
        if not self.selected_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return
        self.set_buttons_enabled(False)
        self.loading_label.setText("⟳  Analyzing…")
        self.loading_label.setVisible(True)
        self.status_badge.set_processing("Running AI model…")
        self.prediction_thread = PredictionThread(self.predictor, self.selected_image_path)
        self.prediction_thread.prediction_complete.connect(self.on_prediction_complete)
        self.prediction_thread.prediction_error.connect(self.on_prediction_error)
        self.prediction_thread.start()

    def on_prediction_complete(self, result):
        self.loading_label.setVisible(False)
        if result == "Pathologique":
            self.status_badge.set_pathologic()
        else:
            self.status_badge.set_normal()
        self.save_result(self.selected_image_path, result)
        self.set_buttons_enabled(True)

    def on_prediction_error(self, error_msg):
        self.loading_label.setVisible(False)
        self.status_badge.set_error(f"Prediction failed: {error_msg}")
        self.set_buttons_enabled(True)
        QMessageBox.critical(self, "Prediction Error", f"An error occurred:\n{error_msg}")

    def save_result(self, image_path, result):
        try:
            os.makedirs("data", exist_ok=True)
            file_exists = os.path.isfile("data/results.csv")
            df = pd.DataFrame({"Image": [image_path], "Prediction": [result]})
            df.to_csv("data/results.csv", mode='a', header=not file_exists, index=False, encoding="utf-8")
        except Exception as e:
            print(f"Error saving result: {e}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.selected_image_path and self.image_label.pixmap() and not self.image_label.pixmap().isNull():
            scaled = self.image_label.pixmap().scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)