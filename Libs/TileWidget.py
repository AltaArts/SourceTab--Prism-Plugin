# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys
import datetime
import shutil
import logging
import traceback
import re

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))        #   TODO

if __name__ == "__main__":
    sys.path.append(os.path.join(prismRoot, "Scripts"))
    import PrismCore                                                                    #   TODO

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

uiPath = os.path.join(os.path.dirname(__file__), "UserInterfaces")
iconPath = os.path.join(uiPath, "Icons")
if uiPath not in sys.path:
    sys.path.append(uiPath)

import ItemList
import MetaDataWidget

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

from UserInterfaces import SceneBrowser_ui


logger = logging.getLogger(__name__)


#   BASE FILE TILE FOR SHARED METHODS
class BaseTileItem(QWidget):

    signalSelect = Signal(object)
    signalReleased = Signal(object)

    def __init__(self, browser, data):
        super(BaseTileItem, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.data = data

        self.getPixmapFromPath = self.core.media.getPixmapFromPath
        self.getThumbnailPath = self.core.media.getThumbnailPath

        self.isSelected = False

        self.previewSize = [self.core.scenePreviewWidth, self.core.scenePreviewHeight]
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69

        self.setupUi()
        self.refreshUi()


    #   Returns the Tile Data
    @err_catcher(name=__name__)
    def getData(self):
        return self.data
    

    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getFilepath(self):
        return self.data.get("filePath", "")


        #   Gets and Sets Thumbnail
    @err_catcher(name=__name__)
    def refreshPreview(self):
        #   Gets thumb path
        thumbPath = self.getThumbnailPath(self.data["filePath"])
        
        #   If thumb already exists it uses the .jpog
        if os.path.exists(thumbPath):
            ppixmap = QPixmap(thumbPath)

        #   If it doesn't it call a new pixmap
        else:
            ppixmap = self.getPixmap()

        if ppixmap:
            #   Scales pixmap
            pmap = self.core.media.scalePixmap(
                ppixmap, self.itemPreviewWidth, self.itemPreviewHeight, fitIntoBounds=False, crop=True
                )
            #   Sets pixmap to Tile label
            self.l_preview.setPixmap(pmap)


    #   Gets Pixmap from Prism function
    @err_catcher(name=__name__)
    def getPixmap(self):
        filePath = self.getFilepath()
        extension = self.getFileExtension()

        if not extension.lower() in self.core.media.supportedFormats:
            logger.debug(f"Cannot createthumbnail for {extension}")
            return None
        
        self.data["thumbPath"] = self.getThumbnailPath(filePath)

        pixmap = self.getPixmapFromPath(filePath,
                                        width=self.itemPreviewWidth,
                                        height=self.itemPreviewHeight,
                                        colorAdjust=False)

        if pixmap:
            return pixmap
        else:
            return None


    #   Returns File's Extension
    @err_catcher(name=__name__)
    def getFileExtension(self):
        filePath = self.getFilepath()
        basefile = os.path.basename(filePath)
        _, extension = os.path.splitext(basefile)

        return extension

    
    #   Returns UUID
    @err_catcher(name=__name__)
    def getUid(self):
        return self.data.get("uuid", "")
    

    #   Returns Date String
    @err_catcher(name=__name__)
    def getDate(self):
        date = self.data.get("date")
        dateStr = self.core.getFormattedDate(date) if date else ""

        return dateStr
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getSize(self):
        if self.browser.projectBrowser.act_filesizes.isChecked():
            if "size" in self.data:
                size_bytes = self.data["size"]
            else:
                size_bytes = os.stat(self.data["filePath"]).st_size

            size_mb = size_bytes / 1024.0 / 1024.0

            if size_mb < 1:
                size_kb = size_bytes / 1024.0
                sizeStr = "%.2f KB" % size_kb

            elif size_mb < 1024:
                sizeStr = "%.2f MB" % size_mb

            else:
                size_gb = size_mb / 1024.0
                sizeStr = "%.2f GB" % size_gb

            return sizeStr


    #   Returns the Tile Icon
    @err_catcher(name=__name__)
    def getIcon(self):
        if self.data.get("icon", ""):
            return self.data["icon"]
        else:
            return self.data["color"]


    #   Launches the Double-click File Action from the Main plugin
    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        self.browser.doubleClickFile(self.data["filePath"])


    #   Sets the Tile State Selected
    @err_catcher(name=__name__)
    def select(self):
        wasSelected = self.isSelected()
        self.signalSelect.emit(self)
        if not wasSelected:
            self.isSelected = True
            self.applyStyle(self.isSelected)
            self.setFocus()


    #   Sets the Tile State UnSelected
    @err_catcher(name=__name__)
    def deselect(self):
        if self.isSelected == True:
            self.isSelected = False
            self.applyStyle(self.isSelected)


    #   Returns if the State is Selected
    @err_catcher(name=__name__)
    def getSelected(self):
        return self.isSelected
    

    #   Sets the State Selected based on the Checkbox
    @err_catcher(name=__name__)
    def setSelected(self, checked=None):
        self.isSelected = self.chb_selected.isChecked()


    #   Sets the Checkbox and sets the State
    @err_catcher(name=__name__)
    def setChecked(self, checked):
        self.chb_selected.setChecked(checked)
        self.setSelected()






#   FILE TILES ON THE SOURCE SIDE
class SourceFileItem(BaseTileItem):
    def __init__(self, browser, data):
        super(SourceFileItem, self).__init__(browser, data)


    def mouseReleaseEvent(self, event):
        super(SourceFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("texture")
        self.applyStyle(self.isSelected)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.lo_main = QHBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.setSpacing(5)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

        self.l_preview = QLabel()
        self.l_preview.setMinimumWidth(self.itemPreviewWidth)
        self.l_preview.setMinimumHeight(self.itemPreviewHeight)
        self.l_preview.setMaximumWidth(self.itemPreviewWidth)
        self.l_preview.setMaximumHeight(self.itemPreviewHeight)

        self.spacer1 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer2 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer3 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer4 = QSpacerItem(15, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer5 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer6 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer7 = QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lo_info = QVBoxLayout()
        self.lo_info.setSpacing(0)
        self.l_icon = QLabel()
        self.chb_selected = QCheckBox()
        self.chb_selected.toggled.connect(self.setSelected)

        self.lo_info.addItem(self.spacer1)
        self.lo_info.addWidget(self.chb_selected)
        self.lo_info.addItem(self.spacer2)
        self.lo_info.addWidget(self.l_icon)
        self.lo_info.addStretch()

        self.lo_details = QVBoxLayout()

        self.l_fileName = QLabel()
        self.lo_details.addItem(self.spacer3)
        self.lo_details.addWidget(self.l_fileName)
        self.lo_details.addStretch()

        self.w_date = QWidget()
        self.lo_fileSpecs = QHBoxLayout(self.w_date)
        self.lo_fileSpecs.setContentsMargins(0, 0, 0, 0)

        # Date Icon and Label
        dateIconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "date.png")
        dateIcon = self.core.media.getColoredIcon(dateIconPath)
        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(dateIcon.pixmap(15, 15))

        self.l_date = QLabel()
        self.l_date.setAlignment(Qt.AlignRight)
        self.lo_fileSpecs.addStretch()
        self.lo_fileSpecs.addWidget(self.l_dateIcon)
        self.lo_fileSpecs.addWidget(self.l_date)

        # Disk Icon and Label (for File Size)
        diskIconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "disk.png")
        diskIcon = self.core.media.getColoredIcon(diskIconPath)
        self.l_diskIcon = QLabel()
        self.l_diskIcon.setPixmap(diskIcon.pixmap(15, 15))

        self.l_fileSize = QLabel()
        self.l_fileSize.setAlignment(Qt.AlignRight)
        self.lo_fileSpecs.addWidget(self.l_diskIcon)
        self.lo_fileSpecs.addWidget(self.l_fileSize)

        self.lo_details.addItem(self.spacer5)
        self.lo_details.addStretch()
        self.lo_details.addWidget(self.w_date)
        self.lo_details.addItem(self.spacer6)

        self.lo_main.addWidget(self.l_preview)
        self.lo_main.addLayout(self.lo_info)
        self.lo_main.addItem(self.spacer7)
        self.lo_main.addLayout(self.lo_details)
        self.lo_main.addStretch(1000)

        self.lo_main.addItem(self.spacer4)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)


    @err_catcher(name=__name__)
    def refreshUi(self):
        icon = self.getIcon()
        date = self.getDate()
        size = self.getSize()

        self.refreshPreview()
        self.setIcon(icon)
        self.l_fileName.setText(os.path.basename(self.data.get("filePath", "")))
        self.l_fileName.setToolTip(self.data.get("filePath", ""))
        self.l_date.setText(date)
        self.l_fileSize.setText(size)


    @err_catcher(name=__name__)
    def setIcon(self, icon):
        self.l_icon.setToolTip(os.path.basename(self.data["filePath"]))
        if isinstance(icon, QIcon):
            self.l_icon.setPixmap(icon.pixmap(24, 24))
        else:
            pmap = QPixmap(20, 20)
            pmap.fill(Qt.transparent)
            painter = QPainter(pmap)
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon)
            painter.drawEllipse(0, 0, 10, 10)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.end()
            self.l_icon.setPixmap(pmap)


    @err_catcher(name=__name__)
    def applyStyle(self, styleType):
        borderColor = (
            "rgb(70, 90, 120)" if self.isSelected is True else "rgb(70, 90, 120)"
        )
        ssheet = (
            """
            QWidget#texture {
                border: 1px solid %s;
                border-radius: 10px;
            }
        """
            % borderColor
        )
        if styleType is not True:
            pass
        elif styleType is True:
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hoverSelected":
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 35);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hover":
            ssheet += """
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
                QWidget#texture {
                    background-color: rgba(255, 255, 255, 20);
                }
            """

        self.setStyleSheet(ssheet)


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)


        selAct = QAction("Add to Transfer List", self.browser)
        selAct.triggered.connect(self.addToDestList)
        rcmenu.addAction(selAct)


        # copAct = QAction("Capture preview", self.browser)
        # copAct.triggered.connect(lambda: self.captureScenePreview(self.data))

        # exp = QAction("Browse preview...", self.browser)
        # exp.triggered.connect(self.browseScenePreview)
        # rcmenu.addAction(exp)

        # rcmenu.addAction(copAct)
        # clipAct = QAction("Paste preview from clipboard", self.browser)
        # clipAct.triggered.connect(
        #     lambda: self.pasteScenePreviewFromClipboard(self.data)
        # )
        # rcmenu.addAction(clipAct)

        # prvAct = QAction("Set as %spreview" % self.data.get("type", ""), self)
        # prvAct.triggered.connect(self.setPreview)
        # rcmenu.addAction(prvAct)


        rcmenu.exec_(QCursor.pos())

    
    @err_catcher(name=__name__)
    def addToDestList(self):
        self.browser.addToDestList(self.data)





