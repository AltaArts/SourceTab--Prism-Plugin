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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")



#   Returns List of Modifiers (subclasses)
def getModifiers():
    return Mods_BaseFilename.__subclasses__()

#   Adds the Specified Modifier
def createModifier(mod_class):
    return mod_class()



##   Base Modifier that Each Child Modifier Inhierits   ##
class Mods_BaseFilename(QObject):
    mod_name = "Base Modifier"
    modChanged = Signal()

    def __init__(self):
        super().__init__()

        self.enabled = True

        #   Enabled Checkbox
        self.chb_enableCheckbox = QCheckBox()
        self.chb_enableCheckbox.setChecked(True)

        #   Remove Button
        self.b_remove = QPushButton()
        self.b_remove.setIcon(QIcon(os.path.join(iconDir, "delete.png")))
        self.b_remove.setFixedWidth(24)

        self.baseConnections()


    def baseConnections(self):
        self.chb_enableCheckbox.stateChanged.connect(self.onEnableChanged)
        self.b_remove.clicked.connect(self.onRemoveModClicked)


    def onEnableChanged(self, state):
        self.enabled = bool(state)
        self.onWidgetChanged()


    def onWidgetChanged(self, *args):
        self.modChanged.emit()


    def onRemoveModClicked(self):
        # Function to remove this mod from the active list
        print(f"Removing modifier: {self.mod_name}")
        # You should implement logic here to remove the mod from your active mods list
        # For example, the mod could store a reference to the parent or have a callback to remove itself.


    #   Returns Base UI Items
    def getModUI(self):
        layout = QHBoxLayout()

        #   Enabled Checkbox
        layout.addWidget(self.chb_enableCheckbox)
        #   Modifier Name
        layout.addWidget(QLabel(self.mod_name))

        container = QWidget()
        container.setLayout(layout)

        return [container]


    #   Returns Un-Altered Name
    def applyMod(self, base_name):
        if not self.enabled:
            return base_name
        return base_name



##   Suffix Modifier    ##
class Mods_AddSuffix(Mods_BaseFilename):
    mod_name = "Add Suffix"

    def __init__(self):
        super().__init__()

        #   Suffix Text Box
        self.le_suffix_input = QLineEdit()
        self.le_suffix_input.setPlaceholderText("Enter suffix")
        self.l_effectExt = QLabel("Extension")
        self.cb_effectExt = QCheckBox()

        self.connections()


    def connections(self):
        self.le_suffix_input.textChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)


    #   Returns Modifier Widgets
    def getModUI(self):
        #   Get Base UI Elements
        base_widgets = super().getModUI()

        layout = QHBoxLayout()
        #   Add Suffix Textbox
        layout.addWidget(self.le_suffix_input)
        layout.addWidget(self.l_effectExt)
        layout.addWidget(self.cb_effectExt)

        #   Add Remove Button
        layout.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(layout)
        
        #   Add Mod Widgets to Base Widgets
        base_widgets.append(container)

        return base_widgets


    #   Alters Name
    def applyMod(self, base_name):
        suffix = self.le_suffix_input.text()

        if self.cb_effectExt.isChecked():
            return f"{base_name}{suffix}"
        else:
            name, ext = os.path.splitext(base_name)
            return f"{name}{suffix}{ext}"
            
    

class Mods_AddPrefix(Mods_BaseFilename):
    mod_name = "Add Prefix"

    def __init__(self):
        super().__init__()
        self.le_prefix_input = QLineEdit()
        self.le_prefix_input.setPlaceholderText("Enter prefix")

        self.connections()


    def connections(self):
        self.le_prefix_input.textChanged.connect(self.onWidgetChanged)


    def getModUI(self):
        base_widgets = super().getModUI()

        layout = QHBoxLayout()

        layout.addWidget(self.le_prefix_input)
        layout.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(layout)
    
        base_widgets.append(container)

        return base_widgets


    def applyMod(self, base_name):
        return f"{self.le_prefix_input.text()}{base_name}"
    


class Mods_RemoveCharactors(Mods_BaseFilename):
    mod_name = "Remove Charactors"

    def __init__(self):
        super().__init__()
        self.cb_orientation = QComboBox()
        self.cb_orientation.addItems(["Beginning", "End"])
        self.sb_numCharactors = QSpinBox()
        self.l_effectExt = QLabel("Extension")
        self.cb_effectExt = QCheckBox()

        self.connections()

    
    def connections(self):
        self.cb_orientation.currentIndexChanged.connect(self.onWidgetChanged)
        self.sb_numCharactors.valueChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()

        layout = QHBoxLayout()
        
        layout.addWidget(self.cb_orientation)
        layout.addWidget(self.sb_numCharactors)
        layout.addStretch()
        layout.addWidget(self.l_effectExt)
        layout.addWidget(self.cb_effectExt)
        layout.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(layout)
    
        base_widgets.append(container)

        return base_widgets


    def applyMod(self, base_name):
        num_chars = self.sb_numCharactors.value()

        if num_chars < 1:
            return base_name
        
        orientation = self.cb_orientation.currentText()
        affect_ext = self.cb_effectExt.isChecked()

        # Separate extension if not affecting it
        if not affect_ext:
            name, ext = os.path.splitext(base_name)
        else:
            name, ext = base_name, ""

        if num_chars >= len(name):
            # Prevent crashing if too many characters are removed
            name = ""
        else:
            if orientation == "Beginning":
                name = name[num_chars:]
            elif orientation == "End":
                name = name[:-num_chars]

        return f"{name}{ext}"
    


class Mods_InsertCharactors(Mods_BaseFilename):
    mod_name = "Insert Charactors"

    def __init__(self):
        super().__init__()

        self.l_position = QLabel("Position")
        self.sp_position = QSpinBox()

        self.le_insertText = QLineEdit()
        self.le_insertText.setPlaceholderText("Enter text")

        self.connections()

    
    def connections(self):
        self.sp_position.valueChanged.connect(self.onWidgetChanged)
        self.le_insertText.textChanged.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()

        layout = QHBoxLayout()
        
        layout.addWidget(self.sp_position)
        layout.addWidget(self.le_insertText)

        layout.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(layout)
    
        base_widgets.append(container)

        return base_widgets


    def applyMod(self, base_name):
        insert_text = self.le_insertText.text()
        insert_pos = self.sp_position.value()

        name, ext = os.path.splitext(base_name)

        # Clamp position to valid range
        insert_pos = max(0, min(insert_pos, len(name)))

        # Insert text into name
        new_name = name[:insert_pos] + insert_text + name[insert_pos:]

        return new_name + ext