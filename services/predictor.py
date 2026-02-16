import os
import sys

# Suppress TensorFlow output for windowed mode
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TF warnings
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

import numpy as np
from tensorflow.keras.models import load_model
from PIL import Image
import logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class Predictor:
    def __init__(self, model_path):
        self.model = load_model(model_path)

    def preprocess(self, image_path):
        img = Image.open(image_path).convert("RGB")
        img = img.resize((80, 80))  # ⚠️ change to your training size
        img = np.array(img) / 255.0
        img = np.expand_dims(img, axis=0)
        return img

    def predict(self, image_path):
        processed = self.preprocess(image_path)
        prediction = self.model.predict(processed, verbose=0)  
        logging.info(f"Prediction: {prediction}")
        if prediction[0][0] > 0.5:
            return "Pathologique"
        else:
            return "Non Pathologique"
