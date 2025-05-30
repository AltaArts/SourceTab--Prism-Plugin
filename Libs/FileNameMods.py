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

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")



#   Returns List of Modifiers (subclasses)
def getModifiers():
    return Mods_BaseFilename.__subclasses__()


#   Returns Matching Modifier from Name
def getModClassByName(name):
    for mod in getModifiers():
        if mod.mod_name == name:
            return mod
        

#   Adds the Specified Modifier
def createModifier(mod_class):
    return mod_class()



##   Base Modifier that Each Child Modifier Inhierits   ##
class Mods_BaseFilename(QObject):
    mod_name = "Base Modifier"
    modChanged = Signal()

    def __init__(self):
        super().__init__()

        #   Enabled State
        self.isEnabled = True

        #   Enabled Checkbox
        self.chb_enableCheckbox = QCheckBox()
        self.chb_enableCheckbox.setChecked(True)

        #   Remove Button
        self.b_remove = QPushButton()
        self.b_remove.setIcon(QIcon(os.path.join(iconDir, "delete.png")))
        self.b_remove.setFixedWidth(24)

        self.baseConnections()


    #   Connect Checkbox to Enabled Method
    def baseConnections(self):
        self.chb_enableCheckbox.stateChanged.connect(self.onEnableChanged)


    #   Toggles Enabled State
    def onEnableChanged(self, state):
        self.isEnabled = bool(state)
        self.onWidgetChanged()


    #   Toggles Checkbox
    def setCheckbox(self, state):
        self.chb_enableCheckbox.setChecked(state)
        self.onEnableChanged(state)


    #   Signals for UI Refresh
    def onWidgetChanged(self, *args):
        self.modChanged.emit()


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
        if not self.isEnabled:
            return base_name
        return base_name



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

        lo_mod = QHBoxLayout()

        lo_mod.addWidget(self.le_prefix_input)
        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)
    
        base_widgets.append(container)

        return base_widgets


    def getSettings(self):
        return {
            "prefix": self.le_prefix_input.text(),
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        self.le_prefix_input.setText(data.get("prefix", ""))


    def applyMod(self, base_name, settings=None):
        if settings:
            prefix = settings["prefix"]
        else:
            prefix = self.le_prefix_input.text()

        return f"{prefix}{base_name}"
 


##   Suffix Modifier    ##                  (each Modifier should use this as a Template)
class Mods_AddSuffix(Mods_BaseFilename):
    mod_name = "Add Suffix"

    def __init__(self):
        super().__init__()

        ##  UI Elements Definied Here   ##
        ## vvvvvvvvvvvvvvvvvvvvvvvvvv   ##

        #   Suffix Text Box
        self.le_suffix_input = QLineEdit()
        self.le_suffix_input.setPlaceholderText("Enter suffix")
        #   Use Extension Checkbox
        self.l_effectExt = QLabel("Extension")
        self.cb_effectExt = QCheckBox()

        ##  ^^^^^^^^^^^^^^^^^^^^^^^^^   ##

        self.connections()


    ##   Connect UI Elements to Refresh UI  ##
    def connections(self):
        self.le_suffix_input.textChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)


    ##  Creates Mod UI Layout and Returns the Layout    ##
    def getModUI(self):
        #   Get Base UI Elements
        base_widgets = super().getModUI()

        lo_mod = QHBoxLayout()

        #   Add Suffix Textbox
        lo_mod.addWidget(self.le_suffix_input)
        lo_mod.addWidget(self.l_effectExt)
        lo_mod.addWidget(self.cb_effectExt)

        #   Add Remove Button
        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)
        
        #   Add Mod Widgets to Base Widgets
        base_widgets.append(container)

        return base_widgets


    ##  Returns the Current Settings    ##
    def getSettings(self):
        return {
            "suffix": self.le_suffix_input.text(),
            "useExt": self.cb_effectExt.isChecked()
        }
    

    ##  Sets Modifier Settings from Passed Data ##
    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        self.le_suffix_input.setText(data.get("suffix", ""))
        self.cb_effectExt.setChecked(data.get("useExt", False))


    ##  Modifier Logic to Edit the Name ##
    def applyMod(self, base_name, settings=None):
        #   If Passed Settings
        if settings:
            suffix = settings["suffix"]
            effectExt = settings["useExt"]
        #   Else Use UI Input
        else:
            suffix = self.le_suffix_input.text()
            effectExt = self.cb_effectExt.isChecked()

        #   Execute Modification
        if effectExt:
            return f"{base_name}{suffix}"
        else:
            name, ext = os.path.splitext(base_name)
            return f"{name}{suffix}{ext}"
   


