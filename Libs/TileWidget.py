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
####################################################
#
#           ########### PLUGIN
#           by Joshua Breckeen
#                Alta Arts
#
#   This PlugIn adds an additional tab to the Prism Settings menu to ##########################
#   allow a user to choose a directory that contains scene presets.###############################
#
        #       TODO


####################################################


import os
import sys
import logging
import time
import json
import hashlib

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
iconDir = os.path.join(uiPath, "Icons")
if uiPath not in sys.path:
    sys.path.append(uiPath)

# import ItemList
# import MetaDataWidget

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

# from UserInterfaces import SceneBrowser_ui


logger = logging.getLogger(__name__)

#   Thread Limit for Thumbnail Generation
MAX_THUMB_THREADS = 12
thumb_semaphore = QSemaphore(MAX_THUMB_THREADS)

#   Thread Limit for File Transfer
MAX_COPY_THREADS = 6
copy_semaphore = QSemaphore(MAX_COPY_THREADS)

#   Size of Copy Chunks
COPY_CHUNK_SIZE = 1  # (in megabytes)

#   Update Interval for Progress Bar
PROG_UPDATE_INTV = .5   # (in secs)

#   Proxy Folder Names
PROXY_NAMES = ["proxy", "pxy", "proxies", "proxys"]


#   Colors
COLOR_GREEN = QColor(0, 150, 0)
COLOR_BLUE = QColor(115, 175, 215)
COLOR_ORANGE = QColor(255, 140, 0)
COLOR_RED = QColor(200, 0, 0)
COLOR_GREY = QColor(100, 100, 100)




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
        self.getThumbnailPath = self.core.media.getThumbnailPath

        #   Set initial Selected State
        self.isSelected = False

        #   Thumbnail Size
        # self.previewSize = [self.core.scenePreviewWidth, self.core.scenePreviewHeight]
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69

        #   Sets Thread Pool
        self.threadPool = QThreadPool.globalInstance()
        #    Limit Max Threads
        self.threadPool.setMaxThreadCount(MAX_THUMB_THREADS)

        #   Calls the SetupUI Method of the Child Tile
        self.setupUi()
        #   Calls the Refresh Method of the Child Tile
        self.refreshUi()


    #   Launches the Double-click File Action from the Main plugin
    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        self.browser.doubleClickFile(self.data["source_mainFile_path"])


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
    

    #   Returns the File Create Date from the OS
    @err_catcher(name=__name__)
    def getFileDate(self, filePath):
        return os.path.getmtime(filePath)

    #   Returns the File Size from the OS
    @err_catcher(name=__name__)
    def getFileSize(self, filePath):
        return os.stat(filePath).st_size


    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_mainfilePath(self):
        return self.data.get("source_mainFile_path", "")
    

     #   Returns the Filepath
    @err_catcher(name=__name__)
    def getBasename(self, filePath):
        return os.path.basename(filePath)
    

    #   Gets Custom Hash of File in Separate Thread
    @err_catcher(name=__name__)
    def setFileHash(self, filePath, callback=None):
        worker = FileHashWorker(filePath)
        worker.signals.finished.connect(callback)
        self.threadPool.start(worker)
    

    @err_catcher(name=__name__)
    def getIconByType(self, filePath):
        fileType = self.browser.getFileType(filePath)

        match fileType:
            case "image":
                iconPath =  os.path.join(iconDir, "render_still.png")
            case "video":        
                iconPath =  os.path.join(iconDir, "movie.png")
            case "audio":
                iconPath =  os.path.join(iconDir, "disk.png")
            case "folder":
                iconPath =  os.path.join(iconDir, "file_folder.png")
            case "other":
                iconPath =  os.path.join(iconDir, "file.png")
            case _:
                iconPath =  os.path.join(iconDir, "error.png")

        return QIcon(iconPath)


    #   Gets and Sets Thumbnail Using Thread
    @err_catcher(name=__name__)
    def refreshPreview(self):
        filePath = self.getSource_mainfilePath()

        # Create Worker Thread
        worker = ThumbnailWorker(
            filePath=filePath,
            getPixmapFromPath=self.core.media.getPixmapFromPath,
            supportedFormats=self.core.media.supportedFormats,
            width=self.itemPreviewWidth,
            height=self.itemPreviewHeight,
            getThumbnailPath=self.getThumbnailPath,
            scalePixmapFunc=self.core.media.scalePixmap
        )
        worker.result.connect(self.updatePreview)
        self.threadPool.start(worker)
        

    @err_catcher(name=__name__)
    def updatePreview(self, scaledPixmap):
        self.l_preview.setAlignment(Qt.AlignCenter)
        self.l_preview.setPixmap(scaledPixmap)


    #   Returns File's Extension
    @err_catcher(name=__name__)
    def getFileExtension(self):
        filePath = self.getSource_mainfilePath()
        basefile = os.path.basename(filePath)
        _, extension = os.path.splitext(basefile)

        return extension

    
    #   Returns UUID
    @err_catcher(name=__name__)
    def getUid(self):
        return self.data.get("uuid", "")
    

    # #   Returns Date String
    # @err_catcher(name=__name__)
    # def getDate(self):
    #     date = self.data.get("date")
    #     dateStr = self.core.getFormattedDate(date) if date else ""

    #     return dateStr
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getFileSizeStr(self, size_bytes):
        if self.browser.projectBrowser.act_filesizes.isChecked():
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


    @err_catcher(name=__name__)
    def setIcon(self, icon):
        self.l_icon.setToolTip(self.getSource_mainfilePath())
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


    #   Returns the Tile Icon
    @err_catcher(name=__name__)
    def getIcon(self):
        if self.data.get("icon", ""):
            return self.data["icon"]
        else:
            return self.data["color"]






