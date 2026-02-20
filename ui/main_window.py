from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QFrame, QComboBox,
    QSizePolicy, QGraphicsDropShadowEffect, QScrollArea
)
from PySide6.QtGui import QPixmap, QFont, QMovie, QColor, QPainter, QPainterPath, QLinearGradient, QBrush
from PySide6.QtCore import Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSize, QTimer
import pandas as pd
import os
from services.predictor import Predictor
from services.dab_extractor import DABExtractor


class PredictionThread(QThread):
    """Thread for running predictions in the background"""
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


class DABExtractionThread(QThread):
    """Thread for running DAB extraction in the background"""
    extraction_complete = Signal(object, object, object, dict, object)
    extraction_error = Signal(str)

    def __init__(self, dab_extractor, image_path):
        super().__init__()
        self.dab_extractor = dab_extractor
        self.image_path = image_path

    def run(self):
        try:
            original, circle_mask, result, metrics, contour_overlay = \
                self.dab_extractor.extract_and_analyze(self.image_path)
            self.extraction_complete.emit(original, circle_mask, result, metrics, contour_overlay)
        except Exception as e:
            self.extraction_error.emit(str(e))


class TissuePreviewThread(QThread):
    """Thread for previewing tissue region detection"""
    preview_complete = Signal(object, object)
    preview_error = Signal(str)

    def __init__(self, dab_extractor, image_path):
        super().__init__()
        self.dab_extractor = dab_extractor
        self.image_path = image_path

    def run(self):
        try:
            preview, tissue_info = self.dab_extractor.preview_tissue_detection(self.image_path)
            self.preview_complete.emit(preview, tissue_info)
        except Exception as e:
            self.preview_error.emit(str(e))


