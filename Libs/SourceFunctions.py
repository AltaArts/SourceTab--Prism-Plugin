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
#           ########### PLUGIN
#           by Joshua Breckeen
#                Alta Arts
#
#   This PlugIn adds an additional tab to the Prism Settings menu to ##########################
#   allow a user to choose a directory that contains scene presets.###############################
#
        #       TODO


####################################################



import os
import sys
import logging


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
sys.path.append(uiPath)

from PrismUtils.Decorators import err_catcher


from SourceFunctions_ui import Ui_w_sourceFunctions

from PopupWindows import NamingPopup, ProxyPopup


logger = logging.getLogger(__name__)


class SourceFunctions(QWidget, Ui_w_sourceFunctions):
    def __init__(self, core, origin, parent=None):
        super(SourceFunctions, self).__init__(parent)

        self.core = core
        self.sourceBrowser = origin

        self.proxyNameMap = {
            "copy": "Copy Proxys",
            "generate": "Generate Proxys",
            "missing": "Generate Missing Proxys"
            }

        #   Setup UI from Ui_w_sourceFunctions
        self.setupUi(self)

        self.configureUI()
        self.connections()

        self.updateUI()


    @err_catcher(name=__name__)
    def connections(self):
        self.b_openDestDir.clicked.connect(lambda: self.openInExplorer(self.sourceBrowser.le_destPath.text()))
        self.b_ovr_config_proxy.clicked.connect(self.configProxy)
        self.b_ovr_config_fileNaming.clicked.connect(self.configFileNaming)
        self.b_ovr_config_metadata.clicked.connect(self.configMetadata)


    @err_catcher(name=__name__)
    def configureUI(self):
        configIcon = self.sourceBrowser.getIconFromPath(os.path.join(uiPath, "Icons", "configure.png"))

        self.b_ovr_config_fileNaming.setIcon(configIcon)
        self.b_ovr_config_proxy.setIcon(configIcon)
        self.b_ovr_config_metadata.setIcon(configIcon)

        self.b_ovr_config_fileNaming.setEnabled(self.chb_ovr_fileNaming.isChecked())
        self.b_ovr_config_proxy.setEnabled(self.chb_ovr_proxy.isChecked())
        self.b_ovr_config_metadata.setEnabled(self.chb_ovr_metadata.isChecked())


    @err_catcher(name=__name__)
    def updateUI(self):
        #   Configure Proxy UI
        proxyEnabled = self.sourceBrowser.proxyEnabled

        #   If Proxy Enabled, Add Mode and Settings to UI
        if proxyEnabled:
            proxyMode = self.sourceBrowser.proxyMode
            #   Get UI Mode String
            proxyModeStr = self.proxyNameMap.get(proxyMode, "")
            #   Add Mode String
            proxyDisplayStr = proxyModeStr

            #   If Proxy Generation
            if proxyMode in ["generate", "missing"]:
                #   Get Proxy Settings
                pData = self.sourceBrowser.proxySettings
                #   If Exists, Add Settings to UI
                if pData:
                    presetStr = f"({pData['proxyPreset']} - {pData['proxyScale']})"
                    proxyDisplayStr = f"{proxyModeStr}   {presetStr}"

        #   Add Disabled to UI
        else:
            proxyDisplayStr = "DISABLED"

        self.l_proxyMode.setText(proxyDisplayStr)
        self.l_proxyMode.setEnabled(proxyEnabled)

        #   Configure File Name Mods UI
        fileNamingEnabled = self.chb_ovr_fileNaming.isChecked()

        #   If Enabled, Add to UI
        if fileNamingEnabled:
            numMods = f"{str(len(self.sourceBrowser.nameMods))} Modifiers"

        #   Add Disabled to UI
        else:
            numMods = "DISABLED"

        self.l_enabledNameMods.setText(numMods)
        self.l_enabledNameMods.setEnabled(fileNamingEnabled)


    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        self.sourceBrowser.openInExplorer(os.path.normpath(path))


    #   Opens File Naming Window to Configure
    @err_catcher(name=__name__)
    def configFileNaming(self):
        destList = self.sourceBrowser.tw_destination
        row_count = destList.rowCount()

        #   If there is only the Blank Entry Use EXAMPLE
        if row_count < 2:
            fileName = "EXAMPLEFILENAME"
        
        #   Get the First File's Basename
        else:
            fileItem = self.sourceBrowser.tw_destination.cellWidget(0, 0)
            filePath = fileItem.getSource_mainfilePath()
            fileName = os.path.basename(filePath)

        #   Call Popup and pass Basename and Existing Modifiers
        namePopup = NamingPopup(self.core, fileName, mods=self.sourceBrowser.nameMods)
        namePopup.exec_()

        #   If User Clicked Apply
        if namePopup.result == "Apply":
            #   Clear Mods List
            self.sourceBrowser.nameMods = []
            #   Populate Mod List with Mods from Popup
            for mod_instance, _ in namePopup.activeMods:
                mod_data = {
                    "mod_type": mod_instance.mod_name,
                    "enabled": mod_instance.isEnabled,
                    "settings": mod_instance.getSettings()
                }
                self.sourceBrowser.nameMods.append(mod_data)
            
            #   Refresh List
            self.sourceBrowser.refreshDestItems(restoreSelection=True)
            #   Save Mods to Project Settings
            self.sourceBrowser.plugin.saveSettings(key="nameMods")


    @err_catcher(name=__name__)
    def configProxy(self):
        #   Get Settings
        pData = {
            "proxyMode": self.sourceBrowser.proxyMode,
            "proxySettings": self.sourceBrowser.proxySettings
        }

        #   Call Popup
        proxyPopup = ProxyPopup(self.core, self, pData)
        proxyPopup.exec_()

        if proxyPopup.result == "Apply":
            self.sourceBrowser.proxyMode = proxyPopup.getProxyMode()
            self.sourceBrowser.proxySettings = proxyPopup.getProxySettings()
            self.updateUI()

            self.sourceBrowser.plugin.saveSettings(key="proxyPresets")



    @err_catcher(name=__name__)
    def configMetadata(self):
        self.core.popup("Configureing Metadata Not Yet Implemented")