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
import subprocess
import logging
from multiprocessing import cpu_count as MP_cpu_count

from PIL import Image
import numpy as np
from OpenGL.GL import *
import av

import PyOpenColorIO as ocio


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *



from PrismUtils.Decorators import err_catcher

import SourceTab_Utils as Utils
from SourceTab_Models import FileTileMimeData
from WorkerThreads import FileInfoWorker
from PopupWindows import OcioPresetsEditor


#   Color names for Beauty/Color pass
COLORNAMES = ["color", 
              "beauty",
              "combined",
              "diffuse",
              "diffcolor",
              "diffusecolor"]



logger = logging.getLogger(__name__)



class PreviewPlayer_GPU(QWidget):
    frameReady = Signal(int, np.ndarray)
    cacheUpdated = Signal()


    def __init__(self, browser):
        super(PreviewPlayer_GPU, self).__init__()
        self.sourceBrowser = browser
        self.core = browser.core

        self.PreviewCache = FrameCacheManager(self.core, pWidth=400)

        self.iconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")
        self.ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))
        self.ffprobePath = Utils.getFFprobePath()

        self.externalMediaPlayers = None
        self.mediaFiles = []
        self.renderResX = 300
        self.renderResY = 169

        self.tlPaused = False
        self.prvIsSequence = False

        self.pduration = 0
        self.pwidth = 0
        self.pheight = 0
        self.pstart = 0
        self.pend = 0
        self.previewEnabled = True
        self.state = "enabled"

        self.playTimer = QTimer(self)
        self.playTimer.timeout.connect(self._playNextFrame)
        self._playFrameIndex = 0
        self._playBaseOffset = 0

        self.updateExternalMediaPlayers()
        self.setupUi()
        self.connectEvents()
        self.loadSettings()
        self.resetImage()

        self.enableControls(False)


        # Connect Signal to GL Widget
        self.frameReady.connect(self.displayWindow.displayFrame)
        self.PreviewCache.firstFrameComplete.connect(self.onFirstFrameReady)

        self.core.registerCallback("onProjectBrowserClose",
                                   self.onProjectBrowserClose,
                                   plugin=self.sourceBrowser.plugin)


    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(400, 100)


    #   Populate Media Players Based on Prism Version
    @err_catcher(name=__name__)
    def updateExternalMediaPlayers(self):
        #   For Prism 2.0.18+
        if hasattr(self.core.media, "getExternalMediaPlayers"):
            self.externalMediaPlayers = self.core.media.getExternalMediaPlayers()

        #   For Before Prism 2.0.18
        else:
            player = self.core.media.getExternalMediaPlayer()
            self.externalMediaPlayers = [player]


    #   Called When ProjectBrowser Closes
    @err_catcher(name=__name__)
    def onProjectBrowserClose(self, projectBrowser):
        #   Stop Running Cache Worker Threads
        if getattr(self, "PreviewCache", None):
            self.PreviewCache.stop()
            self.PreviewCache.threadpool.waitForDone(1000)

        #   Save Current OCIO Settings
        self.saveOcioSettings()


    @err_catcher(name=__name__)
    def setupUi(self):
        self.lo_preview_main = QVBoxLayout(self)
        self.lo_preview_main.setContentsMargins(0, 0, 0, 0)
        self.l_info = QLabel(self)
        self.l_info.setText("")
        self.l_info.setObjectName("l_info")
        self.lo_preview_main.addWidget(self.l_info)

        #   Viewer Window
        self.displayWindow = GLVideoDisplay(self, self.core)
        self.lo_preview_main.addWidget(self.displayWindow)

        #   Proxy Icon Label
        self.l_pxyIcon = QLabel(self.displayWindow)
        self.l_pxyIcon.setPixmap(self.sourceBrowser.icon_proxy.pixmap(40, 40))
        self.l_pxyIcon.setStyleSheet("background-color: rgba(0,0,0,0);")
        self.l_pxyIcon.setVisible(False)
        self.l_pxyIcon.move(3, 3)

        #   Loading Animation
        self.l_loading = QLabel(self)
        self.l_loading.setAlignment(Qt.AlignCenter)
        self.l_loading.setVisible(False)

        #   Timeline
        self.w_timeslider = QWidget()
        self.lo_timeslider = QHBoxLayout(self.w_timeslider)
        self.lo_timeslider.setContentsMargins(0, 0, 0, 0)
        self.l_start = QLabel()
        self.l_end = QLabel()
        self.sl_previewImage = QSlider(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sl_previewImage.sizePolicy().hasHeightForWidth())
        self.sl_previewImage.setSizePolicy(sizePolicy)
        self.sl_previewImage.setOrientation(Qt.Horizontal)
        self.sl_previewImage.setObjectName("sl_previewImage")
        self.sl_previewImage.setMaximum(999)
        self.lo_timeslider.addWidget(self.l_start)
        self.lo_timeslider.addWidget(self.sl_previewImage)
        self.lo_timeslider.addWidget(self.l_end)
        self.sp_current = QSpinBox()
        self.sp_current.sizeHint = lambda: QSize(30, 0)
        self.sp_current.setStyleSheet("min-width: 30px;")
        self.sp_current.setValue(self.pstart)
        self.sp_current.setButtonSymbols(QAbstractSpinBox.NoButtons)
        sizePolicy = self.sp_current.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Preferred)
        self.sp_current.setSizePolicy(sizePolicy)
        self.lo_timeslider.addWidget(self.sp_current)
        self.lo_preview_main.addWidget(self.w_timeslider)

        self.w_playerCtrls = QWidget()
        self.lo_playerCtrls = QHBoxLayout(self.w_playerCtrls)
        self.lo_playerCtrls.setContentsMargins(0, 0, 0, 0)
        
        #   Buttons
        for name in ["first", "prev", "play", "next", "last"]:
            btn = QToolButton()
            path = os.path.join(self.iconPath, f"{name}.png")
            icon = Utils.getIconFromPath(path)
            btn.setIcon(icon)
            setattr(self, f"b_{name}", btn)

        self.playIcon = Utils.getIconFromPath(os.path.join(self.iconPath, "play.png"))
        self.pauseIcon = Utils.getIconFromPath(os.path.join(self.iconPath, "pause.png"))


        self.sl_previewImage.setToolTip("Cache: Idle")

        self.b_first.setToolTip("First Frame")
        self.b_prev.setToolTip("Previous Frame")
        self.b_play.setToolTip("Play / Pause")
        self.b_next.setToolTip("Next Frame")
        self.b_last.setToolTip("Last Frame")
        
        self.lo_playerCtrls.addWidget(self.b_first)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_prev)
        self.lo_playerCtrls.addWidget(self.b_play)
        self.lo_playerCtrls.addWidget(self.b_next)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_last)
        self.lo_preview_main.addWidget(self.w_playerCtrls)

        self.displayWindow.setMinimumWidth(self.renderResX)
        self.displayWindow.setMinimumHeight(self.renderResY)
        self.displayWindow.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.displayWindow.clickEvent = self.displayWindow.mouseReleaseEvent
        self.displayWindow.mouseReleaseEvent = self.previewClk

        self.displayWindow.resizeEventOrig = self.displayWindow.resizeEvent
        self.displayWindow.resizeEvent = self.previewResizeEvent

        self.sl_previewImage.origMousePressEvent = self.sl_previewImage.mousePressEvent
        self.sl_previewImage.mousePressEvent = self.sliderMousePress
        self.sl_previewImage.valueChanged.connect(self.sliderChanged)
        self.sl_previewImage.sliderPressed.connect(self.onSliderPressed)
        self.sl_previewImage.sliderReleased.connect(self.onSliderReleased)

        self.sp_current.editingFinished.connect(
            lambda: self.setCurrentFrame(self.sp_current.value() - 1, manual=True, reset=True)
            )

        self.b_first.clicked.connect(self.onFirstClicked)
        self.b_prev.clicked.connect(self.onPrevClicked)
        self.b_play.clicked.connect(self.onPlayClicked)
        self.b_next.clicked.connect(self.onNextClicked)
        self.b_last.clicked.connect(self.onLastClicked)

        self.PreviewCache.cacheUpdated.connect(self.updateCacheSlider)


    #   Loads Player Settings
    @err_catcher(name=__name__)
    def loadSettings(self, pData=None):

        #   Gets Saved User Config if not Passed
        if not pData:
            pData = self.core.getConfig("browser", "mediaPlayerSettings")

            #   Create and Save New Default Data if it Does Not Exist
            if not pData:
                pData = {
                    "cacheThreads": self.getDefaultCacheThreads(),
                    "check_size": 20,
                    "check_color1": (0.0, 0.0, 0.0),
                    "check_color2": (0.1, 0.1, 0.1)
                    }
                
                #   Save Settings
                self.core.setConfig("browser", "mediaPlayerSettings", pData)

        #   Set Cache Max Threads
        self.PreviewCache.setThreadpool(pData["cacheThreads"])

        #   Set Viewer Settings
        self.displayWindow.setBackground(pData["check_size"],
                                            pData["check_color1"],
                                            pData["check_color2"])


    #   Saves Current OCIO Settings to Project Config
    @err_catcher(name=__name__)
    def saveOcioSettings(self):
        mData = {
            "currOcioPreset": self.sourceBrowser.ocioPresets.currentPreset,
            "ocioPresetOrder": self.sourceBrowser.ocioPresets.presetOrder,
            }

        #   Save to Project Config
        self.sourceBrowser.plugin.saveSettings(key="ocioSettings", data=mData)


    #   Returns Good Initial Number for Cache Threads based on CPUs
    @err_catcher(name=__name__)
    def getDefaultCacheThreads(self):
        numProcs = MP_cpu_count()

        if numProcs <= 2:
            return 1
        elif numProcs <= 4:
            return 2
        elif numProcs <= 8:
            return numProcs - 2
        elif numProcs <= 16:
            return numProcs - 4
        else:
            return min(8, numProcs // 2)


    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state):
        self.previewEnabled = state
        self.displayWindow.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)


    @err_catcher(name=__name__)
    def previewResizeEvent(self, event):
        #   Call Original Resize
        if hasattr(self.displayWindow, "resizeEventOrig"):
            self.displayWindow.resizeEventOrig(event)

        #   Update Aspect for Current Media
        self.adjustPreviewAspect()

        #   Resize GL Widget
        if hasattr(self.displayWindow, "frame") and self.pwidth > 0 and self.pheight > 0:
            container_width = self.displayWindow.width()
            aspect = self.pheight / self.pwidth
            target_height = int(container_width * aspect)
            self.displayWindow.resize(container_width, target_height)

            #   Update GL Viewport
            self.displayWindow.update()


    @err_catcher(name=__name__)
    def adjustPreviewAspect(self):
        if self.pwidth > 0 and self.pheight > 0:
            #   Calculate Preview Size from Window Width and Image Aspect Ration
            window_width = self.displayWindow.width()
            aspect = self.pheight / self.pwidth
            target_height = max(1, int(window_width * aspect))

            #   Resize the Preview Widget
            self.displayWindow.setMinimumHeight(target_height)
            self.displayWindow.setMaximumHeight(target_height)

            #   Resize GL Window
            if hasattr(self.displayWindow, "scale_w") and hasattr(self.displayWindow, "scale_h"):
                self.displayWindow.scale_w = 1.0
                self.displayWindow.scale_h = 1.0

            #   Force GL Widget to Update
            self.displayWindow.update()

        text = self.l_info.toolTip() or self.l_info.text()
        self.setInfoText(text)



    @err_catcher(name=__name__)
    def enableControls(self, enable):
        self.w_playerCtrls.setEnabled(enable)
        self.sp_current.setEnabled(enable)
        self.sl_previewImage.setEnabled(enable)


    @err_catcher(name=__name__)
    def updateCacheSlider(self, frame=None, reset=False):
        #   Reset and Calc Frames
        if reset or not self.PreviewCache.cache:
            total_frames = 1
            cachedMask = [False]
        else:
            total_frames = len(self.PreviewCache.cache)
            cachedMask = [self.PreviewCache.cache[i] is not None for i in range(total_frames)]

        #   Set Sizing
        slider_width = max(1, self.sl_previewImage.width())
        slider_height = 6
        min_segment_px = 5  # Min Width of a Frame segment (pix)

        stops = []

        #   Calculate Range and Segments
        for i in range(total_frames):
            #   Pixel Range for this Frame
            x_start_px = int(i / total_frames * slider_width)
            x_end_px   = int((i + 1) / total_frames * slider_width)
            if x_end_px - x_start_px < min_segment_px:
                x_end_px = x_start_px + min_segment_px
            #   Clamp to Slider Width
            x_end_px = min(x_end_px, slider_width)

            #   Cache Colors (color and transparent)
            color = "#465A78" if cachedMask[i] else "transparent"

            #   Add a Stop for each Pixel in the Frame Range
            for px in range(x_start_px, x_end_px):
                ratio = px / slider_width
                stops.append(f"stop:{ratio} {color}")

        #   Make Stylesheet
        gradient_str = ", ".join(stops)

        style = f"""
        QSlider::groove:horizontal {{
            height: {slider_height}px;
            border-radius: 3px;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                {gradient_str}
            );
        }}
        """
        self.sl_previewImage.setStyleSheet(style)
        
        #   Update Tooltip
        cached = max(0, sum(cachedMask))

        if self.sourceBrowser.b_cacheEnabled.isChecked():
            if self.PreviewCache.isRunning:
                status = "ACTIVE"
            elif cached == total_frames:
                status = "COMPLETE"
            elif cached < total_frames:
                status = "IDLE"
            else:
                status = "UNKNOWN"
            tip = f"Cache: {status} ({cached} of {total_frames} frames in memory)" if status != "UNKNOWN" else "Cache: UNKNOWN"
        else:
            status = "DISABLED"
            tip = f"Cache: {status} ({cached} of {total_frames} frames in memory)" if cached > 0 else "Cache: DISABLED"

        self.sl_previewImage.setToolTip(tip)


    #   Generate a Black 16:9 Frame at Current Preview Width
    @err_catcher(name=__name__)
    def makeBlackFrame(self):
        width = self.displayWindow.width()
        if width <= 0:
            width = 300

        height = int(width / (16/9))

        self.pwidth = width
        self.pheight = height

        frame = np.zeros((height, width, 3), dtype=np.uint8)
        return frame


