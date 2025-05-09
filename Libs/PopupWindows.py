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
        width = screen_geometry.width() // 3
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
            modifierClass = GetModByName(mod_data["mod_type"])
            modifier = CreateMod(modifierClass)

            self.addModToUi(modifier, mod_data)


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
            #   If Checkbox is Enabled
            if mod_instance.isEnabled:
                #   Execute Mod's Apply Method
                newName = mod_instance.applyMod(newName)

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
