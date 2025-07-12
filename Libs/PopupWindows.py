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

logger = logging.getLogger(__name__)



class WaitPopup:
    _popupProcess = None

    @classmethod
    def showPopup(cls, parent=None):
        if cls._popupProcess is None:
            #   Get Paths
            launcherPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "WaitPopup.py"))
            gifPath = os.path.join(iconDir, "loading-dark.gif")

            #   Get Enviroment for Prism Qt Libs
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
    


class DisplayPopup(QDialog):
    def __init__(self, data, title="Display Data", buttons=None, xScale=2, yScale=2, xSize=None, ySize=None):
        super().__init__()

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
                    for group_box in items:
                        scroll_layout.addWidget(group_box)

        else:
            raw_label = QLabel(str(data))
            raw_label.setWordWrap(True)
            scroll_layout.addWidget(raw_label)

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


    @staticmethod
    def display(data, title="Display Data", buttons=None, xScale=2, yScale=2, xSize=None, ySize=None):
        try:
            dialog = DisplayPopup(data, title=title, buttons=buttons, xScale=xScale, yScale=yScale, xSize=xSize, ySize=ySize)
            logger.debug(f"Showing DisplayPopup: {title}")
            dialog.exec_()
            return dialog.result
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Show DisplayPopup:\n{e}")



class OcioConfigPopup(QDialog):
    def __init__(self, core, data):
        super().__init__()

        self.core = core

        self.ocioPresets = []

        self.result = None
        self.setWindowTitle("OCIO Preset Configuration")

        self.loadUI()
        self.connectEvents()

        self.loadPresets(data)


    def loadUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width   = screen_geometry.width() // 2
        height  = screen_geometry.height() // 2
        x_pos   = (screen_geometry.width() - width) // 2
        y_pos   = (screen_geometry.height() - height) // 2
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



    def connectEvents(self):
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



