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
            QMessageBox.critical(None, "TickTray Error", f"حدث خطأ أثناء التشغيل / An error occurred:\n\n{err_msg}")
    except Exception:
        pass
    sys.exit(1)


sys.excepthook = show_error_and_exit

import winsound

from PyQt6.QtCore import QLocale, QLockFile, QTime, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QLineEdit, QMenu, QMessageBox, QSpinBox,
    QSystemTrayIcon, QTimeEdit, QVBoxLayout,
)

import i18n
from i18n import t
from settings_dialog import SettingsDialog
from tray_icon import render_icon

QUICK_MINUTES = (5, 10, 25, 45)
IDLE, RUNNING, PAUSED, FINISHED = range(4)
EN_LOCALE = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(BASE_DIR, "TickTray.ico")


def format_time(seconds):
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


ALARM_WAV = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Media", "Alarm01.wav")

alarm_stop_timer = None  # single-shot QTimer that silences the repeating alarm


def stop_alarm():
    """Silence the alarm at once and cancel its pending auto-stop."""
    global alarm_stop_timer
    if alarm_stop_timer is not None:
        alarm_stop_timer.stop()
    try:
        winsound.PlaySound(None, 0)
    except Exception:
        logging.exception("stopping the alarm sound failed")


def play_alarm():
    """A clearly audible alarm that keeps repeating until stopped. MessageBeep alone is often a faint system sound (or none at all)."""
    global alarm_stop_timer
    try:
        if os.path.exists(ALARM_WAV):
            winsound.PlaySound(
                ALARM_WAV,
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP | winsound.SND_NODEFAULT)
            if alarm_stop_timer is None:
                alarm_stop_timer = QTimer()
                alarm_stop_timer.setSingleShot(True)
                alarm_stop_timer.timeout.connect(stop_alarm)
            alarm_stop_timer.start(60000)  # ms: the alarm stops itself after 60 seconds
        else:
            winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        logging.exception("alarm sound failed")
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass


def icon_label(seconds):
    """Short label drawn on the tray icon: minutes left, or hours once it no longer fits in 2 digits."""
    minutes = math.ceil(max(0, seconds) / 60)
    if minutes <= 99:
        return str(minutes)
    return f"{math.ceil(minutes / 60)}h"


def _dialog_buttons(dialog):
    """Localised OK/Cancel row wired to `dialog`."""
    buttons = QDialogButtonBox()
    buttons.addButton(t("ok"), QDialogButtonBox.ButtonRole.AcceptRole)
    buttons.addButton(t("cancel"), QDialogButtonBox.ButtonRole.RejectRole)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


def _name_field():
    """Optional timer name, 40 characters max."""
    edit = QLineEdit()
    edit.setMaxLength(40)
    edit.setPlaceholderText(t("name_label"))
    return edit


class ClockTimeDialog(QDialog):
    """Asks for a clock time (HH:mm, 24-hour) in Western digits, plus an optional name."""

    def __init__(self, initial_minutes):
        super().__init__()
        self.setWindowTitle(t("until_title"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setLocale(EN_LOCALE)  # Western digits in both languages
        self.time_edit.setTime(QTime.currentTime().addSecs(initial_minutes * 60))
        self.name_edit = _name_field()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t("until_label")))
        layout.addWidget(self.time_edit)
        layout.addWidget(self.name_edit)
        layout.addWidget(_dialog_buttons(self))

    def time(self):
        return self.time_edit.time()

    def name(self):
        return self.name_edit.text().strip()


class CustomTimeDialog(QDialog):
    """Asks for a number of minutes (1..top) and an optional name."""

    def __init__(self, initial_minutes, top_minutes):
        super().__init__()
        self.setWindowTitle(t("custom_title"))
        self.minutes_edit = QSpinBox()
        self.minutes_edit.setLocale(EN_LOCALE)
        self.minutes_edit.setRange(1, top_minutes)
        self.minutes_edit.setValue(min(initial_minutes, top_minutes))
        self.minutes_edit.setSuffix(t("min_suffix"))
        self.name_edit = _name_field()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(t("custom_label")))
        layout.addWidget(self.minutes_edit)
        layout.addWidget(self.name_edit)
        layout.addWidget(_dialog_buttons(self))

    def minutes(self):
        return self.minutes_edit.value()

    def name(self):
        return self.name_edit.text().strip()


