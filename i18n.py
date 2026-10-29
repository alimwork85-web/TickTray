"""Arabic / English UI strings. Numbers stay Western digits (0-9) in both languages."""

LANGS = ("ar", "en")
_lang = "ar"

STRINGS = {
    "tip_idle": ("TickTray - متوقف", "TickTray - Idle"),
    "tip_done": ("TickTray - انتهى الوقت!", "TickTray - Time's up!"),
    "start_default": ("بدء العداد ({mm})", "Start timer ({mm})"),
    "quick": ("أوقات سريعة", "Quick times"),
    "quick_item": ("{mm}", "{mm}"),
    "custom": ("تحديد وقت مخصص...", "Custom time..."),
    "until": ("حتى الساعة...", "Until a time..."),
    "until_title": ("المؤقت حتى الساعة", "Timer until a time"),
    "until_label": ("الوقت (24 ساعة):", "Time (24-hour):"),
    "until_too_long": ("المدة تتجاوز الحد الأقصى ({mm}).", "Longer than the maximum duration ({mm})."),
    "pause": ("إيقاف مؤقت", "Pause"),
    "resume": ("استئناف", "Resume"),
    "extend5": ("إضافة 5 دقائق", "+5 min"),
    "snooze": ("تأجيل ({mm})", "Snooze ({mm})"),
    "cancel_timer": ("إلغاء العداد", "Cancel timer"),
    "settings_menu": ("الإعدادات...", "Settings..."),
    "quit": ("خروج", "Quit"),
    "custom_title": ("ضبط العداد المخصص", "Custom timer"),
    "custom_label": ("أدخل عدد الدقائق:", "Minutes:"),
    "name_label": ("الاسم (اختياري)", "Name (optional)"),
    "notif": ("⏱ انتهى وقت العداد التنازلي! انقر هنا للتأجيل.", "⏱ Time's up! Click here to snooze."),
    "notif_named": ("⏱ انتهى وقت «{name}»! انقر هنا للتأجيل.", "⏱ {name} is done! Click here to snooze."),
    "already_running": ("TickTray يعمل بالفعل في صينية النظام.", "TickTray is already running in the system tray."),
    "save_failed": ("تعذّر حفظ الإعدادات.", "Could not save the settings."),
    "error_msg": ("حدث خطأ أثناء التشغيل:", "An error occurred:"),
    # settings window
    "win_title": ("إعدادات TickTray", "TickTray Settings"),
    "s_title": ("الإعدادات", "Settings"),
    "s_sub": ("اضبط سلوك العداد كما يناسبك", "Tune the timer to your liking"),
    "s_default": ("المدة الافتراضية", "Default duration"),
    "s_default_h": ("تُستخدم عند بدء العداد بنقرة", "Used when you start with one click"),
    "s_snooze": ("مدة التأجيل", "Snooze length"),
    "s_snooze_h": ("بعد انتهاء الوقت", "After time is up"),
    "s_max": ("الحد الأقصى", "Maximum duration"),
    "s_max_h": ("أعلى مدة يمكن ضبطها", "The longest timer you can set"),
    "s_sound": ("صوت التنبيه", "Alert sound"),
    "s_sound_h": ("نغمة عند انتهاء الوقت", "A tone when time is up"),
    "s_auto": ("التشغيل مع Windows", "Start with Windows"),
    "s_auto_h": ("يبدأ تلقائياً عند تسجيل الدخول", "Launches automatically at sign-in"),
    "s_lang": ("اللغة / Language", "Language / اللغة"),
    "s_lang_h": ("لغة القوائم والنوافذ", "Language of menus and windows"),
    "save": ("حفظ", "Save"),
    "cancel": ("إلغاء", "Cancel"),
    "ok": ("موافق", "OK"),
    "min_suffix": (" د", " min"),
}


def set_language(lang):
    global _lang
    _lang = lang if lang in LANGS else "ar"


def current():
    return _lang


def is_rtl():
    return _lang == "ar"


def minutes_text(n):
    """A number of minutes with the right Arabic form: '5 دقائق', '20 دقيقة', 'دقيقتين'."""
    n = int(n)
    if _lang == "en":
        return f"{n} min"
    if n == 1:
        return "دقيقة واحدة"
    if n == 2:
        return "دقيقتين"
    if 3 <= n <= 10:
        return f"{n} دقائق"
    return f"{n} دقيقة"


def t(key, **fmt):
    ar, en = STRINGS[key]
    text = ar if _lang == "ar" else en
    return text.format(**fmt) if fmt else text