class Mods_RemoveStartEnd(Mods_BaseFilename):
    mod_name = "Remove Start/End"

    def __init__(self):
        super().__init__()
        self.cb_orientation   = QComboBox()
        self.cb_orientation.addItems(["Beginning", "End"])
        self.sb_numCharactors = QSpinBox()
        self.l_effectExt      = QLabel("Extension")
        self.cb_effectExt     = QCheckBox()

        self.connections()

    
    def connections(self):
        self.cb_orientation.currentIndexChanged.connect(self.onWidgetChanged)
        self.sb_numCharactors.valueChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()

        lo_mod = QHBoxLayout()
        
        lo_mod.addWidget(self.cb_orientation)
        lo_mod.addWidget(self.sb_numCharactors)
        lo_mod.addStretch()
        lo_mod.addWidget(self.l_effectExt)
        lo_mod.addWidget(self.cb_effectExt)
        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)
    
        base_widgets.append(container)

        return base_widgets


    def getSettings(self):
        return {
            "orientation": self.cb_orientation.currentText(),
            "numChar":     self.sb_numCharactors.value(),
            "useExt":      self.cb_effectExt.isChecked()
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))

        idx = self.cb_orientation.findText(data.get("orientation", ""))
        if idx != -1:
            self.cb_orientation.setCurrentIndex(idx)
        
        self.sb_numCharactors.setValue(data.get("numChar", 0))
        self.cb_effectExt.setChecked(data.get("useExt", False))


    def applyMod(self, base_name, settings=None):
        if settings:
            num_chars   = settings["numChar"]
            orientation = settings["orientation"]
            affect_ext  = settings["useExt"]
        
        else:
            num_chars   = self.sb_numCharactors.value()
            orientation = self.cb_orientation.currentText()
            affect_ext  = self.cb_effectExt.isChecked()

        if num_chars < 1:
            return base_name

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



