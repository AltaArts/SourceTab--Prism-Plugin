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

import os
import sys
import json
import logging
from functools import partial


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
        # Create the source tab widget
        projectSettings.w_sourceTab = QWidget()
        lo_sourceTab = QGridLayout()
        projectSettings.w_sourceTab.setLayout(lo_sourceTab)

        # Horizontal Layout for the configuration area (no splitter now)
        projectSettings.horizontalLayout = QHBoxLayout()
        projectSettings.horizontalLayout.setObjectName("horizontalLayout")

        # Config widget that will contain the form
        projectSettings.w_config = QWidget()
        projectSettings.w_config.setObjectName("w_config")

        # Size Policy and Layout Setup
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        projectSettings.w_config.setSizePolicy(sizePolicy)
        projectSettings.lo_sourceTabOptions = QVBoxLayout(projectSettings.w_config)
        projectSettings.lo_sourceTabOptions.setObjectName("lo_sourceTabOptions")
        projectSettings.lo_sourceTabOptions.setContentsMargins(0, 0, 0, 0)

        # Maximum Thumbnail Threads
        projectSettings.lo_thumbThreads = QHBoxLayout()
        projectSettings.l_thumbThreads = QLabel("Maximum Thumbnail Threads", projectSettings.w_config)
        projectSettings.sb_thumbThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_thumbThreads.setMinimum(1)
        projectSettings.lo_thumbThreads.addWidget(projectSettings.l_thumbThreads)
        projectSettings.lo_thumbThreads.addStretch()
        projectSettings.lo_thumbThreads.addWidget(projectSettings.sb_thumbThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_thumbThreads)

        # Maximum Transfer Threads
        projectSettings.lo_copyThreads = QHBoxLayout()
        projectSettings.l_copyThreads = QLabel("Maximum Transfer Threads", projectSettings.w_config)
        projectSettings.sb_copyThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_copyThreads.setMinimum(1)
        projectSettings.lo_copyThreads.addWidget(projectSettings.l_copyThreads)
        projectSettings.lo_copyThreads.addStretch()
        projectSettings.lo_copyThreads.addWidget(projectSettings.sb_copyThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_copyThreads)

        # Transfer Chunk Size (megabytes)
        projectSettings.lo_copyChunks = QHBoxLayout()
        projectSettings.l_copyChunks = QLabel("Transfer Chunk Size (megabytes)", projectSettings.w_config)
        projectSettings.sb_copyChunks = QSpinBox(projectSettings.w_config)
        projectSettings.sb_copyChunks.setMinimum(1)
        projectSettings.lo_copyChunks.addWidget(projectSettings.l_copyChunks)
        projectSettings.lo_copyChunks.addStretch()
        projectSettings.lo_copyChunks.addWidget(projectSettings.sb_copyChunks)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_copyChunks)

        # Maximum Proxy Generation Threads
        projectSettings.lo_proxyThreads = QHBoxLayout()
        projectSettings.l_proxyThreads = QLabel("Maximum Proxy Generation Threads", projectSettings.w_config)
        projectSettings.sb_proxyThreads = QSpinBox(projectSettings.w_config)
        projectSettings.sb_proxyThreads.setMinimum(1)
        projectSettings.lo_proxyThreads.addWidget(projectSettings.l_proxyThreads)
        projectSettings.lo_proxyThreads.addStretch()
        projectSettings.lo_proxyThreads.addWidget(projectSettings.sb_proxyThreads)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_proxyThreads)

        # Progress Bars Update Rate (seconds)
        projectSettings.lo_progUpdateRate = QHBoxLayout()
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

        # Completion Popup options
        projectSettings.lo_completePopup = QHBoxLayout()
        projectSettings.chb_showPopup = QCheckBox("Show Completion Popup", projectSettings.w_config)
        projectSettings.chb_playSound = QCheckBox("Play Completion Sound", projectSettings.w_config)
        projectSettings.lo_completePopup.addWidget(projectSettings.chb_showPopup)
        projectSettings.lo_completePopup.addWidget(projectSettings.chb_playSound)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_completePopup)

        # Transfer Report Generation option
        projectSettings.lo_transferReport = QHBoxLayout()
        projectSettings.chb_useTransferReport = QCheckBox("Generate Transfer Report on Completion", projectSettings.w_config)
        projectSettings.lo_transferReport.addWidget(projectSettings.chb_useTransferReport)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_transferReport)

        # Custom Icon path option
        projectSettings.lo_customIcon = QHBoxLayout()
        projectSettings.chb_useCustomIcon = QCheckBox("Custom Icon", projectSettings.w_config)
        projectSettings.le_customIconPath = QLineEdit(projectSettings.w_config)
        projectSettings.lo_customIcon.addWidget(projectSettings.chb_useCustomIcon)
        projectSettings.lo_customIcon.addWidget(projectSettings.le_customIconPath)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_customIcon)

        # View Lut option
        projectSettings.lo_viewLut = QHBoxLayout()
        projectSettings.chb_useViewLut = QCheckBox("Use View Lut Presets:", projectSettings.w_config)
        projectSettings.b_configureOcioPreets = QPushButton("Configure OCIO Presets", projectSettings.w_config)
        projectSettings.lo_viewLut.addWidget(projectSettings.chb_useViewLut)
        projectSettings.lo_viewLut.addStretch()
        projectSettings.lo_viewLut.addWidget(projectSettings.b_configureOcioPreets)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_viewLut)

        # Custom Thumbnail Path option
        projectSettings.lo_customThumbPath = QHBoxLayout()
        projectSettings.chb_useCustomThumbPath = QCheckBox("Use Custom Thumbnail Path", projectSettings.w_config)
        projectSettings.le_customThumbPath = QLineEdit(projectSettings.w_config)
        projectSettings.lo_customThumbPath.addWidget(projectSettings.chb_useCustomThumbPath)
        projectSettings.lo_customThumbPath.addWidget(projectSettings.le_customThumbPath)
        projectSettings.lo_sourceTabOptions.addLayout(projectSettings.lo_customThumbPath)

        projectSettings.lo_sourceTabOptions.addStretch()

        # Finalize the layout (no splitter)
        projectSettings.horizontalLayout.addWidget(projectSettings.w_config)

        # Add the layout to the source tab
        lo_sourceTab.addLayout(projectSettings.horizontalLayout, 0, 0)

        # Add the tab to the projectSettings
        projectSettings.addTab(projectSettings.w_sourceTab, "SourceTab")

        # Connect slots for the UI components
        QMetaObject.connectSlotsByName(projectSettings)

        #   CONNECTIONS
        projectSettings.b_configureOcioPreets.clicked.connect(self.openOcioPresets)


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

            if "useViewLut" in sData:
                origin.chb_useViewLut.setChecked(sData["useViewLut"])						

            if "useCustomThumbPath" in sData:
                origin.chb_useCustomThumbPath.setChecked(sData["useCustomThumbPath"])

            if "customThumbPath" in sData:
                origin.le_customThumbPath.setText(sData["customThumbPath"])


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
            "useViewLut": origin.chb_useViewLut.isChecked(),
            "useCustomThumbPath": origin.chb_useCustomThumbPath.isChecked(),
            "customThumbPath": origin.le_customThumbPath.text().strip().strip('\'"')
            }


        settings["sourceTab"]["globals"] = sData


    @err_catcher(name=__name__)
    def saveSettings(self, key=None, data=None, *args, **kwargs):                       #   TODO - ALSO SAVE TO MAIN PRISM SETTINGS.JSON
        if key == "tabSettings":
            tData = {}

            tData["playerEnabled"] = self.sourceBrowser.chb_enablePlayer.isChecked()
            tData["preferProxies"] = self.sourceBrowser.chb_preferProxies.isChecked()

            functs = self.sourceBrowser.sourceFuncts
            tData["enable_fileNaming"] = functs.chb_ovr_fileNaming.isChecked()
            tData["enable_Proxy"] = functs.chb_ovr_proxy.isChecked()
            tData["enable_metadata"] = functs.chb_ovr_metadata.isChecked()
            tData["enable_overwrite"] = functs.chb_overwrite.isChecked()
            tData["enable_copyProxy"] = functs.chb_copyProxy.isChecked()
            tData["enable_generateProxy"] = functs.chb_generateProxy.isChecked()

            self.core.setConfig(cat="sourceTab", param="tabSettings", val=tData, config="project")


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
    def getDefaultSettings(self):
        sData = {
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
                    "@MAINFILEDIR@\\..\\proxys\\@MAINFILENAME@"
                    ],
                "tabSettings": {
                    "playerEnabled": True,
                    "preferProxies": True,
                    "enable_fileNaming": False,
                    "enable_Proxy": False,
                    "enable_metadata": False,
                    "enable_overwrite": False,
                    "enable_copyProxy": False,
                    "enable_generateProxy": False
                },
                "globals": {
                    "max_thumbThreads": 6,
                    "max_copyThreads": 6,
                    "size_copyChunk": 1,
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
                ]
            }

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