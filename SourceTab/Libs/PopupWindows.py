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
import shlex
import re
import textwrap
import logging
import json
import csv
from datetime import datetime


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginRoot = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginRoot, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")


#   Get Name Mod Methods
from FileNameMods import getModifiers as GetMods
from FileNameMods import getModClassByName as GetModByName
from FileNameMods import createModifier as CreateMod

import SourceTab_Utils as Utils

from SourceTab_Models import (MetaFileItems,
                              MetadataModel,
                              MetadataField,
                              MetadataFieldCollection,
                              MetadataTableModel,
                              SectionHeaderDelegate,
                              MetadataComboBoxDelegate,
                              CheckboxDelegate)

from MetadataEditor_ui import Ui_w_metadataEditor

logger = logging.getLogger(__name__)



#################################################
##############    WAIT POPUP    #################


class WaitPopup:
    _popupProcess = None

    @classmethod
    def showPopup(cls, parent=None):
        if cls._popupProcess is None:
            #   Get Paths
            launcherPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "WaitPopup.py"))
            gifPath = os.path.join(iconDir, "loading-dark.gif")

            #   Get Environment for Prism Qt Libs
            env = os.environ.copy()
            env["PRISM_SYSPATH"] = os.pathsep.join(sys.path)

            #   Fallback Geometry
            geo = [0, 0, 0, 0]

            #   Get Window Geo if passed (Project Browser)
            if parent and isinstance(parent, QWidget):
                geom = parent.frameGeometry()
                geo = [geom.x(), geom.y(), geom.width(), geom.height()]

            #   Args: [exe, script, gifPath, x, y, w, h]
            args = [sys.executable, launcherPath, gifPath] + [str(v) for v in geo]

            logger.debug(f"Showing Wait Popup")

            cls._popupProcess = subprocess.Popen(args, env=env)


    @classmethod
    def closePopup(cls):
        logger.debug("Closing Wait Popup")
        if cls._popupProcess is not None:
            cls._popupProcess.terminate()
            cls._popupProcess.wait()
            cls._popupProcess = None


    @classmethod
    def isShowing(cls):
        return cls._popupProcess is not None
    


#################################################
#############    DISPLAY POPUP   ################


class DisplayPopup(QDialog):
    def __init__(self, data, title="Display Data", buttons=None, xScale=2, yScale=2, xSize=None, ySize=None, parent=None):
        super().__init__(parent)

        self.result = None
        self.setWindowTitle(title)

        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        width  = xSize if xSize else screen_geometry.width() // xScale
        height = ySize if ySize else screen_geometry.height() // yScale

        x_pos   = (screen_geometry.width() - width) // 2
        y_pos   = (screen_geometry.height() - height) // 2

        self.setGeometry(x_pos, y_pos, width, height)

        lo_main = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Recursively display data
        self._add_recursive(scroll_layout, data)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        # Buttons
        lo_buttons = QHBoxLayout()
        lo_buttons.addStretch(1)

        if buttons is None:
            buttons = ["Close"]

        for button_text in buttons:
            button = QPushButton(button_text)
            button.clicked.connect(lambda _, t=button_text: self._onButtonClicked(t))
            lo_buttons.addWidget(button)

        lo_main.addLayout(lo_buttons)


    def _onButtonClicked(self, text):
        self.result = text
        self.accept()


    def _add_recursive(self, layout, data, indent=0):
        #   WIDGET
        if isinstance(data, QWidget):
            try:
                layout.addWidget(data)

            except Exception as e:
                logger.warning(f"ERROR: Failed to display Widget: {e}")

        #   DICT
        elif isinstance(data, dict):
            try:
                for key, value in data.items():
                    #   If Empty Just Add Empty Line
                    if key == "" and value == "":
                        layout.addSpacing(10)
                        continue

                    #   Nested dict/list/widget -> header + recursive call
                    if isinstance(value, (dict, list, QWidget)):
                        header = QLabel(" " * indent + str(key))
                        font = header.font()
                        font.setBold(True)

                        #   Colors for Errors/Warnings
                        if str(key).lower().startswith("error"):
                            header.setStyleSheet("color: red;")
                        elif str(key).lower().startswith("warning"):
                            header.setStyleSheet("color: orange;")

                        header.setFont(font)
                        layout.addWidget(header)

                        #   Recurse into Children
                        self._add_recursive(layout, value, indent + 4)

                    else:
                        # Simple Key-Value
                        hlayout = QHBoxLayout()
                        key_lbl = QLabel(" " * indent + str(key) + ":")
                        val_lbl = QLabel(str(value))
                        val_lbl.setWordWrap(True)
                        hlayout.addWidget(key_lbl)
                        hlayout.addWidget(val_lbl)
                        layout.addLayout(hlayout)

            except Exception as e:
                logger.warning(f"ERROR: Failed to display dict: {e}")

        #   LIST
        elif isinstance(data, list):
            try:
                for item in data:
                    self._add_recursive(layout, item, indent)
            
            except Exception as e:
                logger.warning(f"ERROR: Falied to display list: {e}")

        #   STRING
        else:
            try:
                if data == "":
                    layout.addSpacing(10)
                    return
                lbl = QLabel(" " * indent + str(data))
                lbl.setWordWrap(True)
                layout.addWidget(lbl)
            
            except Exception as e:
                logger.warning(f"ERROR: Failed to display string: {e}")


    @staticmethod
    def display(data: QWidget | dict | list | str,
                title: str = "Display Data",
                buttons: list = None,
                xScale: int = 2,
                yScale: int = 2,
                xSize: int = None,
                ySize: int = None,
                modal: bool = True,
                parent: QWindow = None) -> str | None:
        '''Display Data in Popup Window'''
                
        try:
            dialog = DisplayPopup(data, title=title, buttons=buttons,
                                xScale=xScale, yScale=yScale,
                                xSize=xSize, ySize=ySize, parent=parent)
            if modal:
                dialog.exec_()
                return dialog.result
            else:
                dialog.show()
                return None
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Show DisplayPopup:\n{e}")



#################################################
###############    PROXY   ######################


