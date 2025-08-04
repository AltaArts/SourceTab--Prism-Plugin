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
import json
import logging
import uuid
import datetime
import hashlib
import shutil
import numpy

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

prismRoot = os.getenv("PRISM_ROOT")

pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")


import exiftool
import simpleaudio as sa

from PopupWindows import DisplayPopup, PresetsEditor


logger = logging.getLogger(__name__)


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

def debug_recursive_print(data: object, label: str = None) -> None:
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





def getBasename(filePath:str) -> str:
    '''Returns Basename from Path'''
    return os.path.basename(filePath)


def getFileExtension(filePath=None, fileName=None):
    '''Returns Extension from Path or Name'''

    basefile = getBasename(filePath) if filePath else fileName
    _, extension = os.path.splitext(basefile)

    return extension.lower()


def createUUID(simple:bool=False, length:int=8) -> str:
    '''Creates Custom UUID String'''

    #	Creates Simple Date/Time UID as MMDDHHMM
    if simple:
        now = datetime.now()
        uid = now.strftime("%m%d%H%M")

        logger.debug(f"Created Simple UID: {uid}")
    
        return uid
    
    #   Generate 8 Charactor UUID String
    else:
        uid = uuid.uuid4()
        #   Create a SHA-256 hash of the UUID
        hashObject = hashlib.sha256(uid.bytes)
        #   Convert Hash to Hex  and Truncate to Desired Length
        shortUID = hashObject.hexdigest()[:length]

        logger.debug(f"Created UID: {shortUID}")

        return shortUID
    

def explorerDialogue(title: str = None,
                     dir: str = None,
                     selDir: bool = True,
                     save: bool = False,
                     filter: str = None
                     ) -> str:
    """Show a File Dialog to Pick a Directory, File, or Save As."""
    
    if save:
        presetPath, _ = QFileDialog.getSaveFileName(
            None, title or "Save File", dir or "", filter or ""
        )
        return presetPath

    if selDir:
        # Directory selection
        dialog = QFileDialog(None, title or "Select Path", dir or "")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    else:
        # File selection
        dialog = QFileDialog(None, title or "Select File", dir or "")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if filter:
            dialog.setNameFilter(filter)

    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
    dialog.setOption(QFileDialog.Option.ReadOnly, True)

    if dialog.exec():
        return dialog.selectedFiles()[0]

    return None


def openInExplorer(core, path:str) -> None:
    '''Opens Path in File Explorer'''
    if os.path.isdir(path):
        dir = path
    elif os.path.isfile(path):
        dir = os.path.dirname(path)
    else:
        logger.warning(f"ERROR:  Unable to open {path} in File Explorer")
        return

    core.openFolder(dir)


def playSound(path:str) -> None:
    '''Plays Audio with Simple Audio'''

    try:
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        play_obj.wait_done()

    except Exception:
        QApplication.beep()

##################################################
##################  FORMATTING  ##################


def getDriveSpace(path:str) -> int:
    '''Get Storage Space Stats'''

    try:
        total, used, free = shutil.disk_usage(path)   
        return free 
    except Exception as e:
        logger.warning(f"ERROR:  Failed to get Drive Space Stats:\n{e}")


def getFileDate(filePath:str) -> float:
    '''Returns the File Create Date from the OS'''
    return os.path.getmtime(filePath)


def getFileSize(filePath:str) -> int:
    '''Returns the File Size from the OS'''
    return os.stat(filePath).st_size


def getFileSizeStr(size_bytes:int) -> str:
    '''Returns a UI Friendly Size String from Raw Size'''

    size_mb = size_bytes / 1024.0 / 1024.0

    #   Set Size Unit
    if size_mb < 1:
        size_kb = size_bytes / 1024.0
        size = size_kb
        unit = "KB"
    elif size_mb < 1024:
        size = size_mb
        unit = "MB"
    else:
        size = size_mb / 1024.0
        unit = "GB"

    #   Set Decimal Digits Based on Integer Digits
    int_digits = len(str(int(size)))
    if int_digits >= 3:
        fmt = "%.0f"
    elif int_digits == 2:
        fmt = "%.1f"
    else:
        fmt = "%.2f"

    sizeStr = f"{fmt % size} {unit}"
    return sizeStr


