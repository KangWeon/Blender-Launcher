import ssl
import sys
from pathlib import Path
from typing import Text

from modules._platform import get_cwd, get_platform_full, is_frozen
from modules.settings import get_enable_high_dpi_scaling
from PyQt5.QtCore import QFile, QPoint, Qt, QTextStream
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication, QWidget
from urllib3 import PoolManager

if get_enable_high_dpi_scaling():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class BaseWindow(QWidget):
    def __init__(self, parent=None, app=None, version=None):
        super().__init__()
        self.parent = parent

        if parent is None:
            self.app = app
            self.version = version

            # Setup pool manager
            _headers = {
                'user-agent': 'Blender Launcher/{0} ({1})'.format(
                    version, get_platform_full())}

            if is_frozen() is True:
                cacert = sys._MEIPASS + "/files/custom.pem"
            else:
                cacert = (
                    get_cwd() / "source/resources/certificates/custom.pem").as_posix()

            self.manager = PoolManager(
                num_pools=50, maxsize=10, headers=_headers,
                cert_reqs=ssl.CERT_REQUIRED,
                ca_certs=cacert)

            # Setup font
            QFontDatabase.addApplicationFont(
                ":/resources/fonts/OpenSans-SemiBold.ttf")
            self.font = QFont("Open Sans SemiBold", 10)
            self.font.setHintingPreference(QFont.PreferNoHinting)
            self.app.setFont(self.font)

            # Setup style
            file = QFile(":/resources/styles/global.qss")
            file.open(QFile.ReadOnly | QFile.Text)
            self.style_sheet = QTextStream(file).readAll()
            self.app.setStyleSheet(self.style_sheet)

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.pos = self.pos()
        self.pressing = False

        self.destroyed.connect(lambda: self._destroyed())

    def mousePressEvent(self, event):
        self.pos = event.globalPos()
        self.pressing = True
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.pressing:
            delta = QPoint(event.globalPos() - self.pos)
            self.moveWindow(delta, True)
            self.pos = event.globalPos()

    def moveWindow(self, delta, chain=False):
        self.move(self.x() + delta.x(), self.y() + delta.y())

        if chain and self.parent is not None:
            for window in self.parent.windows:
                if window is not self:
                    window.moveWindow(delta)

    def mouseReleaseEvent(self, QMouseEvent):
        self.pressing = False
        self.setCursor(Qt.ArrowCursor)

    def showEvent(self, event):
        parent = self.parent

        if parent is not None:
            if self not in parent.windows:
                parent.windows.append(self)
                parent.show_signal.connect(self.show)
                parent.close_signal.connect(self.hide)

            if self.parent.isVisible():
                x = parent.x() + (parent.width() - self.width()) * 0.5
                y = parent.y() + (parent.height() - self.height()) * 0.5
            else:
                size = parent.app.screens()[0].size()
                x = (size.width() - self.width()) * 0.5
                y = (size.height() - self.height()) * 0.5

            self.move(x, y)
            event.accept()

    def _destroyed(self):
        if self.parent is not None:
            self.parent.windows.remove(self)
