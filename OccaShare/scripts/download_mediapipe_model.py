import os
import urllib.request

model_dir = "app/models"
model_path = os.path.join(model_dir, "face_landmarker.task")
model_url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

try:
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created directory: {model_dir}")

    if not os.path.exists(model_path):
        print(f"Downloading model from {model_url}...")
        urllib.request.urlretrieve(model_url, model_path)
        print(f"Successfully downloaded model to {model_path}")
    else:
        print(f"Model already exists at {model_path}")

    # Verify file size
    size = os.path.getsize(model_path)
    print(f"File size: {size} bytes")

except Exception as e:
    print(f"Error: {e}")
