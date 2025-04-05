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
import shutil
import logging
import threading
import time
import json

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2

# prismRoot = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))        #   TODO

# if __name__ == "__main__":
#     sys.path.append(os.path.join(prismRoot, "Scripts"))
#     import PrismCore                                                                    #   TODO

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

pluginRoot = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginRoot, "Libs", "UserInterfaces")
iconPath = os.path.join(uiPath, "Icons")
if uiPath not in sys.path:
    sys.path.append(uiPath)

# import ItemList
# import MetaDataWidget

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

# from UserInterfaces import SceneBrowser_ui


logger = logging.getLogger(__name__)

#   Thead Limit for Thumbnail Generation
MAX_THUMB_THREADS = 12
thumb_semaphore = QSemaphore(MAX_THUMB_THREADS)

#   Thead Limit for File Transfer
MAX_COPY_THREADS = 6
copy_semaphore = QSemaphore(MAX_COPY_THREADS)

#   Update Interval for Progress Bar (secs)
PROG_UPDATE_INTV = 0.1

#   Proxy Folder Names
PROXY_NAMES = ["proxy", "pxy", "proxies", "proxys"]


#   Colors
COLOR_GREEN = QColor(0, 150, 0)
COLOR_ORANGE = QColor(255, 140, 0)
COLOR_RED = QColor(200, 0, 0)




