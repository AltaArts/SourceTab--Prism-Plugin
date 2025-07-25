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
        self.sourceBrowser = origin

        self.metaMapPath = os.path.join(self.sourceBrowser.pluginPath,
                                        "Libs",
                                        "UserInterfaces",
                                        "MetaMap.json")
        
        self.sourceOptions = []

        self.filterStates = {
            "Hide Disabled": False,
            "Hide Empty": False,
            "----1": False,
            "Crew/Production": True,
            "Shot/Scene": True,
            "Camera": True,
            "Audio": True,
            "----2": False
        }

        #   Loads MetaMap from json file and makes MetaFieldCollection
        self.loadData()

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.refresh()

        self.connectEvents()

        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def refresh(self, loadFilepath=None):
        self.loadFiles(loadFilepath)
        self.populateEditor()
        self.populatePresets()


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

        #   Build Custom Table Model
        self.MetadataTableModel = MetadataTableModel(self.MetadataFieldCollection, self.sourceOptions)
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

        #   Makes It so Single-click will edit a cell                                 #   TODO
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

        tip = ("Table Display Filters (will  not affect Saved Metadata\n\n"
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
        
        self.metaMap = mData["metaMap"]
        self.metaPresets = mData["metaPresets"]
        logger.debug("Loaded Data from 'MetaMap.json'")

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


    #   Loads Presets into Combo
    @err_catcher(name=__name__)
    def populatePresets(self):
        self.cb_presets.clear()
        self.cb_presets.addItem("PRESETS")
        self.cb_presets.addItems(self.metaPresets)

        self.cb_presets.setSizeAdjustPolicy(QComboBox.AdjustToContents)


    #   Loads Destination Files into MetaFiles
    @err_catcher(name=__name__)
    def loadFiles(self, loadFilepath=None):
        #   Instantiate Metafiles
        self.MetaFileItems = MetaFileItems()

        #   Get all Destination File Tiles
        try:
            fileTiles = self.sourceBrowser.getAllDestTiles(onlyChecked=True)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Destination FileTiles")
            return

        #   Get Data from Each Tile and add to MetaFiles
        for fileTile in fileTiles:
            try:
                filePath = fileTile.data.get("source_mainFile_path", "")
                fileName = Utils.getBasename(filePath)

                #   Extract Metadata and add to Model Class
                metadata_raw = Utils.getFFprobeMetadata(filePath)
                metadata = MetadataModel(metadata_raw)

                self.MetaFileItems.addItem(filePath = filePath,
                                            fileName = fileName,
                                            fileTile = fileTile,
                                            metadata=metadata)
            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{fileTile}': {e}")

        #   Clear and Populate File Combo
        self.cb_fileList.blockSignals(True)
        self.cb_fileList.clear()
        try:
            for file in self.MetaFileItems.allItems():
                self.cb_fileList.addItem(file.fileName)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")

        finally:
            self.cb_fileList.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            self.cb_fileList.blockSignals(False)

        #   Select Passed File in Combobox
        if loadFilepath:
            fileName = Utils.getBasename(loadFilepath)
            idx = self.cb_fileList.findText(fileName)
            if idx != -1:
                self.cb_fileList.setCurrentIndex(idx)

        self.onFileChanged()


    @err_catcher(name=__name__)
    def onFileChanged(self, filePath=None):
        if filePath:
            path = filePath
        else:
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.MetaFileItems.getByName(fileName)
                path = fileItem.filePath

            except Exception as e:
                logger.warning(f"ERROR: Unable to get FilePath from Selected File: {e}")
                return

        #   Extract Metadata and add to Model Class
        metadata_raw = Utils.getFFprobeMetadata(path)
        metadata = MetadataModel(metadata_raw)

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
        
        #   Refresh Table
        self.MetadataTableModel.layoutChanged.emit()


    #   Loads MetaFieldItems into the Table
    @err_catcher(name=__name__)
    def populateEditor(self):
        useFilters = self.b_filters.isChecked()
        self.MetadataFieldCollection.applyFilters(self.filterStates, useFilters, self.metaMap)
        self.MetadataTableModel.layoutChanged.emit()


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
            fileItem = self.MetaFileItems.getByName(fileName)
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


    #   Saves Presets to Config
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
        #   Display Meta Presets Popup
        presetPopup = MetaPresetsPopup(self.core, self)

        #   If Saved Button Pressed
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
        
        #   Build Lookup from List
        presetFields = {row["field"]: row for row in pData}

        for row, field in enumerate(self.MetadataFieldCollection.fields):
            if field.name in presetFields:
                info = presetFields[field.name]

                field.enabled = info.get("enabled", False)
                field.sourceField = info.get("sourceField", "")

                #   Preset field is NONE
                if field.sourceField == "- NONE -":
                    field.currentValue = ""

                #   Preset Field is CUSTOM
                elif field.sourceField == "- CUSTOM -":
                    field.currentValue = info.get("currentData", "")

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
    @err_catcher(name=__name__)
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

            for row, field in enumerate(self.MetadataFieldCollection.fields):
                field.enabled = False
                field.sourceField = "- NONE -"
                field.currentValue = ""

            self.MetadataTableModel.layoutChanged.emit()

            logger.debug("Reset Metadata Editor")



    @err_catcher(name=__name__)
    def saveSidecar(self):
        testFileName = self.cb_fileList.currentText()
        fileItem = self.MetaFileItems.getByName(testFileName)
        testPath = fileItem.filePath

        savedir = os.path.dirname(testPath)
        sideCarFilename = "TEST_Sidecar.csv"
        sidecarPath = os.path.join(savedir, sideCarFilename)

        # Get all field names (excluding headers)
        fieldNames = self.MetadataFieldCollection.get_allFieldNames()

        with open(sidecarPath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            # Write header row
            writer.writerow(["File Name"] + fieldNames)

            for fileItem in self.MetaFileItems.allItems():

                print(f"***  metadata:  {fileItem.metadata}")								#	TESTING
                row = []

                for fieldName in fieldNames:
                    field = self.MetadataFieldCollection.get_fieldByName(fieldName)

                    print(f"***  field:  {field}")								#	TESTING

                    if not field:
                        row.append("")
                        continue

                    sourceField = field.sourceField

                    print(f"***  sourceField:  {sourceField}")								#	TESTING

                    if not sourceField or sourceField.strip().upper() == "- NONE -":
                        row.append("")

                    # elif sourceField.strip().upper() == "- CUSTOM -":
                    #     row.append(field.currentValue.strip())

                    else:
                        row.append(field.currentValue)

                writer.writerow(row)

        print(f"[MetadataEditor] Saved sidecar to: {sidecarPath}")




    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def closeWindow(self):
        self.close()



#   Holds All the Destination Files Metadata
@dataclass
class MetaFileItem:
    filePath: str
    fileName: str
    fileTile: object
    metadata: dict

class MetaFileItems:
    def __init__(self):
        self._by_name = {}
        self._by_path = {}
        self._items = []

    def addItem(self, filePath, fileName, fileTile, metadata):
        item = MetaFileItem(filePath=filePath, fileName=fileName, fileTile=fileTile, metadata=metadata)
        self._by_name[fileName] = item
        self._by_path[filePath] = item
        self._items.append(item)

    def getByName(self, name):
        return self._by_name.get(name)

    def getByPath(self, path):
        return self._by_path.get(path)

    def allItems(self):
        return self._items
    
    def getMetadata(self, item):
        return item.metadata
    

#   Contains the Matadata Data
class MetadataModel:
    def __init__(self, raw_metadata):
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


    def get_value(self, section, key_path):
        d = self.metadata.get(section, {})

        for k in key_path:
            d = d.get(k, {})

        return d if not isinstance(d, dict) else None
    

@dataclass
class MetadataField:
    name: str
    category: str
    enabled: bool = True
    is_header: bool = False
    sourceField: str = None
    currentValue: str = ""

class MetadataFieldCollection:
    def __init__(self, fields):
        self.fields_all = fields[:]
        self.fields = fields[:]

    def get_fieldByName(self, name):
        for field in self.fields_all:
            if field.name == name:
                return field
        return None
    
    def get_allFieldNames(self, include_headers=False):
        return [f.name for f in self.fields_all if include_headers or not f.is_header]
    
    def applyFilters(self, filterStates, useFilters, metaMap):
        fields_filtered = []
        seenCategories = set()

        #   Return All Fields if Filters are Disabled
        if not useFilters:
            for mData in metaMap:
                category = mData.get("category", "Crew/Production")
                fieldName = mData["MetaName"]
                field = self.get_fieldByName(fieldName)
                if not field:
                    continue

                #   Add Section Headers
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

        #   If Filters Enabled
        else:
            hideDisabled = filterStates.get("Hide Disabled", False)
            hideEmpty = filterStates.get("Hide Empty", False)

            for mData in metaMap:
                category = mData.get("category", "Crew/Production")
                if not filterStates.get(category, True):
                    continue

                fieldName = mData["MetaName"]
                field = self.get_fieldByName(fieldName)
                if not field:
                    continue

                #   Apply Hide Disabled
                if hideDisabled and not field.enabled:
                    continue

                #   Apply Hide Empty
                if hideEmpty and field.sourceField is None:
                    continue

                #   Add Section Headers
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

        self.fields = fields_filtered



class MetadataTableModel(QAbstractTableModel):
    COL_ENABLED = 0
    COL_NAME = 1
    COL_SOURCE = 2
    COL_VALUE = 3


    def __init__(self, collection, sourceOptions):
        super().__init__()
        self.collection = collection
        self.sourceOptions = sourceOptions

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
                if hasattr(self, "combo_delegate"):
                    return self.combo_delegate.getValueForField(field.sourceField, field.currentValue)
                else:
                    return field.currentValue

        #   Gray-out Current Column if Source is NONE
        if role == Qt.ForegroundRole and col == self.COL_VALUE:
            if not field.sourceField or field.sourceField == "- NONE -":
                return QColor(Qt.gray)

        return None


    def setData(self, index, value, role=Qt.EditRole):
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
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True

        return False


    def flags(self, index):
        field = self.collection.fields[index.row()]

        if field.is_header:
            return Qt.NoItemFlags

        col = index.column()
        if col == self.COL_ENABLED:
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        
        elif col == self.COL_SOURCE:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        elif col == self.COL_VALUE:
            if field.sourceField != "- CUSTOM -":
                return Qt.ItemIsEnabled
            
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled


class SectionHeaderDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
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
    def __init__(self, metadata_model, parent=None):
        super().__init__(parent)
        self.metadata_model = metadata_model

        self.display_strings = []
        self.key_map = {}  # index → (section, path)

        #   Build Combo Items & Map
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


    def paint(self, painter, option, index):
        model = index.model()
        field = model.collection.fields[index.row()]

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


    def createEditor(self, parent, option, index):
        #   Use Model's Collection to Get the Field for this Row
        field = index.model().collection.fields[index.row()]

        if getattr(field, "is_header", False):
            #   No Editor for Header Rows
            return None

        #   Otherwise Create the Combobox
        combo = QComboBox(parent)
        combo.addItems(self.display_strings)
        combo.setStyleSheet("background-color: #28292d; color: #ccc;")
        combo.currentIndexChanged.connect(lambda: self.commitData.emit(combo))

        return combo


    def setEditorData(self, editor, index):
        currentValue = index.model().data(index, Qt.EditRole)
        try:
            idx = self.display_strings.index(currentValue)

        except ValueError:
            # fallback to "- NONE -"
            idx = 0

        editor.setCurrentIndex(idx)


    def setModelData(self, editor, model, index):
        idx = editor.currentIndex()
        display_str = self.display_strings[idx]

        #   Always Update the Source Column
        model.setData(index, display_str, Qt.EditRole)

        current_index = index.siblingAtColumn(MetadataTableModel.COL_VALUE)

        if idx == 0:
            # "- NONE -" clears value
            value = ""

        elif idx == 1:
            #   "- CUSTOM -"
            value = model.data(current_index, Qt.EditRole)

        else:
            #   Regular Metadata Field
            section, path = self.key_map[idx]
            value = self.metadata_model.get_value(section, path)

        model.setData(current_index, value, Qt.EditRole)


    def getValueForField(self, sourceField, currentValue=""):
        try:
            idx = self.display_strings.index(sourceField)
        except ValueError:
            #   Unknown Source Fallback to NONE
            return ""

        if idx == 0:  # "- NONE -"
            return ""

        if idx == 1:  # "- CUSTOM -"
            return currentValue or ""

        #   Otherwise Get from Metadata
        value = self.key_map.get(idx)
        if not isinstance(value, tuple) or len(value) != 2:
            return ""

        section, path = value
        return self.metadata_model.get_value(section, path) or ""



class CheckboxDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
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



    def editorEvent(self, event, model, option, index):
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
