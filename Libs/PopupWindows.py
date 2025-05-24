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
import subprocess
import shlex
import re


#   Get Name Mod Methods
from FileNameMods import getModifiers as GetMods
from FileNameMods import getModClassByName as GetModByName
from FileNameMods import createModifier as CreateMod


PRISMROOT = r"C:\Prism2"                                            ###   TODO
prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *



class DisplayPopup(QDialog):
    def __init__(self, data, title="Display Data", buttons=None):
        super().__init__()

        self.result = None
        self.setWindowTitle(title)

        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 2
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        lo_main = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Display content
        if isinstance(data, dict):
            for section, items in data.items():
                if isinstance(items, dict):
                    # Handle header section (Transfer info)
                    dataGroup = QGroupBox(str(section))
                    font = QFont()
                    font.setBold(True)
                    dataGroup.setFont(font)
                    
                    lo_form = QFormLayout()

                    for key, value in items.items():
                        lo_form.addRow(str(key), QLabel(str(value)))

                    dataGroup.setLayout(lo_form)
                    scroll_layout.addWidget(dataGroup)

                elif isinstance(items, list):
                    # Handle file list section (Files)
                    for group_box in items:  # Iterate over each file's group box
                        scroll_layout.addWidget(group_box)

        else:
            raw_label = QLabel(str(data))
            raw_label.setWordWrap(True)
            scroll_layout.addWidget(raw_label)

        scroll_layout.addStretch(1)  # Push content to top
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


    @staticmethod
    def display(data, title="Display Data", buttons=None):
        dialog = DisplayPopup(data, title=title, buttons=buttons)
        dialog.exec_()
        return dialog.result



class OcioConfigPopup(QDialog):
    def __init__(self, core, data):
        super().__init__()

        self.core = core

        self.ocioPresets = []

        self.result = None
        self.setWindowTitle("OCIO Preset Configuration")

        self.loadUI()
        self.connections()

        self.loadPresets(data)


    def loadUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 2
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        lo_main = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        

        # # Display content
        # if isinstance(data, dict):
        #     for section, items in data.items():
        #         if isinstance(items, dict):
        #             # Handle header section (Transfer info)
        #             dataGroup = QGroupBox(str(section))
        #             font = QFont()
        #             font.setBold(True)
        #             dataGroup.setFont(font)
                    
        #             lo_form = QFormLayout()

        #             for key, value in items.items():
        #                 lo_form.addRow(str(key), QLabel(str(value)))

        #             dataGroup.setLayout(lo_form)
        #             scroll_layout.addWidget(dataGroup)

        #         elif isinstance(items, list):
        #             # Handle file list section (Files)
        #             for group_box in items:  # Iterate over each file's group box
        #                 scroll_layout.addWidget(group_box)

        # else:
        #     raw_label = QLabel(str(data))
        #     raw_label.setWordWrap(True)
        #     scroll_layout.addWidget(raw_label)

        scroll_layout.addStretch(1)  # Push content to top
        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        # Buttons
        lo_buttons = QHBoxLayout()

        self.b_addPreset = QPushButton("Add Preset")
        self.b_close = QPushButton("Close")

        lo_buttons.addWidget(self.b_addPreset)
        lo_buttons.addStretch()
        lo_buttons.addWidget(self.b_close)

        lo_main.addLayout(lo_buttons)



    def connections(self):
        self.b_addPreset.clicked.connect(self.onOcioPresetClicked)
        self.b_close.clicked.connect(self.onCloseClicked)


    def onOcioPresetClicked(self):
        pass


    def onCloseClicked(self):
        self.result = "Close"
        self.accept()


    def addOcioPreset(self, pData):
        self.ocioPresets.append(pData)


    #   Adds Saved Presets to UI
    def loadPresets(self, oData):
        for preset in oData:
            self.addOcioPreset(preset)



    @staticmethod
    def display(core, data, buttons=None):
        dialog = OcioConfigPopup(core, data)
        dialog.exec_()
        return dialog.result