class ProxyPopup(QDialog):
    def __init__(self, core, sourceFuncts):
        super().__init__()

        self.core = core
        self.sourceFuncts = sourceFuncts
        self.sourceBrowser = sourceFuncts.sourceBrowser
        self.proxyMode = self.sourceBrowser.proxyMode
        self.proxyPresets = self.sourceBrowser.proxyPresets

        self.result = None

        self.setWindowTitle("Proxy Configuration")
        self.setupUI()
        self.loadUI()

        logger.debug("Loaded Proxy Window")


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 3
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Main layout
        lo_main = QVBoxLayout(self)

        ##   Proxy Mode
        boldFont = QFont()
        boldFont.setBold(True)

        #   Tooltip
        modeTip = """
        <b>Proxy Handling Mode:</b><br><br>
        <table cellpadding="6">
        <tr><td><b>Copy Proxys:</b></td><td>Detected Proxys will be Transferred with the Source File</td></tr>
        <tr><td><b>Generate Proxys:</b></td><td>Proxy Files will be Generated for all Source Files</td></tr>
        <tr><td><b>Generate Missing Proxys:</b></td><td>
            Detected Proxys will be Transferred AND<br>
            Proxys will be Generated for missing Proxys
        </td></tr>
        </table>
        """

        l_proxyMode = QLabel("Proxy Mode:")
        l_proxyMode.setFont(boldFont)
        l_proxyMode.setToolTip(modeTip)
        lo_main.addWidget(l_proxyMode)

        #   Proxy Mode Radio Buttons
        lo_radio = QHBoxLayout()
        lo_radio.setContentsMargins(50, 0, 50, 0)

        self.radio_group = QButtonGroup(self)

        radio_labels = ["Copy Proxys", "Generate Proxys", "Generate Missing Proxys"]
        self.radio_buttons = {}

        for i, label in enumerate(radio_labels):
            rb = QRadioButton(label)
            rb.setFont(boldFont)
            rb.setToolTip(modeTip)
            self.radio_group.addButton(rb, i)
            lo_radio.addWidget(rb)
            self.radio_buttons[label] = rb

        self.radio_group.buttonClicked.connect(self._onProxyModeChanged)

        lo_main.addLayout(lo_radio)

        spacer_1 = QSpacerItem(10, 20)
        lo_main.addItem(spacer_1)

        ##  Global Settings GroupBox
        self.gb_globalSettings = QGroupBox("Global Proxy Settings")
        lo_globalSettings = QVBoxLayout()
        lo_globalSettings.setContentsMargins(20,10,20,10)

        #   Override Layout
        lo_ovrProxyDir = QHBoxLayout()
        #   Create Widgets
        self.l_ovrProxyDir = QLabel("Override Proxy Dir:")
        self.l_ovrProxyDir.setFixedWidth(125)
        self.le_ovrProxyDir = QLineEdit()
        #   Add Widgets to Layout
        lo_ovrProxyDir.addWidget(self.l_ovrProxyDir)
        lo_ovrProxyDir.addWidget(self.le_ovrProxyDir)
        #   Add Override Layout to Global Layout
        lo_globalSettings.addLayout(lo_ovrProxyDir)

        #   Fallback Layout
        lo_fallBackDir = QHBoxLayout()
        #   Create Widgets
        self.l_fallbackDir = QLabel("Fallback Proxy Dir:")
        self.l_fallbackDir.setFixedWidth(125)
        self.le_fallbackDir = QLineEdit()
        #   Add Widgets to Layout
        lo_fallBackDir.addWidget(self.l_fallbackDir)
        lo_fallBackDir.addWidget(self.le_fallbackDir)
        #   Add Fallback Layout to Global Layout
        lo_globalSettings.addLayout(lo_fallBackDir)

        #   Add Global Layout to Main Layout
        self.gb_globalSettings.setLayout(lo_globalSettings)
        lo_main.addWidget(self.gb_globalSettings)

        spacer_2 = QSpacerItem(10, 20)
        lo_main.addItem(spacer_2)

        ##  Proxy Copy Settings GroupBox
        self.gb_proxyCopySettings = QGroupBox("Proxy Copy Settings")
        lo_proxyCopySettings = QHBoxLayout()
        lo_proxyCopySettings.setContentsMargins(20,10,20,10)

        #   UI ELEMENTS
        self.l_numberTemplatesTitle = QLabel("Proxy Search Templates:    ")
        self.l_numberTemplates = QLabel()
        self.b_editSearchList = QPushButton("Edit Proxy Search Templates")

        #   Add Widgets to Layout
        lo_proxyCopySettings.addWidget(self.l_numberTemplatesTitle)
        lo_proxyCopySettings.addWidget(self.l_numberTemplates)
        lo_proxyCopySettings.addStretch()
        lo_proxyCopySettings.addWidget(self.b_editSearchList)

        #   Add Proxy Copy Layout to Main Layout
        self.gb_proxyCopySettings.setLayout(lo_proxyCopySettings)
        lo_main.addWidget(self.gb_proxyCopySettings)


        ##  FFMPEG Settings GroupBox
        self.gb_ffmpegSettings = QGroupBox("FFMPEG Settings")
        lo_ffmpeg = QHBoxLayout()
        lo_ffmpeg.setContentsMargins(20,10,20,10)

        #   Presets Label
        self.l_ffmpegPresets = QLabel("Proxy Presets")
        lo_ffmpeg.addWidget(self.l_ffmpegPresets)
        #   Presets Combo
        self.cb_proxyPresets = QComboBox()
        lo_ffmpeg.addWidget(self.cb_proxyPresets)

        spacer_3 = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lo_ffmpeg.addItem(spacer_3)

        #   Scale Label
        self.l_proxyScale = QLabel("Proxy Scale")
        lo_ffmpeg.addWidget(self.l_proxyScale)

        #   Scale Combo
        self.cb_proxyScale = QComboBox()
        self.cb_proxyScale.addItems(["25%", "50%", "75%", "100%", "150%", "200%"])
        self.cb_proxyScale.setCurrentText("100%")
        lo_ffmpeg.addWidget(self.cb_proxyScale)

        spacer_4 = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lo_ffmpeg.addItem(spacer_4)

        #   Edit Preset Button
        self.b_editPresets = QPushButton("Edit Proxy Presets")
        lo_ffmpeg.addWidget(self.b_editPresets)

        #   Add FFmpeg Layout to Main Layout
        self.gb_ffmpegSettings.setLayout(lo_ffmpeg)
        lo_main.addWidget(self.gb_ffmpegSettings)

        #   Add Stretch to Bottom to Buttons
        lo_main.addStretch()

        #   Bottom Buttons
        lo_buttons = QHBoxLayout()
        lo_buttons.addStretch(1)

        buttons = ["Apply", "Close"]

        for button_text in buttons:
            button = QPushButton(button_text)
            button.clicked.connect(lambda _, t=button_text: self._onButtonClicked(t))
            lo_buttons.addWidget(button)

        #   Add Buttons Layout to Main Layout
        lo_main.addLayout(lo_buttons)

        self.setToolTips()

    
    def setToolTips(self):
        tip = ("If not Empty, all Proxy files will be transferred to this directory.\n\n"
               "This can be an:\n"
               "   Absolute Dir Path:  ( C:\some_path\Proxy ) or\n"
               "   Relative Dir Path:   ( .\Proxy )")
        self.l_ovrProxyDir.setToolTip(tip)
        self.le_ovrProxyDir.setToolTip(tip)

        tip = ("Directory to be Used if there are no Source Proxys to Resolve\n"
               "a Proxy Path from.\n\n"
               "This can be an:\n"
               "   Absolute Dir Path:  ( C:\some_path\Proxy ) or\n"
               "   Relative Dir Path:   ( .\Proxy )")
        self.l_fallbackDir.setToolTip(tip)
        self.le_fallbackDir.setToolTip(tip)

        tip = ("These are the Search Templates to Find and Resolve Proxy Files\n\n"
               "Use the Template Editor to add/remove/modify Templates")
        self.l_numberTemplatesTitle.setToolTip(tip)
        self.l_numberTemplates.setToolTip(tip)

        tip = "Open Template Editor"
        self.b_editSearchList.setToolTip(tip)

        tip = "Available Proxy Presets"
        self.l_ffmpegPresets.setToolTip(tip)

        tip = ("Scale to be used for the Generated Proxys\n"
               "This will not affect the Main File")
        self.l_proxyScale.setToolTip(tip)
        self.cb_proxyScale.setToolTip(tip)

        tip = "Open Proxy Preset Editor"
        self.b_editPresets.setToolTip(tip)


    #   Adds Red Border to the LineEdit if Not Valid
    def setLineEditColor(self, lineEdit, valid=True):
        if valid:
            lineEdit.setStyleSheet("")
        else:
            lineEdit.setStyleSheet("QLineEdit { border: 1px solid #cc6666; }")


    def connectEvents(self):
        self.le_ovrProxyDir.textChanged.connect(lambda: self.validatePathInput(self.le_ovrProxyDir, allowEmpty=True))
        self.le_fallbackDir.textChanged.connect(lambda: self.validatePathInput(self.le_fallbackDir))
        self.b_editPresets.clicked.connect(self._onEditPresetsClicked)
        self.b_editSearchList.clicked.connect(self._onEditSearchTemplatesClicked)


    #   Populate UI from Passed Settings
    def loadUI(self):
        try:
            #   Match Mode to Radio Button Label
            label = self.sourceFuncts.proxyNameMap.get(self.proxyMode)
            if label and label in self.radio_buttons:
                self.radio_buttons[label].setChecked(True)

            #   Populate Preset Combo
            self.populatePresetCombo()

            #   Preset Settings
            pSettings = self.sourceBrowser.proxySettings
            if "fallback_proxyDir" in pSettings:
                self.le_fallbackDir.setText(pSettings["fallback_proxyDir"])

            if "ovr_proxyDir" in pSettings:
                self.le_ovrProxyDir.setText(pSettings["ovr_proxyDir"])

            if "proxyPreset" in pSettings:
                curPreset = pSettings["proxyPreset"]
                idx = self.cb_proxyPresets.findText(curPreset)
                if idx != -1:
                    self.cb_proxyPresets.setCurrentIndex(idx)

            if "proxyScale" in pSettings:
                curScale = pSettings["proxyScale"]
                idx = self.cb_proxyScale.findText(curScale)
                if idx != -1:
                    self.cb_proxyScale.setCurrentIndex(idx)

            self.connectEvents()
            self._onProxyModeChanged()
            self.updateTemplateNumber()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Load Proxy Window UI:\n{e}")


    #   Returns Proxy Search List
    def getProxySearchList(self):
        return self.sourceFuncts.sourceBrowser.getSettings(key="proxySearch")
    

    #   Populate Preset Combo with Presets
    def updateTemplateNumber(self):
        number = len(self.getProxySearchList())
        self.l_numberTemplates.setText(f"{number} templates")


    #   Populate Preset Combo with Presets
    def populatePresetCombo(self):
        try:
            self.cb_proxyPresets.clear()
            self.cb_proxyPresets.addItems(self.proxyPresets.getOrderedPresetNames())
            self.createPresetsTooltip()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Presets Combo:\n{e}")


    #   Creates and Adds Tooltip to Preset Combo
    def createPresetsTooltip(self):
        tip = self.proxyPresets.getTooltip()
        self.cb_proxyPresets.setToolTip(tip)


    def _onProxyModeChanged(self):
        mode = self.getProxyMode()
        #   Set Visibility of Options Based on Mode
        self.gb_proxyCopySettings.setVisible(mode in ["copy", "missing"])
        self.gb_ffmpegSettings.setVisible(mode in ("generate", "missing"))


    #   Open Window to Edit Presets
    def _onEditSearchTemplatesClicked(self):
        #   Get Existing Presets
        searchList = self.getProxySearchList()

        editWindow = ProxySearchStrEditor(self.core, self, searchList)
        logger.debug("Opening Proxy Search Template Editor")
        editWindow.exec_()

        if editWindow.result() == "Save":
            try:
                #   Get Updated Data
                sData = editWindow.getData()           
                #   Save to Settings
                self.sourceFuncts.sourceBrowser.plugin.saveSettings(key="proxySearch", data=sData)
                #   Refresh Source Items
                self.sourceFuncts.sourceBrowser.refreshSourceItems()
                #   Clear Destination Items
                self.sourceFuncts.sourceBrowser.clearTransferList()
                #   Update UI
                self.updateTemplateNumber()

                logger.debug("Saved Proxy Search Templates")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Save Proxy Search Templates:\n{e}")


    #   Open Window to Edit Presets
    def _onEditPresetsClicked(self):
        editWindow = ProxyPresetsEditor(self.core, self)
        logger.debug("Opening Proxy Presets Editor")
        editWindow.exec_()

        if editWindow.result() == "Save":
            try:
                presetData, presetOrder = editWindow.getPresets()

                #   Detect Newly Added or Modified Presets
                existingNames = set(self.proxyPresets.getPresetNames())

                #   Capture Original Data for Comparison
                originalDataMap = {
                    name: Utils.normalizeData(self.proxyPresets.getPresetData(name))
                    for name in existingNames
                }

                #   Clear and Re-add Presets
                self.proxyPresets.clear()

                for name in presetOrder:
                    data = presetData.get(name, {})
                    self.proxyPresets.addPreset(name, data)

                    normalizedData = Utils.normalizeData(data)

                    originalData = originalDataMap.get(name)

                    #   Save if New or Modified
                    if name not in existingNames or normalizedData != originalData:
                        pData = {"name": name, "data": data}
                        Utils.savePreset(self.core, "proxy", name, pData, project=True, checkExists=False)
                        logger.debug(f"Saved preset '{name}' to project")

                self.proxyPresets.presetOrder = presetOrder
                self.populatePresetCombo()
                logger.debug("Saved Proxy Presets")

            except Exception as e:
                logger.warning(f"ERROR: Failed to Save Proxy Presets:\n{e}")


    #   Checks User Input for Errors
    def validatePathInput(self, lineEdit, allowEmpty=False):
        text = lineEdit.text().strip()

        #   1. Check for Empty 
        if not text:
            if allowEmpty:
                self.setLineEditColor(lineEdit, valid=True)
                lineEdit.setToolTip("")
                return True
            
            else:
                self.setLineEditColor(lineEdit, valid=False)
                lineEdit.setToolTip("Path cannot be empty.")
                return False

        errors = []

        # 2. No illegal characters (on Windows): <>:"|?*
        for idx, ch in enumerate(text):
            if ch in '<>:"|?*':
                if not (ch == ':' and idx == 1):
                    errors.append(f"Illegal Character: '{ch}'")

        # 3. Leading slash without drive or “./”/“../”
        if text.startswith(("\\", "/")) and not re.match(r"^[A-Za-z]:[\\/]", text):
            errors.append("Missing Relative Path or Drive Letter")

        # 4. Empty segments (e.g. "foo\\\\bar" or "foo//bar")
        segs = re.split(r"[\\/]", text)
        if any(seg == "" for seg in segs):
            errors.append("Empty Path Segment Detected")

        # 5. No trailing spaces
        if text.endswith(" "):
            errors.append("Trailing Space in Path")

        # 6. No spaces around separators
        if re.search(r"[ \\]/|/[ \\]", text):
            errors.append("Space Adjacent to Path Separator")

        valid = not errors

        # Update UI
        self.setLineEditColor(lineEdit, valid)

        if valid:
            lineEdit.setToolTip("")
        else:
            lineEdit.setToolTip("\n".join(errors))

        return valid


    def _onButtonClicked(self, text):
        self.result = text
        self.accept()


    #   Return Selected Proxy Mode
    def getProxyMode(self):
        checkedButton = self.radio_group.checkedButton()
        if checkedButton:
            label = checkedButton.text()
            for shortMode, uiLabel in self.sourceFuncts.proxyNameMap.items():
                if uiLabel == label:
                    return shortMode
        
        return "None"
    

    #   Return Selected Proxy Preset Name and Scale
    def getProxySettings(self):
        pData = {
            "fallback_proxyDir":            self.le_fallbackDir.text(),
            "ovr_proxyDir":                 self.le_ovrProxyDir.text(),
            "proxyPreset":                  self.cb_proxyPresets.currentText(),
            "proxyScale":                   self.cb_proxyScale.currentText(),
            "proxyPresetOrder":             self.proxyPresets.presetOrder,
            }
        
        return pData
        
    