#   BASE FILE TILE FOR SHARED METHODS
class BaseTileItem(QWidget):

    #   Signals
    signalSelect = Signal(object)
    signalReleased = Signal(object)

    def __init__(self, browser, data):
        super(BaseTileItem, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.data = data

        #   Renames Prism Functions for ease
        self.getPixmapFromPath = self.core.media.getPixmapFromPath
        self.getThumbnailPath = self.core.media.getThumbnailPath

        #   Set initial Selected State
        self.isSelected = False

        #   Thumbnail Size
        self.previewSize = [self.core.scenePreviewWidth, self.core.scenePreviewHeight]
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69

        #   Sets Thread Pool
        self.threadPool = QThreadPool.globalInstance()
        #    Limit Max Threads
        self.threadPool.setMaxThreadCount(MAX_THUMB_THREADS)

        self.setupUi()
        self.refreshUi()


    #   Returns the Tile Data
    @err_catcher(name=__name__)
    def getSettings(self):
        settingsFile = os.path.join(pluginRoot, "settings.json")

        with open(settingsFile, 'r') as file:
            sData = json.load(file)

            if sData:
                return sData
    

    #   Returns the Tile Data
    @err_catcher(name=__name__)
    def getData(self):
        return self.data
    

    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getFilepath(self):
        return self.data.get("filePath", "")


    #   Gets and Sets Thumbnail Using Threads
    @err_catcher(name=__name__)
    def refreshPreview(self):
        filePath = self.getFilepath()
        thumbPath = self.getThumbnailPath(filePath)

        # Create Worker Thread
        worker = ThumbnailWorker(filePath, thumbPath, self.getPixmap, self.itemPreviewWidth, self.itemPreviewHeight)

        #   Signal Connections
        worker.result.connect(self.updatePreview)  
        worker.finished.connect(worker.deleteLater)

        #   Call the Thread Start
        self.threadPool.start(worker)
        

    #   Gets Pixmap from Prism function
    @err_catcher(name=__name__)
    def getPixmap(self):
        filePath = self.getFilepath()
        extension = self.getFileExtension()

        #   If Extension in supported formats
        if not extension.lower() in self.core.media.supportedFormats:

            # Use the file's icon if it's not Supported Format
            file_info = QFileInfo(filePath)
            icon_provider = QFileIconProvider()
            icon = icon_provider.icon(file_info)
            icon_pixmap = icon.pixmap(self.itemPreviewWidth, self.itemPreviewHeight)

            if icon_pixmap:
                logger.debug(f"Using File Icon for Unsupported Format: {extension.lower()}")
                return icon_pixmap, "icon"
            else:
                return None, None

        # Generate Thumbnail if File is Supported
        self.data["thumbPath"] = self.getThumbnailPath(filePath)

        pixmap = self.getPixmapFromPath(filePath,
                                        width=self.itemPreviewWidth,
                                        height=self.itemPreviewHeight,
                                        colorAdjust=False)
        if pixmap:
            return pixmap, "image"
        else:
            return None, None
        

    #    Update Thumbnail when Ready
    @err_catcher(name=__name__)
    def updatePreview(self, pixmap, pmapType):
        if pixmap:
            if pmapType == "icon":
                fitIntoBounds=True
                crop = False
                scale = .5
            else:
                fitIntoBounds=False
                crop = True
                scale = 1

            scaledPixmap = self.core.media.scalePixmap(pixmap,
                                                       self.itemPreviewWidth * scale,
                                                       self.itemPreviewHeight * scale,
                                                       fitIntoBounds=fitIntoBounds,
                                                       crop=crop)
            
            self.l_preview.setAlignment(Qt.AlignCenter)
            self.l_preview.setPixmap(scaledPixmap)


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

        #   Thumbnail Container (Holds the thumbnail & proxy icon)
        self.thumbContainer = QWidget(self)
        self.thumbContainer.setFixedSize(self.itemPreviewWidth, self.itemPreviewHeight)

        #   Stacked Layout (For Overlaying Elements)
        self.lo_preview = QStackedLayout(self.thumbContainer)
        self.lo_preview.setStackingMode(QStackedLayout.StackAll)  # Ensures stacking order

        #   Thumbnail Label (Main Image)
        self.l_preview = QLabel(self.thumbContainer)
        self.l_preview.setFixedSize(self.itemPreviewWidth, self.itemPreviewHeight)
        self.lo_preview.addWidget(self.l_preview)  # Add thumbnail first

        #   Proxy Icon Label
        pxyIconPath = os.path.join(iconPath, "pxy_icon.png")
        pxyIcon = self.core.media.getColoredIcon(pxyIconPath)
        self.l_pxyIcon = QLabel(self.thumbContainer)
        self.l_pxyIcon.setPixmap(pxyIcon.pixmap(40, 40))
        self.l_pxyIcon.setStyleSheet("background-color: rgba(0,0,0,0);")

        #   Position Proxy Icon in Bottom-Left Corner
        pxy_x = 3
        pxy_y = self.itemPreviewHeight - self.l_pxyIcon.height()
        self.l_pxyIcon.move(pxy_x, pxy_y)
        self.l_pxyIcon.hide()


        ##  Create Details Layout
        self.lo_details = QVBoxLayout()

        ##   Create Top Layout
        self.lo_top = QHBoxLayout()

        #   Selected CheckBox
        self.chb_selected = QCheckBox()
        self.chb_selected.toggled.connect(self.setSelected)
        #   Filename Label
        self.l_fileName = QLabel()

        #   Add Items to Top Layout
        self.lo_top.addWidget(self.chb_selected)
        self.lo_top.addWidget(self.l_fileName)
        self.lo_top.addStretch()

        #   Create Bottom Layout
        self.lo_bottom = QHBoxLayout()

        #   File Type Icon
        self.l_icon = QLabel()

        #   Create Date Layout
        self.lo_date = QHBoxLayout()
        #   Date Icon
        dateIconPath = os.path.join(iconPath, "date.png")
        dateIcon = self.core.media.getColoredIcon(dateIconPath)
        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(dateIcon.pixmap(15, 15))
        #   Date Label
        self.l_date = QLabel()
        self.l_date.setAlignment(Qt.AlignRight)

        #   Add Date Items to Date LAyout
        self.lo_date.addWidget(self.l_dateIcon, alignment=Qt.AlignVCenter)
        self.lo_date.addWidget(self.l_date, alignment=Qt.AlignVCenter)
        
        #   Create File Size Layout
        self.lo_fileSize = QHBoxLayout()

        #   Disk Icon
        diskIconPath = os.path.join(iconPath, "disk.png")
        diskIcon = self.core.media.getColoredIcon(diskIconPath)
        self.l_diskIcon = QLabel()
        self.l_diskIcon.setPixmap(diskIcon.pixmap(15, 15))
        #   File Size Label
        self.l_fileSize = QLabel()
        self.l_fileSize.setAlignment(Qt.AlignRight)

        self.lo_fileSize.addWidget(self.l_diskIcon, alignment=Qt.AlignVCenter)
        self.lo_fileSize.addWidget(self.l_fileSize, alignment=Qt.AlignVCenter)

        #   Add Items to Bottom Layout
        self.lo_bottom.addWidget(self.l_icon, alignment=Qt.AlignVCenter)
        self.lo_bottom.addStretch()
        self.lo_bottom.addLayout(self.lo_date)
        self.lo_bottom.addStretch()
        self.lo_bottom.addLayout(self.lo_fileSize)

        #   Add Top and Bottom to Details Layout
        self.lo_details.addLayout(self.lo_top)
        self.lo_details.addLayout(self.lo_bottom)

        #   Add Layouts to Main Layout
        self.lo_main.addWidget(self.thumbContainer)
        self.lo_main.addLayout(self.lo_details)

        self.spacer4 = QSpacerItem(30, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lo_main.addItem(self.spacer4)

        #   Context Menu
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
        self.l_fileName.setToolTip(f"FilePath {self.data.get('filePath', '')}")
        self.l_fileSize.setToolTip(f"FileHash: {self.data.get('hash', '')}")

        self.l_date.setText(date)
        self.l_fileSize.setText(size)

        self.setProxyFile()


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


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxyFile(self):
        proxy = self.getProxyFile()

        if proxy:
            self.l_pxyIcon.show()
            tip = (f"Proxy File detected:\n\n"
                   f"{proxy}")
            self.l_pxyIcon.setToolTip(tip)
            self.data["proxyFilePath"] = proxy


    #   Uses Setting-defined Template to Search for Proxies
    @err_catcher(name=__name__)
    def getProxyFile(self):
        #   Get the Config Data
        sData = self.getSettings()
        proxySearchList = sData.get("proxySearch", [])

        #   Make the Various Names
        fullPath = self.data['filePath']
        baseDir = os.path.dirname(fullPath)
        baseName = os.path.basename(fullPath)
        fileBase, _ = os.path.splitext(baseName)

        for pathTemplate in proxySearchList:
            #   Replace Template Placeholders with Actual Names
            proxyPath = pathTemplate.replace("@MAINFILEDIR@", baseDir).replace("@MAINFILENAME@", fileBase)
            proxyPath = os.path.normpath(proxyPath)

            #   Extract Names
            proxyDir = os.path.dirname(proxyPath)
            targetFile = os.path.basename(proxyPath).lower()

            #   Remove Extension
            targetFileBase, _ = os.path.splitext(targetFile)

            #   Look for the Proxy
            if os.path.isdir(proxyDir):
                for f in os.listdir(proxyDir):
                    # Remove Extension from the File in the Dir
                    fileBaseName, _ = os.path.splitext(f.lower())

                    # Compare the base names (case-insensitive)
                    if fileBaseName == targetFileBase:
                        logger.debug(f"Proxy found for {targetFileBase}.")
                        return os.path.join(proxyDir, f)

        logger.debug(f"No Proxies found for {fileBase}")
        return None


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

    progressChanged = Signal(object)

    def __init__(self, browser, data):
        super(DestFileItem, self).__init__(browser, data)

        # # Add a progress bar to the tile
        # self.progressBar = QProgressBar(self)
        # self.progressBar.setValue(0)

        self.worker = None  # Placeholder for copy thread


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

        #   Thumbnail Container (Holds the thumbnail & proxy icon)
        self.thumbContainer = QWidget(self)
        self.thumbContainer.setFixedSize(self.itemPreviewWidth, self.itemPreviewHeight)

        #   Stacked Layout (For Overlaying Elements)
        self.lo_preview = QStackedLayout(self.thumbContainer)
        self.lo_preview.setStackingMode(QStackedLayout.StackAll)  # Ensures stacking order

        #   Thumbnail Label (Main Image)
        self.l_preview = QLabel(self.thumbContainer)
        self.l_preview.setFixedSize(self.itemPreviewWidth, self.itemPreviewHeight)
        self.lo_preview.addWidget(self.l_preview)  # Add thumbnail first

        #   Proxy Icon Label
        pxyIconPath = os.path.join(iconPath, "pxy_icon.png")
        pxyIcon = self.core.media.getColoredIcon(pxyIconPath)
        self.l_pxyIcon = QLabel(self.thumbContainer)
        self.l_pxyIcon.setPixmap(pxyIcon.pixmap(40, 40))
        self.l_pxyIcon.setStyleSheet("background-color: rgba(0,0,0,0);")

        #   Position Proxy Icon in Bottom-Left Corner
        pxy_x = 3
        pxy_y = self.itemPreviewHeight - self.l_pxyIcon.height()
        self.l_pxyIcon.move(pxy_x, pxy_y)
        self.l_pxyIcon.hide()


        ##  Create Details Layout
        self.lo_details = QVBoxLayout()

        ##   Create Top Layout
        self.lo_top = QHBoxLayout()

        #   Selected CheckBox
        self.chb_selected = QCheckBox()
        self.chb_selected.toggled.connect(self.setSelected)
        #   Filename Label
        self.l_fileName = QLabel()

        #   Add Items to Top Layout
        self.lo_top.addWidget(self.chb_selected)
        self.lo_top.addWidget(self.l_fileName)
        self.lo_top.addStretch()



        #   Create Bottom Layout
        self.lo_bottom = QHBoxLayout()

        #   File Type Icon
        self.l_icon = QLabel()



        # Add progress bar
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setFixedHeight(10)
        self.progressBar.setTextVisible(False)

        self.progressBar.setVisible(False)



        #   Add Items to Bottom Layout
        self.lo_bottom.addWidget(self.l_icon, alignment=Qt.AlignVCenter)
        self.spacer3 = QSpacerItem(40, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lo_main.addItem(self.spacer3)
        self.lo_bottom.addWidget(self.progressBar)

        #   Add Top and Bottom to Details Layout
        self.lo_details.addLayout(self.lo_top)
        self.lo_details.addLayout(self.lo_bottom)

        #   Add Layouts to Main Layout
        self.lo_main.addWidget(self.thumbContainer)
        self.lo_main.addLayout(self.lo_details)

        self.spacer4 = QSpacerItem(30, 0, QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.lo_main.addItem(self.spacer4)

        #   Context Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.rightClicked)

        self.progressBar.setVisible(True)



    @err_catcher(name=__name__)
    def refreshUi(self):
        icon = self.getIcon()
        # date = self.getDate()
        # size = self.getSize()

        self.refreshPreview()
        self.setIcon(icon)
        self.setProxy()

        self.l_fileName.setText(self.getFilename())
        tip = (f"Source File:  {self.getSourcePath()}\n"
               f"Destination File:  {self.getDestPath()}")
        self.l_fileName.setToolTip(tip)

        # self.l_date.setText(date)
        # self.l_fileSize.setText(size)


    @err_catcher(name=__name__)
    def getSourcePath(self):
        return self.data.get("filePath", None)
    

    @err_catcher(name=__name__)
    def getFilename(self):
        return os.path.basename(self.getSourcePath())    



    @err_catcher(name=__name__)
    def getDestPath(self):
        baseName = os.path.basename(self.data["filePath"])
        destDir = self.browser.l_destPath.text()
        destPath = os.path.join(destDir, baseName)
        return os.path.normpath(destPath)
    

    @err_catcher(name=__name__)
    def setIcon(self, icon):
        self.l_icon.setToolTip(self.getFilename())
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


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def getProxy(self):
        return self.data.get("proxyFilePath", None)



    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxy(self):
        proxy = self.getProxy()

        if proxy:
            self.l_pxyIcon.show()
            tip = (f"Proxy File detected:\n\n"
                   f"{proxy}")
            self.l_pxyIcon.setToolTip(tip)


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



    @err_catcher(name=__name__)
    def start_transfer(self, origin, destPath, options):
        """Starts the file transfer using a background thread."""

        self.destPath = destPath

        self.worker = FileCopyWorker(self.getSourcePath(), destPath)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.copy_complete)
        self.worker.start()


    def update_progress(self, value):
        """Updates progress bar in UI."""
        self.progressBar.setValue(value)


    def copy_complete(self, success):
        """Handles copy completion."""

        #   Sets Destination FilePath ToolTip
        self.l_fileName.setToolTip(os.path.normpath(self.destPath))

        if success:
            #   Force Prog Bar to 100%
            self.progressBar.setValue(100)
            
            #   If the Destination File Exists
            if os.path.isfile(self.destPath):
                #   Retrieve the Orignal Hash Value
                orig_hash = self.data["hash"]
                #   Calculate the Hash of the Transfered File
                dest_hash = self.browser.getFileHash(self.destPath)

                #   Hashes Are Equal
                if dest_hash == orig_hash:
                    status = "Transfer Successful"
                    statusColor = COLOR_GREEN
                    logger.debug(f"Transfer complete: {self.data['filePath']}")    
                
                #   Hashes Are Not Equal
                else:
                    status = "ERROR:  Transfered Hash Incorrect"
                    statusColor = COLOR_ORANGE
                    logger.debug(f"Transfered Hash Incorrect: {self.data['filePath']}")   

                hashMsg = (f"Status: {status}\n\n"
                        f"Source Hash:  {orig_hash}\n"
                        f"Transfer Hash: {dest_hash}")

            #   Destination File Does Not Exist
            else: 
                hashMsg = "ERROR:  Transfer File Does Not Exist"
                statusColor = COLOR_RED
                logger.warning(f"Transfer failed: {self.data['filePath']}")

        #   Did not Receive the Success Signal
        else:
            hashMsg = "ERROR:  Transfer failed"
            statusColor = COLOR_RED
            logger.warning(f"Transfer failed: {self.data['filePath']}")

        #   Set the Prog Bar Tooltip
        self.progressBar.setToolTip(hashMsg)

        #   Convert Color to rgb format string
        color_str = f"rgb({statusColor.red()}, {statusColor.green()}, {statusColor.blue()})"
        
        #   Set Prog Bar StyleSheet
        self.progressBar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {color_str};  /* Set the background color */
            }}
            QProgressBar::chunk {{
                background-color: {color_str};  /* Set the chunk color */
                width: 20px;
            }}
        """)



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

        #   Tooltips
        dirPath = os.path.normpath(self.data["dirPath"])
        self.l_icon.setToolTip(dirPath)
        self.l_fileName.setToolTip(dirPath)

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



#   Signal object to communicate between threads and the main UI
class ThumbnailSignal(QObject):
    finished = Signal(QPixmap, str)



#   Worker thread for loading thumbnails
class ThumbnailWorker(QRunnable, QObject):

    #   Signals
    finished = Signal()
    result = Signal(QPixmap, object)  

    def __init__(self, filePath, thumbPath, getPixmapFunc, width, height):
        super().__init__()
        QObject.__init__(self)  
        self.filePath = filePath
        self.thumbPath = thumbPath
        self.getPixmapFunc = getPixmapFunc
        self.width = width
        self.height = height


    #   Generates and Loads Thumb in Thread
    @Slot()
    def run(self):
        #   Limits number of threads
        thumb_semaphore.acquire()

        try:
            pixmap = None
            #   Uses the Saved Thumb if it exists
            if os.path.exists(self.thumbPath):
                pixmap = QPixmap(self.thumbPath)
                pmapType = "image"
            #   Generates New Thumbnail
            else:
                pixmap, pmapType = self.getPixmapFunc()

            #   Emits Pixmap Signal
            if pixmap:
                self.result.emit(pixmap, pmapType)

        finally:
            #   Emit Finished Signal
            self.finished.emit()  
            #   Release thread slot
            thumb_semaphore.release()




class FileCopyWorker(QThread):
    progress = Signal(int)   # Signal to send progress updates
    finished = Signal(bool)  # Signal when copy is done

    def __init__(self, src, dst):
        super().__init__()
        self.src = src
        self.dst = dst
        self.running = True  # Flag to allow stopping the thread

    def run(self):
        total_size = os.path.getsize(self.src)
        copied_size = 0

        def monitor_progress():
            last_reported = -1
            while self.running:
                if os.path.exists(self.dst):
                    copied_size = os.path.getsize(self.dst)
                    progress_percent = int((copied_size / total_size) * 100)

                    if progress_percent != last_reported:
                        self.progress.emit(progress_percent)  # Send progress update
                        last_reported = progress_percent

                    if copied_size >= total_size:
                        break

                time.sleep(PROG_UPDATE_INTV)

        # Start monitoring in a separate thread
        progress_thread = threading.Thread(target=monitor_progress, daemon=True)
        progress_thread.start()

        # Acquire semaphore to ensure only MAX_COPY_THREADS copies at a time
        copy_semaphore.acquire()

        try:
            shutil.copy2(self.src, self.dst)
            self.finished.emit(True)
        except Exception as e:
            print(f"Error copying file: {e}")
            self.finished.emit(False)

        # Release semaphore after copy completes
        copy_semaphore.release()

        self.running = False
        progress_thread.join()

