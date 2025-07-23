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
import json
import csv
from dataclasses import dataclass

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")
sys.path.append(uiPath)

from PrismUtils.Decorators import err_catcher

import SourceTab_Utils as Utils
from PopupWindows import DisplayPopup, MetaPresetsPopup, WaitPopup

from MetadataEditor_ui import Ui_w_metadataEditor


logger = logging.getLogger(__name__)



class MetadataEditor(QWidget, Ui_w_metadataEditor):
    def __init__(self, core, origin, parent=None):
        super(MetadataEditor, self).__init__(parent)


        self.core = core
        self.sourceFunctions = origin
        self.sourceBrowser = self.sourceFunctions.sourceBrowser

        self.metaMapPath = os.path.join(self.sourceBrowser.pluginPath,
                                        "Libs",
                                        "UserInterfaces",
                                        "MetaMap.json")
        
        self.source_options = []

        self.filterStates = {
            "Hide Disabled": False,
            "Hide Empty": False,
            "----1": False,
            "Shot/Scene": True,
            "Camera": True,
            "Audio": True,
            "Crew/Production": True,
            "----2": False
        }

        #   Loads MetaMap from json file and makes MetaFieldCollection
        self.loadData()

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.loadFiles()
        self.populateEditor()
        self.populatePresets()
        self.connectEvents()


        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def refresh(self):
        self.loadFiles()
        self.populateEditor()



    @err_catcher(name=__name__)
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
        #   Set Width of Presets Combo
        self.cb_presets.setStyleSheet("""
            QComboBox#cb_presets {
                min-width: 200px;
            }
        """)


        #   Build Custom Table Model
        self.tableModel = MetadataTableModel(self.fieldsCollection, self.source_options)
        self.tw_metaEditor.setModel(self.tableModel)
        self.tw_metaEditor.setItemDelegate(QStyledItemDelegate())

        #   Configure Table
        self.tw_metaEditor.verticalHeader().setVisible(False)
        self.tw_metaEditor.setShowGrid(True)
        self.tw_metaEditor.setGridStyle(Qt.SolidLine)
        self.tw_metaEditor.setAlternatingRowColors(True)
        self.tw_metaEditor.horizontalHeader().setHighlightSections(False)
        self.tw_metaEditor.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tw_metaEditor.setAutoFillBackground(True)

        #   Makes It so Single-click will edit a cell
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



    @err_catcher(name=__name__)
    def setToolTips(self):
        tip = ("File Listing\n\n"
               "Select File to View Metadata")
        self.cb_fileList.setToolTip(tip)

        tip = "Opens Metadata Display Window"
        self.b_showMetadataPopup.setToolTip(tip)

        tip = ("Table Filters\n\n"
               "    - Click to Enable/Disable Filters\n"
               "    - Right-click to Configure Filters")
        self.b_filters.setToolTip(tip)

        tip = ("Reset Editor\n\n"
               "This will clear all existing data or changes loaded into the Editor.\n"
               "This will not alter any metadata in the file itself.")
        self.b_reset.setToolTip(tip)

        tip = "Opens Metadata Presets Menu"
        self.b_presets.setToolTip(tip)

        tip = ("Saves the Current Configuration and\n"
               "closes the Editor")
        self.b_save.setToolTip(tip)

        tip = "Closes the Editor without Saving"
        self.b_close.setToolTip(tip)

        # header_tooltips = [
        #     "Enable the Metadata Field\n\n(fields not enabled will not be written)",
        #     "Metadata Field Name",
        #     "Metadata Key Listing from the File (ffprobe)\n\n   - 'None' will be blank\n   - 'Custom' allows User Input in Current cell",
        #     "Value to be written to Metadata Field\n\n(Values from selected Source data will be used, or custom text)"
        # ]

        # for col, tooltip in enumerate(header_tooltips):
        #     item = self.tw_metaEditor.horizontalHeaderItem(col)
        #     if item:
        #         item.setToolTip(tooltip)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_filters.clicked.connect(self.populateEditor)
        self.b_filters.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_filters.customContextMenuRequested.connect(lambda: self.filtersRCL())
        self.b_reset.clicked.connect(self.resetTable)
        self.cb_presets.currentIndexChanged.connect(lambda: self.loadPreset())
        self.b_presets.clicked.connect(self.showPresetsMenu)
        self.b_sidecar_save.clicked.connect(self.saveSidecar)
        self.cb_fileList.currentIndexChanged.connect(lambda: self.onFileChanged())
        self.b_showMetadataPopup.clicked.connect(lambda: self.showMetaDataPopup())
        self.b_close.clicked.connect(self.closeWindow)
        

    #   Right Click List for Filters
    @err_catcher(name=__name__)
    def filtersRCL(self):
        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        def _wrapWidget(widget):
            action = QWidgetAction(self)
            action.setDefaultWidget(widget)
            return action

        def _applyFilterStates(checkboxRefs, menu):
            for label, cb in checkboxRefs.items():
                self.filterStates[label] = cb.isChecked()
            self.populateEditor()
            menu.close()

        checkboxRefs = {}

        for label, checked in self.filterStates.items():
            if label.startswith("----"):
                rcmenu.addAction(_wrapWidget(QGroupBox()))
                continue

            cb = QCheckBox(label)
            cb.setChecked(checked)
            checkboxRefs[label] = cb
            rcmenu.addAction(_wrapWidget(cb))

        # Apply button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")
        b_apply.clicked.connect(lambda: _applyFilterStates(checkboxRefs, rcmenu))
        rcmenu.addAction(_wrapWidget(b_apply))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)



    #   Loads Data from Saved MetaMap
    @err_catcher(name=__name__)
    def loadData(self):
        try:
            with open(self.metaMapPath, "r", encoding="utf-8") as f:
                mData = json.load(f)

        except FileNotFoundError:
            logger.warning("ERROR: MetaMap.json is not found")
            return
        
        self.metaMap = mData["metaMap"]                     #   TODO - LOOK IF NEEDED
        self.metaPresets = mData["metaPresets"]
        logger.debug("Loaded Data from 'MetaMap.json'")

        # Build MetadataFieldCollection here
        metadata_fields = []
        for item in self.metaMap:
            field = MetadataField(
                name=item.get("MetaName", ""),
                category=item.get("category", "Shot/Scene"),
                enabled=item.get("enabled", True)
            )
            metadata_fields.append(field)

        self.fieldsCollection = MetadataFieldCollection(metadata_fields)


    @err_catcher(name=__name__)
    def populatePresets(self):
        self.cb_presets.clear()
        self.cb_presets.addItem("PRESETS")
        self.cb_presets.addItems(self.metaPresets)


    #   Loads MetaFieldItems into the Table
    @err_catcher(name=__name__)
    def populateEditor(self):

        useFilters = self.b_filters.isChecked()                                   #   TODO - FIX FILTERS

        filtered_fields = []
        for mData in self.metaMap:
            category = mData.get("category", "Crew/Production")
            if not useFilters or self.filterStates.get(category, True):
                field_name = mData["MetaName"]
                field = self.fieldsCollection.get_field_by_name(field_name)
                if field:
                    filtered_fields.append(field)

        # replace collection fields with filtered list
        self.fieldsCollection.fields = filtered_fields

        # tell the model/view to update
        self.tableModel.layoutChanged.emit()




    #   Loads Destination Files into MetaFiles
    @err_catcher(name=__name__)
    def loadFiles(self):
        #   Instantiate Metafiles
        self.metaFilesModel = MetaFileItems()

        #   Get all Destination File Tiles
        try:
            tiles = self.sourceBrowser.getAllDestTiles()
        except Exception as e:
            logger.warning(f"ERROR: Unable to get Destination FileTiles")
            return

        #   Get Data from Each Tile and add to MetaFiles
        for tile in tiles:
            try:
                file_path = tile.data.get("source_mainFile_path", "")
                file_name = Utils.getBasename(file_path)

                self.metaFilesModel.addItem(filePath = file_path,
                                       fileName = file_name,
                                       tile = tile)
            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{tile}': {e}")


        self.cb_fileList.clear()

        try:
            for file in self.metaFilesModel.allItems():
                self.cb_fileList.addItem(file.fileName)
        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")


        self.onFileChanged()


    @err_catcher(name=__name__)
    def onFileChanged(self, filePath=None):
        if filePath:
            path = filePath
        else:
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.metaFilesModel.getByName(fileName)
                path = fileItem.filePath
            except Exception as e:
                logger.warning(f"ERROR: Unable to get FilePath from Selected File")
                return

        #   Extract Metadata and add to Model Class
        metadata_raw = Utils.getFFprobeMetadata(path)
        self.sourceMetadata = MetadataModel(metadata_raw)

        #   Update Table Model and Combo Delegate
        self.tableModel.source_options = self.source_options
        self.delegate = MetadataComboBoxDelegate(self.sourceMetadata, parent=self)
        self.tableModel.combo_delegate = self.delegate
        self.tw_metaEditor.setItemDelegateForColumn(MetadataTableModel.COL_SOURCE, self.delegate)

        #   Refresh Table
        self.tableModel.layoutChanged.emit()


    #   Displays Popup with Selected File's Metadata
    @err_catcher(name=__name__)
    def showMetaDataPopup(self, filePath=None):
        #   If passed
        if filePath:
            path = filePath
            fileName = Utils.getBasenamefilePath()

        #   Get Selected File from Combo
        else:
            fileName = self.cb_fileList.currentText()
            fileItem = self.metaFilesModel.getByName(fileName)
            path = fileItem.filePath
            fileName = fileItem.fileName

        #   Get and Format Metadata
        try:
            metadata_raw = Utils.getFFprobeMetadata(path)
            metadata = Utils.groupFFprobeMetadata(metadata_raw)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Grouped Metadata: {e}")
            return

        DisplayPopup.display(metadata, title=f"Metadata: {fileName}", modal=False)


    @err_catcher(name=__name__)
    def savePresets(self):
        with open(self.metaMapPath, "r", encoding="utf-8") as f:
            mData = json.load(f)

        #   Add or Overwrite Preset
        mData["metaPresets"] = self.metaPresets

        #   Write Back to Disk
        with open(self.metaMapPath, "w", encoding="utf-8") as f:
            json.dump(mData, f, indent=4, ensure_ascii=False)

        logger.debug(f"Metadata Presets Saved.")


    #   Displays Preset Popup
    @err_catcher(name=__name__)
    def showPresetsMenu(self):
        presetPopup = MetaPresetsPopup(self.core, self)

        if presetPopup.exec() == QDialog.Accepted:
           self.savePresets()
           self.populatePresets()


    #   Loads Preset into the Table
    @err_catcher(name=__name__)
    def loadPreset(self, presetName=None, onlyExisting=True):
        if not presetName:
            presetName = self.cb_presets.currentText()

        try:
            pData = self.metaPresets[presetName]

        except KeyError:
            logger.debug(f"Preset Not Found: {presetName}")
            return
        
        except Exception as e:
            logger.warning(f"ERROR: Unable to get Preset from Preset Name: {e}")
            return
        
        # Build lookup from list
        presetFields = {row["field"]: row for row in pData}

        for row, field in enumerate(self.fieldsCollection.fields):
            if field.name in presetFields:
                info = presetFields[field.name]

                field.enabled = info.get("enabled", False)
                field.sourceField = info.get("sourceField", "")

                # If preset field explicitly says NONE
                if field.sourceField == "- NONE -":
                    field.currentValue = ""

                # If preset field is CUSTOM
                elif field.sourceField == "- CUSTOM -":
                    # use value provided in preset as currentValue
                    field.currentValue = info.get("currentData", "")

                else:
                    # Check if sourceField exists in metadata (via delegate)
                    if field.sourceField not in self.delegate.display_strings:
                        # Not present — fallback to NONE
                        field.sourceField = "- NONE -"
                        field.currentValue = ""
                    else:
                        # Valid — resolve from metadata
                        field.currentValue = self.delegate.getValueForField(field.sourceField)

            else:
                if not onlyExisting:
                    field.enabled = False
                    field.sourceField = "- NONE -"
                    field.currentValue = ""

            # Notify view of data change
            top_left = self.tableModel.index(row, 0)
            bottom_right = self.tableModel.index(row, self.tableModel.columnCount() - 1)
            self.tableModel.dataChanged.emit(
                top_left, bottom_right, [Qt.DisplayRole, Qt.EditRole]
            )


    #   Returns Currently Configured Metadata
    @err_catcher(name=__name__)
    def getCurrentData(self, filterNone=False):
        mData = []

        for field in self.fieldsCollection.fields:
            if filterNone and field.sourceField == "- NONE -":
                continue

            mData.append({
                "field": field.name,
                "enabled": field.enabled,
                "sourceField": field.sourceField,
                "currentData": field.currentValue
            })

        return mData


    #   Resets Table to Default None's
    @err_catcher(name=__name__)
    def resetTable(self):
        # Confirmation dialog
        title = "Reset Metadata Table"
        text = (
            "Would you like to clear all existing data or changes loaded into the Editor?\n\n"
            "This will not alter any metadata in the file itself."
        )
        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            self.cb_presets.setCurrentIndex(0)

            for row, field in enumerate(self.fieldsCollection.fields):
                field.enabled = False
                field.sourceField = "- NONE -"
                field.currentValue = ""

                # notify view row
                top_left = self.tableModel.index(row, 0)
                bottom_right = self.tableModel.index(row, self.tableModel.columnCount() - 1)
                self.tableModel.dataChanged.emit(
                    top_left, bottom_right, [Qt.DisplayRole, Qt.EditRole]
                )

            logger.debug("Reset Metadata Editor")



    @err_catcher(name=__name__)                                                 #   TODO
    def saveSidecar(self):
        sourceFile = self.testImageFilepath
        sourceBasename = Utils.getBasename(sourceFile)
        savedir = os.path.dirname(sourceFile)
        sideCarFilename = "TEST_Sidecar.csv"
        sidecarPath = os.path.join(savedir, sideCarFilename)

        # build header dynamically from metaMap
        header_fields = [m["MetaName"] for m in self.metaMap]

        # start empty row
        row_data = {field: "" for field in header_fields}

        # fill fields that are known directly
        for metaFieldItem in self.metaFieldItems.values():
            if metaFieldItem.isEnabled():
                field_name = metaFieldItem.metaName
                if field_name in row_data:
                    if field_name == "File Name":
                        row_data[field_name] = sourceBasename
                    else:
                        row_data[field_name] = metaFieldItem.currentData

        # write CSV
        with open(sidecarPath, "w", encoding="utf-8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header_fields)
            writer.writeheader()
            writer.writerow(row_data)

        logger.status(f"Sidecar CSV written: {sidecarPath}")


    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def closeWindow(self):
        self.close()



#   Holds All the Destination Files Metadata
@dataclass
class MetaFileItem:
    filePath: str
    fileName: str
    tile: object

class MetaFileItems:
    def __init__(self):
        self._by_name = {}
        self._by_path = {}
        self._items = []

    def addItem(self, filePath, fileName, tile):
        item = MetaFileItem(filePath=filePath, fileName=fileName, tile=tile)
        self._by_name[fileName] = item
        self._by_path[filePath] = item
        self._items.append(item)

    def getByName(self, name) -> MetaFileItem | None:
        return self._by_name.get(name)

    def getByPath(self, path) -> MetaFileItem | None:
        return self._by_path.get(path)

    def allItems(self):
        return self._items
    

#   Contains the Matadata Data
class MetadataModel:
    def __init__(self, raw_metadata: dict):
        self.metadata = self.group_metadata(raw_metadata)

    @staticmethod
    def group_metadata(metadata):
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


    def get_sections(self):
        return list(self.metadata.keys())


    def get_keys(self, section):
        keys = []
        def recurse(d, path=[]):
            for k, v in d.items():
                if isinstance(v, dict):
                    recurse(v, path + [k])
                else:
                    keys.append( (path + [k], k) )
        recurse(self.metadata.get(section, {}))
        return keys


    def get_value(self, section, key_path: list):
        d = self.metadata.get(section, {})
        for k in key_path:
            d = d.get(k, {})
        return d if not isinstance(d, dict) else None
    

class MetadataField:
    def __init__(self, name, category, enabled=True):
        self.name = name
        self.category = category
        self.enabled = enabled
        self.sourceField = ""      # e.g., "format > duration"
        self.currentValue = ""     # populated from file


class MetadataFieldCollection:
    def __init__(self, fields: list[MetadataField]):
        self.fields = fields

    def apply_preset(self, preset_map: dict[str, str]):
        for field in self.fields:
            if field.name in preset_map:
                field.sourceField = preset_map[field.name]

    def update_from_file_metadata(self, file_metadata: dict):
        for field in self.fields:
            if field.sourceField:
                # extract real value here
                field.currentValue = file_metadata.get(field.sourceField, "")

    def get_field_by_name(self, name: str) -> MetadataField | None:
        for field in self.fields:
            if field.name == name:
                return field
        return None



class MetadataTableModel(QAbstractTableModel):
    COL_ENABLED = 0
    COL_NAME = 1
    COL_SOURCE = 2
    COL_VALUE = 3


    def __init__(self, collection: MetadataFieldCollection, source_options: list[str]):
        super().__init__()
        self.collection = collection
        self.source_options = source_options  # list of strings for combobox

    def rowCount(self, parent=QModelIndex()):
        return len(self.collection.fields)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            headers = ["Enabled", "Field", "Source", "Current"]
            if 0 <= section < len(headers):
                return headers[section]

        return super().headerData(section, orientation, role)


    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        field = self.collection.fields[index.row()]
        col = index.column()

        # ✅ Checkbox for enabled
        if role == Qt.CheckStateRole and col == self.COL_ENABLED:
            return Qt.Checked if field.enabled else Qt.Unchecked

        # ✅ Display/Edit text
        if role in (Qt.DisplayRole, Qt.EditRole):
            if col == self.COL_NAME:
                return field.name
            
            elif col == self.COL_SOURCE:
                return field.sourceField if field.sourceField else "- None -"
            
            elif col == self.COL_VALUE:
                # Always resolve via delegate, passing currentValue as fallback
                if hasattr(self, "combo_delegate"):
                    return self.combo_delegate.getValueForField(
                        field.sourceField,
                        field.currentValue
                    )
                else:
                    return field.currentValue  # fallback if no delegate

        # ✅ Gray out Current if source is NONE
        if role == Qt.ForegroundRole and col == self.COL_VALUE:
            if not field.sourceField or field.sourceField == "- NONE -":
                return QColor(Qt.gray)

        return None


    def setData(self, index, value, role=Qt.EditRole):
        field = self.collection.fields[index.row()]
        col = index.column()

        if col == self.COL_ENABLED and role == Qt.CheckStateRole:
            field.enabled = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True

        elif col == self.COL_SOURCE and role == Qt.EditRole:
            field.sourceField = value

            # Update currentValue if source changed
            if hasattr(self, "combo_delegate"):
                field.currentValue = self.combo_delegate.getValueForField(
                    field.sourceField,
                    field.currentValue
                )
            else:
                # fallback: clear currentValue if unknown
                field.currentValue = ""

            # notify both columns changed
            idx_current = self.index(index.row(), self.COL_VALUE)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            self.dataChanged.emit(idx_current, idx_current, [Qt.DisplayRole, Qt.EditRole])
            return True

        elif col == self.COL_VALUE and role == Qt.EditRole:
            # user manually edited value → save as currentValue
            field.currentValue = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True

        return False



    def flags(self, index):
        col = index.column()
        field = self.collection.fields[index.row()]

        if col == self.COL_ENABLED:
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

        elif col == self.COL_SOURCE:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        elif col == self.COL_VALUE:
            if field.sourceField != "- CUSTOM -":
                return Qt.ItemIsEnabled  # Not editable
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled




class MetadataComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, metadata_model: MetadataModel, parent=None):
        super().__init__(parent)
        self.metadata_model = metadata_model

        self.display_strings = []
        self.key_map = {}  # index → (section, path)

        # Build combobox items & map
        self.display_strings.append("- NONE -")
        self.key_map[0] = None

        self.display_strings.append("- CUSTOM -")
        self.key_map[1] = "CUSTOM" 

        idx = 2
        for section in metadata_model.get_sections():
            for path, _key in metadata_model.get_keys(section):
                display = f"{section} > {' > '.join(path)}"
                self.display_strings.append(display)
                self.key_map[idx] = (section, path)
                idx += 1


    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self.display_strings)
        combo.setStyleSheet("background-color: #28292d; color: #ccc;")
        combo.currentIndexChanged.connect(lambda: self.commitData.emit(combo))

        if parent:
            parent.update()

        return combo


    def setEditorData(self, editor, index):
        currentValue = index.model().data(index, Qt.EditRole)
        try:
            idx = self.display_strings.index(currentValue)
        except ValueError:
            idx = 0  # fallback to "- NONE -"
        editor.setCurrentIndex(idx)


    def setModelData(self, editor, model, index):
        idx = editor.currentIndex()
        display_str = self.display_strings[idx]

        # Always update the Source column text
        model.setData(index, display_str, Qt.EditRole)

        current_index = index.siblingAtColumn(MetadataTableModel.COL_VALUE)

        if idx == 0:
            # "- NONE -" clears value
            value = ""
        elif idx == 1:
            # "- CUSTOM -" leaves current value alone, user will edit manually
            value = model.data(current_index, Qt.EditRole)
        else:
            # regular metadata field
            section, path = self.key_map[idx]
            value = self.metadata_model.get_value(section, path)

        model.setData(current_index, value, Qt.EditRole)


    def getValueForField(self, sourceField: str, currentValue: str = "") -> str:
        """
        Resolve the value to display in the 'Current' column.

        Args:
            sourceField (str): The source mapping string for the field.
            currentValue (str): The currentValue already stored in the model, used if CUSTOM.

        Returns:
            str: The resolved value.
        """
        try:
            idx = self.display_strings.index(sourceField)
        except ValueError:
            # Unknown source → treat as NONE
            return ""

        if idx == 0:  # "- NONE -"
            return ""

        if idx == 1:  # "- CUSTOM -"
            return currentValue or ""

        # Otherwise → fetch from metadata
        value = self.key_map.get(idx)
        if not isinstance(value, tuple) or len(value) != 2:
            return ""

        section, path = value
        return self.metadata_model.get_value(section, path) or ""


