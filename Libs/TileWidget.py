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
import re
import hashlib
import subprocess
import platform
import shlex




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
    @property
    def thumb_threadpool(self):
        return self.browser.thumb_threadpool
    @property
    def dataOps_threadpool(self):
        return self.browser.dataOps_threadpool


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
            if "transferTime" not in self.data and self.destFileExists():                       #   TODO FIX
                borderColor = COLOR_ORANGE

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

        #   Combine Styles
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


    #   Gets the Number of Frames of the File(s) to Transfer
    @err_catcher(name=__name__)
    def setDuration(self, filePath, callback=None):
        #   Create Worker Instance
        worker_frames = FileDurationWorker(self, self.core, filePath)
        #   Connect to Finished Callback
        worker_frames.finished.connect(callback)
        #   Launch Worker in DataOps Treadpool
        self.dataOps_threadpool.start(worker_frames)


     #   Returns the Filepath
    @err_catcher(name=__name__)
    def getBasename(self, filePath):
        return os.path.basename(filePath)
    

    #   Gets Custom Hash of File in Separate Thread
    @err_catcher(name=__name__)
    def setFileHash(self, filePath, callback=None):
        #   Create Worker Instance
        worker_hash = FileHashWorker(filePath)
        #   Connect to Finished Callback
        worker_hash.finished.connect(callback)
        #   Launch Worker in DataOps Treadpool
        self.dataOps_threadpool.start(worker_hash)
    

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
        worker_thumb = ThumbnailWorker(
            self,
            filePath=filePath,
            getPixmapFromPath=self.core.media.getPixmapFromPath,
            supportedFormats=self.core.media.supportedFormats,
            width=self.itemPreviewWidth,
            height=self.itemPreviewHeight,
            getThumbnailPath=self.getThumbnailPath,
            scalePixmapFunc=self.core.media.scalePixmap
        )

        worker_thumb.setAutoDelete(True)
        worker_thumb.result.connect(self.updatePreview)
        self.thumb_threadpool.start(worker_thumb)
        

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
    

    #   Returns Bool if File in Prism Video Formats
    @err_catcher(name=__name__)
    def isVideo(self, path=None, ext=None):
        if path:
            _, extension = os.path.splitext(os.path.basename(path))
        elif ext:
            extension = ext
        else:
            extension = self.getFileExtension()
        
        return  extension.lower() in self.core.media.videoFormats

    
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

        self.main_transfer_worker = None
        self.worker_proxy = None
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
        #   Status Label
        self.l_transStatus = QLabel("Idle")

        #   Add Items to Top Layout
        self.lo_top.addWidget(self.chb_selected)
        self.lo_top.addWidget(self.l_fileName)
        self.lo_top.addStretch()
        self.lo_top.addWidget(self.l_transStatus)

        #   Create Bottom Layout
        self.lo_bottom = QHBoxLayout()

        #   File Type Icon
        self.l_icon = QLabel()

        #   Transfer Progress bar
        self.transferProgBar = QProgressBar()
        self.transferProgBar.setMinimum(0)
        self.transferProgBar.setMaximum(100)
        self.transferProgBar.setValue(0)
        self.transferProgBar.setFixedHeight(10)
        self.transferProgBar.setTextVisible(False)
        self.transferProgBar.setVisible(False)

        #   Proxy Progress bar
        self.proxyProgBar = QProgressBar()
        self.proxyProgBar.setMinimum(0)
        self.proxyProgBar.setMaximum(100)
        self.proxyProgBar.setValue(0)
        self.proxyProgBar.setFixedHeight(10)
        self.proxyProgBar.setTextVisible(False)
        self.proxyProgBar.setVisible(False)

        #   File Size Layout
        self.fileSizeContainer = QWidget()
        self.lo_fileSize = QHBoxLayout()
        self.fileSizeContainer.setLayout(self.lo_fileSize)
        self.fileSizeContainer.setFixedWidth(150)

        #   File Size Labels
        self.l_amountCopied = QLabel("--")
        self.l_size_dash = QLabel("of")
        self.l_amountTotal = QLabel("--")

        #    Add Sizes to Layout
        self.spacer2 = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lo_fileSize.addItem(self.spacer2)
        self.lo_fileSize.addWidget(self.l_amountCopied)
        self.lo_fileSize.addWidget(self.l_size_dash)
        self.lo_fileSize.addWidget(self.l_amountTotal)

        #   Add Items to Bottom Layout
        self.lo_bottom.addWidget(self.l_icon, alignment=Qt.AlignVCenter)
        self.lo_bottom.addWidget(self.transferProgBar)
        self.lo_bottom.addWidget(self.proxyProgBar)
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
        self.setTransferStatus(progBar="transfer", status="Idle")
        self.transferProgBar.setVisible(True)
        self.setTransferStatus(progBar="proxy", status="Idle")


    @err_catcher(name=__name__)
    def refreshUi(self):
        source_MainFilePath = self.getSource_mainfilePath()
        source_MainFileName = self.getBasename(source_MainFilePath)

        self.data["dest_mainFile_path"] = self.getDestMainPath()
        self.setProxyFile()

        self.l_fileName.setText(source_MainFileName)

        tip = (f"Source File:  {source_MainFilePath}\n"
               f"Destination File:  {self.getDestPath()}")
        self.l_fileName.setToolTip(tip)

        #   Set Filetype Icon
        self.setIcon(self.data["icon"])

        #   Set Size String
        if "source_mainFile_duration" in self.data:
            self.l_amountCopied.setText(str(self.data["source_mainFile_duration"]))
            self.l_size_dash.setText("frames -")
        self.l_amountTotal.setText(self.data["source_mainFile_size"])

        # Get File Path
        filePath = self.getSource_mainfilePath()
        self.l_fileName.setText(self.getBasename(filePath))
        self.l_fileName.setToolTip(f"FilePath:  {filePath}")

        self.toggleProxyProgbar()
        self.refreshPreview()


    #   Sets the FileName based on Name Modifiers
    @err_catcher(name=__name__)
    def toggleProxyProgbar(self):
        enabled = False

        if self.browser.proxyEnabled and self.isVideo():
            if self.browser.proxyMode == "copy":
                enabled = self.data.get("hasProxy", False)
            else:
                enabled = True
        
        self.useProxy = enabled
        self.proxyProgBar.setVisible(enabled)


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
    def getTimeElapsed(self):
        return (time.time() - self.transferStartTime)


    @err_catcher(name=__name__)
    def setTransferStatus(self, progBar, status, tooltip=None):
        self.transferState = status
        if progBar == "transfer":
            progWdget = self.transferProgBar
        elif progBar == "proxy":
            progWdget = self.proxyProgBar

        match status:
            case "Idle":
                statusColor = COLOR_BLUE
            case "Transferring":
                statusColor = COLOR_BLUE
            case "Transferring Proxy":
                statusColor = COLOR_BLUE
            case "Generating Proxy":
                statusColor = COLOR_BLUE
            case "Generating Hash":
                statusColor = COLOR_BLUE
            case "Queued":
                statusColor = COLOR_BLUE
            case "Paused":
                statusColor = COLOR_GREY
            case "Cancelled":
                statusColor = COLOR_RED
            case "Complete":
                statusColor = COLOR_GREEN
            case "Warning":
                statusColor = COLOR_ORANGE
            case "Error":
                statusColor = COLOR_RED
            case _:
                statusColor = COLOR_ORANGE

        #   Add Status to Widget UI
        self.l_transStatus.setText(status)

        #   Set the Prog Bar Tooltip
        if tooltip:
            progWdget.setToolTip(tooltip)
        else:
            progWdget.setToolTip(status)

        #   Convert Color to rgb format string
        color_str = f"rgb({statusColor})"
        
        #   Set Prog Bar StyleSheet
        progWdget.setStyleSheet(f"""
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
    @err_catcher(name=__name__)                                                             # TESTING
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
    def start_transfer(self, origin, options, proxyEnabled, proxyMode):
        #   Set and Lock Modes
        self.proxyEnabled = proxyEnabled
        self.proxyMode = proxyMode
        #   Setup Transfer UI
        self.l_amountCopied.setText("--")
        self.l_size_dash.setText("of")

        #   Create Transfer Dict for Use Later
        self.transferData = {
            "proxyEnabled": proxyEnabled,
            "copyProxy": False,
            "generateProxy": False
        }

        if proxyEnabled and self.isVideo():
            self.transferData["proxyMode"] = proxyMode

            #   Handle Copy Proxys
            if proxyMode == "copy" and self.data["hasProxy"]:
                self.transferData["copyProxy"] = True
                self.transferData["sourceProxy"] = self.data["source_proxyFile_path"]
                self.transferData["destProxy"] = self.getDestProxyPath()

            #   Handle Generate Proxys
            elif proxyMode == "generate":
                self.transferData["generateProxy"] = True
                self.transferData["proxySettings"] = options["proxySettings"]

            #   Handle Generate Missing Proxys
            elif proxyMode == "missing":
                if self.data["hasProxy"]:
                    self.transferData["copyProxy"] = True
                    self.transferData["sourceProxy"] = self.data["source_proxyFile_path"]
                    self.transferData["destProxy"] = self.getDestProxyPath()

                else:
                    self.transferData["generateProxy"] = True
                    self.transferData["proxySettings"] = options["proxySettings"]

        #   Get Main Paths
        sourcePath = self.getSource_mainfilePath()
        destPath = self.getDestMainPath()

        #   Start Timers
        self.transferTimer = QTimer(self)
        self.transferStartTime = time.time()

        #   Call Main File Transfer
        self.transferMainFile(sourcePath, destPath)


    
    @err_catcher(name=__name__)
    def transferMainFile(self, sourcePath, destPath):
        self.setTransferStatus(progBar="transfer", status="Queued")

        #   Call the Transfer Worker Thread for Main File
        self.main_transfer_worker = FileCopyWorker(self, "transfer", sourcePath, destPath)
        #   Connect the Progress Signals
        self.main_transfer_worker.progress.connect(self.update_main_transferProgress)
        self.main_transfer_worker.finished.connect(self.main_transfer_complete)
        #   Execute Transfer
        self.main_transfer_worker.start()


    @err_catcher(name=__name__)
    def _onTransferStart(self, transType):
        self.setTransferStatus(progBar=transType, status="Transferring")


    @err_catcher(name=__name__)
    def _onProxyGenStart(self):
        self.setTransferStatus(progBar="proxy", status="Generating Proxy")


    @err_catcher(name=__name__)
    def pause_transfer(self, origin):
        if self.main_transfer_worker and self.transferState != "Complete":
            self.setTransferStatus(progBar="transfer", status="Paused")
            self.transferTimer.stop()
            self.main_transfer_worker.pause()


    @err_catcher(name=__name__)
    def resume_transfer(self, origin):
        if self.main_transfer_worker and self.transferState == "Paused":
            self.setTransferStatus(progBar="transfer", status="Transferring")
            self.transferTimer.start()
            self.main_transfer_worker.resume()


    @err_catcher(name=__name__)
    def cancel_transfer(self, origin):
        if self.main_transfer_worker and self.transferState != "Complete":
            self.setTransferStatus(progBar="transfer", status="Cancelled")
            self.transferTimer.stop()
            self.main_transfer_worker.cancel()

        if self.worker_proxy:                                            #   TODO - FINISH IMPLEMENTATION
            self.worker_proxy.cancel()


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_main_transferProgress(self, value, copied_size):
        self.setTransferStatus(progBar="transfer", status="Transferring")

        self.transferProgBar.setValue(value)
        self.l_amountCopied.setText(self.getSizeString(copied_size))
        self.copied_size = copied_size


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyCopyProgress(self, value, frame):
        self.setTransferStatus(progBar="proxy", status="Transferring Proxy")

        self.proxyProgBar.setValue(value)
        self.l_amountCopied.setText(str(frame))


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyGenerateProgress(self, value, frame):
        self.setTransferStatus(progBar="proxy", status="Generating Proxy")

        self.proxyProgBar.setValue(value)
        self.l_amountCopied.setText(str(frame))



    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def main_transfer_complete(self, success):
        destMainPath = self.getDestMainPath()

        self.transferTimer.stop()
        self.data["transferTime"] = self.browser.getFormattedTimeStr(self.getTimeElapsed())

        #   Sets Destination FilePath ToolTip
        self.l_fileName.setToolTip(os.path.normpath(destMainPath))

        if success:
            self.transferProgBar.setValue(100)

            if os.path.isfile(destMainPath):
                self.setTransferStatus(progBar="transfer", status="Generating Hash")

                #   Calls for Hash Generation with Callback
                self.setFileHash(destMainPath, self.onDestHashReady)

                #   Do Nothing Else if Proxy Not Enabled
                if not self.proxyEnabled:
                    return

                if self.transferData["copyProxy"]:
                    self.transferProxy()

                #   Generate Proxy if Enabled
                if self.transferData["generateProxy"]:
                    self.l_amountCopied.setText("--")
                    self.l_size_dash.setText("of")
                    self.l_amountTotal.setText(str(self.data["source_mainFile_duration"]))

                    self.generateProxy()

                return
            
            else:
                errorMsg = "ERROR:  Transfer File Does Not Exist"
                logger.warning(f"Transfer failed: {destMainPath}")
        else:
            errorMsg = "ERROR:  Transfer failed"
            logger.warning(f"Transfer failed: {destMainPath}")

        # Final fallback (error case only)
        self.setTransferStatus(progBar="transfer", status="Error", tooltip=errorMsg)


    #   Generates Proxy with FFmpeg in a Worker Thread
    @err_catcher(name=__name__)
    def transferProxy(self):
        sourcePath = self.transferData["sourceProxy"]
        destPath = self.transferData["destProxy"]

        #   Call the Transfer Worker Thread for Main File
        self.proxy_transfer_worker = FileCopyWorker(self, "proxy", sourcePath, destPath)
        #   Connect the Progress Signals
        self.proxy_transfer_worker.progress.connect(self.update_proxyCopyProgress)
        self.proxy_transfer_worker.finished.connect(self.proxy_complete)
        #   Execute Transfer
        self.proxy_transfer_worker.start()


    #   Generates Proxy with FFmpeg in a Worker Thread
    @err_catcher(name=__name__)
    def generateProxy(self):
        settings = self.transferData["proxySettings"]

        #   Get File Paths
        input_path = self.getDestMainPath()
        input_dirName = os.path.dirname(input_path)
        proxy_Path = os.path.join(input_dirName, "proxy")

        #   Add Duration to settings Data
        settings["frames"] = self.data["source_mainFile_duration"]


        #   Call the Transfer Worker Thread
        self.worker_proxy = ProxyGenerationWorker(self, self.core, input_path, proxy_Path, settings)
        #   Connect the Progress Signals
        self.worker_proxy.progress.connect(self.update_proxyGenerateProgress)
        self.worker_proxy.finished.connect(self.proxy_complete)
        self.worker_proxy.start()


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def proxy_complete(self, success):
        if success:
            self.proxyProgBar.setValue(100)
            self.setTransferStatus(progBar="proxy", status="Complete", tooltip="Proxy Generated")

            return
            
            # else:
            #     hashMsg = "ERROR:  Transfer File Does Not Exist"
            #     logger.warning(f"Transfer failed: {destMainPath}")
        # else:
        #     hashMsg = "ERROR:  Transfer failed"
        #     logger.warning(f"Transfer failed: {destMainPath}")

        # Final fallback (error case only)
        # self.setTransferStatus(progBar="transfer", status="Error", tooltip=hashMsg)


    #   Called After Hash Genertaion for UI Feedback
    @err_catcher(name=__name__)
    def onDestHashReady(self, dest_hash):
        self.data["dest_mainFile_hash"] = dest_hash
        orig_hash = self.data.get("source_mainFile_hash", None)

        if dest_hash == orig_hash:
            statusMsg = "Transfer Successful"
            self.setTransferStatus(progBar="transfer", status="Complete")

            if self.useProxy:
                status = "Queued"
            else:
                status = "Complete"
            self.setTransferStatus(progBar="proxy", status=status)

            logger.debug(f"Transfer complete: {self.getSource_mainfilePath()}")
            return
            
        else:
            statusMsg = "ERROR:  Transfered Hash Incorrect"
            status = "Warning"
            logger.debug(f"Transfered Hash Incorrect: {self.getSource_mainfilePath()}")

        hashMsg = (f"Status: {statusMsg}\n\n"
                f"Source Hash:   {orig_hash}\n"
                f"Transfer Hash: {dest_hash}")
        
        self.setTransferStatus(progBar="transfer", status=status, tooltip=hashMsg)





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


####    THREAD WORKERS    ####

###     Thumbnail Worker Thread ###
class ThumbnailWorker(QObject, QRunnable):
    result = Signal(QPixmap)

    def __init__(self, origin, filePath, getPixmapFromPath, supportedFormats,
                 width, height, getThumbnailPath, scalePixmapFunc):
        QObject.__init__(self)
        QRunnable.__init__(self)

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
            self.origin.thumb_semaphore.release()



###     Hash Worker Thread    ###
class FileHashWorker(QObject, QRunnable):
    finished = Signal(str)

    def __init__(self, filePath):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.filePath = filePath


    @Slot()
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
            self.finished.emit(result_hash)

        except Exception as e:
            print(f"[FileHashWorker] Error hashing {self.filePath} - {e}")
            self.finished.emit("Error")



###     File Duration (Frames) Worker Thread    ###
class FileDurationWorker(QObject, QRunnable):                                #   TODO - FINISH DURATION FOR SEQUENCES
    finished = Signal(int)

    def __init__(self, origin, core, filePath):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.origin = origin
        self.core = core
        self.filePath = filePath


    @Slot()
    def run(self):
        try:
            extension = os.path.splitext(os.path.basename(self.filePath))[1].lower()

            frames = 1

            #   Return None if not Media File
            if extension not in self.core.media.supportedFormats:
                return
            
            #   Use ffProbe for Video Files
            if self.origin.isVideo(ext=extension):
                #   Get ffProbe path from Plugin Libs
                ffprobePath = self.origin.browser.getFFprobePath()

                kwargs = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text":   True,
                }

                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

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
                    **kwargs
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
            self.finished.emit(int(frames))

        except Exception as e:
            print(f"[Duration Worker] ERROR: {self.filePath} - {e}")
            self.finished.emit("Error")



###     Transfer Worker Thread     ###
class FileCopyWorker(QThread):
    progress = Signal(int, float)
    finished = Signal(bool)

    def __init__(self, origin, transType, sourcePath, destPath):
        super().__init__()
        
        self.origin = origin
        self.transType = transType
        self.sourcePath = sourcePath
        self.destPath = destPath

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
        try:
            total_size = os.path.getsize(self.sourcePath)
            copied_size = 0

            buffer_size = 1024 * 1024 * self.origin.size_copyChunk
            self.origin.copy_semaphore.acquire()

            #   Create Dir if Needed
            os.makedirs(os.path.dirname(self.destPath), exist_ok=True)

            #   Trigger Start UI
            self.origin._onTransferStart(self.transType)

            with open(self.sourcePath, 'rb') as fsrc, open(self.destPath, 'wb') as fdst:
                while True:
                    if self.cancel_flag:
                        self.finished.emit(False)
                        fdst.close()
                        os.remove(self.destPath)
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



###     Proxy Generation Worker Thread    ###
class ProxyGenerationWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool)

    def __init__(self, origin, core, inputPath, outputDir, settings=None):
        super().__init__()

        self.origin = origin
        self.core = core
        self.inputPath  = inputPath
        self.outputDir  = outputDir
        self.settings   = settings or {}

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
        ffmpegPath = self.core.media.getFFmpeg(validate=True)                           #   TODO - Handle Errors
        if not ffmpegPath:
            self.finished.emit(False)
            return

        #   Get Total Frames
        total_frames = int(self.settings.get("frames", 0))
        #   Abort if No Frames
        if total_frames <= 0:
            print("[ProxyWorker] Invalid total frame count!")                           #   TODO - Handle Errors
            self.finished.emit(False)
            return

        #   Get Settings
        output_ext   = self.settings.get("Output_Extension", "")
        vid_params   = self.settings.get("Video_Parameters", "")
        aud_params   = self.settings.get("Audio_Parameters", "")
        scale_str    = self.settings.get("scale", None)

        #   Make File Names/Paths
        input_baseFile  = os.path.basename(self.inputPath)
        input_baseName  = os.path.splitext(input_baseFile)[0]
        output_baseFile = input_baseName + output_ext
        outputPath      = os.path.join(self.outputDir, output_baseFile)

        #   Create Proxy Dir
        os.makedirs(os.path.dirname(outputPath), exist_ok=True)

        #   Check if Video or Image Sequence
        inputExt = os.path.splitext(os.path.basename(self.inputPath))[1].lower()
        videoInput = inputExt in [".mp4", ".mov", ".m4v"]

        #   Set Start Number
        if videoInput:
            #   Video Starts at 0
            startNum = 0
        else:
            #   Default to 25fps
            fps = "25"
            #   Get Project FPS 
            if self.core.getConfig("globals", "forcefps", configPath=self.core.prismIni):
                fps = self.core.getConfig("globals", "fps", configPath=self.core.prismIni)

            #   TODO STARTNUM   #

        startNum = str(startNum)


        ##  Build Arg List  ##

        #   Add FFmpeg path
        argList = [ffmpegPath]

        #   Add Input Path
        argList += ["-i", self.inputPath]

        #   Add Scaling
        if scale_str:
            if scale_str.endswith("%"):
                pct = float(scale_str.strip("%")) / 100.0
                # even dimensions to avoid odd/even misalignment:
                expr = f"scale=trunc(iw*{pct}/2)*2:trunc(ih*{pct}/2)*2"
            else:
                # assume user passed "1280:-1" or similar
                expr = f"scale={scale_str}"
            argList += ["-vf", expr]

        #   Split out Video and Audio Params from Passed Settings into Tokens and add to Args
        if vid_params:
            argList += shlex.split(vid_params)
        if aud_params:
            argList += shlex.split(aud_params)

        #   Add Output Path
        argList += [outputPath, "-y"]

        #   Set Shell True if Windows
        shell = (platform.system() == "Windows")

        # Regex to Catch FFmpeg output (e.g. "frame=  1234")
        frame_re = re.compile(r"frame=\s*(\d+)")

        #   Get Thread Slot
        self.origin.proxy_semaphore.acquire()

        self.origin._onProxyGenStart()

        #   Execute FFmpeg Command
        nProc = subprocess.Popen(
            argList,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=True,
            bufsize=1
        )

        # try:
        while True:
            # cancel?                                           #   TODO
            if self.cancel_flag:
                print("[ProxyWorker] Cancel flag detected, terminating FFmpeg.")
                nProc.terminate()
                try:
                    nProc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("[ProxyWorker] Killing FFmpeg.")
                    nProc.kill()
                self.finished.emit(False)
                return

            # pause?
            if self.pause_flag:
                time.sleep(0.1)
                continue

            #   Read Outputted Console Lines
            line = nProc.stderr.readline()
            if not line:
                break
            
            #   Get Frame from Regex
            match = frame_re.search(line)
            if match:
                current = int(match.group(1))
                #   Calculate Percentage from Current Frame and Total Frames
                pct = int((current / total_frames) * 100)

                #   Update Prog Bar at Specified Interval
                now = time.time()
                if (now - self.last_emit_time >= self.origin.progUpdateInterval) or (pct == 100):
                    #   Emit Percentage and Current Frame
                    self.progress.emit(pct, current)
                    self.last_emit_time = now

        nProc.wait()
        self.finished.emit(nProc.returncode == 0)

        # except Exception as e:
        #     print(f"[ProxyWorker] Exception: {e}")
        #     if nProc.poll() is None:
        #         nProc.kill()
        #     self.finished.emit(False)

        # finally:
        self.origin.proxy_semaphore.release()
        self.running = False

