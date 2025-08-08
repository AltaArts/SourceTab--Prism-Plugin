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
from dataclasses import dataclass, field
from typing import Optional


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")
sys.path.append(uiPath)

logger = logging.getLogger(__name__)



class FileTileMimeData(QMimeData):
    '''Holder for Drag/Drop FileTiles'''
    def __init__(self, fileTiles: list, tileType: str):
        super().__init__()
        self._fileTiles = fileTiles
        self._tileType = tileType

    def fileTiles(self) -> list:
        return self._fileTiles
    
    def tileType(self) -> str:
        return self._tileType



@dataclass
class PresetModel:
    '''Holds Preset Data'''
    name: str
    data: dict

class PresetsCollection:
    '''Holds all Preset Models'''

    def __init__(self):
        self.metaPresets: list[PresetModel] = []
        self.currentPreset: Optional[str] = None
        self.presetOrder: list[str] = []


    def clear(self):
        """Clears all presets"""

        self.metaPresets.clear()
        self.presetOrder.clear()


    def addPreset(self, name: str, data: dict):
        '''Creates PresetModel'''

        preset = PresetModel(name, data)
        self.metaPresets.append(preset)


    def addPreset(self, name: str, data: dict):
        '''Creates PresetModel'''

        #   Overwrite Data if Already Exists
        for preset in self.metaPresets:
            if preset.name == name:
                preset.data = data
                return
        #   If Not, Add New
        self.metaPresets.append(PresetModel(name, data))

        
    def removePreset(self, presetName: str) -> bool:
        """Removes a Preset by Name. Returns True if removed."""

        removed = [p for p in self.metaPresets if p.name != presetName]
        if len(removed) != len(self.metaPresets):
            self.metaPresets = removed
            if presetName in self.presetOrder:
                self.presetOrder.remove(presetName)
            return True
        return False
    

    def getHeaders(self) -> list[str]:
        '''Returns Table Headers: "Name" + keys from first preset data'''

        if not self.metaPresets:
            return ["Name"]
        return ["Name"] + list(self.metaPresets[0].data.keys())
    

    def getNumberPresets(self) -> int:
        '''Returns the Number of Presets'''

        return len(self.getPresetNames())


    def getAllPresets(self) -> list[PresetModel]:
        '''Returns List of PresetModels'''

        return self.metaPresets


    def getOrderedPresets(self) -> list[PresetModel]:
        """Returns Presets in the Project Order"""

        #   Build Map
        preset_map = {p.name: p for p in self.metaPresets}

        #   Ordered List from presetOrder
        ordered = [preset_map[name] for name in self.presetOrder if name in preset_map]

        #   Add Presets Not in presetOrder
        missing = sorted(set(preset_map.keys()) - set(self.presetOrder))
        for name in missing:
            ordered.append(preset_map[name])
            self.presetOrder.append(name)

        return ordered
    

    def getPresetNames(self) -> list[str]:
        '''Returns List of All Preset Names'''

        return [preset.name for preset in self.metaPresets]
    
    
    def getOrderedPresetNames(self) -> list[str]:
        '''Returns List of Ordered Preset Names'''
        
        return [preset.name for preset in self.getOrderedPresets()]
    

    def getPresetData(self, presetName: str) -> dict:
        """Returns Preset Data for a Preset Name"""

        for preset in self.metaPresets:
            if preset.name == presetName:
                return preset.data
        return {}


    def setCurrPreset(self, presetName: str) -> None:
        '''Sets Current Preset'''

        if presetName in self.getPresetNames():
            self.currentPreset = presetName
        else:
            raise ValueError(f"Preset '{presetName}' does not exist.")
        

    def getCurrPreset(self) -> Optional[str]:
        '''Returns Current Preset'''

        return self.currentPreset



