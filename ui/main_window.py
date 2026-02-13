from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QFileDialog
)
from PySide6.QtGui import QPixmap
import pandas as pd
import os
from services.predictor import Predictor


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Colon Cancer Detection")
        self.setMinimumSize(500, 500)

        self.predictor = Predictor("model/colon_cancer_model.h5")

        self.image_label = QLabel("No image selected")
        self.result_label = QLabel("Result will appear here")

        self.button = QPushButton("Import Image")
        self.button.clicked.connect(self.load_image)

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )

        if file_path:
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap.scaled(300, 300))

            result = self.predictor.predict(file_path)
            self.result_label.setText(f"Prediction: {result}")

            self.save_result(file_path, result)

    def save_result(self, image_path, result):
        file_exists = os.path.isfile("data/results.csv")

        df = pd.DataFrame({
            "Image": [image_path],
            "Prediction": [result]
        })

        df.to_csv("data/results.csv", mode='a', header=not file_exists, index=False)