#   FILE TILES ON THE DESTINATION SIDE
class DestFileItem(BaseTileItem):
    def __init__(self, browser, data):
        super(DestFileItem, self).__init__(browser, data)


    def mouseReleaseEvent(self, event):
        super(DestFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("texture")
        self.applyStyle(self.isSelected)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.lo_main = QHBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.setSpacing(5)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

        self.l_preview = QLabel()
        self.l_preview.setMinimumWidth(self.itemPreviewWidth)
        self.l_preview.setMinimumHeight(self.itemPreviewHeight)
        self.l_preview.setMaximumWidth(self.itemPreviewWidth)
        self.l_preview.setMaximumHeight(self.itemPreviewHeight)

        self.spacer1 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer2 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer3 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer4 = QSpacerItem(15, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer5 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer6 = QSpacerItem(0, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.spacer7 = QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.lo_info = QVBoxLayout()
        self.lo_info.setSpacing(0)
        self.l_icon = QLabel()
        self.chb_selected = QCheckBox()

        self.lo_info.addItem(self.spacer1)
        self.lo_info.addWidget(self.chb_selected)
        self.lo_info.addItem(self.spacer2)
        self.lo_info.addWidget(self.l_icon)
        self.lo_info.addStretch()

        self.lo_details = QVBoxLayout()

        self.l_fileName = QLabel()
        self.lo_details.addItem(self.spacer3)
        self.lo_details.addWidget(self.l_fileName)
        self.lo_details.addStretch()

        self.w_date = QWidget()
        self.lo_fileSpecs = QHBoxLayout(self.w_date)
        self.lo_fileSpecs.setContentsMargins(0, 0, 0, 0)

        # Date Icon and Label
        dateIconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "date.png")
        dateIcon = self.core.media.getColoredIcon(dateIconPath)
        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(dateIcon.pixmap(15, 15))

        self.l_date = QLabel()
        self.l_date.setAlignment(Qt.AlignRight)
        self.lo_fileSpecs.addStretch()
        self.lo_fileSpecs.addWidget(self.l_dateIcon)
        self.lo_fileSpecs.addWidget(self.l_date)

        # Disk Icon and Label (for File Size)
        diskIconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism", "disk.png")
        diskIcon = self.core.media.getColoredIcon(diskIconPath)
        self.l_diskIcon = QLabel()
        self.l_diskIcon.setPixmap(diskIcon.pixmap(15, 15))

        self.l_fileSize = QLabel()
        self.l_fileSize.setAlignment(Qt.AlignRight)
        self.lo_fileSpecs.addWidget(self.l_diskIcon)
        self.lo_fileSpecs.addWidget(self.l_fileSize)

        self.lo_details.addItem(self.spacer5)
        self.lo_details.addStretch()
        self.lo_details.addWidget(self.w_date)
        self.lo_details.addItem(self.spacer6)

        self.lo_main.addWidget(self.l_preview)
        self.lo_main.addLayout(self.lo_info)
        self.lo_main.addItem(self.spacer7)
        self.lo_main.addLayout(self.lo_details)
        self.lo_main.addStretch(1000)

        self.lo_main.addItem(self.spacer4)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)


    @err_catcher(name=__name__)
    def refreshUi(self):
        icon = self.getIcon()
        date = self.getDate()
        size = self.getSize()

        self.refreshPreview()
        self.setIcon(icon)
        self.l_fileName.setText(os.path.basename(self.data.get("filePath", "")))
        self.l_fileName.setToolTip(self.data.get("filePath", ""))
        self.l_date.setText(date)
        self.l_fileSize.setText(size)


    @err_catcher(name=__name__)
    def setIcon(self, icon):
        self.l_icon.setToolTip(os.path.basename(self.data["filePath"]))
        if isinstance(icon, QIcon):
            self.l_icon.setPixmap(icon.pixmap(24, 24))
        else:
            pmap = QPixmap(20, 20)
            pmap.fill(Qt.transparent)
            painter = QPainter(pmap)
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon)
            painter.drawEllipse(0, 0, 10, 10)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.end()
            self.l_icon.setPixmap(pmap)


    @err_catcher(name=__name__)
    def applyStyle(self, styleType):
        borderColor = (
            "rgb(70, 90, 120)" if self.isSelected is True else "rgb(70, 90, 120)"
        )
        ssheet = (
            """
            QWidget#texture {
                border: 1px solid %s;
                border-radius: 10px;
            }
        """
            % borderColor
        )
        if styleType is not True:
            pass
        elif styleType is True:
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hoverSelected":
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 35);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hover":
            ssheet += """
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
                QWidget#texture {
                    background-color: rgba(255, 255, 255, 20);
                }
            """

        self.setStyleSheet(ssheet)



    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)


        delAct = QAction("Remove from Transfer List", self.browser)
        delAct.triggered.connect(self.removeFromDestList)
        rcmenu.addAction(delAct)


        # copAct = QAction("Capture preview", self.browser)
        # copAct.triggered.connect(lambda: self.captureScenePreview(self.data))

        # exp = QAction("Browse preview...", self.browser)
        # exp.triggered.connect(self.browseScenePreview)
        # rcmenu.addAction(exp)

        # rcmenu.addAction(copAct)
        # clipAct = QAction("Paste preview from clipboard", self.browser)
        # clipAct.triggered.connect(
        #     lambda: self.pasteScenePreviewFromClipboard(self.data)
        # )
        # rcmenu.addAction(clipAct)

        # prvAct = QAction("Set as %spreview" % self.data.get("type", ""), self)
        # prvAct.triggered.connect(self.setPreview)
        # rcmenu.addAction(prvAct)


        rcmenu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def removeFromDestList(self):
        self.browser.removeFromDestList(self.data)




