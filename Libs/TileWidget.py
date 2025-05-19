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
import hashlib
from collections import OrderedDict
import subprocess
import platform



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

PRISMROOT = r"C:\Prism2"                                            ###   TODO
prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT

rootScripts = os.path.join(prismRoot, "Scripts")
pluginRoot = os.path.dirname(os.path.dirname(__file__))
pyLibsPath = os.path.join(pluginRoot, "PythonLibs")
uiPath = os.path.join(pluginRoot, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")
sys.path.append(os.path.join(rootScripts, "Libs"))
sys.path.insert(0, pyLibsPath)
sys.path.append(pluginRoot)
sys.path.append(uiPath)
# sys.path.append(os.path.join(pyLibsPath))

# if os.path.exists(os.path.join(pyLibsPath, "Python311")):                 #   TODO Add python libs check


import exiftool
EXIF_DIR = os.path.join(pyLibsPath, "ExifTool")

from PopupWindows import DisplayPopup


# from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)

#   Proxy Folder Names
PROXY_NAMES = ["proxy", "pxy", "proxies", "proxys"]                         #   TODO - move to Settings?

#   Colors
COLOR_GREEN = "0, 150, 0"
COLOR_BLUE = "115, 175, 215"
COLOR_ORANGE = "255, 140, 0"
COLOR_RED = "200, 0, 0"
COLOR_GREY = "100, 100, 100"




##   BASE FILE TILE FOR SHARED METHODS  ##
class BaseTileItem(QWidget):

    #   Signals
    signalSelect = Signal(object)
    signalReleased = Signal(object)

    #   Properties from the SourceTab Config Settings
    @property
    def max_thumbThreads(self):
        return self.browser.max_thumbThreads
    @property
    def thumb_semaphore(self):
        return self.browser.thumb_semaphore
    @property
    def copy_semaphore(self):
        return self.browser.copy_semaphore
    @property
    def size_copyChunk(self):
        return self.browser.size_copyChunk
    @property
    def proxy_semaphore(self):
        return self.browser.proxy_semaphore
    @property
    def progUpdateInterval(self):
        return self.browser.progUpdateInterval


    def __init__(self, browser, data):
        super(BaseTileItem, self).__init__()
        self.core = browser.core
        self.browser = browser
        self.data = data

        self.state = "deselected"

        self.setMouseTracking(True)

        #   Get ExifTool EXE
        self.exifToolEXE = self.findExiftool()

        #   Thumbnail Size
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69

        #   Sets Thread Pool
        self.threadPool = QThreadPool.globalInstance()
        #    Limit Max Threads
        self.threadPool.setMaxThreadCount(self.max_thumbThreads)


    #   Launches the Single-click File Action
    @err_catcher(name=__name__)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSelected()
        elif event.button() == Qt.RightButton:
            if self not in self.browser.selectedTiles:
                # Don't clear others, just add this one
                self.state = "selected"
                self.applyStyle(self.state)
                self.browser.selectedTiles.add(self)
                self.browser.lastClickedTile = self

        super().mousePressEvent(event)


    @err_catcher(name=__name__)
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)


    #   Launches the Double-click File Action
    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        child = self.childAt(event.pos())

        #   Thumbnail
        if child == self.l_preview:
            self.doubleClickFile(self.getSource_mainfilePath())
        #   Proxy Icon
        elif child == self.l_pxyIcon:
            self.doubleClickFile(self.getSource_proxyfilePath())
        #   Anywhere Else
        elif child == self.l_fileName:
            self.sendToViewer()
        else:
            self.toggleChecked()


    @err_catcher(name=__name__)
    def isSelected(self):
        return self.state == "selected"


    #   Sets the Tile State UnSelected
    @err_catcher(name=__name__)
    def deselect(self):
        if self.state != "deselected":
            self.state = "deselected"
            self.applyStyle(self.state)
    

    #   Sets the State Selected based on the Checkbox
    @err_catcher(name=__name__)
    def setSelected(self, checked=None):
        modifiers = QApplication.keyboardModifiers()

        # SHIFT: Select range from lastClickedTile to this one
        if modifiers & Qt.ShiftModifier and self.browser.lastClickedTile:
            self.selectRange()
            return

        # CTRL: Toggle this tile's selection
        elif modifiers & Qt.ControlModifier:
            if self in self.browser.selectedTiles:
                self.deselect()
                self.browser.selectedTiles.discard(self)
            else:
                self.state = "selected"
                self.applyStyle(self.state)
                self.setFocus()
                self.browser.selectedTiles.add(self)
            self.browser.lastClickedTile = self
            return

        # Default (no modifier): exclusive selection
        for tile in list(self.browser.selectedTiles):
            tile.deselect()
        self.browser.selectedTiles.clear()

        self.state = "selected"
        self.applyStyle(self.state)
        self.setFocus()
        self.browser.selectedTiles.add(self)
        self.browser.lastClickedTile = self

        #   Refresh Transfer Size
        self.browser.refreshTotalTransSize()


    @err_catcher(name=__name__)
    def selectRange(self):
        # Get all tiles in order
        if isinstance(self, SourceFileItem):
            allTiles = self.browser.getAllSourceTiles()
        elif isinstance(self, DestFileItem):
            allTiles = self.browser.getAllDestTiles()
        else:
            return
        
        try:
            start = allTiles.index(self.browser.lastClickedTile)
            end = allTiles.index(self)
        except ValueError:
            return

        if start > end:
            start, end = end, start

        # Deselect current selection
        for tile in self.browser.selectedTiles:
            tile.deselect()
        self.browser.selectedTiles.clear()

        # Select the range
        for tile in allTiles[start:end + 1]:
            tile.state = "selected"
            tile.applyStyle(tile.state)
            self.browser.selectedTiles.add(tile)

        self.browser.lastClickedTile = self


    #   Sets the Checkbox and sets the State
    @err_catcher(name=__name__)
    def setChecked(self, checked):
        if len(self.browser.selectedTiles) > 1:
            for tile in list(self.browser.selectedTiles):
                tile.chb_selected.setChecked(checked)
                tile.setSelected()
        
        else:
            self.chb_selected.setChecked(checked)
            self.setSelected()


    #   Toggles the Checkbox
    @err_catcher(name=__name__)
    def toggleChecked(self):
        currentState = self.isChecked()
        self.setChecked(not currentState)


    #   Checks the Checkbox
    @err_catcher(name=__name__)
    def isChecked(self):
        try:
            checked = self.chb_selected.isChecked()
        except:
            checked = False
        return checked


    @err_catcher(name=__name__)
    def enterEvent(self, event):
        if self.isSelected():
            self.applyStyle("hoverSelected")
        else:
            self.applyStyle("hover")


    @err_catcher(name=__name__)
    def leaveEvent(self, event):
        self.applyStyle(self.state)


    @err_catcher(name=__name__)
    def applyStyle(self, styleType):
        ###     BORDER      ###
        borderColor = "70, 90, 120"  # default fallback

        if self.tileType == "sourceTile":
            if self.isChecked():
                borderColor = COLOR_GREEN

        elif self.tileType == "destTile":
            if "transferTime" not in self.data and self.destFileExists():
                borderColor = COLOR_ORANGE

        # Construct base stylesheet with just the border
        borderStyle = f"""
            QWidget#FileTile {{
                border: 1px solid rgb({borderColor});
                border-radius: 10px;
            }}
        """

        ####    BACKGROUND      ####
        backgroundStyle = ""
        if styleType == "selected":
            backgroundStyle = """
                QWidget#FileTile {
                    background-color: rgba(115, 175, 215, 100);
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
            """
        elif styleType == "hoverSelected":
            backgroundStyle = """
                QWidget#FileTile {
                    background-color: rgba(115, 175, 215, 150);
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
            """
        elif styleType == "hover":
            backgroundStyle = """
                QWidget#FileTile, QWidget#FolderTile {
                    background-color: rgba(255, 255, 255, 20);
                }
                QWidget {
                    background-color: rgba(255, 255, 255, 0);
                }
            """

        # Combine styles
        fullStyle = borderStyle + backgroundStyle

        try:
            self.setStyleSheet(fullStyle)
        except RuntimeError:
            pass


    #   Opens the File in the OS
    @err_catcher(name=__name__)
    def doubleClickFile(self, filepath):
        self.browser.openInShell(filepath, prog="default")


    #   Returns the Tile Data
    @err_catcher(name=__name__)
    def getSettings(self):
        return self.browser.getSettings()
    

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
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getSizeString(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{size_bytes / 1024 ** 3:.2f} GB"


    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_mainfilePath(self):
        return self.data.get("source_mainFile_path", None)
    

    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_proxyfilePath(self):
        return self.data.get("source_proxyFile_path", None)
    

    #   Gets Thumbnail Save Path
    def getThumbnailPath(self, filepath):                                       #   TODO - USE CUSTOM PATH???
        thumbBasename = os.path.basename(os.path.splitext(filepath)[0]) + ".jpg"

        if self.browser.useCustomThumbPath:
            thumbDir = os.path.join(self.browser.customThumbPath, self.browser.createUUID(simple=True))
            if not os.path.exists(thumbDir):
                os.mkdir(thumbDir)

            thumbPath = os.path.join(thumbDir, thumbBasename)

        else:
            try:
                thumbPath = self.core.media.getThumbnailPath(filepath)
            except:
                thumbPath = os.path.join(os.path.dirname(filepath),"_thumbs", thumbBasename)

        return thumbPath 


    #   Returns the Size of the File(s) to Transfer
    @err_catcher(name=__name__)
    def getTransferSize(self, includeProxy=False):
        total_size = self.getFileSize(self.getSource_mainfilePath())
        if includeProxy and self.getSource_proxyfilePath():
            total_size += self.getFileSize(self.getSource_proxyfilePath())

        return total_size


    #   Returns the Numbr of Frames of the File(s) to Transfer
    @err_catcher(name=__name__)
    def setDuration(self, filePath, callback=None):
        framesWorker = FileDurationWorker(self, self.core, filePath)
        framesWorker.signals.finished.connect(callback)
        self.threadPool.start(framesWorker)


     #   Returns the Filepath
    @err_catcher(name=__name__)
    def getBasename(self, filePath):
        return os.path.basename(filePath)
    

    #   Gets Custom Hash of File in Separate Thread
    @err_catcher(name=__name__)
    def setFileHash(self, filePath, callback=None):
        hashWorker = FileHashWorker(filePath)
        hashWorker.signals.finished.connect(callback)
        self.threadPool.start(hashWorker)
    

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
        if hasattr(self.data, "thumbnail"):
            self.updatePreview(self.data["thumbnail"])
            return

        filePath = self.getSource_mainfilePath()

        # Create Worker Thread
        worker = ThumbnailWorker(
            self,
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
        self.data["thumbnail"] = scaledPixmap


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
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getFileSizeStr(self, size_bytes):
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
        # else:
        #     return self.data["color"]
        

    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        self.core.openFolder(path)


    @err_catcher(name=__name__)
    def findExiftool(self):
        possible_names = ["exiftool.exe", "exiftool(-k).exe"]

        for root, dirs, files in os.walk(EXIF_DIR):
            for file in files:
                if file.lower() in [name.lower() for name in possible_names]:
                    exifToolEXE = os.path.join(root, file)
                    logger.debug(f"ExifTool found at: {exifToolEXE}")
                    return exifToolEXE

        logger.warning(f"ERROR:  Unable to Find ExifTool")
        return None


    #   Returns File MetaData
    @err_catcher(name=__name__)
    def getMetadata(self, filePath):
        try:
            with exiftool.ExifTool(self.exifToolEXE) as et:
                metadata_list = et.execute_json("-G", filePath)

            if metadata_list:
                metadata = metadata_list[0]
                logger.debug(f"MetaData found for {filePath}")
                return metadata
            
            else:
                logger.warning(f"ERROR:  No metadata found for {filePath}")
                return {}

        except Exception as e:
            logger.warning(f"ERROR:  Failed to get metadata for {filePath}: {e}")
            return {}
        
        
    @err_catcher(name=__name__)
    def groupMetadata(self, metadata):
        """
        Groups metadata by the section tags (e.g., 'File', 'QuickTime', etc.)
        Returns a dictionary with grouped metadata.
        """
        grouped = {}
        
        for key, value in metadata.items():
            section = key.split(":")[0]
            tag = key.split(":")[1] if len(key.split(":")) > 1 else key
            
            if section not in grouped:
                grouped[section] = {}
            
            grouped[section][tag] = value
        
        return grouped


    @err_catcher(name=__name__)
    def displayMetadata(self, filePath):
        metadata = self.getMetadata(filePath)

        if metadata:
            grouped_metadata = self.groupMetadata(metadata)
            DisplayPopup.display(grouped_metadata, title="File Metadata")
        else:
            logger.warning("No metadata to display.")


    #   Get Media Player Enabled State
    @err_catcher(name=__name__)
    def isViewerEnabled(self):
        return self.browser.chb_enablePlayer.isChecked()


    #   Get Media Player Prefer Proxies State
    @err_catcher(name=__name__)
    def isPreferProxies(self):
        return self.browser.chb_preferProxies.isChecked()


    #   Sends the File to the Preview Viewer
    @err_catcher(name=__name__)
    def sendToViewer(self, filePath=None):
        if not self.isViewerEnabled():
            return
        
        #   Use passed file
        if filePath:
            sendFile = filePath
        else:
            #   Use Proxy if Proxy Exists and Prefer is Checked
            if self.isPreferProxies() and self.getSource_proxyfilePath():
                sendFile = self.getSource_proxyfilePath()
                isProxy = True
            #   Use Main File
            else:
                sendFile = self.getSource_mainfilePath()
                isProxy = False

        self.browser.mediaPlayer.updatePreview(sendFile, isProxy)



##   FILE TILES ON THE SOURCE SIDE (Inherits from BaseTileItem)     ##
class SourceFileItem(BaseTileItem):
    def __init__(self, browser, data):
        super(SourceFileItem, self).__init__(browser, data)
        self.tileType = "sourceTile"

        #   Calls the SetupUI Method of the Child Tile
        self.setupUi()
        #   Calls the Refresh Method of the Child Tile
        self.refreshUi()


    def mouseReleaseEvent(self, event):
        super(SourceFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("FileTile")
        self.applyStyle("deselected")
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
        self.lo_preview.setStackingMode(QStackedLayout.StackAll)

        #   Thumbnail Label (Main Image)
        self.l_preview = QLabel(self.thumbContainer)
        self.l_preview.setFixedSize(self.itemPreviewWidth, self.itemPreviewHeight)
        self.lo_preview.addWidget(self.l_preview)

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

        #   Frames Label
        self.l_frames = QLabel("")

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

        self.lo_bottom.addWidget(self.l_frames, alignment=Qt.AlignVCenter)

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

        #   Set Number of Frames
        fileType = self.browser.getFileType(filePath)
        if fileType in ["image", "video"]:
            self.setDuration(filePath, self.onMainfileDurationReady)

        #   Set Hash
        self.l_fileSize.setToolTip("Calculating file hash...")
        self.setFileHash(filePath, self.onMainfileHashReady)

        self.refreshPreview()
        self.setProxyFile()


    #   Populates Frames when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileDurationReady(self, duration):
        self.data["source_mainFile_duration"] = duration
        self.l_frames.setText(str(duration))


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
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)

        #   Displayed Always
        addlAct = QAction("Add to Transfer List", self.browser)
        addlAct.triggered.connect(self.addToDestList)
        rcmenu.addAction(addlAct)

        selAct = QAction("Set Selected", self.browser)
        selAct.triggered.connect(lambda: self.setChecked(True))
        rcmenu.addAction(selAct)

        unSelAct = QAction("Un-Select", self.browser)
        unSelAct.triggered.connect(lambda: self.setChecked(False))
        rcmenu.addAction(unSelAct)

        #   Displayed if Multi-Selection
        if len(self.browser.selectedTiles) == 1:
            mDataAct = QAction("Show All MetaData", self.browser)
            mDataAct.triggered.connect(lambda: self.displayMetadata(self.getSource_mainfilePath()))
            rcmenu.addAction(mDataAct)


            playerAct = QAction("Show in Player", self.browser)
            playerAct.triggered.connect(self.sendToViewer)
            rcmenu.addAction(playerAct)

            expAct = QAction("Open in Explorer", self)
            expAct.triggered.connect(lambda: self.openInExplorer(self.getSource_mainfilePath()))
            rcmenu.addAction(expAct)

        rcmenu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def addToDestList(self):
        if len(self.browser.selectedTiles) > 1:
            for tile in list(self.browser.selectedTiles):
                self.browser.addToDestList(tile.data)
        else:
            self.browser.addToDestList(self.data)
        
        self.browser.refreshDestItems()



##   FILE TILES ON THE DESTINATION SIDE (Inherits from BaseTileItem)    ##
class DestFileItem(BaseTileItem):
    def __init__(self, browser, data):
        super(DestFileItem, self).__init__(browser, data)
        self.tileType = "destTile"

        self.copyWorker = None
        self.transferState = None

        #   Calls the SetupUI Method of the Child Tile
        self.setupUi()
        #   Calls the Refresh Method of the Child Tile
        self.refreshUi()


    def mouseReleaseEvent(self, event):
        super(DestFileItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("FileTile")
        self.applyStyle("deselected")
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
        self.setTransferStatus(status="Idle")
        self.progressBar.setVisible(True)


    @err_catcher(name=__name__)
    def refreshUi(self):
        source_MainFilePath = self.getSource_mainfilePath()
        source_MainFileName = self.getBasename(source_MainFilePath)

        self.data["dest_mainFile_path"] = self.getDestMainPath()

        icon = self.getIcon()
        self.setIcon(icon)

        self.setProxyFile()

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


    #   Sets the FileName based on Name Modifiers
    @err_catcher(name=__name__)
    def nameOverride(self, override):
        source_MainFilePath = self.getSource_mainfilePath()
        source_MainFileName = self.getBasename(source_MainFilePath)

        if override:
            modName = self.getModifiedName(source_MainFileName)
            self.l_fileName.setText(modName)
        else:
            self.l_fileName.setText(source_MainFileName)

        
    @err_catcher(name=__name__)
    def getModifiedName(self, orig_name):
        return self.browser.applyMods(orig_name)
       

    #   Returns Proxy Source Path
    @err_catcher(name=__name__)
    def getProxy(self):
        return self.data.get("source_proxyFile_path", None)


    #   Sets Destination Proxy Filepath and Icon
    @err_catcher(name=__name__)
    def setProxyFile(self):
        if self.getProxy():
            #   Show Proxy Icon
            self.l_pxyIcon.show()

            #   Set Proxy Tooltip
            tip = (f"Proxy File detected:\n\n"
                   f"File: {self.data['source_proxyFile_path']}\n"
                   f"Date: {self.data['source_proxyFile_date']}\n"
                   f"Size: {self.data['source_proxyFile_size']}")
            self.l_pxyIcon.setToolTip(tip)

            self.data["dest_proxyFile_path"] = self.getDestProxyPath()



    #   Returns Destination Directory
    @err_catcher(name=__name__)
    def getDestPath(self):
        return os.path.normpath(self.browser.le_destPath.text())


    #   Returns the Destination Mainfile Path
    @err_catcher(name=__name__)
    def getDestMainPath(self):
        sourceMainPath = self.getSource_mainfilePath()
        baseName = self.getBasename(sourceMainPath)

        #   Modifiy Name is Enabled
        if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
            baseName = self.getModifiedName(baseName)

        destPath = self.getDestPath()

        return os.path.join(destPath, baseName)
    

     #   Checks if File Exists at Destination
    @err_catcher(name=__name__)
    def destFileExists(self):   
        return os.path.exists(self.getDestMainPath())
    

    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def getDestProxyPath(self):
        source_mainFilePath = os.path.normpath(self.getSource_mainfilePath())
        source_proxyFilePath = os.path.normpath(self.data["source_proxyFile_path"])
        dest_MainFilePath = os.path.normpath(self.getDestMainPath())

        # Get the directory parts
        source_mainDir = os.path.dirname(source_mainFilePath)
        source_proxyDir = os.path.dirname(source_proxyFilePath)

        # Compute the relative path difference
        rel_proxyDir = os.path.relpath(source_proxyDir, source_mainDir)

        # Get just the proxy filename
        proxy_fileName = os.path.basename(source_proxyFilePath)

        #   Modifiy Name is Enabled
        if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
            proxy_fileName = self.getModifiedName(proxy_fileName)

        # Apply the relative subdir to the dest main directory
        dest_mainDir = os.path.dirname(dest_MainFilePath)
        dest_proxyDir = os.path.join(dest_mainDir, rel_proxyDir)

        # Final proxy path
        dest_proxyFilePath = os.path.join(dest_proxyDir, proxy_fileName)

        return dest_proxyFilePath


    @err_catcher(name=__name__)
    def setTransferStatus(self, status, tooltip=None):
        self.transferState = status

        match status:
            case "Idle":
                statusColor = COLOR_BLUE
            case "Transferring":
                statusColor = COLOR_BLUE
            case "Paused":
                statusColor = COLOR_GREY
            case "Cancelled":
                statusColor = COLOR_RED
            case "Complete":
                statusColor = COLOR_GREEN
            case "Issue":
                statusColor = COLOR_ORANGE
            case "Error":
                statusColor = COLOR_RED

        #   Set the Prog Bar Tooltip
        if tooltip:
            self.progressBar.setToolTip(tooltip)
        else:
            self.progressBar.setToolTip(status)

        #   Convert Color to rgb format string
        color_str = f"rgb({statusColor})"
        
        #   Set Prog Bar StyleSheet
        self.progressBar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color_str};  /* Set the chunk color */
            }}
        """)


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)

        #   Displayed Always
        delAct = QAction("Remove from Transfer List", self.browser)
        delAct.triggered.connect(self.removeFromDestList)
        rcmenu.addAction(delAct)

        selAct = QAction("Set Selected", self.browser)
        selAct.triggered.connect(lambda: self.setChecked(True))
        rcmenu.addAction(selAct)

        unSelAct = QAction("Un-Select", self.browser)
        unSelAct.triggered.connect(lambda: self.setChecked(False))
        rcmenu.addAction(unSelAct)

        #   Displayed if Multi-Selection
        if len(self.browser.selectedTiles) == 1:
            showDataAct = QAction("Show Data", self.browser)                         #   TESTING
            showDataAct.triggered.connect(self.TEST_SHOW_DATA)
            rcmenu.addAction(showDataAct)

            #   If Transferred Files Exists
            if os.path.exists(self.getDestMainPath()):
                mDataAct = QAction("Show All MetaData", self.browser)
                mDataAct.triggered.connect(lambda: self.displayMetadata(self.getDestMainPath()))
                rcmenu.addAction(mDataAct)

                expAct = QAction("Open Transferred File in Explorer", self)
                expAct.triggered.connect(lambda: self.openInExplorer(self.getDestMainPath()))
                rcmenu.addAction(expAct)

        rcmenu.exec_(QCursor.pos())



    ####    TEMP TESTING    ####
    @err_catcher(name=__name__)                                                  # TESTING
    def TEST_SHOW_DATA(self):
        if not hasattr(self, "data") or not isinstance(self.data, dict):
            self.core.popup("No data to display or 'data' is not a dictionary.")
            return

        data_str = "\n\n".join(f"{key}: {value}" for key, value in self.data.items())
        self.core.popup(data_str)
    ####    ^^^^^^^^^^^^^    ####



    @err_catcher(name=__name__)
    def removeFromDestList(self):
        if len(self.browser.selectedTiles) > 1:
            for tile in list(self.browser.selectedTiles):
                self.browser.removeFromDestList(tile.data)
        else:
            self.browser.removeFromDestList(self.data)

        self.browser.refreshDestItems()


    @err_catcher(name=__name__)
    def start_transfer(self, origin, options):
        self.setTransferStatus("Transferring")

        self.transferTimer = QTimer(self)
        self.transferStartTime = time.time()

        copyData = {"sourcePath": self.getSource_mainfilePath(),
                    "destPath": self.getDestMainPath(),
                    "hasProxy": False}

        if options["copyProxy"] and self.data["hasProxy"]:
            copyData["hasProxy"] = True
            copyData["sourceProxy"] = self.data["source_proxyFile_path"]
            copyData["destProxy"] = self.getDestProxyPath()

            destProxyDir = os.path.dirname(self.getDestProxyPath())
            if not os.path.exists(destProxyDir):
                os.makedirs(destProxyDir)

        self.data["generateProxy"] = options["generateProxy"]
        if options["generateProxy"]:
            self.data["proxySettings"] = options["proxySettings"]
        
        #   Call the Transfer Worker Thread
        self.copyWorker = FileCopyWorker(self, copyData)
        #   Connect the Progress Signals
        self.copyWorker.progress.connect(self.update_progress)
        self.copyWorker.finished.connect(self.copy_complete)
        self.copyWorker.start()


    @err_catcher(name=__name__)
    def pause_transfer(self, origin):
        if self.copyWorker and self.transferState != "Complete":
            self.setTransferStatus("Paused")
            self.transferTimer.stop()
            self.copyWorker.pause()


    @err_catcher(name=__name__)
    def resume_transfer(self, origin):
        if self.copyWorker and self.transferState == "Paused":
            self.setTransferStatus("Transferring")
            self.transferTimer.start()
            self.copyWorker.resume()


    @err_catcher(name=__name__)
    def cancel_transfer(self, origin):
        if self.copyWorker and self.transferState != "Complete":
            self.setTransferStatus("Cancelled")
            self.transferTimer.stop()
            self.copyWorker.cancel()

        if self.proxyWorker:                                            #   TODO - FINISH IMPLEMENTATION
            self.proxyWorker.cancel()


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_progress(self, value, copied_size):
        self.progressBar.setValue(value)
        self.l_size_copied.setText(self.getSizeString(copied_size))
        self.copied_size = copied_size


    @err_catcher(name=__name__)
    def getTimeElapsed(self):
        return (time.time() - self.transferStartTime)
    

    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def copy_complete(self, success):
        destMainPath = self.getDestMainPath()

        self.transferTimer.stop()
        self.data["transferTime"] = self.browser.getFormattedTimeStr(self.getTimeElapsed())

        #   Sets Destination FilePath ToolTip
        self.l_fileName.setToolTip(os.path.normpath(destMainPath))

        if success:
            self.progressBar.setValue(100)

            if os.path.isfile(destMainPath):
                #   Calls for Hash Generation with Callback
                self.setFileHash(destMainPath, self.onDestHashReady)



                if self.data["generateProxy"]:
                    self.generateProxy(self.data["proxySettings"])
                return
            

            
            else:
                hashMsg = "ERROR:  Transfer File Does Not Exist"
                logger.warning(f"Transfer failed: {destMainPath}")
        else:
            hashMsg = "ERROR:  Transfer failed"
            logger.warning(f"Transfer failed: {destMainPath}")

        # Final fallback (error case only)
        self.setTransferStatus("Error", tooltip=hashMsg)


    #   Called After Hash Genertaion for UI Feedback
    @err_catcher(name=__name__)
    def onDestHashReady(self, dest_hash):
        self.data["dest_mainFile_hash"] = dest_hash
        orig_hash = self.data.get("source_mainFile_hash", None)

        if dest_hash == orig_hash:
            statusMsg = "Transfer Successful"
            status = "Complete"
            logger.debug(f"Transfer complete: {self.getSource_mainfilePath()}")
        else:
            statusMsg = "ERROR:  Transfered Hash Incorrect"
            status = "Issue"
            logger.debug(f"Transfered Hash Incorrect: {self.getSource_mainfilePath()}")

        hashMsg = (f"Status: {statusMsg}\n\n"
                f"Source Hash:   {orig_hash}\n"
                f"Transfer Hash: {dest_hash}")

        self.setTransferStatus(status, tooltip=hashMsg)



    @err_catcher(name=__name__)
    def generateProxy(self, settings):

        inputPath = self.getDestMainPath()
        input_baseFile = os.path.basename(inputPath)
        input_dirName = os.path.dirname(inputPath)
        proxy_Path = os.path.join(input_dirName, "proxy")
        input_baseName = os.path.splitext(input_baseFile)[0]

        outputPath = os.path.join(proxy_Path, input_baseName + ".mp4")

        #   Call the Transfer Worker Thread
        self.proxyWorker = ProxyGenerationWorker(self, self.core, inputPath, outputPath, settings)
        #   Connect the Progress Signals
        self.copyWorker.progress.connect(self.update_progress)
        self.copyWorker.finished.connect(self.copy_complete)
        self.proxyWorker.start()








##   FOLDER TILES (Inherits from BaseTileItem)  ##
class FolderItem(BaseTileItem):
    def __init__(self, browser, data):
        super(FolderItem, self).__init__(browser, data)
        self.tileType = "folderTile"

        #   Calls the SetupUI Method of the Child Tile
        self.setupUi()
        #   Calls the Refresh Method of the Child Tile
        self.refreshUi()


    def mouseReleaseEvent(self, event):
        super(FolderItem, self).mouseReleaseEvent(event)
        self.signalReleased.emit(self)
        event.accept()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.setObjectName("FolderTile")
        self.applyStyle(self.state)
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
    def mouseDoubleClickEvent(self, event):
        self.browser.doubleClickFolder(self.data["dirPath"], mode="source")


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        pass



###     Thumbnail Worker Thread

#   Signal object to communicate between threads and the main UI
class ThumbnailSignal(QObject):
    finished = Signal(QPixmap, str)

class ThumbnailWorker(QRunnable, QObject):
    finished = Signal()
    result = Signal(QPixmap)  # Only return final scaled pixmap now

    def __init__(self, origin, filePath, getPixmapFromPath, supportedFormats,
                 width, height, getThumbnailPath, scalePixmapFunc):
        super().__init__()
        QObject.__init__(self)
        self.origin = origin
        self.filePath = filePath
        self.getPixmapFromPath = getPixmapFromPath
        self.supportedFormats = supportedFormats
        self.width = width
        self.height = height
        self.getThumbnailPath = getThumbnailPath
        self.scalePixmapFunc = scalePixmapFunc

    @Slot()
    def run(self):
        self.origin.thumb_semaphore.acquire()

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
            self.origin.thumb_semaphore.release()



###     Hash Worker Thread
class FileHashWorkerSignals(QObject):
    finished = Signal(str)

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



###     File Duration (Frames) Worker Thread
class FileDurationWorkerSignals(QObject):
    finished = Signal(int)

class FileDurationWorker(QRunnable):                                #   TODO - FINISH DURATION FOR SEQUENCES
    def __init__(self, origin, core, filePath):
        super(FileDurationWorker, self).__init__()
        self.origin = origin
        self.core = core
        self.filePath = filePath
        self.signals = FileDurationWorkerSignals()


    def run(self):
        try:
            extension = os.path.splitext(os.path.basename(self.filePath))[1].lower()

            frames = 1

            #   Return None if not Media File
            if extension not in self.core.media.supportedFormats:
                return
            
            #   Use ffProbe for Video Files
            if extension in self.core.media.videoFormats:
                #   Get ffProbe path from Plugin Libs
                ffprobePath = self.origin.browser.getFFprobePath()

                #   Execute Quick Method
                result = subprocess.run(
                    [
                        ffprobePath,
                        "-v", "error",
                        "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames",
                        "-of", "default=nokey=1:noprint_wrappers=1",
                        self.filePath
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                #   Get Frames from Output
                frames = result.stdout.strip()

                #   If Quick Method didnt work, try Slower Fallback Method
                if frames == 'N/A' or not frames.isdigit():
                    result = subprocess.run(
                        [
                            ffprobePath,
                            "-v", "error",
                            "-select_streams", "v:0",
                            "-count_frames",
                            "-show_entries", "stream=nb_read_frames",
                            "-of", "default=nokey=1:noprint_wrappers=1",
                            self.filePath
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    frames = result.stdout.strip()

            else:                                                   #   TODO - Add Sequence Count
                baseFile = os.path.basename(self.filePath)
                seq = self.core.media.detectSequence(self.filePath, baseFile=baseFile)
                # frames = len(seq)


            #   Emit Frames to Main Thread
            self.signals.finished.emit(int(frames))

        except Exception as e:
            print(f"[Duration Worker] ERROR: {self.filePath} - {e}")
            self.signals.finished.emit("Error")



###     Transfer Worker Thread
class FileCopyWorker(QThread):
    progress = Signal(int, float)
    finished = Signal(bool)

    def __init__(self, origin, copyData):
        super().__init__()
        self.origin = origin
        self.copyData = copyData
        self.hasProxy = self.copyData["hasProxy"]

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

        if self.hasProxy:
            sourceProxyPath = self.copyData["sourceProxy"]
            destProxyPath = self.copyData["destProxy"]

        try:

            paths_to_copy = [(sourcePath, destPath)]

            if self.hasProxy:
                sourceProxyPath = self.copyData["sourceProxy"]
                destProxyPath = self.copyData["destProxy"]

                paths_to_copy.append((sourceProxyPath, destProxyPath))

            total_size = sum(os.path.getsize(src) for src, _ in paths_to_copy)
            copied_size = 0

            buffer_size = 1024 * 1024 * self.origin.size_copyChunk
            self.origin.copy_semaphore.acquire()

            for src_path, dst_path in paths_to_copy:
                with open(src_path, 'rb') as fsrc, open(dst_path, 'wb') as fdst:
                    while True:
                        if self.cancel_flag:
                            self.finished.emit(False)
                            fdst.close()
                            os.remove(dst_path)
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
                        if now - self.last_emit_time >= self.origin.progUpdateInterval or progress_percent == 100:
                            self.progress.emit(progress_percent, copied_size)
                            self.last_emit_time = now

            self.finished.emit(True)

        except Exception as e:
            print(f"Error copying file: {e}")
            self.finished.emit(False)

        finally:
            self.origin.copy_semaphore.release()
            self.running = False




###     Transfer Worker Thread
class ProxyGenerationWorker(QThread):
    progress = Signal(int, float)
    finished = Signal(bool)

    def __init__(self, origin, core, inputPath, outputPath, settings=None):
        super().__init__()
        self.origin = origin
        self.core = core
        self.origin = origin

        self.inputPath = inputPath
        self.outputPath = outputPath
        self.settings = settings

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

        ffmpegPath = self.core.media.getFFmpeg(validate=True)

        if not ffmpegPath:
            self.finished.emit(False)
            return "ERROR:  FFMPEG is not Found"
        
        startNum = 0


        inputExt = os.path.splitext(os.path.basename(self.inputPath))[1].lower()
        outputExt = os.path.splitext(os.path.basename(self.outputPath))[1].lower()


        videoInput = inputExt in [".mp4", ".mov", ".m4v"]
        startNum = str(startNum) if startNum is not None else None

        if not os.path.exists(os.path.dirname(self.outputPath)):
            try:
                os.makedirs(os.path.dirname(self.outputPath))
            except FileExistsError:
                pass

        if videoInput:
            args = OrderedDict(
                [
                    ("-apply_trc", "iec61966_2_1"),
                    ("-i", self.inputPath),
                    ("-pix_fmt", "yuva420p"),
                    ("-start_number", startNum),
                ]
            )

        else:
            fps = "25"
            if self.core.getConfig(
                "globals", "forcefps", configPath=self.core.prismIni
            ):
                fps = self.core.getConfig(
                    "globals", "fps", configPath=self.core.prismIni
                )

            args = OrderedDict(
                [
                    ("-start_number", startNum),
                    ("-framerate", fps),
                    ("-apply_trc", "iec61966_2_1"),
                    ("-i", self.inputPath),
                    ("-pix_fmt", "yuva420p"),
                    ("-start_number_out", startNum),
                ]
            )

            if startNum is None:
                args.popitem(last=False)
                args.popitem(last=True)

        if outputExt == ".jpg":
            quality = self.core.getConfig(
                "media", "jpgCompression", dft=4, config="project"
            )
            args["-qscale:v"] = str(quality)

        if outputExt == ".mp4":
            quality = self.core.getConfig(
                "media", "mp4Compression", dft=18, config="project"
            )
            args["-crf"] = str(quality)

        if self.settings:
            args.update(self.settings)

        argList = [ffmpegPath]

        for k in args.keys():
            if not args[k]:
                continue

            if isinstance(args[k], list):
                al = [k]
                al.extend([str(x) for x in args[k]])
            else:
                val = str(args[k])
                if k == "-start_number_out":
                    k = "-start_number"
                al = [k, val]

            argList += al

        argList += [self.outputPath, "-y"]
        if platform.system() == "Windows":
            shell = True
        else:
            shell = False


        self.origin.proxy_semaphore.acquire()


        nProc = subprocess.Popen(
            argList,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=True,
            bufsize=1
        )

        try:
            while True:
                # Check for cancellation
                if self.cancel_flag:
                    print("[ProxyWorker] Cancel flag detected, terminating FFmpeg.")
                    nProc.terminate()
                    try:
                        nProc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print("[ProxyWorker] FFmpeg did not terminate cleanly, killing.")
                        nProc.kill()
                    self.finished.emit(False)
                    return

                line = nProc.stderr.readline()
                if not line:
                    break
                print(line.strip())  # Or handle progress parsing here

            nProc.wait()

            if nProc.returncode == 0:
                self.finished.emit(True)
            else:
                print(f"[ProxyWorker] FFmpeg exited with code {nProc.returncode}")
                self.finished.emit(False)

        except Exception as e:
            print(f"[ProxyWorker] Exception: {e}")
            if nProc.poll() is None:
                nProc.kill()
            self.finished.emit(False)

        finally:
            self.origin.proxy_semaphore.release()
            self.running = False