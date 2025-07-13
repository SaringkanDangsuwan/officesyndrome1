#อันนี้มันจะขึ้นเป็นป็ิอปอัพให้ใส่เวลา ซึ่งเราสร้างมาหลายๆเเบบเพื่อเทส
import tkinter as tk
from tkinter import messagebox
import threading
import time
from plyer import notification

class CountdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("โปรแกรมจับเวลา")
        self.root.geometry("300x200")
        
        self.timer_thread = None
        self.running = False

        # --- จัดวาง UI ให้สวยงามขึ้นเล็กน้อยด้วย padding ---
        # ช่องกรอกเวลา
        tk.Label(root, text="ชั่วโมง").grid(row=0, column=0, padx=5, pady=5)
        tk.Label(root, text="นาที").grid(row=0, column=1, padx=5, pady=5)
        tk.Label(root, text="วินาที").grid(row=0, column=2, padx=5, pady=5)

        self.hour_entry = tk.Entry(root, width=5)
        self.hour_entry.grid(row=1, column=0)

        self.minute_entry = tk.Entry(root, width=5)
        self.minute_entry.grid(row=1, column=1)

        self.second_entry = tk.Entry(root, width=5)
        self.second_entry.grid(row=1, column=2)

        # ปุ่มควบคุม
        self.start_button = tk.Button(root, text="เริ่มจับเวลา", command=self.start_timer)
        self.start_button.grid(row=2, column=0, columnspan=3, pady=10)

        self.cancel_button = tk.Button(root, text="ยกเลิก", command=self.cancel_timer, state="disabled")
        self.cancel_button.grid(row=3, column=0, columnspan=3)

        # แสดงเวลา
        self.time_label = tk.Label(root, text="", font=("Arial", 16))
        self.time_label.grid(row=4, column=0, columnspan=3, pady=10)

    def start_timer(self):
        try:
            hours = int(self.hour_entry.get() or 0)
            minutes = int(self.minute_entry.get() or 0)
            seconds = int(self.second_entry.get() or 0)
        except ValueError:
            messagebox.showerror("ข้อผิดพลาด", "กรุณากรอกตัวเลขที่ถูกต้อง")
            return

        total_seconds = hours * 3600 + minutes * 60 + seconds
        if total_seconds <= 0:
            messagebox.showwarning("คำเตือน", "กรุณากรอกเวลามากกว่า 0")
            return

        self.running = True
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        
        self.timer_thread = threading.Thread(target=self.countdown, args=(total_seconds,))
        self.timer_thread.daemon = True
        self.timer_thread.start()

    def countdown(self, total_seconds):
        while total_seconds > 0 and self.running:
            mins, secs = divmod(total_seconds, 60)
            hours, mins = divmod(mins, 60)
            time_string = f"{hours:02d}:{mins:02d}:{secs:02d}"
            
            self.root.after(0, self.update_display, time_string)

            time.sleep(1)
            total_seconds -= 1

        if self.running:
            self.root.after(0, self.on_timer_finish)

    def update_display(self, text):
        self.time_label.config(text=text)

    def on_timer_finish(self):
        """จัดการทุกอย่างเมื่อเวลาหมด (ถูกเรียกจาก Main Thread)"""
        self.time_label.config(text="หมดเวลา!")
        self.running = False
        self.start_button.config(state="normal")
        self.cancel_button.config(state="disabled")
        
        # ส่งเสียงเตือน
        self.root.bell()
        
        # # แก้ไข: แสดง Pop-up ที่จะอยู่บนสุดเสมอ แทน messagebox เดิม
        self.show_topmost_popup()
        
        # แสดง Notification ของระบบ (plyer) ซึ่งจะทำงานได้ดีเมื่อโปรแกรมอยู่เบื้องหลัง
        self.show_notification()

    def cancel_timer(self):
        if self.running:
            self.running = False
            self.time_label.config(text="ยกเลิกแล้ว")
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")

    # # เพิ่มเข้ามา: ฟังก์ชันสำหรับสร้าง pop-up ที่อยู่บนสุด
    def show_topmost_popup(self):
        """สร้างหน้าต่าง Pop-up ที่จะแสดงอยู่บนสุดเสมอ"""
        popup = tk.Toplevel(self.root)
        popup.title("หมดเวลา!")
        popup.geometry("300x120")

        # จัดหน้าต่างให้อยู่กลางจอ
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        popup_x = root_x + (root_width / 2) - (300 / 2)
        popup_y = root_y + (root_height / 2) - (120 / 2)
        popup.geometry(f"+{int(popup_x)}+{int(popup_y)}")

        # # คุณสมบัติสำคัญ: ทำให้หน้าต่างอยู่บนสุดเสมอ
        popup.attributes('-topmost', True)

        label = tk.Label(popup, text="หมดเวลาที่ตั้งไว้แล้ว!", font=("Arial", 16))
        label.pack(pady=20, padx=10)

        ok_button = tk.Button(popup, text="รับทราบ", command=popup.destroy)
        ok_button.pack(pady=5)

        # ทำให้หน้าต่าง pop-up ได้รับ focus ทันที
        popup.focus_force()
        # ทำให้หน้าต่างหลักเด้งขึ้นมาข้างหน้าด้วย
        self.root.lift()


    def show_notification(self):
        """แสดง Notification ของระบบปฏิบัติการ"""
        try:
            notification.notify(
                title="⏰ แจ้งเตือน",
                message="หมดเวลาที่ตั้งไว้แล้ว!",
                timeout=5
            )
        except Exception as e:
            print(f"Error showing notification: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CountdownTimer(root)
    root.mainloop()
