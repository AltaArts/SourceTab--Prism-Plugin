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
from dataclasses import dataclass, field

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
        self.projectBrowser = origin.projectBrowser

        self.metaMapPath = os.path.join(self.sourceBrowser.pluginPath,
                                        "Libs",
                                        "UserInterfaces",
                                        "MetaMap.json")
        
        self.sourceOptions = []

        #   Instantiate Metafiles
        self.MetaFileItems = MetaFileItems()

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

        self.loadData()

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.refresh()
        self.connectEvents()

        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def refresh(self, loadFilepath=None):
        WaitPopup.showPopup(parent=self.projectBrowser)

        self.loadFiles(loadFilepath)
        self.populateEditor()
        self.populatePresets()

        if self.sourceBrowser.currMetaPreset:
            idx = self.cb_presets.findText(self.sourceBrowser.currMetaPreset)
            if idx != -1:
                self.cb_presets.setCurrentIndex(idx)

            self.loadPreset(presetName=self.sourceBrowser.currMetaPreset)

        WaitPopup.closePopup()


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
        self.MetadataTableModel = MetadataTableModel(
            self.MetadataFieldCollection,
            self.sourceOptions,
            parent=self
        )

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

        tip = "Select Metadata Configuration Preset"
        self.cb_presets.setToolTip(tip)

        tip = "Opens Metadata Presets Editor"
        self.b_presets.setToolTip(tip)

        tip = ("Saves the Current Configuration and\n"
               "closes the Editor")
        self.b_save.setToolTip(tip)

        tip = "Closes the Editor without Saving"
        self.b_close.setToolTip(tip)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.cb_fileList.currentIndexChanged.connect(lambda: self.onFileChanged())
        self.b_showMetadataPopup.clicked.connect(lambda: self.showMetaDataPopup())
        self.b_filters.clicked.connect(self.populateEditor)
        self.b_filters.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_filters.customContextMenuRequested.connect(lambda: self.filtersRCL())
        self.b_reset.clicked.connect(self.resetTable)
        self.cb_presets.currentIndexChanged.connect(lambda: self.loadPreset())
        self.b_presets.clicked.connect(self.showPresetsMenu)
        self.b_sidecar_save.clicked.connect(self.saveSidecar)
        self.b_save.clicked.connect(self._onSave)
        self.b_close.clicked.connect(self._onClose)
        

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


    @err_catcher(name=__name__)
    def loadFiles(self, loadFilepath=None):
        #   Get All Checked FileTiles in Dest List
        try:
            fileTiles = self.sourceBrowser.getAllDestTiles(onlyChecked=True)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Destination FileTiles")
            return

        activeFiles = []

        #   Itterate through Files
        for fileTile in fileTiles:
            try:
                #   Get File Name and Check if it Exists in the MetaFileItems
                filePath = fileTile.data.get("source_mainFile_path", "")
                fileName = Utils.getBasename(filePath)
                activeFiles.append(fileName)
                existing_item = self.MetaFileItems.getByName(fileName)

                #   If it Exists, Refresh the fileTile Reference
                if existing_item:
                    existing_item.fileTile = fileTile

                #   Or Add New MetaFileItem
                else:
                    if not existing_item:
                        metadata_raw = Utils.getFFprobeMetadata(filePath)
                        metadata = MetadataModel(metadata_raw)

                        self.MetaFileItems.addItem(
                            filePath=filePath,
                            fileName=fileName,
                            fileTile=fileTile,
                            metadata=metadata,
                        )

            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{fileTile}': {e}")

        #   Update the File List Combobox
        self.cb_fileList.blockSignals(True)
        self.cb_fileList.clear()
        try:
            self.cb_fileList.addItems(activeFiles)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")

        finally:
            self.cb_fileList.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            self.cb_fileList.blockSignals(False)

        #   Select Passed File
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
            if self.cb_fileList.count() < 1:
                return
            
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.MetaFileItems.getByName(fileName)
                path = fileItem.filePath

            except Exception as e:
                logger.warning(f"ERROR: Unable to get FilePath from Selected File: {e}")
                return
            
        #   Bold Current Viewed File in Combo
        current_idx = self.cb_fileList.currentIndex()
        for i in range(self.cb_fileList.count()):
            # Set font bold for current item
            font = self.cb_fileList.font()
            font.setBold(i == current_idx)
            self.cb_fileList.setItemData(i, font, Qt.FontRole)

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

        if len(self.MetaFileItems.allItems()) < 1:
            return
        
        for row, field in enumerate(self.MetadataFieldCollection.fields):
            # Skip UNIQUE rows entirely before touching anything
            if field.sourceField == "- UNIQUE -":
                continue

            if field.name in presetFields:
                info = presetFields[field.name]

                field.enabled = info.get("enabled", False)
                field.sourceField = info.get("sourceField", "")

                #   Preset field is NONE
                if field.sourceField == "- NONE -":
                    field.currentValue = ""

                #   Preset Field is GLOBAL
                elif field.sourceField == "- GLOBAL -":
                    globalValue = info.get("currentData", "")
                    if globalValue:
                        field.currentValue = globalValue

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


    #   Returns Current Data from Editor
    @err_catcher(name=__name__)
    def getCurrentData(self, filterNone=True):
        currentData = []

        fieldNames = self.MetadataFieldCollection.get_allFieldNames()
        for fieldName in fieldNames:
            field = self.MetadataFieldCollection.get_fieldByName(fieldName)
            sourceField = field.sourceField

            if filterNone and (not sourceField or sourceField == "- NONE -"):
                continue

            fieldData = {
                "field": field.name,
                "enabled": field.enabled,
                "sourceField": field.sourceField,
                "currentData": field.currentValue
                }

            currentData.append(fieldData)

        return currentData


    @err_catcher(name=__name__)
    def saveSidecar(self, filePath=None):
        if filePath:
            sidecarPath = filePath

        else:
            # Determine save path
            testFileName = self.cb_fileList.currentText()                   # TODO - Change save location to dest path
            fileItem = self.MetaFileItems.getByName(testFileName)
            testPath = fileItem.filePath
            savedir = os.path.dirname(testPath)
            sideCarFilename = "TEST_Sidecar.csv"
            sidecarPath = os.path.join(savedir, sideCarFilename)
            

        # Get all field names
        fieldNames = self.MetadataFieldCollection.get_allFieldNames()

        with open(sidecarPath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            # Write header
            writer.writerow(fieldNames)

            # Iterate over each file
            for fileItem in self.MetaFileItems.allItems():
                row = []
                metadata = fileItem.metadata

                for fieldName in fieldNames:
                    field = self.MetadataFieldCollection.get_fieldByName(fieldName)

                    # Skip if the field doesn't exist
                    if not field:
                        row.append("")
                        continue

                    sourceField = field.sourceField

                    # Handle each type of source
                    if field.name == "File Name":
                        row.append(fileItem.fileName)

                    elif not sourceField or sourceField == "- NONE -":
                        row.append("")

                    elif sourceField == "- GLOBAL -":
                        row.append(field.currentValue)

                    elif sourceField == "- UNIQUE -":
                        value = self.MetaFileItems.get_uniqueValue(fileItem, field.name)
                        row.append(value)

                    else:
                        # Normal metadata field
                        row.append(metadata.get_valueFromSourcefield(sourceField))

                writer.writerow(row)

        logger.status(f"Saved sidecar to: {sidecarPath}")


    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def _onSave(self):
        self.sourceBrowser.currMetaPreset = self.cb_presets.currentText()
        self.sourceBrowser.sourceFuncts.updateUI()
        self.close()


    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def _onClose(self):
        self.close()



#   Holds All the Destination Files Metadata
@dataclass
class MetaFileItem:
    filePath: str
    fileName: str
    fileTile: "FileTile"
    metadata: "MetadataModel"
    uniqueValues: dict[str, str] = field(default_factory=dict)


class MetaFileItems:
    def __init__(self):
        self._by_name: dict[str, MetaFileItem] = {}
        self._by_path: dict[str, MetaFileItem] = {}
        self._items: list[MetaFileItem] = []

    def addItem(self, filePath: str, fileName: str, fileTile: "FileTile", metadata: "MetadataModel") -> None:
        item = MetaFileItem(filePath=filePath, fileName=fileName, fileTile=fileTile, metadata=metadata)
        self._by_name[fileName] = item
        self._by_path[filePath] = item
        self._items.append(item)

    def getByName(self, name: str) -> MetaFileItem | None:
        return self._by_name.get(name)

    def getByPath(self, path: str) -> MetaFileItem | None:
        return self._by_path.get(path)

    def allItems(self) -> list[MetaFileItem]:
        return self._items
    
    def getMetadata(self, fileItem: MetaFileItem) -> "MetadataModel":
        return fileItem.metadata
    
    def set_uniqueValue(self, fileItem: MetaFileItem, fieldName: str, value: str):
        fileItem.uniqueValues[fieldName] = value

    def get_uniqueValue(self, fileItem: MetaFileItem, fieldName: str) -> str:
        return fileItem.uniqueValues.get(fieldName, "")

    

#   Contains the Matadata Data
class MetadataModel:
    def __init__(self, raw_metadata):
        self.metadata: dict[str, dict] = self.group_metadata(raw_metadata)

    @staticmethod
    def group_metadata(metadata: dict[str, object]) -> dict[str, dict]:
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
        return list(self.metadata.keys())


    def get_keys(self, section: str) -> list[tuple[list[str], str]]:
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
        d = self.metadata.get(section, {})

        for k in key_path:
            d = d.get(k, {})

        return d if not isinstance(d, dict) else None
    
    
    def get_valueFromSourcefield(self, sourceField: str) -> str | None:
        parts = [p.strip() for p in sourceField.split(">")]
        
        section = parts[0]
        key_path = parts[1:]

        return self.get_value(section, key_path)

    

@dataclass
class MetadataField:
    name: str
    category: str
    enabled: bool = True
    is_header: bool = False
    sourceField: str = None
    currentValue: str = ""

class MetadataFieldCollection:
    def __init__(self, fields: list[MetadataField]):
        self.fields_all: list[MetadataField] = fields[:]
        self.fields: list[MetadataField] = fields[:]

    def get_fieldByName(self, name: str) -> MetadataField:
        for field in self.fields_all:
            if field.name == name:
                return field
        return None
    
    def get_allFieldNames(self, include_headers: bool = False) -> list[str]:
        return [f.name for f in self.fields_all if include_headers or not f.is_header]
    
    def applyFilters(self, filterStates: dict[str, bool], useFilters: bool, metaMap: list[dict]) -> None:
        fields_filtered: list[MetadataField] = []
        seenCategories: set[str] = set()

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
                if hasattr(self, "combo_delegate"):
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
        if col == self.COL_ENABLED:
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsEditable
        
        elif col == self.COL_SOURCE:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
        elif col == self.COL_VALUE:
            if field.sourceField not in ["- GLOBAL -", "- UNIQUE -"]:
                return Qt.ItemIsEnabled
            
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

        return Qt.ItemIsEnabled


class SectionHeaderDelegate(QStyledItemDelegate):
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

        if getattr(field, "is_header", False):
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
