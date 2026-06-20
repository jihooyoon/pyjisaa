"""PySide6 GUI for pyjisaa — Shopify app event analyzer.

Ported from jisrot/src/app_egui.rs.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from analyzer import analyze_from_gui
from definitions import (
    EXCLUDING_DEFS_OPTION_LIST,
    EXCLUDING_DEFS_OPTION_MS,
    OPTION_CUSTOM,
    PRICING_DEFS_OPTION_LIST,
    PRICING_DEFS_OPTION_SBM,
    data,
    message,
    ui,
)


class MainWindow(QWidget):

    def __init__(self, reset_default: bool = False):
        super().__init__()
        self.setWindowTitle("Jisrot - Shopify Events Anal")

        self.debug_mode = False
        self.case_sensitive_regex = False
        self.event_history_file_list: list[Path] | None = None

        self.selected_pricing_defs_option: dict = PRICING_DEFS_OPTION_SBM
        self.pricing_defs_file: Path | None = None

        self.selected_excluding_defs_option: dict = EXCLUDING_DEFS_OPTION_MS
        self.excluding_defs_file: Path | None = None

        self._settings = QSettings("pyjisaa", "jisrot")
        if not reset_default:
            self._load_state()

        self._build_ui()

        if not reset_default:
            self._apply_loaded_state()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Row 1: Pricing definitions + Excluding definitions
        row1 = QHBoxLayout()
        pricing_layout, self.lbl_pricing_file = self._build_selector_group(
            data.PRICING_DEFS,
            ui.SELECTOR_PRICING_DEFS_ID,
            PRICING_DEFS_OPTION_LIST,
            self.selected_pricing_defs_option,
            self._on_pricing_option_changed,
            self._on_pricing_browse,
        )
        row1.addLayout(pricing_layout)

        excluding_layout, self.lbl_excluding_file = self._build_selector_group(
            data.EXCLUDING_DEFS,
            ui.SELECTOR_EXCLUDING_DEFS_ID,
            EXCLUDING_DEFS_OPTION_LIST,
            self.selected_excluding_defs_option,
            self._on_excluding_option_changed,
            self._on_excluding_browse,
        )
        row1.addLayout(excluding_layout)
        row1.addStretch()
        root.addLayout(row1)

        # Separator
        root.addWidget(QFrame(frameShape=QFrame.HLine))

        # Row 2: File picker + Analyze button
        row2 = QHBoxLayout()
        self.btn_file_picker = QPushButton(ui.BTN_EVENT_FILE_PICKER_LBL)
        self.btn_file_picker.clicked.connect(self._on_file_picker)
        row2.addWidget(self.btn_file_picker)

        self.btn_analyze = QPushButton(ui.BTN_ANALYZE_LBL)
        self.btn_analyze.clicked.connect(self._on_analyze)
        row2.addWidget(self.btn_analyze)

        row2.addStretch()
        root.addLayout(row2)

        self.lbl_event_files = QLabel("")
        self.lbl_event_files.setVisible(False)
        root.addWidget(self.lbl_event_files)

        # Row 3: Checkboxes
        row3 = QHBoxLayout()
        self.chk_debug = QCheckBox(ui.CHECKBOX_DEBUG_MODE_LBL)
        self.chk_debug.setChecked(self.debug_mode)
        self.chk_debug.toggled.connect(self._on_debug_toggled)
        row3.addWidget(self.chk_debug)

        self.chk_case_sensitive = QCheckBox(ui.CHECKBOX_CASE_SENSITIVE_REGEX_LBL)
        self.chk_case_sensitive.setChecked(self.case_sensitive_regex)
        self.chk_case_sensitive.toggled.connect(self._on_case_sensitive_toggled)
        row3.addWidget(self.chk_case_sensitive)
        row3.addStretch()

        root.addLayout(row3)
        root.addStretch()

    def _build_selector_group(
        self, label: str, selector_id: str,
        option_list: list[dict], current_option: dict,
        on_changed, on_browse,
    ) -> tuple[QVBoxLayout, QLabel]:
        group = QVBoxLayout()
        group.addWidget(QLabel(label))

        row = QHBoxLayout()
        combo = QComboBox()
        combo.setObjectName(selector_id)
        for opt in option_list:
            combo.addItem(opt["text"], opt["value"])
        combo.addItem(OPTION_CUSTOM["text"], OPTION_CUSTOM["value"])
        idx = combo.findData(current_option["value"])
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentIndexChanged.connect(on_changed)
        row.addWidget(combo)

        btn_browse = QPushButton(ui.BTN_BROWSE_LBL)
        btn_browse.setObjectName(f"{selector_id}_browse")
        btn_browse.setEnabled(current_option["value"] == OPTION_CUSTOM["value"])
        btn_browse.clicked.connect(on_browse)
        row.addWidget(btn_browse)

        group.addLayout(row)

        file_label = QLabel("")
        file_label.setVisible(False)
        group.addWidget(file_label)
        return group, file_label

    # ── Event handlers ─────────────────────────────────────────────

    def _sync_help_labels(self) -> None:
        """Show help labels only if at least one has text (keeps layout balanced)."""
        has_text = bool(self.lbl_pricing_file.text()) or bool(self.lbl_excluding_file.text())
        self.lbl_pricing_file.setVisible(has_text)
        self.lbl_excluding_file.setVisible(has_text)

    def _on_pricing_option_changed(self, index: int) -> None:
        combo = self.findChild(QComboBox, ui.SELECTOR_PRICING_DEFS_ID)
        if not combo:
            return
        value = combo.itemData(index)
        for opt in PRICING_DEFS_OPTION_LIST:
            if opt["value"] == value:
                self.selected_pricing_defs_option = opt
                break
        else:
            self.selected_pricing_defs_option = OPTION_CUSTOM

        btn = self.findChild(QPushButton, f"{ui.SELECTOR_PRICING_DEFS_ID}_browse")
        if btn:
            btn.setEnabled(value == OPTION_CUSTOM["value"])
        if value != OPTION_CUSTOM["value"]:
            self.pricing_defs_file = None
            self.lbl_pricing_file.setText("")
            self._sync_help_labels()
        self._save_state()

    def _on_excluding_option_changed(self, index: int) -> None:
        combo = self.findChild(QComboBox, ui.SELECTOR_EXCLUDING_DEFS_ID)
        if not combo:
            return
        value = combo.itemData(index)
        for opt in EXCLUDING_DEFS_OPTION_LIST:
            if opt["value"] == value:
                self.selected_excluding_defs_option = opt
                break
        else:
            self.selected_excluding_defs_option = OPTION_CUSTOM

        btn = self.findChild(QPushButton, f"{ui.SELECTOR_EXCLUDING_DEFS_ID}_browse")
        if btn:
            btn.setEnabled(value == OPTION_CUSTOM["value"])
        if value != OPTION_CUSTOM["value"]:
            self.excluding_defs_file = None
            self.lbl_excluding_file.setText("")
            self._sync_help_labels()
        self._save_state()

    def _on_pricing_browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {data.PRICING_DEFS} file",
            "", "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.pricing_defs_file = Path(file_path)
            self.lbl_pricing_file.setText(self.pricing_defs_file.name)
            self._sync_help_labels()
            self._save_state()

    def _on_excluding_browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {data.EXCLUDING_DEFS} file",
            "", "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.excluding_defs_file = Path(file_path)
            self.lbl_excluding_file.setText(self.excluding_defs_file.name)
            self._sync_help_labels()
            self._save_state()

    def _on_file_picker(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select event history CSV file(s)",
            "", "CSV Files (*.csv);;All Files (*)",
        )
        if files:
            self.event_history_file_list = [Path(f) for f in files]
            names = ", ".join(Path(f).name for f in files)
            self.lbl_event_files.setText(names)
            self.lbl_event_files.setVisible(True)
            self._save_state()

    def _on_analyze(self) -> None:
        try:
            result = analyze_from_gui(
                self.event_history_file_list,
                self.selected_pricing_defs_option,
                self.selected_excluding_defs_option,
                self.pricing_defs_file,
                self.excluding_defs_file,
                self.debug_mode,
                self.case_sensitive_regex,
            )
            QMessageBox.information(self, "Success", result)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_debug_toggled(self, checked: bool) -> None:
        self.debug_mode = checked
        self._save_state()

    def _on_case_sensitive_toggled(self, checked: bool) -> None:
        self.case_sensitive_regex = checked
        self._save_state()

    # ── State persistence ──────────────────────────────────────────

    def _save_state(self) -> None:
        s = self._settings
        s.setValue("debug_mode", self.debug_mode)
        s.setValue("case_sensitive_regex", self.case_sensitive_regex)
        s.setValue("selected_pricing_defs_value",
                   self.selected_pricing_defs_option["value"])
        s.setValue("pricing_defs_file",
                   str(self.pricing_defs_file) if self.pricing_defs_file else "")
        s.setValue("selected_excluding_defs_value",
                   self.selected_excluding_defs_option["value"])
        s.setValue("excluding_defs_file",
                   str(self.excluding_defs_file) if self.excluding_defs_file else "")
        if self.event_history_file_list:
            s.setValue("event_history_files",
                       json.dumps([str(p) for p in self.event_history_file_list]))

    def _load_state(self) -> None:
        """Load persisted values into instance variables (no widget access)."""
        s = self._settings
        self.debug_mode = s.value("debug_mode", False, type=bool)
        self.case_sensitive_regex = s.value("case_sensitive_regex", False, type=bool)

        v = s.value("selected_pricing_defs_value", "")
        if v:
            for opt in PRICING_DEFS_OPTION_LIST:
                if opt["value"] == v:
                    self.selected_pricing_defs_option = opt
                    break
            else:
                self.selected_pricing_defs_option = OPTION_CUSTOM

        pf = s.value("pricing_defs_file", "")
        self.pricing_defs_file = Path(pf) if pf else None

        v = s.value("selected_excluding_defs_value", "")
        if v:
            for opt in EXCLUDING_DEFS_OPTION_LIST:
                if opt["value"] == v:
                    self.selected_excluding_defs_option = opt
                    break
            else:
                self.selected_excluding_defs_option = OPTION_CUSTOM

        ef = s.value("excluding_defs_file", "")
        self.excluding_defs_file = Path(ef) if ef else None

        fj = s.value("event_history_files", "")
        if fj:
            try:
                self.event_history_file_list = [Path(p) for p in json.loads(fj)]
            except (json.JSONDecodeError, TypeError):
                pass

    def _apply_loaded_state(self) -> None:
        """Apply loaded values to widgets (called after _build_ui)."""
        if self.pricing_defs_file:
            self.lbl_pricing_file.setText(self.pricing_defs_file.name)
        if self.excluding_defs_file:
            self.lbl_excluding_file.setText(self.excluding_defs_file.name)
        self._sync_help_labels()
        if self.event_history_file_list:
            names = ", ".join(p.name for p in self.event_history_file_list)
            self.lbl_event_files.setText(names)
            self.lbl_event_files.setVisible(True)

    def closeEvent(self, event) -> None:
        self._save_state()
        super().closeEvent(event)


def run(reset_default: bool = False) -> None:
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName("Jisrot")
    app.setOrganizationName("pyjisaa")

    icon_path = Path(__file__).parent / "ass" / "icon" / "icon256.png"
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(reset_default=reset_default)
    window.show()

    sys.exit(app.exec())