#   FILE TILES ON THE SOURCE SIDE (Inherits from BaseTileItem)
class SourceFileItem(BaseTileItem):
    def __init__(self, browser, data):
        super(SourceFileItem, self).__init__(browser, data)


    def mouseReleaseEvent(self, event):
        super(SourceFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("SourceFileItem")
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
        pxyIconPath = os.path.join(iconDir, "pxy_icon.png")
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
        dateIconPath = os.path.join(iconDir, "date.png")
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
        diskIconPath = os.path.join(iconDir, "disk.png")
        diskIcon = self.core.media.getColoredIcon(diskIconPath)
        self.l_diskIcon = QLabel()
        self.l_diskIcon.setPixmap(diskIcon.pixmap(15, 15))
        #   File Size Label
        self.l_fileSize = QLabel("--")
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
        # Get File Path
        filePath = self.getSource_mainfilePath()
        self.l_fileName.setText(self.getBasename(filePath))
        self.l_fileName.setToolTip(f"FilePath: {filePath}")

        #   Set Filetype Icon
        icon = self.getIconByType(filePath)
        self.data["icon"] = icon
        self.setIcon(icon)

        #   Set Date
        date_data = self.getFileDate(filePath)
        date_str = self.core.getFormattedDate(date_data)
        self.l_date.setText(date_str)
        self.data["source_mainFile_date"] = date_str

        #   Set Filesize
        mainSize_data = self.getFileSize(filePath)
        mainSize_str = self.getFileSizeStr(mainSize_data)
        self.data["source_mainFile_size"] = mainSize_str
        self.l_fileSize.setText(mainSize_str)

        #   Set Hash
        self.l_fileSize.setToolTip("Calculating file hash...")
        self.setFileHash(filePath, self.onMainfileHashReady)

        self.refreshPreview()
        self.setProxyFile()



    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileHashReady(self, result_hash):
        self.data["source_mainFile_hash"] = result_hash
        self.l_fileSize.setToolTip(f"Hash: {result_hash}")


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxyFile(self):
        self.data["hasProxy"] = False

        proxyFilepath = self.searchForProxyFile()

        if proxyFilepath:
            #   Set Proxy Flag
            self.data["hasProxy"] = True

            #   Show Proxy Icon on Thumbnail
            self.l_pxyIcon.show()

            #   Set Source Proxy Path
            self.data["source_proxyFile_path"] = proxyFilepath

            #   Set Source Proxy Date
            date_data = self.getFileDate(proxyFilepath)
            date_str = self.core.getFormattedDate(date_data)
            self.data["source_proxyFile_date"] = date_str

            #   Set Source Proxy Filesize
            mainSize_data = self.getFileSize(proxyFilepath)
            mainSize_str = self.getFileSizeStr(mainSize_data)
            self.data["source_proxyFile_size"] = mainSize_str

            #   Set Source Proxy Hash
            self.setFileHash(proxyFilepath, self.onProxyfileHashReady)

            #   Set Proxy Tooltip
            tip = (f"Proxy File detected:\n\n"
                   f"File: {proxyFilepath}\n"
                   f"Date: {date_str}\n"
                   f"Size: {mainSize_str}")
            
            self.l_pxyIcon.setToolTip(tip)


    #   Uses Setting-defined Template to Search for Proxies
    @err_catcher(name=__name__)
    def searchForProxyFile(self):
        #   Get the Config Data
        sData = self.getSettings()
        proxySearchList = sData.get("proxySearch", [])

        #   Make the Various Names
        fullPath = self.getSource_mainfilePath()
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


    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def onProxyfileHashReady(self, result_hash):
        self.data["source_proxyFile_hash"] = result_hash
        # self.l_fileSize.setToolTip(f"Hash: {result_hash}")


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



#   FILE TILES ON THE DESTINATION SIDE (Inherits from BaseTileItem)
class DestFileItem(BaseTileItem):

    progressChanged = Signal(object)

    def __init__(self, browser, data):
        super(DestFileItem, self).__init__(browser, data)

        self.worker = None  # Placeholder for copy thread


    def mouseReleaseEvent(self, event):
        super(DestFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("DestFileItem")
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
        pxyIconPath = os.path.join(iconDir, "pxy_icon.png")
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

        #   File Size Layout
        self.fileSizeContainer = QWidget()
        self.lo_fileSize = QHBoxLayout()
        self.fileSizeContainer.setLayout(self.lo_fileSize)
        self.fileSizeContainer.setFixedWidth(150)

        #   File Size Labels
        self.l_size_copied = QLabel("--")
        self.l_size_dash = QLabel("of")
        self.l_size_total = QLabel("--")

        #    Add Sizes to Layout
        self.spacer2 = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lo_fileSize.addItem(self.spacer2)
        self.lo_fileSize.addWidget(self.l_size_copied)
        self.lo_fileSize.addWidget(self.l_size_dash)
        self.lo_fileSize.addWidget(self.l_size_total)

        #   Add Items to Bottom Layout
        self.lo_bottom.addWidget(self.l_icon, alignment=Qt.AlignVCenter)
        self.lo_bottom.addWidget(self.progressBar)
        self.lo_bottom.addWidget(self.fileSizeContainer)

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

        #   Reset Progress Bar
        tip = "Idle"
        self.setProgressBarStatus(status="idle", tooltip=tip)
        self.progressBar.setVisible(True)



    @err_catcher(name=__name__)
    def refreshUi(self):

        source_MainFilePath = self.getSource_mainfilePath()
        source_MainFileName = self.getBasename(source_MainFilePath)

        self.refreshPreview()

        icon = self.getIcon()
        self.setIcon(icon)

        self.setProxy()

        self.l_fileName.setText(source_MainFileName)

        tip = (f"Source File:  {source_MainFilePath}\n"
               f"Destination File:  {self.getDestPath()}")
        
        self.l_fileName.setToolTip(tip)

        self.l_size_total.setText(self.data["source_mainFile_size"])

        # Get File Path
        filePath = self.getSource_mainfilePath()
        self.l_fileName.setText(self.getBasename(filePath))
        self.l_fileName.setToolTip(f"FilePath:  {filePath}")

        #   Set Filetype Icon
        self.setIcon(self.data["icon"])

        self.refreshPreview()


    @err_catcher(name=__name__)
    def getDestPath(self):
        source_mainFilePath = self.getSource_mainfilePath()
        baseName = self.getBasename(source_mainFilePath)
        destDir = self.browser.l_destPath.text()
        destPath = os.path.join(destDir, baseName)
        return os.path.normpath(destPath)
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getCopiedSize(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{size_bytes / 1024 ** 3:.2f} GB"
        

    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def getProxy(self):
        return self.data.get("source_proxyFile_path", None)


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxy(self):
        proxy = self.getProxy()

        if proxy:
            self.l_pxyIcon.show()
            tip = (f"Proxy File detected:\n\n"
                   f"{proxy}")
            self.l_pxyIcon.setToolTip(tip)



    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def getDestProxyPath(self):
        source_mainFilePath = os.path.normpath(self.getSource_mainfilePath())
        source_proxyFilePath = os.path.normpath(self.data["source_proxyFile_path"])
        dest_MainFilePath = os.path.normpath(self.getDestPath())

        # Get the directory parts
        source_mainDir = os.path.dirname(source_mainFilePath)
        source_proxyDir = os.path.dirname(source_proxyFilePath)

        # Compute the relative path difference
        rel_proxyDir = os.path.relpath(source_proxyDir, source_mainDir)

        # Get just the proxy filename
        proxy_fileName = os.path.basename(source_proxyFilePath)

        # Apply the relative subdir to the dest main directory
        dest_mainDir = os.path.dirname(dest_MainFilePath)
        dest_proxyDir = os.path.join(dest_mainDir, rel_proxyDir)

        # Final proxy path
        dest_proxyFilePath = os.path.join(dest_proxyDir, proxy_fileName)

        return dest_proxyFilePath



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
    def setProgressBarStatus(self, status, tooltip=None):
        #   Set the Prog Bar Tooltip
        if tooltip:
            self.progressBar.setToolTip(tooltip)

        match status:
            case "idle":
                statusColor = COLOR_BLUE

            case "transferring":
                statusColor = COLOR_BLUE
        
            case "paused":
                statusColor = COLOR_GREY

            case "cancelled":
                statusColor = COLOR_RED

            case "complete":
                statusColor = COLOR_GREEN

            case "error":
                statusColor = COLOR_RED


        #   Convert Color to rgb format string
        color_str = f"rgb({statusColor.red()}, {statusColor.green()}, {statusColor.blue()})"
        
        #   Set Prog Bar StyleSheet
        self.progressBar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color_str};  /* Set the chunk color */
            }}
        """)


        #   Set Prog Bar StyleSheet
        # self.progressBar.setStyleSheet(f"""
        #     QProgressBar {{
        #         background-color: {color_str};  /* Set the background color */
        #     }}
        #     QProgressBar::chunk {{
        #         background-color: {color_str};  /* Set the chunk color */
        #         width: 20px;
        #     }}
        # """)


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)


        delAct = QAction("Remove from Transfer List", self.browser)
        delAct.triggered.connect(self.removeFromDestList)
        rcmenu.addAction(delAct)

        delAct = QAction("Show Data", self.browser)
        delAct.triggered.connect(self.TEST_SHOW_DATA)
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
    def TEST_SHOW_DATA(self):
        self.core.popup(self.data)


    @err_catcher(name=__name__)
    def removeFromDestList(self):
        self.browser.removeFromDestList(self.data)


    @err_catcher(name=__name__)
    def start_transfer(self, origin, destPath, options):
        self.isFinished = False
        
        tip = "Transfering"
        self.setProgressBarStatus("transferring", tooltip=tip)

        self.destPath = destPath

        copyData = {"sourcePath": self.getSource_mainfilePath(),
                    "destPath": self.getDestPath()}

        if options["copyProxy"] and self.data["hasProxy"]:
            copyData["sourceProxy"] = self.data["source_proxyFile_path"]
            copyData["destProxy"] = self.getDestProxyPath()

        self.worker = FileCopyWorker(copyData)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.copy_complete)
        self.worker.start()


    @err_catcher(name=__name__)
    def pause_transfer(self, origin):
        if self.worker and not self.isFinished:

            tip = "Paused"
            self.setProgressBarStatus("paused", tooltip=tip)

            self.worker.pause()
            # self.b_pause.setText("Resume")
            self.paused = True


    @err_catcher(name=__name__)
    def resume_transfer(self, origin):
        if self.worker and not self.isFinished:

            tip = "Transfering"
            self.setProgressBarStatus("transferring", tooltip=tip)

            self.worker.resume()
                # self.b_pause.setText("Pause")
            self.paused = False


    @err_catcher(name=__name__)
    def cancel_transfer(self, origin):
        if self.worker and not self.isFinished:

            tip = "Cancelled"
            self.setProgressBarStatus("cancelled", tooltip=tip)

            self.worker.cancel()
            # self.progressBar.setValue(0)
            # self.progressBar.setStyleSheet("background-color: rgb(255, 0, 0);")


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_progress(self, value, copied_size):
        self.progressBar.setValue(value)

        self.l_size_copied.setText(self.getCopiedSize(copied_size))


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def copy_complete(self, success):
        #   Sets Destination FilePath ToolTip
        self.l_fileName.setToolTip(os.path.normpath(self.destPath))

        if success:
            self.isFinished = True
            self.progressBar.setValue(100)

            if os.path.isfile(self.destPath):
                #   Calls for Hash Generation with Callback
                self.setFileHash(self.destPath, self.onDestHashReady)
                return
            else:
                hashMsg = "ERROR:  Transfer File Does Not Exist"
                status = "error"
                logger.warning(f"Transfer failed: {self.getSource_mainfilePath()}")
        else:
            hashMsg = "ERROR:  Transfer failed"
            status = "error"
            logger.warning(f"Transfer failed: {self.getSource_mainfilePath()}")

        # Final fallback (error case only)
        self.setProgressBarStatus(status, tooltip=hashMsg)


    #   Called After Hash Genertaion for UI Feedback
    @err_catcher(name=__name__)
    def onDestHashReady(self, dest_hash):
        orig_hash = self.data.get("source_mainFile_hash", None)

        if dest_hash == orig_hash:
            statusMsg = "Transfer Successful"
            status = "complete"
            logger.debug(f"Transfer complete: {self.getSource_mainfilePath()}")
        else:
            statusMsg = "ERROR:  Transfered Hash Incorrect"
            status = "error"
            logger.debug(f"Transfered Hash Incorrect: {self.getSource_mainfilePath()}")

        hashMsg = (f"Status: {statusMsg}\n\n"
                f"Source Hash:   {orig_hash}\n"
                f"Transfer Hash: {dest_hash}")

        self.setProgressBarStatus(status, tooltip=hashMsg)