def getFormattedTimeStr(seconds:float) -> str:
    '''Returns Time Formatted String'''

    if seconds is None or seconds > 1e6:
        return "Estimating..."
    
    minutes, sec = divmod(int(seconds), 60)
    return f"{minutes:02}:{sec:02}"


def getFpsStr(fps:float) -> str:
    '''Returns Formatted FPS String (ie 24, 25, 29.97 etc)'''
    if fps.is_integer():
        return f"{int(fps)}"
    else:
        return f"{fps:.2f}"


def getIconFromPath(imagePath:str, normalLevel:int=0.9, dimLevel:int=0.4) -> QIcon:
    '''Returns QIcon with Both Normal and Disabled Versions'''

    try:
        normal_pixmap = QPixmap(imagePath)
        normal_image = normal_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)

        #   Darken Normal Version Slightly (normalLevel)
        darkened_normal_image = QImage(normal_image.size(), QImage.Format_ARGB32)

        for y in range(normal_image.height()):
            for x in range(normal_image.width()):
                color = normal_image.pixelColor(x, y)

                #   Reduce brightness to normalLevel
                dark = int(color.red() * normalLevel)
                color = QColor(dark, dark, dark, color.alpha())
                darkened_normal_image.setPixelColor(x, y, color)

        darkened_normal_pixmap = QPixmap.fromImage(darkened_normal_image)

        #   Darken Disbled Version More (dimLevel)
        disabled_image = QImage(normal_image.size(), QImage.Format_ARGB32)

        for y in range(normal_image.height()):
            for x in range(normal_image.width()):
                color = normal_image.pixelColor(x, y)

                # Reduce brightness to 40%
                dark = int(color.red() * dimLevel)
                color = QColor(dark, dark, dark, color.alpha())
                disabled_image.setPixelColor(x, y, color)

        disabled_pixmap = QPixmap.fromImage(disabled_image)

        #   Convert to QIcon
        icon = QIcon()
        icon.addPixmap(darkened_normal_pixmap, QIcon.Normal)
        icon.addPixmap(disabled_pixmap, QIcon.Disabled)

        logger.debug(f"Created Icon for {imagePath}")
        return icon
    
    except Exception as e:
        logger.warning(f"ERROR:  Failed to Create Icon:\n{e}")


def normalizeData(data: dict) -> dict:
    """Ensures all values are stringified for comparison"""

    return {k: str(v) for k, v in data.items()}


#################################################
#################    THUMBNAIL    ################


def getFallBackImage(core, filePath:str=None, extension:str=None) -> str:
    '''Returns Path to Fallback Image from Path or Extension'''

    if filePath:
        _, extension = os.path.splitext(filePath)

    if not extension:
        return os.path.join(iconDir, "unknown.jpg")

    extFallback = os.path.join(
        core.projects.getFallbackFolder(),
        "%s.jpg" % extension[1:].lower()
    )

    if os.path.isfile(extFallback):
        return extFallback
    else:
        return os.path.join(iconDir, "unknown.jpg")


def getThumbnailPath(path:str) -> str:
    '''Returns Thumbnail Path based on FilePath'''

    thumbPath = os.path.join(os.path.dirname(path), "_thumbs", getBasename(os.path.splitext(path)[0]) + ".jpg")
    return thumbPath