###########################################
###########    MOUSE ACTIONS   ############

    #   Checks if Dragged Object is a File Tile
    @err_catcher(name=__name__)
    def onDragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-fileTile"):
            e.acceptProposedAction()
        else:
            e.ignore()


    #   Adds Dashed Outline to Player During Drag
    @err_catcher(name=__name__)
    def onDragMoveEvent(self, widget, objName, e):
        if e.mimeData().hasFormat("application/x-fileTile"):
            e.acceptProposedAction()
            widget.setStyleSheet(
                f"#{objName} {{ border-style: dashed; border-color: rgb(100, 200, 100); border-width: 2px; }}"
            )
        else:
            e.ignore()


    #   Removes Dashed Line
    @err_catcher(name=__name__)
    def onDragLeaveEvent(self, widget, e):
        widget.setStyleSheet("")


    #   Sends File Tile to Viewer
    @err_catcher(name=__name__)
    def onDropEvent(self, widget, e):
        widget.setStyleSheet("")

        if isinstance(e.mimeData(), FileTileMimeData):
            e.acceptProposedAction()

            #   Get First Tile if Multiple
            tiles = e.mimeData().fileTiles()
            tile = next(iter(tiles))

            #   Show in Viewer
            tile.sendToViewer()
        else:
            e.ignore()