#   FOLDER TILES (Inherits from BaseTileItem)
class FolderItem(BaseTileItem):
    def __init__(self, browser, data):
        super(FolderItem, self).__init__(browser, data)


    def mouseReleaseEvent(self, event):
        super(FolderItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("FolderItem")
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

        # self.refreshUi()


    @err_catcher(name=__name__)
    def refreshUi(self):
        # Set the icon and folder name
        dir_path = self.data["dirPath"]
        dir_icon = self.getIconByType(dir_path)

        # Set the icon on the left side
        self.l_icon.setPixmap(dir_icon.pixmap(32, 32))

        # Set the folder name (extract folder name from the path)
        folder_name = os.path.basename(dir_path)
        self.l_fileName.setText(folder_name)


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



###     Thumbnail Worker Thread

#   Signal object to communicate between threads and the main UI
class ThumbnailSignal(QObject):
    finished = Signal(QPixmap, str)

class ThumbnailWorker(QRunnable, QObject):
    finished = Signal()
    result = Signal(QPixmap)  # Only return final scaled pixmap now

    def __init__(self, filePath, getPixmapFromPath, supportedFormats,
                 width, height, getThumbnailPath, scalePixmapFunc):
        super().__init__()
        QObject.__init__(self)
        self.filePath = filePath
        self.getPixmapFromPath = getPixmapFromPath
        self.supportedFormats = supportedFormats
        self.width = width
        self.height = height
        self.getThumbnailPath = getThumbnailPath
        self.scalePixmapFunc = scalePixmapFunc

    @Slot()
    def run(self):
        thumb_semaphore.acquire()

        try:
            pixmap = None
            extension = os.path.splitext(self.filePath)[1].lower()

            if extension not in self.supportedFormats:
                file_info = QFileInfo(self.filePath)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)
                pixmap = icon.pixmap(self.width, self.height)
                fitIntoBounds = True
                crop = False
                scale = 0.5
                logger.debug(f"Using File Icon for Unsupported Format: {extension}")
            else:
                thumbPath = self.getThumbnailPath(self.filePath)
                if os.path.exists(thumbPath):
                    pixmap = QPixmap(thumbPath)
                else:
                    pixmap = self.getPixmapFromPath(
                        self.filePath,
                        width=self.width,
                        height=self.height,
                        colorAdjust=False
                    )
                fitIntoBounds = False
                crop = True
                scale = 1

            if pixmap:
                scaledPixmap = self.scalePixmapFunc(
                    pixmap,
                    self.width * scale,
                    self.height * scale,
                    fitIntoBounds=fitIntoBounds,
                    crop=crop
                )
                self.result.emit(scaledPixmap)

        finally:
            self.finished.emit()
            thumb_semaphore.release()


