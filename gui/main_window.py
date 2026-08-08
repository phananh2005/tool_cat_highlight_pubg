"""Main GUI window — video player (OpenCV-based), timeline, highlight list, export controls.

Dùng OpenCV VideoCapture + QLabel thay vì QMediaPlayer vì PyQt6 trên pip
không bao gồm QtMultimedia (cần Qt build riêng).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLabel, QFileDialog,
    QProgressBar, QStatusBar, QSlider,
    QDoubleSpinBox, QLineEdit, QCheckBox, QMessageBox,
    QGroupBox, QFormLayout, QDialog, QDialogButtonBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QImage, QPixmap, QFont, QColor

from core.models import Project, Match, Highlight
from core.match_detector import detect_matches
from core.highlight_detector import detect_highlights
from core.video_processor import export_highlights
from gui.timeline_widget import TimelineWidget
from config import load_config, save_config


# ---------------------------------------------------------------------------
# Simple OpenCV-based video player widget
# ---------------------------------------------------------------------------

class VideoPlayer(QWidget):
    """Video player dùng OpenCV + QLabel + QTimer."""

    position_changed = pyqtSignal(float)  # seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cap = None  # cv2.VideoCapture, lazy import
        self._fps: float = 30.0
        self._total_frames: int = 0
        self._current_frame: int = 0
        self._playing: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video display
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setMinimumSize(640, 360)
        self._display.setStyleSheet("background-color: #000;")
        layout.addWidget(self._display, stretch=1)

        # Seek slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.sliderMoved.connect(self._on_slider_moved)
        layout.addWidget(self._slider)

        # Playback timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._read_frame)

        self._slider_dragging = False

    # --- Public API ---

    def open(self, path: str):
        import cv2
        if self._cap:
            self._cap.release()
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            QMessageBox.critical(self, "Lỗi", f"Không mở được video:\n{path}")
            return
        self._fps = self._cap.get(5) or 30.0  # CAP_PROP_FPS
        self._total_frames = int(self._cap.get(4))  # CAP_PROP_FRAME_COUNT
        self._slider.setRange(0, self._total_frames - 1)
        self._current_frame = 0
        self._read_frame()

    @property
    def duration(self) -> float:
        return self._total_frames / max(self._fps, 1)

    @property
    def position(self) -> float:
        return self._current_frame / max(self._fps, 1)

    def play(self):
        if not self._cap:
            return
        self._playing = True
        self._timer.start(int(1000 / self._fps))

    def pause(self):
        self._playing = False
        self._timer.stop()

    def is_playing(self) -> bool:
        return self._playing

    def seek(self, time_sec: float):
        if not self._cap:
            return
        frame = int(time_sec * self._fps)
        frame = max(0, min(frame, self._total_frames - 1))
        self._cap.set(1, frame)  # CAP_PROP_POS_FRAMES
        self._current_frame = frame
        self._read_frame()

    def seek_relative(self, delta_sec: float):
        self.seek(self.position + delta_sec)

    # --- Internal ---

    def _read_frame(self):
        if not self._cap:
            return
        ok, frame = self._cap.read()
        if not ok:
            self.pause()
            return

        self._current_frame = int(self._cap.get(1))  # CAP_PROP_POS_FRAMES

        # Convert BGR → RGB → QImage → QPixmap
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)

        # Scale to fit display
        scaled = QPixmap.fromImage(qimg).scaled(
            self._display.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._display.setPixmap(scaled)

        # Update slider (only if not dragging)
        if not self._slider_dragging:
            self._slider.setValue(self._current_frame)

        self.position_changed.emit(self.position)

    def _on_slider_pressed(self):
        self._slider_dragging = True

    def _on_slider_released(self):
        self._slider_dragging = False
        frame = self._slider.value()
        if self._cap:
            self._cap.set(1, frame)  # CAP_PROP_POS_FRAMES
            self._current_frame = frame
            self._read_frame()

    def _on_slider_moved(self, value: int):
        if self._cap:
            self._cap.set(1, value)  # CAP_PROP_POS_FRAMES
            self._current_frame = value
            self._read_frame()

    def closeEvent(self, event):
        self.pause()
        if self._cap:
            self._cap.release()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class DetectWorker(QThread):
    progress = pyqtSignal(float, str)
    finished_matches = pyqtSignal(list)
    finished_highlights = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, video_path: str, templates_dir: str, config: dict):
        super().__init__()
        self.video_path = video_path
        self.templates_dir = templates_dir
        self.config = config

    def run(self):
        try:
            self.progress.emit(0.0, "Đang detect match boundaries...")
            matches = detect_matches(
                self.video_path,
                self.templates_dir,
                sample_interval=self.config["frame_sample_interval"],
                threshold=self.config["template_match_threshold"],
                progress_cb=lambda p: self.progress.emit(p * 0.4, "Detecting matches..."),
            )
            self.finished_matches.emit(matches)

            self.progress.emit(0.4, "Đang detect highlights...")
            highlights = detect_highlights(
                self.video_path,
                matches,
                player_name=self.config.get("player_name", ""),
                config=self.config,
                progress_cb=lambda p, s: self.progress.emit(0.4 + p * 0.6, s),
            )
            self.finished_highlights.emit(highlights)
        except Exception as e:
            self.error.emit(str(e))


class ExportWorker(QThread):
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, source: str, highlights: list[Highlight],
                 output_dir: str, group_label: str, ffmpeg: str,
                 accurate: bool, merge: bool):
        super().__init__()
        self.source = source
        self.highlights = highlights
        self.output_dir = output_dir
        self.group_label = group_label
        self.ffmpeg = ffmpeg
        self.accurate = accurate
        self.merge = merge

    def run(self):
        try:
            files = export_highlights(
                self.source, self.highlights, self.output_dir,
                self.group_label, self.ffmpeg, self.accurate, self.merge,
                progress_cb=lambda p, s: self.progress.emit(p, s),
            )
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PUBG Highlight Cutter")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)

        self.cfg = load_config()
        self.project: Optional[Project] = None
        self._worker: Optional[DetectWorker] = None
        self._export_worker: Optional[ExportWorker] = None

        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

        self.setStyleSheet(self._build_stylesheet())

    # === UI Setup ===

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Top splitter: video | highlight list
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: video player
        video_container = QWidget()
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.video_player = VideoPlayer()
        video_layout.addWidget(self.video_player, stretch=1)

        # Player controls
        ctrl_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_back5 = QPushButton("⏪ 5s")
        self.btn_fwd5 = QPushButton("5s ⏩")
        self.lbl_time = QLabel("00:00:00 / 00:00:00")
        self.lbl_time.setFont(QFont("Consolas", 10))
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_back5)
        ctrl_layout.addWidget(self.btn_fwd5)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.lbl_time)
        video_layout.addLayout(ctrl_layout)

        splitter.addWidget(video_container)

        # Right: highlight list + controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("📋 Highlights")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        right_layout.addWidget(lbl)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Tên", "Bắt đầu", "Kết thúc", "Loại", "Conf"])
        self.tree.setColumnWidth(0, 160)
        self.tree.setColumnWidth(1, 70)
        self.tree.setColumnWidth(2, 70)
        self.tree.setColumnWidth(3, 80)
        self.tree.setColumnWidth(4, 45)
        self.tree.setAlternatingRowColors(True)
        right_layout.addWidget(self.tree, stretch=1)

        # Highlight action buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("➕ Thêm")
        self.btn_edit = QPushButton("✏️ Sửa")
        self.btn_delete = QPushButton("🗑️ Xóa")
        self.btn_toggle = QPushButton("👁️ Bật/Tắt")
        for b in [self.btn_add, self.btn_edit, self.btn_delete, self.btn_toggle]:
            btn_row.addWidget(b)
        right_layout.addLayout(btn_row)

        # Export buttons
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)
        self.chk_merge = QCheckBox("Gộp thành 1 video mỗi game")
        self.chk_merge.setChecked(True)
        self.chk_accurate = QCheckBox("Accurate cut (re-encode, chậm hơn)")
        export_layout.addWidget(self.chk_merge)
        export_layout.addWidget(self.chk_accurate)

        export_btn_row = QHBoxLayout()
        self.btn_export_selected = QPushButton("📦 Export game đang chọn")
        self.btn_export_all = QPushButton("📦 Export tất cả")
        export_btn_row.addWidget(self.btn_export_selected)
        export_btn_row.addWidget(self.btn_export_all)
        export_layout.addLayout(export_btn_row)
        right_layout.addWidget(export_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([750, 450])
        main_layout.addWidget(splitter, stretch=1)

        # Timeline
        self.timeline = TimelineWidget()
        main_layout.addWidget(self.timeline)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setTextVisible(True)
        main_layout.addWidget(self.progress)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Sẵn sàng. Mở file video để bắt đầu.")

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        act_open = QAction("📂 Mở video...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_video)
        file_menu.addAction(act_open)

        act_open_project = QAction("📁 Mở project...", self)
        act_open_project.setShortcut("Ctrl+Shift+O")
        act_open_project.triggered.connect(self._open_project)
        file_menu.addAction(act_open_project)

        act_save = QAction("💾 Lưu project...", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_project)
        file_menu.addAction(act_save)

        file_menu.addSeparator()
        act_quit = QAction("Thoát", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Detect menu
        detect_menu = menubar.addMenu("&Detect")
        act_detect = QAction("🔍 Chạy Auto Detect", self)
        act_detect.setShortcut("Ctrl+D")
        act_detect.triggered.connect(self._run_detection)
        detect_menu.addAction(act_detect)

        # Settings menu
        settings_menu = menubar.addMenu("&Settings")
        act_settings = QAction("⚙️ Cài đặt...", self)
        act_settings.triggered.connect(self._open_settings)
        settings_menu.addAction(act_settings)

    def _connect_signals(self):
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_back5.clicked.connect(lambda: self.video_player.seek_relative(-5))
        self.btn_fwd5.clicked.connect(lambda: self.video_player.seek_relative(5))

        self.video_player.position_changed.connect(self._on_position_changed)

        self.timeline.seek_requested.connect(self._seek_to)
        self.timeline.highlight_moved.connect(self._on_highlight_moved)

        self.tree.itemClicked.connect(self._on_tree_click)

        self.btn_add.clicked.connect(self._add_highlight)
        self.btn_edit.clicked.connect(self._edit_highlight)
        self.btn_delete.clicked.connect(self._delete_highlight)
        self.btn_toggle.clicked.connect(self._toggle_highlight)

        self.btn_export_selected.clicked.connect(self._export_selected)
        self.btn_export_all.clicked.connect(self._export_all)

    # === Player controls ===

    def _toggle_play(self):
        if self.video_player.is_playing():
            self.video_player.pause()
            self.btn_play.setText("▶")
        else:
            self.video_player.play()
            self.btn_play.setText("⏸")

    def _seek_to(self, time_sec: float):
        self.video_player.seek(time_sec)

    def _on_position_changed(self, pos_sec: float):
        self.timeline.set_position(pos_sec)
        dur = self.video_player.duration
        self.lbl_time.setText(f"{self._fmt_time(pos_sec)} / {self._fmt_time(dur)}")

    @staticmethod
    def _fmt_time(sec: float) -> str:
        s = int(sec)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # === File operations ===

    def _open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Mở file video", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv *.ts);;All Files (*)",
        )
        if not path:
            return

        self.project = Project(source_file=path, player_name=self.cfg.get("player_name", ""))
        self.video_player.open(path)
        self._refresh_tree()
        self.timeline.set_data(self.video_player.duration, [], [])
        self.status.showMessage(f"Đã mở: {Path(path).name}")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Mở project", "",
            "Project Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            self.project = Project.load(path)
            self.video_player.open(self.project.source_file)
            self._refresh_tree()
            self.timeline.set_data(
                self.video_player.duration,
                self.project.matches,
                self.project.highlights,
            )
            self.status.showMessage(f"Đã mở project: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không đọc được project:\n{e}")

    def _save_project(self):
        if not self.project:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu project", "",
            "Project Files (*.json);;All Files (*)",
        )
        if path:
            self.project.save(path)
            self.status.showMessage(f"Đã lưu: {Path(path).name}")

    # === Detection ===

    def _run_detection(self):
        if not self.project:
            QMessageBox.warning(self, "Chưa mở video", "Hãy mở file video trước.")
            return

        templates_dir = str(Path(__file__).parent.parent / "templates")

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status.showMessage("Đang chạy auto detect...")

        self._worker = DetectWorker(self.project.source_file, templates_dir, self.cfg)
        self._worker.progress.connect(self._on_detect_progress)
        self._worker.finished_matches.connect(self._on_matches_detected)
        self._worker.finished_highlights.connect(self._on_highlights_detected)
        self._worker.error.connect(self._on_detect_error)
        self._worker.start()

    @pyqtSlot(float, str)
    def _on_detect_progress(self, value: float, text: str):
        self.progress.setValue(int(value * 100))
        self.progress.setFormat(f"{text} ({int(value * 100)}%)")

    @pyqtSlot(list)
    def _on_matches_detected(self, matches: list):
        if self.project:
            self.project.matches = matches
            self.status.showMessage(f"Detect xong {len(matches)} game(s).")

    @pyqtSlot(list)
    def _on_highlights_detected(self, highlights: list):
        if self.project:
            self.project.highlights = highlights
            self._refresh_tree()
            self.timeline.set_data(
                self.video_player.duration,
                self.project.matches,
                self.project.highlights,
            )
            self.progress.setVisible(False)
            self.status.showMessage(
                f"Hoàn tất: {len(self.project.matches)} game, {len(highlights)} highlight."
            )

    @pyqtSlot(str)
    def _on_detect_error(self, msg: str):
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Lỗi Detection", msg)

    # === Tree view ===

    def _refresh_tree(self):
        self.tree.clear()
        if not self.project:
            return

        for m in self.project.matches:
            match_item = QTreeWidgetItem([
                m.label,
                self._fmt_time(m.start_time),
                self._fmt_time(m.end_time),
                "", "",
            ])
            match_item.setData(0, Qt.ItemDataRole.UserRole, ("match", m.index))
            match_item.setFont(0, QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tree.addTopLevelItem(match_item)

            for hl in self.project.highlights_for_match(m.index):
                label = hl.label or f"{hl.highlight_type}"
                hl_item = QTreeWidgetItem([
                    label,
                    self._fmt_time(hl.start_time),
                    self._fmt_time(hl.end_time),
                    hl.highlight_type,
                    f"{hl.confidence:.0%}",
                ])
                idx = self.project.highlights.index(hl)
                hl_item.setData(0, Qt.ItemDataRole.UserRole, ("highlight", idx))
                if not hl.enabled:
                    for col in range(5):
                        hl_item.setForeground(col, QColor(100, 100, 100))
                match_item.addChild(hl_item)

            match_item.setExpanded(True)

    def _on_tree_click(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, idx = data
        if kind == "match" and self.project:
            m = next((m for m in self.project.matches if m.index == idx), None)
            if m:
                self._seek_to(m.start_time)
        elif kind == "highlight" and self.project:
            hl = self.project.highlights[idx]
            self._seek_to(hl.start_time)

    # === Highlight CRUD ===

    def _get_selected_highlight_idx(self) -> int:
        item = self.tree.currentItem()
        if not item:
            return -1
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] == "highlight":
            return data[1]
        return -1

    def _add_highlight(self):
        if not self.project:
            return
        pos_sec = self.video_player.position
        match_idx = 0
        for m in self.project.matches:
            if m.start_time <= pos_sec <= m.end_time:
                match_idx = m.index
                break

        pad_b = self.cfg["highlight_pad_before"]
        pad_a = self.cfg["highlight_pad_after"]
        hl = Highlight(
            start_time=max(0, pos_sec - pad_b),
            end_time=pos_sec + pad_a,
            confidence=1.0,
            highlight_type="manual",
            match_index=match_idx,
            label="Manual highlight",
        )
        self.project.highlights.append(hl)
        self._refresh_tree()
        self._refresh_timeline()
        self.status.showMessage("Đã thêm highlight thủ công.")

    def _edit_highlight(self):
        idx = self._get_selected_highlight_idx()
        if idx < 0 or not self.project:
            return
        hl = self.project.highlights[idx]
        dlg = HighlightEditDialog(hl, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_tree()
            self._refresh_timeline()

    def _delete_highlight(self):
        idx = self._get_selected_highlight_idx()
        if idx < 0 or not self.project:
            return
        reply = QMessageBox.question(self, "Xác nhận", "Xóa highlight này?")
        if reply == QMessageBox.StandardButton.Yes:
            self.project.highlights.pop(idx)
            self._refresh_tree()
            self._refresh_timeline()

    def _toggle_highlight(self):
        idx = self._get_selected_highlight_idx()
        if idx < 0 or not self.project:
            return
        hl = self.project.highlights[idx]
        hl.enabled = not hl.enabled
        self._refresh_tree()
        self._refresh_timeline()

    def _on_highlight_moved(self, hl_idx: int, new_start: float, new_end: float):
        if not self.project or hl_idx < 0 or hl_idx >= len(self.project.highlights):
            return
        hl = self.project.highlights[hl_idx]
        hl.start_time = new_start
        hl.end_time = new_end
        self._refresh_tree()

    def _refresh_timeline(self):
        if self.project:
            self.timeline.set_data(
                self.video_player.duration,
                self.project.matches,
                self.project.highlights,
            )

    # === Export ===

    def _export_selected(self):
        if not self.project:
            return
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Chọn game", "Hãy chọn 1 game trong danh sách.")
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if data[0] == "highlight":
            parent = item.parent()
            if parent:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
            else:
                return

        match_idx = data[1]
        hls = self.project.highlights_for_match(match_idx)
        if not hls:
            QMessageBox.information(self, "Trống", "Game này không có highlight.")
            return

        self._do_export(hls, f"game_{match_idx + 1}")

    def _export_all(self):
        if not self.project or not self.project.highlights:
            return
        self._do_export(
            [h for h in self.project.highlights if h.enabled],
            "all_highlights",
        )

    def _do_export(self, highlights: list[Highlight], group_label: str):
        output_dir = QFileDialog.getExistingDirectory(self, "Chọn thư mục output")
        if not output_dir:
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)

        self._export_worker = ExportWorker(
            self.project.source_file,
            highlights,
            output_dir,
            group_label,
            self.cfg["ffmpeg_path"],
            self.chk_accurate.isChecked(),
            self.chk_merge.isChecked(),
        )
        self._export_worker.progress.connect(self._on_detect_progress)
        self._export_worker.finished.connect(self._on_export_finished)
        self._export_worker.error.connect(self._on_detect_error)
        self._export_worker.start()

    @pyqtSlot(list)
    def _on_export_finished(self, files: list):
        self.progress.setVisible(False)
        self.status.showMessage(f"Export xong {len(files)} file(s).")
        QMessageBox.information(
            self, "Export hoàn tất",
            f"Đã tạo {len(files)} file:\n" + "\n".join(Path(f).name for f in files[:10]),
        )

    # === Settings dialog ===

    def _open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            save_config(self.cfg)
            self.status.showMessage("Đã lưu cài đặt.")

    # === Stylesheet ===

    @staticmethod
    def _build_stylesheet() -> str:
        return """
        QMainWindow {
            background-color: #1e1e22;
            color: #e0e0e0;
        }
        QMenuBar {
            background-color: #2a2a30;
            color: #e0e0e0;
            border-bottom: 1px solid #3a3a42;
        }
        QMenuBar::item:selected {
            background-color: #3a3a50;
        }
        QMenu {
            background-color: #2a2a30;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
        }
        QMenu::item:selected {
            background-color: #4a4a60;
        }
        QSplitter::handle {
            background-color: #3a3a42;
            width: 2px;
        }
        QTreeWidget {
            background-color: #252528;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            font-size: 12px;
        }
        QTreeWidget::item:selected {
            background-color: #3a4a6a;
        }
        QTreeWidget::item:hover {
            background-color: #303040;
        }
        QTreeWidget QHeaderView::section {
            background-color: #2a2a30;
            color: #a0a0a0;
            border: none;
            padding: 4px;
            font-size: 11px;
        }
        QPushButton {
            background-color: #3a3a50;
            color: #e0e0e0;
            border: 1px solid #4a4a60;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #4a4a68;
            border-color: #6a6a80;
        }
        QPushButton:pressed {
            background-color: #2a2a3a;
        }
        QGroupBox {
            color: #c0c0c0;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
            font-size: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QCheckBox {
            color: #e0e0e0;
            spacing: 6px;
        }
        QProgressBar {
            background-color: #252528;
            border: 1px solid #3a3a42;
            border-radius: 4px;
            text-align: center;
            color: #e0e0e0;
            height: 20px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4a6aaa, stop:1 #6a8acc);
            border-radius: 3px;
        }
        QStatusBar {
            background-color: #2a2a30;
            color: #a0a0a0;
            border-top: 1px solid #3a3a42;
        }
        QLabel {
            color: #e0e0e0;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #252528;
            color: #e0e0e0;
            border: 1px solid #3a3a42;
            border-radius: 3px;
            padding: 4px;
        }
        QSlider::groove:horizontal {
            background: #3a3a42;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #6a8acc;
            width: 14px;
            height: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QSlider::sub-page:horizontal {
            background: #4a6aaa;
            border-radius: 3px;
        }
        """


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------

class HighlightEditDialog(QDialog):
    def __init__(self, highlight: Highlight, parent=None):
        super().__init__(parent)
        self.hl = highlight
        self.setWindowTitle("Chỉnh sửa Highlight")
        self.setMinimumWidth(350)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.txt_label = QLineEdit(highlight.label)
        layout.addRow("Tên:", self.txt_label)

        self.spn_start = QDoubleSpinBox()
        self.spn_start.setDecimals(1)
        self.spn_start.setRange(0, 99999)
        self.spn_start.setValue(highlight.start_time)
        self.spn_start.setSuffix(" s")
        layout.addRow("Bắt đầu:", self.spn_start)

        self.spn_end = QDoubleSpinBox()
        self.spn_end.setDecimals(1)
        self.spn_end.setRange(0, 99999)
        self.spn_end.setValue(highlight.end_time)
        self.spn_end.setSuffix(" s")
        layout.addRow("Kết thúc:", self.spn_end)

        self.txt_type = QLineEdit(highlight.highlight_type)
        layout.addRow("Loại:", self.txt_type)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setStyleSheet("""
            QDialog { background-color: #1e1e22; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QLineEdit, QDoubleSpinBox { background-color: #252528; color: #e0e0e0;
                border: 1px solid #3a3a42; border-radius: 3px; padding: 4px; }
            QPushButton { background-color: #3a3a50; color: #e0e0e0;
                border: 1px solid #4a4a60; border-radius: 4px; padding: 6px 12px; }
        """)

    def _accept(self):
        self.hl.label = self.txt_label.text()
        self.hl.start_time = self.spn_start.value()
        self.hl.end_time = self.spn_end.value()
        self.hl.highlight_type = self.txt_type.text()
        self.accept()


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.cfg = config
        self.setWindowTitle("Cài đặt")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        self.txt_player = QLineEdit(config.get("player_name", ""))
        layout.addRow("Tên tuyển thủ (in-game):", self.txt_player)

        self.txt_ffmpeg = QLineEdit(config.get("ffmpeg_path", "ffmpeg"))
        layout.addRow("FFmpeg path:", self.txt_ffmpeg)

        self.spn_interval = QDoubleSpinBox()
        self.spn_interval.setRange(0.5, 10.0)
        self.spn_interval.setValue(config.get("frame_sample_interval", 2.0))
        self.spn_interval.setSuffix(" s")
        layout.addRow("Frame sample interval:", self.spn_interval)

        self.spn_audio_th = QDoubleSpinBox()
        self.spn_audio_th.setRange(0.1, 1.0)
        self.spn_audio_th.setSingleStep(0.05)
        self.spn_audio_th.setValue(config.get("audio_spike_threshold", 0.8))
        layout.addRow("Audio spike threshold:", self.spn_audio_th)

        self.spn_tmpl_th = QDoubleSpinBox()
        self.spn_tmpl_th.setRange(0.3, 1.0)
        self.spn_tmpl_th.setSingleStep(0.05)
        self.spn_tmpl_th.setValue(config.get("template_match_threshold", 0.75))
        layout.addRow("Template match threshold:", self.spn_tmpl_th)

        self.spn_pad_b = QDoubleSpinBox()
        self.spn_pad_b.setRange(0, 30)
        self.spn_pad_b.setValue(config.get("highlight_pad_before", 3.0))
        self.spn_pad_b.setSuffix(" s")
        layout.addRow("Pad trước highlight:", self.spn_pad_b)

        self.spn_pad_a = QDoubleSpinBox()
        self.spn_pad_a.setRange(0, 30)
        self.spn_pad_a.setValue(config.get("highlight_pad_after", 2.0))
        self.spn_pad_a.setSuffix(" s")
        layout.addRow("Pad sau highlight:", self.spn_pad_a)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setStyleSheet("""
            QDialog { background-color: #1e1e22; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QLineEdit, QDoubleSpinBox { background-color: #252528; color: #e0e0e0;
                border: 1px solid #3a3a42; border-radius: 3px; padding: 4px; }
            QPushButton { background-color: #3a3a50; color: #e0e0e0;
                border: 1px solid #4a4a60; border-radius: 4px; padding: 6px 12px; }
        """)

    def _accept(self):
        self.cfg["player_name"] = self.txt_player.text()
        self.cfg["ffmpeg_path"] = self.txt_ffmpeg.text()
        self.cfg["frame_sample_interval"] = self.spn_interval.value()
        self.cfg["audio_spike_threshold"] = self.spn_audio_th.value()
        self.cfg["template_match_threshold"] = self.spn_tmpl_th.value()
        self.cfg["highlight_pad_before"] = self.spn_pad_b.value()
        self.cfg["highlight_pad_after"] = self.spn_pad_a.value()
        self.accept()
