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
import re
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


from ElapsedTimer import ElapsedTimer

from WorkerThreads import (ThumbnailWorker,
                           FileInfoWorker,
                           FileHashWorker,
                           FileCopyWorker,
                           ProxyGenerationWorker
                           )

import SourceTab_Utils as Utils
from PopupWindows import MetadataEditor
from SourceTab_Models import FileTileMimeData


from PrismUtils.Decorators import err_catcher

logger = logging.getLogger(__name__)


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
        self.tileLocked = False

        self.setMouseTracking(True)

        #   Thumbnail Size
        self.saveThumbWidth = 1280  #   For Saved Thumbs
        self.itemPreviewWidth = 120 #   For Tile Thumbnail
        self.itemPreviewHeight = 69 #   For Tile Thumbnail

        logger.debug("Loaded Base Tile Item")


    #   Launches the Single-click File Action
    @err_catcher(name=__name__)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragStartPosition = event.pos()
            self._pressModifiers = QApplication.keyboardModifiers()
            # Track if Later Single-select
            self._pendingSingleSelect = False

            if self._pressModifiers & Qt.ShiftModifier and self.browser.lastClickedTile:
                self._selectRange()
                return

            if self._pressModifiers & Qt.ControlModifier:
                if self in self.browser.selectedTiles:
                    self.deselect()
                    self.browser.selectedTiles.discard(self)
                else:
                    self.state = "selected"
                    self.applyStyle(self.state)
                    self.browser.selectedTiles.add(self)
                self.browser.lastClickedTile = self
                return

            if self in self.browser.selectedTiles:
                #   Already Selected — Maybe Dragging, Maybe Single-select
                self._pendingSingleSelect = True
            else:
                #   Not selected - Select Immediately
                for tile in list(self.browser.selectedTiles):
                    tile.deselect()
                self.browser.selectedTiles.clear()

                self.state = "selected"
                self.applyStyle(self.state)
                self.browser.selectedTiles.add(self)

            self.browser.lastClickedTile = self
            return

        elif event.button() == Qt.RightButton:
            if self not in self.browser.selectedTiles:
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
        if self.tileLocked:
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        dragDistance = (event.pos() - self.dragStartPosition).manhattanLength()
        if dragDistance >= QApplication.startDragDistance():
            #   Cancel Single-select if Drag Starts
            self._pendingSingleSelect = False

            selectedTiles = self.browser.selectedTiles
            if not selectedTiles:
                return

            drag = QDrag(self)
            drag.setHotSpot(QPoint(10, 10))

            if len(selectedTiles) == 1:
                drag.setPixmap(self.grab())
            else:
                dragIcon = Utils.createStackedDragPixmap(selectedTiles)
                drag.setPixmap(dragIcon)

            mimeData = FileTileMimeData(selectedTiles, self.tileType)
            mimeData.setData("application/x-fileTile", b"")
            drag.setMimeData(mimeData)

            drag.exec_(Qt.CopyAction)


    @err_catcher(name=__name__)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pendingSingleSelect:
            #   Clear Selections and Select
            for tile in list(self.browser.selectedTiles):
                tile.deselect()
            self.browser.selectedTiles.clear()

            self.state = "selected"
            self.applyStyle(self.state)
            self.browser.selectedTiles.add(self)
            self.browser.lastClickedTile = self

            self._pendingSingleSelect = False

        super().mouseReleaseEvent(event)


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
    def setSelected(self, checked=None, modifiers=None, additive=False, set_focus=True):
        try:
            if modifiers is None:
                modifiers = QApplication.keyboardModifiers()

            if checked is False:
                self.deselect()
                self.browser.selectedTiles.discard(self)
                return

            #   SHIFT: Select Range
            if modifiers & Qt.ShiftModifier and self.browser.lastClickedTile:
                self._selectRange()
                return

            #   CTRL: Toggle Selection
            elif modifiers & Qt.ControlModifier:
                if self in self.browser.selectedTiles:
                    self.deselect()
                    self.browser.selectedTiles.discard(self)
                else:
                    self.state = "selected"
                    self.applyStyle(self.state)
                    if set_focus:
                        self.setFocus()
                    self.browser.selectedTiles.add(self)
                self.browser.lastClickedTile = self
                return

            #   Additive Mode: Add Without Clearing
            if additive:
                self.state = "selected"
                self.applyStyle(self.state)
                if set_focus:
                    self.setFocus()
                self.browser.selectedTiles.add(self)
                self.browser.lastClickedTile = self
                return

            #   Default: Clear and Select Only This
            for tile in list(self.browser.selectedTiles):
                tile.deselect()
            self.browser.selectedTiles.clear()

            self.state = "selected"
            self.applyStyle(self.state)
            if set_focus:
                self.setFocus()
            self.browser.selectedTiles.add(self)
            self.browser.lastClickedTile = self

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Item(s) Selected:\n{e}")


    @err_catcher(name=__name__)
    def _selectRange(self):
        #   Get all tiles in order
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

        #   Deselect Current Selection
        for tile in self.browser.selectedTiles:
            tile.deselect()
        self.browser.selectedTiles.clear()

        #   Select the Range
        for tile in allTiles[start:end + 1]:
            tile.state = "selected"
            tile.applyStyle(tile.state)
            self.browser.selectedTiles.add(tile)

        self.browser.lastClickedTile = self


    #   Sets the Checkbox and sets the State
    @err_catcher(name=__name__)
    def setChecked(self, checked, refresh=True):
        if self.tileLocked:
            logger.debug("Tile is Locked: Checked is disabled.")
            return
        
        if len(self.browser.selectedTiles) > 1:
            for tile in list(self.browser.selectedTiles):
                if hasattr(tile, "chb_selected"):
                    tile.chb_selected.setChecked(checked)
        else:
            self.chb_selected.setChecked(checked)

        #   Refresh Transfer Size
        if refresh and self.tileType == "destTile":
            self.browser.refreshTotalTransSize()


    #   Toggles the Checkbox
    @err_catcher(name=__name__)
    def toggleChecked(self):
        if self.tileLocked:
            logger.debug("Tile is Locked: Checked is disabled.")
            return
        
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
        # if self.isChecked():
        #     borderColor = COLOR_GREEN

        #   If Dest Tile File Exists
        if self.tileType == "destTile" and self.transferState == "Idle" and self.destFileExists():
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
        # if self.isChecked() and self.browser.transferState == "Idle":
        #     baseColor = COLOR_GREEN

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
        
        Utils.debug_recursive_print(self.data, label="ItemData")

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
    
  
    #   Returns List of All Sequence Files
    @err_catcher(name=__name__)
    def getSequenceFiles(self):
        return self.data["seqFiles"]
    

    @err_catcher(name=__name__)
    def getFirstSeqFile(self):
        return self.getSequenceFiles()[0]
    

    #   Returns the Filepath
    @err_catcher(name=__name__)
    def getSource_mainfilePath(self):
        try:
            if getattr(self, "isSequence", False):
                return self.getFirstSeqFile()
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
    def getThumbnailPath(self, filepath):
        thumbBasename = Utils.getBasename(os.path.splitext(filepath)[0]) + ".jpg"

        if self.browser.useCustomThumbPath:
            thumbDir = os.path.join(self.browser.customThumbPath, Utils.createUUID(simple=True))
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
                total_size = self.data["seqSize"]
            else:
                #   Or Get the Main File Size
                total_size = self.data["source_mainFile_size_raw"]

        #   Fallback
        except KeyError:
            total_size = Utils.getFileSize(self.getSource_mainfilePath())

        #   Add Proxy Size (or estimated) if this is a Video or Image Sequence
        if proxyEnabled and (self.isVideo() or self.isSequence):
            if proxyMode == "copy":
                if self.getSource_proxyfilePath():
                    total_size += Utils.getFileSize(self.getSource_proxyfilePath())

            elif proxyMode == "missing":
                if self.getSource_proxyfilePath():
                    total_size += Utils.getFileSize(self.getSource_proxyfilePath())
                else:
                    total_size += self.getMultipliedProxySize(total=True)

            elif proxyMode == "generate":
                total_size += self.getMultipliedProxySize(total=True)

        return total_size


    #   Gets Info such as Duration and Codec
    @err_catcher(name=__name__)
    def getFileInfo(self, filePath, callback=None):
        worker_frames = FileInfoWorker(self, self.core, filePath)
        worker_frames.finished.connect(callback)
        self.dataOps_threadpool.start(worker_frames)
    

    #   Gets Custom Hash of File in Separate Thread
    @err_catcher(name=__name__)
    def setFileHash(self, filePath, callback=None, mode="transfer",  mainTile=None, seqTile=None):
        #   Create Worker Instance
        worker_hash = FileHashWorker(filePath, seqTile)
        #   Connect to Finished Callback
        worker_hash.finished.connect(callback)
        #   Launch Worker in DataOps Treadpool
        self.dataOps_threadpool.start(worker_hash)

        #   Timer to Ensure Hash Generation does not Hang
        self.hashWatchdogTimer = QTimer()
        self.hashWatchdogTimer.setSingleShot(True)
        self.hashWatchdogTimer.timeout.connect(lambda: self.onHashTimeout(mainTile, mode))
        self.hashWatchdogTimer.start(30000)


    @err_catcher(name=__name__)
    def setMainHash(self, error=None):
        if hasattr(self, "l_fileSize"):
            if not error:
                tip = f"Hash: {self.data['source_mainFile_hash']}"
            else:
                tip = error

            self.l_fileSize.setToolTip(tip)


    @err_catcher(name=__name__)
    def onHashTimeout(self, mainTile, mode):
        logger.warning("ERROR: Hash generation timed out.")

        tip = "The Hash Worker timed out."
        self.setMainHash(error=tip)

        if mainTile:
            mainTile.setTransferStatus(progBar=mode, status="Warning", tooltip=tip)
    

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
    def getThumbnail(self, path=None, regenerate=False):
        try:
            if path:
                filePath = path
            else:
                filePath = self.getSource_mainfilePath()

            # Create Worker Thread
            worker_thumb = ThumbnailWorker(
                self,
                filePath=filePath,
                saveWidth=self.saveThumbWidth,
                width=self.itemPreviewWidth,
                height=self.itemPreviewHeight,
                regenerate=regenerate
                )

            worker_thumb.setAutoDelete(True)
            worker_thumb.result.connect(self.onThumbComplete)
            self.thumb_threadpool.start(worker_thumb)

            logger.debug("Refreshing Thumbnail")
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Thumbnail:\n{e}")
        

    #   Gets called from Thumb Worker Finished
    @err_catcher(name=__name__)
    def onThumbComplete(self, thumbImage, path, scale, fit, crop):
        #   Get Pixmap from QImage
        pixmap = QPixmap.fromImage(thumbImage)
    
        if pixmap:
            #   Save "Fullsize" Thumb to Disk
            thumbPath = self.getThumbnailPath(path)
            self.core.media.savePixmap(pixmap, thumbPath)

            #   Scale Pixap to Tile Preview Size
            scaledPixmap = self.core.media.scalePixmap(
                pixmap,
                self.itemPreviewWidth * scale,
                self.itemPreviewHeight * scale,
                fitIntoBounds=fit,
                crop=crop
                )

        self.data["source_mainFile_thumbnail"] = scaledPixmap

        if self.tileType == "sourceItem":
            self._notify("thumbnail")

        elif self.tileType == "sourceTile":
            self.setThumbnail()


    #   Adds Thumbnail to FileTile Label
    @err_catcher(name=__name__)
    def setThumbnail(self):
        thumb = self.data.get("source_mainFile_thumbnail")

        self.l_preview.setAlignment(Qt.AlignCenter)
        self.l_preview.setPixmap(thumb)


    @err_catcher(name=__name__)
    def setProxyIcon(self):
        #   Show Proxy Icon on Thumbnail
        if self.data["hasProxy"] and hasattr(self, "l_pxyIcon"):
            self.l_pxyIcon.show()

            #   Get Data Items
            filepath = self.data.get("source_proxyFile_path", "?")
            date = self.data.get("source_proxyFile_date", "?")
            size = self.data.get("source_proxyFile_size", "?")
            frames = self.data.get("source_proxyFile_frames", "?")

            xRez = self.data.get("source_proxyFile_xRez", "?")
            yRez = self.data.get("source_proxyFile_yRez", "?")
            resolution = f"{xRez} x {yRez}"
            fps = self.data.get("source_proxyFile_fps", "?")
            time = self.data.get("source_proxyFile_time", "?")
            codec = self.data.get("source_proxyFile_codec", "?")
            metadata = self.data.get("source_proxyFile_codecMetadata", "")


            #   Set Proxy Tooltip
            tip = (f"Proxy File detected:\n\n"
                f"File:              {filepath}\n"
                f"Date:            {date}\n"
                f"Size:              {size}\n"
                f"Resolution:  {resolution}\n"
                f"Duration:      {time}\n"
                f"Frames:        {frames}\n"
                f"FPS:               {fps}\n"
                f"Codec:          {codec}\n\n"
                f"{Utils.formatCodecMetadata(metadata)}"
                )
            
            self.l_pxyIcon.setToolTip(tip)
            

    #   Populates Duration when ready from Thread
    @err_catcher(name=__name__)
    def setDuration(self):
        sData = self.data

        for key in ["source_mainFile_frames",
                    "source_mainFile_fps",
                    "source_mainFile_time"]:
            if key not in sData:
                return

        if self.isVideo():
            #   Get Data Items
            frames = sData["source_mainFile_frames"]
            fps = sData["source_mainFile_fps"]
            time = sData["source_mainFile_time"]
           
            if self.browser.b_source_sorting_duration.isChecked():
                dur_str = f"{frames} - {fps} fps"
            else:
                dur_str = time

        elif self.isSequence:
            dur_str = str(len(self.data["seqFiles"]))

        else:
            dur_str = str(self.data["source_mainFile_frames"])

        if hasattr(self, "l_frames"):
            self.l_frames.setText(dur_str)

        self.setIconTooltip()
        

    @err_catcher(name=__name__)
    def setIconTooltip(self):
        if hasattr(self, "l_icon"):
            iData = self.data

            #   Get Data Items
            xRez = iData.get("source_mainFile_xRez", "?")
            yRez = iData.get("source_mainFile_yRez", "?")
            resolution = f"{xRez} x {yRez}"

            if self.isSequence:
                frames = len(self.getSequenceFiles())
            else:
                frames = iData.get("source_mainFile_frames", "?")

            fps = iData.get("source_mainFile_fps", "?")
            time = iData.get("source_mainFile_time", "?")
            codec = iData.get("source_mainFile_codec", "?")
            metadata = iData.get("source_mainFile_codecMetadata", "")


            tip = (f"File Type:      {self.fileType}\n"
                    f"Resolution:  {resolution}\n"
                    f"Duration:      {time}\n"
                    f"Frames:        {frames}\n"
                    f"FPS:              {fps}\n"
                    f"Codec:          {codec}\n\n"
                    f"{Utils.formatCodecMetadata(metadata)}"
                )

            self.l_icon.setToolTip(tip)

        if hasattr(self, "l_frames"):
            self.l_frames.setToolTip(tip)
    

    #   Returns Bool if File in Prism Video Formats
    @err_catcher(name=__name__)
    def isVideo(self, path=None, ext=None):
        if path:
            _, extension = os.path.splitext(Utils.getBasename(path))
        elif ext:
            extension = ext
        else:
            extension = Utils.getFileExtension(filePath=self.getSource_mainfilePath())
        
        return  extension.lower() in self.core.media.videoFormats
    

    #   Returns Bool if Codec is Supported by FFmpeg
    @err_catcher(name=__name__)
    def isCodecSupported(self):
        codec = self.data.get("source_mainFile_codec", "unknown")
        return self.browser.isCodecSupported(codec)
    

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
  

     #   Get Media Player Enabled State
    @err_catcher(name=__name__)
    def isViewerEnabled(self):
        # return self.browser.chb_enablePlayer.isChecked()
        return self.browser.b_enablePlayer.isChecked()



    #   Get Media Player Prefer Proxies State
    @err_catcher(name=__name__)
    def isPreferProxies(self):
        # return self.browser.chb_preferProxies.isChecked()
        return self.browser.b_preferProxies.isChecked()



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
                sendFiles = self.getSequenceFiles()
            
            elif self.fileType == "Audio":
                self.core.popup("Audio not Supported in the Preview Viewer, yet")
                return
            
            elif self.fileType == "Other":
                logger.debug("Non-media File Types Not Supported in the Preview Viewer")
                return
            
            else:
                logger.warning(f"ERROR:  File Type Not Supported in the Preview Viewer")
                return

            metadata = self.data


            logger.debug("Sending Image(s) to Media Viewer")

            self.browser.PreviewPlayer.loadMedia(sendFiles, metadata, isProxy, tile=self)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Send Image(s) to Media Viewer:\n{e}")


    @err_catcher(name=__name__)
    def configMetadata(self, filePath=None):
        if hasattr(self.browser, "metaEditor") and self.browser.metaEditor:
            self.browser.metaEditor.refresh(loadFilepath=filePath)
        else:
            self.browser.metaEditor = MetadataEditor(self.core, self.browser, loadFilepath=filePath)
            
        self.browser.metaEditor.show()


