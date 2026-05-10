import sys
import json
import re
import markdown
import httpx
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QTextBrowser, QTextEdit, QVBoxLayout, QHBoxLayout, QFrame,
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath


API_BASE = "http://127.0.0.1:8000"

_formatter = HtmlFormatter(style="monokai", nowrap=False)
_pygments_css = _formatter.get_style_defs('.highlight')

RESPONSE_STYLE = f"""
<style>
    * {{ box-sizing: border-box; }}
    html, body {{
        color: #cdd6f4; background: #181825; font-family: 'Segoe UI'; font-size: 13px;
        margin: 0; padding: 0; line-height: 1.6; width: 100%; max-width: 100%;
        word-break: break-word; overflow-wrap: break-word; white-space: normal;
    }}
    p {{ margin: 6px 0; word-break: break-word; overflow-wrap: break-word; }}
    code {{ background: #313244; padding: 2px 4px; border-radius: 3px; font-family: 'Consolas', monospace; color: #a6e3a1; font-size: 12px; }}
    pre {{ background: #12121e; padding: 12px; border-radius: 6px; border-left: 3px solid #cba6f7; margin: 8px 0; white-space: pre-wrap; word-break: break-word; max-width: 100%; }}
    pre code {{ background: none; padding: 0; font-size: 12px; white-space: pre-wrap; }}
    strong {{ color: #cba6f7; }}
    h1, h2, h3 {{ color: #89b4fa; font-size: 13px; font-weight: bold; margin: 8px 0 4px 0; }}
    ul, ol {{ padding-left: 20px; margin: 4px 0; }}
    li {{ margin: 3px 0; word-break: break-word; }}
    .highlight {{ background: #12121e; border-radius: 6px; border-left: 3px solid #cba6f7; margin: 8px 0; }}
    .highlight pre {{ white-space: pre-wrap; word-break: break-word; font-family: 'Consolas', monospace; font-size: 12px; padding: 12px; margin: 0; line-height: 1.5; }}
    {_pygments_css}
</style>
"""


def render_markdown(text: str) -> str:
    code_blocks = {}

    def replace_code(match):
        code = match.group(2).strip()
        highlighted = highlight(code, PythonLexer(), _formatter)
        key = f"CODEBLOCK{len(code_blocks)}END"
        code_blocks[key] = highlighted
        return key

    text = re.sub(r'```(\w+)?\n?(.*?)```', replace_code, text, flags=re.DOTALL)
    html = markdown.markdown(text, extensions=["nl2br"])
    for key, highlighted in code_blocks.items():
        html = html.replace(f"<p>{key}</p>", highlighted)
        html = html.replace(key, highlighted)
    return RESPONSE_STYLE + html


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
                    data = res.json()
                    content = data.get("content") or json.dumps(data, ensure_ascii=False)
                    self.finished.emit(content)
                return

            try:
                with httpx.Client(timeout=3.0) as client:
                    res = client.post(f"{API_BASE}{self.endpoint}", json=self.payload)
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("content"):
                            self.finished.emit(data["content"])
                            return
            except httpx.TimeoutException:
                pass

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


class CollapsedBar(QWidget):
    """접혔을 때 항상 보이는 바. 클릭하면 패널 토글."""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drag_start = None
        self._dragged = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 26, 26)
        painter.fillPath(path, QColor("#1e1e2e"))

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
            self.clicked.emit()
        self._drag_start = None
        self._dragged = False


class Panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._streaming_buffer = ""
        self._loading_dots = 0
        self._current_endpoint = ""
        self.setFixedWidth(400)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QLabel { color: #cdd6f4; font-family: 'Segoe UI'; font-size: 13px; background: transparent; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 6px; padding: 8px 12px; font-family: 'Segoe UI'; font-size: 13px; }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QTextEdit { background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 8px; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 13px; }
            QTextBrowser { background-color: #181825; border: 1px solid #313244; border-radius: 6px; padding: 8px; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 13px; }
            QFrame { background: transparent; }
        """)
        self._build()
        self._start_poller()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        painter.fillPath(path, QColor("#1e1e2e"))

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        title_row = QHBoxLayout()
        title_tag = QLabel("문제")
        title_tag.setStyleSheet("color: #6c7086; font-size: 11px; background: transparent;")
        title_row.addWidget(title_tag)
        title_row.addStretch()
        layout.addLayout(title_row)

        self.title_label = QLabel("불러오는 중...")
        self.title_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #313244; background: #313244;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        btn_layout = QHBoxLayout()
        self.btn_hint = QPushButton("힌트")
        self.btn_approach = QPushButton("접근법")
        self.btn_solution = QPushButton("정답 보기")
        self.btn_solution.setStyleSheet("""
            QPushButton { background-color: #f38ba8; color: #1e1e2e; border-radius: 6px; padding: 8px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #eba0ac; }
        """)
        for btn in [self.btn_hint, self.btn_approach, self.btn_solution]:
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self.loading_label = QLabel("생각 중")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #6c7086; font-size: 13px; background: transparent;")
        self.loading_label.setFixedHeight(350)
        self.loading_label.setMaximumWidth(368)
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

        self._loading_timer = QTimer()
        self._loading_timer.timeout.connect(self._update_loading)

        self.response_box = QTextBrowser()
        self.response_box.setReadOnly(True)
        self.response_box.setFixedHeight(350)
        self.response_box.setMaximumWidth(368)
        self.response_box.setOpenExternalLinks(False)
        self.response_box.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
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

    def _update_loading(self):
        self._loading_dots = (self._loading_dots + 1) % 4
        self.loading_label.setText("생각 중" + "." * self._loading_dots)

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
        if loading:
            self.response_box.hide()
            self.loading_label.show()
            self._loading_timer.start(400)
        else:
            self._loading_timer.stop()
            self.loading_label.hide()
            self.response_box.show()

    def _load_problem(self):
        self.worker = ApiWorker("/extract")
        self.worker.finished.connect(self._on_problem_loaded)
        self.worker.error.connect(lambda e: self.title_label.setText(f"오류: {e}"))
        self.worker.start()

    def _on_problem_loaded(self, raw: str):
        try:
            data = json.loads(raw)
            title = data.get("title", "")
            self.title_label.setText(title if title else "문제 없음")
        except Exception:
            self.title_label.setText("문제 파싱 오류")

    def _request(self, endpoint: str):
        self._current_endpoint = endpoint
        self._set_loading(True)
        self._streaming_buffer = ""
        self.response_box.clear()
        self.worker = ApiWorker(endpoint, {})
        self.worker.chunk_received.connect(self._on_chunk)
        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _ask(self):
        question = self.question_input.toPlainText().strip()
        if not question:
            return
        self._set_loading(True)
        self._streaming_buffer = ""
        self.response_box.clear()
        self.worker = ApiWorker("/ask", {"question": question})
        self.worker.chunk_received.connect(self._on_chunk)
        self.worker.finished.connect(self._on_response)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_chunk(self, chunk: str):
        self._streaming_buffer += chunk

    def _on_response(self, content: str):
        text = content if content else self._streaming_buffer
        self._streaming_buffer = ""
        self._loading_timer.stop()
        self.loading_label.hide()
        self.response_box.show()
        if text:
            if self._current_endpoint == "/solution":
                highlighted = highlight(text.strip(), PythonLexer(), _formatter)
                self.response_box.setHtml(RESPONSE_STYLE + highlighted)
            else:
                self.response_box.setHtml(render_markdown(text))
        for btn in [self.btn_hint, self.btn_approach, self.btn_solution, self.btn_ask]:
            btn.setEnabled(True)

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
        self._position_right_center()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.panel = Panel()
        self.panel.hide()
        layout.addWidget(self.panel)

        # 항상 보이는 바
        self.bar = CollapsedBar()
        self.bar.setFixedWidth(200)
        self.bar.clicked.connect(self._toggle_panel)

        bar_layout = QHBoxLayout(self.bar)
        bar_layout.setContentsMargins(14, 0, 10, 0)
        bar_layout.setSpacing(8)

        self.bar_label = QLabel("AI_Coding_Assistant")
        self.bar_label.setStyleSheet("color: #a6e3a1; font-size: 12px; background: transparent;")
        bar_layout.addWidget(self.bar_label)
        bar_layout.addStretch()

        self.toggle_btn = DraggableButton("🤖")
        self.toggle_btn.setFixedSize(38, 38)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 30, 46, 200);
                color: #cdd6f4;
                border-radius: 19px;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover { background-color: rgba(50, 50, 70, 220); }
        """)
        self.toggle_btn.clicked.connect(self._toggle_panel)
        bar_layout.addWidget(self.toggle_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6c7086;
                border-radius: 11px;
                font-size: 10px;
                border: none;
            }
            QPushButton:hover { background-color: rgba(243, 139, 168, 200); color: #1e1e2e; }
        """)
        self.close_btn.clicked.connect(QApplication.quit)
        bar_layout.addWidget(self.close_btn)

        layout.addWidget(self.bar, alignment=Qt.AlignmentFlag.AlignRight)

    def _toggle_panel(self):
        bar_global_tl = self.bar.mapToGlobal(self.bar.rect().topLeft())
        bar_global_br = self.bar.mapToGlobal(self.bar.rect().bottomRight())

        self.panel_visible = not self.panel_visible
        self.panel.setVisible(self.panel_visible)
        self.adjustSize()

        if self.panel_visible:
            # 패널이 바 위로 펼쳐짐 (바는 항상 하단 유지)
            self.move(
                bar_global_br.x() - self.width(),
                bar_global_br.y() - self.height()
            )
        else:
            # 접힐 때 바 위치 고정
            self.move(
                bar_global_tl.x(),
                bar_global_tl.y()
            )

    def _position_right_center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 20
        y = screen.center().y() - self.height() // 2
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