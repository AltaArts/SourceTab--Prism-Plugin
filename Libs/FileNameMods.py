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
import logging

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")

logger = logging.getLogger(__name__)


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
    mod_description = "Base Modifier"
    modChanged = Signal()

    def __init__(self):
        super().__init__()

        self._rowWidgets = []

        #   Enabled State
        self.isEnabled = True

        #   Enabled Checkbox
        self.chb_enableCheckbox = QCheckBox()
        self.chb_enableCheckbox.setChecked(True)

        #   Remove Button
        self.b_remove = QPushButton()
        deleteIconPath = os.path.join(iconDir, "delete.png")
        deleteIcon = self.getIconFromPath(deleteIconPath)
        self.b_remove.setIcon(deleteIcon)
        self.b_remove.setFixedWidth(24)

        #   ToolTips
        self.chb_enableCheckbox.setToolTip("Enable/Disable Modifier")
        self.b_remove.setToolTip("Remove Modifier from Stack")

        self.baseConnections()

        logger.debug(f"Created Filename Modifier: {self.mod_name}")


    #   Connect Checkbox to Enabled Method
    def baseConnections(self):
        self.chb_enableCheckbox.stateChanged.connect(self.onEnableChanged)


    #   Returns QIcon with Both Normal and Disabled Versions
    def getIconFromPath(self, imagePath, normalLevel=0.9, dimLevel=0.4):
        normal_pixmap = QPixmap(imagePath)
        normal_image = normal_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)

        #   Darken Normal Version Slightly
        darkened_normal_image = QImage(normal_image.size(), QImage.Format_ARGB32)

        for y in range(normal_image.height()):
            for x in range(normal_image.width()):
                color = normal_image.pixelColor(x, y)

                #   Reduce brightness to normalLevel
                dark = int(color.red() * normalLevel)
                color = QColor(dark, dark, dark, color.alpha())
                darkened_normal_image.setPixelColor(x, y, color)

        darkened_normal_pixmap = QPixmap.fromImage(darkened_normal_image)

        #   Darken Disbled Version More (dimLevel)
        disabled_image = QImage(normal_image.size(), QImage.Format_ARGB32)

        for y in range(normal_image.height()):
            for x in range(normal_image.width()):
                color = normal_image.pixelColor(x, y)

                # Reduce brightness to 40%
                dark = int(color.red() * dimLevel)
                color = QColor(dark, dark, dark, color.alpha())
                disabled_image.setPixelColor(x, y, color)

        disabled_pixmap = QPixmap.fromImage(disabled_image)

        #   Convert to QIcon
        icon = QIcon()
        icon.addPixmap(darkened_normal_pixmap, QIcon.Normal)
        icon.addPixmap(disabled_pixmap, QIcon.Disabled)

        return icon


    #   Toggles Enabled State
    def onEnableChanged(self, state):
        self.isEnabled = bool(state)
        if hasattr(self, "_rowWidgets"):
            for w in self._rowWidgets:
                w.setEnabled(self.isEnabled)
        self.modChanged.emit()


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
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.chb_enableCheckbox)
        nameLabel = QLabel(self.mod_name)
        nameLabel.setToolTip(self.mod_description)
        layout.addWidget(nameLabel)

        group = QFrame()
        group.setLayout(layout)
        group.setFrameStyle(QFrame.NoFrame)

        self._rowWidgets += [nameLabel, self.b_remove]

        return [group]


    #   Returns Un-Altered Name
    def applyMod(self, base_name):
        try:
            if not self.isEnabled:
                return base_name
            return base_name
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod:\n{e}")
            return base_name


