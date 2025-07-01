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
#                SOURCE TAB PLUGIN
#
#                 Joshua Breckeen
#                    Alta Arts
#                josh@alta-arts.com
#
#   This PlugIn adds an additional Main Tab to the
#   Prism Standalone Project Browser.
#
#   This adds functionality to Ingest Media such as Camera clips,
#   as well as handling Proxy's and Metadata.
#
#
####################################################


import os
import sys
import logging
import time
import re
import hashlib
import subprocess
import psutil
import signal
import platform
import shlex
from pathlib import Path



from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if sys.version[0] == "3":
    pVersion = 3
else:
    pVersion = 2


prismRoot = os.getenv("PRISM_ROOT")

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


from PopupWindows import DisplayPopup
from ElapsedTimer import ElapsedTimer


# from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


#   Colors
COLOR_GREEN = "0, 150, 0"
COLOR_BLUE = "115, 175, 215"
COLOR_ORANGE = "255, 140, 0"
COLOR_RED = "200, 0, 0"
COLOR_GREY = "100, 100, 100"



#########   TESTING FUNCTIONS   ############
#   StopWatch Decorator
def stopWatch(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        timer = QElapsedTimer()
        timer.start()
        
        result = func(*args, **kwargs)
        
        elapsed_sec = round(timer.elapsed() / 1000.0, 2)
        print(f"[STOPWATCH]: Method '{func.__name__}' took {elapsed_sec:.2f} seconds")
        
        return result
    return wrapper

def _debug_recursive_print(data: object, label: str = None) -> None:
    """
    Recursively print nested dictionaries and lists with indentation for debugging.

    data:   object to inspect
    label:  text name of object to display (optional)
    """

    def _print_nested(d, indent=0):
        prefix = "    " * indent
        if isinstance(d, dict):
            for key, value in d.items():
                if isinstance(value, (dict, list)):
                    print(f"{prefix}{key}:")
                    _print_nested(value, indent + 1)
                else:
                    print(f"{prefix}{key}: {value}")
        elif isinstance(d, list):
            for item in d:
                _print_nested(item, indent)
        else:
            print(f"{prefix}{d}")

    try:
        print("\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        if label:
            print(f"Object: '{label}':\n")
        _print_nested(data)
    finally:
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n")

###########################################




##   BASE FILE TILE FOR SHARED METHODS  ##
class BaseTileItem(QWidget):

    #   Signals
    signalSelect = Signal(object)
    signalReleased = Signal(object)

    thumbnailReady = Signal(object)
    durationReady = Signal(object)
    hashReady = Signal(object)


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


    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(BaseTileItem, self).__init__(parent)

        self.core = browser.core
        self.browser = browser

        self.state = "deselected"

        self.setMouseTracking(True)

        #   Thumbnail Size
        self.itemPreviewWidth = 120
        self.itemPreviewHeight = 69

        logger.debug("Loaded Base Tile Item")


    #   Launches the Single-click File Action
    @err_catcher(name=__name__)
    def mousePressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()

        if event.button() == Qt.LeftButton:
            self.setSelected()  # Already handles Ctrl/Shift logic
            return

        elif event.button() == Qt.RightButton:
            # If this item is already selected, keep the current selection
            if self in self.browser.selectedTiles:
                # Just update lastClickedTile for consistency
                self.browser.lastClickedTile = self
                return

            # Otherwise, no modifiers -> reset selection to just this tile
            for tile in list(self.browser.selectedTiles):
                tile.deselect()
            self.browser.selectedTiles.clear()

            self.state = "selected"
            self.applyStyle(self.state)
            self.browser.selectedTiles.add(self)
            self.browser.lastClickedTile = self
            return

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
        try:
            modifiers = QApplication.keyboardModifiers()

            #   SHIFT: Select range from lastClickedTile to this one
            if modifiers & Qt.ShiftModifier and self.browser.lastClickedTile:
                self._selectRange()
                return

            #   CTRL: Toggle this tile's selection
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

            #   Default (no modifier): exclusive selection
            for tile in list(self.browser.selectedTiles):
                tile.deselect()
            self.browser.selectedTiles.clear()

            self.state = "selected"
            self.applyStyle(self.state)
            self.setFocus()
            self.browser.selectedTiles.add(self)
            self.browser.lastClickedTile = self

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Item(s) Selected:\n{e}")


    @err_catcher(name=__name__)
    def _selectRange(self):
        # Get all tiles in order
        if isinstance(self, SourceFileTile):
            allTiles = self.browser.getAllSourceTiles()
        elif isinstance(self, DestFileTile):
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
    def setChecked(self, checked, refresh=True):
        if len(self.browser.selectedTiles) > 1:
            for tile in list(self.browser.selectedTiles):
                tile.chb_selected.setChecked(checked)
        else:
            self.chb_selected.setChecked(checked)

        #   Refresh Transfer Size
        if refresh and self.tileType == "destTile":
            self.browser.refreshTotalTransSize()


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
        ###   BORDER  ###
        DEFAULT_BORDER   = "70, 90, 120"

        #   Set Default
        borderColor = DEFAULT_BORDER

        #   If Tile is Checked
        if self.isChecked():
            borderColor = COLOR_GREEN

        #   If Dest Tile File Exists
        elif self.tileType == "destTile" and self.transferState == "Idle" and self.destFileExists():
            borderColor = COLOR_ORANGE

        #   Create Border Style
        borderStyle = f"""
            QWidget#FileTile {{
                border: 1px solid rgb({borderColor});
                border-radius: 10px;
            }}
        """

        ###   BACKGROUND   ###
        #   Default Background Color
        baseColor = "69, 105, 129"

        #   If Tile is Checked
        if self.isChecked() and self.browser.transferState == "Idle":
            baseColor = COLOR_GREEN

        #   If Dest Tile File Exists
        if (self.tileType == "destTile" and self.transferState == "Idle" and self.destFileExists()):
            baseColor = COLOR_ORANGE

        #   Alpha Values Based on Passed StyleType
        alpha_map = {
            "deselected":   20,
            "hover":        50,
            "selected":     60,
            "hoverSelected":75,
        }
        alpha = alpha_map.get(styleType, 20)

        #   Create Background Style
        backgroundStyle = f"""
            QWidget#FileTile {{
                background-color: rgba({baseColor}, {alpha});
            }}
            QWidget {{
                background-color: rgba(255, 255, 255, 0);
            }}
        """

        #   Combine and Apply Border and Background
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
    def getSettings(self, key=None):
        return self.browser.getSettings(key=key)
    

    #   Saves Data to Settings
    @err_catcher(name=__name__)
    def saveSettings(self, key=None, data=None):
        self.browser.plugin.saveSettings(key=key, data=data)
    

    #   Returns the Tile Data
    @err_catcher(name=__name__)
    def getData(self):
        return self.data



    ####    TEMP TESTING    ####                                                      # TESTING
    @err_catcher(name=__name__)
    def TEST_SHOW_DATA(self):
        if not hasattr(self, "data") or not isinstance(self.data, dict):
            self.core.popup("No data to display or 'data' is not a dictionary.")
            return
        
        _debug_recursive_print(self.data, label="ItemData")

        lines = []
        for key, value in self.data.items():
            if key == "seqData" and isinstance(value, dict):
                lines.append(f"{key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"    {sub_key}:     {sub_value}")
            else:
                lines.append(f"{key}:     {value}")

        data_str = "\n".join(lines)

        self.core.popup(data_str)

    ####    ^^^^^^^^^^^^^    ####
    


    #   Returns the File Create Date from the OS
    @err_catcher(name=__name__)
    def getFileDate(self, filePath):
        return os.path.getmtime(filePath)
    

    @err_catcher(name=__name__)
    def getSequenceItems(self):
        return self.data["sequenceItems"]
    

    @err_catcher(name=__name__)
    def getFirstSeqData(self):
        return self.getSequenceItems()[0]["data"]
    

    #   Returns the File Size from the OS
    @err_catcher(name=__name__)
    def getFileSize(self, filePath):
        return os.stat(filePath).st_size
    

    #   Returns File Size (can be slower)
    @err_catcher(name=__name__)
    def getFileSizeStr(self, size_bytes):
        return self.browser.getFileSizeStr(size_bytes)
    

    #   Returns Total Size of Image Sequnce
    @err_catcher(name=__name__)
    def getSequenceSize(self, seqItems):
        totalSize_raw = 0
        
        for item in seqItems:
            size = item.get("data", {}).get("source_mainFile_size_raw")
            if isinstance(size, (int, float)):
                totalSize_raw += size

        return totalSize_raw



    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_mainfilePath(self):
        try:
            if getattr(self, "isSequence", False):
                return self.getFirstSeqData()["source_mainFile_path"]
            else:
                return self.data.get("source_mainFile_path")
            
        except Exception as e:
            logger.warning(f"ERROR:  Failed to get Source Main File Path:\n{e}")
            return None
    

    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_proxyfilePath(self):
        try:
            return self.data.get("source_proxyFile_path")
        except Exception as e:
            logger.warning(f"ERROR:  Failed to get Source Proxy File Path:\n{e}")
    

    #   Gets Thumbnail Save Path
    @err_catcher(name=__name__)
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
    def getTransferSize(self, proxyEnabled, proxyMode):
        try:
            if self.isSequence:
                #   Get Image Sequence Size
                total_size = self.getSequenceSize(self.data.get("sequenceItems", []))
            else:
                #   Or Get the Main File Size
                total_size = self.data["source_mainFile_size_raw"]

        except KeyError:
            #   Fallback
            total_size = self.getFileSize(self.getSource_mainfilePath())

        #   Add Proxy Size (or estimated) if this is a Video or Image Sequence
        if proxyEnabled and (self.isVideo() or self.isSequence):
            if proxyMode == "copy":
                if self.getSource_proxyfilePath():
                    total_size += self.getFileSize(self.getSource_proxyfilePath())

            elif proxyMode == "missing":
                if self.getSource_proxyfilePath():
                    total_size += self.getFileSize(self.getSource_proxyfilePath())
                else:
                    total_size += self.getMultipliedProxySize(total=True)

            elif proxyMode == "generate":
                total_size += self.getMultipliedProxySize(total=True)

        return total_size


    #   Gets the Number of Frames of the File(s) to Transfer
    @err_catcher(name=__name__)
    def calcDuration(self, filePath, callback=None):
        if getattr(self, "isSequence", False):
            duration = len(self.data["seqFiles"])
            self.onMainfileDurationReady(duration)                      #   TODO - Get CALLBACK WORKING BETTER

        else:
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
            case "Images":
                iconPath =  self.browser.icon_image
            case "Image Sequence":
                iconPath =  self.browser.icon_sequence
            case "Videos":        
                iconPath =  self.browser.icon_video
            case "Audio":
                iconPath =  self.browser.icon_audio
            case "Folders":
                iconPath =  self.browser.icon_folder
            case "Other":
                iconPath =  self.browser.icon_file
            case _:
                iconPath =  self.browser.icon_error

        return QIcon(iconPath)


    #   Gets and Sets Thumbnail Using Thread
    @err_catcher(name=__name__)
    def getThumbnail(self, path=None):
        try:
            if path:
                filePath = path
            else:
                filePath = self.getSource_mainfilePath()

            # Create Worker Thread
            worker_thumb = ThumbnailWorker(
                self,
                filePath=filePath,
                mediaLib = self.core.media,
                width=self.itemPreviewWidth,
                height=self.itemPreviewHeight,
                getThumbnailPath=self.getThumbnailPath,
            )

            worker_thumb.setAutoDelete(True)
            worker_thumb.result.connect(self.onThumbComplete)
            self.thumb_threadpool.start(worker_thumb)

            logger.debug("Refreshing Thumbnail")
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Thumbnail:\n{e}")
        

    #   Gets called from Thumb Worker Finished
    @err_catcher(name=__name__)
    def onThumbComplete(self, scaledPixmap):
        self.data["thumbnail"] = scaledPixmap

        self.setThumbnail(scaledPixmap)

        self.thumbnailReady.emit(scaledPixmap)



    #   Adds Thumbnail to FileTile Label
    @err_catcher(name=__name__)
    def setThumbnail(self, pixmap):
        if hasattr(self, "l_preview"):
            self.l_preview.setAlignment(Qt.AlignCenter)
            self.l_preview.setPixmap(pixmap)
            


    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def setDuration(self):
        duration = self.data["source_mainFile_duration"]
        self.l_frames.setText(str(duration))


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
    

    #   Sets Icon Based and Icon Tooltip
    @err_catcher(name=__name__)
    def setIcon(self, icon):
        try:
            #   Tooltip
            fileType = self.fileType
            self.l_icon.setToolTip(f"FileType:  {fileType}")

            #   Sets Icon
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

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Icon:\n{e}")


    #   Returns the Tile Icon
    @err_catcher(name=__name__)
    def getIcon(self):
        if self.data.get("icon", ""):
            return self.data["icon"]
        

    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        self.core.openFolder(path)


    #   Returns File MetaData
    @err_catcher(name=__name__)
    def getMetadata(self, filePath):
        try:
            with exiftool.ExifTool(self.browser.exifToolEXE) as et:
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
            logger.debug("Showing MetaData Popup")
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

        try:
            #   Use passed file
            if filePath:
                sendFiles = [filePath]
                isProxy = False

            elif self.fileType == "Videos":
                if self.isPreferProxies() and self.getSource_proxyfilePath():
                    #   Use Proxy if Proxy Exists and Prefer is Checked
                    sendFiles = [self.getSource_proxyfilePath()]
                    isProxy = True
                else:
                    #   Use Main File
                    sendFiles = [self.getSource_mainfilePath()]
                    isProxy = False

            elif self.fileType == "Images":
                sendFiles = [self.getSource_mainfilePath()]
                isProxy = False

            elif self.fileType == "Image Sequence":
                isProxy = False

                sendFiles = []
                seqItems = self.data["sequenceItems"]
                for item in seqItems:
                    sendFiles.append(item["data"]["source_mainFile_path"])
            
            elif self.fileType == "Audio":
                self.core.popup("AUDIO NOT SUPPORTED YET")
                return

            logger.debug("Sending Image(s) to Media Viewer")

            self.browser.PreviewPlayer.updatePreview(sendFiles, isProxy)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Send Image(s) to Media Viewer:\n{e}")



##   FOLDER TILES (Inherits from BaseTileItem)  ##
class FolderItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(FolderItem, self).__init__(browser, data, parent)
        self.tileType = "folderTile"

        self.data = data

        self.setupUi()
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


    #   Place Holder for RCL for Folder Items
    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)

        showDataAct = QAction("Show Data", self.browser)                         #   TESTING
        showDataAct.triggered.connect(self.TEST_SHOW_DATA)
        rcmenu.addAction(showDataAct)

        expAct = QAction("Open in Explorer", self)
        expAct.triggered.connect(lambda: self.openInExplorer(self.data["dirPath"]))
        rcmenu.addAction(expAct)

        rcmenu.exec_(QCursor.pos())


##   FILE TILES ON THE SOURCE SIDE (Inherits from BaseTileItem)     ##
class SourceFileItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(SourceFileItem, self).__init__(browser, data, passedData, parent)
        self.tileType = "sourceItem"

        if passedData:
            self.data = passedData

        else:
            self.data = data
            self.data["source_mainFile_duration"] = None
            self.data["source_mainFile_hash"] = None
            self.data["hasProxy"] = False
            
            self.fileType = self.data["fileType"]

            self.generateData()


        logger.debug("Loaded Source FileTile")                          #   TODO - LOGGIN FOR SEPARATE CLASSES


    @err_catcher(name=__name__)
    def generateData(self):
        #   Get Main File Path
        filePath = self.getSource_mainfilePath()

        #   Icon
        icon = self.getIconByType(filePath)
        self.data["icon"] = icon

        #   Date
        date_data = self.getFileDate(filePath)
        self.data["source_mainFile_date_raw"] = date_data
        date_str = self.core.getFormattedDate(date_data)
        self.data["source_mainFile_date"] = date_str

        #   Size
        mainSize_data = self.getFileSize(filePath)
        self.data["source_mainFile_size_raw"] = mainSize_data
        mainSize_str = self.getFileSizeStr(mainSize_data)
        self.data["source_mainFile_size"] = mainSize_str

        #   Duration
        if self.fileType in ["Videos", "Images", "Image Sequence"]:
            self.calcDuration(filePath, self.onMainfileDurationReady)

        #   Main File Hash
        self.setFileHash(filePath, self.onMainfileHashReady)

        self.getThumbnail()
        self.setProxyFile()


    #   Populates Frames when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileDurationReady(self, duration):
        try:
            self.data["source_mainFile_duration"] = duration

            if hasattr(self, "l_frames"):
                self.setDuration()
            
            self.durationReady.emit(duration)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Main File Duration:\n{e}")


    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileHashReady(self, result_hash):
        try:
            self.data["source_mainFile_hash"] = result_hash

            if hasattr(self, "l_fileSize"):
                self.l_fileSize.setToolTip(f"Hash: {result_hash}")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Main File Hash:\n{e}")


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxyFile(self):
        try:
            self.data["hasProxy"] = False

            #   Return if Not a Media File Type
            ext = self.getFileExtension()
            if ext.lower() not in self.core.media.supportedFormats:
                return
            
            proxyFilepath = self.searchForProxyFile()

            if proxyFilepath:
                #   Set Proxy Flag
                self.data["hasProxy"] = True

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

                #   Show Proxy Icon on Thumbnail
                if hasattr(self, "l_pxyIcon"):
                    self.l_pxyIcon.show()

                    #   Set Proxy Tooltip
                    tip = (f"Proxy File detected:\n\n"
                        f"File: {proxyFilepath}\n"
                        f"Date: {date_str}\n"
                        f"Size: {mainSize_str}")
                    self.l_pxyIcon.setToolTip(tip)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Proxy File:\n{e}")


    #   Uses Setting-defined Template to Search for Proxies
    @err_catcher(name=__name__)
    def searchForProxyFile(self):
        try:
            #   Get the Config Data
            proxySearchList = self.getSettings(key="proxySearch")

            #   Get Orig Names
            fullPath = self.getSource_mainfilePath()
            baseDir = os.path.dirname(fullPath)
            baseName = os.path.basename(fullPath)
            fileBase, _ = os.path.splitext(baseName)

            for pathTemplate in proxySearchList:
                #   Replace @MAINFILENAME@ with the base name (without extension)
                pathWithFilename = pathTemplate.replace("@MAINFILENAME@", fileBase)

                #   Replace @MAINFILEDIR@ name with any Prefix/Suffix
                def replace_dirToken(match):
                    pre = match.group(1) or ""
                    post = match.group(2) or ""
                    return os.path.join(os.path.dirname(baseDir), pre + os.path.basename(baseDir) + post)

                #   Find any prefix/suffix on @MAINFILEDIR@
                dir_pattern = re.compile(r"(.*?)@MAINFILEDIR@(.*?)")
                proxyPath = dir_pattern.sub(replace_dirToken, pathWithFilename)

                #   Convert Relative Path to Absolute
                proxyPath = os.path.normpath(proxyPath)

                #   Extract Info for Lookup
                proxyDir = os.path.dirname(proxyPath)
                targetFile = os.path.basename(proxyPath).lower()
                targetFileBase, _ = os.path.splitext(targetFile)

                #   Find Match in the Dir
                if os.path.isdir(proxyDir):
                    for f in os.listdir(proxyDir):
                        fileBaseName, _ = os.path.splitext(f.lower())
                        if fileBaseName == targetFileBase:
                            proxyPath = os.path.join(proxyDir, f)
                            logger.debug(f"Proxy found: {proxyPath}")
                            return proxyPath

            logger.debug(f"No Proxies found for {fileBase}")
            return None
        
        except Exception as e:
            logger.warning(f"ERROR:  Proxy Search Failed:\n{e}")
            return None


    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def onProxyfileHashReady(self, result_hash):
        try:
            self.data["source_proxyFile_hash"] = result_hash
            # self.l_fileSize.setToolTip(f"Hash: {result_hash}")
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Proxy File Hash:\n{e}")





class SourceFileTile(BaseTileItem):
    def __init__(self, item: SourceFileItem, fileType, parent=None):
        self.item = item
        self.data = item.data
        self.tileType = "sourceTile"

        super().__init__(item.browser, item.data, parent)

        self.fileType = fileType
        self.isSequence = bool(self.fileType == "Image Sequence")

        self.setupUi()
        self.refreshUi()


    def mouseReleaseEvent(self, event):
        super(SourceFileTile, self).mouseReleaseEvent(event)
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
        self.l_pxyIcon = QLabel(self.thumbContainer)
        self.l_pxyIcon.setPixmap(self.browser.icon_proxy.pixmap(40, 40))
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

        self.l_dateIcon = QLabel()
        self.l_dateIcon.setPixmap(self.browser.icon_date.pixmap(15, 15))
        #   Date Label
        self.l_date = QLabel()
        self.l_date.setAlignment(Qt.AlignRight)

        #   Add Date Items to Date LAyout
        self.lo_date.addWidget(self.l_dateIcon, alignment=Qt.AlignVCenter)
        self.lo_date.addWidget(self.l_date, alignment=Qt.AlignVCenter)
        
        #   Create File Size Layout
        self.lo_fileSize = QHBoxLayout()

        #   Disk Icon
        self.l_diskIcon = QLabel()
        self.l_diskIcon.setPixmap(self.browser.icon_disk.pixmap(15, 15))
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
        try:
            # Get File Path
            filePath = self.getSource_mainfilePath()

            # #   Set Display Name
            if self.isSequence:
                displayName = self.data["displayName"]
            else:
                displayName = self.getBasename(filePath)

            self.l_fileName.setText(displayName)
            self.l_fileName.setToolTip(f"FilePath: {filePath}")

            #   Set Filetype Icon
            if self.isSequence:
                self.setIcon(self.browser.icon_sequence)
            else:
                self.setIcon(self.data["icon"])

            #   Set Date
            if self.isSequence:
                date_str = self.getFirstSeqData()["source_mainFile_date"]
            else:
                date_str = self.data["source_mainFile_date"]
            self.l_date.setText(date_str)

            #   Set Filesize
            self.setFileSize()

            #   Set Number of Frames
            self.setFrames()

            #   Set Hash
            if not self.isSequence:
                self.l_fileSize.setToolTip("Calculating file hash...")
                if self.data["source_mainFile_hash"]:
                    self.l_fileSize.setToolTip(f"Hash: {self.data['source_mainFile_hash']}")

            #   Proxy Icon
            if not self.isSequence and self.data["hasProxy"]:
                self.l_pxyIcon.show()

            #   If Thumbnail Exists, Set Immediately
            if self.isSequence:
                #   If Thumbnail Exists, Set Immediately
                if self.getFirstSeqData().get("thumbnail"):
                    self.setThumbnail(self.data["sequenceItems"][0]["data"].get("thumbnail"))
                    
                else:
                    #   Generate Thumbnail
                    self.getThumbnail(self.getFirstSeqData().get("source_mainFile_path"))

            else:
                #   If Thumbnail Exists, Set Immediately
                if self.data.get("thumbnail"):
                    self.setThumbnail(self.data.get("thumbnail"))
                else:
                    #   Or Add Signal Connection
                    self.item.thumbnailReady.connect(self.setThumbnail)


        except Exception as e:
            logger.warning(f"ERROR:  Failed to Load Source FileTile UI:\n{e}")

    
    @err_catcher(name=__name__)
    def setFileSize(self):
        if self.isSequence:
            totalSize_raw = self.getSequenceSize(self.data.get("sequenceItems", []))
            totalSize_str = self.getFileSizeStr(totalSize_raw)

        else:
            totalSize_str = self.data["source_mainFile_size"]

        self.l_fileSize.setText(totalSize_str)


    @err_catcher(name=__name__)
    def setFrames(self):
        if self.fileType in ["Videos", "Images", "Image Sequence"]:
            self.l_frames.setText("--")

        if self.isSequence:
            self.l_frames.setText(str(len(self.data["sequenceItems"])))

        elif self.data["source_mainFile_duration"]:
            self.setDuration()

        else:
            self.item.durationReady.connect(lambda: self.setDuration())


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

        #   Displayed if Single Selection
        if len(self.browser.selectedTiles) == 1:
            refreshThumbAct = QAction("Regenerate Thumbnail", self.browser)
            refreshThumbAct.triggered.connect(self.getThumbnail)
            rcmenu.addAction(refreshThumbAct)

            mDataAct = QAction("Show All MetaData", self.browser)
            mDataAct.triggered.connect(lambda: self.displayMetadata(self.getSource_mainfilePath()))
            rcmenu.addAction(mDataAct)

            showDataAct = QAction("Show Data", self.browser)                         #   TESTING
            showDataAct.triggered.connect(self.TEST_SHOW_DATA)
            rcmenu.addAction(showDataAct)

            playerAct = QAction("Show in Player", self.browser)
            playerAct.triggered.connect(self.sendToViewer)
            rcmenu.addAction(playerAct)

            expAct = QAction("Open in Explorer", self)
            expAct.triggered.connect(lambda: self.openInExplorer(self.getSource_mainfilePath()))
            rcmenu.addAction(expAct)

        rcmenu.exec_(QCursor.pos())


    #   Adds Tile(s) to Destination
    @err_catcher(name=__name__)
    def addToDestList(self):
        try:
            #   If Multiple Tiles Selected
            if len(self.browser.selectedTiles) > 1:
                for tile in list(self.browser.selectedTiles):
                    tile.setChecked(True)
                    self.browser.addToDestList(tile.data)

            #   If Single Just Add Tile
            else:
                self.setChecked(True)
                self.browser.addToDestList(self.data)
            
            self.browser.refreshDestItems()
            
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Add to Destination List:\n{e}")







##   FILE TILES ON THE DESTINATION SIDE (Inherits from BaseTileItem)    ##
class DestFileItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(DestFileItem, self).__init__(browser, data, passedData, parent)
        self.tileType = "destItem"

        if passedData:
            self.data = passedData

        else:
            self.data = data

        self.fileType = self.data["fileType"]


        logger.debug("Loaded Destination FileTile")                         #   TODO





##   FILE TILES ON THE DESTINATION SIDE (Inherits from BaseTileItem)    ##
class DestFileTile(BaseTileItem):
    def __init__(self, item: DestFileItem, fileType, parent=None):
        self.item = item
        self.data = item.data
        self.tileType = "destTile"

        super().__init__(item.browser, item.data, parent)

        self.fileType = fileType

        self.isSequence = bool(self.fileType == "Image Sequence")

        self.main_transfer_worker = None
        self.worker_proxy = None
        self.transferState = None

        self.main_copiedSize = 0.0
        self.proxy_copiedSize = 0.0

        self.setupUi()
        self.refreshUi()

        logger.debug("Loaded Destination FileTile")



    def mouseReleaseEvent(self, event):
        super(DestFileTile, self).mouseReleaseEvent(event)
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
        self.l_pxyIcon = QLabel(self.thumbContainer)
        self.l_pxyIcon.setPixmap(self.browser.icon_proxy.pixmap(40, 40))
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
        self.l_amountCopied = QLabel()
        self.l_size_dash = QLabel()
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
        try:
            name, source_mainFile_path = self.setModifiedName()

            tip = (f"Source File:  {os.path.join(source_mainFile_path, name)}\n"
                f"Destination File:  {os.path.join(self.getDestPath(), name)}")
            self.l_fileName.setToolTip(tip)

            #   Set Filetype Icon
            if self.isSequence:
                self.setIcon(self.browser.icon_sequence)
            else:
                self.setIcon(self.data["icon"])


            self.setThumbnail(self.data.get("thumbnail"))

            #   Get and Set Proxy File
            self.setProxy()

            #   Set Quanity Details
            self.setQuanityUI("idle")

            self.toggleProxyProgbar()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Load Destination FileTile UI:\n{e}")


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
    def setModifiedName(self):
        try:
            dest_mainFile_dir = self.getDestPath()

            # #   Set Display Name
            if self.isSequence:
                source_mainFile_path = self.getFirstSeqData()["source_mainFile_path"]
                displayName = self.data["displayName"]
            else:
                source_mainFile_path = self.getSource_mainfilePath()
                displayName = self.getBasename(source_mainFile_path)

            #   Get Modified Name
            if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
                name = self.getModifiedName(displayName)

            #   Use Un-Modified Name
            else:
                name = displayName

            #    Set Name and Path
            self.data["dest_mainFile_path"] = os.path.join(dest_mainFile_dir, name)
            self.l_fileName.setText(name)

            return name, source_mainFile_path

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Name Override:\n{e}")

        
    @err_catcher(name=__name__)
    def getModifiedName(self, orig_name):
        return self.browser.applyMods(orig_name)
       

    #   Returns Proxy Source Path
    @err_catcher(name=__name__)
    def getProxy(self):
        return self.data.get("source_proxyFile_path", None)


    #   Sets Destination Proxy Filepath and Icon
    @err_catcher(name=__name__)
    def setProxy(self):
        try:
            if self.getProxy():
                #   Show Proxy Icon
                self.l_pxyIcon.show()

                #   Set Proxy Tooltip
                tip = (f"Proxy File detected:\n\n"
                    f"File: {self.data['source_proxyFile_path']}\n"
                    f"Date: {self.data['source_proxyFile_date']}\n"
                    f"Size: {self.data['source_proxyFile_size']}")
                self.l_pxyIcon.setToolTip(tip)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Proxy File:\n{e}")


    #   Returns Destination Directory
    @err_catcher(name=__name__)
    def getDestPath(self):
        return os.path.normpath(self.browser.destDir)


    #   Returns the Destination Mainfile Path
    @err_catcher(name=__name__)
    def getDestMainPath(self):
        try:
            if self.isSequence:
                baseName = self.data["displayName"]
            else:
                sourceMainPath = self.getSource_mainfilePath()
                baseName = self.getBasename(sourceMainPath)

            #   Modifiy Name is Enabled
            if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
                baseName = self.getModifiedName(baseName)

            destPath = self.getDestPath()

            return os.path.join(destPath, baseName)
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Destination MainFile Path:\n{e}")
    

     #   Checks if File Exists at Destination
    @err_catcher(name=__name__)
    def destFileExists(self):   
        return os.path.exists(self.data["dest_mainFile_path"])


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def getResolvedDestProxyPath(self, dirOnly=False):
        try:
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

            #   Return Directory
            if dirOnly:
                return dest_proxyDir

            # Final proxy path
            dest_proxyFilePath = os.path.join(dest_proxyDir, proxy_fileName)

            return dest_proxyFilePath
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Resolved Proxy Path:\n{e}")
            return None
    

    #   Returns an Estimated Proxy Size Based on a Fractional Multiplier
    @err_catcher(name=__name__)
    def getMultipliedProxySize(self, frame=None, total=False):
        try:
            #   Get Main File Size
            mainSize = self.getFileSize(self.getSource_mainfilePath())

            if not mainSize:
                return 0

            #   Get Presets and Multiplier from Preset
            presetName = self.browser.proxySettings.get("proxyPreset", "")
            presets = self.browser.ffmpegPresets
            preset = presets.get(presetName, {})
            mult = float(preset.get("Multiplier", 0.0))

            #   Get and Apply Proxy Scaling
            scale_str = self.browser.proxySettings.get("proxyScale", "100%")
            scale = int(scale_str.strip('%'))
            scaled_mult = mult * (scale / 100) ** 2

            #   Get Estimated Proxy Size based on Multiplier
            proxySize = mainSize * scaled_mult

            if total:
                #   Just Return Full Proxy Size
                return proxySize
            
            else:
                #   Get Number of Frames
                total_frames = self.data["source_mainFile_duration"]

                #   Abort if Incorrect Data
                if total_frames <= 0 or frame is None:
                    return 0            
                
                #   Clamp Frame
                frame = max(0, min(frame, total_frames))
                #   Calculate Proxy Size per Frame
                per_frame = proxySize / total_frames

                return per_frame * frame
            
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Multiplied Proxy Size:\n{e}")
            return 0
        
    
    #   Gets Generated Proxy Size and Updates Presets Multiplier
    @err_catcher(name=__name__)
    def updateProxyPresetMultiplier(self):
        try:
            #   Get File Sizes
            mainSize = self.getFileSize(self.data["dest_mainFile_path"])
            proxySize = self.getFileSize(self.data["dest_proxyFile_path"])

            if mainSize <= 0 or proxySize <= 0:
                logger.warning("Cannot update multiplier: one of the sizes is zero")
                return
            
            #   Get Scale
            scale_str = self.browser.proxySettings.get("proxyScale", "100%")
            scale_pct = int(scale_str.strip("%")) / 100.0

            #   Reverse the Multiplir Calc
            new_base_mult = proxySize / (mainSize * (scale_pct ** 2))
            #   Clamp Result
            new_base_mult = max(0.001, min(new_base_mult, 5.0))

            #   Add Calculated Multiplier to Mult List
            self.browser.calculated_proxyMults.append(new_base_mult)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Proxy Multiplier:\n{e}")


    @err_catcher(name=__name__)
    def setTransferStatus(self, progBar, status, tooltip=None):
        try:
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

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Tile Transfer Status:\n{e}")


    #   Sets the Quality UI for Each Mode
    @err_catcher(name=__name__)
    def setQuanityUI(self, mode):
        copied = ""
        dash = ""
        total = ""

        #   Gets Frames and File Size of Sequence
        if self.isSequence:
            totalSize_raw = self.getSequenceSize(self.getSequenceItems())
            self.data["totalSeqSize"] = totalSize_raw
            mainSize = self.getFileSizeStr(totalSize_raw)

            duration = str(len(self.data["sequenceItems"]))
            self.data["seqDuration"] = duration
            
        #   Get Frames and File Size of Non-Sequences
        else:
            mainSize = self.data["source_mainFile_size"]
            duration = str(self.data["source_mainFile_duration"])

        #   Sets UI Based on Mode
        if mode in ["idle", "complete"]:
            if "source_mainFile_duration" in self.data:
                if self.fileType in ["Videos", "Images", "Image Sequence"]:
                    copied = duration
                    dash = "frames -"
                else:
                    copied = ""
                    dash = ""

                total = mainSize

        elif mode == "copyMain":
            copied = "--"
            dash = "of"
            total = mainSize

        elif mode == "copyProxy":
            copied = "--"
            dash = "of"
            total = self.data["source_proxyFile_size"]

        elif mode == "generate":
            copied = "--"
            dash = "of"
            total = duration

        self.l_amountCopied.setText(copied)
        self.l_size_dash.setText(dash)
        self.l_amountTotal.setText(total)


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

        #   Displayed if Single Selection
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


    @err_catcher(name=__name__)
    def removeFromDestList(self):
        try:
            if len(self.browser.selectedTiles) > 1:
                for tile in list(self.browser.selectedTiles):
                    self.browser.removeFromDestList(tile.data)
            else:
                self.browser.removeFromDestList(self.data)

            self.browser.refreshDestItems()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Remove FileTile from Destination List:\n{e}")


    #   Return Proxy Path Based on Mode, Overrides, and Filename Mods
    @err_catcher(name=__name__)
    def getDestProxyFilepath(self, sourcePath, proxyMode, proxySettings):
        
        #   Helper to Resolve Absolute or Relative Path
        def _resolvePath(user_dir, dest_dir):
            try:
                #   Convert to Path
                user_path = Path(os.path.normpath(user_dir))

                # Determine if it's relative or absolute
                if user_path.is_absolute():
                    resolvedPath = user_path
                else:
                    resolvedPath = os.path.join(dest_dir, user_path)

                return resolvedPath
            
            except Exception as e:
                logger.warning(f"ERROR:  Failed to Resolve Path:\n{e}")
                return None

        try:
            #   Get Source Base Name and Modify if Enabled
            source_baseFile = os.path.basename(sourcePath)
            if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
                source_baseFile = self.getModifiedName(source_baseFile)

            #   Make Proxy Name
            source_baseName = os.path.splitext(source_baseFile)[0]
            proxy_baseFile = source_baseName + proxySettings["Extension"]

            #   Convert dest_dir to Path
            dest_dir = Path(self.getDestPath())

            proxyPath = None

            ##  OVERIDE PROXY PATH  ##
            #   Get Override Dir if it Exists
            override_dir_raw = proxySettings.get("ovr_proxyDir", "").strip()
            if override_dir_raw:
                #   Resolve Absolute or Relative Path
                ovrPath = _resolvePath(override_dir_raw, dest_dir)
                #   Make Override Proxy Path
                proxyPath = os.path.join(ovrPath, proxy_baseFile)
                self.data["dest_proxyFile_path"] = str(proxyPath)

                #   Add Proxy to Tile Data
                if self.data["hasProxy"]:
                    self.transferData["sourceProxy"] = self.data["source_proxyFile_path"]

                #   Return Override Proxy Path
                return str(proxyPath)

            ##  NO OVERRIDE  ##
            #   COPY MODE
            if proxyMode == "copy" and self.data["hasProxy"]:
                self.transferData["sourceProxy"] = self.data["source_proxyFile_path"]
                proxyPath = Path(self.getResolvedDestProxyPath())

            #   GENERATE MODE
            elif proxyMode == "generate":
                if proxySettings["resolved_proxyDir"]:
                    proxy_dir = Path(proxySettings["resolved_proxyDir"])
                else:
                    fallback_dir_raw = proxySettings["fallback_proxyDir"].strip()
                    proxy_dir = _resolvePath(fallback_dir_raw, dest_dir)

                proxyPath = os.path.join(proxy_dir, proxy_baseFile)

            #   GENERATE MISSING MODE
            elif proxyMode == "missing":
                if self.data["hasProxy"]:
                    self.transferData["sourceProxy"] = self.data["source_proxyFile_path"]
                    proxyPath = Path(self.getResolvedDestProxyPath())
                else:
                    if proxySettings["resolved_proxyDir"]:
                        proxy_dir = Path(proxySettings["resolved_proxyDir"])
                    else:
                        fallback_dir_raw = proxySettings["fallback_proxyDir"].strip()
                        proxy_dir = _resolvePath(fallback_dir_raw, dest_dir)

                    proxyPath = os.path.join(proxy_dir, proxy_baseFile)

            self.data["dest_proxyFile_path"] = str(proxyPath)

            return str(proxyPath)
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Destination Proxy File Path:\n{e}")


    @err_catcher(name=__name__)
    def start_transfer(self, origin, options, proxyEnabled, proxyMode):
        #   Set and Lock Modes
        self.proxyEnabled = proxyEnabled
        self.proxyMode = proxyMode

        #   Create Transfer Dict for Use Later
        self.transferData = {
            "proxyEnabled": proxyEnabled,
            "copyProxy": False,
            "generateProxy": False
        }

        #   Get Main Paths
        sourcePath = self.getSource_mainfilePath()
        destPath = self.getDestMainPath()
        self.data["dest_mainFile_path"] = destPath

        if self.isSequence:
            transferList = []
            for item in self.data.get("sequenceItems", []):
                iData = item["data"]

                if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
                    name = self.getModifiedName(iData["displayName"])
                else:
                    name = iData["displayName"]

                sourcePath = iData["source_mainFile_path"]
                destPath = os.path.join(self.getDestPath(), name)
                iData["dest_mainFile_path"] = destPath

                transferList.append({"sourcePath": sourcePath,
                                     "destPath": destPath})

        else:
            transferList = [{"sourcePath": sourcePath,
                            "destPath": destPath}]


        ##  IF PROXY IS ENABLED ##
        if proxyEnabled and self.isVideo():                                     #   TODO - HANDLE PROXY FOR NON-VIDEO
            proxySettings = options["proxySettings"]
            self.transferData["proxyMode"] = proxyMode
            self.transferData["proxySettings"] = proxySettings

            #   Temp Vars for Logic
            hasProxy = self.data["hasProxy"]
            isCopyMode = proxyMode == "copy"
            isGenerateMode = proxyMode == "generate"
            isMissingMode = proxyMode == "missing"
            #   Set Copy and Generate Logic
            self.transferData["copyProxy"] = hasProxy and (isCopyMode or isMissingMode)
            self.transferData["generateProxy"] = isGenerateMode or (isMissingMode and not hasProxy)

            #   Get Proxy Destination Path
            self.transferData["destProxy"] = self.getDestProxyFilepath(sourcePath, proxyMode, proxySettings)

        #   Start Timers
        self.transferTimer = ElapsedTimer()

        #   Call Main File Transfer
        self.transferMainFile(transferList)


    #   Call Worker Thread to Copy Main File
    @err_catcher(name=__name__)
    def transferMainFile(self, transferList):
        self.setTransferStatus(progBar="transfer", status="Queued")
        self.setQuanityUI("copyMain")
        self.applyStyle(self.state)

        logger.debug(f"Starting MainFile Transfer: {transferList[0]}")

        #   Call the Transfer Worker Thread for Main File
        self.main_transfer_worker = FileCopyWorker(self, "transfer", transferList)
        #   Connect the Progress Signals
        self.main_transfer_worker.progress.connect(self.update_main_transferProgress)
        self.main_transfer_worker.finished.connect(self.main_transfer_complete)
        #   Execute Transfer
        self.main_transfer_worker.start()


    #   Gets called when Transfer Thread Starts in Queue
    @err_catcher(name=__name__)
    def _onTransferStart(self, transType, filePath):
        self.setTransferStatus(progBar=transType, status="Transferring")
        self.transferTimer.start()

        if transType == "transfer":
            logger.status(f"MainFile Transfer Started: {filePath}")

        elif transType == "proxy":
            logger.status(f"Proxy Transfer Started: {filePath}")


    #   Gets called when Proxy Thread Starts in Queue
    @err_catcher(name=__name__)
    def _onProxyGenStart(self):
        self.setTransferStatus(progBar="proxy", status="Generating Proxy")
        logger.status(f"Proxy Generation Started: {self.data['dest_proxyFile_path']}")


    @err_catcher(name=__name__)
    def pause_transfer(self, origin):
        if self.main_transfer_worker and self.transferState != "Complete":
            self.transferTimer.pause()
            self.main_transfer_worker.pause()
            logger.debug("Sending Pause to Worker")

            if self.transferState != "Queued":
                self.setTransferStatus(progBar="transfer", status="Paused")


    @err_catcher(name=__name__)
    def resume_transfer(self, origin):
        if self.main_transfer_worker and self.transferState == "Paused":
            self.setTransferStatus(progBar="transfer", status="Transferring")

            self.transferTimer.start()
            self.main_transfer_worker.resume()
            logger.debug("Sending Resume to Worker")


    @err_catcher(name=__name__)
    def cancel_transfer(self, origin):
        if self.main_transfer_worker and self.transferState != "Complete":
            self.setTransferStatus(progBar="transfer", status="Cancelled")
            self.transferTimer.stop()
            self.main_transfer_worker.cancel()
            logger.debug("Sending Cancel Transfer to Worker")

        if self.worker_proxy and self.transferState != "Complete":
            self.setTransferStatus(progBar="proxy", status="Cancelled")
            self.transferTimer.stop()
            self.worker_proxy.cancel()
            logger.debug("Sending Cancel Generation to Worker")



    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_main_transferProgress(self, value, copied_size):
        if self.transferState != "Cancelled":
            self.setTransferStatus(progBar="transfer", status="Transferring")

            self.transferProgBar.setValue(value)
            self.l_amountCopied.setText(self.getFileSizeStr(copied_size))
            self.main_copiedSize = copied_size


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyCopyProgress(self, value, copied_size):
        if self.transferState != "Cancelled":
            self.setTransferStatus(progBar="proxy", status="Transferring Proxy")

            self.proxyProgBar.setValue(value)
            self.l_amountCopied.setText(self.getFileSizeStr(copied_size))
            self.proxy_copiedSize = copied_size


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyGenerateProgress(self, value, frame):
        if self.transferState != "Cancelled":
            self.setTransferStatus(progBar="proxy", status="Generating Proxy")

            self.proxyProgBar.setValue(value)
            self.l_amountCopied.setText(str(frame))

            self.proxy_copiedSize = self.getMultipliedProxySize(frame=frame)


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def main_transfer_complete(self, success):
        self.transferTimer.stop()
        self.data["transferTime"] = self.transferTimer.elapsed()

        if success:
            destMainPath = self.getDestMainPath()

            #   Sets Destination FilePath ToolTip
            self.l_fileName.setToolTip(os.path.normpath(destMainPath))

            self.transferProgBar.setValue(100)

            destFiles = []

            if self.isSequence:
                transferItems = self.getSequenceItems()

                for transItem in transferItems:
                    destFiles.append(transItem["data"]["dest_mainFile_path"])

            else:
                destFiles.append(destMainPath)

            #   Itterate through all Transfered Files to Check Exists
            filesExist = all(os.path.isfile(file) for file in destFiles)

            if filesExist:
                self.setTransferStatus(progBar="transfer", status="Generating Hash")

                self.data["mainFile_result"] = "Complete"
                logger.debug("Main Transfer Successful")

                #   Calls for Hash Generation with Callback
                self.setFileHash(destMainPath, self.onDestHashReady)
            
            else:
                errorMsg = "ERROR:  Transfer File(s) Does Not Exist"
                logger.warning(f"Transfer failed: {destMainPath}")

                self.data["mainFile_result"] = errorMsg

                self.setTransferStatus(progBar="transfer", status="Error", tooltip=errorMsg)

        else:
            errorMsg = "ERROR:  Transfer failed"
            logger.warning(f"Transfer failed: {destMainPath}")

            self.data["mainFile_result"] = errorMsg

            self.setTransferStatus(progBar="transfer", status="Error", tooltip=errorMsg)


    #   Called After Hash Genertaion for UI Feedback
    @err_catcher(name=__name__)
    def onDestHashReady(self, dest_hash):
        self.data["dest_mainFile_hash"] = dest_hash
        orig_hash = self.data.get("source_mainFile_hash", None)

        #   If Transfer Hash Check is Good
        if dest_hash == orig_hash:
            statusMsg = "Transfer Successful"
            self.data["mainFile_result"] = statusMsg

            self.setTransferStatus(progBar="transfer", status="Complete")
            self.setQuanityUI("complete")

            #   Proxy Enabled
            if self.useProxy:
                self.setTransferStatus(progBar="proxy", status="Queued")

                #   Copy Proxy if Applicable
                if self.transferData["copyProxy"]:
                    self.setQuanityUI("copyProxy")
                    self.transferProxy()

                #   Generate Proxy if Enabled
                if self.transferData["generateProxy"]:
                    self.setQuanityUI("generate")
                    self.generateProxy()


            logger.status(f"Main Transfer complete: {self.data['dest_mainFile_path']}")
            
        #   Transfer Hash is Not Correct
        else:
            statusMsg = "ERROR:  Transfered Hash Incorrect"

            self.data["mainFile_result"] = statusMsg

            status = "Warning"
            logger.warning(f"Transfered Hash Incorrect: {self.getSource_mainfilePath()}")

            hashMsg = (f"Status: {statusMsg}\n\n"
                    f"Source Hash:   {orig_hash}\n"
                    f"Transfer Hash: {dest_hash}")
            
            self.setTransferStatus(progBar="transfer", status=status, tooltip=hashMsg)


    #   Generates Proxy with FFmpeg in a Worker Thread
    @err_catcher(name=__name__)
    def transferProxy(self):
        transferList = [{"sourcePath": self.transferData["sourceProxy"],
                        "destPath": self.transferData["destProxy"]}]

        #   Call the Transfer Worker Thread for Main File
        self.proxy_transfer_worker = FileCopyWorker(self, "proxy", transferList)
        #   Connect the Progress Signals
        self.proxy_transfer_worker.progress.connect(self.update_proxyCopyProgress)
        self.proxy_transfer_worker.finished.connect(self.proxyCopy_complete)
        #   Execute Transfer
        self.proxy_transfer_worker.start()


    #   Generates Proxy with FFmpeg in a Worker Thread
    @err_catcher(name=__name__)
    def generateProxy(self):
        settings = self.transferData["proxySettings"]

        #   Get File Paths
        input_path = self.getDestMainPath()
        output_path = self.data["dest_proxyFile_path"]

        #   Add Duration to settings Data
        settings["frames"] = self.data["source_mainFile_duration"]

        #   Call the Transfer Worker Thread
        self.worker_proxy = ProxyGenerationWorker(self, self.core, input_path, output_path, settings)
        #   Connect the Progress Signals
        self.worker_proxy.progress.connect(self.update_proxyGenerateProgress)
        self.worker_proxy.finished.connect(self.proxyGenerate_complete)
        self.worker_proxy.start()


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def proxyCopy_complete(self, success):
        if success:
            self.proxyProgBar.setValue(100)
            self.setTransferStatus(progBar="proxy", status="Complete", tooltip="Proxy Transferred")
            self.setQuanityUI("complete")

            logger.status(f"Transfer Proxy Complete: {self.data['dest_proxyFile_path']}")

            return
            
            # else:
            #     hashMsg = "ERROR:  Transfer File Does Not Exist"                      #   TODO - ADD ERROR CHECKING
            #     logger.warning(f"Transfer failed: {destMainPath}")
        # else:
        #     hashMsg = "ERROR:  Transfer failed"
        #     logger.warning(f"Transfer failed: {destMainPath}")

        # Final fallback (error case only)
        # self.setTransferStatus(progBar="transfer", status="Error", tooltip=hashMsg)


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def proxyGenerate_complete(self, success):
        if success:
            self.proxyProgBar.setValue(100)
            self.setTransferStatus(progBar="proxy", status="Complete", tooltip="Proxy Generated")
            self.setQuanityUI("complete")

            self.updateProxyPresetMultiplier()

            logger.status(f"Transfer Generation Complete: {self.data['dest_proxyFile_path']}")

            return
            
            # else:
            #     hashMsg = "ERROR:  Transfer File Does Not Exist"                      #   TODO - ADD ERROR CHECKING
            #     logger.warning(f"Transfer failed: {destMainPath}")
        # else:
        #     hashMsg = "ERROR:  Transfer failed"
        #     logger.warning(f"Transfer failed: {destMainPath}")

        # Final fallback (error case only)
        # self.setTransferStatus(progBar="transfer", status="Error", tooltip=hashMsg)


    #   Returns Total Transferred Size
    @err_catcher(name=__name__)
    def getCopiedSize(self):
        return self.main_copiedSize + self.proxy_copiedSize



####    THREAD WORKERS    ####

###     Thumbnail Worker Thread ###
class ThumbnailWorker(QObject, QRunnable):
    result = Signal(QPixmap)

    def __init__(self, origin, filePath, mediaLib, width, height, getThumbnailPath):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.origin = origin
        self.filePath = filePath
        self.getPixmapFromPath = mediaLib.getPixmapFromPath
        self.supportedFormats = mediaLib.supportedFormats
        self.width = width
        self.height = height
        self.getThumbnailPath = getThumbnailPath
        self.scalePixmapFunc = mediaLib.scalePixmap


    @Slot()
    def run(self):
        self.origin.thumb_semaphore.acquire()

        try:
            pixmap = None
            extension = os.path.splitext(self.filePath)[1].lower()

            #   Use App Icon for Non-Media Formats
            if extension not in self.supportedFormats:
                file_info = QFileInfo(self.filePath)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)
                pixmap = icon.pixmap(self.width, self.height)
                fitIntoBounds = True
                crop = False
                scale = 0.5
                logger.debug(f"Using File Icon for Unsupported Format: {extension}")

            #   Get Thumbnail for Media Formats
            else:
                #   Use Saved Thumbnail in "_thumbs" if Exists
                thumbPath = self.getThumbnailPath(self.filePath)
                if os.path.exists(thumbPath):
                    image = QImage(thumbPath)
                    pixmap = QPixmap.fromImage(image)

                #   Or Generate New Thumb
                else:
                    pixmap = self.getPixmapFromPath(
                        self.filePath,
                        width=self.width * 4,
                        height=self.height * 4,
                        colorAdjust=False
                        )
                
                fitIntoBounds = False
                crop = True
                scale = 1

            #   Scale and Emit Signal
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

    def __init__(self, origin, transType, transferList):
        super().__init__()
        
        self.origin = origin
        self.transType = transType
        self.transferList = transferList

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
            self.origin.copy_semaphore.acquire()

            # Step 1: Get total size of all transfers
            total_size_all = 0
            for transItem in self.transferList:
                try:
                    total_size_all += os.path.getsize(transItem["sourcePath"])
                except Exception as e:
                    print(f"Could not get size for: {transItem['sourcePath']} - {e}")

            copied_size_all = 0

            # Step 2: Loop through all items
            for transItem in self.transferList:
                sourcePath = transItem["sourcePath"]
                destPath = transItem["destPath"]

                try:
                    total_size = os.path.getsize(sourcePath)
                except Exception as e:
                    print(f"Error getting size of {sourcePath}: {e}")
                    continue  # skip this file

                copied_size_file = 0
                buffer_size = 1024 * 1024 * self.origin.size_copyChunk

                os.makedirs(os.path.dirname(destPath), exist_ok=True)

                #   Signal Main Code for UI
                self.origin._onTransferStart(self.transType, sourcePath)

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
                        copied_size_file += len(chunk)
                        copied_size_all += len(chunk)

                        progress_percent = int((copied_size_all / total_size_all) * 100)

                        now = time.time()
                        if now - self.last_emit_time >= self.origin.progUpdateInterval or progress_percent == 100:
                            self.progress.emit(progress_percent, copied_size_all)
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

    def __init__(self, origin, core, inputPath, outputPath, settings=None):
        super().__init__()

        self.origin = origin
        self.core = core
        self.inputPath  = inputPath
        self.outputPath  = outputPath
        self.settings   = settings or {}

        self.running = True
        self.pause_flag = False
        self.cancel_flag = False
        self.last_emit_time = 0


    # def pause(self):                                      #   Not Implemented
    #     self.pause_flag = True


    # def resume(self):                                      #   Not Implemented
    #     self.pause_flag = False


    def cancel(self):
        print("[ProxyWorker] Cancel called!")                       #   TODO - Add Logging
        self.cancel_flag = True


    #   Kills the FFmpeg Process
    def _kill_ffmpeg_tree(self):
        try:
            proc = psutil.Process(self.nProc.pid)
        except (psutil.NoSuchProcess, AttributeError):
            return

        #   Terminate Child Processes
        for child in proc.children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass

        #   Kill Parent Process
        try:
            if platform.system() == "Windows":
                #   Send CTRL_BREAK_EVENT Signal to the Group
                self.nProc.send_signal(signal.CTRL_BREAK_EVENT)
                self.nProc.kill()
            else:
                #   Kill the Process Group  (Linux, Mac)
                os.killpg(os.getpgid(self.nProc.pid), signal.SIGTERM)

        except Exception:
            #   Fallback Attempt
            proc.kill()


    def run(self):
        ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))
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
        vid_params   = self.settings.get("Video_Parameters", "")
        aud_params   = self.settings.get("Audio_Parameters", "")
        scale_str    = self.settings.get("scale", None)

        #   Create Proxy Dir
        os.makedirs(os.path.dirname(self.outputPath), exist_ok=True)

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
        argList += [self.outputPath, "-y"]

        # Regex to Catch FFmpeg output (e.g. "frame=  1234")
        frame_re = re.compile(r"frame=\s*(\d+)")


        #   Set Shell True if Windows
        shell = (platform.system() == "Windows")

        # On Windows, make FFmpeg its own process group so we can signal it.
        creationflags = 0
        if shell and platform.system() == "Windows":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        #   Get Thread Slot
        self.origin.proxy_semaphore.acquire()

        self.origin._onProxyGenStart()

        self.nProc = subprocess.Popen(
            argList,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=True,
            bufsize=1,
            creationflags=creationflags,
            preexec_fn=(os.setsid if platform.system() != "Windows" else None)
        )

        try:
            while True:
                #   Cancel Generation
                if self.cancel_flag:
                    print("[ProxyWorker] Cancel flag detected, terminating FFmpeg.")
                    self._kill_ffmpeg_tree()
                    self.finished.emit(False)
                    return

                # # pause?
                # if self.pause_flag:
                #     time.sleep(0.1)
                #     continue

                #   Read Outputted Console Lines
                line = self.nProc.stderr.readline()
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

            self.nProc.wait()
            self.finished.emit(self.nProc.returncode == 0)

        except Exception as e:
            print(f"[ProxyWorker] Exception: {e}")
            if self.nProc.poll() is None:
                self._kill_ffmpeg_tree()
            self.finished.emit(False)

        finally:
            self.origin.proxy_semaphore.release()
            self.running = False