class ProxySearchStrEditor(QDialog):
    def __init__(self, core, origin, searchList):
        super().__init__(origin)
        self.core = core
        self.origin = origin

        self.searchList = searchList.copy()
        self._action = None

        self.setWindowTitle("Proxy Search List")

        self.setupUI()
        self.connectEvents()
        self.populateTable(self.searchList)

        logger.debug("Loaded Proxy Search Editor")


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 3
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Create table
        self.headers = ["Proxy Search Templates"]
        self.tw_searchList = QTableWidget(len(self.searchList), len(self.headers), self)
        self.tw_searchList.setHorizontalHeaderLabels(self.headers)
        self.tw_searchList.setSelectionBehavior(QTableWidget.SelectRows)
        self.tw_searchList.setEditTriggers(QTableWidget.NoEditTriggers)

        #   Footer Buttons
        lo_buttonBox    = QVBoxLayout()

        lo_buttonsTop   = QHBoxLayout()
        self.b_edit     = QPushButton("Edit")
        self.b_add      = QPushButton("Add")
        self.b_remove   = QPushButton("Remove")
        self.b_moveup   = QPushButton("Move Up")
        self.b_moveDn   = QPushButton("Move Down")

        lo_buttonsBottom = QHBoxLayout()
        self.b_test      = QPushButton("Validate Template")
        self.b_reset     = QPushButton("Reset to Defaults")
        self.b_save      = QPushButton("Save")
        self.b_cancel    = QPushButton("Cancel")
        
        lo_buttonsTop.addWidget(self.b_edit)
        lo_buttonsTop.addWidget(self.b_add)
        lo_buttonsTop.addWidget(self.b_remove)
        lo_buttonsTop.addStretch()
        lo_buttonsTop.addWidget(self.b_moveup)
        lo_buttonsTop.addWidget(self.b_moveDn)

        lo_buttonsBottom.addWidget(self.b_test)
        lo_buttonsBottom.addWidget(self.b_reset)
        lo_buttonsBottom.addStretch()
        lo_buttonsBottom.addWidget(self.b_save)
        lo_buttonsBottom.addWidget(self.b_cancel)

        lo_buttonBox.addLayout(lo_buttonsTop)
        lo_buttonBox.addLayout(lo_buttonsBottom)

        #   Add to Main Layout
        lo_main.addWidget(self.tw_searchList)
        lo_main.addLayout(lo_buttonBox)

        self.tw_searchList.horizontalHeader().setStretchLastSection(True)
        self.tw_searchList.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        #   ToolTips
        tip = """
        Proxy Search Templates that will be scanned to attempt to
        find a Mainfile's associated Proxy.  This ignores the file-extension.

        This uses relative paths based on the MainFile's directory,
        and uses standard dot-notation for relative directories:
        ./   - current directory
        ../  - parent directory

        The search also uses placeholders to allow the search to find Proxys
        that have prefixes or suffixes:
        @MAINFILEDIR@    @MAINFILENAME@

        Examples:

        @MAINFILEDIR@\\proxy\\@MAINFILENAME@      -- search in a subdir named "proxy" with same name as the mainfile
        @MAINFILEDIR@\\@MAINFILENAME@_proxy      -- search in the same dir with the mainfile name with a "_proxy" suffix
        @MAINFILEDIR@\\..\\proxy\\@MAINFILENAME@" -- search in dir named "proxy" that is at the same level as the main dir
        """
        self.tw_searchList.setToolTip(tip)

        self.b_edit.setToolTip("Edit Selected Template")
        self.b_add.setToolTip("Add New Template")
        self.b_remove.setToolTip("Remove Selected Template")
        self.b_moveup.setToolTip("Move Selected Template Up One Row")
        self.b_moveDn.setToolTip("Move Selected Template Down One Row")
        self.b_test.setToolTip("Run a quick Test on the Template to Validate")
        self.b_reset.setToolTip("Reset All Templates to Factory Defaults")
        self.b_save.setToolTip("Save Changes and Close Window")
        self.b_cancel.setToolTip("Discard Changes and Close Window")


    def connectEvents(self):
        self.b_edit.clicked.connect(self._onEdit)
        self.b_add.clicked.connect(self._onAdd)
        self.b_remove.clicked.connect(self._onRemove)
        self.b_test.clicked.connect(self._onValidate)
        self.b_reset.clicked.connect(self._onReset)
        self.b_moveup.clicked.connect(self._onMoveUp)
        self.b_moveDn.clicked.connect(self._onMoveDown)
        self.b_save.clicked.connect(lambda: self._onFinish("Save"))
        self.b_cancel.clicked.connect(lambda: self._onFinish("Cancel"))


    def populateTable(self, templateList):
        try:
            #   Clear the Table
            self.tw_searchList.setRowCount(0)

            #   Set Column Count
            self.tw_searchList.setColumnCount(len(self.headers))
            self.tw_searchList.setHorizontalHeaderLabels(self.headers)

            #   Add Each Template String to New Row
            for template in templateList:
                row = self.tw_searchList.rowCount()
                self.tw_searchList.insertRow(row)
                self.tw_searchList.setItem(row, 0, QTableWidgetItem(template))

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Proxy Search Templates Table:\n{e}")


    #   Sets Row Editable
    def _onEdit(self):
        row = self.tw_searchList.currentRow()
        if row < 0: 
            return
        
        self.tw_searchList.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.tw_searchList.editItem(self.tw_searchList.item(row, 0))


    #   Adds Empty Row
    def _onAdd(self):
        #   Insert Blank Row after Current
        row = max(0, self.tw_searchList.currentRow() + 1)
        self.tw_searchList.insertRow(row)

        for col in range(self.tw_searchList.columnCount()):
            self.tw_searchList.setItem(row, col, QTableWidgetItem(""))

        self.tw_searchList.selectRow(row)


    #   Remove Selected Row
    def _onRemove(self):
        row = self.tw_searchList.currentRow()
        #   Gets Item Info
        preset_item = self.tw_searchList.item(row, 0)
        preset_name = preset_item.text() if preset_item else "Unknown"

        #   Create Question
        title = "Remove Template"
        text = f"Would you like to Remove template:\n\n{preset_name}"
        buttons = ["Remove", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)
        #   Remove if Affirmed
        if result == "Remove":
            if row >= 0:
                self.tw_searchList.removeRow(row)


    #   Handle Tests for Preset
    def _onValidate(self):
        row = self.tw_searchList.currentRow()
        if row == -1:
            self.core.popup(title="No Selection", text="Please Select a Template to Validate.")
            return

        #   Get data from the table
        template = self.tw_searchList.item(row, 0).text()

        #   Get Full Validation Results
        results = self._validateTemplate(template)

        #   Format Output
        lines = [f"Template Validation Report:\n   {template}:\n\n"]
        # all_passed = True

        for label, passed, msg in results:
            if passed:
                lines.append(f"{label} — Passed")
                lines.append("")
            else:
                lines.append(f"{label} — Failed: {msg}")
                lines.append("")

                # all_passed = False

        #   Show Popup
        title="Preset Validation Results"
        text="\n".join(lines)
        DisplayPopup.display(text, title, xScale=4, yScale=3)


    #   Runs Several Sanity Checks on Templates
    def _validateTemplate(self, template):
        results = []

        #   1. Check Placeholders
        has_dir = "@MAINFILEDIR@" in template
        has_name = "@MAINFILENAME@" in template
        results.append((
            "Contains @MAINFILEDIR@ token",
            has_dir,
            "Missing @MAINFILEDIR@"
        ))
        results.append((
            "Contains @MAINFILENAME@ token",
            has_name,
            "Missing @MAINFILENAME@"
        ))

        #   2. Check Illegal Characters (except the backslashes, dot, underscore, hyphen, colon for drive letter)
        illegal = set('<>:"|?*')
        bad = sorted(set(template) & illegal)
        results.append((
            "No illegal characters",
            not bad,
            f"Found illegal chars: {', '.join(bad)}"
        ))

        #   3. Check Replacement Tokens by Simulating a File Path
        dummy_dir  = os.path.join("C:", "MyProject", "Some", "Path")
        dummy_name = "MyFile"
        try:
            replaced = (template
                        .replace("@MAINFILEDIR@", dummy_dir)
                        .replace("@MAINFILENAME@", dummy_name))
            
            nor_dir = os.path.normpath(replaced)

            tokens_left = any(tok in nor_dir for tok in ("@MAINFILEDIR@", "@MAINFILENAME@"))

            results.append((
                "Tokens Resolve Correctly",
                not tokens_left,
                "Some Tokens Failed to Resolve"
            ))
        except Exception as e:
            results.append((
                "Tokens resolve cleanly",
                False,
                f"Exception During Resolving: {e}"
            ))

        #   4. Check for Empty Path Segments (i.e. no “foo\\\bar”)
        segs = nor_dir.split(os.sep)
        empty = any(s == "" for s in segs)
        results.append((
            "No Empty Path Segments",
            not empty,
            "Found Empty Segment(s) after Splitting Path Separator"
        ))

        #   5. Check to Make Sure it Resolves Inside the Dir Tree
        if ".." in template:
            inside = nor_dir.startswith(dummy_dir)
            results.append((
                "‘..’ stays inside project",
                inside,
                f"Resolved Path jumps outside Dir Structure"
            ))

        return results
    

    #   Resets the Templates to Default Data from Prism_SourceTab_Functions.py
    def _onReset(self):
        #   Create Question
        title = "Reset Templates to Default"
        text = ("Would you like to Reset the Proxy Search\n"
                "Templates to the Factory Defaults?\n\n"
                "All Custom Templates will be lost.\n\n"
                "This effects all Users in this Prism Project.")
        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            try:
                #   Get Default Templates
                sData = self.origin.sourceFuncts.sourceBrowser.plugin.getDefaultSettings(key="proxySearch")
                #   Re-assign searchList
                self.searchList = sData
                #   Populate Table with Default Data
                self.populateTable(sData)

                logger.debug("Reset Proxy Search Templates to Defaults")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Reset Proxy Search Templates to Defaults:\n{e}")


    def _onMoveUp(self):
        row = self.tw_searchList.currentRow()
        if row > 0:
            self._swapRows(row, row-1)
            self.tw_searchList.selectRow(row-1)


    def _onMoveDown(self):
        row = self.tw_searchList.currentRow()
        if row < self.tw_searchList.rowCount() - 1:
            self._swapRows(row, row+1)
            self.tw_searchList.selectRow(row+1)


    def _swapRows(self, r1, r2):
        for c in range(self.tw_searchList.columnCount()):
            t1 = self.tw_searchList.takeItem(r1, c)
            t2 = self.tw_searchList.takeItem(r2, c)
            self.tw_searchList.setItem(r1, c, t2)
            self.tw_searchList.setItem(r2, c, t1)


    def _onFinish(self, action):
        self._action = action
        if action == "Save":
            newTemplates = []

            #   Re-assign searchList from UI data
            for row in range(self.tw_searchList.rowCount()):
                template = self.tw_searchList.item(row, 0).text()
                newTemplates.append(template)

            self.searchList = newTemplates

        self.accept()


    def result(self):
        return self._action


    def getData(self):
        return self.searchList