####    USE THIS AS A TEMPLATE FOR NEW MODIFIERS    ####
##   Prefix Modifier    ##
class Mods_AddPrefix(Mods_BaseFilename):
    mod_name = "Add Prefix"
    mod_description = "Adds Text to the Beginning of Filename"

    def __init__(self):
        super().__init__()

        ##  vvvv    Define Mod UI Widgets  (required)   vvvv    ##
        self.le_prefix_input = QLineEdit()
        self.le_prefix_input.setPlaceholderText("Enter prefix")

        self._rowWidgets.append(self.le_prefix_input)
        self._rowWidgets.append(self.b_remove)

        #   ToolTips (optional)
        self.le_prefix_input.setToolTip("Prefix Text")
        ##  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^    ##

        self.connections()


    #   Add All UI Elements to Trigger Updates (required)
    def connections(self):
        self.le_prefix_input.textChanged.connect(self.onWidgetChanged)


    #   Add UI Elements
    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()

        ##  vvvv    Add Widgets to Layout (required)   vvvv    ##
        rowLayout.addWidget(self.le_prefix_input)
        ##  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^    ##

        #   Add Remove Button to End
        rowLayout.addWidget(self.b_remove)

        return base_widgets


    #   Define Settings to Save (required)
    def getSettings(self):
        return {
            "prefix": self.le_prefix_input.text(),
            }
    

    #   Define Settings to Load into UI (required)
    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        self.le_prefix_input.setText(data.get("prefix", ""))


    #   Logic for Modifier (required)
    def applyMod(self, base_name, settings=None):
        try:
            if settings:
                prefix = settings["prefix"]
            else:
                prefix = self.le_prefix_input.text()

            return f"{prefix}{base_name}"
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name
 


##   Suffix Modifier    ##
class Mods_AddSuffix(Mods_BaseFilename):
    mod_name = "Add Suffix"
    mod_description = "Adds Text to the End of Filename"

    def __init__(self):
        super().__init__()

        #   Suffix Text Box
        self.le_suffix_input = QLineEdit()
        self.le_suffix_input.setPlaceholderText("Enter suffix")
        #   Use Extension Checkbox
        self.l_effectExt = QLabel("Extension")
        self.cb_effectExt = QCheckBox()

        self._rowWidgets.append(self.le_suffix_input)
        self._rowWidgets.append(self.l_effectExt)
        self._rowWidgets.append(self.cb_effectExt)

        #   ToolTips
        self.le_suffix_input.setToolTip("Suffix Text")

        tip = "Apply to Extension"
        self.l_effectExt.setToolTip(tip)
        self.cb_effectExt.setToolTip(tip)

        self.connections()


    ##   Connect UI Elements to Refresh UI  ##
    def connections(self):
        self.le_suffix_input.textChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)


    ##  Creates Mod UI Layout and Returns the Layout    ##
    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()

        #   Add Suffix Textbox
        rowLayout.addWidget(self.le_suffix_input)
        rowLayout.addWidget(self.l_effectExt)
        rowLayout.addWidget(self.cb_effectExt)

        #   Add Remove Button
        rowLayout.addWidget(self.b_remove)

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
        try:
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
            
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name
   