class NamingPopup(QDialog):
    def __init__(self, core, origName, mods=None):
        super().__init__()

        self.core = core
        self.origName = origName

        self.activeMods = []

        #   Make Modifier References List
        self.modDefs = [{"name": cls.mod_name, "class": cls} for cls in GetMods()]

        self.result = None

        self.setupUI()
        self.setWindowTitle("File Naming Configuration")

        #   If passed Mods, Load Mods into the UI
        if mods:
            self.loadMods(mods)

        self.refreshUI()


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 2.5
        height = screen_geometry.height() // 1.5
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Main Window Layout
        lo_main = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        ##  Display content

        #   Original Name
        lo_origName = QHBoxLayout()
        l_origName = QLabel("Original:")
        l_origName.setFixedWidth(70)
        self.le_origName = QLineEdit()
        lo_origName.addWidget(l_origName)
        lo_origName.addWidget(self.le_origName)
        scroll_layout.addLayout(lo_origName)

        #   New Name
        lo_newName = QHBoxLayout()
        l_newName = QLabel("Modified:")
        l_newName.setFixedWidth(70)
        self.le_newName = QLineEdit()
        lo_newName.addWidget(l_newName)
        lo_newName.addWidget(self.le_newName)
        scroll_layout.addLayout(lo_newName)

        #   Groupbox for Added Modifiers
        self.gb_activeMods = QGroupBox("Active Modifiers")
        self.lo_activeMods = QVBoxLayout()
        self.gb_activeMods.setLayout(self.lo_activeMods)
        self.gb_activeMods.setMinimumHeight(100)

        #   Add Modifiers Groupbox
        scroll_layout.addWidget(self.gb_activeMods)

        scroll_layout.addStretch(1)

        #   Bottom Add Mods Layout
        lo_addMods = QHBoxLayout()

        l_availMods = QLabel("Modifier")
        self.cb_availMods = QComboBox()
        b_addMod = QPushButton(text="Add Modifier")

        #   Add Bottom Layout
        lo_addMods.addWidget(l_availMods)
        lo_addMods.addWidget(self.cb_availMods)
        lo_addMods.addWidget(b_addMod)
        scroll_layout.addLayout(lo_addMods)

        #   Connect Add Mod Button
        b_addMod.clicked.connect(self.onAddModifierClicked)

        #    Add Layout to Main
        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        # Buttons
        lo_buttons = QHBoxLayout()
        lo_buttons.addStretch(1)

        buttons = ["Apply", "Close"]

        for button_text in buttons:
            button = QPushButton(button_text)
            button.clicked.connect(lambda _, t=button_text: self._onButtonClicked(t))
            lo_buttons.addWidget(button)

        lo_main.addLayout(lo_buttons)

        self.populateModsCombo()


    #    Add Modifier Names to Combo
    def populateModsCombo(self):
        self.cb_availMods.clear()

        for mod in self.modDefs:
            name = mod["name"]
            self.cb_availMods.addItem(name)


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

            except Exception as e:
                print(f"ERROR:  Unable to add Filename Mod: {modifierClass}:\n{e}")         #   TODO - Add Logging


    #   Creates New Modifier from Selected Combo
    def onAddModifierClicked(self):
        #   Get Mod Name from Combo
        selIndx = self.cb_availMods.currentIndex()
        selMod = self.modDefs[selIndx]["class"]
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
                print(f"ERROR:  Unable to Add Filename Modifier:\n{e}")

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