###############################################
###########    PLAYBACK CONTROLS   ############

    @err_catcher(name=__name__)
    def resetImage(self):
        self.displayWindow.displayFrame(0, self.makeBlackFrame())
        self.adjustPreviewAspect()

        self.PreviewCache.clear()
        self.l_pxyIcon.setVisible(False)
        self.currentFrameIdx = 0
        self._playFrameIndex = 0
        self._playBaseOffset = 0
        self._pausedOffset = 0

        self.sl_previewImage.setValue(0)
        self.sp_current.setValue(0)
        self.updateCacheSlider(reset=True)


    @err_catcher(name=__name__)
    def onCurrentChanged(self, frame):
        # if not self.PreviewCache.cache:
        #     return

        self.sl_previewImage.blockSignals(True)
        self.sl_previewImage.setValue(frame)
        self.sl_previewImage.blockSignals(False)

        if self.sp_current.value() != (self.pstart + frame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + frame))
            self.sp_current.blockSignals(False)


    @err_catcher(name=__name__)
    def onOcioChanged(self, idx):
        presetName = self.sourceBrowser.cb_ocioPresets.currentText()
        self.sourceBrowser.ocioPresets.currentPreset = presetName
        self.configureOCIO()
        self.reloadCurrentFrame()


    @err_catcher(name=__name__)
    def setTimelinePaused(self, paused: bool):
        if paused:
            if self.isPlaying():
                self.playTimer.stop()
                if hasattr(self, "_playStartTime"):
                    self._pausedOffset += self._playStartTime.elapsed()
        else:
            if not hasattr(self, "_playStartTime"):
                self._playStartTime = QElapsedTimer()
            self._playStartTime.restart()
            self.playTimer.start(10)

        #   Update Button Icon
        if paused:
            self.b_play.setIcon(self.playIcon)
            self.b_play.setToolTip("Play")
        else:
            self.b_play.setIcon(self.pauseIcon)
            self.b_play.setToolTip("Pause")

        #   Set State
        self.tlPaused = paused


    @err_catcher(name=__name__)
    def isPlaying(self):
        return hasattr(self, "playTimer") and self.playTimer.isActive()


    @err_catcher(name=__name__)
    def setCurrentFrame(self, frameIdx:int, manual:bool = False, reset:bool = False):
        """Move the Playhead to a Specific Frame and Update the UI."""
        
        frameIdx = max(0, min(frameIdx, len(self.PreviewCache.cache) - 1))
        self.currentFrameIdx = frameIdx
        self._playFrameIndex = frameIdx

        if reset:
            self._playBaseOffset = frameIdx * getattr(self, "_playInterval", 1000/24)
            self._pausedOffset = 0
            if hasattr(self, "_playStartTime"):
                self._playStartTime.restart()

        elif manual:
            if hasattr(self, "_playInterval"):
                self._playBaseOffset = frameIdx * self._playInterval
            if hasattr(self, "_playStartTime"):
                self._playStartTime.restart()

        #   UI Sync
        self.sl_previewImage.blockSignals(True)
        self.sl_previewImage.setValue(frameIdx)
        self.sl_previewImage.blockSignals(False)

        self.sp_current.blockSignals(True)
        self.sp_current.setValue(frameIdx + self.pstart)
        self.sp_current.blockSignals(False)

        #   Display the Frame
        frame = self.PreviewCache.getFrame(frameIdx)
        if frame is not None:
            self.frameReady.emit(frameIdx, frame)


    @err_catcher(name=__name__)
    def reloadCurrentFrame(self):
        if hasattr(self, "currentFrameIdx"):
            self.setCurrentFrame(self.currentFrameIdx, manual=True)


    @err_catcher(name=__name__)
    def onFirstClicked(self):
        self.setCurrentFrame(0, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onPrevClicked(self):
        self.setCurrentFrame(self.currentFrameIdx - 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onPlayClicked(self):
        if self.isPlaying():
            self.setTimelinePaused(True)
        else:
            fps = getattr(self, "fps", 24) or 24
            self._playInterval = 1000.0 / float(fps)
            self.setTimelinePaused(False)


    @err_catcher(name=__name__)
    def _playNextFrame(self):
        elapsed_ms = self._playStartTime.elapsed() + self._playBaseOffset + self._pausedOffset
        target_frame = int(elapsed_ms / self._playInterval)

        total_frames = len(self.PreviewCache.cache)
        if total_frames <= 0:
            return
        if target_frame >= total_frames:
            target_frame %= total_frames

        if target_frame != self._playFrameIndex:
            self.setCurrentFrame(target_frame, manual=False)


    @err_catcher(name=__name__)
    def onNextClicked(self):
        self.setCurrentFrame(self.currentFrameIdx + 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def onLastClicked(self):
        self.setCurrentFrame(len(self.PreviewCache.cache) - 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def sliderChanged(self, frameIdx):
        was_playing = self.isPlaying()
        if was_playing:
            self.playTimer.stop()

        self.setCurrentFrame(frameIdx, manual=True, reset=True)

        if was_playing:
            self._playStartTime.restart()
            self.playTimer.start(10)


    @err_catcher(name=__name__)
    def onSliderPressed(self):
        self._resumeAfterDrag = self.isPlaying()
        if self._resumeAfterDrag:
            self.playTimer.stop()


    @err_catcher(name=__name__)
    def onSliderReleased(self):
        if self._resumeAfterDrag:
            self._playStartTime.restart()
            self.playTimer.start(10)
        self._resumeAfterDrag = False


    @err_catcher(name=__name__)
    def sliderMousePress(self, event):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.sl_previewImage.initStyleOption(opt)
            groove_rect = self.sl_previewImage.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self.sl_previewImage
            )
            handle_rect = self.sl_previewImage.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self.sl_previewImage
            )

            if groove_rect.contains(event.pos()) and not handle_rect.contains(event.pos()):
                new_val = QStyle.sliderValueFromPosition(
                    self.sl_previewImage.minimum(),
                    self.sl_previewImage.maximum(),
                    event.pos().x() - groove_rect.x(),
                    groove_rect.width()
                )
                self.sl_previewImage.setValue(new_val)
                event.accept()
                return

        self.sl_previewImage.origMousePressEvent(event)


    @err_catcher(name=__name__)
    def previewClk(self, event):
        if event.button() == Qt.LeftButton:
            self.onPlayClicked()



###########################################
###########    LOADING MEDIA   ############

    #   Entry Point for Media to be Played
    @err_catcher(name=__name__)
    def loadMedia(self, mediaFiles, metadata, isProxy, tile=None):
        """Entry Point for Media to be Played."""

        self.mediaFiles = mediaFiles
        self.metadata = metadata
        self.isProxy = isProxy
        self.tile = tile

        #   Reset Timeline and Image
        self.resetImage()

        #   Configure OCIO 
        self.configureOCIO()

        #   Setup Image and Timeline
        self.updatePreview(mediaFiles)

        #   Resize Player for Image
        self.adjustPreviewAspect()



    @err_catcher(name=__name__)
    def updatePreview(self, mediaFiles):
        if not self.previewEnabled:
            return
        
        #   Shows PXY Icon if Proxy
        self.l_pxyIcon.setVisible(self.isProxy)

        if len(mediaFiles) > 0:
            _, extension = os.path.splitext(mediaFiles[0])
            extension = extension.lower()

            #   Image Sequence
            if (len(mediaFiles) > 1 and extension not in self.core.media.videoFormats):
                self.fileType = "Images"
                iData = FileInfoWorker.probeFile(mediaFiles[0], self, self.core)
                self.prvIsSequence = True
                start, end = self.core.media.getFrameRangeFromSequence(mediaFiles)
                duration = len(mediaFiles)
                useControls = True

            #   Single Image
            elif len(mediaFiles) == 1 and extension not in self.core.media.videoFormats:
                self.fileType = "Images"
                iData = FileInfoWorker.probeFile(mediaFiles[0], self, self.core)
                self.prvIsSequence = False
                start = 1
                end = 1
                duration = 1
                useControls = False

            #   Video File
            else:
                self.fileType = "Videos"
                iData = FileInfoWorker.probeFile(mediaFiles[0], self, self.core)
                duration = iData[0]
                start = 1
                end = start + duration - 1
                self.prvIsSequence = False
                useControls = True

            self.pstart = start
            self.pend = end
            self.pduration = duration
            self.fps = round(float(iData[1]), 2)
            self.codec = iData[3]
            self.pwidth = iData[5]
            self.pheight = iData[6]

            #   Sets Framerange on Slider
            self.l_start.setText(str(self.pstart))
            self.l_end.setText(str(self.pend))

            #   Sets Up Current Frame Spinbox
            self.sp_current.setMinimum(int(self.pstart))
            self.sp_current.setMaximum(int(self.pend))

            #   Sets Slider Max
            self.sl_previewImage.setMaximum(self.pduration - 1)

            #   Sets Controls Enabled/Disabled
            self.enableControls(useControls)

            #   Updates Preview Info at the Top
            self.updatePrvInfo()

            #   Build Dict for Caching
            prevData = {
                "start": self.pstart,
                "end": self.pend,
                "duration": self.pduration,
                "fps": self.fps,
                "codec": self.codec,
                "width": self.pwidth,
                "height": self.pheight
            }

            #   Get Window Width for Scaling
            windowWidth = self.displayWindow.width()

            #   Set the Media in the Cache System
            self.PreviewCache.setMedia(mediaFiles, windowWidth, self.fileType, self.prvIsSequence, prevData)

            #   Start the Caching
            if self.sourceBrowser.cacheEnabled:
                self.PreviewCache.start()

            return True

        #   No Image Loaded
        self.sl_previewImage.setEnabled(False)
        self.l_start.setText("")
        self.l_end.setText("")
        self.enableControls(False)
        self.sp_current.setEnabled(False)


    @err_catcher(name=__name__)
    def updatePrvInfo(self):
        if not self.mediaFiles:
            return

        if not os.path.exists(self.mediaFiles[0]):
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.displayWindow.setToolTip("")
            return

        #   Filename (Use Placeholders for Sequences)
        if self.prvIsSequence:
            seqs = self.core.media.detectSequences(self.mediaFiles)
            fileName = Utils.getBasename(list(seqs.keys())[0])
        else:
            fileName = Utils.getBasename(self.mediaFiles[0])

        #   Get File Date
        pdate = self.core.getFileModificationDate(self.mediaFiles[0])

        if self.pduration == 1:
            frStr = "frame"
        else:
            frStr = "frames"

        #   Display String
        infoStr = (f"{fileName}\n"
                   f"{self.pwidth} x {self.pheight}   -   {self.pduration} {frStr}   -   {pdate}")

        #   Add File Size if Enabled
        if self.core.getConfig("globals", "showFileSizes"):
            size = 0
            for file in self.mediaFiles:
                if os.path.exists(file):
                    size += Utils.getFileSize(file)

            infoStr += f"   -   {Utils.getFileSizeStr(size)}"

        self.setInfoText(infoStr)
        self.l_info.setToolTip(infoStr)


    @err_catcher(name=__name__)
    def setInfoText(self, text):
        metrics = QFontMetrics(self.l_info.font())
        lines = []
        for line in text.split("\n"):
            elidedText = metrics.elidedText(line, Qt.ElideRight, self.displayWindow.width()-20)
            lines.append(elidedText)

        self.l_info.setText("\n".join(lines))



###########################################
###########    IMAGE DISPLAY   ############

    @err_catcher(name=__name__)
    def onFirstFrameReady(self, frameIdx: int):
        self.currentFrameIdx = frameIdx
        self.sl_previewImage.setValue(0)
        self.sp_current.setValue(frameIdx)
        
        self.loadFrame(frameIdx)


    @err_catcher(name=__name__)
    def loadFrame(self, frameIdx):
        # if not self.PreviewCache.cache:
        #     logger.debug("No frames in cache yet")
        #     return

        frameIdx = max(0, min(frameIdx, len(self.PreviewCache.cache)-1))
        frame = self.PreviewCache.getFrame(frameIdx)

        if frame is not None:
            self.frameReady.emit(frameIdx, frame)


    @err_catcher(name=__name__)
    def configureOCIO(self):                                                 #   TODO - ADD FALLBACKS
        pName = self.sourceBrowser.ocioPresets.currentPreset
        oData = self.sourceBrowser.ocioPresets.getPresetData(pName)

        input_space = oData["Color_Space"]
        display = oData["Display"]
        view = oData["View"]
        look = oData["Look"]
        luts = oData["LUT"]

        self.displayWindow.setOcioTransforms(
            inputSpace=input_space,
            display=display,
            view=view,
            look=look,
            luts=luts,
        )



    ########    DELETE AFTER TESTING    #########

    @err_catcher(name=__name__)
    def printOcioInfo(self):                                                                              # TESTING
        try:
            config = ocio.GetCurrentConfig()
            print("=== OCIO Config Info ===")
            print(f"Config Name: {config.getName()}")
            print(f"Search Path: {config.getSearchPath()}")
            print(f"Working Dir: {config.getWorkingDir()}\n")

            print("ColorSpaces:")
            for cs in config.getColorSpaces():
                try:
                    fam = getattr(cs, "getFamilyName", lambda: "")()
                    print(f"  - {cs.getName()} (family={fam})")
                except Exception:
                    print(f"  - {cs.getName()} (family=Unknown)")

            print("\nDisplays + Views:")
            for display in config.getDisplays():
                print(f"  Display: {display}")
                for view in config.getViews(display):
                    print(f"    View: {view}")

            print("\nRoles:")
            try:
                for role_name in config.getRoles():
                    cs = None
                    try:
                        cs = config.getColorSpace(role_name)
                        cs_name = cs.getName() if cs else "None"
                    except Exception:
                        cs_name = "Unresolved"
                    print(f"  {role_name} -> {cs_name}")
            except Exception:
                print("  (Unable to query roles with this OCIO version)")

            print("\nLooks:")
            try:
                for look in config.getLooks():
                    try:
                        name = look.getName()
                        process_space = look.getProcessSpace()
                        transform = look.getTransform()
                        print(f"  - {name} (processSpace={process_space}, transform={transform})")
                    except Exception as e:
                        print(f"  - <Failed to query look: {e}>")
            except Exception:
                print("  (No looks found in this config)")

            print("\n\n\n")

        except Exception as e:
            print(f"[OCIO] Failed to query config: {e}")

################################




#######################################
###########    RCL MENU    ############

    @err_catcher(name=__name__)
    def rclPreview(self, pos):
        menu = self.getMediaPreviewMenu()

        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self):
        if len(self.mediaFiles) < 1:
            return
        
        hasProxy = self.tile.data.get("hasProxy", False)
        sc = self.sourceBrowser.shortcutsByAction
        rcmenu = QMenu(self)

        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action


        path = self.mediaFiles[0]

        #   Cache
        iconPath = os.path.join(self.iconPath, "refresh.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Reload Cache", sc, rcmenu, self, self.reloadCache, icon=icon)

        rcmenu.addAction(_separator())

        #   External Player
        playMenu = QMenu("Play in", self)
        iconPath = os.path.join(self.iconPath, "play.png")
        icon = self.core.media.getColoredIcon(iconPath)
        playMenu.setIcon(icon)

        if self.externalMediaPlayers is not None:
            for player in self.externalMediaPlayers:
                funct = lambda x=None, name=player.get("name", ""): self.compare(name)
                Utils.createMenuAction(player.get("name", ""), sc, playMenu, self, funct)

        #   Add External Player Menu
        rcmenu.addMenu(playMenu)

        Utils.createMenuAction("Default", sc, playMenu, self, lambda: self.compare(prog="default"))
       
        rcmenu.addAction(_separator())

        iconPath = os.path.join(self.iconPath, "folder.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Open in Explorer", sc, rcmenu, self, lambda: self.core.openFolder(path), icon=icon)

        iconPath = os.path.join(self.iconPath, "copy.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Copy", sc, rcmenu, self, lambda: self.core.copyToClipboard(path, file=True), icon=icon)

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Set File Checked", sc, rcmenu, self, lambda: self.setTileChecked(True))
        Utils.createMenuAction("Set File UnChecked", sc, rcmenu, self, lambda: self.setTileChecked(False))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Add to Transfer List", sc, rcmenu, self, self.addToTransferList)
        Utils.createMenuAction("Remove from Transfer List", sc, rcmenu, self, self.removeFromTransferList)

        rcmenu.addAction(_separator())

        funct = lambda: Utils.displayCombinedMetadata(self.tile.getSource_mainfilePath())
        Utils.createMenuAction("Show Metadata (Main File)", sc, rcmenu, self, funct)

        funct = lambda: Utils.displayCombinedMetadata(self.tile.getSource_proxyfilePath())
        Utils.createMenuAction("Show Metadata (Proxy File)", sc, rcmenu, self, funct)

        rcmenu.addAction(_separator())

        iconPath = os.path.join(self.iconPath, "configure.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Player Settings", sc, rcmenu, self, self.editPlayerSettings, icon=icon)

        Utils.createMenuAction("Edit OCIO Presets", sc, rcmenu, self, self.editOcioPresets)

        return rcmenu



    @err_catcher(name=__name__)
    def reloadCache(self):
        self.resetImage()
        self.configureOCIO()
        self.updatePreview(self.mediaFiles)


    @err_catcher(name=__name__)
    def tileExists(self, obj):
        try:
            if obj is None:
                return False
            
            obj.objectName()
            return True
        
        except RuntimeError:
            return False


    @err_catcher(name=__name__)
    def setTileChecked(self, checked):
        sourceTile = self.tile.data.get("sourceTile", None)
        destTile = self.tile.data.get("destTile", None)

        if self.tileExists(sourceTile):
            sourceTile.setChecked(checked)

        if self.tileExists(destTile):
            destTile.setChecked(checked)


    @err_catcher(name=__name__)
    def addToTransferList(self):
        sourceTile = self.tile.data.get("sourceTile", None)

        if self.tileExists(sourceTile):
            sourceTile.addToDestList()


    @err_catcher(name=__name__)
    def removeFromTransferList(self):
        destTile = self.tile.data.get("destTile", None)

        if self.tileExists(destTile):
            destTile.removeFromDestList()


    @err_catcher(name=__name__)
    def editPlayerSettings(self):
        #   Get Settings from User Config (Prism.json)
        pData = self.core.getConfig("browser", "mediaPlayerSettings")

        #   Create and Load UI Window
        playerConfigWindow = PlayerConfigPopup(self, self.core)
        playerConfigWindow.loadSettings(pData)

        result = playerConfigWindow.exec()

        if result == QDialog.Accepted:
            #   Get Settings from UI
            pData = playerConfigWindow.getSettings()

            #   Save to Local Prism User Settings (Prism.json)
            self.core.setConfig("browser", "mediaPlayerSettings", pData)

            self.loadSettings(pData)


    @err_catcher(name=__name__)
    def editOcioPresets(self):
        currPreset = self.sourceBrowser.cb_ocioPresets.currentText()
        self.sourceBrowser.ocioPresets.currentPreset = currPreset

        editWindow = OcioPresetsEditor(self.core, self)
        logger.debug("Opening OCIO Presets Editor")
        editWindow.exec_()

        if editWindow.result() == "Save":
            try:
                presetData, presetOrder = editWindow.getPresets()

                #   Detect Newly Added or Modified Presets
                existingNames = set(self.sourceBrowser.ocioPresets.getPresetNames())

                #   Capture Original Data for Comparison
                originalDataMap = {
                    name: Utils.normalizeData(self.sourceBrowser.ocioPresets.getPresetData(name))
                    for name in existingNames
                }

                #   Clear and Re-add Presets
                self.sourceBrowser.ocioPresets.clear()

                for name in presetOrder:
                    data = presetData.get(name, {})

                    self.sourceBrowser.ocioPresets.addPreset(name, data)

                    normalizedData = Utils.normalizeData(data)

                    originalData = originalDataMap.get(name)

                    #   Save if New or Modified
                    if name not in existingNames or normalizedData != originalData:
                        pData = {"name": name, "data": data}
                        Utils.savePreset(self.core, "ocio", name, pData, project=True, checkExists=False)
                        logger.debug(f"Saved preset '{name}' to project")


                self.sourceBrowser.ocioPresets.presetOrder = presetOrder

                self.saveOcioSettings()

                self.sourceBrowser.loadOcioCombo()


                logger.debug("Saved OCIO Presets")

            except Exception as e:
                logger.warning(f"ERROR: Failed to Save OCIO Presets:\n{e}")



    @err_catcher(name=__name__)
    def compare(self, prog=""):
        if prog == "default":
            progPath = ""
        else:
            mediaPlayer = None
            if prog and self.externalMediaPlayers:
                matchingPlayers = [player for player in self.externalMediaPlayers if player.get("name") == prog]
                if matchingPlayers:
                    mediaPlayer = matchingPlayers[0]
                else:
                    self.core.popup("Can't find media player: %s" % prog)
                    return

            if not mediaPlayer:
                mediaPlayer = self.externalMediaPlayers[0] if self.externalMediaPlayers else None

            progPath = (mediaPlayer.get("path") or "") if mediaPlayer else ""

        comd = []
        filePath = self.mediaFiles[0]
        comd = [progPath, filePath]

        if comd:
            with open(os.devnull, "w") as f:
                logger.debug("launching: %s" % comd)
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
                except:
                    comd = "%s %s" % (comd[0], comd[1])
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))



