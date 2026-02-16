from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QFrame
)
from PySide6.QtGui import QPixmap, QFont, QMovie
from PySide6.QtCore import Qt, QThread, Signal
import pandas as pd
import os
from services.predictor import Predictor


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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Colon Cancer Detection")
        self.setMinimumSize(600, 500)
        self.selected_image_path = None
        self.prediction_thread = None

        # Initialize predictor
        self.predictor = Predictor("model/colon_cancer_model.h5")

        # Apply modern stylesheet
        self.apply_modern_style()

        # UI Elements
        self.setup_ui()

    def apply_modern_style(self):
        """Apply modern, clean stylesheet to the application"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
            
            QLabel#subtitle {
                font-size: 14px;
                color: #7f8c8d;
                padding-bottom: 5px;
            }
            
            QFrame#imageFrame {
                background-color: white;
                border: 2px dashed #bdc3c7;
                border-radius: 12px;
            }
            
            QLabel#imageLabel {
                background-color: white;
                border-radius: 8px;
            }
            
            QLabel#resultLabel {
                font-size: 18px;
                font-weight: 600;
                padding: 20px;
                border-radius: 8px;
                background-color: white;
                border: 1px solid #e0e0e0;
            }
            
            QLabel#loadingLabel {
                font-size: 16px;
                color: #3498db;
                padding: 15px;
            }
            
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 15px;
                font-weight: 600;
                min-height: 25px;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #21618c;
            }
            
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #ecf0f1;
            }
            
            QPushButton#predictButton {
                background-color: #27ae60;
            }
            
            QPushButton#predictButton:hover {
                background-color: #229954;
            }
            
            QPushButton#predictButton:pressed {
                background-color: #1e8449;
            }
        """)

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("Colon Cancer Detection")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Upload an image for AI-powered analysis")
        subtitle_label.setObjectName("subtitle")
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Image Frame
        image_frame = QFrame()
        image_frame.setObjectName("imageFrame")
        image_frame_layout = QVBoxLayout()
        
        self.image_label = QLabel("No image selected")
        self.image_label.setObjectName("imageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setStyleSheet("color: #95a5a6; font-size: 16px;")
        
        image_frame_layout.addWidget(self.image_label)
        image_frame.setLayout(image_frame_layout)
        main_layout.addWidget(image_frame)

        # Loading Label (hidden by default)
        self.loading_label = QLabel("Analyzing image, please wait...")
        self.loading_label.setObjectName("loadingLabel")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setVisible(False)
        main_layout.addWidget(self.loading_label)

        # Result Label
        self.result_label = QLabel("Results will appear here")
        self.result_label.setObjectName("resultLabel")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: #7f8c8d;")
        main_layout.addWidget(self.result_label)

        # Buttons Layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.import_button = QPushButton("Import Image")
        self.import_button.clicked.connect(self.load_image)
        buttons_layout.addWidget(self.import_button)

        self.predict_button = QPushButton("Analyze")
        self.predict_button.setObjectName("predictButton")
        self.predict_button.clicked.connect(self.run_prediction)
        self.predict_button.setEnabled(False)
        buttons_layout.addWidget(self.predict_button)

        main_layout.addLayout(buttons_layout)

        # Add stretch to push everything up
        main_layout.addStretch()

        self.setLayout(main_layout)

    def load_image(self):
        """Load image from file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Medical Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            self.selected_image_path = file_path

            # Display image
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(
                pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.image_label.setStyleSheet("color: #2c3e50;")

            # Update UI
            self.result_label.setText("Image loaded. Click Analyze to begin.")
            self.result_label.setStyleSheet("color: #3498db; background-color: #ebf5fb; border: 1px solid #3498db;")
            self.predict_button.setEnabled(True)
            self.loading_label.setVisible(False)

    def run_prediction(self):
        """Run prediction in background thread"""
        if not self.selected_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        # Disable buttons during prediction
        self.import_button.setEnabled(False)
        self.predict_button.setEnabled(False)
        
        # Show loading indicator
        self.loading_label.setVisible(True)
        self.result_label.setText("Processing...")
        self.result_label.setStyleSheet("color: #3498db; background-color: #ebf5fb; border: 1px solid #3498db;")

        # Create and start prediction thread
        self.prediction_thread = PredictionThread(self.predictor, self.selected_image_path)
        self.prediction_thread.prediction_complete.connect(self.on_prediction_complete)
        self.prediction_thread.prediction_error.connect(self.on_prediction_error)
        self.prediction_thread.start()

    def on_prediction_complete(self, result):
        """Handle successful prediction"""
        # Hide loading indicator
        self.loading_label.setVisible(False)
        
        # Update result display with modern styling
        if result == "Pathologique":
            self.result_label.setText(f"Result: {result}")
            self.result_label.setStyleSheet("""
                color: #c0392b;
                background-color: #fadbd8;
                border: 2px solid #e74c3c;
                font-size: 20px;
                font-weight: bold;
            """)
        else:
            self.result_label.setText(f"Result: {result}")
            self.result_label.setStyleSheet("""
                color: #27ae60;
                background-color: #d5f4e6;
                border: 2px solid #27ae60;
                font-size: 20px;
                font-weight: bold;
            """)

        # Save result
        self.save_result(self.selected_image_path, result)

        # Re-enable buttons
        self.import_button.setEnabled(True)
        self.predict_button.setEnabled(True)

    def on_prediction_error(self, error_msg):
        """Handle prediction error"""
        self.loading_label.setVisible(False)
        self.result_label.setText(f"Error: {error_msg}")
        self.result_label.setStyleSheet("""
            color: #c0392b;
            background-color: #fadbd8;
            border: 2px solid #e74c3c;
        """)
        
        # Re-enable buttons
        self.import_button.setEnabled(True)
        self.predict_button.setEnabled(True)
        
        QMessageBox.critical(self, "Prediction Error", f"An error occurred: {error_msg}")

    def save_result(self, image_path, result):
        """Save prediction result to CSV"""
        try:
            os.makedirs("data", exist_ok=True)
            file_exists = os.path.isfile("data/results.csv")

            df = pd.DataFrame({
                "Image": [image_path],
                "Prediction": [result]
            })

            df.to_csv(
                "data/results.csv",
                mode='a',
                header=not file_exists,
                index=False,
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Error saving result: {e}")