class Mods_RemoveCharactors(Mods_BaseFilename):
    mod_name = "Remove Charactors"

    def __init__(self):
        super().__init__()

        self.l_position       = QLabel("Position")
        self.sb_position      = QSpinBox()
        self.l_numCharactors  = QLabel("Charactors")
        self.sb_numCharactors = QSpinBox()

        self.connections()

    
    def connections(self):
        self.sb_position.valueChanged.connect(self.onWidgetChanged)
        self.sb_numCharactors.valueChanged.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()

        lo_mod = QHBoxLayout()

        lo_mod.addWidget(self.l_numCharactors)
        lo_mod.addWidget(self.sb_numCharactors)
        lo_mod.addWidget(self.l_position)
        lo_mod.addWidget(self.sb_position)
        lo_mod.addStretch()
        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)
    
        base_widgets.append(container)

        return base_widgets


    def getSettings(self):
        return {
            "position": self.sb_position.value(),
            "numChar":  self.sb_numCharactors.value(),
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        
        self.sb_position.setValue(data.get("position", 0))
        self.sb_numCharactors.setValue(data.get("numChar", 0))


    def applyMod(self, base_name, settings=None):
        if settings:
            position = settings["position"]
            numChar  = settings["numChar"]
        
        else:
            position = self.sb_position.value()
            numChar  = self.sb_numCharactors.value()

        #   Clamp Position to Valid Range
        position = max(0, min(position, len(base_name)))

        #   Adjust numChar to keep Inbounds
        numChar = min(numChar, len(base_name) - position)

        #   Remove Characters
        name = base_name[:position] + base_name[position + numChar:]

        return name



class Mods_InsertCharactors(Mods_BaseFilename):
    mod_name = "Insert Charactors"

    def __init__(self):
        super().__init__()

        self.l_position     = QLabel("Position")
        self.sp_position    = QSpinBox()
        self.le_insertText  = QLineEdit()
        self.le_insertText.setPlaceholderText("Enter text")

        self.connections()

    
    def connections(self):
        self.sp_position.valueChanged.connect(self.onWidgetChanged)
        self.le_insertText.textChanged.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()

        lo_mod = QHBoxLayout()
        
        lo_mod.addWidget(self.sp_position)
        lo_mod.addWidget(self.le_insertText)

        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)
    
        base_widgets.append(container)

        return base_widgets


    def getSettings(self):
        return {
            "position":  self.sp_position.value(),
            "insertText":   self.le_insertText.text()
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        self.sp_position.setValue(data.get("position", 0))
        self.le_insertText.setText(data.get("insertText", ""))


    def applyMod(self, base_name, settings=None):
        if settings:
            insert_text = settings["insertText"]
            insert_pos  = settings["position"]
        else:
            insert_text = self.le_insertText.text()
            insert_pos  = self.sp_position.value()

        name, ext = os.path.splitext(base_name)

        # Clamp position to valid range
        insert_pos = max(0, min(insert_pos, len(name)))

        # Insert text into name
        new_name = name[:insert_pos] + insert_text + name[insert_pos:]

        return new_name + ext



class Mods_ShiftCharactors(Mods_BaseFilename):
    mod_name = "Shift Charactors"

    def __init__(self):
        super().__init__()

        self.l_position    = QLabel("Position")
        self.sb_position   = QSpinBox()
        self.l_numChar     = QLabel("Charactors")
        self.sb_numChar    = QSpinBox()
        self.l_shift       = QLabel("Shift")
        self.sb_shift      = QSpinBox()
        self.sb_shift.setRange(-999, 999)

        self.connections()


    def connections(self):
        self.sb_position.valueChanged.connect(self.onWidgetChanged)
        self.sb_numChar.valueChanged.connect(self.onWidgetChanged)
        self.sb_shift.valueChanged.connect(self.onWidgetChanged)


    def getModUI(self):
        base_widgets = super().getModUI()

        lo_mod = QHBoxLayout()

        lo_mod.addWidget(self.l_numChar)
        lo_mod.addWidget(self.sb_numChar)
        lo_mod.addWidget(self.l_position)
        lo_mod.addWidget(self.sb_position)
        lo_mod.addWidget(self.l_shift)
        lo_mod.addWidget(self.sb_shift)
        lo_mod.addStretch()
        lo_mod.addWidget(self.b_remove)

        container = QWidget()
        container.setLayout(lo_mod)

        base_widgets.append(container)

        return base_widgets
    

    def getSettings(self):
        return {
            "position": self.sb_position.value(),
            "numChar":  self.sb_numChar.value(),
            "shift":    self.sb_shift.value(),
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        self.sb_position.setValue(data.get("position", 0))
        self.sb_numChar.setValue(data.get("numChar", 0))
        self.sb_shift.setValue(data.get("shift", 0))


    def applyMod(self, base_name, settings=None):
        if settings:
            position = settings["position"]
            numChar  = settings["numChar"]
            shift    = settings["shift"]
        else:
            position = self.sb_position.value()
            numChar  = self.sb_numChar.value()
            shift    = self.sb_shift.value()

        name, ext = os.path.splitext(base_name)

        #   Clamp position to valid range
        position = max(0, min(position, len(name)))

        #   Adjust numChar to keep Inbounds
        numChar = min(numChar, len(name) - position)

        #   Return Original if Nothing
        if numChar < 1 or shift == 0:
            return base_name

        #   Extract the Substring and Remove
        segment   = name[position:position + numChar]
        remainder = name[:position] + name[position + numChar:]

        #   Find New Position
        new_pos = position + shift
        new_pos = max(0, min(new_pos, len(remainder)))

        #   Insert at Position
        new_name = remainder[:new_pos] + segment + remainder[new_pos:]

        return new_name + ext