class Mods_RemoveStartEnd(Mods_BaseFilename):
    mod_name = "Remove Start/End"
    mod_description = "Removes Characters from the Beginning or End of Filename"

    def __init__(self):
        super().__init__()

        self.cb_orientation   = QComboBox()
        self.cb_orientation.addItems(["Beginning", "End"])
        self.sb_numcharacters = QSpinBox()
        self.l_effectExt      = QLabel("Extension")
        self.cb_effectExt     = QCheckBox()

        self._rowWidgets.append(self.cb_orientation)
        self._rowWidgets.append(self.sb_numcharacters)
        self._rowWidgets.append(self.l_effectExt)
        self._rowWidgets.append(self.cb_effectExt)

        self._rowWidgets.append(self.b_remove)

        #   ToolTips
        self.cb_orientation.setToolTip("Set Orientation")
        self.sb_numcharacters.setToolTip("Number of Characters to Remove")

        tip = "Apply to Extension"
        self.l_effectExt.setToolTip(tip)
        self.cb_effectExt.setToolTip(tip)

        self.connections()


    def connections(self):
        self.cb_orientation.currentIndexChanged.connect(self.onWidgetChanged)
        self.sb_numcharacters.valueChanged.connect(self.onWidgetChanged)
        self.cb_effectExt.toggled.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()
        
        rowLayout.addWidget(self.cb_orientation)
        rowLayout.addWidget(self.sb_numcharacters)
        rowLayout.addStretch()
        rowLayout.addWidget(self.l_effectExt)
        rowLayout.addWidget(self.cb_effectExt)

        rowLayout.addWidget(self.b_remove)

        return base_widgets


    def getSettings(self):
        return {
            "orientation": self.cb_orientation.currentText(),
            "numChar":     self.sb_numcharacters.value(),
            "useExt":      self.cb_effectExt.isChecked()
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))

        idx = self.cb_orientation.findText(data.get("orientation", ""))
        if idx != -1:
            self.cb_orientation.setCurrentIndex(idx)
        
        self.sb_numcharacters.setValue(data.get("numChar", 0))
        self.cb_effectExt.setChecked(data.get("useExt", False))


    def applyMod(self, base_name, settings=None):
        try:
            if settings:
                num_chars   = settings["numChar"]
                orientation = settings["orientation"]
                affect_ext  = settings["useExt"]
            
            else:
                num_chars   = self.sb_numcharacters.value()
                orientation = self.cb_orientation.currentText()
                affect_ext  = self.cb_effectExt.isChecked()

            if num_chars < 1:
                return base_name

            #   Separate Extension if not Affecting It
            if not affect_ext:
                name, ext = os.path.splitext(base_name)
            else:
                name, ext = base_name, ""

            if num_chars >= len(name):
                #   Clamp to Max Length
                name = ""
            else:
                if orientation == "Beginning":
                    name = name[num_chars:]
                elif orientation == "End":
                    name = name[:-num_chars]

            return f"{name}{ext}"

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name



class Mods_RemoveCharacters(Mods_BaseFilename):
    mod_name = "Remove Characters"
    mod_description = "Remove Characters from a Position in the Filename"


    def __init__(self):
        super().__init__()

        self.l_position       = QLabel("Position")
        self.sb_position      = QSpinBox()
        self.l_numcharacters  = QLabel("Characters")
        self.sb_numcharacters = QSpinBox()

        self._rowWidgets.append(self.l_position)
        self._rowWidgets.append(self.sb_position)
        self._rowWidgets.append(self.l_numcharacters)
        self._rowWidgets.append(self.sb_numcharacters)

        self._rowWidgets.append(self.b_remove)

        #   ToolTips
        tip = "Character Position to Apply"
        self.l_position.setToolTip(tip)
        self.sb_position.setToolTip(tip)

        tip = "Number of Characters to Remove"
        self.l_numcharacters.setToolTip(tip)
        self.sb_numcharacters.setToolTip(tip)

        self.connections()

    
    def connections(self):
        self.sb_position.valueChanged.connect(self.onWidgetChanged)
        self.sb_numcharacters.valueChanged.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()

        rowLayout.addWidget(self.l_numcharacters)
        rowLayout.addWidget(self.sb_numcharacters)
        rowLayout.addWidget(self.l_position)
        rowLayout.addWidget(self.sb_position)

        rowLayout.addStretch()
        rowLayout.addWidget(self.b_remove)

        return base_widgets


    def getSettings(self):
        return {
            "position": self.sb_position.value(),
            "numChar":  self.sb_numcharacters.value(),
            }
    

    def setSettings(self, data):
        self.setCheckbox(data.get("enabled", False))
        
        self.sb_position.setValue(data.get("position", 0))
        self.sb_numcharacters.setValue(data.get("numChar", 0))


    def applyMod(self, base_name, settings=None):
        try:
            if settings:
                position = settings["position"]
                numChar  = settings["numChar"]
            
            else:
                position = self.sb_position.value()
                numChar  = self.sb_numcharacters.value()

            #   Clamp Position to Valid Range
            position = max(0, min(position, len(base_name)))

            #   Adjust numChar to keep Inbounds
            numChar = min(numChar, len(base_name) - position)

            #   Remove Characters
            name = base_name[:position] + base_name[position + numChar:]

            return name
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name