##   FOLDER TILES (Inherits from BaseTileItem)  ##
class FolderItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(FolderItem, self).__init__(browser, data, parent)
        self.tileType = "folderTile"

        self.data = data

        self.setupUi()
        self.refreshUi()

        logger.debug("Loaded Source FolderTile")


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
        folder_name = Utils.getBasename(dir_path)
        self.l_fileName.setText(folder_name)


    @err_catcher(name=__name__)
    def mouseDoubleClickEvent(self, event):
        self.browser.doubleClickFolder(self.data["dirPath"], mode="source")


    #   Place Holder for RCL for Folder Items
    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        rcmenu = QMenu(self.browser)

        sc = self.browser.shortcutsByAction

        Utils.createMenuAction("Show Data", sc, rcmenu, self.browser, self.TEST_SHOW_DATA)

        funct = lambda: Utils.openInExplorer(self.core, self.data["dirPath"])
        Utils.createMenuAction("Open in Explorer", sc, rcmenu, self.browser, funct)

        rcmenu.exec_(QCursor.pos())


##   FILE TILES ON THE SOURCE SIDE (process and holds the Data)(Inherits from BaseTileItem)     ##
class SourceFileItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(SourceFileItem, self).__init__(browser, data, passedData, parent)
        self.tileType = "sourceItem"

        self.tile = None

        self.updateCallbacks = {
            "duration": [],
            "thumbnail": [],
            "hash": [],
            "proxy": []
        }

        if passedData:
            self.data = passedData

        else:
            self.data = data
            self.data["source_mainFile_frames"] = None
            self.data["source_mainFile_hash"] = None
            self.data["hasProxy"] = False
            
            self.fileType = self.data["fileType"]

            if self.fileType == "Image Sequence":
                self.isSequence = True
                self.seqFiles = self.data["seqFiles"]
                self.data["source_mainFile_frames"] = len(self.seqFiles)

            else:
                self.isSequence = False
                self.seqFiles = None

            self.generateData()

        logger.debug("Loaded SourceFileItem")


    @err_catcher(name=__name__)
    def generateData(self):
        #   Get Main File Path
        filePath = self.getSource_mainfilePath()

        #   Duration
        if self.fileType in ["Videos", "Images", "Image Sequence"]:
            self.getFileInfo(filePath, self.onMainfileInfoReady)

        #   Main File Hash
        if self.isSequence:
            self.setFileHash(self.getSequenceFiles(), self.onMainfileHashReady)
        else:
            self.setFileHash(filePath, self.onMainfileHashReady)

        #   Icon
        icon = self.getIconByType(filePath)
        self.data["icon"] = icon

        #   Date
        date_data = Utils.getFileDate(filePath)
        self.data["source_mainFile_date_raw"] = date_data
        date_str = self.core.getFormattedDate(date_data)
        self.data["source_mainFile_date"] = date_str

        #   Size
        mainSize_data = Utils.getFileSize(filePath)
        self.data["source_mainFile_size_raw"] = mainSize_data
        mainSize_str = Utils.getFileSizeStr(mainSize_data)
        self.data["source_mainFile_size"] = mainSize_str

        self.getThumbnail()
        self.setProxyFile()


    #   Attach a FileTile and Process Callbacks
    @err_catcher(name=__name__)
    def registerTile(self, tile: "SourceFileTile"):
        self.tile = tile
        self.data["sourceTile"] = tile

        for field in self.updateCallbacks:
            ready = self.data.get(f"source_mainFile_{field}") is not None
            if ready:
                tile.updateField(field)
            else:
                self.updateCallbacks[field].append(tile.updateField)


    #   Process Callbacks when Ready
    @err_catcher(name=__name__)
    def _notify(self, field):
        for callback in self.updateCallbacks[field]:
            callback(field)

        self.updateCallbacks[field].clear()
    
    
    #   Sets Info when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileInfoReady(self, frames, fps, time, codec, codecMetadata, xRez, yRez):
        try:
            self.data["source_mainFile_xRez"] = xRez
            self.data["source_mainFile_yRez"] = yRez
            self.data["source_mainFile_frames"] = frames
            self.data["source_mainFile_fps"] = Utils.getFpsStr(fps)
            self.data["source_mainFile_time_raw"] = time
            self.data["source_mainFile_time"] = Utils.getFormattedTimeStr(time)
            self.data["source_mainFile_codec"] = codec
            self.data["source_mainFile_codecMetadata"] = codecMetadata

            self._notify("duration")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Main File Duration:\n{e}")


    #   Populates Hash when ready from Thread
    @err_catcher(name=__name__)
    def onMainfileHashReady(self, result_hash, tile):
        self.hashWatchdogTimer.stop()

        try:
            self.data["source_mainFile_hash"] = result_hash
            self._notify("hash")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Main File Hash:\n{e}")


    #   Sets Proxy Icon and FilePath if Proxy Exists
    @err_catcher(name=__name__)
    def setProxyFile(self):
        try:
            self.data["hasProxy"] = False

            #   Return if Not a Media File Type
            ext = Utils.getFileExtension(filePath=self.getSource_mainfilePath())
            if ext.lower() not in self.core.media.supportedFormats:
                return
            
            proxyFilepath = self.searchForProxyFile()

            if proxyFilepath:
                #   Set Proxy Flag
                self.data["hasProxy"] = True

                #   Set Source Proxy Path
                self.data["source_proxyFile_path"] = proxyFilepath

                #   Set Source Proxy Date
                date_data = Utils.getFileDate(proxyFilepath)
                date_str = self.core.getFormattedDate(date_data)
                self.data["source_proxyFile_date"] = date_str

                #   Set Source Proxy Filesize
                mainSize_data = Utils.getFileSize(proxyFilepath)
                mainSize_str = Utils.getFileSizeStr(mainSize_data)
                self.data["source_proxyFile_size"] = mainSize_str

                #   Set Source Proxy Hash
                self.setFileHash(proxyFilepath, self.onProxyfileHashReady, mode="proxy")

                self.getFileInfo(proxyFilepath, self.onProxyInfoReady)

                self.setProxyIcon()

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
            baseName = Utils.getBasename(fullPath)
            fileBase, _ = os.path.splitext(baseName)

            for pathTemplate in proxySearchList:
                #   Replace @MAINFILENAME@ with the base name (without extension)
                pathWithFilename = pathTemplate.replace("@MAINFILENAME@", fileBase)

                #   Replace @MAINFILEDIR@ name with any Prefix/Suffix
                def replace_dirToken(match):
                    pre = match.group(1) or ""
                    post = match.group(2) or ""
                    return os.path.join(os.path.dirname(baseDir), pre + Utils.getBasename(baseDir) + post)

                #   Find any prefix/suffix on @MAINFILEDIR@
                dir_pattern = re.compile(r"(.*?)@MAINFILEDIR@(.*?)")
                proxyPath = dir_pattern.sub(replace_dirToken, pathWithFilename)

                #   Convert Relative Path to Absolute
                proxyPath = os.path.normpath(proxyPath)

                #   Extract Info for Lookup
                proxyDir = os.path.dirname(proxyPath)
                targetFile = Utils.getBasename(proxyPath).lower()
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
    def onProxyfileHashReady(self, result_hash, tile):
        self.hashWatchdogTimer.stop()

        try:
            self.data["source_proxyFile_hash"] = result_hash

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Proxy File Hash:\n{e}")


    #   Sets Info when ready from Thread
    @err_catcher(name=__name__)
    def onProxyInfoReady(self, frames, fps, time, codec, codecMetadata, xRez, yRez):
        try:
            self.data["source_proxyFile_xRez"] = xRez
            self.data["source_proxyFile_yRez"] = yRez
            self.data["source_proxyFile_frames"] = frames
            self.data["source_proxyFile_fps"] = Utils.getFpsStr(fps)
            self.data["source_proxyFile_time_raw"] = time
            self.data["source_proxyFile_time"] = Utils.getFormattedTimeStr(time)
            self.data["source_proxyFile_codec"] = codec
            self.data["source_proxyFile_codecMetadata"] = codecMetadata

            self._notify("proxy")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Main File Duration:\n{e}")



