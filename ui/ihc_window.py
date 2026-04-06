from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QFrame,
    QComboBox, QSizePolicy, QButtonGroup, QRadioButton
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QThread, Signal
import os
from services.dab_extractor import DABExtractor


class DABExtractionThread(QThread):
    extraction_complete = Signal(object, object, object, dict, object)
    extraction_error = Signal(str)

    def __init__(self, dab_extractor, image_path, whole_image=False):
        super().__init__()
        self.dab_extractor = dab_extractor
        self.image_path = image_path
        self.whole_image = whole_image

    def run(self):
        try:
            if self.whole_image:
                result = self.dab_extractor.extract_and_analyze_whole(self.image_path)
            else:
                result = self.dab_extractor.extract_and_analyze(self.image_path)
            self.extraction_complete.emit(*result)
        except Exception as e:
            self.extraction_error.emit(str(e))


class TissuePreviewThread(QThread):
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(60)
        self._set_idle()

    def _set_idle(self):
        self.setText("Awaiting Analysis")
        self.setStyleSheet("QLabel { color: #94a3b8; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; font-size: 15px; font-weight: 600; padding: 14px 20px; font-family: 'JetBrains Mono', 'Consolas', monospace; }")

    def set_processing(self, msg="Processing..."):
        self.setText(f"⟳  {msg}")
        self.setStyleSheet("QLabel { color: #0284c7; background-color: #f0f9ff; border: 1px solid #7dd3fc; border-radius: 12px; font-size: 15px; font-weight: 600; padding: 14px 20px; font-family: 'JetBrains Mono', 'Consolas', monospace; }")

    def set_success(self, msg):
        self.setText(f"✓  {msg}")
        self.setStyleSheet("QLabel { color: #15803d; background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 12px; font-size: 15px; font-weight: 600; padding: 14px 20px; font-family: 'JetBrains Mono', 'Consolas', monospace; }")

    def set_error(self, msg):
        self.setText(f"✕  {msg}")
        self.setStyleSheet("QLabel { color: #dc2626; background-color: #fef2f2; border: 1px solid #fca5a5; border-radius: 12px; font-size: 15px; font-weight: 600; padding: 14px 20px; font-family: 'JetBrains Mono', 'Consolas', monospace; }")

    def set_warning(self, msg):
        self.setText(f"⚠  {msg}")
        self.setStyleSheet("QLabel { color: #b45309; background-color: #fffbeb; border: 1px solid #fcd34d; border-radius: 12px; font-size: 15px; font-weight: 600; padding: 14px 20px; font-family: 'JetBrains Mono', 'Consolas', monospace; }")


