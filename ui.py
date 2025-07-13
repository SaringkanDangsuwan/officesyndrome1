import customtkinter
import threading
import time
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk

# ลองนำเข้า plyer หากติดตั้งไว้ ถ้าไม่มีจะแสดงข้อความใน console แทน
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("Plyer library not found. System notifications will be disabled.")
    print("Install it using: pip install plyer")


# --- ตั้งค่าธีมเริ่มต้นของโปรแกรม ---
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    """
    คลาสหลักของแอปพลิเคชัน สร้างหน้าต่างและจัดการส่วนประกอบ UI ทั้งหมด
    """
    def __init__(self):
        super().__init__()

        # --- 1. ตั้งค่าหน้าต่างหลัก (Main Window) ---
        self.title("CustomTkinter App with Posture Timer & Detection")
        self.geometry("800x600")

        # --- ตัวแปรสำหรับระบบจับเวลาเพื่อสุขภาพ ---
        self.posture_timer_thread = None
        self.posture_timer_running = False
        self.posture_timer_seconds = 0
        self.notification_target_seconds = 5
        self.notification_cycle_index = 0
        self.health_notifications = [
            {"title": "เปลี่ยนอิริยาบถ", "message": "ลองลุกขึ้นยืดเส้นยืดสาย หรือเปลี่ยนอิริยาบถสักหน่อยไหมครับ"},
            {"title": "พักสายตา", "message": "พักสายตาสักครู่ มองไปไกลๆ หรือหลับตาสัก 1-2 นาทีก็ดีนะ"},
            {"title": "ได้เวลาขยับ", "message": "ได้เวลาลุกเดินไปดื่มน้ำ เข้าห้องน้ำ หรือทำอะไรเล็กๆ น้อยๆ เพื่อขยับร่างกายแล้ว"},
            {"title": "คำเตือนสุขภาพ", "message": "การนั่งนานๆ อาจส่งผลเสียต่อสุขภาพได้ ลุกขึ้นมาขยับตัวบ้างนะ!"},
            {"title": "ยืดกล้ามเนื้อด่วน!", "message": "ร่างกายต้องการการพักผ่อนอย่างจริงจังแล้ว ลุกขึ้นมายืดกล้ามเนื้อหลัง ไหล่ และคอ เพื่อป้องกันออฟฟิศซินโดรม"},
            {"title": "อันตราย! พักทันที", "message": "อันตราย! คุณนั่งทำงานต่อเนื่องมานานแล้ว ควรหยุดพักทันที! การนั่งนานเกินไปเสี่ยงต่อสุขภาพอย่างมาก ลุกไปพักผ่อนอย่างน้อย 15-30 นาทีก่อนกลับมาทำงานต่อนะครับ"}
        ]

        # --- ตัวแปรสำหรับระบบตรวจจับท่าทาง ---
        self.detection_thread = None
        self.detection_running = False
        self.cap = None
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=1)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # --- 2. กำหนด Layout หลักของหน้าต่าง ---
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- 3. สร้าง Frame สำหรับปุ่มนำทาง (Navigation) ---
        self.navigation_frame = customtkinter.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="ew")
        self.navigation_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.home_button = customtkinter.CTkButton(self.navigation_frame, text="Home", command=lambda: self.select_frame_by_name("home"))
        self.home_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.detect_button = customtkinter.CTkButton(self.navigation_frame, text="Detect", command=lambda: self.select_frame_by_name("detect"))
        self.detect_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.exercise_button = customtkinter.CTkButton(self.navigation_frame, text="Exercise", command=lambda: self.select_frame_by_name("exercise"))
        self.exercise_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        # --- 4. สร้าง Frame สำหรับเนื้อหาแต่ละหน้า ---
        self.home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.detect_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.exercise_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")

        # --- 5. เพิ่มเนื้อหาในแต่ละ Frame ---
        self.setup_home_frame()
        self.setup_detect_frame()
        self.setup_exercise_frame()

        # --- 6. แสดง Frame เริ่มต้น ---
        self.select_frame_by_name("home")
        
        # --- 7. ตั้งค่าการปิดโปรแกรม ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # =================================================================================
    # SETUP FRAMES
    # =================================================================================
    def setup_home_frame(self):
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(0, weight=1)
        timer_container = customtkinter.CTkFrame(self.home_frame)
        timer_container.grid(row=0, column=0, padx=20, pady=20, sticky="")
        customtkinter.CTkLabel(timer_container, text="จับเวลาเพื่อสุขภาพ", font=customtkinter.CTkFont(size=20, weight="bold")).pack(pady=(20,10), padx=40)
        settings_frame = customtkinter.CTkFrame(timer_container)
        settings_frame.pack(pady=10, padx=20, fill="x")
        customtkinter.CTkLabel(settings_frame, text="แจ้งเตือนทุกๆ:").pack(side="left", padx=(10, 5), pady=10)
        self.interval_options = ["5 วินาที", "30 นาที", "1 ชั่วโมง", "1.5 ชั่วโมง", "2 ชั่วโมง"]
        self.interval_var = customtkinter.StringVar(value=self.interval_options[0])
        self.interval_menu = customtkinter.CTkOptionMenu(settings_frame, values=self.interval_options, variable=self.interval_var)
        self.interval_menu.pack(side="left", expand=True, fill="x", padx=(5, 10), pady=10)
        self.posture_timer_label = customtkinter.CTkLabel(timer_container, text="00:00:00", font=customtkinter.CTkFont(size=48, weight="bold"))
        self.posture_timer_label.pack(pady=10, padx=40)
        button_frame = customtkinter.CTkFrame(timer_container, fg_color="transparent")
        button_frame.pack(padx=20, pady=(10, 20))
        self.posture_timer_start_button = customtkinter.CTkButton(button_frame, text="เริ่ม", command=self.posture_timer_start)
        self.posture_timer_start_button.grid(row=0, column=0, padx=5)
        self.posture_timer_stop_button = customtkinter.CTkButton(button_frame, text="หยุด", command=self.posture_timer_stop, state="disabled")
        self.posture_timer_stop_button.grid(row=0, column=1, padx=5)

    def setup_detect_frame(self):
        self.detect_frame.grid_columnconfigure(0, weight=1)
        self.detect_frame.grid_rowconfigure(0, weight=1)
        
        # Label to display camera feed
        self.video_label = customtkinter.CTkLabel(self.detect_frame, text="กด 'Start Detection' เพื่อเปิดกล้อง")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Frame for buttons
        detect_button_frame = customtkinter.CTkFrame(self.detect_frame)
        detect_button_frame.grid(row=1, column=0, pady=10)
        
        self.start_detect_button = customtkinter.CTkButton(detect_button_frame, text="Start Detection", command=self.start_detection_thread)
        self.start_detect_button.pack(side="left", padx=10)
        
        self.stop_detect_button = customtkinter.CTkButton(detect_button_frame, text="Stop Detection", command=self.stop_detection, state="disabled")
        self.stop_detect_button.pack(side="left", padx=10)

    def setup_exercise_frame(self):
        exercise_label = customtkinter.CTkLabel(self.exercise_frame, text="💪\n\nExercise Page\nส่วนสำหรับออกกำลังกาย", font=customtkinter.CTkFont(size=20, weight="bold"))
        exercise_label.pack(expand=True, padx=20, pady=20)
        exercise_progressbar = customtkinter.CTkProgressBar(self.exercise_frame)
        exercise_progressbar.pack(pady=10, padx=20, fill="x")
        exercise_progressbar.set(0.5)

    # =================================================================================
    # POSTURE TIMER LOGIC (HOME FRAME)
    # =================================================================================
    def posture_timer_start(self):
        if self.posture_timer_running: return
        selected_interval_str = self.interval_var.get()
        interval_map = {"5 วินาที": 5, "30 นาที": 30 * 60, "1 ชั่วโมง": 60 * 60, "1.5 ชั่วโมง": 90 * 60, "2 ชั่วโมง": 120 * 60}
        self.notification_target_seconds = interval_map.get(selected_interval_str, 5)
        self.posture_timer_running = True
        self.posture_timer_seconds = 0
        self.notification_cycle_index = 0
        self.posture_timer_start_button.configure(state="disabled")
        self.posture_timer_stop_button.configure(state="normal")
        self.interval_menu.configure(state="disabled")
        self.posture_timer_thread = threading.Thread(target=self.posture_timer_run, daemon=True)
        self.posture_timer_thread.start()

    def posture_timer_run(self):
        while self.posture_timer_running:
            time.sleep(1)
            if not self.posture_timer_running: break
            self.posture_timer_seconds += 1
            self.after(0, self.posture_timer_update_display)
            if self.notification_target_seconds > 0 and self.posture_timer_seconds > 0 and self.posture_timer_seconds % self.notification_target_seconds == 0:
                notification_data = self.health_notifications[self.notification_cycle_index]
                self.after(0, self.trigger_notification, notification_data["title"], notification_data["message"])
                if self.notification_cycle_index < len(self.health_notifications) - 1:
                    self.notification_cycle_index += 1

    def posture_timer_update_display(self):
        mins, secs = divmod(self.posture_timer_seconds, 60)
        hours, mins = divmod(mins, 60)
        time_string = f"{hours:02d}:{mins:02d}:{secs:02d}"
        self.posture_timer_label.configure(text=time_string)

    def posture_timer_stop(self):
        if self.posture_timer_running:
            self.posture_timer_running = False
            self.posture_timer_label.configure(text="00:00:00")
            self.posture_timer_start_button.configure(state="normal")
            self.posture_timer_stop_button.configure(state="disabled")
            self.interval_menu.configure(state="normal")
            self.posture_timer_seconds = 0
            self.notification_cycle_index = 0

    # =================================================================================
    # POSTURE DETECTION LOGIC (DETECT FRAME)
    # =================================================================================
    def start_detection_thread(self):
        if self.detection_running: return
        self.detection_running = True
        self.start_detect_button.configure(state="disabled")
        self.stop_detect_button.configure(state="normal")
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.detection_thread.start()

    def detection_loop(self):
        self.cap = cv2.VideoCapture(1) # ลองใช้ 0, ถ้าไม่ได้ลอง 1
        if not self.cap.isOpened():
            self.after(0, self.show_camera_error)
            self.stop_detection()
            return
            
        while self.detection_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = self.pose.process(image_rgb)
            image_rgb.flags.writeable = True
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            posture_status, text_color = "No Person Detected", (0, 165, 255)
            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(image_bgr, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                                               landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style())
                posture_status, text_color = self.analyze_posture(results.pose_landmarks.landmark, frame.shape[1], frame.shape[0])
            
            cv2.putText(image_bgr, f"Status: {posture_status}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2, cv2.LINE_AA)
            
            # Convert image for CTk
            img = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
            ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(640, 480))
            
            # Update label in main thread
            self.after(0, self.update_video_label, ctk_img)
            time.sleep(0.01) # Small delay

        if self.cap:
            self.cap.release()

    def stop_detection(self):
        self.detection_running = False
        if self.cap:
            self.cap.release()
        self.start_detect_button.configure(state="normal")
        self.stop_detect_button.configure(state="disabled")
        self.video_label.configure(image=None, text="กด 'Start Detection' เพื่อเปิดกล้อง")

    def show_camera_error(self):
        self.video_label.configure(text="Error: ไม่สามารถเปิดกล้องได้\nกรุณาตรวจสอบว่ากล้องเชื่อมต่ออยู่และไม่ถูกใช้งานโดยโปรแกรมอื่น")

    def update_video_label(self, ctk_img):
        self.video_label.configure(image=ctk_img, text="")

    def calculate_angle(self, a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        return np.degrees(np.arccos(cosine_angle))

    def analyze_posture(self, landmarks, image_width, image_height):
        try:
            lm = self.mp_pose.PoseLandmark
            left_shoulder = [landmarks[lm.LEFT_SHOULDER.value].x * image_width, landmarks[lm.LEFT_SHOULDER.value].y * image_height]
            right_shoulder = [landmarks[lm.RIGHT_SHOULDER.value].x * image_width, landmarks[lm.RIGHT_SHOULDER.value].y * image_height]
            left_ear = [landmarks[lm.LEFT_EAR.value].x * image_width, landmarks[lm.LEFT_EAR.value].y * image_height]
            right_ear = [landmarks[lm.RIGHT_EAR.value].x * image_width, landmarks[lm.RIGHT_EAR.value].y * image_height]
            nose = [landmarks[lm.NOSE.value].x * image_width, landmarks[lm.NOSE.value].y * image_height]

            angle_left_neck = self.calculate_angle(left_shoulder, left_ear, nose)
            angle_right_neck = self.calculate_angle(right_shoulder, right_ear, nose)
            
            if angle_left_neck < 165 or angle_right_neck < 165:
                return "Incorrect: Forward Head", (0, 0, 255)

            shoulder_y_diff = abs(left_shoulder[1] - right_shoulder[1])
            if shoulder_y_diff > 25:
                return "Incorrect: Leaning", (0, 0, 255)
            
            return "Correct Posture", (0, 255, 0)
        except Exception:
            return "Cannot Analyze", (0, 165, 255)

    # =================================================================================
    # GENERAL APP LOGIC
    # =================================================================================
    def select_frame_by_name(self, name):
        # Stop detection if navigating away
        if self.detection_running:
            self.stop_detection()
            
        self.home_frame.grid_forget()
        self.detect_frame.grid_forget()
        self.exercise_frame.grid_forget()
        if name == "home": self.home_frame.grid(row=1, column=0, sticky="nsew")
        elif name == "detect": self.detect_frame.grid(row=1, column=0, sticky="nsew")
        elif name == "exercise": self.exercise_frame.grid(row=1, column=0, sticky="nsew")

    def trigger_notification(self, title, message):
        self.bell()
        self.show_popup(title, message, topmost=True)
        self.show_system_notification(title, message)

    def show_system_notification(self, title, message):
        if not PLYER_AVAILABLE: return
        try:
            notification.notify(title=title, message=message, timeout=10)
        except Exception as e:
            print(f"Error showing notification: {e}")

    def show_popup(self, title, message, topmost=False):
        popup = customtkinter.CTkToplevel(self)
        popup.title(title)
        popup.geometry("380x180")
        self.update_idletasks()
        app_x, app_y, app_width, app_height = self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height()
        popup_x, popup_y = app_x + (app_width // 2) - (380 // 2), app_y + (app_height // 2) - (180 // 2)
        popup.geometry(f"+{popup_x}+{popup_y}")
        if topmost: popup.attributes('-topmost', True)
        label = customtkinter.CTkLabel(popup, text=message, font=customtkinter.CTkFont(size=16), wraplength=350)
        label.pack(pady=20, padx=20, expand=True, fill="both")
        ok_button = customtkinter.CTkButton(popup, text="รับทราบ", command=popup.destroy, width=100)
        ok_button.pack(pady=(0, 20))
        popup.grab_set()
        popup.focus_force()

    def on_closing(self):
        """Called when the main window is closed."""
        self.posture_timer_running = False
        self.detection_running = False
        if self.cap:
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