######################################
#######      Frame Cache       #######
                    
class VideoCacheWorker(QRunnable):
    def __init__(self, core, mediaPath, cacheRef, mutex, pWidth, progCallback):
        super().__init__()
        self.core = core
        self.mediaPath = mediaPath
        self.cacheRef = cacheRef
        self.mutex = mutex
        self.pWidth = pWidth
        self.progCallback = progCallback
        self._running = True


    @err_catcher(name=__name__)
    def stop(self) -> None:
        '''Stop Frame Cache Worker'''
        self._running = False


    @err_catcher(name=__name__)
    def run(self):
        '''Start Video Cache Worker'''
        
        try:
            #   Start FFmpeg Player
            container = av.open(self.mediaPath)
            stream = container.streams.video[0]

            #   Let FFmpeg Handle Threading
            try:
                stream.thread_type = "AUTO"
            except Exception:
                pass

            firstFrame_signaled = False

            for frame_idx, frame in enumerate(container.decode(stream)):
                if not self._running:
                    break

                #   Scale & Flip
                src_w, src_h = frame.width, frame.height
                if src_w <= 0 or src_h <= 0:
                    continue

                scale = self.pWidth / float(src_w)
                dst_w = self.pWidth
                dst_h = max(1, int(round(src_h * scale)))

                try:
                    f2 = frame.reformat(width=dst_w, height=dst_h,
                                        format='rgba', interpolation='BILINEAR')
                    img = f2.to_ndarray()

                except Exception:
                    #   If Reformat Fails, Fallback to Raw ndarray and Resize
                    img = frame.to_ndarray(format='rgba')
                    if img.shape[1] != dst_w or img.shape[0] != dst_h:
                        img = np.array(
                            Image.fromarray(img).resize((dst_w, dst_h), Image.BILINEAR)
                        )

                img = np.flipud(img)

                #   Lock Cache and Load Frame into Cache
                self.mutex.lock()
                self.cacheRef[frame_idx] = img
                self.mutex.unlock()

                #   Emit When First Frame Ready
                if not firstFrame_signaled and self.progCallback:
                    firstFrame_signaled = True
                    self.progCallback(frame_idx, firstFrame=True)

                #   Emit Regular Progress
                if self.progCallback:
                    self.progCallback(frame_idx, firstFrame=False)

            container.close()

        except Exception as e:
            logger.warning(f"ERROR: Unable to Cache Video File {self.mediaPath}: {e}")

            #   Fallback: Fill Cache with Fallback Images
            fallbackPath = Utils.getFallBackImage(self.core, filePath=self.mediaPath)
            try:
                img = np.array(Image.open(fallbackPath).convert("RGBA"))
                scale = self.pWidth / float(img.shape[1])
                dst_w = self.pWidth
                dst_h = max(1, int(round(img.shape[0] * scale)))
                img = np.array(
                    Image.fromarray(img).resize((dst_w, dst_h), Image.BILINEAR)
                )
                img = np.flipud(img)

                #   Fill Every Cache Slot with Placeholder
                self.mutex.lock()
                for i in self.cacheRef.keys():
                    self.cacheRef[i] = img
                self.mutex.unlock()

                #   Signal First Frame Ready
                if self.progCallback:
                    self.progCallback(0, firstFrame=True)

            except Exception as fe:
                logger.error(f"Failed to load fallback image: {fe}")



