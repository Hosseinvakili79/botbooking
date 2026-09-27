import os
import queue
import threading
import logging

import PySide6
from PySide6.QtCore import QEvent, QTimer, Qt, Signal, QSize, qVersion
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from .capability_service import detect_capabilities
from .clock_service import CorrectedClock
from .input_backend import UnsupportedInputBackend
from .models import AppSettings, TimeOfDay
from .ntp_service import query_ntp
from .portals.global_shortcuts import GlobalShortcutService
from .portals.remote_desktop import RemoteDesktopBackend
from .scheduler_service import SchedulerService
from .settings_service import SettingsService


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    log_signal = Signal(str)
    ntp_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sarkhati Bourse Dackeh Version 4.1")
        self.settings_service = SettingsService()
        self.settings = self.settings_service.load()
        self.clock = CorrectedClock()
        self.capabilities = detect_capabilities()
        self.log_queue = queue.Queue()
        self.capture_mode = False
        self.setMinimumSize(520, 360)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.resize(QSize(min(1100, max(520, available.width() - 48)),
                              min(760, max(360, available.height() - 96))))
        else:
            self.resize(1100, 760)
        self._build_ui()
        self._setup_services()
        self.installEventFilter(self)
        self.log_signal.connect(self._append_log)
        self.ntp_signal.connect(self._apply_ntp_result)
        self.log("Application startup.")
        self.log(f"Platform detected: {self.capabilities.session_type} / {self.capabilities.desktop}.")
        self.log("Global shortcut: F6 registered." if self.shortcut else "Global shortcut unavailable.")
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(33)
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self._drain_logs)
        self.log_timer.start(50)

    def _log_ui_diagnostics(self):
        app = QGuiApplication.instance()
        screen = self.screen() or QGuiApplication.primaryScreen()
        logger.info("Qt=%s PySide6=%s platform=%s session=%s desktop=%s",
                    qVersion(), PySide6.__version__, app.platformName() if app else "none",
                    self.capabilities.session_type, self.capabilities.desktop)
        if screen is not None:
            logger.info("Screen=%s available=%s dpr=%s logicalDpi=%s",
                        screen.geometry().getRect(), screen.availableGeometry().getRect(),
                        screen.devicePixelRatio(), screen.logicalDotsPerInch())
        logger.info("MainWindow visible=%s size=%s central=%s",
                    self.isVisible(), self.size().toTuple(), self.centralWidget().size().toTuple())
        for name in ("start_fields", "end_fields"):
            for index, widget in enumerate(getattr(self, name)):
                logger.info("Widget %s[%d] objectName=%s visible=%s enabled=%s size=%s geometry=%s parent=%s",
                            name, index, widget.objectName(), widget.isVisible(), widget.isEnabled(),
                            widget.size().toTuple(), widget.geometry().getRect(),
                                type(widget.parentWidget()).__name__)
        for name in ("interval", "limit", "button_combo", "type_combo", "x_field", "y_field",
                     "ntp_server", "start_button", "stop_button", "log_view"):
            widget = getattr(self, name)
            logger.info("Widget %s objectName=%s visible=%s enabled=%s size=%s geometry=%s parent=%s",
                        name, widget.objectName(), widget.isVisible(), widget.isEnabled(),
                        widget.size().toTuple(), widget.geometry().getRect(),
                        type(widget.parentWidget()).__name__)

    def _setup_services(self):
        self.input = RemoteDesktopBackend() if self.capabilities.remote_desktop else UnsupportedInputBackend()
        self.scheduler = SchedulerService(self.clock, self.input, self.log)
        self.shortcut = None
        if self.capabilities.global_shortcuts:
            try:
                self.shortcut = GlobalShortcutService(self.toggle_scheduler)
                self.shortcut.start()
            except Exception as exc:
                self.log(f"Global shortcut registration failed: {exc}.")
                self.shortcut = None

    def _card(self, title):
        return QGroupBox(title)

    def _control_policy(self, control):
        control.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return control

    def _row(self, label, control):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        label_widget = QLabel(label)
        label_widget.setWordWrap(True)
        label_widget.setMinimumWidth(0)
        label_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(label_widget)
        row.setStretch(0, 1)
        row.addWidget(control, 1)
        return row

    def _spin(self, value, minimum, maximum):
        control = QSpinBox()
        control.setRange(minimum, maximum)
        control.setValue(value)
        return self._control_policy(control)

    def _build_ui(self):
        root = QWidget()
        root.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        heading = QLabel("Sarkhati Bourse Dackeh 4.1")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        columns = QGridLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        left, right = QVBoxLayout(), QVBoxLayout()
        columns.addLayout(left, 0, 0)
        columns.addLayout(right, 0, 1)
        columns.setHorizontalSpacing(10)
        columns.setVerticalSpacing(10)
        columns.setColumnStretch(0, 1)
        columns.setColumnStretch(1, 1)
        left.setSpacing(6)
        right.setSpacing(6)
        layout.addLayout(columns)
        self._build_timing(left)
        self._build_click(left)
        self._build_ntp(left)
        self._build_controls(left)
        self._build_location(right)
        self._build_log(right)
        self._build_guide(right)
        scroll = QScrollArea()
        scroll.setObjectName("mainScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)

    def _build_timing(self, parent):
        box = self._card("Timing Settings")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        headings = QHBoxLayout()
        headings.setContentsMargins(8, 8, 8, 8)
        headings.setSpacing(6)
        for column, title in enumerate(("Hour", "Min", "Sec", "Ms")):
            heading = QLabel(title)
            heading.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            headings.addWidget(heading, 1)
        layout.addLayout(headings)
        start = self.settings.timing.start
        end = self.settings.timing.end
        self.start_fields = [self._spin(v, 0, maxv) for v, maxv in zip((start.hour, start.minute, start.second, start.millisecond), (23, 59, 59, 999))]
        self.end_fields = [self._spin(v, 0, maxv) for v, maxv in zip((end.hour, end.minute, end.second, end.millisecond), (23, 59, 59, 999))]
        for index, field in enumerate(self.start_fields): field.setObjectName(f"startField{index}")
        for index, field in enumerate(self.end_fields): field.setObjectName(f"endField{index}")
        start_row = QHBoxLayout()
        start_row.setContentsMargins(8, 8, 8, 8)
        start_row.setSpacing(6)
        for field in self.start_fields:
            start_row.addWidget(field, 1)
        layout.addLayout(start_row)
        end_label = QLabel("End Hour")
        end_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        layout.addWidget(end_label)
        end_row = QHBoxLayout()
        end_row.setContentsMargins(8, 8, 8, 8)
        end_row.setSpacing(6)
        for field in self.end_fields:
            end_row.addWidget(field, 1)
        layout.addLayout(end_row)
        self.interval = self._spin(self.settings.timing.interval_ms, 1, 2_147_483_647)
        self.interval.setObjectName("clickInterval")
        self.limit = self._spin(self.settings.timing.click_limit, 0, 2_147_483_647)
        self.limit.setObjectName("clickLimit")
        layout.addLayout(self._row("Interval (ms)", self.interval))
        layout.addLayout(self._row("Stop After N Clicks (0 = unlimited)", self.limit))
        parent.addWidget(box)

    def _build_click(self, parent):
        box = self._card("Click Settings")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.button_combo = self._control_policy(QComboBox()); self.button_combo.setObjectName("mouseButton"); self.button_combo.addItems(["Left", "Right"]); self.button_combo.setCurrentText(self.settings.button)
        self.type_combo = self._control_policy(QComboBox()); self.type_combo.setObjectName("clickType"); self.type_combo.addItems(["Single", "Double"]); self.type_combo.setCurrentText(self.settings.click_type)
        layout.addLayout(self._row("Button", self.button_combo))
        layout.addLayout(self._row("Type", self.type_combo))
        parent.addWidget(box)

    def _build_ntp(self, parent):
        box = self._card("Online Atomic Clock (NTP)")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.ntp_server = self._control_policy(QLineEdit(self.settings.ntp_server)); self.ntp_server.setObjectName("ntpServer")
        self.offset = self._control_policy(QLineEdit("0")); self.offset.setObjectName("ntpOffset"); self.offset.setReadOnly(True)
        self.adjustment = self._control_policy(QSpinBox()); self.adjustment.setObjectName("ntpAdjustment"); self.adjustment.setRange(-2_147_483_648, 2_147_483_647); self.adjustment.setValue(self.settings.user_adjustment_ms)
        self.digital_clock = QLabel("--:--:--.---")
        self.digital_clock.setObjectName("digitalClock")
        sync = self._control_policy(QPushButton("Sync with NTP")); sync.setObjectName("syncNtpButton"); sync.clicked.connect(self.sync_ntp)
        layout.addLayout(self._row("NTP Server", self.ntp_server))
        layout.addLayout(self._row("NTP Calculated Offset (ms)", self.offset))
        layout.addLayout(self._row("User Adjustment (ms)", self.adjustment))
        layout.addLayout(self._row("Digital clock", self.digital_clock))
        layout.addWidget(sync)
        parent.addWidget(box)

    def _build_controls(self, parent):
        box = self._card("Controls")
        row = QHBoxLayout(box)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(6)
        self.start_button = QPushButton("Start (F6)"); self.start_button.setObjectName("startButton")
        self.start_button.setProperty("role", "primary")
        self.stop_button = QPushButton("Stop (F6)"); self.stop_button.setObjectName("stopButton")
        self.stop_button.setProperty("role", "danger")
        self.stop_button.setEnabled(False)
        for button in (self.start_button, self.stop_button):
            self._control_policy(button)
            button.setMinimumHeight(30)
        self.start_button.clicked.connect(self.start_scheduler); self.stop_button.clicked.connect(self.stop_scheduler)
        row.addWidget(self.start_button, 1)
        row.addWidget(self.stop_button, 1)
        parent.addWidget(box)

    def _build_location(self, parent):
        box = self._card("Sarkhati Location")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.x_field = self._control_policy(QSpinBox()); self.x_field.setObjectName("xCoordinate"); self.x_field.setRange(0, 100000); self.x_field.setValue(self.settings.x)
        self.y_field = self._control_policy(QSpinBox()); self.y_field.setObjectName("yCoordinate"); self.y_field.setRange(0, 100000); self.y_field.setValue(self.settings.y)
        capture = self._control_policy(QPushButton("Get X/Y (Press SPACE)")); capture.setObjectName("captureCoordinatesButton"); capture.clicked.connect(self.begin_capture)
        layout.addLayout(self._row("X", self.x_field))
        layout.addLayout(self._row("Y", self.y_field))
        layout.addWidget(capture)
        parent.addWidget(box)

    def _build_log(self, parent):
        box = self._card("Activity Log")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        self.log_view = QPlainTextEdit(); self.log_view.setObjectName("activityLog")
        self.log_view.setReadOnly(True)
        self.log_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.log_view, 1)
        parent.addWidget(box, 1)

    def _build_guide(self, parent):
        box = self._card("Keyboard Shortcuts Guide")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel("F6: Toggle Start/Stop Clicking\n\nGet X/Y button then SPACE: Capture Current Cursor Position\n\nESC: Cancel X/Y Capture Mode")
        label.setWordWrap(True)
        layout.addWidget(label)
        parent.addWidget(box)

    def log(self, message):
        self.log_queue.put(f"[{self.clock.now().strftime('%H:%M:%S.%f')[:-3]}] {message}")

    def _drain_logs(self):
        while True:
            try: self.log_signal.emit(self.log_queue.get_nowait())
            except queue.Empty: return

    def _append_log(self, message):
        self.log_view.appendPlainText(message)

    def _update_clock(self):
        self.digital_clock.setText(self.clock.now().strftime("%H:%M:%S.%f")[:-3])
        if not self.scheduler.running and not self.start_button.isEnabled(): self._set_running(False)

    def _timing(self):
        vals = [field.value() for field in self.start_fields]; start = TimeOfDay(*vals)
        vals = [field.value() for field in self.end_fields]; end = TimeOfDay(*vals)
        from .models import TimingSettings
        return TimingSettings(start, end, self.interval.value(), self.limit.value())

    def start_scheduler(self):
        try:
            if not self.capabilities.remote_desktop: raise RuntimeError("RemoteDesktop portal is unavailable")
            self.scheduler.start(self._timing(), self.x_field.value(), self.y_field.value(), self.button_combo.currentText(), self.type_combo.currentText())
            self._set_running(True)
        except Exception as exc: QMessageBox.warning(self, "Cannot start", str(exc)); self.log(f"Scheduler start failed: {exc}.")

    def stop_scheduler(self): self.scheduler.stop(); self._set_running(False)
    def toggle_scheduler(self): self.stop_scheduler() if self.scheduler.running else self.start_scheduler()

    def _set_running(self, running):
        self.start_button.setEnabled(not running); self.stop_button.setEnabled(running)
        for widget in self.start_fields + self.end_fields + [self.interval, self.limit, self.x_field, self.y_field, self.button_combo, self.type_combo]: widget.setEnabled(not running)

    def begin_capture(self):
        self.capture_mode = True; self.log("Coordinate capture started.")
        if not self.capabilities.cursor_position: self.log("Global cursor coordinates are not available through the current Wayland session.")

    def eventFilter(self, watched, event):
        if self.capture_mode and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape: self.capture_mode = False; self.log("Coordinate capture cancelled."); return True
            if event.key() == Qt.Key_Space:
                self.capture_mode = False; self.log("Global cursor coordinates are not available through the current Wayland session."); return True
        return super().eventFilter(watched, event)

    def sync_ntp(self):
        self.log("NTP sync started.")
        server = self.ntp_server.text().strip()
        def worker():
            try:
                result = query_ntp(server)
                self.clock.ntp_offset_ms = result.offset_ms
                self.ntp_signal.emit(f"{result.offset_ms:.3f}", f"NTP sync completed: {result.offset_ms:+.3f}ms offset, {result.round_trip_ms:.3f}ms round trip.")
            except Exception as exc: self.log(f"NTP sync failed: {exc}.")
        threading.Thread(target=worker, daemon=True).start()

    def _apply_ntp_result(self, offset, message):
        self.offset.setText(offset)
        self.log(message)

    def closeEvent(self, event):
        self.scheduler.stop("application closing") if self.scheduler.running else None
        if self.shortcut: self.shortcut.stop()
        self.settings = AppSettings(self._timing(), self.x_field.value(), self.y_field.value(), self.button_combo.currentText(), self.type_combo.currentText(), self.ntp_server.text(), self.adjustment.value())
        self.settings_service.save(self.settings)
        event.accept()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication([])
    app.setStyle("Fusion")
    app_font = QFont("DejaVu Sans")
    app_font.setPointSize(10)
    app.setFont(app_font)
    app.setStyleSheet("""
        QMainWindow { background: #f4f6f8; }
        QGroupBox {
            font-weight: 600;
            border: 1px solid #c7ced8;
            border-radius: 5px;
            margin-top: 10px;
            padding: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QLabel#heading {
            color: #19324d;
            font-size: 22px;
            font-weight: 700;
            padding: 4px 0 8px;
        }
        QLabel#digitalClock {
            color: #1d5d7a;
            font-size: 20px;
            font-weight: 700;
        }
        QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {
            background: white;
            border: 1px solid #b9c2cc;
            padding: 4px;
        }
        QPushButton {
            min-height: 28px;
            padding: 4px 8px;
        }
        QPushButton[role="primary"] {
            background: #1976d2;
            color: white;
            font-weight: 600;
        }
        QPushButton[role="danger"] {
            background: #c62828;
            color: white;
            font-weight: 600;
        }
    """)
    try:
        window = MainWindow()
        window.show()
        app.processEvents()
        window._log_ui_diagnostics()
        logger.info("Application window shown")
        app.exec()
    except Exception:
        logger.exception("GUI initialization failed")
        raise


if __name__ == "__main__": main()
