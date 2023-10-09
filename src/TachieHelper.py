import os

from PIL import Image
from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .AssetManager import AssetManager
from .Config import Config
from .ui import IconViewer, Menu, Previewer, Table


class AzurLaneTachieHelper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("AzurLane Tachie Helper"))
        self.setAcceptDrops(True)
        self.resize(720, 560)

        self.config = Config("config.ini")
        self.asset_manager = AssetManager()

        self._init_statusbar()
        self._init_menu()
        self._init_ui()

    def _init_ui(self):
        self.preview = Previewer(self.mEdit.aEncodeTexture)
        self.tPainting = Table.Painting(self.preview)
        self.tFace = Table.Paintingface(self.preview)
        self.preview.set_callback(self.tPainting.load_painting, self.tFace.load_face)

        left = QVBoxLayout()
        left.addLayout(self.tPainting)
        left.addLayout(self.tFace)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)

        layout = QHBoxLayout()
        layout.addLayout(left)
        layout.addWidget(sep)
        layout.addWidget(self.preview)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def _init_statusbar(self):
        self.message = QLabel(self.tr("Ready"))
        self.message.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.statusBar().addWidget(self.message)
        self.statusBar().setStyleSheet("QStatusBar::item{border:0px}")

    def _init_menu(self):
        callbacks = {
            "Open Metadata": self.onClickFileOpenMetadata,
            "Import Painting": self.onClickFileImportPainting,
            "Import Paintingface": self.onClickFileImportPaintingface,
            "Import Icons": self.onClickFileImportIcons,
            "Clip Icons": self.onClickEditClip,
            "Decode Texture": self.onClickEditDecode,
            "Encode Texture": self.onClickEditEncode,
            "Dump Intermediate Layers": self.onClickOption,
            "Advanced Paintingface Mode": self.onClickOption,
            "Replace Icons": self.onClickOption,
        }
        self.mFile = Menu.File(callbacks)
        self.mEdit = Menu.Edit(callbacks)
        self.mOption = Menu.Option(callbacks, self.config)

        self.menuBar().addMenu(self.mFile)
        self.menuBar().addMenu(self.mEdit)
        self.menuBar().addMenu(self.mOption)

    def show_path(self, text: str):
        msg_box = QMessageBox()
        msg_box.setText(self.tr("Successfully written into:") + f"\n{text}")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def open_metadata(self, file: str):
        self.config.set("File/RecentPath", file)
        self.message.setText(f"({os.path.basename(file)})  {QDir.toNativeSeparators(file)}")
        print("[INFO] Metadata:", file)

        self.tPainting.table.clearContents()
        self.tFace.table.clearContents()

        self.asset_manager.analyze(file)

        self.tPainting.set_data(self.asset_manager.deps, self.asset_manager.layers)

        face_layer = self.asset_manager.face_layer
        prefered = self.asset_manager.prefered(face_layer)
        adv_mode = self.config.get_bool("Edit/AdvancedMode")
        self.tFace.set_data(self.asset_manager.faces, face_layer, prefered, adv_mode)

        self.mFile.aImportPainting.setEnabled(True)
        self.mFile.aImportPaintingface.setEnabled(True)
        self.mFile.aImportIcons.setEnabled(True)
        self.mEdit.aDecodeTexture.setEnabled(True)
        self.mEdit.aClipIcons.setEnabled(True)

    def onClickFileOpenMetadata(self):
        last = self.config.get_str("File/RecentPath")
        file, _ = QFileDialog.getOpenFileName(self, self.tr("Select Metadata"), last)
        if file:
            self.open_metadata(file)

    def onClickFileImportPainting(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath"))
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Select Paintings"), last, "Image (*.png)"
        )
        if files:
            flag = False
            for file in files:
                if self.tPainting.load_painting(file):
                    flag = True
            if flag:
                self.mEdit.aEncodeTexture.setEnabled(True)

    def onClickFileImportPaintingface(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath"))
        dir = QFileDialog.getExistingDirectory(self, self.tr("Select Paintingface Folder"), last)
        if dir:
            if self.tFace.load_face(dir):
                self.mEdit.aEncodeTexture.setEnabled(True)

    def onClickFileImportIcons(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath"))
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Select Icons"), last, "Image (*.png)"
        )
        if files:
            print("[INFO] Icons:")

            for file in files:
                name, _ = os.path.splitext(os.path.basename(file))
                if name in ["shipyardicon", "squareicon", "herohrzicon"]:
                    print("      ", QDir.toNativeSeparators(file))
                    self.asset_manager.repls[name] = Image.open(file)

            self.mEdit.aEncodeTexture.setEnabled(True)

    def onClickEditClip(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath"))
        file, _ = QFileDialog.getOpenFileName(
            self, self.tr("Select Reference"), last, "Image (*.png)"
        )
        if file:
            viewer = IconViewer(self.asset_manager.icons, *self.asset_manager.prepare_icon(file))
            if viewer.exec():
                res = self.asset_manager.clip_icons(file, viewer.presets)
                self.show_path("\n".join([QDir.toNativeSeparators(_) for _ in res]))

    def onClickEditDecode(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath", ""))
        dir = QFileDialog.getExistingDirectory(self, self.tr("Select Output Folder"), last)
        if dir:
            res = self.asset_manager.decode(dir, self.config.get_bool("Edit/DumpLayer"))
            self.show_path(QDir.toNativeSeparators(res))

    def onClickEditEncode(self):
        last = os.path.dirname(self.config.get_str("File/RecentPath"))
        dir = QFileDialog.getExistingDirectory(self, dir=last)
        if dir:
            enable_icon = self.config.get_bool("Edit/ReplaceIcon")
            res = self.asset_manager.encode(dir, enable_icon)
            self.show_path("\n".join([QDir.toNativeSeparators(_) for _ in res]))

    def onClickOption(self):
        self.config.set("Edit/DumpLayer", self.mOption.aDumpLayer.isChecked())

        adv_mode = self.mOption.aAdvMode.isChecked()
        if adv_mode != self.config.get_bool("Edit/AdvancedMode"):
            self.config.set("Edit/AdvancedMode", adv_mode)
            if hasattr(self, "num_faces"):
                for i in range(self.tFace.num):
                    if adv_mode:
                        flag = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                    else:
                        flag = ~Qt.ItemFlag.ItemIsEnabled
                    self.tFace.table.item(i, 0).setFlags(flag)

        self.config.set("Edit/ReplaceIcon", self.mOption.aReplaceIcons.isChecked())

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            if not event.isAccepted():
                event.accept()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            self.open_metadata(event.mimeData().urls()[0].toLocalFile())
            self.preview.setAcceptDrops(True)
            if event.isAccepted():
                self.mEdit.aEncodeTexture.setEnabled(True)
            else:
                event.accept()
