import os
from typing import Callable

from PIL import Image, ImageOps
from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ..base import FaceLayer, IconLayer, Layer
from ..utility import exists


class Previewer(QWidget):
    def __init__(self, aEncodeTexture: QAction):
        super().__init__()
        self.aEncodeTexture = aEncodeTexture
        self.layer = None

        self.lPath = QLabel()
        self.lName = QLabel()
        self.lWidth = QLabel()
        self.lHeight = QLabel()
        self.lImage = QLabel()
        self.lPath.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lName.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lWidth.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lHeight.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lImage.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.lPath)
        layout.addWidget(self.lName)
        layout.addWidget(self.lWidth)
        layout.addWidget(self.lHeight)
        layout.addWidget(self.lImage)

        self.setLayout(layout)

    def set_callback(self, *cbs: list[Callable[[str], bool]]):
        self.load_painting, self.load_face, self.load_icon = cbs

    def display_painting(self, layer: Layer):
        self.layer = layer
        self.lName.setText(f"Name: {layer.texture2D.name}")
        self.lWidth.setText(f"Width: {layer.spriteSize.X}")
        self.lHeight.setText(f"Height: {layer.spriteSize.Y}")
        self.lPath.setText(QDir.toNativeSeparators(layer.path))
        self.refresh()

    def display_face_or_icon(self, layer: FaceLayer | IconLayer):
        self.layer = layer
        self.lName.setText(f"Name: {layer.name}")
        self.lWidth.setText(f"Width: {layer.decode().size[0]}")
        self.lHeight.setText(f"Height: {layer.decode().size[1]}")
        self.lPath.setText(QDir.toNativeSeparators(layer.path))
        self.refresh()

    def refresh(self):
        if not exists(self.layer.repl):
            self.layer.repl = self.layer.decode()
        img = self.layer.repl.copy()
        img.thumbnail((640, 640))
        self.lImage.setPixmap(img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).toqpixmap())
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.clone().accept()

    def dropEvent(self, event: QDropEvent):
        flag = False
        for link in [x.toLocalFile() for x in event.mimeData().urls()]:
            if os.path.isdir(link) and self.load_face(link):
                flag = True
            elif link.endswith(".png"):
                if self.load_icon(link) or self.load_painting(link):
                    flag = True
        if flag:
            self.aEncodeTexture.setEnabled(True)
            self.refresh()
            event.accept()
