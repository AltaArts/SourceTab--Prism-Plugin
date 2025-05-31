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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

pluginPath = os.path.dirname(os.path.dirname(__file__))                              #   NEEDED ???
sys.path.append(pluginPath)
sys.path.append(os.path.join(pluginPath, "Libs"))


import SourceBrowser as SourceBrowser
from PopupWindows import OcioConfigPopup


logger = logging.getLogger(__name__)


class Prism_SourceTab_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.sourceBrowser = None

        #	Register callbacks
        try:
            callbacks = [
                        ("projectBrowser_loadUI", self.projectBrowser_loadUI, 20),
                        ("onProjectBrowserClose", lambda *args, **kwargs: self.saveSettings(key="tabSettings"), 40),
                        ("projectSettings_loadUI", self.projectSettings_loadUI, 40),
                        ("preProjectSettingsLoad", self.preProjectSettingsLoad, 40),
                        ("preProjectSettingsSave", self.preProjectSettingsSave, 40),
                        ]

            # Iterate through the list to register callbacks
            for callback_name, method, priority in callbacks:
                self.core.registerCallback(callback_name, method, plugin=self.plugin, priority=priority)

            logger.debug("Registered callbacks")

        except Exception as e:
            logger.warning(f"ERROR: Registering callbacks failed:\n {e}")


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True


    #   Called from Callback when ProjectBrowser is Created
    @err_catcher(name=__name__)
    def projectBrowser_loadUI(self, pb):
        #   Creates Source Browser
        self.sourceBrowser = SourceBrowser.SourceBrowser(self, core=self.core, projectBrowser=pb, refresh=False)

        #   Adds Source Tab to Project Browser
        pb.addTab("Source", self.sourceBrowser, position=0)


    #   From Callback to Load Settings UI
    @err_catcher(name=__name__)
    def projectSettings_loadUI(self, origin):
        self.addUiToProjectSettings(origin)


    #   Creates Project Settings Tab UI
    @err_catcher(name=__name__)
    def addUiToProjectSettings(self, projectSettings):
        #   Simple Line Generator
        def separatorLine(title=None):
            box = QWidget()
            layout = QVBoxLayout(box)
            layout.setContentsMargins(0, 10, 0, 0)
            layout.setSpacing(2)
            
            if title:
                layout.addWidget(QLabel(f"{title}"))
            
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #465A78;")
            layout.addWidget(line)

            return box

        #   Create the SourceTab Widget
        projectSettings.w_sourceTab = QWidget()
        lo_sourceTab = QGridLayout()
        projectSettings.w_sourceTab.setLayout(lo_sourceTab)

        #   Layout for the Settings
        projectSettings.horizontalLayout = QHBoxLayout()
        projectSettings.horizontalLayout.setObjectName("horizontalLayout")

        #   Config widget that will contain the form
        projectSettings.w_config = QWidget()
        projectSettings.w_config.setObjectName("w_config")

        #   Size Policy and Layout Setup
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        projectSettings.w_config.setSizePolicy(sizePolicy)
        projectSettings.lo_sourceTabOptions = QVBoxLayout(projectSettings.w_config)
        projectSettings.lo_sourceTabOptions.setObjectName("lo_sourceTabOptions")
        projectSettings.lo_sourceTabOptions.setContentsMargins(0, 0, 0, 0)

        projectSettings.lo_sourceTabOptions.addWidget(separatorLine("Performance / Processes"))

        #   Maximum Thumbnail Threads
        projectSettings.lo_thumbThreads = QHBoxLayout()
        projectSettings.lo_thumbThreads.setContentsMargins(50, 0, 20, 0)
        projectSettings.l_thumbThreads = QLabel("Maximum Parallel Thumbnail Processes", projectSettings.w_config)
        projectSettings.sb_thumbThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_thumbThreads.setMinimum(1)
        projectSettings.lo_thumbThreads.addWidget(projectSettings.l_thumbThreads)
        projectSettings.lo_thumbThreads.addStretch()
        projectSettings.lo_thumbThreads.addWidget(projectSettings.sb_thumbThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_thumbThreads)

        #   Maximum Transfer Threads
        projectSettings.lo_copyThreads = QHBoxLayout()
        projectSettings.lo_copyThreads.setContentsMargins(50, 0, 20, 0)
        projectSettings.l_copyThreads = QLabel("Maximum Parallel Transfer Processes", projectSettings.w_config)
        projectSettings.sb_copyThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_copyThreads.setMinimum(1)
        projectSettings.lo_copyThreads.addWidget(projectSettings.l_copyThreads)
        projectSettings.lo_copyThreads.addStretch()
        projectSettings.lo_copyThreads.addWidget(projectSettings.sb_copyThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_copyThreads)

        #   Transfer Chunk Size
        projectSettings.lo_copyChunks = QHBoxLayout()
        projectSettings.lo_copyChunks.setContentsMargins(50, 0, 20, 0)
        projectSettings.l_copyChunks = QLabel("Transfer Chunk Size (megabytes)", projectSettings.w_config)
        projectSettings.sb_copyChunks = QSpinBox(projectSettings.w_config)
        projectSettings.sb_copyChunks.setMinimum(1)
        projectSettings.lo_copyChunks.addWidget(projectSettings.l_copyChunks)
        projectSettings.lo_copyChunks.addStretch()
        projectSettings.lo_copyChunks.addWidget(projectSettings.sb_copyChunks)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_copyChunks)

        #   Maximum Proxy Generation Threads
        projectSettings.lo_proxyThreads = QHBoxLayout()
        projectSettings.lo_proxyThreads.setContentsMargins(50, 0, 20, 0)
        projectSettings.l_proxyThreads = QLabel("Maximum Parallel Proxy Generation Processes", projectSettings.w_config)
        projectSettings.sb_proxyThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_proxyThreads.setMinimum(1)
        projectSettings.lo_proxyThreads.addWidget(projectSettings.l_proxyThreads)
        projectSettings.lo_proxyThreads.addStretch()
        projectSettings.lo_proxyThreads.addWidget(projectSettings.sb_proxyThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_proxyThreads)

        projectSettings.lo_sourceTabOptions.addWidget(separatorLine("Progress Bar"))

        #   Progress Bars Update Rate
        projectSettings.lo_progUpdateRate = QHBoxLayout()
        projectSettings.lo_progUpdateRate.setContentsMargins(50, 0, 20, 0)
        projectSettings.l_progUpdateRate = QLabel("Progress Bars Update Rate (seconds)", projectSettings.w_config)
        projectSettings.sp_progUpdateRate = QDoubleSpinBox(projectSettings.w_config)
        projectSettings.sp_progUpdateRate.setDecimals(1)
        projectSettings.sp_progUpdateRate.setMinimum(0.1)
        projectSettings.sp_progUpdateRate.setSingleStep(0.1)
        projectSettings.sp_progUpdateRate.setValue(0.5)
        projectSettings.lo_progUpdateRate.addWidget(projectSettings.l_progUpdateRate)
        projectSettings.lo_progUpdateRate.addStretch()
        projectSettings.lo_progUpdateRate.addWidget(projectSettings.sp_progUpdateRate)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_progUpdateRate)

        projectSettings.lo_sourceTabOptions.addWidget(separatorLine("Completion / Report"))

        #   Completion Popup
        projectSettings.lo_completePopup = QHBoxLayout()
        projectSettings.lo_completePopup.setContentsMargins(50, 0, 20, 0)
        projectSettings.chb_showPopup = QCheckBox("Show Completion Popup", projectSettings.w_config)
        projectSettings.chb_playSound = QCheckBox("Play Completion Sound", projectSettings.w_config)
        projectSettings.lo_completePopup.addWidget(projectSettings.chb_showPopup)
        projectSettings.lo_completePopup.addWidget(projectSettings.chb_playSound)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_completePopup)

        #   Transfer Report
        projectSettings.lo_transferReport = QHBoxLayout()
        projectSettings.lo_transferReport.setContentsMargins(50, 0, 20, 0)
        projectSettings.chb_useTransferReport = QCheckBox("Generate Transfer Report on Completion", projectSettings.w_config)
        projectSettings.lo_transferReport.addWidget(projectSettings.chb_useTransferReport)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_transferReport)

        projectSettings.lo_sourceTabOptions.addWidget(separatorLine("Misc"))

        #   Custom Icon
        projectSettings.lo_customIcon = QHBoxLayout()
        projectSettings.lo_customIcon.setContentsMargins(50, 0, 20, 0)
        projectSettings.chb_useCustomIcon = QCheckBox("Custom Icon", projectSettings.w_config)
        projectSettings.le_customIconPath = QLineEdit(projectSettings.w_config)
        projectSettings.lo_customIcon.addWidget(projectSettings.chb_useCustomIcon)
        projectSettings.lo_customIcon.addWidget(projectSettings.le_customIconPath)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_customIcon)

        # #   View Lut                                                                      #   TODO - IMPLEMENT
        # projectSettings.lo_viewLut = QHBoxLayout()
        # projectSettings.chb_useViewLut = QCheckBox("Use View Lut Presets:", projectSettings.w_config)
        # projectSettings.b_configureOcioPreets = QPushButton("Configure OCIO Presets", projectSettings.w_config)
        # projectSettings.lo_viewLut.addWidget(projectSettings.chb_useViewLut)
        # projectSettings.lo_viewLut.addStretch()
        # projectSettings.lo_viewLut.addWidget(projectSettings.b_configureOcioPreets)
        # projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_viewLut)

        # #   Custom Thumbnail Path option                                                      #   TODO - DO WE WANT THIS ???
        # projectSettings.lo_customThumbPath = QHBoxLayout()
        # projectSettings.chb_useCustomThumbPath = QCheckBox("Use Custom Thumbnail Path", projectSettings.w_config)
        # projectSettings.le_customThumbPath = QLineEdit(projectSettings.w_config)
        # projectSettings.lo_customThumbPath.addWidget(projectSettings.chb_useCustomThumbPath)
        # projectSettings.lo_customThumbPath.addWidget(projectSettings.le_customThumbPath)
        # projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_customThumbPath)

        projectSettings.lo_sourceTabOptions.addStretch()

        #   Finalize the layout (no splitter)
        projectSettings.horizontalLayout.addWidget(projectSettings.w_config)

        #   Add the layout to the source tab
        lo_sourceTab.addLayout(projectSettings.horizontalLayout, 0, 0)

        #   Add the tab to the projectSettings
        projectSettings.addTab(projectSettings.w_sourceTab, "SourceTab")

        #   Connect slots for the UI components
        QMetaObject.connectSlotsByName(projectSettings)

        #   TOOLTIPS
        tip = ("Maximum Seperate Processes to use for Media Thumbnail generation.\n"
               "  note:  too many threads tends to hang the ffmpeg process.\n\n"
               "    (default = 6)")
        projectSettings.l_thumbThreads.setToolTip(tip)
        projectSettings.sb_thumbThreads.setToolTip(tip)

        tip = ("Maximum Seperate Processes to use for the File Transfer (copying).\n"
               "The system's optimum setting will depend on processor/disk/network speeds.\n\n"
               "    (default = 6)")
        projectSettings.l_copyThreads.setToolTip(tip)
        projectSettings.sb_copyThreads.setToolTip(tip)

        tip = ("Size of each Packet used in the Transfer.\n"
               "The system's optimum setting will depend on processor/ram/disk/network speeds.\n\n"
               "    (default = 2)")
        projectSettings.l_copyChunks.setToolTip(tip)
        projectSettings.sb_copyChunks.setToolTip(tip)

        tip = ("Maximum Seperate Processes for Proxy Generation.\n"
               "This plugin uses ffmpeg for Proxy Generation and ffmpeg is multi-threaded by default.\n"
               "This means each process should be using all available processor cores,\n"
               "thus higher settings do not tend to speed up the generation.\n\n"
               "    (default = 2)")
        projectSettings.l_proxyThreads.setToolTip(tip)
        projectSettings.sb_proxyThreads.setToolTip(tip)

        tip = ("Time in seconds for each UI progress update.\n"
               "Too low a rate (high frequency) may slow the UI.\n\n"
               "    (default = 1.0)")
        projectSettings.l_progUpdateRate.setToolTip(tip)
        projectSettings.sp_progUpdateRate.setToolTip(tip)

        projectSettings.chb_showPopup.setToolTip("Enable the Completion popup Window")
        projectSettings.chb_playSound.setToolTip("Enable the Completion Audio Alert")

        tip = ("Enable the Generation of the Completion Report .pdf file.\n\n"
               "The report will be generated and saved in the transfer destination\n"
               "directory, and contains the transfer data and stats.")
        projectSettings.chb_useTransferReport.setToolTip(tip)

        tip = ("Filepath to a custom file to be used as an icon in the Completion Report.\n"
               "This can be any 'normal' image file (.png, .jpg, .tif, .bmp).\n\n"
               "   (leave blank to use the default Prism Icon)")
        projectSettings.chb_useCustomIcon.setToolTip(tip)
        projectSettings.le_customIconPath.setToolTip(tip)



        #   CONNECTIONS
        # projectSettings.b_configureOcioPreets.clicked.connect(self.openOcioPresets)


    #   Gets SourceTab Settings when Prism Project Settings Loads
    @err_catcher(name=__name__)
    def preProjectSettingsLoad(self, origin, settings):
        if not settings:
            return
        
        if "sourceTab" in settings:
            sData = settings["sourceTab"]["globals"]

            if "max_thumbThreads" in sData:
                origin.sb_thumbThreads.setValue(sData["max_thumbThreads"])

            if "max_copyThreads" in sData:
                origin.sb_copyThreads.setValue(sData["max_copyThreads"])

            if "size_copyChunk" in sData:
                origin.sb_copyChunks.setValue(sData["size_copyChunk"])	

            if "max_proxyThreads" in sData:
                origin.sb_proxyThreads.setValue(sData["max_proxyThreads"])

            if "updateInterval" in sData:
                origin.sp_progUpdateRate.setValue(sData["updateInterval"])

            if "useCompletePopup" in sData:
                origin.chb_showPopup.setChecked(sData["useCompletePopup"])

            if "useCompleteSound" in sData:
                origin.chb_playSound.setChecked(sData["useCompleteSound"])

            if "useTransferReport" in sData:
                origin.chb_useTransferReport.setChecked(sData["useTransferReport"])	

            if "useCustomIcon" in sData:
                origin.chb_useCustomIcon.setChecked(sData["useCustomIcon"])

            if "customIconPath" in sData:
                origin.le_customIconPath.setText(sData["customIconPath"])

            # if "useViewLut" in sData:
            #     origin.chb_useViewLut.setChecked(sData["useViewLut"])						

            # if "useCustomThumbPath" in sData:
            #     origin.chb_useCustomThumbPath.setChecked(sData["useCustomThumbPath"])

            # if "customThumbPath" in sData:
            #     origin.le_customThumbPath.setText(sData["customThumbPath"])


    #   Saves SourceTab Settings when Prism Project Settings Saves
    @err_catcher(name=__name__)
    def preProjectSettingsSave(self, origin, settings):
        if "sourceTab" not in settings:
            settings["sourceTab"] = {}

        sData = {
            "max_thumbThreads": origin.sb_thumbThreads.value(),
            "max_copyThreads": origin.sb_copyThreads.value(),
            "size_copyChunk": origin.sb_copyChunks.value(),
            "max_proxyThreads": origin.sb_proxyThreads.value(),
            "updateInterval": origin.sp_progUpdateRate.value(),
            "useCompletePopup": origin.chb_showPopup.isChecked(),
            "useCompleteSound": origin.chb_playSound.isChecked(),
            "useTransferReport": origin.chb_useTransferReport.isChecked(),
            "useCustomIcon": origin.chb_useCustomIcon.isChecked(),
            "customIconPath": origin.le_customIconPath.text().strip().strip('\'"'),
            # "useViewLut": origin.chb_useViewLut.isChecked(),
            # "useCustomThumbPath": origin.chb_useCustomThumbPath.isChecked(),
            # "customThumbPath": origin.le_customThumbPath.text().strip().strip('\'"')
            }

        settings["sourceTab"]["globals"] = sData


    @err_catcher(name=__name__)
    def saveSettings(self, key=None, data=None, *args, **kwargs):                       #   TODO - ALSO SAVE TO MAIN PRISM SETTINGS.JSON
        if key == "tabSettings":
            tData = {}

            tData["playerEnabled"] = self.sourceBrowser.chb_enablePlayer.isChecked()
            tData["preferProxies"] = self.sourceBrowser.chb_preferProxies.isChecked()
            tData["proxyMode"] = self.sourceBrowser.proxyMode

            functs = self.sourceBrowser.sourceFuncts
            tData["enable_proxy"] = functs.chb_ovr_proxy.isChecked()
            tData["enable_fileNaming"] = functs.chb_ovr_fileNaming.isChecked()
            tData["enable_metadata"] = functs.chb_ovr_metadata.isChecked()
            tData["enable_overwrite"] = functs.chb_overwrite.isChecked()

            self.core.setConfig(cat="sourceTab", param="tabSettings", val=tData, config="project")

        elif key == "proxySettings":
            pData = self.sourceBrowser.proxySettings
            self.core.setConfig(cat="sourceTab", param="proxySettings", val=pData, config="project")

        elif key == "proxySearch":
            self.core.setConfig(cat="sourceTab", param="proxySearch", val=data, config="project")

        elif key == "ffmpegPresets":
            self.core.setConfig(cat="sourceTab", param="ffmpegPresets", val=data, config="project")
            
        elif key == "nameMods":
            nData = self.sourceBrowser.nameMods
            self.core.setConfig(cat="sourceTab", param="activeNameMods", val=nData, config="project")


    #   Loads Saved SourceTab Settings
    @err_catcher(name=__name__)
    def loadSettings(self):
        sData = self.core.getConfig("sourceTab", config="project") 

        if sData and "globals" in sData:
            return sData

        else:
            sData = {}
            defaultData = self.getDefaultSettings()
            sData["sourceTab"] = defaultData
            self.core.setConfig("sourceTab", data=sData, config="project")
            return defaultData
    

    #   Default Settings File Data
    @err_catcher(name=__name__)
    def getDefaultSettings(self, key=None):
        sData = {
                "globals": {
                    "max_thumbThreads": 6,
                    "max_copyThreads": 6,
                    "size_copyChunk": 2,
                    "max_proxyThreads": 2,
                    "updateInterval": 1,
                    "useCompletePopup": True,
                    "useCompleteSound": True,
                    "useTransferReport": True,
                    "useCustomIcon": False,
                    "customIconPath": "", 
                    "useViewLut": False,
                    "useCustomThumbPath": False,
                    "customThumbPath": ""
                },
                "tabSettings": {
                    "playerEnabled": True,
                    "preferProxies": True,
                    "enable_proxy": False,
                    "proxyMode": "None",
                    "enable_fileNaming": False,
                    "enable_metadata": False,
                    "enable_overwrite": False
                },
                "proxySettings": {
                    "fallback_proxyDir": "\\proxy",
                    "ovr_proxyDir": "",
                },
                "activeNameMods":
                [],
                "proxySearch": [
                    "@MAINFILEDIR@\\proxy\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\pxy\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\proxies\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\proxys\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\proxy\\@MAINFILENAME@_proxy",
                    "@MAINFILEDIR@\\pxy\\@MAINFILENAME@_proxy",
                    "@MAINFILEDIR@\\proxies\\@MAINFILENAME@_proxy",
                    "@MAINFILEDIR@\\proxys\\@MAINFILENAME@_proxy",
                    "@MAINFILEDIR@\\@MAINFILENAME@_proxy",
                    "@MAINFILEDIR@\\..\\proxy\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\..\\pxys\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\..\\proxies\\@MAINFILENAME@",
                    "@MAINFILEDIR@\\..\\proxys\\@MAINFILENAME@",
                    "@MAINFILEDIR@_proxy\\@MAINFILENAME@"
                    ],
                "viewLutPresets": [
                    {
                    "name": "Linear to Rec70924",
                    "transform_input": "Rec709Linear",
                    "transform_output": "Rec70924",
                    "look": "None"
                    },
                    {
                    "name": "ACEScg to Rec70924",
                    "transform_input": "ACEScg",
                    "transform_output": "Rec70924",
                    "look": "None"
                    },
                ],
                "ffmpegPresets": {
                    "Fast H.264 Proxy": {
                        "Description": "Quick and small proxy, good for review or offline editing",
                        "Video_Parameters": "-c:v libx264 -preset veryfast -crf 28 -pix_fmt yuv420p",
                        "Audio_Parameters": "-c:a aac -b:a 128k",
                        "Extension": ".mp4",
                        "Multiplier": 0.1
                    },
                    "ProRes Proxy": {
                        "Description": "Edit-friendly proxy for high-performance workflows (large size)",
                        "Video_Parameters": "-c:v prores_ks -profile:v 0 -pix_fmt yuv422p10le",
                        "Audio_Parameters": "-c:a copy",
                        "Extension": ".mov",
                        "Multiplier": 0.2
                    },
                    "DNxHD 36M Proxy": {
                        "Description": "Avid-style proxy with intra-frame compression (36 Mbps)",
                        "Video_Parameters": "-c:v dnxhd -b:v 36M -pix_fmt yuv422p",
                        "Audio_Parameters": "-c:a pcm_s16le",
                        "Extension": ".mov",
                        "Multiplier": 0.3
                    },
                    "Ultra-Light Preview": {
                        "Description": "Low-res H.264 preview for web or quick review",
                        "Video_Parameters": "-c:v libx264 -preset ultrafast -crf 32 -pix_fmt yuv420p",
                        "Audio_Parameters": "-c:a aac -b:a 96k",
                        "Extension": ".mp4",
                        "Multiplier": 0.05
                    },
                    "Full-Res H.264": {
                        "Description": "Full-resolution H.264 transcode, good quality balance",
                        "Video_Parameters": "-c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p",
                        "Audio_Parameters": "-c:a aac -b:a 192k",
                        "Extension": ".mp4",
                        "Multiplier": 0.01
                    }
                }
            }

        #   Return Specific Key Default
        if key and key in sData:
            return sData[key]
        
        #   Return Entire Defaults Dict
        else:
            return sData
    


    #   Default Settings File Data
    @err_catcher(name=__name__)
    def openOcioPresets(self):
        sData = self.loadSettings()
        oData = sData["viewLutPresets"]

        OcioConfigPopup.display(self.core, oData)

        # mediaEx = self.core.getPlugin("MediaExtension")
        # entity = mediaEx

        # import inspect
        # print("########################")
        # print(f"{entity} > Type: {str(type(entity))}")
        # print("----")
        # methods = [func for func in dir(entity) if callable(getattr(entity, func)) and not func.startswith("__")]
        # for method in methods:
        #     func = getattr(entity, method)
        #     try:
        #         sig = inspect.signature(func)
        #         print(f"Method: {method}, Arguments: {sig}")
        #     except:
        #         print(f"Method: {method}")
        # for attribute_name, attribute in entity.__dict__.items():
        #     print(f"Attribute: {attribute_name} | {str(type(attribute))}")
        # print("########################")


        # ocio = mediaEx.browseOcioConfig(self)

        # self.core.popup(ocio)