class ImageCacheWorker(QRunnable):
    def __init__(self, core, imgPath, frame_idx, cacheRef, mutex, pWidth, progCallback):
        super().__init__()
        self.core = core
        self.imgPath = imgPath
        self.frame_idx = frame_idx
        self.cacheRef = cacheRef
        self.mutex = mutex
        self.pWidth = int(pWidth)
        self.progCallback = progCallback
        self._running = True

        self.oiio = self.core.media.getOIIO()


    @err_catcher(name=__name__)
    def getfirstColorLayer(self, layers):
        for name in COLORNAMES:
            for layer in layers:
                if name.lower() in layer.lower():
                    return layer
        return None


    @err_catcher(name=__name__)
    def stop(self) -> None:
        '''Stop Frame Cache Worker'''
        self._running = False


    @err_catcher(name=__name__)
    def run(self):
        '''Start Image Cache Worker'''

        try:
            if not self._running:
                return
            if not os.path.exists(self.imgPath):
                raise FileNotFoundError(f"Image not found: {self.imgPath}")

            #   Get Layer Names from Prism
            layers = self.core.media.getLayersFromFile(self.imgPath)

            #   Find the First Color/Beauty Layer
            selected_layer = self.getfirstColorLayer(layers)

            inp = self.oiio.ImageInput.open(self.imgPath)
            if not inp:
                raise RuntimeError(f"OIIO could not open: {self.imgPath}")

            spec = inp.spec()
            channels = spec.channelnames
            img_np = None

            #   If Beauty/Color Layer Found
            if selected_layer:
                rgb_channels = [c for c in channels if selected_layer in c and not c.endswith(".A")]
                if len(rgb_channels) == 3:
                    chbegin = channels.index(rgb_channels[0])
                    chend = channels.index(rgb_channels[-1]) + 1
                    img = inp.read_image(0, 0, chbegin, chend, self.oiio.UINT8)
                    img_np = np.array(img).reshape(spec.height, spec.width, 3)

            #   Fallback: Read Whatever is There
            if img_np is None:
                img = inp.read_image(format=self.oiio.UINT8)
                img_np = np.array(img).reshape(spec.height, spec.width, spec.nchannels)

                #   Grayscale (Repeat Channel to RGB)
                if img_np.shape[-1] == 1:
                    img_np = np.repeat(img_np, 3, axis=-1)
                 #  RGBA
                elif img_np.shape[-1] >= 4:
                    img_np = img_np[..., :4]
                #   RGB
                else:
                    img_np = img_np[..., :3]

            inp.close()

            #   Resize
            src_w, src_h = spec.width, spec.height
            scale = self.pWidth / float(src_w)
            dst_w, dst_h = self.pWidth, max(1, int(round(src_h * scale)))
            if (dst_w, dst_h) != (src_w, src_h):
                img_np = np.array(Image.fromarray(img_np).resize((dst_w, dst_h), Image.BILINEAR))

            img_np = np.flipud(img_np)

            #   Lock Cache and Load Frame into Cache
            self.mutex.lock()
            self.cacheRef[self.frame_idx] = img_np
            self.mutex.unlock()

            if self.progCallback:
                self.progCallback(self.frame_idx, firstFrame=(self.frame_idx == 0))

        except Exception as e:
            logger.warning(f"ERROR: Unable to Cache Image {self.imgPath}: {e}")

            #   Fallback: Fill Cache with Fallback Images
            fallbackPath = Utils.getFallBackImage(self.core, filePath=self.imgPath)
            try:
                img = np.array(Image.open(fallbackPath).convert("RGBA"))
                scale = self.pWidth / float(img.shape[1])
                dst_w, dst_h = self.pWidth, max(1, int(round(img.shape[0] * scale)))
                img = np.array(Image.fromarray(img).resize((dst_w, dst_h), Image.BILINEAR))
                img = np.flipud(img)

                self.mutex.lock()
                self.cacheRef[self.frame_idx] = img
                self.mutex.unlock()

                if self.progCallback:
                    self.progCallback(self.frame_idx, firstFrame=(self.frame_idx == 0))

            except Exception as fe:
                logger.error(f"Failed to load fallback image: {fe}")


            
