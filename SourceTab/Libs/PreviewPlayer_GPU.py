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
import subprocess
import logging
import traceback
import shutil
from functools import partial
import threading
from collections import OrderedDict
import math
import time

from PIL import Image
import numpy as np
from OpenGL.GL import *
import av


import PyOpenColorIO as ocio                        #   TODO - Handle MediaExtension




from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *



from PrismUtils.Decorators import err_catcher

import SourceTab_Utils as Utils
from SourceTab_Models import FileTileMimeData
from WorkerThreads import FileInfoWorker
from PopupWindows import OcioConfigPopup


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

        self.tempOCIOLoad()                         #   TESTING

        self.resetImage()

        self.enableControls(False)


        # Connect signal to GL widget
        self.frameReady.connect(self.displayWindow.setFrame)
        self.PreviewCache.firstFrameComplete.connect(self.onFirstFrameReady)


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



    @err_catcher(name=__name__)
    def setupUi(self):
        self.lo_preview_main = QVBoxLayout(self)
        self.lo_preview_main.setContentsMargins(0, 0, 0, 0)
        self.l_info = QLabel(self)
        self.l_info.setText("")
        self.l_info.setObjectName("l_info")
        self.lo_preview_main.addWidget(self.l_info)

        #   View LUT
        self.container_viewLut = QWidget()
        self.lo_viewLut = QHBoxLayout(self.container_viewLut)
        self.l_viewLut = QLabel("View Lut Preset:")
        self.cb_viewLut = QComboBox()
        self.lo_viewLut.addWidget(self.l_viewLut)
        self.lo_viewLut.addWidget(self.cb_viewLut)
        self.lo_preview_main.addWidget(self.container_viewLut)

        #   Viewer Window
        self.displayWindow = GLVideoDisplay(self)
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
        # self.displayWindow.clickEvent = self.displayWindow.mouseReleaseEvent
        # self.displayWindow.mouseReleaseEvent = self.previewClk
        # self.displayWindow.resizeEventOrig = self.displayWindow.resizeEvent
        # self.displayWindow.resizeEvent = self.previewResizeEvent
        # self.displayWindow.customContextMenuRequested.connect(self.rclPreview)

        self.sl_previewImage.valueChanged.connect(self.sliderChanged)
        # self.sl_previewImage.sliderPressed.connect(self.sliderClk)
        # self.sl_previewImage.sliderReleased.connect(self.sliderRls)
        # self.sl_previewImage.origMousePressEvent = self.sl_previewImage.mousePressEvent
        # self.sl_previewImage.mousePressEvent = self.sliderDrag
        # self.sp_current.valueChanged.connect(self.onCurrentChanged)

        self.sp_current.editingFinished.connect(lambda: self.loadFrame(self.sp_current.value()))

        self.b_first.clicked.connect(self.onFirstClicked)
        self.b_prev.clicked.connect(self.onPrevClicked)
        self.b_play.clicked.connect(self.onPlayClicked)
        self.b_next.clicked.connect(self.onNextClicked)
        self.b_last.clicked.connect(self.onLastClicked)

        self.PreviewCache.cacheUpdated.connect(self.updateCacheSlider)
        self.cb_viewLut.currentIndexChanged.connect(self.onLutChanged)


    def tempOCIOLoad(self):
        self.cb_viewLut.addItems(["sRGB", "Linear", "AgX", "ACEScg", "zCam", "ARRI LogC4", "ARRI LogC3"])





    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state):
        self.previewEnabled = state
        self.displayWindow.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)


    @err_catcher(name=__name__)
    def previewResizeEvent(self, event):
        self.displayWindow.resizeEventOrig(event)
        self.adjustPreviewAspect()

        text = self.l_info.toolTip()
        if not text:
            text = self.l_info.text()

        self.setInfoText(text)


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
            self.displayWindow.resize(window_width, target_height)

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
        if not self.PreviewCache.cache and not reset:
            return
        
        if reset:
            progress_ratio = 0
            logger.debug("Reset Cache Slider")

        else:
            cached_count = sum(1 for f in self.PreviewCache.cache.values() if f is not None)
            total_frames = len(self.PreviewCache.cache)
            progress_ratio = cached_count / total_frames if total_frames else 0
            logger.debug(f"Cache progress: {cached_count}/{total_frames} ({progress_ratio*100:.1f}%)")

        total_segments = 100
        stops = []
        for i in range(total_segments + 1):
            ratio = i / total_segments
            color = "#465A78" if ratio <= progress_ratio else "transparent"
            stops.append(f"stop:{ratio} {color}")

        gradient_str = ", ".join(stops)

        style = f"""
        QSlider::groove:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                {gradient_str}
            );
        }}
        """

        self.sl_previewImage.setStyleSheet(style)


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
        self.displayWindow.setFrame(0, self.makeBlackFrame())
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
        if not self.PreviewCache.cache:
            return

        self.sl_previewImage.blockSignals(True)
        self.sl_previewImage.setValue(frame)
        self.sl_previewImage.blockSignals(False)

        if self.sp_current.value() != (self.pstart + frame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + frame))
            self.sp_current.blockSignals(False)


    @err_catcher(name=__name__)
    def onLutChanged(self, idx):
        self.configureOCIO()
        self.reloadCurrentFrame()


    @err_catcher(name=__name__)
    def setTimelinePaused(self, paused: bool):
        """Pause or resume playback, update icon and playback timer."""

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

        if not self.PreviewCache.cache:
            return

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
        frame = self.PreviewCache.cache.get(frameIdx)
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
        self.setCurrentFrame(self.currentFrameIdx - 1, manual=True)


    @err_catcher(name=__name__)
    def onPlayClicked(self):
        if not self.mediaFiles or not self.PreviewCache.cache:
            return

        if self.isPlaying():
            self.setTimelinePaused(True)
        else:
            fps = getattr(self, "fps", 24) or 24
            self._playInterval = 1000.0 / float(fps)
            self.setTimelinePaused(False)


    @err_catcher(name=__name__)
    def _playNextFrame(self):
        if not self.PreviewCache.cache:
            self.playTimer.stop()
            return

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
        self.setCurrentFrame(self.currentFrameIdx + 1, manual=True)


    @err_catcher(name=__name__)
    def onLastClicked(self):
        self.setCurrentFrame(len(self.PreviewCache.cache) - 1, manual=True, reset=True)


    @err_catcher(name=__name__)
    def sliderChanged(self, frameIdx):
        if not self.mediaFiles or not self.PreviewCache.cache:
            return

        was_playing = self.isPlaying()
        if was_playing:
            self.playTimer.stop()

        self.setCurrentFrame(frameIdx, manual=True, reset=True)

        if was_playing:
            self._playStartTime.restart()
            self.playTimer.start(10)



    @err_catcher(name=__name__)
    def sliderDrag(self, event):
        custEvent = QMouseEvent(
            QEvent.MouseButtonPress,
            event.pos(),
            Qt.MidButton,
            Qt.MidButton,
            Qt.NoModifier,
        )
        self.sl_previewImage.origMousePressEvent(custEvent)


    @err_catcher(name=__name__)
    def sliderClk(self):
        self.slStop = False
        if self.isPlaying():
            self.slStop = True
            self.playTimer.stop()


    @err_catcher(name=__name__)
    def sliderRls(self):
        if self.slStop:
            self._playStartTime.restart()
            self.playTimer.start(10)




    @err_catcher(name=__name__)
    def previewClk(self, event):
        # if (len(self.mediaFiles) > 1 or self.pduration > 1) and event.button() == Qt.LeftButton:
        #     if self.previewTimeline.state() == QTimeLine.Paused:
        #         self.setTimelinePaused(False)

        #     else:
        #         if self.previewTimeline.state() == QTimeLine.Running:
        #             self.setTimelinePaused(True)

        self.displayWindow.clickEvent(event)



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

        #   Configure OCIO                                                  #   TODO
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

            #   Build Dict for Cacheing
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

            #   Start the Caching                                   #   TODO - ADD TOGGLE TO START/STOP/ENABLE
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

        #   Get File Data
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

    def onFirstFrameReady(self, frameIdx: int):
        self.currentFrameIdx = frameIdx
        self.sl_previewImage.setValue(0)
        self.sp_current.setValue(frameIdx)
        
        self.loadFrame(frameIdx)


    @err_catcher(name=__name__)
    def loadFrame(self, frameIdx):
        if not self.PreviewCache.cache:
            logger.debug("No frames in cache yet")
            return

        frameIdx = max(0, min(frameIdx, len(self.PreviewCache.cache)-1))
        frame = self.PreviewCache.cache.get(frameIdx)

        if frame is not None:
            self.frameReady.emit(frameIdx, frame)




    @err_catcher(name=__name__)
    def configureOCIO(self, input_space="sRGB", display="sRGB", view="Standard", lut_path=None):                #   TESTING

        match self.cb_viewLut.currentText():
            case "sRGB":
                input_space = "sRGB"
                display = "sRGB"
                view = "Standard"

            case "Linear":
                input_space = "Linear Rec.709"
                display = "sRGB"
                view = "Standard"

            case "AgX":
                input_space = "Linear Rec.709"
                display = "sRGB"
                view = "AgX"

            case "ACEScg":
                input_space = "Linear ACES - AP0"
                display = "sRGB"
                view = "ACES"

            case "zCam":
                input_space = "zCam zLog2 Rec.1886"
                display = "sRGB"
                view = "Standard"

            case "ARRI LogC4":
                input_space = "ARRI LogC4"
                display = "Rec.1886"
                view = "ARRI ALF2"

            case "ARRI LogC3":
                input_space = "ARRI LogC3"
                display = "Rec.1886"
                view = "ARRI ALF2"

                


        # self.printOcioInfo()                                  #   TESTING

        # input_space = "sRGB"
        # input_space = "Linear Rec.709"
        # input_space = "Linear ACES - AP0"
        # input_space = "ARRI LogC4"
        # input_space = "zCam zLog2 Rec.1886"

        # display = "sRGB"
        # display = "Rec.1886"

        # view = "Standard"
        # view = "AgX"
        # view = "Filmic"
        # view = "ACES"

        lut_path = None

        self.displayWindow.setOcioTransforms(
            inputSpace=input_space,
            display=display,
            view=view,
            lut=lut_path
        )





    def printOcioInfo(self):                                                 #   TESTING
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

            print("\n\n\n")

        except Exception as e:
            print(f"[OCIO] Failed to query config: {e}")





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

        #   External Player
        playMenu = QMenu("Play in", self)
        iconPath = os.path.join(self.iconPath, "play.png")
        icon = self.core.media.getColoredIcon(iconPath)
        playMenu.setIcon(icon)

        if self.externalMediaPlayers is not None:
            for player in self.externalMediaPlayers:
                funct = lambda x=None, name=player.get("name", ""): self.compare(name)
                Utils.createMenuAction(player.get("name", ""), sc, playMenu, self, funct)

        Utils.createMenuAction("Default", sc, playMenu, self, lambda: self.compare(prog="default"))


        iconPath = os.path.join(self.iconPath, "refresh.png")
        icon = self.core.media.getColoredIcon(iconPath)
        Utils.createMenuAction("Reload Cache", sc, rcmenu, self, self.reloadCache, icon=icon)

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

        Utils.createMenuAction("Edit OCIO Presets", sc, rcmenu, self, self.editOcioPresets)

        return rcmenu


    @err_catcher(name=__name__)
    def reloadCache(self):
        self.resetImage()
        self.configureOCIO()
        self.updatePreview(self.mediaFiles)



    @err_catcher(name=__name__)
    def clearCurrentThumbnails(self):
        if not self.mediaFiles:
            return

        thumbdir = os.path.dirname(self.core.media.getThumbnailPath(self.mediaFiles[0]))
        if not os.path.exists(thumbdir):
            return

        try:
            shutil.rmtree(thumbdir)
        except Exception as e:
            logger.warning("Failed to remove thumbnail: %s" % e)


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
    def editOcioPresets(self):
        data = {}
        ocioPresetsWindow = OcioConfigPopup(self, self.core, data)

        ocioPresetsWindow.exec()


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


    def stop(self) -> None:
        '''Stop Frame Cache Worker'''
        self._running = False


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
                                        format='rgb24', interpolation='BILINEAR')
                    img = f2.to_ndarray()

                except Exception:
                    img = frame.to_ndarray(format='rgb24')
                    if img.shape[1] != dst_w or img.shape[0] != dst_h:
                        img = np.array(Image.fromarray(img).resize((dst_w, dst_h), Image.BILINEAR))

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
            logger.warning(f"ERROR: Unable to Cache Video File: {e}")



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


    def stop(self) -> None:
        '''Stop Frame Cache Worker'''
        self._running = False


    def getfirstColorLayer(self, layers):
        for name in COLORNAMES:
            for layer in layers:
                if name.lower() in layer.lower():
                    return layer
        return None


    def run(self):
        '''Start Image Cache Worker'''

        try:
            if not self._running:
                return
            if not os.path.exists(self.imgPath):
                return

            #   Get Layer Names from Prism
            layers = self.core.media.getLayersFromFile(self.imgPath)

            #   Find the First Color/Beauty Layer
            selected_layer = self.getfirstColorLayer(layers)

            inp = self.oiio.ImageInput.open(self.imgPath)
            if not inp:
                return

            spec = inp.spec()
            channels = spec.channelnames

            img_np = None

            #   If Beauty/Color Layer Found
            if selected_layer:
                #   Find RGB Channels for the Selected Layer
                rgb_channels = [c for c in channels if selected_layer in c and not c.endswith(".A")]
                if len(rgb_channels) == 3:
                    chbegin = channels.index(rgb_channels[0])
                    chend = channels.index(rgb_channels[-1]) + 1
                    img = inp.read_image(0, 0, chbegin, chend, self.oiio.UINT8)
                    img_np = np.array(img).reshape(spec.height, spec.width, 3)

            #   Fallback
            if img_np is None:
                img = inp.read_image(format=self.oiio.UINT8)
                img_np = np.array(img).reshape(spec.height, spec.width, spec.nchannels)

                #   If Single Channel, Repeat to Make 3 Channel
                if img_np.shape[-1] == 1:
                    img_np = np.repeat(img_np, 3, axis=-1)

                #   Fallback to First 3 Channels
                else:
                    img_np = img_np[..., :3]

            inp.close()

            #   Resize
            src_w, src_h = spec.width, spec.height
            scale = self.pWidth / float(src_w)
            dst_w = self.pWidth
            dst_h = max(1, int(round(src_h * scale)))
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
            logger.warning(f"ERROR: Unable to Cache Image: {e}")


            
