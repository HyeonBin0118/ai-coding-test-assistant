import sys
import httpx
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QTextEdit, QVBoxLayout, QHBoxLayout, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


API_BASE = "http://127.0.0.1:8000"


class ApiWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, endpoint: str, payload: dict = None):
        super().__init__()
        self.endpoint = endpoint
        self.payload = payload or {}

    def run(self):
        try:
            if self.endpoint == "/extract":
                with httpx.Client(timeout=30.0) as client:
                    res = client.get(f"{API_BASE}/extract")
                    res.raise_for_status()
                    import json
                    data = res.json()
                    content = data.get("content") or json.dumps(data, ensure_ascii=False)
                    self.finished.emit(content)
                return

            stream_endpoint = self.endpoint + "/stream"
            with httpx.Client(timeout=60.0) as client:
                with client.stream("POST", f"{API_BASE}{stream_endpoint}", json=self.payload) as res:
                    res.raise_for_status()
                    for line in res.iter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk:
                                self.chunk_received.emit(chunk)
            self.finished.emit("")

        except Exception as e:
            self.error.emit(str(e))


class ProblemPoller(QThread):
    problem_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._last_title = ""
        self._running = True

    def run(self):
        while self._running:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.get(f"{API_BASE}/status")
                    res.raise_for_status()
                    data = res.json()
                    title = data.get("title", "")
                    if title and title != self._last_title:
                        self._last_title = title
                        self.problem_changed.emit(title)
            except Exception:
                pass
            self.msleep(2000)

    def stop(self):
        self._running = False


class DraggableButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._drag_start = None
        self._dragged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._dragged = False
            top = self.window()
            top._drag_pos = event.globalPosition().toPoint() - top.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_start and event.buttons() == Qt.MouseButton.LeftButton:
            delta = (event.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if delta > 6:
                self._dragged = True
                top = self.window()
                if top._drag_pos:
                    top.move(event.globalPosition().toPoint() - top._drag_pos)

    def mouseReleaseEvent(self, event):
        self.window()._drag_pos = None
        if not self._dragged:
            super().mousePressEvent(event)
            super().mouseReleaseEvent(event)
        self._drag_start = None
        self._dragged = False


class Panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QTextEdit {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
            }
        """)
        self._build()
        self._start_poller()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self.title_label = QLabel("문제를 불러오는 중...")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #313244;")
        layout.addWidget(line)

        btn_layout = QHBoxLayout()
        self.btn_hint = QPushButton("힌트")
        self.btn_approach = QPushButton("접근법")
        self.btn_solution = QPushButton("정답 보기")
        self.btn_solution.setStyleSheet("""
            QPushButton {
                background-color: #f38ba8;
                color: #1e1e2e;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #eba0ac; }
        """)
        for btn in [self.btn_hint, self.btn_approach, self.btn_solution]:
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setMinimumHeight(200)
        self.response_box.setPlaceholderText("")
        layout.addWidget(self.response_box)

        self.question_input = QTextEdit()
        self.question_input.setFixedHeight(70)
        self.question_input.setPlaceholderText("궁금한 점을 입력하세요...")
        layout.addWidget(self.question_input)

        self.btn_ask = QPushButton("질문하기")
        layout.addWidget(self.btn_ask)

        self.btn_hint.clicked.connect(lambda: self._request("/hint"))
        self.btn_approach.clicked.connect(lambda: self._request("/approach"))
        self.btn_solution.clicked.connect(lambda: self._request("/solution"))
        self.btn_ask.clicked.connect(self._ask)

        self._load_problem()

    def _start_poller(self):
        self.poller = ProblemPoller()
        self.poller.problem_changed.connect(self._on_problem_changed)
        self.poller.start()

    def _on_problem_changed(self, title: str):
        self.title_label.setText(title)
        self.response_box.clear()
        self.question_input.clear()

    def _set_loading(self, loading: bool):
        for btn in [self.btn_hint, self.btn_approach, self.btn_solution, self.btn_ask]:
            btn.setEnabled(not loading)

    def _load_problem(self):
        self.worker = ApiWorker("/extract")
        self.worker.finished.connect(self._on_problem_loaded)
        self.worker.error.connect(lambda e: self.title_label.setText(f"오류: {e}"))
        self.worker.start()

    def _on_problem_loaded(self, raw: str):
        import json
        try:
            data = json.loads(raw)
            title = data.get("title", "")
            self.title_label.setText(title if title else "문제 없음")
        except Exception:
            self.title_label.setText("문제 파싱 오류")

    def _request(self, endpoint: str):
        self._set_loading(True)
        self.response_box.clear()
        self.worker = ApiWorker(endpoint, {})
        self.worker.chunk_received.connect(
            lambda chunk: self.response_box.insertPlainText(chunk)
        )
        self.worker.finished.connect(lambda _: self._set_loading(False))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _ask(self):
        question = self.question_input.toPlainText().strip()
        if not question:
            return
        self._set_loading(True)
        self.response_box.clear()
        self.worker = ApiWorker("/ask", {"question": question})
        self.worker.chunk_received.connect(
            lambda chunk: self.response_box.insertPlainText(chunk)
        )
        self.worker.finished.connect(lambda _: self._set_loading(False))
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_error(self, msg: str):
        self.response_box.setPlainText(f"오류: {msg}")
        self._set_loading(False)


class FloatingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.panel_visible = False
        self._drag_pos = None
        self._build()
        self._position_bottom_right()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.panel = Panel()
        self.panel.hide()
        layout.addWidget(self.panel)

        self.toggle_btn = DraggableButton("💡")
        self.toggle_btn.setFixedSize(48, 48)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border-radius: 24px;
                font-size: 20px;
                border: none;
            }
            QPushButton:hover { background-color: #b4befe; }
        """)
        self.toggle_btn.clicked.connect(self._toggle_panel)
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border-radius: 12px;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover { background-color: #f38ba8; color: #1e1e2e; }
        """)
        self.close_btn.clicked.connect(QApplication.quit)
        layout.addWidget(self.close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _toggle_panel(self):
        self.panel_visible = not self.panel_visible
        self.panel.setVisible(self.panel_visible)
        current_pos = self.pos()
        self.adjustSize()
        self.move(current_pos)

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 20
        y = screen.bottom() - self.height() - 20
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        if hasattr(self.panel, 'poller'):
            self.panel.poller.stop()
        event.accept()


def main():
    import signal
    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    widget = FloatingWidget()
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()