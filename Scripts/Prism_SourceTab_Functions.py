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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

pluginPath = os.path.dirname(os.path.dirname(__file__))                              #   NEEDED ???
sys.path.append(pluginPath)
sys.path.append(os.path.join(pluginPath, "Libs"))

SETTINGS_FILE = os.path.join(pluginPath, "settings.json")

import SourceBrowser as SourceBrowser


class Prism_SourceTab_Functions(object):
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin

        self.sourceBrowser = None

        #   Only add Tab in Standalone
        if self.core.appPlugin.pluginName == "Standalone":
            self.core.registerCallback("postInitialize", self.postInitialize, plugin=self)   
            self.core.registerCallback("onProjectBrowserStartup", self.sourceBrowserStartup, plugin=self)   
            self.core.registerCallback("onProjectBrowserClose", self.saveSettings, plugin=self,
                                                                                                # priority=40
                                                                                                )


    # if returns true, the plugin will be loaded by Prism
    @err_catcher(name=__name__)
    def isActive(self):
        return True
    

    @err_catcher(name=__name__)
    def sourceBrowserStartup(self, origin):
        self.pbMenu = origin


    @err_catcher(name=__name__)
    def postInitialize(self):
        self.pb = self.core.pb

        #   Creates Source Browser
        self.sourceBrowser = SourceBrowser.SourceBrowser(self, core=self.core, projectBrowser=self.pb, refresh=False)
        self.pbMenu.addTab("Source", self.sourceBrowser, position=0)


    #   Loads Saved SourceTab Settings
    @err_catcher(name=__name__)
    def loadSettings(self):
        if not os.path.exists(SETTINGS_FILE):
            self.createSettings()

        with open(SETTINGS_FILE, 'r') as file:
            sData = json.load(file)

            if sData:
                return sData


    #   Creates the Settings File
    @err_catcher(name=__name__)
    def createSettings(self):
        default_data = self.getDefaultSettings()
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(default_data, f, indent=4)

        except Exception as e:
            print(f"Failed to write settings file: {e}")


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
                    "copyProxy": False
                },
                "settings": {
                    "max_thumbThreads": 12,
                    "max_copyThreads": 6,
                    "size_copyChunk": 1,
                    "updateInterval": 1,
                    "useCompletePopup": True,
                    "useCompleteSound": True,
                    "useTransferReport": True
                }
            }

        return sData


    #   Called from PB Close Callback
    @err_catcher(name=__name__)
    def saveSettings(self, origin, key=None, data=None):
        #   Gets Current Settings
        sData = self.loadSettings()

        #   If the SourceBrowser has been Loaded
        if self.sourceBrowser:
            #   Gets and Updates SourceBrowser UI Settings
            tabSettings = self.sourceBrowser.getTabSettings()
            sData["tabSettings"] = tabSettings

        if key:
            sData[key] = data

        with open(SETTINGS_FILE, "w") as file:
            json.dump(sData, file, indent=4)
