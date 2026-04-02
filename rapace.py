import cv2
import threading
import time
import os
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from ultralytics import YOLO
import numpy as np
import pygame
from datetime import datetime
import serial  # Import nécessaire pour la communication série

# Désactivation des logs OpenCV inutiles
os.environ['OPENCV_VIDEOIO_LOGLEVEL'] = '0'
os.environ['OPENCV_OPENCL_CACHE_CLEANUP'] = '0'

class RAPACE:
    def __init__(self, root):
        self.root = root
        self.root.title("RAPACE")
        self.root.configure(bg="#020c1b")
       
        try:
            self.root.iconbitmap("logo.ico")
        except:
            pass
       
        # --- CONFIGURATION SÉRIE (ELRS) ---
        try:
            self.ser = serial.Serial('COM3', 115200, timeout=0.1)
        except:
            self.ser = None
            print("ERREUR : Module ELRS non détecté sur COM3")

        # --- CAMÉRA & IA YOLO ---
        self.model = YOLO("best.pt")
        self.cap = cv2.VideoCapture(0)  # Change à 1 ou l'URL du flux drone si besoin
       
        self.frame = None
        self.running = True
        self.target_box = None
        self.is_tracking = False
        self.lock_confirmed = False
        self.start_time = 0
        self.LOCK_DURATION = 5.0
       
        # Coordonnées servos normalisées 0-100
        self.servo_x = 50
        self.servo_y = 50
       
        # Modes
        self.night_mode = False
        self.auto_mode = False
        self.flip_view = True
       
        # Son
        pygame.mixer.init()
        self.sound_playing = False
        try:
            self.alarm_sound = pygame.mixer.Sound("Topgun.wav")
        except:
            self.alarm_sound = None

        self.init_tracker_module()
        self.setup_ui()
       
        # Bind souris sur Canvas
        self.canvas.bind("<Motion>", self.mouse_move)

        # Thread IA
        self.thread_ia = threading.Thread(target=self.ia_detection_loop, daemon=True)
        self.thread_ia.start()
       
        self.add_log("SYSTÈME RAPACE OPTIMISÉ - PRÊT")
        self.update_view()

    # ---------------- UI ----------------
    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg="#020c1b")
        self.main_container.pack(padx=20, pady=20)

        self.left_panel = tk.Frame(self.main_container, bg="#020c1b")
        self.left_panel.pack(side="left")

        self.canvas = tk.Canvas(self.left_panel, width=640, height=480, bg="#000", highlightthickness=2, highlightbackground="#00f5d4")
        self.canvas.pack()

        self.side_panel = tk.Frame(self.main_container, bg="#020c1b")
        self.side_panel.pack(side="right", fill="y", padx=(20, 0))

        tk.Label(self.side_panel, text="DONNÉES TACTIQUES", fg="#00f5d4", bg="#020c1b", font=("Courier", 11, "bold")).pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(self.side_panel, width=35, height=15, bg="#011627", fg="#4cc9f0", font=("Courier", 9), bd=0)
        self.log_area.pack(pady=(5, 15))

        tk.Label(self.side_panel, text="CONTRÔLE", fg="#00f5d4", bg="#020c1b", font=("Courier", 11, "bold")).pack(anchor="w")
        self.btn_nv = self.create_button("VISION NOCTURNE [OFF]", self.toggle_nv)
        self.btn_flip = self.create_button("MIROIR OPTIQUE [ON]", self.toggle_flip)
        self.btn_mode = self.create_button("MODE : MANUEL", self.toggle_mode)
        self.btn_cam = self.create_button("SOURCE : INTERNE", self.toggle_camera)

        self.status_frame = tk.Frame(self.root, bg="#001d3d", height=40)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_bar = tk.Label(self.status_frame, text="OPÉRATIONNEL", fg="#fff", bg="#001d3d", font=("Courier", 12, "bold"))
        self.status_bar.pack(pady=5)

    def create_button(self, text, command):
        btn = tk.Button(self.side_panel, text=text, command=command, bg="#1a2e44", fg="#ffffff", font=("Courier", 10), relief="flat", width=28, pady=8)
        btn.pack(pady=4)
        return btn

    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"> {timestamp} : {message}\n")
        self.log_area.see(tk.END)

    # ---------------- TOGGLES ----------------
    def toggle_nv(self):
        self.night_mode = not self.night_mode
        self.btn_nv.config(text=f"VISION NOCTURNE [{'ON' if self.night_mode else 'OFF'}]", bg="#004b23" if self.night_mode else "#1a2e44")

    def toggle_flip(self):
        self.flip_view = not self.flip_view
        self.btn_flip.config(text=f"MIROIR OPTIQUE [{'ON' if self.flip_view else 'OFF'}]")

    def toggle_mode(self):
        self.auto_mode = not self.auto_mode
        self.btn_mode.config(text=f"MODE : {'AUTO' if self.auto_mode else 'MANUEL'}", bg="#9b2226" if self.auto_mode else "#1a2e44")
        self.add_log(f"MODE PASSÉ EN { 'AUTOMATIQUE' if self.auto_mode else 'MANUEL' }")

    def toggle_camera(self):
        self.cap.release()
        current_text = self.btn_cam.cget("text")
        if "INTERNE" in current_text:
            self.cap = cv2.VideoCapture(1)  # Caméra externe
            self.btn_cam.config(text="SOURCE : DRONE")
        else:
            self.cap = cv2.VideoCapture(0)
            self.btn_cam.config(text="SOURCE : INTERNE")

    # ---------------- SOURIS ----------------
    def mouse_move(self, event):
        if not self.auto_mode:
            self.servo_x = int((event.x / 640) * 100)
            self.servo_y = int((event.y / 480) * 100)
            self.send_to_elrs()

    def send_to_elrs(self):
        if self.ser:
            data = f"{self.servo_x},{self.servo_y}\n"
            self.ser.write(data.encode())

    # ---------------- TRACKER ----------------
    def init_tracker_module(self):
        try:
            self.tracker = cv2.TrackerKCF_create()
        except:
            self.tracker = cv2.legacy.TrackerKCF_create()

    # ---------------- IA DETECTION ----------------
    def ia_detection_loop(self):
        while self.running:
            if self.frame is not None:
                results = self.model.predict(self.frame, conf=0.25, classes=[0], imgsz=640, verbose=False)
                if len(results[0].boxes) > 0:
                    box = results[0].boxes[0]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    new_box = (x1, y1, x2-x1, y2-y1)
                   
                    if not self.is_tracking:
                        self.target_box = new_box
                        self.init_tracker_module()
                        self.tracker.init(self.frame, self.target_box)
                        self.is_tracking = True
                        self.add_log("DRONE IDENTIFIÉ")
                elif not self.is_tracking:
                    self.target_box = None
            time.sleep(0.05)

    # ---------------- AFFICHAGE ----------------
    def update_view(self):
        ret, frame = self.cap.read()
        if not ret:
            self.root.after(10, self.update_view)
            return
           
        if self.flip_view:
            frame = cv2.flip(frame, 1)
        self.frame = frame.copy()
        display_frame = frame.copy()

        if self.night_mode:
            display_frame[:,:,0] = 0
            display_frame[:,:,2] = 0
            display_frame = cv2.addWeighted(display_frame, 1.4, display_frame, 0, 15)

        if self.is_tracking:
            success, box = self.tracker.update(frame)
            if success:
                x, y, w, h = [int(v) for v in box]
                cx, cy = x + w//2, y + h//2
               
                if self.auto_mode:
                    diff_x = (cx - 320) / 320
                    diff_y = (cy - 240) / 240
                    self.servo_x = np.clip(self.servo_x + (diff_x * 5), 0, 100)
                    self.servo_y = np.clip(self.servo_y + (diff_y * 5), 0, 100)
                    self.send_to_elrs()

                if abs(cx - 320) < 100 and abs(cy - 240) < 100:
                    if not self.sound_playing:
                        if self.alarm_sound: self.alarm_sound.play(-1)
                        self.start_time = time.time()
                        self.sound_playing = True
                        self.add_log("VERROUILLAGE...")
                   
                    elapsed = time.time() - self.start_time
                    if elapsed >= self.LOCK_DURATION:
                        if not self.lock_confirmed: self.add_log("CIBLE VERROUILLÉE")
                        self.lock_confirmed = True
                        color = (0, 0, 255)
                        progress = 1.0
                    else:
                        color = (0, 210, 255)
                        progress = elapsed / self.LOCK_DURATION
                else:
                    self.reset_lock()
                    color = (0, 255, 0)
                    progress = 0

                self.draw_target_box(display_frame, x, y, w, h, color)
                cv2.rectangle(display_frame, (x, y + h + 8), (x + int(w * progress), y + h + 12), color, -1)
            else:
                self.is_tracking = False
                self.reset_lock()

        self.draw_flight_hud(display_frame)
        img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk
       
        if self.lock_confirmed:
            self.status_bar.config(text="LOCK CONFIRMÉ", bg="#9b2226")
        elif self.sound_playing:
            self.status_bar.config(text="ACQUISITION...", bg="#e67e22")
        else:
            self.status_bar.config(text="VEILLE RADAR", bg="#001d3d")

        self.root.after(10, self.update_view)

    def reset_lock(self):
        if self.sound_playing:
            pygame.mixer.stop()
            self.sound_playing = False
        self.lock_confirmed = False

    # ---------------- HUD ----------------
    def draw_target_box(self, frame, x, y, w, h, color):
        l = 15
        cv2.line(frame, (x, y), (x+l, y), color, 2)
        cv2.line(frame, (x, y), (x, y+l), color, 2)
        cv2.line(frame, (x+w, y), (x+w-l, y), color, 2)
        cv2.line(frame, (x+w, y), (x+w, y+l), color, 2)
        cv2.line(frame, (x, y+h), (x+l, y+h), color, 2)
        cv2.line(frame, (x, y+h), (x, y+h-l), color, 2)
        cv2.line(frame, (x+w, y+h), (x+w-l, y+h), color, 2)
        cv2.line(frame, (x+w, y+h), (x+w, y+h-l), color, 2)

    def draw_flight_hud(self, frame):
        color = (0, 0, 255) if self.lock_confirmed else (0, 255, 210)
        cv2.circle(frame, (320, 240), 30, color, 1)
        cv2.line(frame, (320, 200), (320, 230), color, 1)
        cv2.line(frame, (320, 250), (320, 280), color, 1)
        cv2.line(frame, (280, 240), (310, 240), color, 1)
        cv2.line(frame, (330, 240), (360, 240), color, 1)
        cv2.putText(frame, "RAPACE", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.putText(frame, f"X: {int(self.servo_x)}% Y: {int(self.servo_y)}%", (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

if __name__ == "__main__":
    root = tk.Tk()
    app = RAPACE(root)
    root.mainloop()