class FrameCacheManager(QObject):
    cacheUpdated = Signal(int)
    cacheComplete = Signal()
    firstFrameComplete = Signal(int)


    def __init__(self, core, pWidth=400):
        super().__init__()
        self.core = core
        self.mediaFiles = []
        self.cache = {}
        self.threadpool = QThreadPool.globalInstance()
        self.mutex = QMutex()
        self.worker = None
        self.pWidth = int(pWidth)
        self.total_frames = 0
        self._firstFrameEmitted = False

        # self.threadpool.setMaxThreadCount(8)                         #   TODO - Look at adding Max Threads to Settings   
        # max_threads = self.threadpool.maxThreadCount()
        # print(f"***  max_threads:  {max_threads}")								#	TESTING


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


    def start(self) -> None:
        '''Starts the Frame Caching'''

        if not self.mediaFiles:
            return
        
        logger.debug("Frame Caching Started")

        #   Record Caching Start Time
        self._cacheStartTime = time.time()

        #   Image Sequences
        if self.isSeq:
            #   Creates Frame Cache Dict with None's for Each Frame
            self.totalFrames = len(self.mediaFiles)
            self.cache = {i: None for i in range(self.totalFrames)}

            #   Launch Worker per Sequence Image
            for frame_idx, imgPath in enumerate(self.mediaFiles):
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
                self.threadpool.start(worker)

        #   Non-Sequences
        else:
            mediaPath = self.mediaFiles[0]

            #   Get Codec and Frame Count
            container = av.open(mediaPath)
            stream = container.streams.video[0]
            self.totalFrames = stream.frames if stream.frames else sum(1 for _ in container.decode(stream))

            if not self.codec:
                self.codec = stream.codec_context.name.lower()

            container.close()

            #   Creates Frame Cache Dict with None's for Each Frame
            self.cache = {i: None for i in range(self.totalFrames)}

            #   Launch Worker Instance
            self.worker = VideoCacheWorker(
                self.core,
                mediaPath,
                self.cache,
                self.mutex,
                self.pWidth,
                self._onWorkerProgress,
            )
            self.worker.setAutoDelete(True)
            self.threadpool.start(self.worker)


    def _onWorkerProgress(self, frameIdx, firstFrame=False):
        if firstFrame:
            self.firstFrameComplete.emit(frameIdx)
            self._firstFrameEmitted = True

        self.cacheUpdated.emit(frameIdx)

        if all(v is not None for v in self.cache.values()):
            elapsed = time.time() - self._cacheStartTime
            logger.debug(f"Frame Cache Complete in {elapsed:.2f} seconds")
            self.cacheComplete.emit()


    def stop(self) -> None:
        '''Stops the Frame Cache Worker'''
        if self.worker:
            self.worker.stop()

        self.worker = None
        logger.debug("Frame Cache Stopped")


    def clear(self) -> None:
        '''Clears the Current Frame Cache'''
        self.mutex.lock()
        self.cache.clear()
        self.mutex.unlock()
        logger.debug("Frame Cache Cleared")