class TickTrayApp:
    def __init__(self):
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.config = config.load_config()
        self.apply_language()

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TickTray.App")
        except Exception:
            pass

        self.lock = QLockFile(os.path.join(config.APP_DIR, "TickTray.lock"))
        self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(100):
            QMessageBox.information(None, "TickTray", t("already_running"))
            sys.exit(0)

        self.config["startWithWindows"] = config.get_autostart()
        self.state = IDLE
        self.total_seconds = 0
        self.deadline = 0.0
        self.paused_remaining = 0.0
        self.timer_name = ""
        self.last_angle = None
        self.last_label = None
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
        self.quick_menu = self.menu.addMenu("")
        self.quick_actions = []
        for m in QUICK_MINUTES:
            a = QAction(self.quick_menu)
            a.triggered.connect(lambda _=False, m=m: self.start_timer(m))
            self.quick_menu.addAction(a)
            self.quick_actions.append((a, m))
        self.action_custom = self._action("", self.set_custom_timer)
        self.action_until = self._action("", self.set_timer_until)
        self.menu.addSeparator()
        self.action_pause_resume = self._action("", self.toggle_pause)
        self.action_extend = self._action("", self.add_five_minutes)
        self.action_snooze = self._action("", self.snooze)
        self.action_stop = self._action("", self.stop_timer)
        self.menu.addSeparator()
        self.action_settings = self._action("", self.open_settings)
        self.action_quit = self._action("", self.quit_app)

        self.tray_icon.setContextMenu(self.menu)

    def _action(self, text, slot):
        a = QAction(text, self.menu)
        a.triggered.connect(lambda _=False: slot())
        self.menu.addAction(a)
        return a

    def refresh_ui(self):
        """Sync menu texts/availability, tooltip and icon with the current state."""
        self.action_start_default.setText(t("start_default", m=self.config["defaultMinutes"]))
        self.quick_menu.setTitle(t("quick"))
        for a, m in self.quick_actions:
            a.setText(t("quick_item", m=m))
        self.action_custom.setText(t("custom"))
        self.action_until.setText(t("until"))
        self.action_stop.setText(t("cancel_timer"))
        self.action_extend.setText(t("extend5"))
        self.action_extend.setEnabled(self.state != IDLE)
        self.action_settings.setText(t("settings_menu"))
        self.action_quit.setText(t("quit"))
        self.action_snooze.setText(t("snooze", m=self.config["defaultSnoozeMinutes"]))
        self.action_snooze.setVisible(self.state == FINISHED)
        active = self.state in (RUNNING, PAUSED)
        self.action_pause_resume.setEnabled(active)
        self.action_pause_resume.setText(t("resume") if self.state == PAUSED else t("pause"))
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
        dlg = CustomTimeDialog(self.config["lastCustomMinutes"], self.config["maximumMinutes"])
        dlg.setWindowIcon(self.app_icon)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        minutes = dlg.minutes()
        self.config["lastCustomMinutes"] = minutes
        self.save_quietly()
        self.start_timer(minutes, name=dlg.name())

    def set_timer_until(self):
        dlg = ClockTimeDialog(self.config["defaultMinutes"])
        dlg.setWindowIcon(self.app_icon)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        seconds = QTime.currentTime().secsTo(dlg.time())
        if seconds <= 0:
            seconds += 24 * 3600  # that time already passed today: aim at tomorrow
        if seconds > self.config["maximumMinutes"] * 60:
            QMessageBox.warning(None, "TickTray", t("until_too_long", m=self.config["maximumMinutes"]))
            return
        self.start_timer(0, seconds=seconds, name=dlg.name())

    def start_timer(self, minutes, seconds=None, name=""):
        stop_alarm()
        self.timer_name = name
        self.total_seconds = seconds if seconds is not None else minutes * 60
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

    def add_five_minutes(self):
        """Extend the running/paused timer by 5 minutes, or start a fresh 5-minute one after it finished."""
        if self.state == FINISHED:
            self.start_timer(min(5, self.config["maximumMinutes"]))
            return
        if self.state not in (RUNNING, PAUSED):
            return
        extra = min(300.0, self.config["maximumMinutes"] * 60 - self.remaining())
        if extra <= 0:
            return
        self.total_seconds += extra
        if self.state == RUNNING:
            self.deadline += extra
        else:
            self.paused_remaining += extra
        self.refresh_ui()

    def stop_timer(self):
        stop_alarm()
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
            tip = "\u200e" + shown
            if self.timer_name:
                tip = f"{self.timer_name} {tip}"
            self.tray_icon.setToolTip(tip)
            fraction = rem / self.total_seconds if self.total_seconds else 0
            angle = int(fraction * 360)
            label = icon_label(rem)
            if force or angle != self.last_angle or label != self.last_label:
                self.last_angle = angle
                self.last_label = label
                self.tray_icon.setIcon(render_icon(fraction, show_check=False, text=label))
        elif self.state == FINISHED:
            self.tray_icon.setToolTip(t("tip_done"))
            self.last_angle = None
            self.tray_icon.setIcon(render_icon(0.0, show_check=True))
        else:
            self.tray_icon.setToolTip(t("tip_idle"))
            self.last_angle = None
            self.tray_icon.setIcon(render_icon())

    def on_timer_finished(self):
        if self.config.get("completionSound"):
            play_alarm()
        self.tray_icon.showMessage(
            "TickTray",
            t("notif_named", name=self.timer_name) if self.timer_name else t("notif"),
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
        self.apply_language()
        try:
            config.save_config(self.config)
            config.set_autostart(self.config["startWithWindows"])
        except Exception:
            logging.exception("failed to save settings")
            QMessageBox.warning(None, "TickTray", t("save_failed"))
        self.refresh_ui()

    def save_quietly(self):
        try:
            config.save_config(self.config)
        except Exception:
            logging.exception("failed to save config")

    def apply_language(self):
        i18n.set_language(self.config["language"])
        self.app.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if i18n.is_rtl() else Qt.LayoutDirection.LeftToRight)

    def quit_app(self):
        stop_alarm()
        if self.settings_dialog is not None:
            self.settings_dialog.force_close()
        self.app.quit()

    def run(self):
        code = self.app.exec()
        self.lock.unlock()
        sys.exit(code)


if __name__ == "__main__":
    TickTrayApp().run()