#   FOLDER
class FolderItem(BaseTileItem):
    def __init__(self, browser, data):
        super(FolderItem, self).__init__(browser, data)


    def mouseReleaseEvent(self, event):
        super(FolderItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("texture")
        self.applyStyle(self.isSelected)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Main horizontal layout
        self.lo_main = QHBoxLayout()
        self.setLayout(self.lo_main)
        self.lo_main.setSpacing(5)
        self.lo_main.setContentsMargins(0, 0, 0, 0)

        #   Icon Label
        self.l_icon = QLabel()
        #   Directory Name Label
        self.l_fileName = QLabel()

        self.lo_main.addWidget(self.l_icon)
        self.lo_main.addWidget(self.l_fileName)

        self.lo_main.addStretch()
        self.lo_main.addStretch(1000)

        # Set up context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)

        self.refreshUi()


    @err_catcher(name=__name__)
    def refreshUi(self):
        # Set the icon and folder name
        dir_icon = self.data["icon"]
        dir_path = self.data["dirPath"]

        # Set the icon on the left side
        self.l_icon.setPixmap(dir_icon.pixmap(32, 32))

        # Set the folder name (extract folder name from the path)
        folder_name = os.path.basename(dir_path)
        self.l_fileName.setText(folder_name)



    @err_catcher(name=__name__)
    def setIcon(self, icon):
        self.l_icon.setToolTip(os.path.basename(self.data["filename"]))
        if isinstance(icon, QIcon):
            self.l_icon.setPixmap(icon.pixmap(24, 24))
        else:
            pmap = QPixmap(20, 20)
            pmap.fill(Qt.transparent)
            painter = QPainter(pmap)
            painter.setPen(Qt.NoPen)
            painter.setBrush(icon)
            painter.drawEllipse(0, 0, 10, 10)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.end()
            self.l_icon.setPixmap(pmap)



    @err_catcher(name=__name__)
    def applyStyle(self, styleType):
        borderColor = (
            "rgb(70, 90, 120)" if self.isSelected is True else "rgb(70, 90, 120)"
        )
        ssheet = (
            """
            QWidget#texture {
                border: 1px solid %s;
                border-radius: 10px;
            }
        """
            % borderColor
        )
        if styleType is not True:
            pass
        elif styleType is True:
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 30);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hoverSelected":
            ssheet = """
                QWidget#texture {
                    border: 1px solid rgb(70, 90, 120);
                    background-color: rgba(255, 255, 255, 35);
                    border-radius: 10px;
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }

            """
        elif styleType == "hover":
            ssheet += """
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
                QWidget#texture {
                    background-color: rgba(255, 255, 255, 20);
                }
            """

        self.setStyleSheet(ssheet)


    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        self.browser.doubleClickFolder(self.data["dirPath"], mode="source")


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        pass
        # rcmenu = QMenu(self.browser)

        # copAct = QAction("Capture preview", self.browser)
        # copAct.triggered.connect(lambda: self.captureScenePreview(self.data))

        # exp = QAction("Browse preview...", self.browser)
        # exp.triggered.connect(self.browseScenePreview)
        # rcmenu.addAction(exp)

        # rcmenu.addAction(copAct)
        # clipAct = QAction("Paste preview from clipboard", self.browser)
        # clipAct.triggered.connect(
        #     lambda: self.pasteScenePreviewFromClipboard(self.data)
        # )
        # rcmenu.addAction(clipAct)

        # prvAct = QAction("Set as %spreview" % self.data.get("type", ""), self)
        # prvAct.triggered.connect(self.setPreview)
        # rcmenu.addAction(prvAct)
        # rcmenu.exec_(QCursor.pos())