@dataclass
class MetaFileItem:
    '''Dataclass to Hold All the Destination Files Metadata'''
    filePath: str
    fileName: str
    fileName_mod: str
    fileTile: "FileTile"
    metadata: "MetadataModel"
    uniqueValues: dict[str, str] = field(default_factory=dict)

class MetaFileItems:
    '''Holds MetaFileItem's'''
    def __init__(self):
        self._by_name: dict[str, MetaFileItem] = {}
        self._by_path: dict[str, MetaFileItem] = {}
        self._items: list[MetaFileItem] = []
        self.activeFiles: list[str] = []


    def addItem(self,
                filePath: str,
                fileName: str,
                fileName_mod: str,
                fileTile: "FileTile",
                metadata: "MetadataModel"
                ) -> None:
        '''Creates MetaFileItem'''

        item = MetaFileItem(filePath=filePath,
                            fileName=fileName,
                            fileName_mod=fileName_mod,
                            fileTile=fileTile,
                            metadata=metadata)

        self._by_name[fileName] = item
        self._by_path[filePath] = item
        self._items.append(item)


    def getByName(self, name: str) -> MetaFileItem | None:
        '''Returns MetaFileItem by Name'''

        return self._by_name.get(name)
    

    def getByPath(self, path: str) -> MetaFileItem | None:
        '''Returns MeteFileItem by Path'''

        return self._by_path.get(path)
    

    def allItems(self, active:bool=False) -> list[MetaFileItem]:
        '''Retuns List of All MetaFileItem's'''

        if active:
            return [item for file in self.activeFiles if (item := self.getByName(file))]
        
        else:
            return self._items
        
    
    def getMetadata(self, fileItem: MetaFileItem) -> "MetadataModel":
        '''Returns MetaFileItem's MetadataModel'''

        return fileItem.metadata
    
    
    def set_uniqueValue(self, fileItem: MetaFileItem, fieldName: str, value: str):
        '''Sets the MetaFileItems Field's Unique Value'''

        fileItem.uniqueValues[fieldName] = value


    def get_uniqueValue(self, fileItem: MetaFileItem, fieldName: str) -> str:
        '''Gets the MetaFileItems Field's Unique Value'''

        return fileItem.uniqueValues.get(fieldName, "")

    

#   Contains the Matadata Data
class MetadataModel:
    '''Metadata Structured Data'''

    def __init__(self, raw_metadata):
        self.metadata: dict[str, dict] = self.group_metadata(raw_metadata)

    @staticmethod
    def group_metadata(metadata: dict[str, object]) -> dict[str, dict]:
        '''Groups Raw Metadata into Sections'''

        grouped = {}

        if "format" in metadata:
            grouped["format"] = {}
            for k, v in metadata["format"].items():
                if k == "tags" and isinstance(v, dict):
                    grouped["format"]["tags"] = v.copy()
                else:
                    grouped["format"][k] = v

        if "streams" in metadata:
            for idx, stream in enumerate(metadata["streams"]):
                section_name = f"stream_{idx}"
                grouped[section_name] = {}
                for k, v in stream.items():
                    if k == "tags" and isinstance(v, dict):
                        grouped[section_name]["tags"] = v.copy()
                    else:
                        grouped[section_name][k] = v

        return grouped


    def get_sections(self) -> list[str]:
        '''Returns List of Metadata Sections'''

        return list(self.metadata.keys())


    def get_keys(self, section: str) -> list[tuple[list[str], str]]:
        '''Returns Section's Keys'''

        keys = []
        def recurse(d, path=[]):
            for k, v in d.items():
                if isinstance(v, dict):
                    recurse(v, path + [k])
                else:
                    keys.append( (path + [k], k) )

        recurse(self.metadata.get(section, {}))

        return keys


    def get_value(self, section: str, key_path: list[str]) -> str | None:
        '''Returns Value for a Given Section and Field Path'''

        d = self.metadata.get(section, {})

        for k in key_path:
            d = d.get(k, {})

        return d if not isinstance(d, dict) else None
    
    
    def get_valueFromSourcefield(self, sourceField: str) -> str | None:
        '''Returns Field's Value'''

        parts = [p.strip() for p in sourceField.split(">")]
        
        section = parts[0]
        key_path = parts[1:]

        return self.get_value(section, key_path)

    

