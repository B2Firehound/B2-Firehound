from ultralytics import YOLO
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

if __name__ == '__main__':
    model = YOLO("yolov8s.pt")

    model.train(
        data="C:/Users/Utilisateur/Downloads/RAPACE_dataset/drone.yaml",
        epochs=150,
        imgsz=640,
        batch=16,
        lr0=0.001,
        optimizer="AdamW",
        mosaic=0.8,
        scale=0.5,
        fliplr=0.5,
    )