##   FILE TILES ON THE SOURCE SIDE (the Tile UI)(Inherits from BaseTileItem)    ##
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

        self.item.registerTile(self)

        logger.debug("Loaded SourceFileTile")


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
            filePath = self.getSource_mainfilePath()

            # Display Name
            displayName = (
                self.data["displayName"] if self.isSequence else Utils.getBasename(filePath)
            )
            self.l_fileName.setText(displayName)
            self.l_fileName.setToolTip(f"FilePath: {filePath}")

            # Filetype Icon
            if self.isSequence:
                self.setIcon(self.browser.icon_sequence)
            else:
                self.setIcon(self.data["icon"])

            self.l_date.setText(self.data["source_mainFile_date"])

            # File Size
            self.setFileSize()

            # Hash tooltip placeholder
            self.l_fileSize.setToolTip("Calculating file hash…")

            # Proxy Icon
            if not self.isSequence:
                self.setProxyIcon()

            if self.fileType in ["Videos", "Images", "Image Sequence"]:
                self.setDuration()


        except Exception as e:
            logger.warning(f"ERROR: Failed to Load Source FileTile UI:\n{e}")


    #   Gets Called From FileItem Callbacks to Update when Ready
    @err_catcher(name=__name__)
    def updateField(self, field):        
        if field == "duration":
            self.setDuration()
        elif field == "thumbnail":
            self.setThumbnail()
        elif field == "hash":
            self.setMainHash()
        elif field == "proxy":
            self.setProxyIcon()

    
    @err_catcher(name=__name__)
    def setFileSize(self):
        if self.isSequence:
            totalSize_raw = self.data["seqSize"]
            totalSize_str = Utils.getFileSizeStr(totalSize_raw)
        else:
            totalSize_str = self.data["source_mainFile_size"]

        self.l_fileSize.setText(totalSize_str)


    @err_catcher(name=__name__)
    def rightClicked(self, pos):
        if self.tileLocked:
            logger.debug("Tile is Locked: Aborting Right-click Menu.")
            return
        
        rcmenu = QMenu(self.browser)
        hasProxy = self.data.get("hasProxy", False)
        sc = self.browser.shortcutsByAction


        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action
        

        #   Always Displayed
        Utils.createMenuAction("Add Selected to Destination", sc, rcmenu, self.browser, self.addToDestList)

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Set Selected", sc, rcmenu, self.browser, lambda: self.setChecked(True))

        Utils.createMenuAction("Un-Select", sc, rcmenu, self.browser, lambda: self.setChecked(False))

        #   Displayed if Single Selection
        if len(self.browser.selectedTiles) == 1:
            rcmenu.addAction(_separator())

            funct = lambda: self.getThumbnail(regenerate=True)
            Utils.createMenuAction("Regenerate Thumbnail", sc, rcmenu, self.browser, funct)

            rcmenu.addAction(_separator())

            funct = lambda: Utils.displayCombinedMetadata(self.getSource_mainfilePath())
            Utils.createMenuAction("Show MetaData (Main File)", sc, rcmenu, self.browser, funct)

            funct = lambda: Utils.displayCombinedMetadata(self.getSource_proxyfilePath())
            Utils.createMenuAction("Show MetaData (Proxy)", sc, rcmenu, self.browser, funct, enabled=hasProxy)

            Utils.createMenuAction("Show Data", sc, rcmenu, self.browser, self.TEST_SHOW_DATA)

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Show in Viewer", sc, rcmenu, self.browser, self.sendToViewer)

            funct = lambda: Utils.openInExplorer(self.core, self.getSource_mainfilePath())
            Utils.createMenuAction("Open in Explorer", sc, rcmenu, self.browser, funct)

        #   Add List Menu Actions
        rcmenu.addAction(_separator())
        self.browser.listRCL(sc, rcmenu, self.browser.lw_source)

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