class FrameCacheManager(QObject):
    cacheUpdated = Signal(int)
    cacheComplete = Signal()
    firstFrameComplete = Signal(int)


    def __init__(self, core, pWidth=400):
        super().__init__()
        self.core = core
        self.pWidth = int(pWidth)

        self.mediaFiles = []
        self.cache = {}
        self.workers = []

        self.total_frames = 0
        self._firstFrameEmitted = False
        self.isRunning = False

        self.mutex = QMutex()


    #########################
    #######   API    ########


    @err_catcher(name=__name__)
    def setThreadpool(self, threadNum:int) -> None:
        '''Updates Cache Threadpool Max Workers'''

        self.threadpool = QThreadPool(self)
        self.threadpool.setMaxThreadCount(threadNum)

        logger.debug(f"Cache Threads set to {threadNum}")


    @err_catcher(name=__name__)
    def setMedia(self, mediaFiles:list, prevWidth:int, fileType:str, isSeq:bool, prevData:dict) -> None:
        '''Sets Media to Frame Cache Manager'''

        self.stop()
        self.clear()

        self.mediaFiles = mediaFiles
        self.fileType = fileType
        self.isSeq = isSeq

        self.pstart = prevData["start"]
        self.pend = prevData["end"]
        self.pduration = prevData["duration"]
        self.fps = prevData["fps"]
        self.codec = prevData["codec"]
        self.pwidth = prevWidth
        self.pheight = prevData["height"]

        #   Initialize Cache Dict with None for each Frame
        if self.isSeq:
            self.totalFrames = len(self.mediaFiles)

        else:
            mediaPath = self.mediaFiles[0]
            container = av.open(mediaPath)
            stream = container.streams.video[0]
            self.totalFrames = stream.frames if stream.frames else sum(1 for _ in container.decode(stream))
            if not self.codec:
                self.codec = stream.codec_context.name.lower()

            container.close()

        self.cache = {i: None for i in range(self.totalFrames)}


    @err_catcher(name=__name__)
    def start(self) -> None:
        '''Starts the Frame Caching'''

        if not self.mediaFiles:
            return
        
        logger.debug("Frame Caching Started")

        self.workers = []
        self.isRunning = True

        #   Image Sequences
        if self.isSeq:
            #   Launch Worker per Sequence Image
            for frame_idx, imgPath in enumerate(self.mediaFiles):
                if self.cache.get(frame_idx) is None:
                    worker = ImageCacheWorker(
                        self.core,
                        imgPath,
                        frame_idx,
                        self.cache,
                        self.mutex,
                        self.pWidth,
                        self._onWorkerProgress
                    )
                    worker.setAutoDelete(True)
                    self.workers.append(worker)
                    self.threadpool.start(worker)

        #   Non-Sequences
        else:
            mediaPath = self.mediaFiles[0]
            worker_needed = any(v is None for v in self.cache.values())

            if worker_needed:
                #   Launch Worker Instance
                worker = VideoCacheWorker(
                    self.core,
                    mediaPath,
                    self.cache,
                    self.mutex,
                    self.pWidth,
                    self._onWorkerProgress,
                )
                worker.setAutoDelete(True)
                self.workers.append(worker)
                self.threadpool.start(worker)


    @err_catcher(name=__name__)
    def stop(self) -> None:
        '''Stops the Frame Caching'''

        self.isRunning = False

        for worker in self.workers:
            worker.stop()
        self.workers.clear()

        logger.debug("Frame Cache Stopped")


    @err_catcher(name=__name__)
    def clear(self) -> None:
        '''Clears the Current Frame Cache'''

        self.mutex.lock()
        self.cache.clear()
        self.mutex.unlock()
        logger.debug("Frame Cache Cleared")


    @err_catcher(name=__name__)
    def getFrame(self, frameIdx: int) -> np.array:
        """
            Return numpy Array Frame.\n
            Gets Frame from Cache if Available, or Decode and Insert into Cache.
        """

        #   Return from Cache if Exists in Cache
        frame = self.cache.get(frameIdx)
        if frame is not None:
            return frame

        if not self.mediaFiles:
            return None
        
        return self._generateFrame(frameIdx)


    ##############################
    #######   INTERNAL    ########

    @err_catcher(name=__name__)
    def _onWorkerProgress(self, frameIdx, firstFrame=False):
        if firstFrame:
            self.firstFrameComplete.emit(frameIdx)
            self._firstFrameEmitted = True

        self.cacheUpdated.emit(frameIdx)

        if all(v is not None for v in self.cache.values()):
            self.isRunning = False
            logger.debug("Frame Cache Complete")
            self.cacheComplete.emit()

    
    @err_catcher(name=__name__)
    def _generateFrame(self, frameIdx):
        #   Image Sequence
        if self.isSeq:
            imgPath = self.mediaFiles[frameIdx]
            worker = ImageCacheWorker(
                self.core,
                imgPath,
                frameIdx,
                self.cache,
                self.mutex,
                self.pWidth,
                None,
            )
            #   Blocking Decode
            worker.run()

            self._onWorkerProgress(frameIdx, firstFrame=False)

            return self.cache.get(frameIdx)

        #   Video
        else:
            mediaPath = self.mediaFiles[0]
            try:
                container = av.open(mediaPath)
                stream = container.streams.video[0]

                #   Attempt Direct Seek if Possible (faster)
                try:
                    container.seek(frameIdx * stream.time_base.denominator // self.fps)
                except Exception:
                    #   Fallback full Decode
                    pass

                for idx, frame in enumerate(container.decode(stream)):
                    if idx == frameIdx:
                        #   Scale and Flip
                        src_w, src_h = frame.width, frame.height
                        scale = self.pWidth / float(src_w)
                        dst_w = self.pWidth
                        dst_h = max(1, int(round(src_h * scale)))

                        f2 = frame.reformat(width=dst_w, height=dst_h,
                                            format='rgba', interpolation='BILINEAR')
                        img = np.flipud(f2.to_ndarray())

                        self.mutex.lock()
                        self.cache[frameIdx] = img
                        self.mutex.unlock()
                        container.close()

                        self._onWorkerProgress(frameIdx, firstFrame=False)
                        return img
                container.close()

            except Exception as e:
                logger.warning(f"getFrame() failed for frame {frameIdx}: {e}")
                return None

        return None




############################################
#######     GL GPU Image Display     #######

class GLVideoDisplay(QOpenGLWidget):
    def __init__(self, player, core, parent=None):
        super().__init__(parent)
        self.player = player
        self.core = core
        self.frame = None
        self.texture_id = None
        self.program = None
        self.vao = None
        self.scale_w = 1.0
        self.scale_h = 1.0

        self.pixel_size = 20
        self.checker_color1 = (0.0, 0.0, 0.0) # black
        self.checker_color2 = (0.1, 0.1, 0.1) # grey

        self.inputSpace = "sRGB"
        self.display = "sRGB"
        self.view = "Standard"
        self.look = None
        self.luts = None

        self.config = ocio.GetCurrentConfig()
        self.processor = self.config.getProcessor("lin_srgb", "sRGB")
        self.gpu_proc = self.processor.getDefaultGPUProcessor()

        #   Add RCL Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.player.rclPreview)


    #######################
    ######    API   #######

    #   Updates OCIO Transforms
    @err_catcher(name=__name__)
    def setBackground(self, pixel_size:int = 20,
                      checker_color1:tuple = (0.0, 0.0, 0.0),
                      checker_color2:tuple = (0.1, 0.1, 0.1)
                      ) -> bool:
        '''Updates Checkboard Background'''

        try:
            self.pixel_size = pixel_size
            self.checker_color1 = checker_color1
            self.checker_color2 = checker_color2

            #   Update Checksize Calc
            self.setCheckerPixelSize()

            #   Refresh Viewer
            self.update()

            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Background: {e}")
            return False


    #   Updates OCIO Transforms
    @err_catcher(name=__name__)
    def setOcioTransforms(self,
                          inputSpace: str,
                          display: str,
                          view: str,
                          look: str = None,
                          luts: list = None
                          ) -> bool:
        '''Updates OCIO Transforms for Display'''

        try:
            config = ocio.GetCurrentConfig()

            #   Fallback Defaults
            fallback_space = config.getColorSpaceNames()[0] if config.getColorSpaceNames() else "sRGB"
            fallback_display = config.getDefaultDisplay()
            fallback_view = config.getDefaultView(fallback_display)

            errors = []

            ##   Validate Passed Transforms Exist in Config

            #   Check Input Colorspace
            if inputSpace not in config.getColorSpaceNames():
                errStr = f"Invalid OCIO Input ColorSpace '{inputSpace}', falling back to '{fallback_space}'"
                logger.warning(errStr)
                errors.append(errStr)
                inputSpace = fallback_space

            #   Check Display
            if display not in config.getDisplays():
                errStr = f"Invalid OCIO Display '{display}', falling back to '{fallback_display}'"
                logger.warning(errStr)
                errors.append(errStr)
                display = fallback_display

            #   Check View
            if view not in config.getViews(display):
                errStr = f"Invalid OCIO View '{view}' for display '{display}', falling back to '{fallback_view}'"
                logger.warning(errStr)
                errors.append(errStr)
                view = fallback_view

            #   Check LUT File
            validLuts = []
            if luts:
                for lut in luts:
                    #   Check if LUT Path Exists
                    if not os.path.isfile(lut):
                        errStr = f"LUT is not a Valid File.  Ignoring LUT"
                        logger.warning(errStr)
                        errors.append(errStr)
                    
                    #   Test if LUT is Valid
                    else:
                        try:
                            if self.createLutTransform(lut):
                                validLuts.append(lut)
                            else:
                                raise Exception

                        except Exception as e:
                            errStr = f"Invalid LUT file '{lut}': {e}.\n\nIgnoring LUT."
                            # logger.warning(errStr)
                            errors.append(errStr)
                            lut = None

            #   Check Look
            if look and look not in config.getLookNames():
                errStr = f"Invalid OCIO Look '{look}', ignoring."
                logger.warning(errStr)
                errors.append(errStr)
                look = None

            #   Display Errors in the UI
            if errors:
                title = "OCIO PRESET ERROR"
                text = "There are Errors with the Selected OCIO Transforms:\n\n"
                text += "\n".join(f"- {err}\n" for err in errors)
                self.core.popup(text=text, title=title)

            self.inputSpace = inputSpace
            self.display = display
            self.view = view
            self.look = look
            self.luts = validLuts

            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set OCIO Transforms: {e}")
            #   Fallback to Defaults
            self.inputSpace = "sRGB"
            self.display = "sRGB"
            self.view = "Standard"
            self.luts = []
            self.look = None
            return False
        

    #   Displays Frame Numpy Array in Viewer
    @err_catcher(name=__name__)
    def displayFrame(self, frameIdx: int, frame: np.ndarray) -> bool:
        '''Displays Frame in Viwer'''

        try:
            self.frameIdx = frameIdx
            self.frame = frame
            self.update()
            return True
        
        except Exception as e:
            logger.warning(f"ERROR: Failed to Set Image Frame: {e}")
            return False


    ###########################
    ######   INTERNAL   #######

    #   Calc Checkboard Squares based on Pixels
    @err_catcher(name=__name__)
    def setCheckerPixelSize(self):
        self.checker_count = max(1, self.width() / max(1, self.pixel_size))


    #   Create the GL Shaders
    @err_catcher(name=__name__)
    def _compileShaderProgram(self, vert_src, frag_src):
        #   Compile the Shaders
        vs = self.compileShader(vert_src, GL_VERTEX_SHADER)
        fs = self.compileShader(frag_src, GL_FRAGMENT_SHADER)

        #   Create a GL Progrm and Add Shaders
        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        if not glGetProgramiv(program, GL_LINK_STATUS):
            err = glGetProgramInfoLog(program).decode()
            logger.warning(f"ERROR: GLSL link error: {err}")
            glDeleteProgram(program)
            return None
             
        return program
    

    #   Compile GL Shader
    @err_catcher(name=__name__)
    def compileShader(self, src, shader_type):
        #   Create Empty Shader
        shader = glCreateShader(shader_type)
        #   Compile Using Shader Code
        glShaderSource(shader, src)
        glCompileShader(shader)

        if not glGetShaderiv(shader, GL_COMPILE_STATUS):
            err = glGetShaderInfoLog(shader).decode()
            logger.warning(f"ERROR: GLSL compile: [{shader_type}]: {err}")
            glDeleteShader(shader)
            return None
        
        return shader
    

    #   Create GL Context and Generate Textures/Shaders
    @err_catcher(name=__name__)
    def initializeGL(self):
        #   Generate Texture ID
        self.texture_id = glGenTextures(1)

        #   Vertex Shader Code for both Image and Checkerboard
        vertex_shader_src = """
        #version 330
        layout(location = 0) in vec2 position;
        layout(location = 1) in vec2 texcoord;
        out vec2 vTexCoord;
        uniform vec2 uScale;
        void main() {
            vTexCoord = texcoord;
            gl_Position = vec4(position * uScale, 0.0, 1.0);
        }
        """

        #   Shader Code for Image
        fragment_shader_src = """
        #version 330
        uniform sampler2D uTex;
        in vec2 vTexCoord;
        out vec4 fragColor;
        void main() {
            fragColor = texture(uTex, vTexCoord);
        }
        """

        #    Shader Code for Checkboard
        checker_frag_src = """
        #version 330
        in vec2 vTexCoord;
        out vec4 fragColor;

        uniform float uCheckerCount;
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        uniform float uAspect; // width / height

        void main() {
            float cx = floor(vTexCoord.x * uCheckerCount * uAspect);
            float cy = floor(vTexCoord.y * uCheckerCount);

            if (mod(cx + cy, 2.0) < 1.0)
                fragColor = vec4(uColor1, 1.0);
            else
                fragColor = vec4(uColor2, 1.0);
        }
        """

        #   Compile/link Programs
        self.program_image = self._compileShaderProgram(vertex_shader_src, fragment_shader_src)
        self.program_checker = self._compileShaderProgram(vertex_shader_src, checker_frag_src)

        if not self.program_image or not self.program_checker:
            logger.error("ERROR: Failed to Compile/Link Shaders")
            self.program_image = None

        #   Setup Quad Geo Buffers/VAO (uses fixed locations 0-1)
        self._setupQuad()

        #   Enable Alpha Blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


    #   Create GL Display Qaud
    @err_catcher(name=__name__)
    def _setupQuad(self):
        #   Sets Verts for Quad
        verts = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 1.0,
        ], dtype=np.float32)

        #   Create Two Tris for the Quad
        indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

        #   Generate GL Objects
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.ebo = glGenBuffers(1)

        #   Bind VAO and Upload Vertex Data
        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)

        #   Upload EBO
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        #   Set Vertex Pointers
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))

        #   Unbind VAO
        glBindVertexArray(0)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)  # bypass EBO
        glBindVertexArray(0)


    #   Resize GL Window and Recalc Checkboard
    @err_catcher(name=__name__)
    def resizeGL(self, w, h):
        glViewport(0, 0, max(1, w), max(1, h))
        if self.frame is not None:
            vid_h, vid_w = self.frame.shape[:2]
            img_aspect = vid_w / float(vid_h) if vid_h != 0 else 1.0
            widget_aspect = w / float(h) if h != 0 else 1.0

            if widget_aspect > img_aspect:
                self.scale_w = img_aspect / widget_aspect
                self.scale_h = 1.0
            else:
                self.scale_w = 1.0
                self.scale_h = widget_aspect / img_aspect
        else:
            self.scale_w = 1.0
            self.scale_h = 1.0

        #   Recalc Checkerboard Size
        self.setCheckerPixelSize()


    @err_catcher(name=__name__)
    def createLutTransform(self, lut_path: str):
        if not os.path.isfile(lut_path):
            logger.warning(f"LUT path not found: {lut_path}")
            return None

        try:
            lutTransform = ocio.FileTransform(
                lut_path,
                interpolation=ocio.Interpolation.INTERP_LINEAR,
                direction=ocio.TransformDirection.TRANSFORM_DIR_FORWARD
            )

            # Quick validation by trying to create a temporary processor
            ocio.GetCurrentConfig().getProcessor(lutTransform)
            return lutTransform

        except Exception as e:
            logger.warning(f"Invalid LUT file '{lut_path}': {e}")
            return None


    #   Apply OCIO Transforms in CPU
    @err_catcher(name=__name__)
    def applyOCIO_CPU(self,
                      img_np,
                      input_space="sRGB",
                      display="sRGB",
                      view="Standard",
                      luts=None):
        
        if img_np is None or not isinstance(img_np, np.ndarray) or img_np.size == 0:
            return img_np

        #   Ensure 3-channel RGB
        if img_np.ndim == 2 or img_np.shape[-1] == 1:
            img_np = np.repeat(img_np, 3, axis=-1)
        elif img_np.shape[-1] > 3:
            img_np = img_np[..., :3]

        #   Convert to Float32 Normalized
        img_np_f32 = img_np.astype(np.float32)
        if img_np_f32.max() > 1.0:
            img_np_f32 /= 255.0

        h, w, c = img_np_f32.shape

        #   Get and Set Transforms
        config = ocio.GetCurrentConfig()

        #   Transform Fallbacks
        space_name = input_space or "sRGB"
        display_name = display or config.getDefaultDisplay()
        view_name = view or config.getDefaultView(display_name)

        #   Create Transform Group to Hold All Transforms
        final_transform = ocio.GroupTransform()

        #   Build Look Transform if Exists
        if self.look:
            look_transform = ocio.LookTransform()
            look_transform.setSrc(space_name)
            look_transform.setDst(space_name)
            look_transform.setLooks(self.look)
            final_transform.appendTransform(look_transform)

        #   Build DisplayViewTransform
        disp_view_transform = ocio.DisplayViewTransform(
            src=space_name,
            display=display_name,
            view=view_name,
            looksBypass=False,
            dataBypass=True
        )

        final_transform.appendTransform(disp_view_transform)

        #   Apply LUT if Applicable
        if luts:
            for lut_path in luts:
                lutTransform = self.createLutTransform(lut_path)
                if lutTransform is not None:
                    final_transform.appendTransform(lutTransform)
                else:
                    logger.warning(f"Skipping invalid LUT: {lut_path}")

        #   Create CPU Processor
        processor = config.getProcessor(final_transform)
        cpu_proc = processor.getDefaultCPUProcessor()

        #   Apply Transform
        img_desc = ocio.PackedImageDesc(img_np_f32, w, h, 3)
        cpu_proc.apply(img_desc)

        img_np_out = np.clip(img_np_f32 * 255.0, 0, 255).astype(np.uint8)

        return img_np_out


    #   Paint the Image to the GL Window
    @err_catcher(name=__name__)
    def paintGL(self):
        #   Clear Window
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)

        #   Bind VAO Quad
        glBindVertexArray(self.vao)

        ###   Draw Checkerboard
        glUseProgram(self.program_checker)

        #   Get Variables
        checkerLoc = glGetUniformLocation(self.program_checker, "uCheckerCount")
        if checkerLoc != -1:
            glUniform1f(checkerLoc, self.checker_count)

        color1Loc = glGetUniformLocation(self.program_checker, "uColor1")
        color2Loc = glGetUniformLocation(self.program_checker, "uColor2")
        if color1Loc != -1:
            glUniform3f(color1Loc, *self.checker_color1)
        if color2Loc != -1:
            glUniform3f(color2Loc, *self.checker_color2)

        scaleLoc = glGetUniformLocation(self.program_checker, "uScale")
        if scaleLoc != -1:
            glUniform2f(scaleLoc, 1.0, 1.0)

        #   Calculate Aspect Ratio
        aspect = self.width() / max(1, self.height())

        aspectLoc = glGetUniformLocation(self.program_checker, "uAspect")
        if aspectLoc != -1:
            glUniform1f(aspectLoc, aspect)

        #   Paint Checkboard Quad
        glDrawArrays(GL_TRIANGLE_FAN, 0, 4)

        ### Draw Image
        if self.frame is not None and self.program_image:
            img_data = np.ascontiguousarray(self.frame)

            #   Convert Float32 to UINT8 if Needed
            if img_data.dtype in (np.float32, np.float64):
                img_data = np.clip(img_data * 255.0, 0, 255).astype(np.uint8)

            #   Apply OCIO CPU Transform on Image
            try:
                src = img_data

                #   RGBA Image
                if src.ndim == 3 and src.shape[2] == 4:
                    #   Strip Alpha if Applicable
                    rgb = src[..., :3].copy()
                    alpha = src[..., 3:].copy()

                    #   Apply OCIO
                    rgb_out = self.applyOCIO_CPU(rgb, self.inputSpace, self.display, self.view, self.luts)

                    if rgb_out.dtype != np.uint8:
                        rgb_out = rgb_out.astype(np.uint8)

                    #   Re-attach Alpha to RGB
                    img_data = np.concatenate([rgb_out, alpha], axis=-1)

                #   RGB Image
                else:
                    #   Apply OCIO
                    rgb_out = self.applyOCIO_CPU(src, self.inputSpace, self.display, self.view, self.luts)

                    if rgb_out.ndim == 2:
                        rgb_out = np.repeat(rgb_out[..., None], 3, axis=2)

                    if rgb_out.dtype != np.uint8:
                        rgb_out = rgb_out.astype(np.uint8)

                    img_data = rgb_out

            except Exception as e:
                logger.warning(f"ERROR: Unable to Apply OCIO transform: {e}")
                img_data = self.frame

            #   Prepare Texture Upload
            h, w = img_data.shape[:2]
            channels = img_data.shape[2] if img_data.ndim == 3 else 1

            glBindTexture(GL_TEXTURE_2D, self.texture_id)

            if channels == 4:
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            else:
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
                glBlendFunc(GL_ONE, GL_ZERO)

            #   Set Filtering
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

            #   Draw the Image Quad
            glUseProgram(self.program_image)

            #   Set Scale
            scaleLoc = glGetUniformLocation(self.program_image, "uScale")
            if scaleLoc != -1:
                glUniform2f(scaleLoc, self.scale_w, self.scale_h)

            #   Bind Texture to Sampler
            texLoc = glGetUniformLocation(self.program_image, "uTex")
            if texLoc != -1:
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.texture_id)
                glUniform1i(texLoc, 0)

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        #   Unbiond VAO
        glBindVertexArray(0)



