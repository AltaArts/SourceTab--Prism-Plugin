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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
sys.path.append(uiPath)


from SourceTab_Config_ui import Ui_w_sourceConfig

class SourceTab_Config(QDialog, Ui_w_sourceConfig):
    def __init__(self, browser, core, parent=None):
        super(SourceTab_Config, self).__init__(parent)
        self.browser = browser
        self.core = core

        #   Call UI Setup
        self.setupUi(self)

        self.setWindowFlags(Qt.Window)

        #   Get Prism StyleSheet
        try:
            activeStyle = self.core.getActiveStyleSheet()
            if activeStyle and "css" in activeStyle:
                self.setStyleSheet(activeStyle["css"])

        except Exception as e:
            print(f"Failed to apply Prism style: {e}")

        #   Resize Window
        self.resize(600, 800)

        self.loadSettings()

        #   Connect Buttons
        self.bb_saveCancel.accepted.connect(self.saveSettings)
        self.bb_saveCancel.rejected.connect(self.reject)
        #   Toggle CustomIcon Enabled
        self.chb_useCustomIcon.toggled.connect(self.le_customIconPath.setEnabled)
        self.chb_useCustomThumbPath.toggled.connect(self.le_customThumbPath.setEnabled)


    #   Loads Settings from Source Browser Values
    def loadSettings(self):
        self.sb_thumbThreads.setValue(self.browser.max_thumbThreads)
        self.sb_copyThreads.setValue(self.browser.max_copyThreads)
        self.sb_copyChunks.setValue(self.browser.size_copyChunk)
        self.sp_progUpdateRate.setValue(self.browser.progUpdateInterval)
        self.chb_showPopup.setChecked(self.browser.useCompletePopup)
        self.chb_playSound.setChecked(self.browser.useCompleteSound)
        self.chb_useTransferReport.setChecked(self.browser.useTransferReport)
        self.chb_useCustomIcon.setChecked(self.browser.useCustomIcon)
        self.le_customIconPath.setText(self.browser.customIconPath)
        self.chb_useViewLut.setChecked(self.browser.useViewLuts)
        self.chb_useCustomThumbPath.setChecked(self.browser.useCustomThumbPath)
        self.le_customThumbPath.setText(self.browser.customThumbPath)


    #   Gets called from Source Browser Save Method
    def saveSettings(self):
        self.cData = {
            "max_thumbThreads": self.sb_thumbThreads.value(),
            "max_copyThreads": self.sb_copyThreads.value(),
            "size_copyChunk": self.sb_copyChunks.value(),
            "updateInterval": self.sp_progUpdateRate.value(),
            "useCompletePopup": self.chb_showPopup.isChecked(),
            "useCompleteSound": self.chb_playSound.isChecked(),
            "useTransferReport": self.chb_useTransferReport.isChecked(),
            "useCustomIcon": self.chb_useCustomIcon.isChecked(),
            "customIconPath": self.le_customIconPath.text(),
            "useViewLut": self.chb_useViewLut.isChecked(),
            "useCustomThumbPath": self.chb_useCustomThumbPath.isChecked(),
            "customThumbPath": self.le_customThumbPath.text()
            }
        
        self.accept()