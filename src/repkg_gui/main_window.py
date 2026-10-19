import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from . import config
from .repkg_runner import RepkgThread

MODES = {"single": "单文件 / 单目录提取", "recursive": "递归批量提取", "tex": "仅 TEX 目录转换"}


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.thread: RepkgThread | None = None
        self._warned_format = False
        self._warned_dotnet = False

        self.setWindowTitle("RePKG GUI")
        self.setMinimumSize(820, 620)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)

        # --- 输入路径 ---
        in_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        btn_file = QPushButton("浏览文件")
        btn_dir = QPushButton("浏览文件夹")
        btn_file.clicked.connect(self.browse_file)
        btn_dir.clicked.connect(self.browse_dir)
        in_row.addWidget(QLabel("输入:"))
        in_row.addWidget(self.input_edit, 1)
        in_row.addWidget(btn_file)
        in_row.addWidget(btn_dir)
        layout.addLayout(in_row)

        # --- 输出路径 ---
        out_row = QHBoxLayout()
        self.output_edit = QLineEdit(self.cfg.get("default_output_dir", ""))
        btn_out = QPushButton("选择输出目录")
        btn_out.clicked.connect(self.pick_output)
        out_row.addWidget(QLabel("输出:"))
        out_row.addWidget(self.output_edit, 1)
        out_row.addWidget(btn_out)
        layout.addLayout(out_row)

        # --- 模式 ---
        mode_box = QGroupBox("处理模式")
        mode_row = QHBoxLayout(mode_box)
        self.mode_group = QButtonGroup(self)
        self.mode_radios = {}
        for key, label in MODES.items():
            r = QRadioButton(label)
            self.mode_radios[key] = r
            self.mode_group.addButton(r)
            mode_row.addWidget(r)
            r.toggled.connect(self.on_mode_changed)
        layout.addWidget(mode_box)

        # --- 选项 ---
        opt_box = QGroupBox("选项")
        opt_col = QVBoxLayout(opt_box)
        self.chk_meta = QCheckBox("复制 project.json / preview.jpg（-c）")
        self.chk_name = QCheckBox("使用 project.json 中的名称作为子目录（-n）")
        self.chk_no_tex = QCheckBox("仅解包，不转换 TEX（--no-tex-convert）")
        self.chk_overwrite = QCheckBox("覆盖已有文件（--overwrite）")
        opt_col.addWidget(self.chk_meta)
        opt_col.addWidget(self.chk_name)
        opt_col.addWidget(self.chk_no_tex)
        opt_col.addWidget(self.chk_overwrite)

        ext_row = QHBoxLayout()
        self.e_edit = QLineEdit()
        self.e_edit.setPlaceholderText("仅提取扩展名，逗号分隔，如 tex,png（-e）")
        self.i_edit = QLineEdit()
        self.i_edit.setPlaceholderText("忽略扩展名，逗号分隔（-i）")
        ext_row.addWidget(QLabel("仅提取:"))
        ext_row.addWidget(self.e_edit)
        ext_row.addWidget(QLabel("忽略:"))
        ext_row.addWidget(self.i_edit)
        opt_col.addLayout(ext_row)
        layout.addWidget(opt_box)

        # --- 按钮 ---
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("开始处理")
        self.btn_start.setDefault(True)
        self.btn_info = QPushButton("查看信息")
        self.btn_cancel = QPushButton("取消")
        self.btn_open = QPushButton("打开输出目录")
        self.btn_cancel.setEnabled(False)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_start.clicked.connect(self.start)
        self.btn_info.clicked.connect(self.show_info)
        self.btn_cancel.clicked.connect(self.cancel_task)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_info)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_open)
        layout.addLayout(btn_row)

        # --- 进度条 ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # --- 日志 ---
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("font-family: Consolas, 'Courier New', monospace;")
        layout.addWidget(self.log, 1)

        self.status = QStatusBar()
        layout.addWidget(self.status)

        # 恢复上次状态
        last_mode = self.cfg.get("last_mode", "single")
        self.mode_radios.get(last_mode, self.mode_radios["single"]).setChecked(True)
        if self.cfg.get("last_input_path"):
            self.input_edit.setText(self.cfg["last_input_path"])
        self.on_mode_changed()

        # 首次启动指定 RePKG.exe
        if not self._exe_valid():
            self.pick_repkg()

    # ---------- 基础工具 ----------
    def _exe_valid(self) -> bool:
        p = self.cfg.get("repkg_exe_path", "")
        return bool(p) and Path(p).is_file()

    def pick_repkg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 RePKG.exe", "", "RePKG 可执行文件 (*.exe)"
        )
        if path:
            self.cfg["repkg_exe_path"] = path
            config.save(self.cfg)
            self._warned_format = False
        self._refresh_exe_state()

    def _refresh_exe_state(self) -> None:
        ok = self._exe_valid()
        self.btn_start.setEnabled(ok)
        self.btn_info.setEnabled(ok)

    def current_mode(self) -> str:
        for key, r in self.mode_radios.items():
            if r.isChecked():
                return key
        return "single"

    def browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 PKG / TEX 文件", "", "支持文件 (*.pkg *.mpkg *.tex);;所有文件 (*)"
        )
        if path:
            self.input_edit.setText(path)

    def browse_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self.input_edit.setText(path)

    def pick_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_edit.text())
        if path:
            self.output_edit.setText(path)

    # ---------- 模式联动 ----------
    def on_mode_changed(self) -> None:
        tex = self.current_mode() == "tex"
        self.chk_meta.setEnabled(not tex)
        self.chk_name.setEnabled(not tex)
        self.chk_no_tex.setEnabled(not tex)
        if tex:
            self.e_edit.setText("tex")
            self.e_edit.setReadOnly(True)
        else:
            self.e_edit.setReadOnly(False)

    # ---------- 命令构造 ----------
    def _common_flags(self, args: list[str]) -> None:
        mode = self.current_mode()
        if mode != "tex":
            if self.chk_meta.isChecked():
                args.append("-c")
            if self.chk_name.isChecked():
                args.append("-n")
            if self.chk_no_tex.isChecked():
                args.append("--no-tex-convert")
        if self.chk_overwrite.isChecked():
            args.append("--overwrite")
        e = self.e_edit.text().strip()
        if e:
            args += ["-e", e]
        i = self.i_edit.text().strip()
        if i:
            args += ["-i", i]

    def build_extract_args(self, src: str, out: str) -> list[str]:
        args = ["extract"]
        mode = self.current_mode()
        if mode == "recursive":
            args += ["-r", src]
        elif mode == "tex":
            args += ["-t", "-s", src]
        else:
            args.append(src)
        args += ["-o", out]
        self._common_flags(args)
        return args

    # ---------- 运行流程 ----------
    def validate(self) -> tuple[str, str] | None:
        src = self.input_edit.text().strip()
        if not src or not Path(src).exists():
            QMessageBox.warning(self, "路径无效", "输入路径不存在，请重新选择。")
            return None
        out = self.output_edit.text().strip()
        if not out:
            out = self.cfg.get("default_output_dir", "")
            self.output_edit.setText(out)
        try:
            Path(out).mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            QMessageBox.critical(self, "无写入权限", f"输出目录创建失败：{e}\n请更换输出目录。")
            return None
        if not self._exe_valid():
            self.pick_repkg()
            if not self._exe_valid():
                QMessageBox.warning(self, "未找到 RePKG.exe", "请指定 RePKG.exe 的位置。")
                return None
        return src, out

    def start(self) -> None:
        v = self.validate()
        if not v:
            return
        src, out = v
        args = self.build_extract_args(src, out)
        self._launch(args, is_info=False)
        self.cfg["last_input_path"] = src
        self.cfg["last_mode"] = self.current_mode()

    def show_info(self) -> None:
        src = self.input_edit.text().strip()
        if not src or not Path(src).exists():
            QMessageBox.warning(self, "路径无效", "输入路径不存在，请重新选择。")
            return
        if not self._exe_valid():
            self.pick_repkg()
            if not self._exe_valid():
                return
        args = ["info", src, "-e", "-p", "*"]
        if Path(src).is_dir():
            args.insert(1, "-r")
        self.log_line("===== 信息模式输出，非提取任务 =====", False)
        self._launch(args, is_info=True)

    def _launch(self, args: list[str], is_info: bool) -> None:
        self.is_info = is_info
        self.thread = RepkgThread(self.cfg["repkg_exe_path"], args, self)
        self.thread.line.connect(self.on_line)
        self.thread.finished_with.connect(self.on_finished)
        self.thread.startup_error.connect(self.on_startup_error)
        self._set_running(True)
        self.log_line(f"$ RePKG.exe {' '.join(args)}", False)
        self.thread.start()

    def _set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_info.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        self.progress.setVisible(running)
        self.status.showMessage("运行中" if running else "就绪")

    def cancel_task(self) -> None:
        if self.thread:
            self.thread.cancel()

    def on_startup_error(self, msg: str) -> None:
        self._set_running(False)
        self.status.showMessage("出错")
        self.log_line(f"启动 RePKG 失败：{msg}", True)
        if ".NET" in msg or "dotnet" in msg.lower():
            QMessageBox.critical(self, "缺少 .NET 运行时", "RePKG 需要 .NET 运行时，请安装 .NET 6.0 或更高版本。")

    def on_line(self, text: str, is_err: bool) -> None:
        self.log_line(text, is_err)
        low = text.lower()
        if is_err and not self._warned_format and ("unknownmagic" in low or "not supported" in low):
            self._warned_format = True
            self.log_line("文件格式不受支持，请确认是 Wallpaper Engine 正版 PKG/TEX。", True)
        if is_err and ".NET" in text and not self._warned_dotnet:
            self._warned_dotnet = True
            QMessageBox.critical(self, "缺少 .NET 运行时", "RePKG 需要 .NET 运行时，请安装 .NET 6.0 或更高版本。")

    def on_finished(self, code: int, canceled: bool) -> None:
        self._set_running(False)
        if canceled:
            self.status.showMessage("已取消")
            self.log_line("任务已被用户取消。已生成的文件保留在输出目录中。", True)
            return
        if code == 0:
            self.status.showMessage("已完成")
            out = self.output_edit.text().strip()
            self.log_line(f"处理完成，输出位于：{out}", False)
            if not self.is_info:
                config.add_history(self.cfg, self.input_edit.text().strip(), out, self.current_mode())
                config.save(self.cfg)
        else:
            self.status.showMessage(f"出错（退出码 {code}）")
            self.log_line(f"RePKG 返回非零退出码 {code}，请检查上方错误信息。", True)

    def open_output(self) -> None:
        out = self.output_edit.text().strip()
        if out and Path(out).is_dir():
            os.startfile(out)

    # ---------- 日志 ----------
    def log_line(self, text: str, is_err: bool) -> None:
        ts = datetime.now().strftime("[%H:%M:%S] ")
        self.log.appendHtml(
            f'<span style="color:{"#c0392b" if is_err else "#222222"}">{ts}{self._escape(text)}</span>'
        )

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ---------- 拖拽 ----------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            self.input_edit.setText(urls[0].toLocalFile())

    def closeEvent(self, event) -> None:
        self.cfg["default_output_dir"] = self.output_edit.text().strip()
        config.save(self.cfg)
        super().closeEvent(event)
