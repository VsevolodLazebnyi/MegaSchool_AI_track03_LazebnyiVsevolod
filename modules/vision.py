from ultralytics import YOLO
import numpy as np

class VisionSystem:
    def __init__(self):
        print("Загрузка модели YOLOv8...")
        self.model = YOLO('yolov8n.pt') 

    def analyze_frame(self, frame_np):
        if frame_np is None:
            return "Camera feed unavailable."

        results = self.model(frame_np, verbose=False)
        detected_objects = []
        
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                detected_objects.append(label)

        unique_objects = set(detected_objects)
        
        context = []
        if 'cell phone' in unique_objects:
            context.append("ALERT: Candidate is holding a phone!")
        if 'person' not in unique_objects:
            context.append("ALERT: Candidate is NOT visible.")
        if 'book' in unique_objects or 'laptop' in unique_objects:
             context.append("Note: Books/Laptop visible nearby.")
        
        if not context:
            return "Candidate is present. No suspicious objects detected."
        
        return " | ".join(context)