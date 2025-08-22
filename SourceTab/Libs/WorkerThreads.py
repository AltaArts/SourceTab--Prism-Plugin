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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


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


import SourceTab_Utils as Utils

logger = logging.getLogger(__name__)



###     Thumbnail Worker Thread ###
class ThumbnailWorker(QObject, QRunnable):
    result = Signal(QImage, str, float, bool, bool)

    def __init__(self, origin, filePath, saveWidth, width, height, regenerate):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.origin = origin
        self.core = self.origin.core

        self.filePath = filePath

        self.saveThumbWidth = saveWidth
        self.tileThumbWidth = width
        self.tileThumbHeight = height
        self.regenerate = regenerate


    @Slot()
    def run(self):
        self.origin.thumb_semaphore.acquire()

        try:
            thumbImage = None
            extension = os.path.splitext(self.filePath)[1].lower()

            #   Use App Icon for Non-Media Formats
            if extension not in self.core.media.supportedFormats:
                file_info = QFileInfo(self.filePath)
                icon_provider = QFileIconProvider()
                icon = icon_provider.icon(file_info)                
                pixmap = icon.pixmap(self.tileThumbWidth, self.tileThumbHeight)
                thumbImage = pixmap.toImage()

                fitIntoBounds = True
                crop = False
                scale = 0.5 # Scale to make Icon smaller in Tile
                logger.debug(f"Using File Icon for Unsupported Format: {extension}")

            #   Get Thumbnail for Media Formats
            else:
                thumbPath = Utils.getThumbnailPath(self.filePath)
                if not self.regenerate and os.path.exists(thumbPath):
                #   Use Saved Thumbnail in "_thumbs" if Exists
                    thumbImage = QImage(thumbPath)

                #   Or Generate New Thumb
                else:
                    thumbImage = self.getThumbImageFromPath(
                        self.filePath,
                        saveThumbWidth=self.saveThumbWidth,
                        colorAdjust=False,
                        regenerateThumb=self.regenerate
                        )
                
                fitIntoBounds = False
                crop = True
                scale = 1

            self.result.emit(thumbImage, self.filePath, scale, fitIntoBounds, crop)

        finally:
            self.origin.thumb_semaphore.release()


    def getThumbImageFromPath(self, path, saveThumbWidth=None, colorAdjust=False, regenerateThumb=False):
        if not path:
            return

        ext = Utils.getFileExtension(filePath=path)

        if ext in self.core.media.videoFormats:
            thumbImage = Utils.getThumbFromVideoPath(self.core, path, thumbWidth=saveThumbWidth, regenerateThumb=regenerateThumb)
        
        elif ext in [".exr", ".dpx", ".hdr"]:
            thumbImage = Utils.getThumbImageFromExrPath(self.core, path, thumbWidth=saveThumbWidth)

        else:
            thumbImage = Utils.getThumbFromImage(path, maxWidth=self.saveThumbWidth)

        return thumbImage



###     Hash Worker Thread    ###
class FileHashWorker(QObject, QRunnable):
    finished = Signal(str, QObject)

    def __init__(self, filePath, tile=None):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.filePath = filePath
        self.tile = tile


    @Slot()
    def run(self):
        try:
            chunk_size = 8192
            hash_func = hashlib.sha256()
            file_size = os.path.getsize(self.filePath)

            with open(self.filePath, "rb") as f:
                if file_size <= chunk_size * 2:
                    #   File is Small, Read it All
                    hash_func.update(f.read())
                else:
                    #   Large File, First and Last chunks
                    hash_func.update(f.read(chunk_size))
                    f.seek(-chunk_size, os.SEEK_END)
                    hash_func.update(f.read(chunk_size))

            #   Always include file size in hash
            hash_func.update(str(file_size).encode())
            result_hash = hash_func.hexdigest()

            logger.debug(f"[FileHashWorker] Hash Generated for {self.filePath}")
            self.finished.emit(result_hash, self.tile)

        except Exception as e:
            logger.warning(f"[FileHashWorker] Error hashing {self.filePath} - {e}")
            self.finished.emit("Error", self.tile)