class StatusBadge(QLabel):
    """Animated status badge widget"""
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
                color: #94a3b8;
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_processing(self, msg="Processing..."):
        self.setText(f"⟳  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #0284c7;
                background-color: #f0f9ff;
                border: 1px solid #7dd3fc;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_success(self, msg):
        self.setText(f"✓  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #15803d;
                background-color: #f0fdf4;
                border: 1px solid #86efac;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_error(self, msg):
        self.setText(f"✕  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #dc2626;
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_warning(self, msg):
        self.setText(f"⚠  {msg}")
        self.setStyleSheet("""
            QLabel {
                color: #b45309;
                background-color: #fffbeb;
                border: 1px solid #fcd34d;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                padding: 14px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_pathologic(self):
        self.setText("⬤  PATHOLOGIQUE\nCancer Detected")
        self.setStyleSheet("""
            QLabel {
                color: #b91c1c;
                background-color: #fef2f2;
                border: 2px solid #ef4444;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 700;
                padding: 16px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)

    def set_normal(self):
        self.setText("⬤  NORMAL\nNo Cancer Detected")
        self.setStyleSheet("""
            QLabel {
                color: #15803d;
                background-color: #f0fdf4;
                border: 2px solid #22c55e;
                border-radius: 12px;
                font-size: 18px;
                font-weight: 700;
                padding: 16px 20px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
            }
        """)


class MetricCard(QFrame):
    """Card widget to display a single metric"""
    def __init__(self, label, value="—", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.value_label = QLabel(str(value))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("""
            color: #1e293b;
            font-size: 15px;
            font-weight: 700;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
        """)

        self.key_label = QLabel(label)
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("""
            color: #94a3b8;
            font-size: 10px;
            font-weight: 500;
            font-family: 'Segoe UI', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.key_label)
        self.setStyleSheet("""
            QFrame#metricCard {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)

    def update_value(self, value):
        self.value_label.setText(str(value))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ColonScan — AI Cancer Detection")
        self.selected_image_path = None
        self.prediction_thread = None
        self.extraction_thread = None
        self.preview_thread = None
        self.tissue_confirmed = False

        # Initialize services
        self.predictor = Predictor("model/colon_cancer_model.h5")
        self.dab_extractor = DABExtractor(method='multi_threshold')

        self.apply_style()
        self.setup_ui()

        # Start maximized / full-screen
        self.showMaximized()

    def apply_style(self):
        self.setStyleSheet("""
            /* ── Root ── */
            QWidget {
                background-color: #f8fafc;
                color: #1e293b;
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }

            /* ── Sidebar ── */
            QFrame#sidebar {
                background-color: #ffffff;
                border-right: 1px solid #e2e8f0;
            }

            /* ── Image drop zone ── */
            QFrame#imageFrame {
                background-color: #ffffff;
                border: 2px dashed #cbd5e1;
                border-radius: 16px;
            }
            QFrame#imageFrame:hover {
                border-color: #3b82f6;
                background-color: #f0f7ff;
            }

            /* ── Default button ── */
            QPushButton {
                background-color: #eff6ff;
                color: #2563eb;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                min-height: 38px;
            }
            QPushButton:hover {
                background-color: #dbeafe;
                border-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #bfdbfe;
            }
            QPushButton:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }

            /* Import */
            QPushButton#importBtn {
                background-color: #f8fafc;
                color: #475569;
                border: 1px solid #e2e8f0;
            }
            QPushButton#importBtn:hover {
                background-color: #f1f5f9;
                color: #1e293b;
                border-color: #94a3b8;
            }

            /* Analyze / predict */
            QPushButton#predictBtn {
                background-color: #f0fdf4;
                color: #16a34a;
                border: 1px solid #bbf7d0;
            }
            QPushButton#predictBtn:hover {
                background-color: #dcfce7;
                border-color: #4ade80;
            }
            QPushButton#predictBtn:disabled {
                background-color: #f8fafc;
                color: #94a3b8;
                border-color: #e2e8f0;
            }

            /* Preview */
            QPushButton#previewBtn {
                background-color: #faf5ff;
                color: #7c3aed;
                border: 1px solid #e9d5ff;
            }
            QPushButton#previewBtn:hover {
                background-color: #f3e8ff;
                border-color: #a78bfa;
            }
            QPushButton#previewBtn:disabled {
                background-color: #f8fafc;
                color: #94a3b8;
                border-color: #e2e8f0;
            }

            /* Extract */
            QPushButton#extractBtn {
                background-color: #fff7ed;
                color: #c2410c;
                border: 1px solid #fed7aa;
            }
            QPushButton#extractBtn:hover {
                background-color: #ffedd5;
                border-color: #fb923c;
            }
            QPushButton#extractBtn:disabled {
                background-color: #f8fafc;
                color: #94a3b8;
                border-color: #e2e8f0;
            }

            /* ── Combo box ── */
            QComboBox {
                background-color: #ffffff;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 7px 12px;
                font-size: 13px;
                min-height: 36px;
                min-width: 200px;
            }
            QComboBox:hover {
                border-color: #3b82f6;
                color: #1e293b;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #94a3b8;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #e2e8f0;
                selection-background-color: #dbeafe;
                selection-color: #1e293b;
                outline: none;
            }

            /* ── Scrollbar ── */
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT SIDEBAR ──────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(24, 32, 24, 24)
        sidebar_layout.setSpacing(0)

        # Logo / brand
        brand_label = QLabel("ColonScan")
        brand_label.setStyleSheet("""
            font-size: 22px;
            font-weight: 800;
            color: #1e293b;
            letter-spacing: -0.5px;
            font-family: 'Segoe UI', sans-serif;
        """)
        tagline = QLabel("AI-Powered Pathology")
        tagline.setStyleSheet("""
            font-size: 11px;
            color: #94a3b8;
            font-weight: 500;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 32px;
        """)
        sidebar_layout.addWidget(brand_label)
        sidebar_layout.addWidget(tagline)
        sidebar_layout.addSpacing(28)

        # Divider
        def make_divider():
            d = QFrame()
            d.setFrameShape(QFrame.HLine)
            d.setStyleSheet("border: none; border-top: 1px solid #f1f5f9; margin: 8px 0;")
            return d

        # Section label helper
        def section_label(text):
            lbl = QLabel(text.upper())
            lbl.setStyleSheet("""
                font-size: 10px;
                color: #94a3b8;
                font-weight: 700;
                letter-spacing: 2px;
                margin-top: 20px;
                margin-bottom: 8px;
            """)
            return lbl

        # ── Import button ─────────────────────────
        sidebar_layout.addWidget(section_label("Image"))
        self.import_button = QPushButton("  ⊕  Import Image")
        self.import_button.setObjectName("importBtn")
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.clicked.connect(self.load_image)
        sidebar_layout.addWidget(self.import_button)

        # File name display
        self.file_name_label = QLabel("No file selected")
        self.file_name_label.setStyleSheet("""
            color: #64748b;
            font-size: 11px;
            padding: 6px 2px;
            font-family: 'Consolas', monospace;
        """)
        self.file_name_label.setWordWrap(True)
        sidebar_layout.addWidget(self.file_name_label)

        sidebar_layout.addWidget(make_divider())

        # ── DAB Method ────────────────────────────
        sidebar_layout.addWidget(section_label("DAB Extraction Method"))
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Multi-Threshold RGB",
            "Color Deconvolution",
            "Lab Color Space"
        ])
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.method_combo.setCursor(Qt.PointingHandCursor)
        sidebar_layout.addWidget(self.method_combo)

        sidebar_layout.addWidget(make_divider())

        # ── Action buttons ────────────────────────
        sidebar_layout.addWidget(section_label("Actions"))

        self.predict_button = QPushButton("  ◈  Analyze")
        self.predict_button.setObjectName("predictBtn")
        self.predict_button.setCursor(Qt.PointingHandCursor)
        self.predict_button.clicked.connect(self.run_prediction)
        self.predict_button.setEnabled(False)
        sidebar_layout.addWidget(self.predict_button)
        sidebar_layout.addSpacing(6)

        self.preview_button = QPushButton("  ◉  Preview Region")
        self.preview_button.setObjectName("previewBtn")
        self.preview_button.setCursor(Qt.PointingHandCursor)
        self.preview_button.clicked.connect(self.preview_tissue)
        self.preview_button.setEnabled(False)
        sidebar_layout.addWidget(self.preview_button)
        sidebar_layout.addSpacing(6)

        self.extract_button = QPushButton("  ⬡  Extract DAB")
        self.extract_button.setObjectName("extractBtn")
        self.extract_button.setCursor(Qt.PointingHandCursor)
        self.extract_button.clicked.connect(self.extract_dab)
        self.extract_button.setEnabled(False)
        sidebar_layout.addWidget(self.extract_button)

        sidebar_layout.addStretch()

        # Footer
        version_lbl = QLabel("v1.0.0  ·  ColonScan")
        version_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        sidebar_layout.addWidget(version_lbl)

        root.addWidget(sidebar)

        # ── MAIN CONTENT AREA ─────────────────────────────────────────
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        # ── Page header ───────────────────────────
        header_layout = QHBoxLayout()
        page_title = QLabel("Pathology Analysis")
        page_title.setStyleSheet("""
            font-size: 26px;
            font-weight: 700;
            color: #1e293b;
            letter-spacing: -0.5px;
        """)
        page_subtitle = QLabel("Upload tissue image for AI analysis")
        page_subtitle.setStyleSheet("font-size: 13px; color: #94a3b8; padding-top: 4px;")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(page_title)
        title_col.addWidget(page_subtitle)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # Loading indicator (in header)
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("""
            color: #0284c7;
            font-size: 13px;
            font-weight: 600;
            font-family: 'Consolas', monospace;
        """)
        self.loading_label.setVisible(False)
        header_layout.addWidget(self.loading_label)

        content_layout.addLayout(header_layout)

        # ── Main panels row ───────────────────────
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(20)

        # ── Image panel ───────────────────────────
        image_panel = QFrame()
        image_panel.setObjectName("imageFrame")
        image_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        image_panel_layout = QVBoxLayout(image_panel)
        image_panel_layout.setContentsMargins(20, 20, 20, 20)

        img_header = QLabel("Image Preview")
        img_header.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #94a3b8;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 8px;
        """)
        image_panel_layout.addWidget(img_header)

        self.image_label = QLabel()
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setMinimumSize(400, 400)

        # Placeholder text
        self.image_label.setText(
            "<span style='color:#cbd5e1; font-size:15px; font-family:Segoe UI;'>"
            "⊕ No image selected<br>"
            "<span style='font-size:11px; color:#e2e8f0;'>Click Import Image to begin</span>"
            "</span>"
        )
        self.image_label.setTextFormat(Qt.RichText)
        image_panel_layout.addWidget(self.image_label)

        panels_layout.addWidget(image_panel, stretch=3)

        # ── Right column: status + metrics ────────
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Status badge
        status_header = QLabel("RESULT")
        status_header.setStyleSheet("""
            font-size: 10px; font-weight: 700; color: #94a3b8;
            letter-spacing: 2px;
        """)
        right_col.addWidget(status_header)

        self.status_badge = StatusBadge()
        right_col.addWidget(self.status_badge)

        # Metrics grid
        metrics_header = QLabel("METRICS")
        metrics_header.setStyleSheet("""
            font-size: 10px; font-weight: 700; color: #94a3b8;
            letter-spacing: 2px; margin-top: 8px;
        """)
        right_col.addWidget(metrics_header)

        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("background: transparent;")
        self.metrics_grid = QVBoxLayout(metrics_frame)
        self.metrics_grid.setSpacing(8)

        # Placeholder metric cards
        self.metric_cards = {}
        default_metrics = {
            "DAB Coverage": "—",
            "Tissue Area": "—",
            "DAB Area": "—",
            "Mean Intensity": "—",
        }
        for k, v in default_metrics.items():
            card = MetricCard(k, v)
            self.metric_cards[k] = card
            self.metrics_grid.addWidget(card)

        right_col.addWidget(metrics_frame)
        right_col.addStretch()

        panels_layout.addLayout(right_col, stretch=2)
        content_layout.addLayout(panels_layout)

        root.addWidget(content_area)

    # ── Helpers ───────────────────────────────────────────────────────

    def set_buttons_enabled(self, enabled: bool):
        self.import_button.setEnabled(enabled)
        self.predict_button.setEnabled(enabled and self.selected_image_path is not None)
        self.preview_button.setEnabled(enabled and self.selected_image_path is not None)
        # extract only if tissue confirmed
        self.extract_button.setEnabled(enabled and self.tissue_confirmed)

    def on_method_changed(self, index):
        method_map = {0: 'multi_threshold', 1: 'color_deconv', 2: 'lab'}
        self.dab_extractor.method = method_map[index]

    # ── Image Loading ─────────────────────────────────────────────────

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Medical Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.selected_image_path = file_path
            self.tissue_confirmed = False

            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
            self.image_label.setTextFormat(Qt.PlainText)

            # Update file name label
            self.file_name_label.setText(os.path.basename(file_path))

            self.status_badge.set_warning("Image loaded — preview region to proceed")
            self.predict_button.setEnabled(True)
            self.preview_button.setEnabled(True)
            self.extract_button.setEnabled(False)
            self.loading_label.setVisible(False)

    def _display_image(self, path):
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    # ── Prediction ────────────────────────────────────────────────────

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

    # ── Tissue Preview ────────────────────────────────────────────────

    def preview_tissue(self):
        if not self.selected_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        self.set_buttons_enabled(False)
        self.loading_label.setText("⟳  Detecting tissue region…")
        self.loading_label.setVisible(True)
        self.status_badge.set_processing("Detecting tissue region…")

        self.preview_thread = TissuePreviewThread(self.dab_extractor, self.selected_image_path)
        self.preview_thread.preview_complete.connect(self.on_preview_complete)
        self.preview_thread.preview_error.connect(self.on_preview_error)
        self.preview_thread.start()

    def on_preview_complete(self, preview, tissue_info):
        self.loading_label.setVisible(False)

        if preview is None or tissue_info is None:
            self.status_badge.set_error("Tissue region not detected")
            self.set_buttons_enabled(True)
            self.extract_button.setEnabled(False)
            return

        import cv2
        os.makedirs("data", exist_ok=True)
        preview_path = "data/tissue_preview.png"
        cv2.imwrite(preview_path, cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))
        self._display_image(preview_path)

        area = tissue_info['area']
        x, y, w, h = tissue_info['bbox']

        self.status_badge.set_success(
            f"Tissue region detected\nArea: {int(area):,} px  |  {w}×{h}"
        )

        # Update metric cards with tissue info
        self.metric_cards["Tissue Area"].update_value(f"{int(area):,} px")

        self.tissue_confirmed = True
        self.set_buttons_enabled(True)

    def on_preview_error(self, error_msg):
        self.loading_label.setVisible(False)
        self.status_badge.set_error(f"Preview failed")
        self.set_buttons_enabled(True)
        self.extract_button.setEnabled(False)
        QMessageBox.critical(self, "Preview Error", f"An error occurred:\n{error_msg}")

    # ── DAB Extraction ────────────────────────────────────────────────

    def extract_dab(self):
        if not self.selected_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        if not self.tissue_confirmed:
            reply = QMessageBox.question(
                self, "Region Not Previewed",
                "You haven't previewed the tissue region yet.\nProceed anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.set_buttons_enabled(False)
        method_names = {
            'multi_threshold': 'Multi-Threshold RGB',
            'color_deconv': 'Color Deconvolution',
            'lab': 'Lab Color Space'
        }
        method_str = method_names.get(self.dab_extractor.method, 'Unknown')
        self.loading_label.setText(f"⟳  Extracting DAB ({method_str})…")
        self.loading_label.setVisible(True)
        self.status_badge.set_processing(f"Running DAB extraction…")

        self.extraction_thread = DABExtractionThread(self.dab_extractor, self.selected_image_path)
        self.extraction_thread.extraction_complete.connect(self.on_extraction_complete)
        self.extraction_thread.extraction_error.connect(self.on_extraction_error)
        self.extraction_thread.start()

    def on_extraction_complete(self, original, circle_mask, result, metrics, contour_overlay):
        self.loading_label.setVisible(False)

        if "Error" in metrics:
            self.status_badge.set_error(metrics["Error"])
            self.set_buttons_enabled(True)
            return

        import cv2
        os.makedirs("data", exist_ok=True)

        overlay_path = "data/dab_contour_overlay.png"
        cv2.imwrite(overlay_path, cv2.cvtColor(contour_overlay, cv2.COLOR_RGB2BGR))
        output_path = "data/dab_result.png"
        cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        self._display_image(overlay_path)

        self.status_badge.set_success("DAB Extraction Complete")

        # Populate metric cards
        label_map = {
            "DAB Coverage": "DAB Coverage",
            "Tissue Area": "Tissue Area",
            "DAB Area": "DAB Area",
            "Mean Intensity": "Mean Intensity",
        }
        for key in list(self.metric_cards.keys()):
            # Try to find a matching key in metrics (case-insensitive)
            for mk, mv in metrics.items():
                if key.lower() in mk.lower() or mk.lower() in key.lower():
                    self.metric_cards[key].update_value(str(mv))
                    break

        self.set_buttons_enabled(True)

    def on_extraction_error(self, error_msg):
        self.loading_label.setVisible(False)
        self.status_badge.set_error("Extraction failed")
        self.set_buttons_enabled(True)
        QMessageBox.critical(self, "Extraction Error", f"An error occurred:\n{error_msg}")

    # ── Persistence ───────────────────────────────────────────────────

    def save_result(self, image_path, result):
        try:
            os.makedirs("data", exist_ok=True)
            file_exists = os.path.isfile("data/results.csv")
            df = pd.DataFrame({"Image": [image_path], "Prediction": [result]})
            df.to_csv("data/results.csv", mode='a', header=not file_exists,
                      index=False, encoding="utf-8")
        except Exception as e:
            print(f"Error saving result: {e}")

    def resizeEvent(self, event):
        """Re-scale displayed image when window is resized."""
        super().resizeEvent(event)
        if self.selected_image_path and not self.image_label.pixmap() is None:
            if not self.image_label.pixmap().isNull():
                scaled = self.image_label.pixmap().scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)