##   FILE TILES ON THE DESTINATION SIDE (holds the Data)(Inherits from BaseTileItem)    ##
class DestFileItem(BaseTileItem):
    def __init__(self, browser, data=None, passedData=None, parent=None):
        super(DestFileItem, self).__init__(browser, data, passedData, parent)
        self.tileType = "destItem"

        self.tile = None

        self.data = passedData if passedData else data

        self.fileType = self.data["fileType"]

        logger.debug("Loaded DestFileItem")


    @err_catcher(name=__name__)
    def registerTile(self, tile: "SourceFileTile"):
        self.tile = tile
        self.data["destTile"] = tile
        self.data["sourceTile"].data["destTile"] = tile



##   FILE TILES ON THE DESTINATION SIDE (the Tile UI)(Inherits from BaseTileItem)    ##
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
        self.item.registerTile(self)

        logger.debug("Loaded DestFileTile")


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
        if self.tileLocked:
            logger.debug("Tile is Locked: Aborting refreshUI.")
            return
        try:
            self.setModifiedName()

            #   Set Filetype Icon
            if self.isSequence:
                self.setIcon(self.browser.icon_sequence)
            else:
                self.setIcon(self.data["icon"])

            self.setDuration()
            self.setThumbnail()
            self.setProxyIcon()
            self.setQuantityUI("idle")
            self.toggleProxyProgbar()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Load Destination FileTile UI:\n{e}")


    #   Displays Proxy Progbar if Applicable
    @err_catcher(name=__name__)
    def toggleProxyProgbar(self):
        enabled = False

        if self.browser.proxyEnabled and self.isVideo():
            if self.browser.proxyMode == "copy":
                enabled = self.data.get("hasProxy", False)

            elif self.isCodecSupported():
                enabled = True
        
        self.useProxy = enabled
        self.proxyProgBar.setVisible(enabled)


    #   Sets the FileName based on Name Modifiers
    @err_catcher(name=__name__)
    def setModifiedName(self):
        try:
            dest_mainFile_dir = self.getDestPath()
            source_mainFile_path = self.getSource_mainfilePath()

            #   Get Modified Name
            name = self.getModifiedName(self.data["displayName"])

            #    Set Name and Path
            self.data["dest_mainFile_path"] = os.path.join(dest_mainFile_dir, name)
            self.l_fileName.setText(name)

            tip = (f"Source:          {source_mainFile_path}\n"
                   f"Destination:  {os.path.join(self.getDestPath(), name)}")
            self.l_fileName.setToolTip(tip)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Get Name Override:\n{e}")

        
    @err_catcher(name=__name__)
    def getModifiedName(self, orig_name):
        if self.browser.sourceFuncts.chb_ovr_fileNaming.isChecked():
            return self.browser.applyMods(orig_name)
        else:
            return orig_name
       

    #   Returns Proxy Source Path
    @err_catcher(name=__name__)
    def getProxy(self):
        return self.data.get("source_proxyFile_path", None)


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
                baseName = Utils.getBasename(sourceMainPath)

            destPath = self.getDestPath()

            #   Modify Name is Enabled
            baseName = self.getModifiedName(baseName)

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
            proxy_fileName = Utils.getBasename(source_proxyFilePath)

            #   Modify Name if Enabled
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
            mainSize = Utils.getFileSize(self.getSource_mainfilePath())

            if not mainSize:
                return 0

            #   Get Presets and Multiplier from Preset
            presetName = self.browser.proxySettings.get("proxyPreset", "")
            pData = self.browser.proxyPresets.getPresetData(presetName)
            mult = float(pData.get("Multiplier", 0.0))

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
                total_frames = self.data["source_mainFile_frames"]

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
            mainSize = Utils.getFileSize(self.data["dest_mainFile_path"])
            proxySize = Utils.getFileSize(self.data["dest_proxyFile_path"])

            if mainSize <= 0 or proxySize <= 0:
                logger.warning("Cannot update multiplier: one of the sizes is zero")
                return
            
            #   Get Scale
            scale_str = self.browser.proxySettings.get("proxyScale", "100%")
            scale_pct = int(scale_str.strip("%")) / 100.0

            #   Reverse the Multiplier Calc
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
    def setQuantityUI(self, mode):
        copied = ""
        dash = ""
        total = ""

        #   Gets Frames and File Size of Sequence
        if self.isSequence:
            totalSize_raw = self.data["seqSize"]
            self.data["totalSeqSize"] = totalSize_raw
            mainSize = Utils.getFileSizeStr(totalSize_raw)

            duration = str(len(self.getSequenceFiles()))
            self.data["seqDuration"] = duration
            
        #   Get Frames and File Size of Non-Sequences
        else:
            mainSize = self.data["source_mainFile_size"]
            duration = str(self.data["source_mainFile_frames"])

        #   Sets UI Based on Mode
        if mode in ["idle", "complete"]:
            if "source_mainFile_frames" in self.data:
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
        if self.tileLocked:
            logger.debug("Tile is Locked: Aborting Right-click Menu.")
            return
        
        rcmenu = QMenu(self.browser)
        destExists =  os.path.exists(self.getDestMainPath())
        sc = self.browser.shortcutsByAction


        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action


        #   Displayed Always
        Utils.createMenuAction("Remove Selected Tiles", sc, rcmenu, self.browser, self.removeFromDestList)

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Set Selected", sc, rcmenu, self.browser, lambda: self.setChecked(True))
        Utils.createMenuAction("Un-Select", sc, rcmenu, self.browser, lambda: self.setChecked(False))

        rcmenu.addAction(_separator())

        funct = lambda: self.configMetadata(filePath=self.getSource_mainfilePath())
        Utils.createMenuAction("Show Source File in Metadata Editor", sc, rcmenu, self.browser, funct)

        #   Displayed if Single Selection
        if len(self.browser.selectedTiles) == 1:
            Utils.createMenuAction("Show Data", sc, rcmenu, self.browser, self.TEST_SHOW_DATA)      #   TESTING

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Show in Viewer", sc, rcmenu, self.browser, self.sendToViewer)

            funct = lambda: Utils.openInExplorer(self.core, self.getSource_mainfilePath())
            Utils.createMenuAction("Open in Explorer (Source)", sc, rcmenu, self.browser, funct)

            rcmenu.addAction(_separator())

            funct = lambda: Utils.displayCombinedMetadata(self.getDestMainPath())
            Utils.createMenuAction("Show MetaData (Transferred File)", sc, rcmenu, self.browser, funct, enabled=destExists)

            funct = lambda: Utils.openInExplorer(self.core, self.getDestMainPath())
            Utils.createMenuAction("Open in Explorer (Transferred File)", sc, rcmenu, self.browser, funct, enabled=destExists)

        #   Add List Menu Actions
        rcmenu.addAction(_separator())
        self.browser.listRCL(sc, rcmenu, self.browser.lw_destination)


        rcmenu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def removeFromDestList(self):
        if self.tileLocked:
            logger.debug("Tile is Locked: Aborting removeFromDestList.")
            return
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
    def getDestProxyFilepath(self):
        
        #   Helper to Resolve Absolute or Relative Path
        def _resolvePath(user_dir, dest_dir):
            try:
                #   Convert to Path
                user_path = Path(os.path.normpath(user_dir))

                #   Determine Relative or Absolute
                if user_path.is_absolute():
                    resolvedPath = user_path
                else:
                    resolvedPath = os.path.join(dest_dir, user_path)

                return resolvedPath
            
            except Exception as e:
                logger.warning(f"ERROR:  Failed to Resolve Path:\n{e}")
                return None

        try:
            sourcePath = self.getSource_mainfilePath()
            #   Get Source Base Name and Modify if Enabled
            source_baseFile = Utils.getBasename(sourcePath)
            source_baseFile = self.getModifiedName(source_baseFile)

            #   Get Proxy Settings
            proxyMode = self.browser.proxyMode
            resolved_proxyDir = self.browser.resolved_proxyDir
            proxySettings = self.browser.proxySettings.copy()
            try:
                preset = self.browser.proxyPresets.getPresetData(proxySettings["proxyPreset"])

            except KeyError:
                raise RuntimeError(f"Proxy preset {proxySettings['proxyPreset']} not found in settings")
            
            #   Make Proxy Name
            source_baseName = os.path.splitext(source_baseFile)[0]
            proxy_baseFile = source_baseName + preset["Extension"]

            #   Convert dest_dir to Path
            dest_dir = Path(self.getDestPath())

            proxyPath = None

            ##  OVERRIDE PROXY PATH  ##
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
                if resolved_proxyDir:
                    proxy_dir = Path(resolved_proxyDir)
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
                    if resolved_proxyDir:
                        proxy_dir = Path(resolved_proxyDir)
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

        #   Get Main Paths
        sourcePath = self.getSource_mainfilePath()
        destPath = self.getDestMainPath()
        self.data["dest_mainFile_path"] = destPath

        if self.isSequence:
            transferList = []
            for file in self.getSequenceFiles():
                basename = Utils.getBasename(file)
                name = self.getModifiedName(basename)
                destPath = os.path.join(self.getDestPath(), name)

                transferList.append({"sourcePath": file,
                                     "destPath": destPath})

        else:
            transferList = [{"sourcePath": sourcePath,
                            "destPath": destPath}]

        #   Create Transfer Dict
        self.transferData = {"proxyEnabled": proxyEnabled,
                             "proxyAction": None}

        ##  IF PROXY IS ENABLED ##
        if proxyEnabled and self.isVideo() and self.isCodecSupported():
            proxySettings = options["proxySettings"]
            self.transferData["proxyMode"] = proxyMode
            self.transferData["proxySettings"] = proxySettings

            #   Temp Vars for Logic
            hasProxy = self.data["hasProxy"]
            isCopyMode = proxyMode == "copy"
            isGenerateMode = proxyMode == "generate"
            isMissingMode = proxyMode == "missing"

            if hasProxy and (isCopyMode or isMissingMode):
                self.transferData["proxyAction"] = "copy"
            elif isGenerateMode or (isMissingMode and not hasProxy):
                self.transferData["proxyAction"] = "generate"

            #   Get Proxy Destination Path
            self.transferData["destProxy"] = self.getDestProxyFilepath()

        #   Start Timers
        self.transferTimer = ElapsedTimer()

        #   Call Main File Transfer
        self.transferMainFile(transferList)


    #   Call Worker Thread to Copy Main File
    @err_catcher(name=__name__)
    def transferMainFile(self, transferList):
        self.setTransferStatus(progBar="transfer", status="Queued")
        self.setQuantityUI("copyMain")
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
            self.l_amountCopied.setText(Utils.getFileSizeStr(copied_size))
            self.main_copiedSize = copied_size


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyCopyProgress(self, value, copied_size):
        if self.transferState != "Cancelled":
            self.setTransferStatus(progBar="proxy", status="Transferring Proxy")

            self.proxyProgBar.setValue(value)
            self.l_amountCopied.setText(Utils.getFileSizeStr(copied_size))
            self.proxy_copiedSize = copied_size


    #   Updates the UI During the Transfer
    @err_catcher(name=__name__)
    def update_proxyGenerateProgress(self, value, frame):
        if self.transferState != "Cancelled":
            self.setTransferStatus(progBar="proxy", status="Generating Proxy")
            self.proxyProgBar.setValue(value)
            self.l_amountCopied.setText(str(frame))
            self.proxy_copiedSize = self.getMultipliedProxySize(frame=frame)


    @err_catcher(name=__name__)
    def checkFilesExist(self, mode):
        if mode == "main":
            try:
                destMainPath = self.getDestMainPath()
                destFiles = []

                if self.isSequence:
                    for file in self.getSequenceFiles():
                        basename = Utils.getBasename(file)
                        name = self.getModifiedName(basename)
                        destPath = os.path.join(self.getDestPath(), name)
                        destFiles.append(destPath)

                else:
                    destFiles.append(destMainPath)

                #   Iterate through all Transferred Files to Check Exists
                filesExist = all(os.path.isfile(file) for file in destFiles)

                return filesExist
        
            except Exception as e:
                logger.warning(f"ERROR: Unable to Check if Files Exist:\n{e}")
                return False
            
        elif mode == "proxy":
            return os.path.exists(self.data["dest_proxyFile_path"])
    

    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def main_transfer_complete(self, success):
        self.transferTimer.stop()
        self.data["transferTime"] = self.transferTimer.elapsed()

        if success:
            self.transferProgBar.setValue(100)

            #   Check if all the Transferred Files Exist in Destination
            if self.checkFilesExist("main"):
                self.setTransferStatus(progBar="transfer", status="Generating Hash")

                self.data["mainFile_result"] = "Complete"
                logger.debug("Main Transfer Successful")

                #   Calls for Hash Generation
                self.generateDestHashs()
            
            else:
                errMsg = "Transfer File(s) Does Not Exist"
                self.addTransferError(self.data["displayName"], errMsg)
                logger.warning(f"ERROR: {self.data['displayName']} - {errMsg}")
                self.data["mainFile_result"] = errMsg
                self.setTransferStatus(progBar="transfer", status="Error", tooltip=errMsg)

        else:
            errMsg = "Transfer Failed"
            self.addTransferError(self.data["displayName"], errMsg)
            logger.warning(f"ERROR: {self.data['displayName']} - {errMsg}")
            self.data["mainFile_result"] = errMsg
            self.setTransferStatus(progBar="transfer", status="Error", tooltip=errMsg)


    #   Called After Hash Generation for UI Feedback
    @err_catcher(name=__name__)
    def generateDestHashs(self):
        self._pending_tiles = set()
        self._hash_results = {}
        dummy_tile = QObject()

        if self.isSequence:
            destFiles = []
            for file in self.getSequenceFiles():
                basename = Utils.getBasename(file)
                name = self.getModifiedName(basename)
                destPath = os.path.join(self.getDestPath(), name)
                destFiles.append(destPath)

            self.setFileHash(destFiles, self.onDestHashReady, mainTile=dummy_tile)

        else:
            self._pending_tiles.add(dummy_tile)
            self.setFileHash(self.getDestMainPath(), self.onDestHashReady, mainTile=dummy_tile)


    @err_catcher(name=__name__)
    def setDestHash(self, dest_hash, tile):
        tile.hashWatchdogTimer.stop()

        tile.data["dest_mainFile_hash"] = dest_hash
        orig_hash = tile.data.get("source_mainFile_hash", None)

        #   If Transfer Hash Check is Good
        if dest_hash == orig_hash:
            self.seqHashes = True

        #   Transfer Hash is Not Correct
        else:
            self.seqHashes = False

        if self.seqHashes:
            statusMsg = "Transfer Successful"
            tile.data["mainFile_result"] = statusMsg

            self.setTransferStatus(progBar="transfer", status="Complete")
            self.setQuantityUI("complete")

            logger.status(f"Main Transfer complete: {tile.data['dest_mainFile_path']}")

        else:
            statusMsg = "ERROR:  Transferred Hash Incorrect"
            self.addTransferWarning(self.data["displayName"], "Transferred Hash Incorrect")
            tile.data["mainFile_result"] = statusMsg

            status = "Warning"
            logger.warning(f"Transferred Hash Incorrect: {tile.getSource_mainfilePath()}")

            hashMsg = (f"Status: {statusMsg}\n\n"
                       f"Source Hash:   {orig_hash}\n"
                       f"Transfer Hash: {dest_hash}")

            self.setTransferStatus(progBar="transfer", status=status, tooltip=hashMsg)


    #   Called After Hash Generation for UI Feedback
    @err_catcher(name=__name__)
    def onDestHashReady(self, dest_hash, tile):
        self.hashWatchdogTimer.stop()

        self.data["dest_mainFile_hash"] = dest_hash
        orig_hash = self.data.get("source_mainFile_hash", None)

        #   If Transfer Hash Check is Good
        if dest_hash == orig_hash:
            statusMsg = "Transfer Successful"
            self.data["mainFile_result"] = statusMsg

            self.setQuantityUI("complete")

            hashMsg = (f"Status: {statusMsg}\n\n"
                       f"Source Hash:   {orig_hash}\n"
                       f"Transfer Hash: {dest_hash}")
            
            self.setTransferStatus(progBar="transfer", status="Complete", tooltip=hashMsg)

            #   Proxy Enabled
            if self.useProxy:
                self.setTransferStatus(progBar="proxy", status="Queued")

                #   Copy Proxy if Applicable
                if self.transferData["proxyAction"] == "copy":
                    self.setQuantityUI("copyProxy")
                    self.transferProxy()

                #   Generate Proxy if Enabled
                if self.transferData["proxyAction"] == "generate":
                    self.setQuantityUI("generate")
                    self.generateProxy()

            logger.status(f"Main Transfer complete: {self.data['dest_mainFile_path']}")
            
        #   Transfer Hash is Not Correct
        else:
            statusMsg = "ERROR:  Transferred Hash Incorrect"
            self.addTransferWarning(self.data["displayName"], "Transferred Hash Incorrect")
            self.data["mainFile_result"] = statusMsg

            status = "Warning"
            logger.warning(f"Transferred Hash Incorrect: {self.getSource_mainfilePath()}")

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
        settings["frames"] = self.data["source_mainFile_frames"]

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
            if self.checkFilesExist("proxy"):
                proxySize = Utils.getFileSize(self.data["dest_proxyFile_path"])
                self.data["dest_proxyFile_size"] = Utils.getFileSizeStr(proxySize)

                status = "Generating Hash"
                tip = "Proxy Transferred"
                self.setQuantityUI("complete")
                logger.status(f"Proxy Transfer Complete: {self.data['dest_proxyFile_path']}")

                self.setFileHash(self.data["dest_proxyFile_path"], self.onDestProxyHashReady, mode="proxy", mainTile=self)

            else:
                errMsg = "Transferred Proxy Does Not Exist"
                self.addTransferError(self.data["displayName"], errMsg)
                logger.warning(f"ERROR: {self.data['displayName']} - {errMsg}")
                status = "Error"
                tip = "ERROR:  Proxy File Does Not Exist"

        else:
            errMsg = "Proxy Transfer Failed"
            self.addTransferError(self.data["displayName"], errMsg)
            logger.warning(f"ERROR: {self.data['displayName']} - {errMsg}")
            status = "Error"
            tip = "ERROR:  Proxy Transfer Failed"

        self.setTransferStatus(progBar="proxy", status=status, tooltip=tip)


    #   Called After Hash Generation
    @err_catcher(name=__name__)
    def onDestProxyHashReady(self, dest_hash, tile):
        self.hashWatchdogTimer.stop()

        self.data["dest_proxyFile_hash"] = dest_hash
        orig_hash = self.data.get("source_proxyFile_hash", None)

        #   If Transfer Hash Check is Good
        if dest_hash == orig_hash:
            statusMsg = "Proxy Transfer Successful"
            self.data["proxyFile_result"] = statusMsg

            self.setQuantityUI("complete")

            hashMsg = (f"Status: {statusMsg}\n\n"
                       f"Source Hash:   {orig_hash}\n"
                       f"Transfer Hash: {dest_hash}")
            
            self.setTransferStatus(progBar="proxy", status="Complete", tooltip=hashMsg)


    #   Gets Called from the Finished Signal
    @err_catcher(name=__name__)
    def proxyGenerate_complete(self, result):
        self.proxyProgBar.setValue(100)
       
        if result == "success":
            if self.checkFilesExist("proxy"):
                proxySize = Utils.getFileSize(self.data["dest_proxyFile_path"])
                self.data["dest_proxyFile_size"] = Utils.getFileSizeStr(proxySize)
                status = "Complete"
                tip = "Proxy Generated"

                self.updateProxyPresetMultiplier()
                logger.status(f"Proxy Generation Complete: {self.data['dest_proxyFile_path']}")

            else:
                status = "Error"
                tip = "ERROR:  Generated Proxy Does Not Exist"
                self.addTransferError(self.data["displayName"], "Generated Proxy Does Not Exist")
                logger.warning(tip)

            self.setQuantityUI("complete")
        
        else:
            status = "Error"
            tip = f"ERROR:  Proxy Generation failed: {result}"
            self.addTransferError(self.data["displayName"], "Proxy Generation Failed")
            logger.warning(tip)

        self.data["proxyFile_result"] = status
        self.setTransferStatus(progBar="proxy", status=status, tooltip=tip)


    #   Returns Total Transferred Size
    @err_catcher(name=__name__)
    def getCopiedSize(self):
        return self.main_copiedSize + self.proxy_copiedSize


    @err_catcher(name=__name__)
    def addTransferError(self, fileName, error):
        self.browser.transferErrors[fileName] = error


    @err_catcher(name=__name__)
    def addTransferWarning(self, fileName, warning):
        self.browser.transferWarnings[fileName] = warning