###     File Info Worker Thread    ###
class FileInfoWorker(QObject, QRunnable):
    finished = Signal(int, float, float, str, dict, int, int)

    def __init__(self, origin, core, filePath):
        QObject.__init__(self)
        QRunnable.__init__(self)

        self.origin = origin
        self.core = core
        self.filePath = filePath

    @Slot()
    def run(self):
        try:
            extension = os.path.splitext(Utils.getBasename(self.filePath))[1].lower()

            frames = 1
            fps = 0.0
            secs = 0.0
            codec = None
            metadata = {}

            if extension not in self.core.media.supportedFormats:
                return

            fileType = self.origin.fileType

            if fileType in ("Videos", "Images", "Audio"):
                ffprobePath = Utils.getFFprobePath()

                kwargs = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text": True,
                }

                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                # Determine stream type
                if fileType in ("Videos", "Images"):
                    stream_type = "v:0"
                elif fileType == "Audio":
                    stream_type = "a:0"
                else:
                    logger.debug(f"[FileInfoWorker] Unknown fileType for ffprobe: {fileType}")
                    self.finished.emit(1, 0.0, 0.0, None, {})
                    return

                result = subprocess.run(
                    [
                        ffprobePath,
                        "-v", "error",
                        "-select_streams", stream_type,
                        "-show_entries",
                        "stream=nb_frames,r_frame_rate,codec_name,profile,codec_tag_string,codec_long_name,width,height:format=duration",
                        "-of", "default=noprint_wrappers=1",
                        self.filePath
                    ],
                    **kwargs
                )

                if result.returncode != 0:
                    logger.warning(f"[FileInfoWorker] ERROR: FFprobe failed for {self.filePath}:\n{result.stderr}")
                    self.finished.emit(1, 0.0, 0.0, None, {})
                    return

                output_lines = result.stdout.strip().splitlines()
                values = {}
                for line in output_lines:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        values[k] = v

                metadata = values

                frames_str = values.get("nb_frames", "1")
                fps_str = values.get("r_frame_rate", "0/1")
                sec_str = values.get("duration", "0")
                codec = values.get("codec_name")
                width_str = values.get("width", "0")
                height_str = values.get("height", "0")

                #   Parse Resolution
                try:
                    width = int(width_str)
                except Exception:
                    width = 0

                try:
                    height = int(height_str)
                except Exception:
                    height = 0

                #   Parse FPS
                if '/' in fps_str:
                    try:
                        num, denom = map(int, fps_str.split('/'))
                        fps = num / denom if denom else 0.0
                    except Exception:
                        fps = 0.0

                #   Parse Duration
                try:
                    secs = float(sec_str)
                except Exception:
                    secs = 0.0

                #   Parse Frames
                if frames_str == 'N/A' or not frames_str.isdigit():
                    logger.debug("[FileInfoWorker] FFprobe failed to get Frames Metadata. Estimating.")
                    frames = int(round(secs * fps)) if fps > 0 and secs > 0 else 1
                else:
                    frames = int(frames_str)

                logger.debug(f"[FileInfoWorker] ffprobe complete for {self.filePath}")

            else:
                logger.debug(f"[FileInfoWorker] Unsupported fileType: {fileType}")
                self.finished.emit(1, 0.0, 0.0, None, {})
                return


            self.finished.emit(frames, fps, secs, codec, metadata, width, height)

        except Exception as e:
            logger.warning(f"[FileInfoWorker] ERROR: {self.filePath} - {e}")
            self.finished.emit(1, 0.0, 0.0, None, {})




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
                    logger.warning(f"[FileCopyWorker] ERROR: Could not get size for: {transItem['sourcePath']} - {e}")

            copied_size_all = 0

            # Step 2: Loop through all items
            for transItem in self.transferList:
                sourcePath = transItem["sourcePath"]
                destPath = transItem["destPath"]

                try:
                    total_size = os.path.getsize(sourcePath)
                except Exception as e:
                    logger.warning(f"[FileCopyWorker] ERROR: Could not get size of {sourcePath}: {e}")
                    continue

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
            logger.warning(f"[FileCopyWorker] ERROR: Could not copy file: {e}")
            self.finished.emit(False)

        finally:
            self.origin.copy_semaphore.release()
            self.running = False



