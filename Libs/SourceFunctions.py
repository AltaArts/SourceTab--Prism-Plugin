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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
sys.path.append(uiPath)

from PrismUtils.Decorators import err_catcher


from SourceFunctions_ui import Ui_w_sourceFunctions

from PopupWindows import NamingPopup, ProxyPopup, MetadataEditor
import SourceTab_Utils as Utils


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
        
        self.setToolTips()
        self.configureUI()
        self.connectEvents()

        self.updateUI()

        logger.debug("Loaded Functions Panel")


    @err_catcher(name=__name__)
    def setToolTips(self):
        tip = ("Enable/Disable Proxy Handling\n"
               "(Proxy transfer / generation)")
        self.chb_ovr_proxy.setToolTip(tip)

        tip = "Open Proxy Settings"
        self.b_ovr_config_proxy.setToolTip(tip)

        tip = "Open Filename Modifiers Settings"
        self.b_ovr_config_fileNaming.setToolTip(tip)

        tip = "Open MetaData Settings"
        self.b_ovr_config_metadata.setToolTip(tip)

        tip = ("Enable/Disable Filename Modifiers\n"
               "(this affects the Transferred File Naming)")
        self.chb_ovr_fileNaming.setToolTip(tip)

        tip = ("Enable/Disable Metadata Genertion\n"
               "(this affects the Transferred File(s) Metatdata)")
        self.chb_ovr_metadata.setToolTip(tip)

        tip = ("Enable/Disable Detination File Overwriting\n"
               "(files with the same name in the Destination will be overwritten)")
        self.chb_overwrite.setToolTip(tip)

        tip = "Open Destination Directory in the os File Explorer"
        self.b_openDestDir.setToolTip(tip)

        tip = ("Start the File Transfer\n"
               "(this will lock the interface)")
        self.b_transfer_start.setToolTip(tip)

        tip = ("Pause the File Transfer\n\n"
               "This will pause the copying of files,\n"
               "but does not affect Proxy Generation.\n\n"
               "This will not survive after closing/reopening the Project Browser")
        self.b_transfer_pause.setToolTip(tip)

        tip = ("Resume the File Transfer")
        self.b_transfer_resume.setToolTip(tip)

        tip = ("Stop and Cancel the File Transfer\n\n"
               "Any unfinished partial transfers or Proxy\n"
               "generation will be removed")
        self.b_transfer_cancel.setToolTip(tip)

        tip = ("Resets the Transfer Functions.\n"
               "(resets all Progress)")
        self.b_transfer_reset.setToolTip(tip)
        


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_openDestDir.clicked.connect(lambda: Utils.openInExplorer(self.core, self.sourceBrowser.destDir))
        self.b_ovr_config_proxy.clicked.connect(self.configProxy)
        self.b_ovr_config_fileNaming.clicked.connect(self.configFileNaming)
        self.b_ovr_config_metadata.clicked.connect(self.configMetadata)


    @err_catcher(name=__name__)
    def configureUI(self):
        configIcon = Utils.getIconFromPath(os.path.join(uiPath, "Icons", "configure.png"))

        self.b_ovr_config_fileNaming.setIcon(configIcon)
        self.b_ovr_config_proxy.setIcon(configIcon)
        self.b_ovr_config_metadata.setIcon(configIcon)

        self.b_ovr_config_fileNaming.setEnabled(self.chb_ovr_fileNaming.isChecked())
        self.b_ovr_config_proxy.setEnabled(self.chb_ovr_proxy.isChecked())
        self.b_ovr_config_metadata.setEnabled(self.chb_ovr_metadata.isChecked())


    @err_catcher(name=__name__)
    def updateUI(self):
        #   Configure Proxy UI
        try:
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
                        presetStr = f"( {pData['proxyPreset']} - {pData['proxyScale']} )"
                        proxyDisplayStr = f"{proxyModeStr}   {presetStr}"

            #   Add Disabled to UI
            else:
                proxyDisplayStr = "DISABLED"

            self.l_proxyMode.setText(proxyDisplayStr)
            self.l_proxyMode.setEnabled(proxyEnabled)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Functions Panel Proxy UI:\n{e}")

        #   Configure File Name Mods UI
        try:
            fileNamingEnabled = self.chb_ovr_fileNaming.isChecked()

            #   If Enabled, Add to UI
            if fileNamingEnabled:
                #   Get Modifiers
                mods = self.sourceBrowser.nameMods
                #   Get Number of Mods
                numMods = f"{str(len(mods))} Modifiers"
                #   Create ToolTip
                nameTipStr = (
                    "<table>"
                    + "".join(
                        f"<tr>"
                        f"<td style='padding-right: 20px;'>{mod['mod_type']}</td>"
                        f"<td>{'Enabled' if mod['enabled'] else 'Disabled'}</td>"
                        f"</tr>"
                        for mod in mods
                    )
                    + "</table>"
                    )

            #   Add Disabled to UI
            else:
                numMods = nameTipStr = "DISABLED"

            #   Update UI Label and ToolTip
            self.l_enabledNameMods.setText(numMods)
            self.l_enabledNameMods.setEnabled(fileNamingEnabled)
            self.l_enabledNameMods.setToolTip(nameTipStr)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Functions Panel Naming UI:\n{e}")

        #   Configure Metadata UI
        try:
            metadataEnabled = self.sourceBrowser.metadataEnabled = self.chb_ovr_metadata.isChecked()

            if metadataEnabled:
                #   Collect all Enabled Sidecar Extensions (or None)
                enabled_sidecars = [
                    re.search(r"\((.*?)\)", sc).group(1)
                    for sc, state in self.sourceBrowser.sidecarStates.items()
                    if state and re.search(r"\((.*?)\)", sc)
                ]
                sc_str = ", ".join(enabled_sidecars) if enabled_sidecars else "None"

                presetName = self.sourceBrowser.metaPresets.currentPreset
                nameTipStr = f"{sc_str}    ({presetName})"
            else:
                nameTipStr = "DISABLED"

            self.l_enabledMetaData.setText(nameTipStr)
            self.l_enabledMetaData.setEnabled(metadataEnabled)
            self.l_enabledMetaData.setToolTip(nameTipStr)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Functions Panel Metadata UI:\n{e}")



    #   Opens File Naming Window to Configure
    @err_catcher(name=__name__)
    def configFileNaming(self):
        destList = self.sourceBrowser.lw_destination
        row_count = destList.count()

        #   If there is only the Blank Entry Use EXAMPLE
        if row_count < 1:
            fileName = "EXAMPLEFILENAME"
        
        #   Get the First File's Basename
        else:
            listItem = self.sourceBrowser.lw_destination.item(0)
            fileItem = self.sourceBrowser.lw_destination.itemWidget(listItem)
            
            filePath = fileItem.getSource_mainfilePath()
            fileName = Utils.getBasename(filePath)

        #   Call Popup and pass Basename and Existing Modifiers
        namePopup = NamingPopup(self.core, fileName, mods=self.sourceBrowser.nameMods)
        logger.debug("Opening File Naming Settings Window")
        namePopup.exec_()

        #   If User Clicked Apply
        if namePopup.result == "Apply":
            try:
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
                self.sourceBrowser.refreshDestTable(restoreSelection=True)
                #   Save Mods to Project Settings
                self.sourceBrowser.plugin.saveSettings(key="nameMods")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Update File Naming Settings:\n{e}")


    @err_catcher(name=__name__)
    def configProxy(self):
        #   Call Popup
        proxyPopup = ProxyPopup(self.core, self)
        logger.debug("Opening Proxy Settings Window")
        proxyPopup.exec_()

        if proxyPopup.result == "Apply":
            try:
                #   Update Proxy Settings in SourceTab
                self.sourceBrowser.proxyMode = proxyPopup.getProxyMode()
                self.sourceBrowser.proxySettings = proxyPopup.getProxySettings()

                self.updateUI()
                self.sourceBrowser.refreshTotalTransSize()
                self.sourceBrowser.toggleProxy(self.sourceBrowser.proxyEnabled)
                #   Save Proxy Settings
                self.sourceBrowser.plugin.saveSettings(key="proxySettings")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Update Proxy Settings:\n{e}")


    @err_catcher(name=__name__)
    def configMetadata(self, showUI=True):
        if hasattr(self.sourceBrowser, "metaEditor") and self.sourceBrowser.metaEditor:
            self.sourceBrowser.metaEditor.refresh()

        else:
            self.sourceBrowser.metaEditor = MetadataEditor(self.core, self.sourceBrowser)
            
        if showUI:
            self.sourceBrowser.metaEditor.show()

        