###     Hash Worker Thread

class FileHashWorkerSignals(QObject):
    finished = Signal(str)  # emits the final hash

class FileHashWorker(QRunnable):
    def __init__(self, filePath):
        super(FileHashWorker, self).__init__()
        self.filePath = filePath
        self.signals = FileHashWorkerSignals()

    def run(self):
        try:
            chunk_size = 8192
            hash_func = hashlib.sha256()
            with open(self.filePath, "rb") as f:
                hash_func.update(f.read(chunk_size))  # First chunk
                f.seek(-chunk_size, os.SEEK_END)      # Last chunk
                hash_func.update(f.read(chunk_size))
            file_size = os.path.getsize(self.filePath)
            hash_func.update(str(file_size).encode())
            result_hash = hash_func.hexdigest()
            self.signals.finished.emit(result_hash)
        except Exception as e:
            print(f"[FileHashWorker] Error hashing {self.filePath} - {e}")
            self.signals.finished.emit("Error")



###     Transfer Worker Thread

class FileCopyWorker(QThread):
    progress = Signal(int, float)
    finished = Signal(bool)

    def __init__(self, copyData):
        super().__init__()
        self.copyData = copyData

        self.running = True
        self.pause_flag = False
        self.cancel_flag = False
        self.last_emit_time = 0

    def pause(self):
        self.pause_flag = True

    def resume(self):
        self.pause_flag = False

    def cancel(self):
        self.cancel_flag = True

    def run(self):

        sourcePath = self.copyData["sourcePath"]
        destPath = self.copyData["destPath"]

        # if getattr(self, data["sourceProxy"]):
        #     sourceProxyPath = self.data["sourceProxy"]
        #     destProxyPath = self.data["destProxy"]


        try:
            total_size = os.path.getsize(sourcePath)
            copied_size = 0

            buffer_size = 1024 * 1024 * COPY_CHUNK_SIZE
            copy_semaphore.acquire()

            with open(sourcePath, 'rb') as fsrc, open(destPath, 'wb') as fdst:
                while True:
                    if self.cancel_flag:
                        self.finished.emit(False)
                        fdst.close()
                        os.remove(destPath)
                        return

                    if self.pause_flag:
                        time.sleep(0.1)
                        continue

                    chunk = fsrc.read(buffer_size)
                    if not chunk:
                        break

                    fdst.write(chunk)
                    copied_size += len(chunk)
                    progress_percent = int((copied_size / total_size) * 100)

                    now = time.time()
                    if now - self.last_emit_time >= PROG_UPDATE_INTV or progress_percent == 100:
                        self.progress.emit(progress_percent, copied_size)
                        self.last_emit_time = now

            self.finished.emit(True)

        except Exception as e:
            print(f"Error copying file: {e}")
            self.finished.emit(False)

        finally:
            copy_semaphore.release()
            self.running = False