@dataclass
class MetadataField:
    '''Dataclass to hold each Metadata Field'''

    name: str
    category: str
    enabled: bool = True
    is_header: bool = False
    sourceField: str = None
    currentValue: str = ""

class MetadataFieldCollection:
    '''Holds All Metadata Fields'''

    def __init__(self, fields: list[MetadataField]):
        self.fields_all: list[MetadataField] = fields[:]
        self.fields: list[MetadataField] = fields[:]


    def get_fieldByName(self, name: str) -> MetadataField:
        '''Returns Field Model by Name'''

        for field in self.fields_all:
            if field.name == name:
                return field
        return None
    

    def get_allFieldNames(self, include_headers: bool = False) -> list[str]:
        '''Returns List of All Field Names'''

        return [f.name for f in self.fields_all if include_headers or not f.is_header]
    

    def applyFilters(self, filterStates: dict[str, bool], useFilters: bool, metaMap: list[dict]) -> None:
        '''Returns List of Filtered Field Names'''

        fields_filtered: list[MetadataField] = []
        seenCategories: set[str] = set()

        # Separate File category from the rest
        fileCategoryItems = [m for m in metaMap if m.get("category") == "File"]
        otherItems = [m for m in metaMap if m.get("category") != "File"]

        def add_items(items: list[dict], bypass_filters: bool = False):
            for mData in items:
                category = mData.get("category", "Crew/Production")

                # Skip filter check for File category if bypass_filters=True
                if not bypass_filters:
                    # If filters enabled and this category is filtered out
                    if useFilters and not filterStates.get(category, True):
                        continue

                fieldName = mData["MetaName"]
                field = self.get_fieldByName(fieldName)
                if not field:
                    continue

                # Apply hideDisabled and hideEmpty only when filters are enabled
                if not bypass_filters and useFilters:
                    hideDisabled = filterStates.get("Hide Disabled", False)
                    hideEmpty = filterStates.get("Hide Empty", False)

                    if hideDisabled and not field.enabled:
                        continue
                    if hideEmpty and field.sourceField is None:
                        continue

                # Add header for new category
                if category not in seenCategories:
                    headerField = MetadataField(
                        name=category,
                        category=category,
                        enabled=False,
                        is_header=True
                    )
                    fields_filtered.append(headerField)
                    seenCategories.add(category)

                fields_filtered.append(field)

        # Always add File category first, bypassing filters
        add_items(fileCategoryItems, bypass_filters=True)

        # Add remaining categories, normal filtering
        add_items(otherItems, bypass_filters=False)

        self.fields = fields_filtered