class ProxyPresetsEditor(QDialog):
    def __init__(self, core, origin):
        super().__init__(origin)
        self.core = core
        self.origin = origin

        self.proxyPresets = self.origin.sourceBrowser.proxyPresets
        presetDir = Utils.getProjectPresetDir(self.core, "proxy")
        Utils.loadPresets(presetDir, self.proxyPresets, ".p_preset")

        self._action = None

        self.setWindowTitle("FFMPEG Proxy Presets")

        self.setupUI()
        self.connectEvents()
        self.populateTable()

        logger.debug("Loaded Proxy Presets Editor")


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1700, min(2500, calc_width))
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Create table
        self.headers = self.proxyPresets.getHeaders()
        rows = self.proxyPresets.getNumberPresets()
        self.tw_presets = QTableWidget(rows, len(self.headers), self)
        self.tw_presets.setHorizontalHeaderLabels(self.headers)
        self.tw_presets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tw_presets.setSelectionBehavior(QTableWidget.SelectRows)
        self.tw_presets.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tw_presets.setShowGrid(False)
        self.tw_presets.setStyleSheet("""
            QTableView::item {
                border-right: 1px solid grey;
            }
        """)

        #   Footer Buttons
        lo_buttonBox    = QHBoxLayout()
        self.b_moveup   = QPushButton("Move Up")
        self.b_moveDn   = QPushButton("Move Down")
        self.b_test     = QPushButton("Validate Preset")
        self.b_save     = QPushButton("Save")
        self.b_cancel   = QPushButton("Cancel")

        lo_buttonBox.addWidget(self.b_moveup)
        lo_buttonBox.addWidget(self.b_moveDn)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_test)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_save)
        lo_buttonBox.addWidget(self.b_cancel)

        #   Add to Main Layout
        lo_main.addWidget(self.tw_presets)
        lo_main.addLayout(lo_buttonBox)

        #   Stretch Columns over Entire Width
        self.tw_presets.horizontalHeader().setStretchLastSection(False)
        self.tw_presets.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        ##   ToolTips

        #   Make Tooltip Lines as Pairs of Label and Description
        tip_lines = [
            ("Name:", "Short name to be used in the UI<br>(max 20 chars and normal symbols)"),

            ("Description:", "Blurb to describe the Preset (optional)"),

            ("Global Parameters:", textwrap.dedent("""\
                ffmpeg Global args (before the input args)
                <div style='margin-left:20px;'>- This are parameters such as:</div>
                <table style='margin-left:40px;'>
                    <tr><td><code>-GPU hardware configuration</code></td></tr>
                    <tr><td><code>-Threading settings</code></td></tr>
                    <tr><td><code>-Logging options</code></td></tr>
                </table>
            """)),

            ("Video Parameters:", textwrap.dedent("""\
                ffmpeg output Video transcode args
                <div style='margin-left:20px;'>- must contain -c:v and the Codec</div>
                <div style='margin-left:20px;'>- should not contain scaling args (that is handled automatically)</div>
                <div style='margin-left:20px;'>- may contain other args such as:</div>
                <table style='margin-left:40px;'>
                    <tr><td><code>-b:v</code></td><td>(bitrate)</td></tr>
                    <tr><td><code>-crf</code></td><td>(constant rate factor)</td></tr>
                    <tr><td><code>-preset</code></td><td>(quality/speed presets)</td></tr>
                    <tr><td><code>-pix_fmt</code></td><td>(colorspace)</td></tr>
                </table>
            """)),

            ("Audio Parameters:", textwrap.dedent("""\
                ffmpeg output Audio args
                <div style='margin-left:20px;'>- if blank will copy existing audio stream</div>
                <div style='margin-left:20px;'>- using -an will encode no audio</div>
                <div style='margin-left:20px;'>- may contain other audio args</div>
            """)),

            ("Extension:",
                "Output file extension (.mov, .mp4, etc)<br>"
                "The extension (container) must be compatible with the video Codec used"
            ),

            ("Multiplier:",
                "Percentage factor of the generated proxy size to the original.<br>"
                "(e.g. 0.15 is 15% of the original filesize)<br><br>"
                "Used only to estimate the generation progress and has no effect on the resulting file.<br><br>"
                "The initial multiplier does not have to be precise, as<br>"
                "the multiplier will automatically be updated each time a<br>"
                "Proxy is generated."
            ),
        ]

        #   Convert to HTML Table
        tip = "<table>"
        for label, description in tip_lines:
            tip += f"<tr><td style='padding-right: 15px;'>{label}</td><td>{description}</td></tr>"
            tip += "<tr><td colspan='2'>&nbsp;</td></tr>"
        tip += "</table>"
        
        self.tw_presets.setToolTip(tip)

        tip = """
        Run a quick test on the Preset to validate.

        This will check various points such as:
        - Acceptable Preset Name
        - File extension is applicable to the encode codec
        - Video parameters contain the required args
        - Audio parameters contain the required args
        - Multiplier is in the correct format

        It will also perform a small test ffmpeg transcode with the settings.
        """
        self.b_test.setToolTip(tip)

        self.b_moveup.setToolTip("Move Selected Preset Up One Row")
        self.b_moveDn.setToolTip("Move Selected Preset Down One Row")
        self.b_save.setToolTip("Save Changes and Close Window")
        self.b_cancel.setToolTip("Discard Changes and Close Window")


    #   Make Signal Connections
    def connectEvents(self):
        self.tw_presets.customContextMenuRequested.connect(lambda x: self.rclList(x, self.tw_presets))

        self.b_test.clicked.connect(self._onValidate)
        self.b_moveup.clicked.connect(self._onMoveUp)
        self.b_moveDn.clicked.connect(self._onMoveDown)
        self.b_save.clicked.connect(lambda: self._onFinish("Save"))
        self.b_cancel.clicked.connect(lambda: self._onFinish("Cancel"))


    def rclList(self, pos, lw):
        cpos = QCursor.pos()
        item = lw.itemAt(pos)

        rcmenu = QMenu(self)
        sc = self.origin.sourceBrowser.shortcutsByAction

        #   Dummy Separator
        def _separator():
            gb = QGroupBox()
            gb.setFlat(False)
            gb.setFixedHeight(15)
            action = QWidgetAction(self)
            action.setDefaultWidget(gb)
            return action

        #   If Called from Item
        if item:
            row = item.row()
            nameItem = self.tw_presets.item(row, 0)

            Utils.createMenuAction("Edit Preset", sc, rcmenu, self, lambda: self.editPreset(item=nameItem))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Export Preset to File", sc, rcmenu, self, lambda: self.exportPreset(item=nameItem))
            Utils.createMenuAction("Save Preset to Local Machine", sc, rcmenu, self, lambda: self.saveToLocal(item=nameItem))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Delete Preset", sc, rcmenu, self, lambda: self.deletePreset(item=nameItem))

            rcmenu.addAction(_separator())

        #   Always Displayed
        Utils.createMenuAction("Create New Preset", sc, rcmenu, self, lambda: self.editPreset(addNew=True))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Import Preset from File", sc, rcmenu, self, lambda: self.importPreset())
        Utils.createMenuAction("Import Preset from Local Directory", sc, rcmenu, self, lambda: self.importPreset(local=True))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Open Project Presets Directory", sc, rcmenu, self, lambda: self.openPresetsDir(project=True))
        Utils.createMenuAction("Open Local Presets Directory", sc, rcmenu, self, lambda: self.openPresetsDir(project=False))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Gets Called when Window is Displayed
    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.adjustColumnWidths)


    #   Adjusts Column Widths to fit Window
    def adjustColumnWidths(self):
        total_width = self.tw_presets.viewport().width()

        #   Column weights (column index → weight)
        weights = {
            0: 1.3,  # Name
            1: 3.2,  # Description
            2: 2.0,  # Global Params
            3: 3.2,  # Video Params
            4: 1.5,  # Audio Params
            5: 0.5,  # Extension
            6: 0.5   # Compression Multiplier
        }

        total_weight = sum(weights.values())
        #   Iterate and Set Widths
        for col in range(self.tw_presets.columnCount()):
            weight = weights.get(col, 1)
            col_width = int((weight / total_weight) * total_width)
            self.tw_presets.setColumnWidth(col, col_width)


    def populateTable(self):
        try:
            #   Clear Table
            self.tw_presets.setRowCount(0)

            for preset in self.proxyPresets.getOrderedPresets():
                row = self.tw_presets.rowCount()
                self.tw_presets.insertRow(row)
                self.tw_presets.setItem(row, 0, QTableWidgetItem(preset.name))

                for col, key in enumerate(self.headers[1:], start=1):
                    value = preset.data.get(key, "")
                    self.tw_presets.setItem(row, col, QTableWidgetItem(str(value)))

            #   Re-Apply Widths
            QTimer.singleShot(0, self.adjustColumnWidths)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Proxy Presets Table:\n{e}")


    #   Opens File Explorer to Preset Dir (Project or Local Plugin)
    def openPresetsDir(self, project):
        if project:
            presetDir = Utils.getProjectPresetDir(self.core, "proxy")
        else:
            presetDir = Utils.getLocalPresetDir("proxy")

        Utils.openInExplorer(self.core, presetDir)


    #   Import Preset from File
    def importPreset(self, local=False):
        try:
            importData = Utils.importPreset(self.core, "proxy", local=local)

            if importData:
                presetName = importData["name"]
                self.proxyPresets.addPreset(presetName, importData["data"])

                self.populateTable()
                logger.debug(f"Imported Preset '{presetName}'")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Import Preset: {e}")


    #   Export Preset to Selected Location
    def exportPreset(self, item):
        try:
            #   Get Preset Name and Data
            pName = item.text()
            pData = self.proxyPresets.getPresetData(item.text())

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return

        Utils.exportPreset(self.core, "proxy", pName, pData)
        logger.debug(f"Exported Preset {pName}")


    #   Saves Preset to Local Plugin Dir (to be used for all Projects)
    def saveToLocal(self, item):
        try:
            pName = item.text()
            currData = self.proxyPresets.getPresetData(pName)

            pData = {"name": pName,
                     "data": currData}

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return
        
        Utils.savePreset(self.core, "proxy", pName, pData, project=False)


    #   Gets Selected Preset Data and Displays Preset Editor
    def editPreset(self, addNew=False, item=None):
        if addNew:
            #   Insert Blank Row after Current
            row = max(0, self.tw_presets.currentRow() + 1)
            self.tw_presets.insertRow(row)

            for col in range(self.tw_presets.columnCount()):
                self.tw_presets.setItem(row, col, QTableWidgetItem(""))

            self.tw_presets.selectRow(row)

        row = self.tw_presets.currentRow()
        if row < 0: 
            return
        
        self.tw_presets.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.tw_presets.editItem(self.tw_presets.item(row, 0))


    #   Remove Selected Preset
    def deletePreset(self, item):
        row = item.row()

        #   Get Selected Preset Name
        presetItem = self.tw_presets.item(row, 0)
        presetName = presetItem.text() if presetItem else "Unknown"

        #   Confirmation Dialogue
        title = "Delete Template"
        text = f"Would you like to remove the Preset:\n\n{presetName}"
        buttons = ["Remove", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Remove":
            self.tw_presets.removeRow(row)
            Utils.deletePreset(self.core, "proxy", presetName)
            self.proxyPresets.removePreset(presetName)


    #   Handle Tests for Preset
    def _onValidate(self):
        row = self.tw_presets.currentRow()
        if row == -1:
            self.core.popup(title="No Selection", text="Please Select a Preset to Validate.")
            return

        #   Get data from the table
        name    = self.tw_presets.item(row, 0).text()
        desc    = self.tw_presets.item(row, 1).text()
        glob  = self.tw_presets.item(row, 2).text()
        vid     = self.tw_presets.item(row, 3).text()
        aud     = self.tw_presets.item(row, 4).text()
        ext     = self.tw_presets.item(row, 5).text()
        mult    = self.tw_presets.item(row, 6).text()

        #   Make Preset Dict
        preset = {
            "Description": desc,
            "Global_Parameters": glob,
            "Video_Parameters": vid,
            "Audio_Parameters": aud,
            "Extension": ext,
            "Multiplier": mult
        }

        #   Get Full Validation Results
        results = self._validatePreset(name, preset)

        #   Format Output
        lines = [f"Preset '{name}' Validation Report:\n"]

        for label, passed, msg in results:
            if passed:
                lines.append(f"{label} — Passed")
                lines.append("")
            else:
                lines.append(f"{label} — Failed: {msg}")
                lines.append("")

        #   Show Popup
        title="Preset Validation Results"
        text="\n".join(lines)
        DisplayPopup.display(text, title, xScale=4, yScale=3)


    #   Runs Several Sanity Checks on Presets
    def _validatePreset(self, name, data):
        ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))

        results = []

        # 1. Preset Name Check
        valid_name_pattern = re.compile(
            r'^[A-Za-z0-9 \-!@#$%^&()_+=.,;{}\[\]~`^]{1,20}$'
        )

        if not name:
            results.append(("Preset Name", False, "Preset name cannot be blank."))

        elif not valid_name_pattern.match(name):
            results.append((
                "Preset Name", 
                False, 
                f"'{name}' is not valid.\n\n"
                "           Allowed characters: letters, numbers, spaces, dashes, underscores, and common symbols.\n\n"
                "           Length: 1-20 characters.\n\n"
                "           Not allowed: \\ / : * ? \" < > |"
            ))
        else:
            results.append(("Preset Name", True, ""))

        # 2. FFmpeg Check
        if not os.path.isfile(ffmpegPath):
            results.append(("FFmpeg Executable", False, "FFmpeg was not found"))
        else:
            results.append(("FFmpeg Executable", True, ""))

        # 3. Extension check
        ext = data["Extension"]
        if not re.match(r'^\.\w+$', ext):
            results.append(("Output Extension", False, "Must begin with a period (e.g., .mp4)"))
        else:
            results.append(("Output Extension", True, ""))

        # 4. Required codec flags
        if "-c:v" not in data["Video_Parameters"]:
            results.append(("Video Codec (-c:v)", False, "Missing -c:v in video parameters"))
        else:
            results.append(("Video Codec (-c:v)", True, ""))

        if "-c:a" not in data["Audio_Parameters"]:
            results.append(("Audio Codec (-c:a)", False, "Missing -c:a in audio parameters"))
        else:
            results.append(("Audio Codec (-c:a)", True, ""))

        # 5. Codec compatibility check
        allowed = {
            '.mp4': {'libx264', 'libx265', 'mpeg4', 'h264_nvenc', 'hevc_nvenc'},
            '.mov': {'prores_ks', 'prores_aw', 'dnxhd', 'dnxhr', 'libx264', 'libx265', 'mpeg4'},
            '.mkv': {'libx264', 'libx265', 'vp8', 'vp9', 'av1', 'mpeg4'},
            '.webm': {'vp8', 'vp9', 'libvpx', 'libvpx-vp9'},
            '.avi': {'mpeg4', 'msmpeg4v2', 'libx264', 'libxvid'},
            '.flv': {'flv', 'libx264'},
            '.mxf': {'dnxhd', 'dnxhr', 'mpeg2video', 'libx264'},
            '.mpg': {'mpeg1video', 'mpeg2video'},
        }

        video_tokens = data["Video_Parameters"].split()
        try:
            vid_codec = video_tokens[video_tokens.index("-c:v") + 1]
            if vid_codec not in allowed.get(ext, set()):
                results.append(("Codec Compatibility", False, f"'{vid_codec}' may not be compatible with '{ext}'"))
            else:
                results.append(("Codec Compatibility", True, ""))
        except (ValueError, IndexError):
            results.append(("Codec Compatibility", False, "Unable to determine -c:v codec"))

        # 6. FFmpeg Dry Run
        try:
            cmd = [
                ffmpegPath,
                "-hide_banner", "-v", "error",
            ]

            cmd.extend(shlex.split(data["Global_Parameters"]))

            cmd.extend([
                "-f", "lavfi", "-i", "testsrc=duration=0.1:size=1920x1080:rate=25",
                "-f", "lavfi", "-i", "anullsrc=duration=0.1",
            ])

            cmd.extend(shlex.split(data["Video_Parameters"]))
            cmd.extend(shlex.split(data["Audio_Parameters"]))
            cmd.extend(["-f", "null", "-"])

            testCmd = " ".join(shlex.quote(arg) for arg in cmd)
            logger.status(f"Test FFmpeg command:\n{testCmd}")

            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "timeout": 10,
            }

            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)

            if result.returncode != 0:
                msg = result.stderr.decode("utf-8").strip()
                logger.warning(f"DRY RUN ERROR: \n{msg}")
                results.append(("FFmpeg Dry Run", False, msg))
            else:
                results.append(("FFmpeg Dry Run", True, ""))

        except Exception as e:
            results.append(("FFmpeg Dry Run", False, str(e)))

        # 7. Multiplier validation
        try:
            raw_mult = data.get("Multiplier", "")
            mult = float(raw_mult)
            if 0.001 <= mult <= 5:
                results.append(("Multiplier", True, ""))
            else:
                results.append(("Multiplier", False, f"Multiplier {mult} must be between 0.001 and 5."))
        except (ValueError, TypeError):
            results.append(("Multiplier", False, f"Multiplier '{raw_mult}' must be a number between 0.001 and 5."))

        return results


    def _onMoveUp(self):
        row = self.tw_presets.currentRow()
        if row > 0:
            self._swapRows(row, row-1)
            self.tw_presets.selectRow(row-1)


    def _onMoveDown(self):
        row = self.tw_presets.currentRow()
        if row < self.tw_presets.rowCount() - 1:
            self._swapRows(row, row+1)
            self.tw_presets.selectRow(row+1)


    def _swapRows(self, r1, r2):
        for c in range(self.tw_presets.columnCount()):
            t1 = self.tw_presets.takeItem(r1, c)
            t2 = self.tw_presets.takeItem(r2, c)
            self.tw_presets.setItem(r1, c, t2)
            self.tw_presets.setItem(r2, c, t1)


    def _onFinish(self, action):
        self._action = action
        if action == "Save":
            try:
                self.presetData = {}
                self.presetOrder = []

                data_keys = self.headers[1:]

                for row in range(self.tw_presets.rowCount()):
                    name_item = self.tw_presets.item(row, 0)
                    if not name_item:
                        continue

                    name = name_item.text().strip()
                    self.presetOrder.append(name)

                    data = {}
                    for c, key in enumerate(data_keys, start=1):
                        item = self.tw_presets.item(row, c)
                        data[key] = item.text().strip() if item else ""

                    self.presetData[name] = data

                logger.debug("Proxy Presets data collected successfully.")

            except Exception as e:
                logger.warning(f"ERROR: Failed to Save Proxy Presets:\n{e}")

        self.accept()


    def result(self):
        return self._action


    def getPresets(self):
        return self.presetData, self.presetOrder