class ProxyPopup(QDialog):
    def __init__(self, core, sourceFuncts, settings):
        super().__init__()

        self.core = core
        self.sourceFuncts = sourceFuncts
        self.settings = settings

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
            #   Proxy Mode
            proxyMode = self.settings.get("proxyMode", "none")
            #   Match Mode to Radio Button Label
            label = self.sourceFuncts.proxyNameMap.get(proxyMode)
            if label and label in self.radio_buttons:
                self.radio_buttons[label].setChecked(True)

            #   Populate Preset Combo
            self.populatePresetCombo()

            #   Preset Settings
            proxySettings = self.settings.get("proxySettings", {})

            if "fallback_proxyDir" in proxySettings:
                self.le_fallbackDir.setText(proxySettings["fallback_proxyDir"])

            if "ovr_proxyDir" in proxySettings:
                self.le_ovrProxyDir.setText(proxySettings["ovr_proxyDir"])

            if "proxyPreset" in proxySettings:
                curPreset = proxySettings["proxyPreset"]
                idx = self.cb_proxyPresets.findText(curPreset)
                if idx != -1:
                    self.cb_proxyPresets.setCurrentIndex(idx)

            if "proxyScale" in proxySettings:
                curScale = proxySettings["proxyScale"]
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
    

    #   Returns FFmpeg Preset Dict
    def getFFmpegPresets(self):
        return self.sourceFuncts.sourceBrowser.getSettings(key="ffmpegPresets")


    #   Populate Preset Combo with Presets
    def updateTemplateNumber(self):
        number = len(self.getProxySearchList())
        self.l_numberTemplates.setText(f"{number} templates")


    #   Populate Preset Combo with Presets
    def populatePresetCombo(self):
        try:
            self.cb_proxyPresets.clear()

            for preset in self.getFFmpegPresets():
                self.cb_proxyPresets.addItem(preset)

            self.createPresetsTooltip()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Presets Combo:\n{e}")


    #   Creates and Adds Tooltip to Preset Combo
    def createPresetsTooltip(self):
        try:
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

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Presets Tooltip:\n{e}")


    def _onProxyModeChanged(self):
        mode = self.getProxyMode()
        #   Set Visabilty of Options Based on Mode
        self.gb_proxyCopySettings.setVisible(mode in ["copy", "missing"])
        self.gb_ffmpegSettings.setVisible(mode in ("generate", "missing"))


    #   Open Window to Edit Presets
    def _onEditSearchTemplatesClicked(self):
        #   Get Existing Presets
        searchList = self.getProxySearchList()

        editWindow = ProxySearchStrEditor(self.core, self, searchList)
        logger.debug("Opening Proxy Search Tempplate Editor")
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
        #   Get Existing Presets
        pData = self.getFFmpegPresets()

        #   Instanciate and Execute Window
        editWindow = ProxyPresetsEditor(self.core, self, pData)
        logger.debug("Opening Proxy Presets Editor")
        editWindow.exec_()

        if editWindow.result() == "Save":
            try:
                #   Get Updated Data
                presetData = editWindow.getPresets()
                #   Update FFmpeg List
                self.sourceFuncts.sourceBrowser.ffmpegPresets = presetData
                #   Save to Settings
                self.sourceFuncts.sourceBrowser.plugin.saveSettings(key="ffmpegPresets", data=presetData)
                #   Reload Combo
                self.populatePresetCombo()

                logger.debug("Saved Proxy Presets")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Save Proxy Presets:\n{e}")


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
            "proxyScale":                   self.cb_proxyScale.currentText()
            }
        
        return pData
        
    
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

        logger.debug("Loaded Proxy Seaarch Editor")


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
                lines.append(f"✅ {label} — Passed")
                lines.append("")
            else:
                lines.append(f"❌ {label} — Failed: {msg}")
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
    def __init__(self, core, origin, presets):
        super().__init__(origin)
        self.core = core
        self.origin = origin

        self.presetData = presets.copy()
        self._action = None

        self.setWindowTitle("FFMPEG Proxy Presets")

        self.setupUI()
        self.connectEvents()
        self.populateTable(self.presetData)

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
        self.headers = ["Name"] + list(next(iter(self.presetData.values())).keys())
        self.tw_presets = QTableWidget(len(self.presetData), len(self.headers), self)
        self.tw_presets.setHorizontalHeaderLabels(self.headers)
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
        self.b_edit     = QPushButton("Edit")
        self.b_add      = QPushButton("Add")
        self.b_remove   = QPushButton("Remove")
        self.b_test     = QPushButton("Validate Preset")
        self.b_reset    = QPushButton("Reset to Defaults")
        self.b_moveup   = QPushButton("Move Up")
        self.b_moveDn   = QPushButton("Move Down")
        self.b_save     = QPushButton("Save")
        self.b_cancel   = QPushButton("Cancel")
        
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

        ##   ToolTips

        #   Make Tooltip Lines as Pairs of Label and Description
        tip_lines = [
            ("Name:", "Short name to be used in the UI"),

            ("Description:", "Blurb to describe the Preset (optional)"),

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
        - File extension is applicable to the encode codec
        - Video parameters contain the required args
        - Audio parameters contain the required args
        - Multiplier is in the correct format

        It will also perform a small test ffmpeg transcode with the settings.
        """
        self.b_test.setToolTip(tip)

        self.b_edit.setToolTip("Edit Selected Preset")
        self.b_add.setToolTip("Add New Preset")
        self.b_remove.setToolTip("Remove Selected Preset")
        self.b_moveup.setToolTip("Move Selected Preset Up One Row")
        self.b_moveDn.setToolTip("Move Selected Preset Down One Row")
        self.b_reset.setToolTip("Reset All Presets to Factory Defaults")
        self.b_save.setToolTip("Save Changes and Close Window")
        self.b_cancel.setToolTip("Discard Changes and Close Window")


    #   Make Signal Connections
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
        #   Intterate and Set Widths
        for col in range(self.tw_presets.columnCount()):
            weight = weights.get(col, 1)
            col_width = int((weight / total_weight) * total_width)
            self.tw_presets.setColumnWidth(col, col_width)


    def populateTable(self, pData):
        try:
            #   Clear Table
            self.tw_presets.setRowCount(0)

            #   Create Row per Preset form Data
            for name, fields in pData.items():
                row = self.tw_presets.rowCount()
                self.tw_presets.insertRow(row)
                self.tw_presets.setItem(row, 0, QTableWidgetItem(name))
                for col, key in enumerate(self.headers[1:], start=1):
                    # self.tw_presets.setItem(row, col, QTableWidgetItem(fields.get(key, "")))
                    value = fields.get(key, "")
                    self.tw_presets.setItem(row, col, QTableWidgetItem(str(value)))

            #   Re-Apply Widths
            QTimer.singleShot(0, self.adjustColumnWidths)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Populate Proxy Presets Table:\n{e}")


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
        text = f"Would you like to Remove:\n\n{preset_name}"
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
        # all_passed = True

        for label, passed, msg in results:
            if passed:
                lines.append(f"✅ {label} — Passed")
                lines.append("")
            else:
                lines.append(f"❌ {label} — Failed: {msg}")
                lines.append("")

                # all_passed = False

        #   Show Popup
        title="Preset Validation Results"
        text="\n".join(lines)
        DisplayPopup.display(text, title, xScale=4, yScale=3)


    #   Runs Several Sanity Checks on Presets
    def _validatePreset(self, name, data):
        ffmpegPath = os.path.normpath(self.core.media.getFFmpeg(validate=True))

        results = []

        # 1. FFmpeg Check
        if not os.path.isfile(ffmpegPath):
            results.append(("FFmpeg Executable", False, "FFmpeg was not found"))
        else:
            results.append(("FFmpeg Executable", True, ""))

        # 2. Extension check
        ext = data["Extension"]
        if not re.match(r'^\.\w+$', ext):
            results.append(("Output Extension", False, "Must begin with a period (e.g., .mp4)"))
        else:
            results.append(("Output Extension", True, ""))

        # 3. Required codec flags
        if "-c:v" not in data["Video_Parameters"]:
            results.append(("Video Codec (-c:v)", False, "Missing -c:v in video parameters"))
        else:
            results.append(("Video Codec (-c:v)", True, ""))

        if "-c:a" not in data["Audio_Parameters"]:
            results.append(("Audio Codec (-c:a)", False, "Missing -c:a in audio parameters"))
        else:
            results.append(("Audio Codec (-c:a)", True, ""))

        # 4. Codec compatibility check
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

        # 5. FFmpeg Dry Run
        try:

            cmd = [
                ffmpegPath,
                "-hide_banner", "-v", "error",
            ]

            cmd.extend(shlex.split(data["Global_Parameters"]))

            cmd.extend([
                "-f", "lavfi", "-i", "testsrc=duration=0.1",
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
                results.append(("FFmpeg Dry Run", False, msg))
            else:
                results.append(("FFmpeg Dry Run", True, ""))

        except Exception as e:
            results.append(("FFmpeg Dry Run", False, str(e)))

        # 6. Multiplier validation
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
            fData = self.origin.sourceFuncts.sourceBrowser.plugin.getDefaultSettings(key="ffmpegPresets")
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
            try:
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

                logger.debug("Saved Proxy Presets")

            except Exception as e:
                logger.warning(f"ERROR:  Failed to Save Proxy Presets:\n{e}")

        self.accept()


    def result(self):
        return self._action


    def getPresets(self):
        return self.presetData
    