class MetadataTableModel(QAbstractTableModel):
    '''Custom Table Model for Metadata Display'''

    COL_ENABLED: int = 0
    COL_NAME: int = 1
    COL_SOURCE: int = 2
    COL_VALUE: int = 3


    def __init__(
        self,
        collection: "MetadataFieldCollection",
        sourceOptions: list[str],
        parent: QWidget = None
        ) -> None:
        
        super().__init__(parent)
        self.collection: MetadataFieldCollection = collection
        self.sourceOptions: list[str] = sourceOptions


    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.collection.fields)


    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 4


    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> str:
        #   Tooltip Role for Headers
        if orientation == Qt.Horizontal and role == Qt.ToolTipRole:
            tip_enabled = ("Enable the Metadata Field\n\n"
                           "(fields not enabled will not be written)")

            tip_field = "Metadata Field Name"

            tip_source = ("Metadata Key Listing from the File (ffprobe)\n\n"
                          "   - 'NONE': no data\n"
                          "   - 'GLOBAL': custom text for all files\n"
                          "   - 'UNIQUE': custom text for current file\n"
                          "   -  Metadata fields discovered")

            tip_current = ("Value to be written to Metadata Field\n\n"
                           "(Values from selected Source data will be used, or custom text)")

            header_tooltips = [tip_enabled, tip_field, tip_source, tip_current]

            if 0 <= section < len(header_tooltips):
                return header_tooltips[section]

        #   Display Role for Headers
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            headers = ["Enabled", "Field", "Source", "Current"]
            if 0 <= section < len(headers):
                return headers[section]

        return super().headerData(section, orientation, role)


    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> any:
        if not index.isValid():
            return None

        field = self.collection.fields[index.row()]
        col = index.column()

        #   Section Header Row
        if getattr(field, "is_header", False):
            if role == Qt.DisplayRole:
                #   Display Section in Field Column
                if col == self.COL_NAME:
                    return field.name
                else:
                    return ""

            if role == Qt.FontRole:
                font = QFont()
                font.setBold(True)
                font.setPointSize(font.pointSize() + 1)
                return font

            if role == Qt.BackgroundRole:
                return QColor("#44475a")

            #   No Checkbox on Section Header Rows
            if role == Qt.CheckStateRole and col == self.COL_ENABLED:
                return None

            #   Disable Editing on Section Header
            if role == Qt.ItemIsEnabled:
                return False

            return None

        #   Normal Row Behavior for the Enabled Checkbox Cells
        if role == Qt.CheckStateRole and col == self.COL_ENABLED:
            return Qt.Checked if field.enabled else Qt.Unchecked

        #   Display/Edit Text
        if role in (Qt.DisplayRole, Qt.EditRole):
            if col == self.COL_NAME:
                return field.name
            
            elif col == self.COL_SOURCE:
                return field.sourceField if field.sourceField is not None else "- None -"
            
            elif col == self.COL_VALUE:
                if field.name in ["File Name", "Original File Name"]:
                    # Show currentValue directly for these special fields
                    return field.currentValue
                
                elif hasattr(self, "combo_delegate"):
                    return self.combo_delegate.getValueForField(
                        field.sourceField,
                        field.currentValue,
                        model=self,
                        fieldName=field.name,
                    )
                else:
                    return field.currentValue

        #   Gray-out Current Column if Source is NONE
        if role == Qt.ForegroundRole and col == self.COL_VALUE:
            if not field.sourceField or field.sourceField == "- NONE -":
                return QColor(Qt.gray)

        return None


    def setData(self, index: QModelIndex, value: any, role: int = Qt.EditRole) -> bool:
        field = self.collection.fields[index.row()]
        col = index.column()

        if role == Qt.CheckStateRole and col == self.COL_ENABLED:
            field.enabled = value == Qt.Checked
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        elif col == self.COL_SOURCE and role == Qt.EditRole:
            field.sourceField = value

            #   Update currentValue if Source Changed
            if hasattr(self, "combo_delegate"):
                field.currentValue = self.combo_delegate.getValueForField(
                    field.sourceField,
                    field.currentValue
                )
            else:
                #   Fallback: Clear currentValue if Unknown
                field.currentValue = ""

            #   Notify Both Columns Changed to Refresh
            idx_current = self.index(index.row(), self.COL_VALUE)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            self.dataChanged.emit(idx_current, idx_current, [Qt.DisplayRole, Qt.EditRole])
            return True

        #   User Manually Edited Value
        elif col == self.COL_VALUE and role == Qt.EditRole:
            field.currentValue = value

            # If this field's source is UNIQUE, also update MetaFileItems
            if field.sourceField == "- UNIQUE -":
                parent = self.parent()
                if parent:  # parent is the main widget holding cb_fileList and MetaFileItems
                    fileName = parent.cb_fileList.currentText()
                    fileItem = parent.MetaFileItems.getByName(fileName)
                    if fileItem:
                        fileItem.uniqueValues[field.name] = value

            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True

        return False


    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        field = self.collection.fields[index.row()]

        if field.is_header:
            return Qt.NoItemFlags

        col = index.column()

        # Special case for File Name & Original File Name
        if field.name in ["File Name", "Original File Name"]:
            return Qt.ItemIsEnabled

        # Normal rows
        if col == self.COL_ENABLED:
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable

        elif col == self.COL_SOURCE:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        elif col == self.COL_VALUE:
            if field.sourceField not in ["- GLOBAL -", "- UNIQUE -"]:
                # Make it normal looking, but not editable
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable

            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled



class SectionHeaderDelegate(QStyledItemDelegate):
    '''Custom Table Header'''

    def paint(self, painter: QPainter, option: any, index: QModelIndex) -> None:
        model = index.model()
        field = model.collection.fields[index.row()]
        col = index.column()

        if getattr(field, "is_header", False):
            #   Draw Custom Background
            painter.save()
            painter.fillRect(option.rect, QColor("#44475a"))
            painter.restore()

            #   Make Header Font Bold and Bigger
            option.font.setBold(True)
            option.font.setPointSize(option.font.pointSize() + 1)

            #   Draw Text Only in COL_NAME
            if col == MetadataTableModel.COL_NAME:
                text = field.name
                painter.setFont(option.font)
                painter.setPen(QColor("#f8f8f2"))
                rect = option.rect.adjusted(4, 0, 0, 0)
                painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
            else:
                pass
            return

        #   For Normal Rows, Use Default Painting
        super().paint(painter, option, index)



class MetadataComboBoxDelegate(QStyledItemDelegate):
    '''Custom ComboBox'''

    def __init__(self, metadata_model: any, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.metadata_model = metadata_model

        self.display_strings = []
        self.key_map = {}  # index → (section, path)

        #   Build Combo Items & Map
        self.display_strings.append("- NONE -")
        self.key_map[0] = None

        self.display_strings.append("- GLOBAL -")
        self.key_map[1] = "GLOBAL"

        self.display_strings.append("- UNIQUE -")
        self.key_map[2] = "UNIQUE"

        idx = 3
        for section in metadata_model.get_sections():
            for path, _key in metadata_model.get_keys(section):
                display = f"{section} > {' > '.join(path)}"
                self.display_strings.append(display)
                self.key_map[idx] = (section, path)
                idx += 1


    def paint(self, painter: QPainter, option: any, index: QModelIndex) -> None:
        model = index.model()
        field = model.collection.fields[index.row()]

        # If it's File Name or Original File Name and we're in the Source column -> paint nothing
        if field.name in ["File Name", "Original File Name"] and index.column() == MetadataTableModel.COL_SOURCE:
            # Just leave the cell empty (no text, no combo)
            return

        if getattr(field, "is_header", False):
            painter.save()
            painter.fillRect(option.rect, QColor("#44475a"))  # same header bg color            #   TODO - Colors CONST
            painter.restore()

            #   Bold Font and Slightly Bigger
            option.font.setBold(True)
            option.font.setPointSize(option.font.pointSize() + 1)

            #   Draw Text Instead of Combobox
            text = field.name if index.column() == MetadataTableModel.COL_NAME else ""

            painter.setFont(option.font)
            painter.setPen(QColor("#f8f8f2"))

            rect = option.rect.adjusted(4, 0, 0, 0)
            painter.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
            return

        #   Otherwise Use Normal Combo Painting
        super().paint(painter, option, index)


    def createEditor(self, parent: QWidget, option: any, index: QModelIndex) -> QComboBox:
        #   Use Model's Collection to Get the Field for this Row
        field = index.model().collection.fields[index.row()]

        if getattr(field, "is_header", False) or field.name in ["File Name", "Original File Name"]:
            #   No Editor for Header Rows
            return None

        #   Otherwise Create the Combobox
        combo = QComboBox(parent)
        combo.addItems(self.display_strings)
        combo.setStyleSheet("background-color: #28292d; color: #ccc;")
        combo.currentIndexChanged.connect(lambda: self.commitData.emit(combo))

        return combo


    def setEditorData(self, editor: QComboBox, index: QModelIndex) -> None:
        currentValue = index.model().data(index, Qt.EditRole)
        try:
            idx = self.display_strings.index(currentValue)

        except ValueError:
            # fallback to "- NONE -"
            idx = 0

        editor.setCurrentIndex(idx)


    def setModelData(self, editor: QComboBox, model: MetadataTableModel, index: QModelIndex) -> None:
        idx = editor.currentIndex()
        display_str = self.display_strings[idx]

        # Always update the Source column
        model.setData(index, display_str, Qt.EditRole)
        current_index = index.siblingAtColumn(MetadataTableModel.COL_VALUE)
        field = model.collection.fields[index.row()]

        if idx == 0:  # - NONE -
            value = ""

        elif idx == 1:  # - GLOBAL -
            value = model.data(current_index, Qt.EditRole)

        elif idx == 2:  # - UNIQUE -
            fileName = model.parent().cb_fileList.currentText()
            fileItem = model.parent().MetaFileItems.getByName(fileName)

            unique_value = model.data(current_index, Qt.EditRole)
            if fileItem:
                fileItem.uniqueValues[field.name] = unique_value
            value = unique_value

        else:
            # Regular metadata
            section, path = self.key_map[idx]
            value = self.metadata_model.get_value(section, path)

        model.setData(current_index, value, Qt.EditRole)



    def getValueForField(self, sourceField: str, currentValue: str = "", model: MetadataTableModel = None, fieldName: str = None) -> str:
        try:
            idx = self.display_strings.index(sourceField)
        except ValueError:
            return ""

        if idx == 0:  # NONE
            return ""

        if idx == 1:  # GLOBAL
            return currentValue or ""

        if idx == 2:  # UNIQUE
            if model and fieldName:
                fileName = model.parent().cb_fileList.currentText()
                fileItem = model.parent().MetaFileItems.getByName(fileName)
                if fileItem:
                    return fileItem.uniqueValues.get(fieldName, "")
                
            return currentValue or ""

        # Regular metadata
        value = self.key_map.get(idx)
        if not isinstance(value, tuple) or len(value) != 2:
            return ""

        section, path = value
        return self.metadata_model.get_value(section, path) or ""



class CheckboxDelegate(QStyledItemDelegate):
    '''Custom Checkbox'''
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        if not (index.flags() & Qt.ItemIsUserCheckable):
            return  # ← skip painting if not checkable (like section headers)

        checked = index.model().data(index, Qt.CheckStateRole) == Qt.Checked
        style = QApplication.style()
        opt = QStyleOptionButton()
        opt.state |= QStyle.State_Enabled
        opt.state |= QStyle.State_On if checked else QStyle.State_Off

        checkbox_rect = style.subElementRect(QStyle.SE_CheckBoxIndicator, opt, None)
        opt.rect = option.rect
        opt.rect.setX(option.rect.x() + (option.rect.width() - checkbox_rect.width()) // 2)
        opt.rect.setY(option.rect.y() + (option.rect.height() - checkbox_rect.height()) // 2)

        style.drawControl(QStyle.CE_CheckBox, opt, painter)


    def editorEvent(self, event: QEvent, model: any, option: QStyleOptionViewItem, index: QModelIndex) -> bool:
        if (
            event.type() == QEvent.MouseButtonRelease
            or event.type() == QEvent.MouseButtonDblClick
        ):
            if index.flags() & Qt.ItemIsEditable:
                current = model.data(index, Qt.CheckStateRole)
                new_value = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                model.setData(index, new_value, Qt.CheckStateRole)

            return True
        
        return False