#################################################
##############    FILE NAMING   #################


class NamingPopup(QDialog):
    def __init__(self, core, origName, mods=None):
        super().__init__()

        self.core = core
        self.origName = origName

        self.activeMods = []

        #   Make Modifier References List
        self.modDefs = [{"name": cls.mod_name, "description": cls.mod_description, "class": cls} for cls in GetMods()]

        self.result = None

        self.setupUI()
        self.setWindowTitle("File Naming Configuration")

        #   If passed Mods, Load Mods into the UI
        if mods:
            self.loadMods(mods)

        self.refreshUI()

        logger.debug("Loaded NamingPopup")


    def setupUI(self):
        #   Calculate Window Geometry
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width   = screen_geometry.width() // 2.5
        height  = screen_geometry.height() // 1.5
        x_pos   = (screen_geometry.width() - width) // 2
        y_pos   = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Main layout
        lo_main = QVBoxLayout(self)

        #   TOP NAMES SECTION
        lo_top = QVBoxLayout()

        #   Original Name
        lo_origName = QHBoxLayout()
        l_origName = QLabel("Original:")
        l_origName.setFixedWidth(70)
        self.le_origName = QLineEdit()

        lo_origName.addWidget(l_origName)
        lo_origName.addWidget(self.le_origName)

        #   Modified Name
        lo_newName = QHBoxLayout()
        l_newName = QLabel("Modified:")
        l_newName.setFixedWidth(70)
        self.le_newName = QLineEdit()
        lo_newName.addWidget(l_newName)
        lo_newName.addWidget(self.le_newName)

        #   Add Top Layouts
        lo_top.addLayout(lo_origName)
        lo_top.addLayout(lo_newName)
        lo_main.addLayout(lo_top)

        #   MIDDLE MODIFIERS SECTION
        mod_container = QWidget()
        mod_container_layout = QVBoxLayout(mod_container)
        mod_container_layout.setContentsMargins(0, 0, 0, 0)
        mod_container_layout.setSpacing(4)

        self.gb_activeMods = QGroupBox("Active Modifiers")
        self.lo_activeMods = QVBoxLayout()
        self.lo_activeMods.setContentsMargins(4, 4, 4, 4)
        self.lo_activeMods.setSpacing(6)
        self.gb_activeMods.setLayout(self.lo_activeMods)

        mod_container_layout.addWidget(self.gb_activeMods)
        mod_container_layout.addStretch(1)

        mod_scroll = QScrollArea()
        mod_scroll.setWidgetResizable(True)
        mod_scroll.setWidget(mod_container)
        mod_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lo_main.addWidget(mod_scroll, 1)

        #   BOTTOM BUTTONS SECTION
        lo_buttons = QHBoxLayout()
        l_availMods = QLabel("Modifier")
        self.cb_availMods = QComboBox()
        b_addMod = QPushButton(text="Add Modifier")
        b_apply = QPushButton("Apply")
        b_close = QPushButton("Close")

        lo_buttons.addWidget(l_availMods)
        lo_buttons.addWidget(self.cb_availMods)
        lo_buttons.addWidget(b_addMod)
        lo_buttons.addStretch(1)
        lo_buttons.addWidget(b_apply)
        lo_buttons.addWidget(b_close)

        lo_main.addLayout(lo_buttons)

        #   Connections
        b_addMod.clicked.connect(self.onAddModifierClicked)
        b_apply.clicked.connect(lambda: self._onButtonClicked("Apply"))
        b_close.clicked.connect(lambda: self._onButtonClicked("Close"))

        #   ToolTips
        tip = ("Original Un-Altered Name\n\n"
               "To use as an Example:\n"
               "First file is used, or EXAMPLEFILENAME")
        self.le_origName.setToolTip(tip)

        tip = ("Altered Name after all Enabled Modifiers\n\n"
               "This will affect all selected files in the\n"
               "Destination list")
        self.le_newName.setToolTip(tip)

        tip = ("Active Modifier Stack.\n\n"
               "Select desired Modifiers and click Add Modifier\n"
               "to add Mods to Stack")
        self.gb_activeMods.setToolTip(tip)

        self.cb_availMods.setToolTip("Select Modifier Type to add")
        b_addMod.setToolTip("Add Selected Modifier to Stack")
        b_apply.setToolTip("Apply Changes and Close Window")
        b_close.setToolTip("Discard Changes and Close Window")

        self.populateModsCombo()


    #    Add Modifier Names to Combo
    def populateModsCombo(self):
        try:
            self.cb_availMods.clear()

            tipRows = []

            #   Get All Available Mod Details
            for mod in self.modDefs:
                name = mod["name"]
                descrip = mod["description"]
                #   Add to Combobox
                self.cb_availMods.addItem(name)
                #   Add to Tooltip
                tipRows.append(f"<tr><td><b>{name}</b></td><td>{descrip}</td></tr>")

            #   Create Tooltip
            tipHtml = (
                "<html><head/><body>"
                "<table style='min-width: 800px;' cellspacing='6' cellpadding='4'>"
                + "\n".join(tipRows) +
                "</table></body></html>"
            )
            #   Set Tooltip
            self.cb_availMods.setToolTip(tipHtml)

            logger.debug("Populated Mods Combo")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Mods Combo:\n{e}")


    #    Removes all Mod Widgets from Layout
    def clearLayout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

            #   Clear Any Nested Layouts
            elif item.layout():
                self.clearLayout(item.layout())


    #   Updates Filename Text
    def refreshUI(self):
        #   Set Original Name
        self.le_origName.setText(self.origName)
        #    Get Modified Name
        newName = self.applyMods(self.origName)
        #    Set Modified Name
        self.le_newName.setText(newName)


    #   Loads Existing Mods into UI
    def loadMods(self, mods):
        #   Clear List
        self.activeMods = []
        #   Clear Layout
        self.clearLayout(self.lo_activeMods)

        for mod_data in mods:
            try:
                modifierClass = GetModByName(mod_data["mod_type"])
                modifier = CreateMod(modifierClass)
                self.addModToUi(modifier, mod_data)

                logger.debug(f"Loaded Modifier: {modifierClass}")

            except Exception as e:
                logger.debug(f"ERROR:  Unable to add Filename Mod: {modifierClass}:\n{e}")


    #   Creates New Modifier from Selected Combo
    def onAddModifierClicked(self):
        #   Get Mod Name from Combo
        selIndx = self.cb_availMods.currentIndex()
        selMod  = self.modDefs[selIndx]["class"]
        #   Create New Modifier
        modifier = CreateMod(selMod)
        #   Add to UI
        self.addModToUi(modifier)


    #   Creates UI Item for passed Modifier
    def addModToUi(self, modifier, data=None):
        modifier.modChanged.connect(self.refreshUI)

        #   Connect each Mod's Remove button to the UI
        modifier.b_remove.clicked.connect(lambda _, m=modifier: self.removeModifier(m))

        #   Create Layout for the Modifier
        lo_mod = QHBoxLayout()

        #   Add Widgets from Returned getModUI()
        for widget in modifier.getModUI():
            lo_mod.addWidget(widget)

        #   Wrap Layout in a QWidget
        mod_widget = QWidget()
        mod_widget.setLayout(lo_mod)

        #   Add Widget to Mods Layout
        self.lo_activeMods.addWidget(mod_widget)

        #   If passed Existing Mod Settings
        if data:
            modifier.setSettings(data["settings"])
            modifier.isEnabled = data.get("enabled", True)
            modifier.chb_enableCheckbox.setChecked(modifier.isEnabled)

        #   Add Mod to List
        self.activeMods.append((modifier, mod_widget))

        self.refreshUI()


    #   Modify Original Name based on Active Mods
    def applyMods(self, origName):
        #   Start with Orig Name
        newName = origName

        #    Loop Through All Modifiers
        for mod_instance, _ in self.activeMods:
            try:
                #   If Checkbox is Enabled
                if mod_instance.isEnabled:
                    #   Execute Mod's Apply Method
                    newName = mod_instance.applyMod(newName)
                
            except Exception as e:
                logger.warning(f"ERROR:  Unable to Add Filename Modifier:\n{e}")

        return newName
            

    #   Removes Modifier (obviously)
    def removeModifier(self, mod_instance):
        #   Find the Mod and its Associated Widget
        for i, (instance, widget) in enumerate(self.activeMods):
            if instance == mod_instance:
                self.lo_activeMods.removeWidget(widget)

                #   Removes Mod from UI
                widget.setParent(None)
                widget.deleteLater()

                #   Removes Mod from List
                self.activeMods.pop(i)
                break

        self.refreshUI()


    def _onButtonClicked(self, text):
        self.result = text
        self.accept()



#################################################
################    METADATA   ##################