class Mods_InsertCharacters(Mods_BaseFilename):
    mod_name = "Insert Characters"
    mod_description = "Inserts Text into Filename"


    def __init__(self):
        super().__init__()

        self.l_position     = QLabel("Position")
        self.sp_position    = QSpinBox()
        self.le_insertText  = QLineEdit()
        self.le_insertText.setPlaceholderText("Enter text")

        self._rowWidgets.append(self.l_position)
        self._rowWidgets.append(self.sp_position)
        self._rowWidgets.append(self.le_insertText)

        self._rowWidgets.append(self.b_remove)

        #   ToolTips
        tip = "Character Position to Apply"
        self.l_position.setToolTip(tip)
        self.sp_position.setToolTip(tip)

        tip = "Text to Insert"
        self.le_insertText.setToolTip(tip)

        self.connections()

    
    def connections(self):
        self.sp_position.valueChanged.connect(self.onWidgetChanged)
        self.le_insertText.textChanged.connect(self.onWidgetChanged)
        

    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()
        
        rowLayout.addWidget(self.sp_position)
        rowLayout.addWidget(self.le_insertText)

        rowLayout.addWidget(self.b_remove)

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
        try:
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
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name



class Mods_ShiftCharacters(Mods_BaseFilename):
    mod_name = "Shift Characters"
    mod_description = "Shift Block of Characters in the Filename"


    def __init__(self):
        super().__init__()

        self.l_position    = QLabel("Position")
        self.sb_position   = QSpinBox()
        self.l_numChar     = QLabel("Characters")
        self.sb_numChar    = QSpinBox()
        self.l_shift       = QLabel("Shift")
        self.sb_shift      = QSpinBox()
        self.sb_shift.setRange(-999, 999)

        self._rowWidgets.append(self.l_position)
        self._rowWidgets.append(self.sb_position)
        self._rowWidgets.append(self.l_numChar)
        self._rowWidgets.append(self.sb_numChar)
        self._rowWidgets.append(self.l_shift)
        self._rowWidgets.append(self.sb_shift)

        self._rowWidgets.append(self.b_remove)

        #   ToolTips
        tip = "Character Position to Apply"
        self.l_position.setToolTip(tip)
        self.sb_position.setToolTip(tip)

        tip = "Number of Characters to Shift"
        self.l_numChar.setToolTip(tip)
        self.sb_numChar.setToolTip(tip)

        tip = ("Number of Positions to Shift\n\n"
               "   - Positive Numbers to the Right"
               "   - Negative Numbers to the Left")
        self.l_shift.setToolTip(tip)
        self.sb_shift.setToolTip(tip)

        self.connections()


    def connections(self):
        self.sb_position.valueChanged.connect(self.onWidgetChanged)
        self.sb_numChar.valueChanged.connect(self.onWidgetChanged)
        self.sb_shift.valueChanged.connect(self.onWidgetChanged)


    def getModUI(self):
        base_widgets = super().getModUI()
        group = base_widgets[0]
        rowLayout = group.layout()

        rowLayout.addWidget(self.l_numChar)
        rowLayout.addWidget(self.sb_numChar)
        rowLayout.addWidget(self.l_position)
        rowLayout.addWidget(self.sb_position)
        rowLayout.addWidget(self.l_shift)
        rowLayout.addWidget(self.sb_shift)

        rowLayout.addStretch()
        rowLayout.addWidget(self.b_remove)

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
        try:
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
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Mod {self.mod_name}:\n{e}")
            return base_name
