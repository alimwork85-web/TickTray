import sys
import os
import json
import traceback

# معالجة أخطاء النظام وعرضها في نافذة رسالة إن حدثت
def show_error_and_exit(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(err_msg)
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "TickTray Error", f"حدث خطأ أثناء التشغيل:\n\n{err_msg}")
    except Exception:
        pass
    sys.exit(1)

sys.excepthook = show_error_and_exit

from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, 
                             QInputDialog, QMessageBox)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QTime
import winsound

# دالة لتحديد المسار الصحيح للملفات والموارد سواء أثناء التطوير أو بعد التجميع بـ PyInstaller
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_PATH = resource_path("TickTray.ico")

DEFAULT_CONFIG = {
    "defaultMinutes": 20,
    "defaultSnoozeMinutes": 5,
    "maximumMinutes": 1440,
    "buttonLabel": "⏱ Timer",
    "completionSound": 1
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

class TickTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.config = load_config()
        self.remaining_seconds = 0
        self.is_running = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)

        # إنشاء الأيقونة
        self.tray_icon = QSystemTrayIcon()
        
        # التأكد من تحميل الأيقونة بنجاح
        if os.path.exists(ICON_PATH):
            self.icon = QIcon(ICON_PATH)
            self.tray_icon.setIcon(self.icon)
        else:
            # أيقونة افتراضية في حال عدم وجود الملف
            self.icon = self.app.style().standardIcon(self.app.style().StandardPixmap.SP_ComputerIcon)
            self.tray_icon.setIcon(self.icon)

        self.create_menu()
        self.update_tooltip("TickTray - متوقف")
        
        # إظهار الأيقونة في صينية النظام
        self.tray_icon.show()

    def create_menu(self):
        self.menu = QMenu()

        self.action_start_default = QAction(f"بدء العداد ({self.config['defaultMinutes']} دقيقة)", self.menu)
        self.action_start_default.triggered.connect(self.start_default_timer)
        self.menu.addAction(self.action_start_default)

        self.action_custom = QAction("تحديد وقت مخصص...", self.menu)
        self.action_custom.triggered.connect(self.set_custom_timer)
        self.menu.addAction(self.action_custom)

        self.menu.addSeparator()

        self.action_pause_resume = QAction("إيقاف مؤقت / استئناف", self.menu)
        self.action_pause_resume.triggered.connect(self.toggle_pause)
        self.action_pause_resume.setEnabled(False)
        self.menu.addAction(self.action_pause_resume)

        self.action_stop = QAction("إلغاء العداد", self.menu)
        self.action_stop.triggered.connect(self.stop_timer)
        self.action_stop.setEnabled(False)
        self.menu.addAction(self.action_stop)

        self.menu.addSeparator()

        self.action_quit = QAction("خروج", self.menu)
        self.action_quit.triggered.connect(self.app.quit)
        self.menu.addAction(self.action_quit)

        self.tray_icon.setContextMenu(self.menu)

    def start_default_timer(self):
        self.start_timer(self.config["defaultMinutes"])

    def set_custom_timer(self):
        minutes, ok = QInputDialog.getInt(
            None, 
            "ضبط العداد المخصص", 
            "أدخل عدد الدقائق:", 
            self.config["defaultMinutes"], 
            1, 
            self.config["maximumMinutes"]
        )
        if ok:
            self.start_timer(minutes)

    def start_timer(self, minutes):
        self.remaining_seconds = minutes * 60
        self.is_running = True
        self.timer.start(1000)
        self.action_pause_resume.setEnabled(True)
        self.action_stop.setEnabled(True)
        self.update_display()

    def toggle_pause(self):
        if self.is_running:
            self.timer.stop()
            self.is_running = False
            self.update_tooltip(f"TickTray - متوقف مؤقتاً ({self.format_time(self.remaining_seconds)})")
        else:
            self.timer.start(1000)
            self.is_running = True
            self.update_display()

    def stop_timer(self):
        self.timer.stop()
        self.is_running = False
        self.remaining_seconds = 0
        self.action_pause_resume.setEnabled(False)
        self.action_stop.setEnabled(False)
        self.update_tooltip("TickTray - متوقف")

    def update_timer(self):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.update_display()
        else:
            self.timer.stop()
            self.is_running = False
            self.on_timer_finished()

    def update_display(self):
        time_str = self.format_time(self.remaining_seconds)
        self.update_tooltip(f"TickTray: {time_str}")

    def format_time(self, seconds):
        time = QTime(0, 0, 0).addSecs(seconds)
        if seconds >= 3600:
            return time.toString("hh:mm:ss")
        return time.toString("mm:ss")

    def update_tooltip(self, text):
        self.tray_icon.setToolTip(text)

    def on_timer_finished(self):
        self.action_pause_resume.setEnabled(False)
        self.action_stop.setEnabled(False)
        self.update_tooltip("TickTray - انتهى الوقت!")

        if self.config.get("completionSound", 1):
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

        self.tray_icon.showMessage(
            "TickTray",
            "⏱ انتهى وقت العداد التنازلي!",
            QSystemTrayIcon.MessageIcon.Information,
            5000
        )

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = TickTrayApp()
    app.run()