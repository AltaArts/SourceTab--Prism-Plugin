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


class NamingPopup(QDialog):
    def __init__(self, origName, title="File Naming Configuration", buttons=None):
        super().__init__()

        self.origName = origName
        self.buttons = buttons              #   NEEDED???

        from FileNameMods import getModifiers
        self.modDefs = [{"name": cls.mod_name, "class": cls} for cls in getModifiers()]

        self.result = None

        self.setupUI()
        self.refreshUI()
        self.setWindowTitle(title)


    def setupUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        width = screen_geometry.width() // 3
        height = screen_geometry.height() // 1.5
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

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


        # Create group box to hold active modifiers
        self.gb_activeMods = QGroupBox("Active Modifiers")
        self.lo_activeMods = QVBoxLayout()
        self.gb_activeMods.setLayout(self.lo_activeMods)

        # Optionally add a minimum height or a frame style
        self.gb_activeMods.setMinimumHeight(100)
        # self.gb_activeMods.setStyleSheet("QGroupBox { border: 1px solid gray; margin-top: 10px; }")

        # Add group box to the scroll layout
        scroll_layout.addWidget(self.gb_activeMods)

        scroll_layout.addStretch(1)  # Push content to top


        lo_addMods = QHBoxLayout()

        l_availMods = QLabel("Modifier")
        self.cb_availMods = QComboBox()
        b_addMod = QPushButton(text="Add Modifier")

        lo_addMods.addWidget(l_availMods)
        lo_addMods.addWidget(self.cb_availMods)
        lo_addMods.addWidget(b_addMod)
        scroll_layout.addLayout(lo_addMods)


        b_addMod.clicked.connect(self.onAddModifierClicked)


        scroll_area.setWidget(scroll_widget)
        lo_main.addWidget(scroll_area)

        # Buttons
        lo_buttons = QHBoxLayout()
        lo_buttons.addStretch(1)

        if self.buttons is None:
            self.buttons = ["Close"]

        for button_text in self.buttons:
            button = QPushButton(button_text)
            button.clicked.connect(lambda _, t=button_text: self._onButtonClicked(t))
            lo_buttons.addWidget(button)

        lo_main.addLayout(lo_buttons)

        self.populateModsCombo()


    def refreshUI(self):
        self.le_origName.setText(self.origName)

        newName = self.applyMods(self.origName)

        self.le_newName.setText(newName)


    def populateModsCombo(self):
        self.cb_availMods.clear()

        for mod in self.modDefs:
            name = mod["name"]
            self.cb_availMods.addItem(name)


    def onAddModifierClicked(self):
        from FileNameMods import createModifier

        selected_index = self.cb_availMods.currentIndex()
        selected_mod_class = self.modDefs[selected_index]["class"]
        mod_instance = createModifier(selected_mod_class)
        mod_instance.modChanged.connect(self.refreshUI)


        # Create a layout for the whole mod block
        mod_layout = QHBoxLayout()

        # Add widgets from getModUI
        for widget in mod_instance.getModUI():
            mod_layout.addWidget(widget)

        # Wrap the layout in a QWidget
        mod_widget = QWidget()
        mod_widget.setLayout(mod_layout)

        # Add to active mods area
        self.lo_activeMods.addWidget(mod_widget)

        # Store active mod
        if not hasattr(self, "active_mods"):
            self.active_mods = []

        self.active_mods.append((mod_instance, mod_widget))

        print(f"*** Active Mods:  {self.active_mods}")                      #   TESTING

        self.refreshUI()


    def applyMods(self, origName):
        newName = origName
        if hasattr(self, "active_mods"):
            for mod_instance, _ in self.active_mods:
                newName = mod_instance.applyMod(newName)
        return newName


    def _onButtonClicked(self, text):
        self.result = text
        self.accept()


    @staticmethod
    def display(data, title="File Naming Configuration", buttons=None):
        dialog = NamingPopup(data, title=title, buttons=buttons)
        dialog.exec_()
        return dialog.result