############################################
#######     PLAYER SETTINGS UI      ########
    

class PlayerConfigPopup(QDialog):
    def __init__(self, player, core):
        super().__init__()

        self.player = player
        self.core = core

        #   Defaults
        self.cacheThreads = 4
        self.pixel_size = 20
        self.checker_color1 = (0.0, 0.0, 0.0)
        self.checker_color2 = (0.1, 0.1, 0.1)

        self.result = None
        self.setWindowTitle("Media Player Configuration")

        self.loadUI()
        self.connectEvents()


    @err_catcher(name=__name__)
    def loadUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width   = screen_geometry.width() // 4
        height  = screen_geometry.height() // 3
        x_pos   = (screen_geometry.width() - width) // 2
        y_pos   = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        lo_main = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)


        ##   PERFORMACE
        gb_performance = QGroupBox("Performace")

        #   Layout for Margins
        lo_margins = QVBoxLayout(gb_performance)

        #   Inner Layout
        checkContainer = QWidget()
        lo_performace = QVBoxLayout(checkContainer)
        lo_performace.setContentsMargins(20, 5, 20, 5)

        #   Cache Threads
        lo_threads = QHBoxLayout()
        l_threads = QLabel("Frame Cache Threads")
        self.sp_threads = QSpinBox()
        self.sp_threads.setRange(1, 50)
        self.sp_threads.setValue(4)

        lo_threads.addWidget(l_threads)
        lo_threads.addStretch()
        lo_threads.addWidget(self.sp_threads)
        lo_performace.addLayout(lo_threads)

        lo_margins.addWidget(checkContainer)
        scroll_layout.addWidget(gb_performance)


        ##  Checker Background
        gb_checkerBG = QGroupBox("Checker Background")

        #   Layout for Margins
        lo_margins = QVBoxLayout(gb_checkerBG)

        #   Inner Layout
        checkContainer = QWidget()
        lo_checker = QVBoxLayout(checkContainer)
        lo_checker.setContentsMargins(20, 5, 20, 5)

        # Checker Size
        lo_checkSize = QHBoxLayout()
        l_checkSize = QLabel("Checker Size (pix)")
        self.sp_checkSize = QSpinBox()
        self.sp_checkSize.setRange(1, 100)
        self.sp_checkSize.setValue(20)

        lo_checkSize.addWidget(l_checkSize)
        lo_checkSize.addStretch()
        lo_checkSize.addWidget(self.sp_checkSize)
        lo_checker.addLayout(lo_checkSize)

        #   Color 1
        row1, self._swatch_checker_color1 = self.makeColorRow(
            "Checker Color 1", (0, 0, 0), lambda c: setattr(self, "checker_color1", c)
        )
        lo_checker.addLayout(row1)

        #   Color 2
        row2, self._swatch_checker_color2 = self.makeColorRow(
            "Checker Color 2", (25, 25, 25), lambda c: setattr(self, "checker_color2", c)
        )
        lo_checker.addLayout(row2)

        lo_margins.addWidget(checkContainer)
        scroll_layout.addWidget(gb_checkerBG)


        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        # Bottom Buttons
        lo_buttons = QHBoxLayout()

        self.b_save = QPushButton("Save")
        self.b_close = QPushButton("Close")

        lo_buttons.addStretch()
        lo_buttons.addWidget(self.b_save)
        lo_buttons.addWidget(self.b_close)

        lo_main.addLayout(lo_buttons)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_save.clicked.connect(self.onSaveClicked)
        self.b_close.clicked.connect(self.onCloseClicked)


    @err_catcher(name=__name__)
    def loadSettings(self, data):
        self.sp_threads.setValue(data.get("cacheThreads", 4))
        self.sp_checkSize.setValue(data.get("check_size", 20))

        #   Convert Lists to Tuples
        color1 = tuple(data.get("check_color1", (0.0, 0.0, 0.0)))
        color2 = tuple(data.get("check_color2", (0.1, 0.1, 0.1)))

        #   Update Vars
        self.checker_color1 = color1
        self.checker_color2 = color2

        #   Update Swatches
        self.setSwatchColor(self._swatch_checker_color1, color1)
        self.setSwatchColor(self._swatch_checker_color2, color2)


    @err_catcher(name=__name__)
    def getSettings(self):
        return {
            "cacheThreads": self.sp_threads.value(),
            "check_size": self.sp_checkSize.value(),
            "check_color1": self.checker_color1,
            "check_color2": self.checker_color2,
        }


    @err_catcher(name=__name__)
    def makeColorRow(self, label_text, default_color, callback=None):
        layout = QHBoxLayout()

        #   Name Label
        lbl = QLabel(label_text)

        #   Swatch (QFrame with Background Color)
        swatch = QFrame()
        swatch.setObjectName("checkerSwatch")

        swatch.setFixedSize(40, 25)
        swatch.setFrameShape(QFrame.Box)
        swatch.setFrameShadow(QFrame.Plain)
        swatch.setStyleSheet(f"""
            QFrame#checkerSwatch {{
                background-color: rgb{default_color};
                border: 2px solid #454545;
                border-radius: 2px;
            }}
        """)
        swatch.setProperty("color", tuple(c/255 for c in default_color))

        #   Button
        btn = QPushButton("Choose...")
        btn.clicked.connect(lambda: self.pickColor(swatch, callback))

        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(swatch)
        layout.addWidget(btn)

        return layout, swatch


    @err_catcher(name=__name__)
    def pickColor(self, swatch, callback=None):
        initial = swatch.palette().window().color()
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            r, g, b, _ = color.getRgb()
            swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #444;")
            normalized = (round(r/255,3), round(g/255,3), round(b/255,3))
            swatch.setProperty("color", normalized)
            if callback:
                callback(normalized)


    # Get current color from swatch
    @err_catcher(name=__name__)
    def getSwatchColor(self, swatch):
        return swatch.property("color")  # returns (r, g, b) in 0–1 range


    # Set swatch color programmatically
    @err_catcher(name=__name__)
    def setSwatchColor(self, swatch, rgb):
        """rgb can be (0–1 floats) or (0–255 ints)."""
        if all(0 <= c <= 1 for c in rgb):
            r, g, b = [int(c*255) for c in rgb]
            # Clamp floats to 3 decimal places
            normalized = tuple(round(c, 3) for c in rgb)
        else:
            r, g, b = rgb
            normalized = tuple(round(c/255, 3) for c in rgb)

        swatch.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid #444;")
        swatch.setProperty("color", normalized)





    @err_catcher(name=__name__)
    def onSaveClicked(self):
        self.result = self.getSettings()
        self.accept()


    @err_catcher(name=__name__)
    def onCloseClicked(self):
        self.reject()