############################################
#######     GL GPU Image Display     #######



class GLVideoDisplay(QOpenGLWidget):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self.frame = None
        self.texture_id = None
        self.program = None
        self.vao = None
        self.scale_w = 1.0
        self.scale_h = 1.0

        self.inputSpace = "sRGB"
        self.display = "sRGB"
        self.view = "Standard"
        self.lut_path = None

        self.config = ocio.GetCurrentConfig()
        self.processor = self.config.getProcessor("lin_srgb", "sRGB")
        self.gpu_proc = self.processor.getDefaultGPUProcessor()

        #   Add RCL Menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.player.rclPreview)


    def _compileShaderProgram(self, vert_src, frag_src):

        def compileShader(src, shader_type):
            shader = glCreateShader(shader_type)
            glShaderSource(shader, src)
            glCompileShader(shader)

            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader).decode())
            
            return shader


        vs = compileShader(vert_src, GL_VERTEX_SHADER)
        fs = compileShader(frag_src, GL_FRAGMENT_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        glLinkProgram(program)

        if not glGetProgramiv(program, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(program).decode())
        
        return program


    def initializeGL(self):
        self.texture_id = glGenTextures(1)
        #   Simple Pass-through Shader
        vertex_shader_src = """
        #version 330
        in vec2 position;
        in vec2 texcoord;
        out vec2 vTexCoord;
        uniform vec2 uScale;
        void main() {
            vTexCoord = texcoord;
            gl_Position = vec4(position * uScale, 0.0, 1.0);
        }
        """
        fragment_shader_src = """
        #version 330
        uniform sampler2D uTex;
        in vec2 vTexCoord;
        out vec4 fragColor;
        void main() {
            fragColor = texture(uTex, vTexCoord);
        }
        """
        self.program = self._compileShaderProgram(vertex_shader_src, fragment_shader_src)
        self._setupQuad()


    def setOcioTransforms(self, inputSpace, display, view, lut):
        self.inputSpace = inputSpace
        self.display = display
        self.view = view
        self.lut_path = lut


    def _setupQuad(self):
        verts = np.array([
            -1, -1, 0, 0,
             1, -1, 1, 0,
             1,  1, 1, 1,
            -1,  1, 0, 1,
        ], dtype=np.float32)

        indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

        self.vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)

        glBindVertexArray(self.vao)

        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, verts.nbytes, verts, GL_STATIC_DRAW)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        posLoc = glGetAttribLocation(self.program, "position")
        texLoc = glGetAttribLocation(self.program, "texcoord")

        glEnableVertexAttribArray(posLoc)
        glVertexAttribPointer(posLoc, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))

        glEnableVertexAttribArray(texLoc)
        glVertexAttribPointer(texLoc, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))

        glBindVertexArray(0)



    def resizeGL(self, w, h):
        if self.frame is not None:
            vid_h, vid_w, _ = self.frame.shape
            aspect = vid_h / vid_w
            target_h = int(w * aspect)

            #   Keep Viewport Matching Widget Size
            glViewport(0, 0, w, target_h)

            #   Ensure Scale Matches Container
            self.scale_w = 1.0
            self.scale_h = 1.0
        else:
            glViewport(0, 0, w, h)
            self.scale_w = 1.0
            self.scale_h = 1.0



    def setFrame(self, frameIdx: int, frame: np.ndarray) -> None:
        self.frameIdx = frameIdx
        self.frame = frame
        self.update()


    def applyOCIO_CPU(self, img_np, input_space="sRGB", display="sRGB", view="Standard", lut_path=None):
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

        config = ocio.GetCurrentConfig()
        disp_view_transform = ocio.DisplayViewTransform(
            src=input_space or '',
            display=display or '',
            view=view or '',
            looksBypass=False,
            dataBypass=True
        )
        final_transform = disp_view_transform

        if lut_path:
            file_lut = ocio.FileTransform(
                lut_path,
                interpolation=ocio.Interpolation.INTERP_LINEAR,
                direction=ocio.TransformDirection.TRANSFORM_DIR_FORWARD
            )
            group = ocio.GroupTransform()
            group.appendTransform(disp_view_transform)
            group.appendTransform(file_lut)
            final_transform = group

        processor = config.getProcessor(final_transform)
        cpu_proc = processor.getDefaultCPUProcessor()

        img_desc = ocio.PackedImageDesc(img_np_f32, w, h, 3)
        cpu_proc.apply(img_desc)

        img_np_out = np.clip(img_np_f32 * 255.0, 0, 255).astype(np.uint8)
        return img_np_out



    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT)
        if self.frame is None:
            return

        #   Apply OCIO
        try:
            img_data = self.applyOCIO_CPU(self.frame, self.inputSpace, self.display, self.view, self.lut_path)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Apply OCIO Transforms: {e}")
            img_data = self.frame


        h, w, c = img_data.shape
        img_data = np.ascontiguousarray(img_data)

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glUseProgram(self.program)
        loc = glGetUniformLocation(self.program, "uScale")
        glUniform2f(loc, self.scale_w, self.scale_h)

        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)

        glUseProgram(0)
        self.player.onCurrentChanged(self.frameIdx)