class ProxyPopup(QDialog):
    def __init__(self, core, sourceFuncts, settings):
        super().__init__()

        self.core = core
        self.sourceFuncts = sourceFuncts
        self.settings = settings

        self.result = None

        self.setupUI()
        self.setWindowTitle("Proxy Configuration")
       
        self.loadUI()


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


        ##  FFMPEG Settings
        self.gb_ffmpegSettings = QGroupBox("FFMPEG Settings")
        lo_ffmpeg = QHBoxLayout()
        lo_ffmpeg.setContentsMargins(20,10,20,10)

        #   Presets Label
        l_ffmpegPresets = QLabel("Proxy Presets")
        lo_ffmpeg.addWidget(l_ffmpegPresets)
        #   Presets Combo
        self.cb_proxyPresets = QComboBox()
        lo_ffmpeg.addWidget(self.cb_proxyPresets)

        spacer_2 = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lo_ffmpeg.addItem(spacer_2)

        #   Scale Label
        l_proxyScale = QLabel("Proxy Scale")
        lo_ffmpeg.addWidget(l_proxyScale)

        #   Scale Combo
        self.cb_proxyScale = QComboBox()
        self.cb_proxyScale.addItems(["25%", "50%", "75%", "100%", "150%", "200%"])
        self.cb_proxyScale.setCurrentText("100%")
        lo_ffmpeg.addWidget(self.cb_proxyScale)

        spacer_3 = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lo_ffmpeg.addItem(spacer_3)

        #   Edit Preset Button
        self.b_editPresets = QPushButton("Edit Presets")
        lo_ffmpeg.addWidget(self.b_editPresets)

        #   Add to Layout
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

        lo_main.addLayout(lo_buttons)


    #   Populate UI from Passed Settings
    def loadUI(self):
        #   Proxy Mode
        proxyMode = self.settings.get("proxyMode", "none")
        #   Match Mode to Radio Button Label
        label = self.sourceFuncts.proxyNameMap.get(proxyMode)
        if label and label in self.radio_buttons:
            self.radio_buttons[label].setChecked(True)

        #   Populate Preset Combo
        self.populatePresetCombo()

        #   Preset Settings
        ffmpegSettings = self.settings.get("proxySettings", {})
        
        if "proxyPreset" in ffmpegSettings:
            curPreset = ffmpegSettings["proxyPreset"]
            idx = self.cb_proxyPresets.findText(curPreset)
            if idx != -1:
                self.cb_proxyPresets.setCurrentIndex(idx)

        if "proxyScale" in ffmpegSettings:
            curScale = ffmpegSettings["proxyScale"]
            idx = self.cb_proxyScale.findText(curScale)
            if idx != -1:
                self.cb_proxyScale.setCurrentIndex(idx)

        #   Connections
        self.b_editPresets.clicked.connect(self._onEditPresetsClicked)

        self._onProxyModeChanged()


    #   Returns FFmpeg Preset Dict
    def getFFmpegPresets(self):
        return self.sourceFuncts.sourceBrowser.getSettings(key="ffmpegPresets")


    #   Populate Preset Combo with Presets
    def populatePresetCombo(self):
        self.cb_proxyPresets.clear()

        for preset in self.getFFmpegPresets():
            self.cb_proxyPresets.addItem(preset)

        self.createPresetsTooltip()


    #   Creates and Adds Tooltip to Preset Combo
    def createPresetsTooltip(self):
        presets = self.getFFmpegPresets()

        #   Start HTML with div wrapper
        tooltip_html = "<div style='min-width: 400px;'>"
        tooltip_html += "<table>"

        #   Make Separate Rows for each Preset
        for name, data in presets.items():
            desc = data.get("Description", "")
            tooltip_html += f"""
                <tr>
                    <td><b>{name}</b></td>
                    <td style='padding-left: 10px;'>{desc}</td>
                </tr>
                <tr><td colspan='2' style='height: 10px;'>&nbsp;</td></tr>  <!-- spacer row -->
            """

        tooltip_html += "</table></div>"

        self.cb_proxyPresets.setToolTip(tooltip_html)


    def _onProxyModeChanged(self):
        mode = self.getProxyMode()
        #   Only Show ffmpeg Settings for "generate" or "missing"
        self.gb_ffmpegSettings.setVisible(mode in ("generate", "missing"))


    #   Open Window to Edit Presets
    def _onEditPresetsClicked(self):
        #   Get Existing Presets
        pData = self.getFFmpegPresets()

        #   Instanciate and Execute Window
        editWindow = ProxyPresetsEditor(self.core, self, pData)
        editWindow.exec_()

        if editWindow.result() == "Save":
            #   Get Updated Data
            fData = editWindow.getData()
            #   Save to Settings
            self.sourceFuncts.sourceBrowser.plugin.saveSettings(key="ffmpegPresets", data=fData)
            #   Reload Combo
            self.populatePresetCombo()


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
            "proxyPreset": self.cb_proxyPresets.currentText(),
            "proxyScale": self.cb_proxyScale.currentText()
        }
        
        return pData
    