def getThumbFromImage(path:str, maxWidth:int=320) -> QImage:
    '''Returns a QImage from a FilePath'''
    
    reader = QImageReader(path)
    if not reader.canRead():
        logger.warning(f"Cannot read image: {path}")
        return None

    thumbImage = reader.read()
    if thumbImage.isNull():
        logger.warning(f"Failed to load image: {path}")
        return None

    #   Scale by Width
    origWidth = thumbImage.width()
    origHeight = thumbImage.height()
    if origWidth > maxWidth:
        newHeight = int(origHeight * (maxWidth / origWidth))
        thumbImage = thumbImage.scaled(maxWidth, newHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    return thumbImage


def getThumbFromVideoPath(
                        core,
                        path: str,
                        thumbWidth: int,
                        allowThumb: bool = True,
                        regenerateThumb: bool = False,
                        videoReader: object = None,
                        imgNum: int = 0,
                        needPixMap: bool = False
                    ) -> QImage | QPixmap:
    """
    Returns a QImage or QPixmap thumbnail for a video file.

    - Uses Prism's VideoReader if available.
    - Falls back to ffmpeg (with fps-based timestamp) if needed.
    """

    fallbackPath = getFallBackImage(core, filePath=path)

    ##   Try Prism's Native Reader
    try:
        vidFile = core.media.getVideoReader(path) if videoReader is None else videoReader
        if core.isStr(vidFile):
            raise RuntimeError(vidFile)

        image = vidFile.get_data(imgNum)
        width, height = vidFile._meta["size"]
        qimg = QImage(image, width, height, 3 * width, QImage.Format_RGB888)

        thumbHeight = int(height * (thumbWidth / width))
        thumbImage = qimg.scaled(thumbWidth, thumbHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return QPixmap.fromImage(thumbImage) if needPixMap else thumbImage

    except Exception as e:
        logger.debug(f"[Thumbnail Worker] Prism VideoReader failed for {path}, falling back to ffmpeg:\n{e}")

    ##  Fallback to ffmpeg
    import tempfile
    thumbTempPath = None
    try:
        ffmpegPath = os.path.normpath(core.media.getFFmpeg(validate=True))
        ffprobePath = getFFprobePath()

        #   Determine fps
        fps = 24.0
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        probe = subprocess.run(
            [
                ffprobePath,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        if probe.returncode == 0:
            fps_str = probe.stdout.strip()
            if "/" in fps_str:
                num, denom = fps_str.split("/", 1)
                fps = float(num) / float(denom) if float(denom) > 0 else fps

        timestamp = imgNum / fps

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmpfile:
            thumbTempPath = tmpfile.name

        cmd = [
            ffmpegPath,
            "-v", "error", "-y",
            "-ss", f"{timestamp:.3f}",
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
            creationflags=creationflags,
        )

        if result.returncode != 0:
            logger.warning(f"FFmpeg thumbnail failed: {result.stderr}")
            return QPixmap.fromImage(QImage(fallbackPath)) if needPixMap else QImage(fallbackPath)

        thumbImage = QImage(thumbTempPath)

        if not thumbImage.isNull() and thumbWidth > 0:
            origWidth = thumbImage.width()
            origHeight = thumbImage.height()
            thumbHeight = int(origHeight * (thumbWidth / origWidth))
            thumbImage = thumbImage.scaled(thumbWidth, thumbHeight, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        return QPixmap.fromImage(thumbImage) if needPixMap else thumbImage

    except Exception as e2:
        logger.warning(f"FFmpeg fallback failed for {path}: {e2}")
        return QPixmap.fromImage(QImage(fallbackPath)) if needPixMap else QImage(fallbackPath)

    finally:
        if thumbTempPath:
            try:
                os.remove(thumbTempPath)
            except Exception:
                pass


def getThumbImageFromExrPath(core,
                             path:str,
                             thumbWidth:int=None,
                             channel:str=None,
                             allowThumb:bool=True,
                             regenerateThumb:bool=False,
                             needPixMap:bool=False
                             ) -> QPixmap | QImage:
    '''Returns a QImage or Qpixmap from a EXR FilePath.'''
    
    oiio = core.media.getOIIO()
    if not oiio:                                #   TODO - LOOK AT THIS
        return core.getPixmapFromExrPathWithoutOIIO(path, width=None, height=None, channel=channel,
                                                    allowThumb=allowThumb, regenerateThumb=regenerateThumb)

    path = str(path)
    imgInput = oiio.ImageInput.open(path)
    if not imgInput:
        logger.debug("failed to read media file: %s" % path)
        return

    chbegin = 0
    chend = 3
    numChannels = 3
    subimage = 0

    if channel:
        #   Channel Logic
        while imgInput.seek_subimage(subimage, 0):
            idx = imgInput.spec().channelindex(channel + ".R")
            if idx == -1:
                for suffix in [".red", ".r", ".x", ".Z"]:
                    idx = imgInput.spec().channelindex(channel + suffix)
                    if idx != -1:
                        if suffix == ".Z":
                            numChannels = 1
                        break
                if idx == -1 and channel in ["RGB", "RGBA"]:
                    idx = imgInput.spec().channelindex("R")
            if idx == -1:
                subimage += 1
            else:
                chbegin = idx
                chend = chbegin + numChannels
                break
    else:
        #   Try to get RGB, fallback to Grayscale
        while imgInput.seek_subimage(subimage, 0):
            spec = imgInput.spec()
            r = spec.channelindex("R")
            g = spec.channelindex("G")
            b = spec.channelindex("B")
            y = spec.channelindex("Y")
            z = spec.channelindex("Z")

            if r != -1 and g != -1 and b != -1:
                chbegin = r
                chend = r + 3
                numChannels = 3
                break
            elif y != -1:
                chbegin = y
                chend = y + 1
                numChannels = 1
                break
            elif z != -1:
                chbegin = z
                chend = z + 1
                numChannels = 1
                break
            else:
                #   Fallback: Use First Available Channel
                chbegin = 0
                chend = 1
                numChannels = 1
                break

            subimage += 1

    try:
        pixels = imgInput.read_image(subimage=subimage, miplevel=0, chbegin=chbegin, chend=chend)
    except Exception as e:
        logger.warning("failed to read image: %s - %s" % (path, e))
        return

    if pixels is None:
        logger.warning("failed to read image (no pixels): %s" % (path))
        return

    spec = imgInput.spec()
    imgWidth = spec.full_width
    imgHeight = spec.full_height
    if not imgWidth or not imgHeight:
        return

    rgbImgSrc = oiio.ImageBuf(
        oiio.ImageSpec(imgWidth, imgHeight, numChannels, oiio.UINT16)
    )
    imgInput.close()

    if "numpy" in globals():
        rgbImgSrc.set_pixels(spec.roi, numpy.array(pixels))
    else:
        for h in range(imgHeight):
            for w in range(imgWidth):
                color = [pixels[h][w][0], pixels[h][w][1], pixels[h][w][2]]
                rgbImgSrc.setpixel(w, h, 0, color)

    #   Thumbnail Size Calculation
    if thumbWidth:
        thumbHeight = int(imgHeight * (thumbWidth / float(imgWidth)))
        newImgWidth = thumbWidth
        newImgHeight = thumbHeight
    else:
        newImgWidth = imgWidth
        newImgHeight = imgHeight

    #   Resize and Gamma Correct
    imgDst = oiio.ImageBuf(
        oiio.ImageSpec(int(newImgWidth), int(newImgHeight), numChannels, oiio.UINT16)
    )
    oiio.ImageBufAlgo.resample(imgDst, rgbImgSrc)
    sRGBimg = oiio.ImageBuf()
    oiio.ImageBufAlgo.pow(sRGBimg, imgDst, (1.0 / 2.2, 1.0 / 2.2, 1.0 / 2.2))
    bckImg = oiio.ImageBuf(
        oiio.ImageSpec(int(newImgWidth), int(newImgHeight), numChannels, oiio.UINT16)
    )
    oiio.ImageBufAlgo.fill(bckImg, (0.5, 0.5, 0.5))
    oiio.ImageBufAlgo.paste(bckImg, 0, 0, 0, 0, sRGBimg)

    #   Numpy to QImage Conversion
    try:
        arr = bckImg.get_pixels(oiio.FLOAT)  # Shape: (H, W, C)
        arr = numpy.clip(arr * 255.0, 0, 255).astype(numpy.uint8)
        height, width, channels = arr.shape

        if channels >= 3:
            fmt = QImage.Format_RGB888
            arr = arr[:, :, :3]
        else:
            fmt = QImage.Format_Grayscale8

        bytesPerLine = width * arr.shape[2]
        thumbImage = QImage(arr.data, width, height, bytesPerLine, fmt).copy()

    except Exception as e:
        logger.debug(f"[Fallback] Slow pixel copy: {e}")
        thumbImage = QImage(int(newImgWidth), int(newImgHeight), QImage.Format_RGB32)
        for i in range(int(newImgWidth)):
            for k in range(int(newImgHeight)):
                px = bckImg.getpixel(i, k)
                if numChannels == 3:
                    rgb = qRgb(px[0] * 255, px[1] * 255, px[2] * 255)
                else:
                    v = px[0] * 255
                    rgb = qRgb(v, v, v)
                thumbImage.setPixel(i, k, rgb)

    return QPixmap.fromImage(thumbImage) if needPixMap else thumbImage


#################################################
#################    METADATA    ################


def formatCodecMetadata(metadata:dict) -> str:
    '''Returns String from Metadata Dict'''
    if not metadata:
        return "Metadata:    None"
    lines = ["Metadata:"]
    for k, v in metadata.items():
        lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def getFFprobePath() -> str:
    '''Returns File Path of ffprobe.exe'''
    return os.path.join(pluginPath, "PythonLibs", "FFmpeg", "ffprobe.exe")


def getExiftool() -> str:
    '''Returns File Path of exitool.exe'''

    exifDir = os.path.join(pluginPath, "PythonLibs", "ExifTool")

    possible_names = ["exiftool.exe", "exiftool(-k).exe"]

    for root, dirs, files in os.walk(exifDir):
        for file in files:
            if file.lower() in [name.lower() for name in possible_names]:
                exifToolEXE = os.path.join(root, file)
                logger.debug(f"ExifTool found at: {exifToolEXE}")

                return exifToolEXE

    logger.warning(f"ERROR:  Unable to Find ExifTool")
    return None


def getMetadata(filePath:str) -> dict:
    '''Returns Dict of All Raw Metadata from ExifTool'''
    try:
        exifToolEXE = getExiftool()
        with exiftool.ExifTool(exifToolEXE) as et:
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
    
    
def groupMetadata(metadata:dict) -> dict:
    '''Groups Raw Metadata into Logical Groups'''

    grouped = {}
    
    for key, value in metadata.items():
        section = key.split(":")[0]
        tag = key.split(":")[1] if len(key.split(":")) > 1 else key
        
        if section not in grouped:
            grouped[section] = {}
        
        grouped[section][tag] = value
    
    return grouped


def displayMetadata(filePath:str) -> None:
    '''Displays Popup of Groupded Metadata from ExifTool'''

    metadata = getMetadata(filePath)

    if metadata:
        grouped_metadata = groupMetadata(metadata)
        logger.debug("Showing MetaData Popup")
        DisplayPopup.display(grouped_metadata, title="File Metadata", modal=False)
    else:
        logger.warning("No metadata to display.")


def getFFprobeMetadata(filePath: str) -> dict:
    '''Returns Dict of All Raw Metadata from FFprobe'''

    cmd = [
        getFFprobePath(),
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-print_format", "json",
        filePath
    ]

    #   Prepare kwargs for Subprocess
    kwargs = {
        "capture_output": True,
        "text": True,
        "check": True
    }

    #   Suppress Console Window
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(cmd, **kwargs)
        metadata_json = result.stdout
        metadata = json.loads(metadata_json)

        if metadata:
            logger.debug(f"FFprobe metadata found for {filePath}")
            return metadata
        else:
            logger.warning(f"FFprobe: No metadata found for {filePath}")
            return {}

    except subprocess.CalledProcessError as e:
        logger.warning(f"FFprobe failed for {filePath}: {e.stderr}")
        return {}
    except Exception as e:
        logger.warning(f"Failed to get ffprobe metadata for {filePath}: {e}")
        return {}


def groupFFprobeMetadata(metadata:dict) -> dict:
    '''Groups Raw Metadata into Logical Groups'''

    grouped = {}

    if "format" in metadata:
        grouped["format"] = {}
        for k, v in metadata["format"].items():
            if k == "tags" and isinstance(v, dict):
                grouped["format"]["tags"] = v.copy()
            else:
                grouped["format"][k] = v

    if "streams" in metadata:
        for idx, stream in enumerate(metadata["streams"]):
            section_name = f"stream_{idx}"
            grouped[section_name] = {}
            for k, v in stream.items():
                if k == "tags" and isinstance(v, dict):
                    grouped[section_name]["tags"] = v.copy()
                else:
                    grouped[section_name][k] = v

    return grouped


def displayFFprobeMetadata(filePath:str) -> None:
    '''Displays Popup of Groupded Metadata from FFprobe'''

    metadata = getFFprobeMetadata(filePath)

    if metadata:
        grouped_metadata = groupFFprobeMetadata(metadata)
        logger.debug("Showing FFprobe MetaData Popup")
        DisplayPopup.display(grouped_metadata, title="File Metadata (FFprobe)", modal=False)
    else:
        logger.warning("No FFprobe metadata to display.")


def getProjectPresetDir(core, presetType:str) -> str:
    '''Returns Projects Preset Dir by Type'''

    projPipelineDir = core.projects.getPipelineFolder()
    return os.path.join(projPipelineDir, "SourceTab", "Presets", presetType.capitalize())


def getLocalPresetDir(presetType:str) -> str:
    '''Returns Local Preset Dir by Type'''

    pluginPath = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(pluginPath, "Presets", presetType.capitalize())


################################################
#################    PRESETS    ################

def getExtFromType(pType:str) -> str:
    '''Returns Preset File Extension by Type'''

    if pType == "proxy":
        ext = ".p_preset"
    elif pType == "metadata":
        ext = ".m_preset"
    else:
        ext = ""

    return ext


def importPreset(core, pType:str, local:bool=False) -> dict | None:
    '''Import Preset from File'''

    presetDir = None
    presetExt = getExtFromType(pType)

    if local:
        #   Get Local Preset Dir for Explorer
        presetDir = getLocalPresetDir(pType)
    
    #   Call Explorer to Select Preset to Import
    presetPath_source = explorerDialogue(
                            "Select Preset File",
                            dir = presetDir,
                            selDir = False,
                            filter = f"Preset Files (*{presetExt})"
                            )
    
    if not presetPath_source or not os.path.isfile(presetPath_source):
        return None
    
    try:
        #   Get Preset File Name and Make Project Destination Path
        _, presetName = os.path.split(presetPath_source)
        presetPath_dest = os.path.join(getProjectPresetDir(core, pType), presetName)

        #   If Exists Already Ask for Overwrite
        if os.path.exists(presetPath_dest):
            title = "Overwrite Preset"
            text = ("A Preset with the same name:\n\n"
                    f"{presetName}\n\n"
                    "exists in the Project Presets Directory.\n\n"
                    "Would you like to Overwrite?")
            buttons = ["Overwrite", "Cancel"]
            result = core.popupQuestion(text=text, title=title, buttons=buttons)

            #   Abort
            if result != "Overwrite":
                return None

        #   Copy from Source to Project Presets Dir
        shutil.copy(presetPath_source, presetPath_dest)

        #   Load Data and Add to Presets Dict
        importData = loadPreset(presetPath_dest)

        return importData

    except Exception as e:
        logger.warning(f"ERROR: Unable to Import Preset: {e}")



def exportPreset(core, pType:str, pName:str, pData:dict) -> bool:
    '''Export Preset to Selected Location'''

    presetExt = getExtFromType(pType)
    initialName = pName + presetExt   

    #   Open Explorer to Choose Destination Path
    presetPath = explorerDialogue(
                        "Save Preset File",
                        dir = initialName,
                        selDir = False,
                        save = True,
                        filter = f"Preset Files (*{presetExt})"
                    )

    if not presetPath:
        return False

    try:
        #   Replace Any Extension with '.*_preset'
        root, ext = os.path.splitext(presetPath)
        if ext.lower() != f"{presetExt.lower()}":
            presetPath = f"{root}{presetExt}"

        pData = {"name": pName,
                 "data": pData}

        #   Save Preset
        savePreset(core, pType, pName, pData, path=presetPath)
        return True

    except Exception as e:
        logger.warning(f"ERROR: Unable to Export Preset: {e}")
        return False


def loadPreset(presetPath:str) -> dict:
    '''Loads Preset Data from Preset File'''

    with open(presetPath, "r", encoding="utf-8") as f:
        return json.load(f)


def savePreset(core,
               pType:str,
               pName:str,
               pData:dict,
               project:bool=True,
               path:str=None,
               checkExists:bool=True
               ) -> None:
    
    '''Saves Preset by Type to Either Project or Local Plugin Dir'''

    presetExt = getExtFromType(pType)
    if not presetExt or presetExt == "":
        return

    #   Create Preset File Name with Extension
    presetName = f"{pName}{presetExt}"

    #   Saves to Project Presets Dir
    if project:
        projPipelineDir = getProjectPresetDir(core, pType)
        presetPath = os.path.join(projPipelineDir, presetName)

    #   Saves to Local Plugin Presets Dir
    else:
        localPresetDir = getLocalPresetDir(pType)
        presetPath = os.path.join(localPresetDir, presetName)

    #   Saves to Passed Path
    if path:
        presetPath = path

    #   Popup Question if Exists
    if os.path.exists(presetPath) and checkExists:
        title = "Preset Exists!"
        msg = ("A Preset already exists with the name:\n\n"
                f"     {presetName}\n\n"
                "Would you like to Overwrite the Preset?")
        buttons = ["Overwrite", "Cancel"]
        result = core.popupQuestion(text=msg, title=title, buttons=buttons)
        if result != "Overwrite":
            return

    #   Write Preset to Applicable Presets Dir
    try:
        with open(presetPath, "w", encoding="utf-8") as f:
            json.dump(pData, f, indent=4, ensure_ascii=False)

        logger.debug(f"Preset'{presetName}' Saved.")

    except Exception as e:
        logger.warning(f"ERROR:  Failed to Save Preset: {e}")


def deletePreset(core, pType:str, pName:str) -> None:
    '''Delete Preset by Type from Project Preset Dir'''

    presetExt = getExtFromType(pType)
    if not presetExt or presetExt == "":
        return

    #   Create Preset File Name with Extension
    presetName = f"{pName}{presetExt}"

    #   Generate Preset Path
    projPipelineDir = getProjectPresetDir(core, pType)
    presetPath = os.path.join(projPipelineDir, presetName)

    #   Attempt to Delete Preset
    if os.path.exists(presetPath):
        try:
            os.remove(presetPath)
            logger.debug(f"Removed Preset: {presetName}")

        except Exception as e:
            msg = f"ERROR: Unable to Remove Preset: {e}"
            logger.warning(msg)
            core.popup(msg)

    else:
        logger.warning(f"ERROR: Preset '{presetName} does not appear to Exist in the Project")

