import ctypes
import logging
import math
import os
import sys
import time
import traceback

import config

config.setup_logging()


def show_error_and_exit(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.error("Unhandled exception:\n%s", err_msg)
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            QMessageBox.critical(None, "TickTray Error", f"حدث خطأ أثناء التشغيل:\n\n{err_msg}")
    except Exception:
        pass
    sys.exit(1)


sys.excepthook = show_error_and_exit

import winsound

from PyQt6.QtCore import QLocale, QLockFile, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QSystemTrayIcon

from settings_dialog import SettingsDialog
from tray_icon import render_icon

QUICK_MINUTES = (5, 10, 25, 45)
IDLE, RUNNING, PAUSED, FINISHED = range(4)

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, "TickTray.ico")


def format_time(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class TickTrayApp:
    def __init__(self):
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TickTray.App")
        except Exception:
            pass

        self.lock = QLockFile(os.path.join(config.APP_DIR, "TickTray.lock"))
        self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(100):
            QMessageBox.information(None, "TickTray", "TickTray يعمل بالفعل في صينية النظام.")
            sys.exit(0)

        self.config = config.load_config()
        self.config["startWithWindows"] = config.get_autostart()
        self.state = IDLE
        self.total_seconds = 0
        self.deadline = 0.0
        self.paused_remaining = 0.0
        self.last_angle = None
        self.settings_dialog = None

        self.app_icon = QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else render_icon()
        self.app.setWindowIcon(self.app_icon)

        self.timer = QTimer()
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.tick)

        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(render_icon())
        self.tray_icon.activated.connect(self.on_activated)
        self.tray_icon.messageClicked.connect(self.on_message_clicked)

        self.create_menu()
        self.refresh_ui()
        self.tray_icon.show()

    # ---- menu -------------------------------------------------------------------------------------------------
    def create_menu(self):
        self.menu = QMenu()

        self.action_start_default = self._action("", self.start_default_timer)
        self.quick_menu = self.menu.addMenu("أوقات سريعة")
        for m in QUICK_MINUTES:
            a = QAction(f"{m} دقيقة", self.quick_menu)
            a.triggered.connect(lambda _=False, m=m: self.start_timer(m))
            self.quick_menu.addAction(a)
        self.action_custom = self._action("تحديد وقت مخصص...", self.set_custom_timer)
        self.menu.addSeparator()
        self.action_pause_resume = self._action("إيقاف مؤقت", self.toggle_pause)
        self.action_snooze = self._action("", self.snooze)
        self.action_stop = self._action("إلغاء العداد", self.stop_timer)
        self.menu.addSeparator()
        self.action_settings = self._action("الإعدادات...", self.open_settings)
        self.action_quit = self._action("خروج", self.quit_app)

        self.tray_icon.setContextMenu(self.menu)

    def _action(self, text, slot):
        a = QAction(text, self.menu)
        a.triggered.connect(lambda _=False: slot())
        self.menu.addAction(a)
        return a

    def refresh_ui(self):
        """Sync menu texts/availability, tooltip and icon with the current state."""
        self.action_start_default.setText(f"بدء العداد ({self.config['defaultMinutes']} دقيقة)")
        self.action_snooze.setText(f"تأجيل ({self.config['defaultSnoozeMinutes']} دقيقة)")
        self.action_snooze.setVisible(self.state == FINISHED)
        active = self.state in (RUNNING, PAUSED)
        self.action_pause_resume.setEnabled(active)
        self.action_pause_resume.setText("استئناف" if self.state == PAUSED else "إيقاف مؤقت")
        self.action_stop.setEnabled(active)
        self.update_display(force=True)

    # ---- timer ------------------------------------------------------------------------------------------------
    def remaining(self):
        if self.state == RUNNING:
            return max(0.0, self.deadline - time.monotonic())
        if self.state == PAUSED:
            return self.paused_remaining
        return 0.0

    def start_default_timer(self):
        self.start_timer(self.config["defaultMinutes"])

    def set_custom_timer(self):
        top = self.config["maximumMinutes"]
        minutes, ok = QInputDialog.getInt(
            None, "ضبط العداد المخصص", "أدخل عدد الدقائق:",
            min(self.config["lastCustomMinutes"], top), 1, top)
        if ok:
            self.config["lastCustomMinutes"] = minutes
            self.save_quietly()
            self.start_timer(minutes)

    def start_timer(self, minutes):
        self.total_seconds = minutes * 60
        self.deadline = time.monotonic() + self.total_seconds
        self.state = RUNNING
        self.timer.start()
        self.refresh_ui()

    def snooze(self):
        self.start_timer(self.config["defaultSnoozeMinutes"])

    def toggle_pause(self):
        if self.state == RUNNING:
            self.paused_remaining = self.remaining()
            self.timer.stop()
            self.state = PAUSED
        elif self.state == PAUSED:
            self.deadline = time.monotonic() + self.paused_remaining
            self.state = RUNNING
            self.timer.start()
        self.refresh_ui()

    def stop_timer(self):
        self.timer.stop()
        self.state = IDLE
        self.refresh_ui()

    def tick(self):
        if self.remaining() <= 0:
            self.timer.stop()
            self.state = FINISHED
            self.refresh_ui()
            self.on_timer_finished()
        else:
            self.update_display()

    def update_display(self, force=False):
        if self.state in (RUNNING, PAUSED):
            rem = self.remaining()
            shown = format_time(math.ceil(rem))
            # digits only, prefixed with LRM so Windows keeps Western digits (no Arabic context to shape them)
            self.tray_icon.setToolTip("‎" + shown)
            fraction = rem / self.total_seconds if self.total_seconds else 0
            angle = int(fraction * 360)
            if force or angle != self.last_angle:
                self.last_angle = angle
                self.tray_icon.setIcon(render_icon(fraction, show_check=False))
        elif self.state == FINISHED:
            self.tray_icon.setToolTip("TickTray - انتهى الوقت!")
            self.last_angle = None
            self.tray_icon.setIcon(render_icon(0.0, show_check=True))
        else:
            self.tray_icon.setToolTip("TickTray - متوقف")
            self.last_angle = None
            self.tray_icon.setIcon(render_icon())

    def on_timer_finished(self):
        if self.config.get("completionSound"):
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        self.tray_icon.showMessage(
            "TickTray",
            "⏱ انتهى وقت العداد التنازلي! انقر هنا للتأجيل.",
            QSystemTrayIcon.MessageIcon.Information,
            8000,
        )

    # ---- tray interaction -------------------------------------------------------------------------------------
    def on_activated(self, reason):
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self.state in (RUNNING, PAUSED):
            self.toggle_pause()
        else:
            self.start_default_timer()

    def on_message_clicked(self):
        if self.state == FINISHED:
            self.snooze()

    # ---- settings ---------------------------------------------------------------------------------------------
    def is_dark(self):
        try:
            return self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            return self.app.palette().window().color().lightness() < 128

    def open_settings(self):
        if self.settings_dialog is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        dlg = SettingsDialog(self.config, self.is_dark())
        dlg.setWindowIcon(self.app_icon)
        dlg.finished.connect(lambda _r, d=dlg: self.on_settings_closed(d))
        self.settings_dialog = dlg
        dlg.show()
        dlg.activateWindow()

    def on_settings_closed(self, dlg):
        self.settings_dialog = None
        new_cfg = dlg.result_config
        dlg.deleteLater()
        if not new_cfg:
            return
        self.config = new_cfg
        try:
            config.save_config(self.config)
            config.set_autostart(self.config["startWithWindows"])
        except Exception:
            logging.exception("failed to save settings")
            QMessageBox.warning(None, "TickTray", "تعذّر حفظ الإعدادات.")
        self.refresh_ui()

    def save_quietly(self):
        try:
            config.save_config(self.config)
        except Exception:
            logging.exception("failed to save config")

    def quit_app(self):
        if self.settings_dialog is not None:
            self.settings_dialog.force_close()
        self.app.quit()

    def run(self):
        code = self.app.exec()
        self.lock.unlock()
        sys.exit(code)


if __name__ == "__main__":
    TickTrayApp().run()