class MetricCard(QFrame):
    def __init__(self, label, value="—", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        self.value_label = QLabel(str(value))
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: #1e293b; font-size: 15px; font-weight: 700; font-family: 'JetBrains Mono', 'Consolas', monospace;")
        self.key_label = QLabel(label)
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: 500; font-family: 'Segoe UI', sans-serif; letter-spacing: 1px;")
        layout.addWidget(self.value_label)
        layout.addWidget(self.key_label)
        self.setStyleSheet("QFrame#metricCard { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; }")

    def update_value(self, value):
        self.value_label.setText(str(value))


class IHCWindow(QWidget):
    MODE_CONTOUR = "contour"
    MODE_WHOLE   = "whole"

    def __init__(self, navigator):
        super().__init__()
        self.navigator = navigator
        self.selected_image_path = None
        self.extraction_thread = None
        self.preview_thread = None
        self.tissue_confirmed = False
        self.current_mode = self.MODE_CONTOUR
        self.dab_extractor = DABExtractor(method='multi_threshold')
        self.apply_style()
        self.setup_ui()

    def apply_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #f8fafc; color: #1e293b; font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; }
            QFrame#sidebar { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
            QFrame#imageFrame { background-color: #ffffff; border: 2px dashed #cbd5e1; border-radius: 16px; }
            QFrame#imageFrame:hover { border-color: #3b82f6; background-color: #f0f7ff; }
            QFrame#modeCard { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; }
            QRadioButton { font-size: 13px; font-weight: 600; color: #1e293b; spacing: 8px; }
            QRadioButton::indicator { width: 16px; height: 16px; border-radius: 8px; border: 2px solid #cbd5e1; background-color: #ffffff; }
            QRadioButton::indicator:checked { border-color: #3b82f6; background-color: #3b82f6; }
            QPushButton { background-color: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; border-radius: 8px; padding: 10px 18px; font-size: 13px; font-weight: 600; min-height: 38px; }
            QPushButton:hover { background-color: #dbeafe; border-color: #3b82f6; }
            QPushButton:pressed { background-color: #bfdbfe; }
            QPushButton:disabled { background-color: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#importBtn { background-color: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
            QPushButton#importBtn:hover { background-color: #f1f5f9; color: #1e293b; border-color: #94a3b8; }
            QPushButton#previewBtn { background-color: #faf5ff; color: #7c3aed; border: 1px solid #e9d5ff; }
            QPushButton#previewBtn:hover { background-color: #f3e8ff; border-color: #a78bfa; }
            QPushButton#previewBtn:disabled { background-color: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#extractBtn { background-color: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
            QPushButton#extractBtn:hover { background-color: #ffedd5; border-color: #fb923c; }
            QPushButton#extractBtn:disabled { background-color: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }
            QPushButton#backBtn { background-color: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; font-size: 12px; min-height: 32px; padding: 6px 14px; }
            QPushButton#backBtn:hover { background-color: #f1f5f9; color: #1e293b; border-color: #94a3b8; }
            QComboBox { background-color: #ffffff; color: #334155; border: 1px solid #e2e8f0; border-radius: 8px; padding: 7px 12px; font-size: 13px; min-height: 36px; min-width: 200px; }
            QComboBox:hover { border-color: #3b82f6; color: #1e293b; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow { border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid #94a3b8; width: 0; height: 0; }
            QComboBox QAbstractItemView { background-color: #ffffff; color: #1e293b; border: 1px solid #e2e8f0; selection-background-color: #dbeafe; selection-color: #1e293b; outline: none; }
        """)

    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # SIDEBAR
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(24, 32, 24, 24)
        sl.setSpacing(0)

        back_btn = QPushButton("← Back to Home")
        back_btn.setObjectName("backBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.navigator.go_home)
        sl.addWidget(back_btn)
        sl.addSpacing(20)

        brand = QLabel("ColonScan")
        brand.setStyleSheet("font-size: 22px; font-weight: 800; color: #1e293b; letter-spacing: -0.5px;")
        tagline = QLabel("IHC Analysis")
        tagline.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500; letter-spacing: 2px; margin-bottom: 32px;")
        sl.addWidget(brand)
        sl.addWidget(tagline)

        def divider():
            ln = QFrame()
            ln.setFrameShape(QFrame.HLine)
            ln.setStyleSheet("color: #f1f5f9; margin: 12px 0;")
            return ln

        def section_lbl(text):
            lb = QLabel(text.upper())
            lb.setStyleSheet("font-size: 10px; color: #94a3b8; font-weight: 700; letter-spacing: 2px; margin-top: 20px; margin-bottom: 8px;")
            return lb

        # Image
        sl.addWidget(section_lbl("Image"))
        self.import_button = QPushButton("  ⊕  Import Image")
        self.import_button.setObjectName("importBtn")
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.clicked.connect(self.load_image)
        sl.addWidget(self.import_button)

        self.file_name_label = QLabel("No file selected")
        self.file_name_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 6px 2px; font-family: 'Consolas', monospace;")
        self.file_name_label.setWordWrap(True)
        sl.addWidget(self.file_name_label)

        sl.addWidget(divider())

        # Processing Mode
        sl.addWidget(section_lbl("Processing Mode"))
        mode_card = QFrame()
        mode_card.setObjectName("modeCard")
        ml = QVBoxLayout(mode_card)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(6)

        self.radio_contour = QRadioButton("Contour Detection")
        self.radio_contour.setChecked(True)
        contour_hint = QLabel("Preview tissue region first,\nthen extract DAB within it")
        contour_hint.setStyleSheet("color: #94a3b8; font-size: 10px; padding-left: 24px;")

        self.radio_whole = QRadioButton("Whole Image")
        whole_hint = QLabel("Extract DAB directly on\nthe entire image")
        whole_hint.setStyleSheet("color: #94a3b8; font-size: 10px; padding-left: 24px;")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_contour)
        self.mode_group.addButton(self.radio_whole)
        self.mode_group.buttonClicked.connect(self.on_mode_changed)

        ml.addWidget(self.radio_contour)
        ml.addWidget(contour_hint)
        ml.addSpacing(6)
        ml.addWidget(self.radio_whole)
        ml.addWidget(whole_hint)
        sl.addWidget(mode_card)

        sl.addWidget(divider())


        # Actions
        sl.addWidget(section_lbl("Actions"))

        self.preview_button = QPushButton("  ◉  Preview Region")
        self.preview_button.setObjectName("previewBtn")
        self.preview_button.setCursor(Qt.PointingHandCursor)
        self.preview_button.clicked.connect(self.preview_tissue)
        self.preview_button.setEnabled(False)
        sl.addWidget(self.preview_button)
        sl.addSpacing(6)

        self.extract_button = QPushButton("  ⬡  Extract DAB")
        self.extract_button.setObjectName("extractBtn")
        self.extract_button.setCursor(Qt.PointingHandCursor)
        self.extract_button.clicked.connect(self.extract_dab)
        self.extract_button.setEnabled(False)
        sl.addWidget(self.extract_button)

        sl.addStretch()
        version_lbl = QLabel("v1.0.0  ·  ColonScan")
        version_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        sl.addWidget(version_lbl)
        root.addWidget(sidebar)

        # CONTENT
        content_area = QWidget()
        cl = QVBoxLayout(content_area)
        cl.setContentsMargins(32, 32, 32, 32)
        cl.setSpacing(20)

        header_layout = QHBoxLayout()
        page_title = QLabel("IHC Image Processing")
        page_title.setStyleSheet("font-size: 26px; font-weight: 700; color: #1e293b; letter-spacing: -0.5px;")
        self.page_subtitle = QLabel("Contour detection mode — preview tissue region, then extract DAB")
        self.page_subtitle.setStyleSheet("font-size: 13px; color: #94a3b8; padding-top: 4px;")
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.addWidget(page_title)
        title_col.addWidget(self.page_subtitle)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet("color: #0284c7; font-size: 13px; font-weight: 600; font-family: 'Consolas', monospace;")
        self.loading_label.setVisible(False)
        header_layout.addWidget(self.loading_label)
        cl.addLayout(header_layout)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(20)

        image_panel = QFrame()
        image_panel.setObjectName("imageFrame")
        image_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        ipl = QVBoxLayout(image_panel)
        ipl.setContentsMargins(20, 20, 20, 20)
        img_header = QLabel("Image Preview")
        img_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 2px; margin-bottom: 8px;")
        ipl.addWidget(img_header)
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
        ipl.addWidget(self.image_label)
        panels_layout.addWidget(image_panel, stretch=3)

        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        status_header = QLabel("RESULT")
        status_header.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 2px;")
        right_col.addWidget(status_header)
        self.status_badge = StatusBadge()
        right_col.addWidget(self.status_badge)

        metrics_header = QLabel("METRICS")
        metrics_header.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8; letter-spacing: 2px; margin-top: 8px;")
        right_col.addWidget(metrics_header)

        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("background: transparent;")
        metrics_grid = QVBoxLayout(metrics_frame)
        metrics_grid.setSpacing(8)
        self.metric_cards = {}
        for k in ["DAB Coverage", "Tissue Area", "DAB Regions", "Mean Intensity"]:
            card = MetricCard(k, "—")
            self.metric_cards[k] = card
            metrics_grid.addWidget(card)
        right_col.addWidget(metrics_frame)
        right_col.addStretch()

        panels_layout.addLayout(right_col, stretch=2)
        cl.addLayout(panels_layout)
        root.addWidget(content_area)

    # Mode logic
    def on_mode_changed(self, btn):
        if btn == self.radio_contour:
            self.current_mode = self.MODE_CONTOUR
            self.page_subtitle.setText("Contour detection mode — preview tissue region, then extract DAB")
            self.preview_button.setEnabled(self.selected_image_path is not None)
            self.extract_button.setEnabled(self.tissue_confirmed)
        else:
            self.current_mode = self.MODE_WHOLE
            self.page_subtitle.setText("Whole image mode — DAB extraction runs on the entire image")
            self.preview_button.setEnabled(False)
            self.extract_button.setEnabled(self.selected_image_path is not None)

    def on_method_changed(self, index):
        self.dab_extractor.method = {0: 'multi_threshold', 1: 'color_deconv', 2: 'lab'}[index]

    def set_buttons_enabled(self, enabled):
        self.import_button.setEnabled(enabled)
        if self.current_mode == self.MODE_CONTOUR:
            self.preview_button.setEnabled(enabled and self.selected_image_path is not None)
            self.extract_button.setEnabled(enabled and self.tissue_confirmed)
        else:
            self.preview_button.setEnabled(False)
            self.extract_button.setEnabled(enabled and self.selected_image_path is not None)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select IHC Image", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.selected_image_path = file_path
            self.tissue_confirmed = False
            pixmap = QPixmap(file_path)
            scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setTextFormat(Qt.PlainText)
            self.file_name_label.setText(os.path.basename(file_path))
            self.loading_label.setVisible(False)
            if self.current_mode == self.MODE_CONTOUR:
                self.status_badge.set_warning("Image loaded — preview region to proceed")
                self.preview_button.setEnabled(True)
                self.extract_button.setEnabled(False)
            else:
                self.status_badge.set_warning("Image loaded — click Extract DAB to process")
                self.preview_button.setEnabled(False)
                self.extract_button.setEnabled(True)

    def _display_image(self, path):
        pixmap = QPixmap(path)
        scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def _reset_metrics(self):
        for card in self.metric_cards.values():
            card.update_value("—")

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
        self.status_badge.set_success(f"Tissue detected\nArea: {int(area):,} px  |  {w}x{h}")
        self.metric_cards["Tissue Area"].update_value(f"{int(area):,} px")
        self.tissue_confirmed = True
        self.set_buttons_enabled(True)

    def on_preview_error(self, error_msg):
        self.loading_label.setVisible(False)
        self.status_badge.set_error("Preview failed")
        self.set_buttons_enabled(True)
        self.extract_button.setEnabled(False)
        QMessageBox.critical(self, "Preview Error", f"An error occurred:\n{error_msg}")

    def extract_dab(self):
        if not self.selected_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return
        if self.current_mode == self.MODE_CONTOUR and not self.tissue_confirmed:
            reply = QMessageBox.question(
                self, "Region Not Previewed",
                "You haven't previewed the tissue region yet.\nProceed anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        self.set_buttons_enabled(False)
        method_names = {'multi_threshold': 'Multi-Threshold RGB', 'color_deconv': 'Color Deconvolution', 'lab': 'Lab Color Space'}
        method_str = method_names.get(self.dab_extractor.method, 'Unknown')
        mode_str = "whole image" if self.current_mode == self.MODE_WHOLE else "tissue region"
        self.loading_label.setText(f"⟳  Extracting DAB — {mode_str} ({method_str})…")
        self.loading_label.setVisible(True)
        self.status_badge.set_processing("Running DAB extraction…")
        self._reset_metrics()

        whole = (self.current_mode == self.MODE_WHOLE)
        self.extraction_thread = DABExtractionThread(self.dab_extractor, self.selected_image_path, whole_image=whole)
        self.extraction_thread.extraction_complete.connect(self.on_extraction_complete)
        self.extraction_thread.extraction_error.connect(self.on_extraction_error)
        self.extraction_thread.start()

    def on_extraction_complete(self, original, tissue_mask, result, metrics, contour_overlay):
        self.loading_label.setVisible(False)
        if "Error" in metrics:
            self.status_badge.set_error(metrics["Error"])
            self.set_buttons_enabled(True)
            return
        import cv2
        os.makedirs("data", exist_ok=True)
        overlay_path = "data/dab_contour_overlay.png"
        cv2.imwrite(overlay_path, cv2.cvtColor(contour_overlay, cv2.COLOR_RGB2BGR))
        cv2.imwrite("data/dab_result.png", cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
        self._display_image(overlay_path)
        self.status_badge.set_success("DAB Extraction Complete")
        for key in list(self.metric_cards.keys()):
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.selected_image_path and self.image_label.pixmap() and not self.image_label.pixmap().isNull():
            scaled = self.image_label.pixmap().scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)