###     Proxy Generation Worker Thread    ###
class ProxyGenerationWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(str)

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


    def cancel(self):
        logger.warning("[ProxyWorker] Cancel called!")
        self.cancel_flag = True


    #   Stop the FFmpeg Process
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
        #   Get FFmpeg from Core
        ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))
        if not ffmpegPath:
            self.finished.emit("ERROR: FFmpeg binary not found")
            return

        total_frames = int(self.settings.get("frames", 0))
        if total_frames <= 0:
            logger.warning("[ProxyWorker] ERROR: Invalid total frame count.")
            self.finished.emit("ERROR: Invalid total frame count")
            return

        #   Get Parameters from Passed Preset
        global_params = self.settings.get("Global_Parameters", "")
        vid_params = self.settings.get("Video_Parameters", "")
        aud_params = self.settings.get("Audio_Parameters", "")
        scale_str = self.settings.get("scale", None)

        #   Create Proxy Dir if Needed
        os.makedirs(os.path.dirname(self.outputPath), exist_ok=True)

        # inputExt = os.path.splitext(Utils.getBasename(self.inputPath))[1].lower()
        # videoInput = inputExt in self.core.media.videoFormats
        # startNum = 0 if videoInput else 0                                                #   NEEDED???

        ##   Build Args List
        
        #   Add FFmpeg Path
        argList = [ffmpegPath]

        #   Add Global Params
        if global_params:
            argList += shlex.split(global_params)

        #   Add Input Path
        argList += ["-i", self.inputPath]

        #   Add Scaling
        if scale_str:
            if scale_str.endswith("%"):
                pct = float(scale_str.strip("%")) / 100.0
                expr = f"scale=trunc(iw*{pct}/2)*2:trunc(ih*{pct}/2)*2"

            else:
                expr = f"scale={scale_str}"
            argList += ["-vf", expr]

        #   Add Video Encode Params
        if vid_params:
            argList += shlex.split(vid_params)

        #   Add Audio Encode Params
        if aud_params:
            argList += shlex.split(aud_params)

        #   Add Output Path
        argList += [self.outputPath, "-y"]

        #   Build Frame Parser
        frame_re = re.compile(r"frame=\s*(\d+)")

        #   Shell Commands
        shell = (platform.system() == "Windows")
        creationflags = 0
        if shell and platform.system() == "Windows":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        #   Obtain Slot and Callback to Start
        self.origin.proxy_semaphore.acquire()
        self.origin._onProxyGenStart()
        logger.debug(f"FFmpeg command:\n:  {argList}")

        #   List of Error Patterns to Detect in stderr
        fatal_errors = [
            "Error while processing the decoded data",
            "Failed to inject frame into filter network",
            "Error reinitializing filters",
            "Conversion failed!",
        ]

        error_detected = None

        #   Make Proc Object
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
            #   Run Proc in Execute Loop
            while True:
                if self.cancel_flag:
                    logger.warning("[ProxyWorker] Cancel flag detected, terminating FFmpeg.")
                    self._kill_ffmpeg_tree()
                    self.finished.emit("Cancelled")
                    return

                #   Get Output Lines
                line = self.nProc.stderr.readline()
                if not line:
                    break

                #   Detect Error Patterns
                if error_detected is None:
                    for error in fatal_errors:
                        if error in line:
                             #  Kill ffmpeg and Emit Error String
                            self._kill_ffmpeg_tree()
                            self.finished.emit(f"FFmpeg Error: {error}")
                            return

                #   Parse Frame Numbers
                match = frame_re.search(line)
                if match:
                    current = int(match.group(1))
                    pct = int((current / total_frames) * 100)
                    now = time.time()
                    if (now - self.last_emit_time >= self.origin.progUpdateInterval) or (pct == 100):
                        self.progress.emit(pct, current)
                        self.last_emit_time = now

            self.nProc.wait()

            #   Handle Exit Returncode
            if self.nProc.returncode != 0:
                error_msg = f"FFmpeg exited with error code {self.nProc.returncode}"
                logger.error(f"[ProxyWorker] {error_msg}")
                self.finished.emit(error_msg)
                return

            #   If No Errors and Returncode == 0
            self.finished.emit("success")

        except Exception as e:
            logger.warning(f"[ProxyWorker] ERROR: {e}")
            if self.nProc.poll() is None:
                self._kill_ffmpeg_tree()
            self.finished.emit(f"Exception: {str(e)}")

        finally:
            self.origin.proxy_semaphore.release()
            self.running = False