class MetadataEditor(QWidget, Ui_w_metadataEditor):

    def __init__(self, core, origin, loadFilepath=None, parent=None):
        super(MetadataEditor, self).__init__(parent)
        self.core = core
        self.sourceBrowser = origin
        self.projectBrowser = origin.projectBrowser

        self.metaMapPath = os.path.join(self.sourceBrowser.pluginPath,
                                        "Libs",
                                        "UserInterfaces",
                                        "MetaMap.json")
        
        self.sourceOptions = []

        #   Instantiate Metafiles
        self.MetaFileItems = MetaFileItems()

        self.loadMetamap()

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.createFilters()
        self.refresh(loadFilepath)
        self.connectEvents()

        logger.debug("Loaded Metadata Editor")


    def refresh(self, loadFilepath=None):
        WaitPopup.showPopup(parent=self.projectBrowser)

        self.populatePresets()
        self.loadFiles(loadFilepath)
        self.populateEditor()

        WaitPopup.closePopup()


    def configureUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1000, min(2000, calc_width))
        calc_height = screen_geometry.height() // 1.2
        height = max(900, min(2500, calc_height))
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Color MetadataEditor Background
        self.setStyleSheet("""
            #w_metadataEditor {
                background-color: #323537;
                color: #ccc;
            }
        """)

        #   Icons
        icon_filters = QIcon(os.path.join(iconDir, "sort.png"))
        icon_reset = QIcon(os.path.join(iconDir, "reset.png"))
        self.b_filters.setIcon(icon_filters)
        self.b_reset.setIcon(icon_reset)

        #   Build Custom Table Model
        self.MetadataTableModel = MetadataTableModel(
            self.MetadataFieldCollection,
            self.sourceOptions,
            parent=self
        )

        self.tw_metaEditor.setModel(self.MetadataTableModel)

        # Set Section Headers Delegate
        sectionHeaderDelegate = SectionHeaderDelegate(self.tw_metaEditor)
        self.tw_metaEditor.setItemDelegate(sectionHeaderDelegate)

        #   Configure Table
        self.tw_metaEditor.verticalHeader().setVisible(False)
        self.tw_metaEditor.setShowGrid(True)
        self.tw_metaEditor.setGridStyle(Qt.SolidLine)
        self.tw_metaEditor.setAlternatingRowColors(True)
        self.tw_metaEditor.horizontalHeader().setHighlightSections(False)
        self.tw_metaEditor.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tw_metaEditor.setAutoFillBackground(True)

        #   Makes It so Single-click Will Edit a Cell
        self.tw_metaEditor.setEditTriggers(QAbstractItemView.SelectedClicked)

        self.tw_metaEditor.setStyleSheet("""
            QTableView {
                background-color: #2f3136;
                color: #ccc;
                gridline-color: #555;
                alternate-background-color: #313335;
            }
            QHeaderView::section {
                background-color: #444;
                color: #eee;
                padding: 4px;
                border: 1px solid #555;
            }
        """)

        QTimer.singleShot(.1, self.setInitialColumnWidths)
        self.setToolTips()


    #   Set Column Widths After Launch
    def setInitialColumnWidths(self):
        try:
            table_width = self.tw_metaEditor.viewport().width()
            self.tw_metaEditor.setColumnWidth(0, int(table_width * 0.05))
            self.tw_metaEditor.setColumnWidth(1, int(table_width * 0.20))
            self.tw_metaEditor.setColumnWidth(2, int(table_width * 0.30))
            self.tw_metaEditor.horizontalHeader().setStretchLastSection(True)
        except Exception as e:
            logger.warning(f"ERROR: Unable to resize Table Columns:{e}")


    def setToolTips(self):
        tip = ("File Listing\n\n"
               "Select File to View Metadata")
        self.cb_fileList.setToolTip(tip)

        tip = "Opens Metadata Display Window"
        self.b_showMetadataPopup.setToolTip(tip)

        tip = ("Table Display Filters (will  not affect Saved Metadata\n\n"
               "    - Click to Enable/Disable Filters\n"
               "    - Right-click to Configure Filters")
        self.b_filters.setToolTip(tip)

        tip = ("Reset Editor\n\n"
               "This will clear all existing data or changes loaded into the Editor.\n"
               "This will not alter any metadata in the file itself.")
        self.b_reset.setToolTip(tip)

        tip = "Select Metadata Configuration Preset"
        self.cb_presets.setToolTip(tip)

        tip = "Opens Metadata Presets Editor"
        self.b_presets.setToolTip(tip)

        tip = ("Select which types of Metadata Sidecar Files are Generated")
        self.b_sidecarMenu.setToolTip(tip)

        tip = ("Generate Selected Metadata Sidecar Files now.\n"
               "These files will be saved in the selected Destination Directory\n\n"
               "(note: this does not affect the automatic sidecar generation during a transfer)")
        self.b_sidecar_save.setToolTip(tip)

        tip = ("Saves the Current Configuration and\n"
               "closes the Editor")
        self.b_save.setToolTip(tip)

        tip = "Closes the Editor without Saving"
        self.b_close.setToolTip(tip)


    #   Dynamically Build Filters Menu from MetaMap
    def createFilters(self):
        categories = self.MetadataFieldCollection.get_allCategories()

        #   Add Filter Types
        self.filterStates = {
            "Hide Disabled": False,
            "Hide Empty": False,
            }

        #   Add Separator
        self.filterStates["----1"] = False

        #   Add All Categories (default True)
        for cat in categories:
            if cat == "File":
                continue
            self.filterStates[cat] = True

        #   Add Separator
        self.filterStates["----2"] = False


    def connectEvents(self):
        self.cb_fileList.currentIndexChanged.connect(lambda: self.onFileChanged())
        self.b_showMetadataPopup.clicked.connect(lambda: self.showMetaDataPopup())
        self.b_filters.clicked.connect(self.populateEditor)
        self.b_filters.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_filters.customContextMenuRequested.connect(lambda: self.filtersRCL())
        self.b_reset.clicked.connect(self.resetTable)
        self.cb_presets.currentIndexChanged.connect(lambda: self.loadPreset())
        self.b_presets.clicked.connect(self.showPresetsMenu)
        
        self.b_sidecarMenu.clicked.connect(self.sidecarTypeMenu)

        self.b_sidecar_save.clicked.connect(lambda: self.saveSidecar(popup=True))
        self.b_save.clicked.connect(self._onSave)
        self.b_close.clicked.connect(self._onClose)
        

    #   Right Click List for Filters
    def filtersRCL(self):
        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        def _wrapWidget(widget):
            action = QWidgetAction(self)
            action.setDefaultWidget(widget)
            return action
        
        def _separator():
            gb = QGroupBox()
            gb.setFixedHeight(15)
            return _wrapWidget(gb)

        def _applyFilterStates(checkboxRefs, menu):
            for label, cb in checkboxRefs.items():
                self.filterStates[label] = cb.isChecked()
            self.populateEditor()
            menu.close()

        checkboxRefs = {}

        #   Add Filter Checkboxes
        for label, checked in self.filterStates.items():
            if label.startswith("----"):
                rcmenu.addAction(_separator())
                continue

            cb = QCheckBox(label)
            cb.setChecked(checked)
            checkboxRefs[label] = cb
            rcmenu.addAction(_wrapWidget(cb))

        #   Apply Button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")
        b_apply.clicked.connect(lambda: _applyFilterStates(checkboxRefs, rcmenu))
        rcmenu.addAction(_wrapWidget(b_apply))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Sidecar Selection Menu
    def sidecarTypeMenu(self):
        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        #   Helper to Wrap Action in Widget
        def _wrapWidget( widget):
            action = QWidgetAction(self)
            action.setDefaultWidget(widget)
            return action
                
        #   Helper for filtersRCL()
        def _applyFilterStates(checkboxRefs, menu):
            for label, cb in checkboxRefs.items():
                self.sourceBrowser.sidecarStates[label] = cb.isChecked()

            menu.close()

        #   Temporary State Dictionary
        tempStates = self.sourceBrowser.sidecarStates.copy()
        
        checkboxRefs = {}

        #   Checkboxes
        for label, checked in tempStates.items():
            cb = QCheckBox(label)
            cb.setChecked(checked)
            checkboxRefs[label] = cb
            rcmenu.addAction(_wrapWidget(cb))

        #   Vert Dummy Spacer
        spacer = QLabel(" ")
        rcmenu.addAction(_wrapWidget(spacer))

        #   Apply Button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")
        b_apply.clicked.connect(lambda: _applyFilterStates(checkboxRefs, rcmenu))
        rcmenu.addAction(_wrapWidget(b_apply))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Builds MetadataFieldCollection from MetaMap.json
    def loadMetamap(self):
        try:
            with open(self.metaMapPath, "r", encoding="utf-8") as f:
                mData = json.load(f)

            self.metaMap = mData["metaMap"]

        except FileNotFoundError:
            logger.warning("ERROR: MetaMap.json is not found")
            return
        
        try:
            #   Build MetadataFieldCollection
            metadata_fields = []
            for item in self.metaMap:
                field = MetadataField(
                    name=item.get("MetaName", ""),
                    category=item.get("category", "Shot/Scene"),
                    enabled=item.get("enabled", True)
                )
                metadata_fields.append(field)

            self.MetadataFieldCollection = MetadataFieldCollection(metadata_fields)

            logger.debug("Built MetadataFieldCollection from 'MetaMap.json'")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Build MetadataFieldCollection: {e}")


    #   Loads Preset Data and Loads Presets into Combo
    def populatePresets(self):
        self.cb_presets.clear()
        self.cb_presets.addItem("PRESETS")

        orderedPresetNames = self.sourceBrowser.metaPresets.getOrderedPresetNames()

        #   Populate Combobox
        for name in orderedPresetNames:
            self.cb_presets.addItem(name)

        idx = self.cb_presets.findText(self.sourceBrowser.metaPresets.currentPreset)
        if idx != -1:
            self.cb_presets.setCurrentIndex(idx)

        self.cb_presets.setSizeAdjustPolicy(QComboBox.AdjustToContents)


    #   Loads Files into MetaFileItems an Combo
    def loadFiles(self, loadFilepath=None):
        #   Get All Checked FileTiles in Dest List
        try:
            fileTiles = self.sourceBrowser.getAllDestTiles(onlyChecked=False)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Destination FileTiles")
            return

        activeFiles = []

        #   Itterate through Files
        for fileTile in fileTiles:
            try:
                #   Get File Name and Check if it Exists in the MetaFileItems
                filePath = fileTile.data.get("source_mainFile_path", "")
                fileName_orig = Utils.getBasename(filePath)
                fileName_mod = fileTile.getModifiedName(fileName_orig)
                activeFiles.append(fileName_orig)
                existing_item = self.MetaFileItems.getByName(fileName_orig)

                #   If it Exists, Refresh the fileTile Reference
                if existing_item:
                    existing_item.fileName=fileName_orig
                    existing_item.fileName_mod = fileName_mod
                    existing_item.fileTile = fileTile

                #   Or Add New MetaFileItem
                else:
                    if not existing_item:
                        metadata = Utils.getGroupedCombinedMetadata(filePath)                   
                        metadata = MetadataModel(metadata)

                        self.MetaFileItems.addItem(
                            filePath=filePath,
                            fileName=fileName_orig,
                            fileName_mod = fileName_mod,
                            fileTile=fileTile,
                            metadata=metadata,
                        )

            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{fileTile}': {e}")

        #   Update Active Files List
        self.MetaFileItems.activeFiles = activeFiles

        #   Update the File List Combobox
        self.cb_fileList.blockSignals(True)
        self.cb_fileList.clear()
        try:
            self.cb_fileList.addItems(activeFiles)

            #   Select Passed File
            if loadFilepath:
                fileName = Utils.getBasename(loadFilepath)
                idx = self.cb_fileList.findText(fileName)
                if idx != -1:
                    self.cb_fileList.setCurrentIndex(idx)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")

        finally:
            self.cb_fileList.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            self.cb_fileList.blockSignals(False)

        self.onFileChanged()


    def onFileChanged(self, filePath=None):
        if filePath:
            path = filePath
        else:
            if self.cb_fileList.count() < 1:
                return
            
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.MetaFileItems.getByName(fileName)
                path = fileItem.filePath

            except Exception as e:
                logger.warning(f"ERROR: Unable to get FilePath from Selected File: {e}")
                return
            
        #   Bold Current Viewed File in Combo
        current_idx = self.cb_fileList.currentIndex()
        for i in range(self.cb_fileList.count()):
            font = self.cb_fileList.font()
            font.setBold(i == current_idx)
            self.cb_fileList.setItemData(i, font, Qt.FontRole)

        #   Extract Metadata and add to Model Class
        metadata = Utils.getGroupedCombinedMetadata(path)
        metadata = MetadataModel(metadata)

        #   Update Table Model
        self.MetadataTableModel.sourceOptions = self.sourceOptions

        #   Create Combox Delegate
        self.ComobDelegate = MetadataComboBoxDelegate(metadata, parent=self)
        self.MetadataTableModel.combo_delegate = self.ComobDelegate
        self.tw_metaEditor.setItemDelegateForColumn(MetadataTableModel.COL_SOURCE, self.ComobDelegate)

        #   Create Checkbox Delegate
        self.CheckboxDelegate = CheckboxDelegate()
        self.MetadataTableModel.checkbox_delegate = self.CheckboxDelegate
        self.tw_metaEditor.setItemDelegateForColumn(MetadataTableModel.COL_ENABLED, self.CheckboxDelegate)
        
        #   Add File Names to Fixed Rows
        for field in self.MetadataTableModel.collection.fields_all:
            if field.name == "File Name":
                field.currentValue = fileItem.fileName_mod
            elif field.name == "Original File Name":
                field.currentValue = fileItem.fileName

        #   Refresh Table
        self.MetadataTableModel.layoutChanged.emit()

        self.loadPreset()


    #   Loads MetaFieldItems into the Table
    def populateEditor(self):
        useFilters = self.b_filters.isChecked()
        self.MetadataFieldCollection.applyFilters(self.filterStates, useFilters, self.metaMap)
        self.MetadataTableModel.layoutChanged.emit()


    #   Displays Popup with Selected File's Metadata
    def showMetaDataPopup(self, filePath=None):
        #   If passed
        if filePath:
            path = filePath
            fileName = Utils.getBasenamefilePath()

        #   Get Selected File from Combo
        else:
            fileName = self.cb_fileList.currentText()
            fileItem = self.MetaFileItems.getByName(fileName)
            path = fileItem.filePath
            fileName = fileItem.fileName

        #   Get and Format Metadata
        try:
            Utils.displayCombinedMetadata(path)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Display Grouped Metadata: {e}")
            return


    #   Saves Presets to Config
    def savePresets(self):
        mData = {
            "currMetaPreset": self.sourceBrowser.metaPresets.currentPreset,
            "metaPresetOrder": self.sourceBrowser.metaPresets.presetOrder,
            "sidecarStates": self.sourceBrowser.sidecarStates
            }

        #   Save to Project Config
        self.sourceBrowser.plugin.saveSettings(key="metadataSettings", data=mData)


    #   Displays Preset Popup
    def showPresetsMenu(self):
        #   Display Meta Presets Popup
        presetPopup = MetaPresetsPopup(self.core, self)

        #   If Saved Button Pressed
        if presetPopup.exec() == QDialog.Accepted:
           self.savePresets()
           self.populatePresets()


    #   Loads Preset into the Table
    def loadPreset(self, presetName=None, onlyExisting=True):
        if not presetName:
            presetName = self.cb_presets.currentText()

        try:
            pData = self.sourceBrowser.metaPresets.getPresetData(presetName)
            if not pData:
                logger.debug(f"Preset Not Found: {presetName}")
                return
        
        except Exception as e:
            logger.warning(f"ERROR: Unable to get Preset from Preset Name: {e}")
            return
        
        #   Build Lookup from List
        presetFields = {row["field"]: row for row in pData}

        if len(self.MetaFileItems.allItems()) < 1:
            return
        
        for row, field in enumerate(self.MetadataFieldCollection.fields):
            #   Skip UNIQUE Rows
            if field.sourceField == "- UNIQUE -":
                continue

            if field.name in presetFields:
                info = presetFields[field.name]

                field.enabled = info.get("enabled", False)
                field.sourceField = info.get("sourceField", "")

                #   Preset field is NONE
                if field.sourceField == "- NONE -":
                    field.currentValue = ""

                #   Preset Field is GLOBAL
                elif field.sourceField == "- GLOBAL -":
                    globalValue = info.get("currentData", "")
                    if globalValue:
                        field.currentValue = globalValue

                else:
                    #   Check sourceField Exists in Metadata
                    if field.sourceField not in self.ComobDelegate.display_strings:
                        #   Not present Fallback to NONE
                        field.sourceField = "- NONE -"
                        field.currentValue = ""
                    else:
                        #   Exists Use Metadata
                        field.currentValue = self.ComobDelegate.getValueForField(field.sourceField)
            else:
                if not onlyExisting:
                    field.enabled = False
                    field.sourceField = "- NONE -"
                    field.currentValue = ""

        #   Update Table
        self.MetadataTableModel.layoutChanged.emit()


    #   Resets Table to Default None's
    def resetTable(self):
        title = "Reset Metadata Table"
        text = (
            "Would you like to clear all existing data or changes loaded into the Editor?\n\n"
            "This will not alter any metadata in the file itself."
        )
        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            self.cb_presets.setCurrentIndex(0)

            fieldNames = self.MetadataFieldCollection.get_allFieldNames()
            for fieldName in fieldNames:
                if fieldName in ["File Name", "Original File Name"]:
                    continue

                field = self.MetadataFieldCollection.get_fieldByName(fieldName)
                field.enabled = False
                field.sourceField = "- NONE -"
                field.currentValue = ""

            self.MetadataTableModel.layoutChanged.emit()
            logger.debug("Reset Metadata Editor")


    #   Returns Current Data from Editor
    def getCurrentData(self, filterNone=True):
        currentData = []

        fieldNames = self.MetadataFieldCollection.get_allFieldNames()
        for fieldName in fieldNames:
            field = self.MetadataFieldCollection.get_fieldByName(fieldName)
            sourceField = field.sourceField

            if filterNone and (not sourceField or sourceField == "- NONE -"):
                continue

            fieldData = {
                "field": field.name,
                "enabled": field.enabled,
                "sourceField": field.sourceField,
                "currentData": field.currentValue
                }

            currentData.append(fieldData)

        return currentData


    #   Saves Selected Metadata Sidecar Files
    def saveSidecar(self, basePath=None, popup=False):
        #   Use Passed Path
        if basePath:
            sidecarPath_base = basePath

        #   Or Save to Destination Path
        else:
            if not os.path.exists(self.sourceBrowser.destDir):
                self.core.popup("There is no Destination Directory Selected.\n\n"
                                "Aborting Sidecar Generation.")
                return
            
            report_uuid = Utils.createUUID()
            timestamp  = datetime.now()
            timestamp_str  = timestamp.strftime("%Y-%m-%d_%H%M%S")
            sideCarFilename = f"MetadataSidecar_{timestamp_str}_{report_uuid}"
            sidecarPath_base = os.path.join(self.sourceBrowser.destDir, sideCarFilename)
            

        #   Create .CSV
        if self.sourceBrowser.sidecarStates["Resolve (.csv)"]:
            self.saveSidecarCSV(sidecarPath_base)

        #   Create .ALE
        if self.sourceBrowser.sidecarStates["Avid (.ale)"]:
            self.saveSidecarALE(sidecarPath_base)

        if popup:
            self.core.popup(f"Created Sidecar Files ({sidecarPath_base})")
    

    #   Create Resolve Type .CSV
    def saveSidecarCSV(self, sidecarPath_base):
        sidecarPath = sidecarPath_base + ".csv"

        #   Get All Field Names
        fieldNames = self.MetadataFieldCollection.get_allFieldNames()

        #   Open CSV file to Write To
        with open(sidecarPath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            #   Write Header
            writer.writerow(fieldNames)

            #   Iterate Over each File
            for fileItem in self.MetaFileItems.allItems(active=True):
                #   Skip Unchecked File Tiles
                if not fileItem.fileTile.isChecked():
                    continue

                try:
                    row = []
                    metadata = fileItem.metadata

                    for fieldName in fieldNames:
                        field = self.MetadataFieldCollection.get_fieldByName(fieldName)

                        #   Skip if the Field Doesn't Exist
                        if not field:
                            row.append("")
                            continue

                        #   Add File Name Fixed Cells
                        if field.name == "File Name":
                            row.append(fileItem.fileName_mod)
                            continue
                        if field.name == "Original File Name":
                            row.append(fileItem.fileName)
                            continue

                        #   Get Currently Selected Source
                        sourceField = field.sourceField

                        #   Handle Each Type of Source
                        if not sourceField or sourceField == "- NONE -":
                            row.append("")

                        elif sourceField == "- GLOBAL -":
                            row.append(field.currentValue)

                        elif sourceField == "- UNIQUE -":
                            value = self.MetaFileItems.get_uniqueValue(fileItem, field.name)
                            row.append(value)

                        #   Normal Metadata Field
                        else:
                            row.append(metadata.get_valueFromSourcefield(sourceField))

                    writer.writerow(row)

                except Exception as e:
                    logger.warning(f"Failed to Generate Metadata File Row in the .CSV file: {e}")

        logger.status(f"Saved .CSV sidecar to: {sidecarPath}")


    def saveSidecarALE(self, sidecarPath_base):
        sidecarPath = sidecarPath_base + ".ale"

        fieldNames = self.MetadataFieldCollection.get_allFieldNames()
        
        with open(sidecarPath, "w", newline="", encoding="utf-8") as file:
            # --- Heading Section ---
            file.write("Heading\n")
            file.write("FIELD_DELIM\tTABS\n")
            file.write("VIDEO_FORMAT\tCUSTOM\n")
            file.write("AUDIO_FORMAT\t48kHz\n")
            file.write("FPS\t24\n\n")

            # --- Column Section ---
            file.write("Column\n")
            file.write("\t".join(fieldNames) + "\n\n")

            # --- Data Section ---
            file.write("Data\n")

            for fileItem in self.MetaFileItems.allItems(active=True):
                if not fileItem.fileTile.isChecked():
                    continue

                try:
                    row = []
                    metadata = fileItem.metadata

                    for fieldName in fieldNames:
                        field = self.MetadataFieldCollection.get_fieldByName(fieldName)

                        if not field:
                            row.append("")
                            continue

                        if field.name == "File Name":
                            row.append(fileItem.fileName_mod)
                            continue
                        if field.name == "Original File Name":
                            row.append(fileItem.fileName)
                            continue

                        sourceField = field.sourceField
                        if not sourceField or sourceField == "- NONE -":
                            row.append("")
                        elif sourceField == "- GLOBAL -":
                            row.append(field.currentValue)
                        elif sourceField == "- UNIQUE -":
                            row.append(self.MetaFileItems.get_uniqueValue(fileItem, field.name))
                        else:
                            row.append(metadata.get_valueFromSourcefield(sourceField))

                    file.write("\t".join(row) + "\n")

                except Exception as e:
                    logger.warning(f"Failed to Generate Metadata File Row in the .ALE file: {e}")

        logger.status(f"Saved .ALE sidecar to: {sidecarPath}")


    #   Saves and Closes the MetaEditor
    def _onSave(self):
        preset = self.cb_presets.currentText()
        if preset == "PRESETS":
            preset = ""
            
        self.sourceBrowser.metaPresets.currentPreset = preset

        self.savePresets()
        self.sourceBrowser.sourceFuncts.updateUI()
        self.close()


    #   Closes the MetaEditor
    def _onClose(self):
        self.close()



class MetaPresetsPopup(QDialog):
    def __init__(self, core, metaEditor):
        super().__init__(metaEditor)
        self.core = core
        self.metaEditor = metaEditor
        self.sourceBrowser = metaEditor.sourceBrowser
        self.metaPresets = self.sourceBrowser.metaPresets

        self.setWindowTitle("MetaData Presets")

        self.setupUI()
        self.connectEvents()
        self.refreshList()

        logger.debug("Loaded Metadata Presets Dialogue")


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 5
        width = max(200, min(800, calc_width))
        calc_height = screen_geometry.height() // 2
        height = max(400, min(1000, calc_height))
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Create List
        self.lw_presetList = QListWidget(self)
        self.lw_presetList.setContextMenuPolicy(Qt.CustomContextMenu)

        #   Footer Buttons
        lo_buttons      = QHBoxLayout()
        self.b_moveUp   = QPushButton("Move Up")
        self.b_moveDn   = QPushButton("Move Down")
        self.b_save     = QPushButton("Save")
        self.b_close    = QPushButton("Close")
        
        lo_buttons.addWidget(self.b_moveUp)
        lo_buttons.addWidget(self.b_moveDn)
        lo_buttons.addStretch()
        lo_buttons.addWidget(self.b_save)
        lo_buttons.addWidget(self.b_close)

        #   Add to Main Layout
        lo_main.addWidget(self.lw_presetList)
        lo_main.addLayout(lo_buttons)

        #   ToolTips
        self.b_moveUp.setToolTip("Moves Selected Preset UP one Row")
        self.b_moveDn.setToolTip("Moves Selected Preset DOWN one Row")
        self.b_save.setToolTip("Saves Updates and Closes the Editor")
        self.b_close.setToolTip("Close the Preset Editor")

        tip = ("List of Available Metadata Presets\n\n"
               "   - Right-click Preset to Edit or Delete\n"
               "   - Right-click Empty space to Add New Preset or Restore Defaults Presets")
        self.lw_presetList.setToolTip(tip)


    def connectEvents(self):
        self.lw_presetList.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_presetList))

        self.b_moveUp.clicked.connect(self._onMoveUp)
        self.b_moveDn.clicked.connect(self._onMoveDown) 
        self.b_save.clicked.connect(lambda: self._onSave())
        self.b_close.clicked.connect(lambda: self._onClose())


    def rclList(self, pos, lw):
        cpos = QCursor.pos()
        item = lw.itemAt(pos)
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

        #   If Called from Item
        if item:
            Utils.createMenuAction("Edit Preset", sc, rcmenu, self, lambda: self.editPreset(item=item))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Export Preset to File", sc, rcmenu, self, lambda: self.exportPreset(item=item))
            Utils.createMenuAction("Save Preset to Local Machine", sc, rcmenu, self, lambda: self.saveToLocal(item=item))

            rcmenu.addAction(_separator())

            Utils.createMenuAction("Delete Preset", sc, rcmenu, self, self.deletePreset)

            rcmenu.addAction(_separator())

        #   Always Displayed
        Utils.createMenuAction("Create New Preset from Current", sc, rcmenu, self, lambda: self.editPreset(addNew=True))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Import Preset from File", sc, rcmenu, self, lambda: self.importPreset())
        Utils.createMenuAction("Import Preset from Local Directory", sc, rcmenu, self, lambda: self.importPreset(local=True))

        rcmenu.addAction(_separator())

        Utils.createMenuAction("Open Project Presets Directory", sc, rcmenu, self, lambda: self.openPresetsDir(project=True))
        Utils.createMenuAction("Open Local Presets Directory", sc, rcmenu, self, lambda: self.openPresetsDir(project=False))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Adds Presets to List
    def refreshList(self):
        self.lw_presetList.clear()
        self.lw_presetList.addItems(self.metaPresets.getOrderedPresetNames())


    #   Import Preset from File
    def importPreset(self, local=False):
        try:
            importData = Utils.importPreset(self.core, "metadata", local=local)

            if importData:
                presetName = importData["name"]
                self.metaPresets.addPreset(presetName, importData["data"])

                self.refreshList()
                self.updateMetaPresetsOrder()

                logger.debug(f"Imported Preset '{presetName}'")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Import Preset: {e}")


    #   Export Preset to Selected Location
    def exportPreset(self, item):
        try:
            #   Get Preset Name and Data
            pName = item.text()
            pData = self.metaPresets.getPresetData(item.text())

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return

        Utils.exportPreset(self.core, "metadata", pName, pData)
        logger.debug(f"Exported Preset {pName}")



    #   Gets Selected Preset Data and Displays Preset Editor
    def editPreset(self, addNew=False, item=None):
        if addNew:
            presetName = ""
            currData = self.metaEditor.getCurrentData(filterNone=True)
        else:
            presetName = item.text()
            currData = self.metaPresets.getPresetData(item.text())

        currPresetData = {
            "name": presetName,
            "data": currData
        }

        resultData = self.openPresetEditor(currPresetData)

        if resultData:
            pName = resultData["name"]
            pData = {"name": pName,
                     "data": resultData["data"]}
            
            #   Save Preset to Project Preset Dir
            Utils.savePreset(self.core, "metadata", pName, pData, project=True)

            #   Update Presets Dict
            self.metaPresets.addPreset(pName, resultData["data"])

            self.refreshList()
            self.updateMetaPresetsOrder()


    #   Opens File Explorer to Preset Dir (Project or Local Plugin)
    def openPresetsDir(self, project):
        if project:
            presetDir = Utils.getProjectPresetDir(self.core, "metadata")
        else:
            presetDir = Utils.getLocalPresetDir("metadata")

        Utils.openInExplorer(self.core, presetDir)


    #   Opens Preset Editor to Edit/Create Preset
    def openPresetEditor(self, presetData):
        presetEditor = MetaPresetsEditor(self.core, self, presetData)

        if presetEditor.exec() == QDialog.Accepted:
            return presetEditor.resultData
        

    #   Saves Preset to Local Plugin Dir (to be used for all Projects)
    def saveToLocal(self, item):
        try:
            pName = item.text()
            currData = self.metaPresets.getPresetData(pName)

            pData = {"name": pName,
                     "data": currData}

        except Exception as e:
            logger.warning(f"ERROR: Unable to Get Preset Data for Export: {e}")
            return
        
        Utils.savePreset(self.core, "metadata", pName, pData, project=False)


    #   Remove Selected Preset
    def deletePreset(self):
        row = self.lw_presetList.currentRow()
        if row < 0:
            return

        #   Get Selected Preset Name
        presetItem = self.lw_presetList.item(row)
        presetName = presetItem.text() if presetItem else "Unknown"

        #   Confirmation Dialogue
        title = "Delete Preset"
        text = f"Would you like to remove the Preset:\n\n{presetName}"
        buttons = ["Remove", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Remove":
            self.lw_presetList.takeItem(row)
            Utils.deletePreset(self.core, "metadata", presetName)
            self.metaPresets.removePreset(presetName)

            self.updateMetaPresetsOrder()

   
    def _onMoveUp(self):
        row = self.lw_presetList.currentRow()
        if row > 0:
            item = self.lw_presetList.takeItem(row)
            self.lw_presetList.insertItem(row - 1, item)
            self.lw_presetList.setCurrentRow(row - 1)

        self.updateMetaPresetsOrder()


    def _onMoveDown(self):
        row = self.lw_presetList.currentRow()
        if row < self.lw_presetList.count() - 1 and row != -1:
            item = self.lw_presetList.takeItem(row)
            self.lw_presetList.insertItem(row + 1, item)
            self.lw_presetList.setCurrentRow(row + 1)
        
        self.updateMetaPresetsOrder()


    #   Replaces 'metaPresets' Dict with New Verion with new Ordering
    def updateMetaPresetsOrder(self):
        #   Get New Order from the List Widget
        new_order = [self.lw_presetList.item(i).text() for i in range(self.lw_presetList.count())]
        self.metaPresets.presetOrder = new_order


    #   Stores Selected Preset Name for Main Code to Load
    def _onSave(self):
        self.updateMetaPresetsOrder()
        # self.metaEditor.metaPresets = self.metaPresets_copy
        self.accept()


    def _onClose(self):
        self.reject()



class MetaPresetsEditor(QDialog):
    def __init__(self, core, metaPresetPopup, presetData):
        super().__init__(metaPresetPopup)
        self.core = core
        self.metaPresetPopup = metaPresetPopup
        self.presetData = presetData

        self.setWindowTitle("Metadata Preset Editor")

        self.setupUI()
        self.connectEvents()
        self.loadData(presetData)

        logger.debug("Loaded Metadata Preset Editor")

        
    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 2.5
        width = max(200, min(1200, calc_width))
        calc_height = screen_geometry.height() // 1.5
        height = max(400, min(1000, calc_height))
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Header
        lo_header       = QHBoxLayout()
        l_pName         = QLabel("Preset Name")
        self.le_pName   = QLineEdit()

        lo_header.addWidget(l_pName)
        lo_header.addWidget(self.le_pName)

        spacer = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)

        #   Main Table
        self.te_presetEditor = QPlainTextEdit(self)

        #   Footer Buttons
        lo_buttons      = QHBoxLayout()
        self.b_save     = QPushButton("Save")
        self.b_cancel   = QPushButton("Cancel")
        
        lo_buttons.addStretch()
        lo_buttons.addWidget(self.b_save)
        lo_buttons.addWidget(self.b_cancel)

        #   Add to Main Layout
        lo_main.addLayout(lo_header)
        lo_main.addItem(spacer)
        lo_main.addWidget(self.te_presetEditor)
        lo_main.addLayout(lo_buttons)

        #   ToolTips
        tip = ("Preset Name (will overwrite existing Preset with same name)\n\n"
               "Must use Letters, Numbers, Normal Symbols, Spaces, and less than 30 charactors")
        l_pName.setToolTip(tip)
        self.le_pName.setToolTip(tip)

        tip = ("Preset Data\n\n"
               "This must be a List of Dictionaries with:\n"
               "   - 'field':                string\n"
               "   - 'enabled':          bool\n"
               "   - 'sourceField':    string\n"
               "   - 'currentData':   string")
        self.te_presetEditor.setToolTip(tip)

        self.b_save.setToolTip("Save current Preset to settings")
        self.b_cancel.setToolTip("Cancel and Discard any Changes")


    def connectEvents(self):
        self.le_pName.editingFinished.connect(lambda: self.validateName(self.le_pName.text()))
        self.b_save.clicked.connect(lambda: self._onSavePreset())
        self.b_cancel.clicked.connect(lambda: self._onCancel())


    #   Loads Preset Data into Editor
    def loadData(self, pData):
        try:
            self.le_pName.setText(pData["name"])
            pretty_json = json.dumps(pData["data"], indent=4)
            self.te_presetEditor.setPlainText(pretty_json)
        except Exception as e:
            logger.warning(f"ERROR: Unable to Load Preset into Editor: {e}")


    #   Validates Name: Letters, Numbers, Normal Symbols, Spaces, < 30 charactors
    def validateName(self, name):
        valid = True
        msg = ""

        # Regex pattern: allows letters, numbers, spaces, dashes, underscores, and "safe" symbols
        # Disallows: \ / : * ? " < > |
        valid_name_pattern = re.compile(
            r'^[A-Za-z0-9 \-!@#$%^&()_+=.,;{}\[\]~`^]{1,30}$'
        )

        #   Check Blank
        if not name:
            valid = False
            msg = "Preset name cannot be blank."
        
        #   Check RegEx
        elif not valid_name_pattern.match(name):
            valid = False
            msg = ("Preset name is not valid:\n\n"
                f"'{name}'\n\n"
                "Allowed characters: letters, numbers, spaces, dashes, underscores, and common symbols.\n\n"
                "Length: 1-30 characters.\n\n"
                "Not allowed: \\ / : * ? \" < > |")
        
        #   Color Border if Invalid
        if not valid:
            self.le_pName.setStyleSheet("QLineEdit { border: 1px solid #cc6666; }")
        else:
            self.le_pName.setStyleSheet("")

        return valid, msg

    

    #   Validates Text Edit for Valid Json Array of Dicts
    def validateData(self, data):
        valid = True
        msg = ""

        try:
            data = json.loads(data)

        except json.JSONDecodeError as e:
            valid = False
            msg = f"Preset data is not valid JSON:\n{e}"
            data = {}
            return valid, msg, data

        if not isinstance(data, list):
            valid = False
            msg = "Preset data must be a JSON array (list)."

        elif not all(isinstance(item, dict) for item in data):
            valid = False
            msg = "Each item in the list must be a JSON object (dictionary)."

        return valid, msg, data
        

    #   Validates and Saves Preset
    def _onSavePreset(self):
        #   Check Valid Name
        name = self.le_pName.text().strip()
        valid, msg = self.validateName(name)
        if not valid:
            self.core.popup(msg)
            return

        #   Check Valid Data
        data = self.te_presetEditor.toPlainText()
        valid, msg, data = self.validateData(data)
        if not valid:
            self.core.popup(msg, title="Invalid Data")
            return       

        #   If Passes make pDataand Accept
        self.resultData = {"name": name,
                           "data": data}
        
        self.accept()


    def _onCancel(self):
        self.reject()