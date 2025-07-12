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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


from PrismUtils.Decorators import err_catcher


logger = logging.getLogger(__name__)


class PreviewPlayer(QWidget):
    def __init__(self, origin):
        super(PreviewPlayer, self).__init__()

        self.sourceBrowser = origin

        self.core = self.sourceBrowser.core

        self.iconPath = os.path.join(self.core.prismRoot, "Scripts", "UserInterfacesPrism")

        self.renderResX = 300
        self.renderResY = 169
        self.videoPlayers = {}
        self.currentPreviewMedia = None
        self.previewThreads = []
        self.previewTimeline = None
        self.tlPaused = False
        self.previewSeq = []
        self.pduration = 0
        self.pwidth = 0
        self.pheight = 0
        self.pstart = 0
        self.pend = 0
        self.openPreviewPlayer = False
        self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
        self.previewEnabled = True
        self.state = "enabled"
        self.updateExternalMediaPlayer()
        self.setupUi()
        self.connectEvents()


    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(400, 100)


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

        #   Viewer Image Label
        self.l_previewImage = QLabel(self)
        self.l_previewImage.setContextMenuPolicy(Qt.CustomContextMenu)
        self.l_previewImage.setText("")
        self.l_previewImage.setAlignment(Qt.AlignCenter)
        self.l_previewImage.setObjectName("l_previewImage")
        self.lo_preview_main.addWidget(self.l_previewImage)

        #   Proxy Icon Label
        self.l_pxyIcon = QLabel(self.l_previewImage)
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
        
        self.b_first = QToolButton()
        self.b_first.clicked.connect(self.onFirstClicked)
        self.b_prev = QToolButton()
        self.b_prev.clicked.connect(self.onPrevClicked)
        self.b_play = QToolButton()
        self.b_play.clicked.connect(self.onPlayClicked)
        self.b_next = QToolButton()
        self.b_next.clicked.connect(self.onNextClicked)
        self.b_last = QToolButton()
        self.b_last.clicked.connect(self.onLastClicked)
        
        self.lo_playerCtrls.addWidget(self.b_first)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_prev)
        self.lo_playerCtrls.addWidget(self.b_play)
        self.lo_playerCtrls.addWidget(self.b_next)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_last)
        self.lo_preview_main.addWidget(self.w_playerCtrls)

        #   Icons
        path = os.path.join(self.iconPath, "first.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_first.setIcon(icon)
        self.b_first.setToolTip("First Frame")

        path = os.path.join(self.iconPath, "prev.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_prev.setIcon(icon)
        self.b_prev.setToolTip("Previous Frame")

        path = os.path.join(self.iconPath, "play.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_play.setIcon(icon)
        self.b_play.setToolTip("Play")

        path = os.path.join(self.iconPath, "next.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_next.setIcon(icon)
        self.b_next.setToolTip("Next Frame")

        path = os.path.join(self.iconPath, "last.png")
        icon = self.core.media.getColoredIcon(path)
        self.b_last.setIcon(icon)
        self.b_last.setToolTip("Last Frame")

        self.l_previewImage.setMinimumWidth(self.renderResX)
        self.l_previewImage.setMinimumHeight(self.renderResY)
        self.l_previewImage.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.l_previewImage.clickEvent = self.l_previewImage.mouseReleaseEvent
        self.l_previewImage.mouseReleaseEvent = self.previewClk
        self.l_previewImage.resizeEventOrig = self.l_previewImage.resizeEvent
        self.l_previewImage.resizeEvent = self.previewResizeEvent
        self.l_previewImage.customContextMenuRequested.connect(self.rclPreview)
        self.l_previewImage.mouseMoveEvent = lambda x: self.mouseDrag(x, self.l_previewImage)

        self.sl_previewImage.valueChanged.connect(self.sliderChanged)
        self.sl_previewImage.sliderPressed.connect(self.sliderClk)
        self.sl_previewImage.sliderReleased.connect(self.sliderRls)
        self.sl_previewImage.origMousePressEvent = self.sl_previewImage.mousePressEvent
        self.sl_previewImage.mousePressEvent = self.sliderDrag
        self.sp_current.valueChanged.connect(self.onCurrentChanged)


    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state):
        self.previewEnabled = state
        self.l_previewImage.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)


    @err_catcher(name=__name__)
    def onFirstClicked(self):
        self.previewTimeline.setCurrentTime(0)


    @err_catcher(name=__name__)
    def onPrevClicked(self):
        time = self.previewTimeline.currentTime() - self.previewTimeline.updateInterval()
        if time < 0:
            time = self.previewTimeline.duration() - self.previewTimeline.updateInterval()

        self.previewTimeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onPlayClicked(self):
        if not self.previewSeq:
            return

        self.setTimelinePaused(self.previewTimeline.state() == QTimeLine.Running)


    @err_catcher(name=__name__)
    def onNextClicked(self):
        time = self.previewTimeline.currentTime() + self.previewTimeline.updateInterval()
        time = min(self.previewTimeline.duration(), time)
        self.previewTimeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onLastClicked(self):
        self.previewTimeline.setCurrentTime(self.previewTimeline.updateInterval() * (self.pduration - 1))


    @err_catcher(name=__name__)
    def sliderChanged(self, val):
        if not self.previewSeq:
            return

        time = int(val / self.sl_previewImage.maximum() * self.previewTimeline.duration())
        if time == self.previewTimeline.duration():
            time -= 1

        self.previewTimeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onCurrentChanged(self, value):
        if not self.previewTimeline:
            return

        time = (value - self.pstart) * self.previewTimeline.updateInterval()
        self.previewTimeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def loadMedia(self, mediaFiles, metadata, isProxy):
        self.mediaFiles = mediaFiles
        self.metadata = metadata
        self.isProxy = isProxy

        self.updatePreview(regenerateThumb=False)


    @err_catcher(name=__name__)
    def getSelectedImage(self):
        return self.mediaFiles


    @err_catcher(name=__name__)
    def updatePreview(self, regenerateThumb=False):
        if not self.previewEnabled:
            return
        
        self.l_pxyIcon.setVisible(self.isProxy)

        if self.previewTimeline:
            curFrame = self.getCurrentFrame()

            if self.previewTimeline.state() != QTimeLine.NotRunning:
                if self.previewTimeline.state() == QTimeLine.Running:
                    self.tlPaused = False
                elif self.previewTimeline.state() == QTimeLine.Paused:
                    self.tlPaused = True

                self.previewTimeline.stop()
        else:
            self.tlPaused = True
            curFrame = 0

        for thread in reversed(self.previewThreads):
            if thread.isRunning():
                thread.requestInterruption()

        prevFrame = self.pstart + curFrame
        self.sl_previewImage.setValue(0)
        self.sp_current.setValue(0)
        self.previewSeq = []
        self.prvIsSequence = False

        QPixmapCache.clear()
       
        for videoPlayers in self.videoPlayers:
            if not self.core.isStr(self.videoPlayers[videoPlayers]):
                try:
                    self.videoPlayers[videoPlayers].close()
                except:
                    pass

        self.videoPlayers = {}

        if len(self.mediaFiles) > 0:
            _, extension = os.path.splitext(self.mediaFiles[0])
            extension = extension.lower()

            if (len(self.mediaFiles) > 1 and extension not in self.core.media.videoFormats):
                self.previewSeq = self.mediaFiles
                self.prvIsSequence = True

                (self.pstart, self.pend,) = self.core.media.getFrameRangeFromSequence(self.mediaFiles)

            else:
                self.prvIsSequence = False
                self.previewSeq = self.mediaFiles

            self.pduration = len(self.previewSeq)

            imgPath = self.mediaFiles[0]
            if (self.pduration == 1 and os.path.splitext(imgPath)[1].lower() in self.core.media.videoFormats):
                self.vidPrw = "loading"
                self.updatePrvInfo(imgPath, vidReader="loading", frame=prevFrame)

            else:
                self.updatePrvInfo(imgPath, frame=prevFrame)

            if self.tlPaused:
                self.changeImage_threaded(regenerateThumb=regenerateThumb)
            elif self.pduration < 3:
                self.changeImage_threaded(regenerateThumb=regenerateThumb)

            return True


        pmap = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        self.currentPreviewMedia = pmap
        self.l_previewImage.setPixmap(pmap)
        self.sl_previewImage.setEnabled(False)
        self.l_start.setText("")
        self.l_end.setText("")
        self.w_playerCtrls.setEnabled(False)
        self.sp_current.setEnabled(False)

        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.l_loading.setVisible(False)
            self.loadingGif.stop()


    @err_catcher(name=__name__)
    def updatePrvInfo(self, prvFile="", vidReader=None, seq=None, frame=None):
        if seq is not None:
            if self.previewSeq != seq:
                logger.debug("Exit Preview Info Update")
                return

        if not os.path.exists(prvFile):
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.l_previewImage.setToolTip("")
            return

        if self.state == "disabled" or os.getenv("PRISM_DISPLAY_MEDIA_RESOLUTION") == "0":
            self.pwidth = "?"
            self.pheight = "?"

        else:
            if vidReader == "loading":
                self.pwidth = "loading..."
                self.pheight = ""
            else:
                self.pwidth = self.metadata.get("source_mainFile_xRez", None)
                self.pheight = self.metadata.get("source_mainFile_yRez", None)

                if not self.pwidth:
                    resolution = self.core.media.getMediaResolution(prvFile, videoReader=vidReader)
                    self.pwidth = resolution["width"]
                    self.pheight = resolution["height"]

        ext = os.path.splitext(prvFile)[1].lower()
        if ext in self.core.media.videoFormats:
            if len(self.previewSeq) == 1:
                duration = self.metadata.get("source_mainFile_frames", None)
                if not duration:
                    duration = self.getVideoDuration(prvFile)
                if not duration:
                    duration = 1

                self.pduration = int(duration)

        self.pformat = "*" + ext

        pdate = self.core.getFileModificationDate(prvFile)
        self.sl_previewImage.setEnabled(True)
        start = "1"
        end = "1"

        if self.prvIsSequence:
            start = str(self.pstart)
            end = str(self.pend)

        elif ext in self.core.media.videoFormats:
            if self.pwidth != "?":
                end = str(int(start) + self.pduration - 1)

        self.l_start.setText(start)
        self.l_end.setText(end)
        self.sp_current.setMinimum(int(start))
        self.sp_current.setMaximum(int(end))
        self.w_playerCtrls.setEnabled(True)
        self.sp_current.setEnabled(True)

        if self.previewTimeline:
            self.previewTimeline.stop()

        fps = self.core.projects.getFps() or 25
        self.previewTimeline = QTimeLine(int(1000/float(fps)) * self.pduration, self)
        self.previewTimeline.setEasingCurve(QEasingCurve.Linear)
        self.previewTimeline.setLoopCount(0)
        self.previewTimeline.setUpdateInterval(int(1000/float(fps)))
        self.previewTimeline.valueChanged.connect(lambda x: self.changeImg(x))

        QPixmapCache.setCacheLimit(2097151)

        frame = frame or self.pstart
        if frame != self.sp_current.value():
            self.sp_current.setValue(frame)
        else:
            self.onCurrentChanged(self.sp_current.value())

        self.previewTimeline.resume()

        if self.tlPaused or self.state == "disabled":
            self.setTimelinePaused(True)

        if self.pduration == 1:
            frStr = "frame"
        else:
            frStr = "frames"

        width = self.pwidth if self.pwidth is not None else "?"
        height = self.pheight if self.pheight is not None else "?"

        if self.prvIsSequence:
            infoStr = "%sx%s   %s   %s-%s (%s %s)" % (
                width,
                height,
                self.pformat,
                self.pstart,
                self.pend,
                self.pduration,
                frStr,
            )

        elif len(self.previewSeq) > 1:
            infoStr = "%s files %sx%s   %s\n%s" % (
                self.pduration,
                width,
                height,
                self.pformat,
                os.path.basename(prvFile),
            )

        elif ext in self.core.media.videoFormats:
            if self.pwidth == "?":
                duration = "?"
                frStr = "frames"
            else:
                duration = self.pduration

            if self.pwidth == "loading...":
                infoStr = "\n" + os.path.basename(prvFile)
            else:
                infoStr = "%sx%s   %s %s\n%s" % (
                    width,
                    height,
                    duration,
                    frStr,
                    os.path.basename(prvFile),
                )

                if self.core.isStr(duration) or duration <= 1:
                    self.sl_previewImage.setEnabled(False)
                    self.l_start.setText("")
                    self.l_end.setText("")
                    self.w_playerCtrls.setEnabled(False)
                    self.sp_current.setEnabled(False)
        else:
            infoStr = "%sx%s\n%s" % (
                width,
                height,
                os.path.basename(prvFile),
            )

            self.sl_previewImage.setEnabled(False)
            self.l_start.setText("")
            self.l_end.setText("")
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        infoStr += "\n" + pdate

        if self.core.getConfig("globals", "showFileSizes"):
            size = 0
            for file in self.previewSeq:
                if os.path.exists(file):
                    size += float(os.stat(file).st_size / 1024.0 / 1024.0)

            infoStr += " - %.2f mb" % size

        if self.state == "disabled":
            infoStr += "\nPreview is disabled"
            self.sl_previewImage.setEnabled(False)
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        self.setInfoText(infoStr)
        self.l_info.setToolTip(infoStr)


    @err_catcher(name=__name__)
    def getVideoDuration(self, filePath):
        frames = 1
        fps = 0.0
        duration_sec = 0.0

        ffprobePath = self.sourceBrowser.getFFprobePath()

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        #   Quick Method
        result = subprocess.run(
            [
                ffprobePath,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames,r_frame_rate:format=duration",
                "-of", "default=noprint_wrappers=1",
                filePath
            ],
            **kwargs
        )

        #   Parse Output
        output_lines = result.stdout.strip().splitlines()
        values = {}
        for line in output_lines:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                values[k] = v

        frames_str = values.get("nb_frames", "1")
        fps_str = values.get("r_frame_rate", "0/1")
        duration_sec_str = values.get("duration", "0")

        #   Parse FPS
        if '/' in fps_str:
            try:
                num, denom = map(int, fps_str.split('/'))
                fps = num / denom if denom else 0.0
            except Exception:
                fps = 0.0

        #   Parse Duration
        try:
            duration_sec = float(duration_sec_str)
        except Exception:
            duration_sec = 0.0

        #   Decide on Frames MEthod
        if frames_str == 'N/A' or not frames_str.isdigit():
            logger.debug("FFprobe failed to get Frames Metadata. Calculating Frames.")
            frames = int(round(duration_sec * fps)) if fps > 0 and duration_sec > 0 else 1
        else:
            frames = int(frames_str)

        return frames


    @err_catcher(name=__name__)
    def setInfoText(self, text):
        metrics = QFontMetrics(self.l_info.font())
        lines = []
        for line in text.split("\n"):
            elidedText = metrics.elidedText(line, Qt.ElideRight, self.l_previewImage.width()-20)
            lines.append(elidedText)

        self.l_info.setText("\n".join(lines))


    @err_catcher(name=__name__)
    def createPMap(self, resx, resy):
        fbFolder = self.core.projects.getFallbackFolder()
        if resx == 300:
            imgFile = os.path.join(fbFolder, "noFileBig.jpg")
        else:
            imgFile = os.path.join(fbFolder, "noFileSmall.jpg")

        pmap = self.core.media.getPixmapFromPath(imgFile)
        if not pmap:
            pmap = QPixmap()

        return pmap


    @err_catcher(name=__name__)
    def moveLoadingLabel(self):
        geo = QRect()
        pos = self.l_previewImage.parent().mapToGlobal(self.l_previewImage.geometry().topLeft())
        pos = self.mapFromGlobal(pos)
        geo.setWidth(self.l_previewImage.width())
        geo.setHeight(self.l_previewImage.height())
        geo.moveTopLeft(pos)
        self.l_loading.setGeometry(geo)


    @err_catcher(name=__name__)
    def changeImage_threaded(self, frame=0, regenerateThumb=False):
        for thread in reversed(self.previewThreads):
            if thread.isRunning():
                thread.requestInterruption()
            else:
                self.previewThreads.remove(thread)

        self.moveLoadingLabel()
        path = os.path.join(self.iconPath, "loading.gif")
        self.loadingGif = QMovie(path, QByteArray(), self) 
        self.loadingGif.setCacheMode(QMovie.CacheAll) 
        self.loadingGif.setSpeed(100) 
        self.l_loading.setMovie(self.loadingGif)
        self.loadingGif.start()
        self.l_loading.setVisible(True)

        thread = self.core.worker(self.core)
        thread.function = lambda x=list(self.previewSeq): self.changeImg(
            frame=frame, seq=x, thread=thread, regenerateThumb=regenerateThumb
        )
        
        thread.errored.connect(self.core.writeErrorLog)
        thread.finished.connect(self.onMediaThreadFinished)
        thread.warningSent.connect(self.core.popup)
        thread.dataSent.connect(self.onChangeImgDataSent)
        if not getattr(self, "curMediaThread", None):
            self.curMediaThread = thread
            thread.start()
        else:
            self.nextMediaThread = thread


    @err_catcher(name=__name__)
    def onMediaThreadFinished(self):
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None
            self.l_loading.setVisible(False)
            self.loadingGif.stop()


    @err_catcher(name=__name__)
    def onChangeImgDataSent(self, data):
        getattr(self, data["function"])(*data["args"], **data["kwargs"])


    @err_catcher(name=__name__)
    def getThumbnailWidth(self):
        return self.l_previewImage.width()


    @err_catcher(name=__name__)
    def getThumbnailHeight(self):
        return self.l_previewImage.height()


    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        if not self.previewTimeline:
            return

        return int(self.previewTimeline.currentTime() / self.previewTimeline.updateInterval())


    @err_catcher(name=__name__)
    def getPixmapFromVideoPath(
        self, path, thumbWidth, allowThumb=True, regenerateThumb=False, videoReader=None, imgNum=0
        ):

        _, ext = os.path.splitext(path)

        fallbackPath = os.path.join(
            self.core.projects.getFallbackFolder(),
            "%s.jpg" % ext[1:].lower(),
        )

        try:
            # Attempt to use videoReader (fast)
            vidFile = self.core.media.getVideoReader(path) if videoReader is None else videoReader
            if self.core.isStr(vidFile):
                raise RuntimeError(vidFile)

            # Success: read frame
            image = vidFile.get_data(imgNum)
            fileRes = vidFile._meta["size"]
            width = fileRes[0]
            height = fileRes[1]
            qimg = QImage(image, width, height, 3 * width, QImage.Format_RGB888)

            # Resize
            origWidth = qimg.width()
            origHeight = qimg.height()
            thumbHeight = int(origHeight * (thumbWidth / origWidth))
            thumbImage = qimg.scaled(
                thumbWidth, thumbHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            return QPixmap.fromImage(thumbImage)

        except Exception as e:
            logger.debug(f"[Thumbnail Worker] Prism Video Reader failed for {path}, falling back to ffmpeg:\n{e}")

        # --- fallback: ffmpeg ---
        try:
            import tempfile

            ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmpfile:
                thumbTempPath = tmpfile.name

            cmd = [
                ffmpegPath,
                "-v", "error",
                "-y",
                "-ss", "00:00:01.000",  # 1 second in
                "-i", path,
                "-frames:v", "1",
                "-q:v", "2",
                thumbTempPath,
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if result.returncode != 0:
                logger.warning(f"ERROR: FFmpeg thumbnail failed: {result.stderr}")
                return QImage(fallbackPath)

            thumbImage = QImage(thumbTempPath)

            if not thumbImage.isNull() and thumbWidth > 0:
                origWidth = thumbImage.width()
                origHeight = thumbImage.height()
                thumbHeight = int(origHeight * (thumbWidth / origWidth))
                thumbImage = thumbImage.scaled(
                    thumbWidth, thumbHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

            return QPixmap.fromImage(thumbImage)

        except Exception as e2:
            logger.warning(f"ERROR: FFmpeg fallback failed for {path}: {e2}")
            return QImage(fallbackPath)

        finally:
            try:
                os.remove(thumbTempPath)
            except Exception:
                pass


    @err_catcher(name=__name__)
    def changeImg(self, frame=0, seq=None, thread=None, regenerateThumb=False):
        if seq is not None:
            if self.previewSeq != seq:
                logger.debug("exit thread")
                return

        if thread and thread.isInterruptionRequested():
            return

        if not self.previewSeq:
            return

        curFrame = self.getCurrentFrame()
        pmsmall = QPixmap()
        if (
            len(self.previewSeq) == 1
            and os.path.splitext(self.previewSeq[0])[1].lower()
            in self.core.media.videoFormats
        ):
            fileName = self.previewSeq[0]
        else:
            fileName = self.previewSeq[curFrame]

        _, ext = os.path.splitext(fileName)
        ext = ext.lower()

        if self.state == "disabled":
            pmsmall = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())

        else:
            pmsmall = QPixmapCache.find(("Preview_Frame" + str(curFrame)))

            if not pmsmall:
                if ext in [
                    ".jpg",
                    ".jpeg",
                    ".JPG",
                    ".png",
                    ".PNG",
                    ".tif",
                    ".tiff",
                    ".tga",
                    ".exr",
                    ".dpx",
                    ".hdr"
                ]:
                    pm = self.core.media.getPixmapFromPath(
                                        fileName,
                                        self.getThumbnailWidth(),
                                        self.getThumbnailHeight(),
                                        colorAdjust=True
                                        )
                    if pm:
                        if pm.width() == 0 or pm.height() == 0:
                            filename = "%s.jpg" % ext[1:].lower()
                            imgPath = os.path.join(
                                self.core.projects.getFallbackFolder(), filename
                            )
                            pmsmall = self.core.media.getPixmapFromPath(imgPath)
                            pmsmall = self.core.media.scalePixmap(
                                pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                            )
                        elif (pm.width() / float(pm.height())) > 1.7778:
                            pmsmall = pm.scaledToWidth(self.getThumbnailWidth())
                        else:
                            pmsmall = pm.scaledToHeight(self.getThumbnailHeight())
                    else:
                        pmsmall = self.core.media.getPixmapFromPath(
                            os.path.join(
                                self.core.projects.getFallbackFolder(),
                                "%s.jpg" % ext[1:].lower(),
                            )
                        )
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )

                elif ext in self.core.media.videoFormats:
                    try:
                        if len(self.previewSeq) > 1:
                            imgNum = 0
                            vidFile = self.core.media.getVideoReader(fileName)
                        else:
                            imgNum = curFrame
                            vidFile = self.vidPrw
                            if vidFile == "loading":
                                if fileName in self.videoPlayers:
                                    vidFile = self.videoPlayers[fileName]
                                else:
                                    self.vidPrw = self.core.media.getVideoReader(fileName)
                                    vidFile = self.vidPrw
                                    if self.core.isStr(vidFile):
                                        logger.warning(vidFile)

                                    self.videoPlayers[fileName] = vidFile

                                if thread:
                                    data = {"function": "updatePrvInfo", "args": [fileName], "kwargs": {"vidReader": vidFile, "seq": seq}}
                                    thread.dataSent.emit(data)
                                else:
                                    self.updatePrvInfo(fileName, vidReader=vidFile, seq=seq)

                        # pm = self.getPixmapFromVideoPath(
                        #         fileName,
                        #         thumbWidth=1280,
                        #         videoReader=vidFile,
                        #         imgNum=imgNum,
                        #         regenerateThumb=regenerateThumb
                        #     )
                        
                        #####   PRISM NATIVE METHOD     ########
                        pm = self.core.media.getPixmapFromVideoPath(
                                fileName,
                                videoReader=vidFile,
                                imgNum=imgNum,
                                regenerateThumb=regenerateThumb
                            )
                        #########################################

                        pmsmall = self.core.media.scalePixmap(
                            pm, self.getThumbnailWidth(), self.getThumbnailHeight()
                        ) or QPixmap()
                        
                    except Exception as e:
                        logger.debug(traceback.format_exc())
                        imgPath = os.path.join(
                            self.core.projects.getFallbackFolder(),
                            "%s.jpg" % ext[1:].lower(),
                        )
                        pmsmall = self.core.media.getPixmapFromPath(imgPath)
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                else:
                    return False

                if seq is not None:
                    if self.previewSeq != seq:
                        logger.debug("exit preview update")
                        return

                QPixmapCache.insert(("Preview_Frame" + str(curFrame)), pmsmall)

        if not self.prvIsSequence and len(self.previewSeq) > 1:
            fileName = self.previewSeq[curFrame]
            if thread:
                thread.dataSent.emit({"function": "updatePrvInfo", "args": [fileName], "kwargs": {"seq": seq}})
            else:
                self.updatePrvInfo(fileName, seq=seq)

        if thread:
            thread.dataSent.emit({"function": "completeChangeImg", "args": [pmsmall, curFrame, ext], "kwargs": {}})
        else:
            self.completeChangeImg(pmsmall, curFrame, ext)


    @err_catcher(name=__name__)
    def completeChangeImg(self, pmsmall, curFrame, ext):
        self.currentPreviewMedia = pmsmall
        self.l_previewImage.setPixmap(pmsmall)
        if self.pduration > 1:
            newVal = int(self.sl_previewImage.maximum() * (curFrame / float(self.pduration-1)))
        else:
            newVal = 0

        curSliderVal = int((self.sl_previewImage.value() / self.sl_previewImage.maximum()) * float(self.pduration))
        if curSliderVal != curFrame:
            self.sl_previewImage.blockSignals(True)
            self.sl_previewImage.setValue(newVal)
            self.sl_previewImage.blockSignals(False)

        if ext in self.core.media.videoFormats:
            curFrame += 1

        if self.sp_current.value() != (self.pstart + curFrame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + curFrame))
            self.sp_current.blockSignals(False)


    @err_catcher(name=__name__)
    def setTimelinePaused(self, state):
        self.previewTimeline.setPaused(state)
        if state:
            path = os.path.join(self.iconPath, "play.png")
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Play")
        else:
            path = os.path.join(self.iconPath, "pause.png")
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Pause")


    @err_catcher(name=__name__)
    def previewClk(self, event):
        if (len(self.previewSeq) > 1 or self.pduration > 1) and event.button() == Qt.LeftButton:
            if self.previewTimeline.state() == QTimeLine.Paused:
                self.setTimelinePaused(False)

            else:
                if self.previewTimeline.state() == QTimeLine.Running:
                    self.setTimelinePaused(True)

        self.l_previewImage.clickEvent(event)


    @err_catcher(name=__name__)
    def rclPreview(self, pos):
        menu = self.getMediaPreviewMenu()

        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self):
        path = self.mediaFiles[0]

        rcmenu = QMenu(self)

        if len(self.mediaFiles) > 0:

            #   External Player
            playMenu = QMenu("Play in", self)
            iconPath = os.path.join(self.iconPath, "play.png")
            icon = self.core.media.getColoredIcon(iconPath)
            playMenu.setIcon(icon)

            if self.mediaPlayerPath is not None:
                pAct = QAction(self.mediaPlayerName, self)
                pAct.triggered.connect(self.compare)
                playMenu.addAction(pAct)

            pAct = QAction("Default", self)
            pAct.triggered.connect(
                lambda: self.compare(prog="default")
            )
            playMenu.addAction(pAct)
            rcmenu.addMenu(playMenu)

            #   Regenerate Thumb
            if self.core.media.getUseThumbnails():
                prvAct = QAction("Regenerate Thumbnail", self)
                iconPath = os.path.join(self.iconPath, "refresh.png")
                icon = self.core.media.getColoredIcon(iconPath)
                prvAct.setIcon(icon)
                prvAct.triggered.connect(self.regenerateThumbnail)
                rcmenu.addAction(prvAct)

            #   Open in Explorer
            expAct = QAction("Open in Explorer", self)
            iconPath = os.path.join(self.iconPath, "folder.png")
            icon = self.core.media.getColoredIcon(iconPath)
            expAct.setIcon(icon)
            expAct.triggered.connect(lambda: self.core.openFolder(path))
            rcmenu.addAction(expAct)

            #   Copy
            copAct = QAction("Copy", self)
            iconPath = os.path.join(self.iconPath, "copy.png")
            icon = self.core.media.getColoredIcon(iconPath)
            copAct.setIcon(icon)
            copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
            rcmenu.addAction(copAct)

        return rcmenu


    @err_catcher(name=__name__)
    def regenerateThumbnail(self):
        self.clearCurrentThumbnails()
        self.updatePreview(regenerateThumb=True)


    @err_catcher(name=__name__)
    def clearCurrentThumbnails(self):
        if not self.previewSeq:
            return

        thumbdir = os.path.dirname(self.core.media.getThumbnailPath(self.previewSeq[0]))
        if not os.path.exists(thumbdir):
            return

        try:
            shutil.rmtree(thumbdir)
        except Exception as e:
            logger.warning("Failed to remove thumbnail: %s" % e)


    @err_catcher(name=__name__)
    def previewResizeEvent(self, event):
        self.l_previewImage.resizeEventOrig(event)
        height = int(self.l_previewImage.width()*(self.renderResY/self.renderResX))
        self.l_previewImage.setMinimumHeight(height)
        self.l_previewImage.setMaximumHeight(height)
        if self.currentPreviewMedia:
            pmap = self.core.media.scalePixmap(
                self.currentPreviewMedia, self.getThumbnailWidth(), self.getThumbnailHeight()
            )
            self.l_previewImage.setPixmap(pmap)

        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.moveLoadingLabel()

        QPixmapCache.clear()
        text = self.l_info.toolTip()
        if not text:
            text = self.l_info.text()

        self.setInfoText(text)


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
        if (
            self.previewTimeline
            and self.previewTimeline.state() == QTimeLine.Running
        ):
            self.slStop = True
            self.setTimelinePaused(True)
        else:
            self.slStop = False


    @err_catcher(name=__name__)
    def sliderRls(self):
        if self.slStop:
            self.setTimelinePaused(False)


    @err_catcher(name=__name__)
    def compare(self, prog=""):
        if (
            self.previewTimeline
            and self.previewTimeline.state() == QTimeLine.Running
        ):
            self.setTimelinePaused(True)

        if prog == "default":
            progPath = ""
        else:
            progPath = self.mediaPlayerPath or ""

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


    @err_catcher(name=__name__)
    def updateExternalMediaPlayer(self):
        player = self.core.media.getExternalMediaPlayer()
        self.mediaPlayerPath = player.get("path", None)
        self.mediaPlayerName = player.get("name", None)
        self.mediaPlayerPattern = player.get("framePattern", None)