class ProxyPresetsEditor(QDialog):
    def __init__(self, core, origin, presets):
        super().__init__(origin)
        self.core = core
        self.origin = origin

        self.presetData = presets.copy()
        self._action = None

        self.setWindowTitle("FFMPEG Proxy Presets")

        self.setupUI()
        self.connections()
        self.populateTable(self.presetData)


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 1.5
        height = screen_geometry.height() // 2
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Create Main Layout
        lo_main = QVBoxLayout(self)

        #   Create table
        self.headers = ["Name"] + list(next(iter(self.presetData.values())).keys())
        self.tw_presets = QTableWidget(len(self.presetData), len(self.headers), self)
        self.tw_presets.setHorizontalHeaderLabels(self.headers)
        self.tw_presets.setSelectionBehavior(QTableWidget.SelectRows)
        self.tw_presets.setEditTriggers(QTableWidget.NoEditTriggers)

        #   Footer Buttons
        lo_buttonBox = QHBoxLayout()
        self.b_edit   = QPushButton("Edit")
        self.b_add    = QPushButton("Add")
        self.b_remove = QPushButton("Remove")
        self.b_test   = QPushButton("Validate Preset")
        self.b_reset = QPushButton("Reset to Defaults")
        self.b_moveup = QPushButton("Move Up")
        self.b_moveDn = QPushButton("Move Down")
        self.b_save   = QPushButton("Save")
        self.b_cancel = QPushButton("Cancel")
        
        lo_buttonBox.addWidget(self.b_edit)
        lo_buttonBox.addWidget(self.b_add)
        lo_buttonBox.addWidget(self.b_remove)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_test)
        lo_buttonBox.addWidget(self.b_reset)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_moveup)
        lo_buttonBox.addWidget(self.b_moveDn)
        lo_buttonBox.addStretch()
        lo_buttonBox.addWidget(self.b_save)
        lo_buttonBox.addWidget(self.b_cancel)

        #   Add to Main Layout
        lo_main.addWidget(self.tw_presets)
        lo_main.addLayout(lo_buttonBox)

        #   Stretch Columns over Entire Width
        self.tw_presets.horizontalHeader().setStretchLastSection(False)
        self.tw_presets.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)


    def connections(self):
        self.b_edit.clicked.connect(self._onEdit)
        self.b_add.clicked.connect(self._onAdd)
        self.b_remove.clicked.connect(self._onRemove)
        self.b_test.clicked.connect(self._onValidate)
        self.b_reset.clicked.connect(self._onReset)
        self.b_moveup.clicked.connect(self._onMoveUp)
        self.b_moveDn.clicked.connect(self._onMoveDown)
        self.b_save.clicked.connect(lambda: self._onFinish("Save"))
        self.b_cancel.clicked.connect(lambda: self._onFinish("Cancel"))


    #   Gets Called when Window is Displayed
    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.adjustColumnWidths)


    #   Adjusts Column Widths to fit Window
    def adjustColumnWidths(self):
        total_width = self.tw_presets.viewport().width()

        #   Column weights (column index → weight)
        weights = {
            0: 1,  # Name
            1: 3,  # Description
            2: 3,  # Video Params
            3: 2,  # Audio Params
            4: 1   # Extension
        }

        total_weight = sum(weights.values())
        #   Intterate and Set Widths
        for col in range(self.tw_presets.columnCount()):
            weight = weights.get(col, 1)
            col_width = int((weight / total_weight) * total_width)
            self.tw_presets.setColumnWidth(col, col_width)


    def populateTable(self, pData):
        #   Clear Table
        self.tw_presets.setRowCount(0)

        #   Create Row per Preset form Data
        for name, fields in pData.items():
            row = self.tw_presets.rowCount()
            self.tw_presets.insertRow(row)
            self.tw_presets.setItem(row, 0, QTableWidgetItem(name))
            for col, key in enumerate(self.headers[1:], start=1):
                self.tw_presets.setItem(row, col, QTableWidgetItem(fields.get(key, "")))

        #   Re-Apply Widths
        QTimer.singleShot(0, self.adjustColumnWidths)


    #   Sets Row Editable
    def _onEdit(self):
        row = self.tw_presets.currentRow()
        if row < 0: 
            return
        
        self.tw_presets.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)
        self.tw_presets.editItem(self.tw_presets.item(row, 0))


    #   Adds Empty Row
    def _onAdd(self):
        #   Insert Blank Row after Current
        row = max(0, self.tw_presets.currentRow() + 1)
        self.tw_presets.insertRow(row)

        for col in range(self.tw_presets.columnCount()):
            self.tw_presets.setItem(row, col, QTableWidgetItem(""))

        self.tw_presets.selectRow(row)


    #   Remove Selected Row
    def _onRemove(self):
        row = self.tw_presets.currentRow()
        #   Gets Item Info
        preset_item = self.tw_presets.item(row, 0)
        preset_name = preset_item.text() if preset_item else "Unknown"

        #   Create Question
        title = "Remove Preset"
        text = f"Would you like to Remove preset:\n\n{preset_name}"
        buttons = ["Remove", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)
        #   Remove if Affirmed
        if result == "Remove":
            if row >= 0:
                self.tw_presets.removeRow(row)


    #   Handle Tests for Preset
    def _onValidate(self):
        row = self.tw_presets.currentRow()
        if row == -1:
            self.core.popup(title="No Selection", text="Please select a preset to validate.")
            return

        # Get data from the table
        name = self.tw_presets.item(row, 0).text()
        desc = self.tw_presets.item(row, 1).text()
        vid  = self.tw_presets.item(row, 2).text()
        aud  = self.tw_presets.item(row, 3).text()
        ext  = self.tw_presets.item(row, 4).text()

        #   Make Preset Dict
        preset = {
            "Description": desc,
            "Video_Parameters": vid,
            "Audio_Parameters": aud,
            "Output_Extension": ext
        }

        #   Get Errors from Validations
        errors = self._validatePreset(name, preset)

        if errors:                                                                  #   TODO - Add Logging
            self.core.popup(
                title="Preset Validation Failed",
                text=f"Preset '{name}' has the following issues:\n\n- " + "\n- ".join(errors)
            )
        else:
            self.core.popup(
                title="Preset Validation",
                text=f"Preset '{name}' passed validation successfully."
            )

    #   Runs Several Sanity Checks on Presets
    def _validatePreset(self, name, data):
        ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))

        errors = []

        #   1. Extension check
        if not re.match(r'^\.\w+$', data["Output_Extension"]):
            errors.append("Output extension must begin with a period (e.g., .mp4)")

        #   2. Required Flags
        if "-c:v" not in data["Video_Parameters"]:
            errors.append("Missing -c:v (video codec) in video parameters")

        if "-c:a" not in data["Audio_Parameters"]:
            errors.append("Missing -c:a (audio codec) in audio parameters")

        #   3. Allowed codecs for extension
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

            if vid_codec not in allowed.get(data["Output_Extension"], set()):
                errors.append(f"Codec '{vid_codec}' may not be compatible with extension '{data['Output_Extension']}'")

        except (ValueError, IndexError):
            pass

        #   4. FFmpeg dry-run test
        try:
            #   Build Command with Generated Test Image
            cmd = [
                ffmpegPath,
                "-hide_banner", "-v", "error",
                "-f", "lavfi", "-i", "testsrc=duration=0.1",
                "-f", "lavfi", "-i", "anullsrc=duration=0.1",
            ]

            cmd.extend(shlex.split(data["Video_Parameters"]))
            cmd.extend(shlex.split(data["Audio_Parameters"]))
            cmd.extend(["-f", "null", "-"])

            print(f"ffmpeg Validation Command:\n{cmd}")                             #   TODO - Add Logging

            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "timeout": 10,
            }

            #   Suppress Popup CMD Window
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            #   Run ffmpeg Test
            result = subprocess.run(cmd, **kwargs)

            #   Add Errors to List
            if result.returncode != 0:
                errors.append("FFmpeg error:\n" + result.stderr.decode("utf-8").strip())

        except Exception as e:
            errors.append(f"Failed to run FFmpeg test: {e}")

        return errors


    #   Resets the Presets to Default Data from Prism_SourceTab_Functions.py
    def _onReset(self):
        #   Create Question
        title = "Reset Presets to Default"
        text = ("Would you like to Resets the Proxy Presets to\n"
                "the Factory Defaults?\n\n"
                "All Custom Presets will be lost.\n\n"
                "This effects all Users in this Prism Project.")
        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            #   Get Default Presets
            fData = self.origin.getFFmpegPresets()
            #   Re-assign presetData
            self.presetData = fData
            #   Populate Table with Default Data
            self.populateTable(fData)


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
            newData = {}

            #   Re-assign self.presetData from UI data
            for row in range(self.tw_presets.rowCount()):
                name = self.tw_presets.item(row, 0).text().strip()
                fields = {
                    self.headers[c]: self.tw_presets.item(row, c).text().strip()
                    for c in range(1, len(self.headers))
                }
                newData[name] = fields
            self.presetData = newData

        self.accept()


    def result(self):
        return self._action


    def getData(self):
        return self.presetData