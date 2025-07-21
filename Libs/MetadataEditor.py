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
        
        self.metaFieldItems = {}

        WaitPopup.showPopup(parent=self.sourceBrowser.projectBrowser)

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.loadData()

        self.loadFiles()
        self.populateFilesCombo()
        self.loadMetadata()

        self.createMetaFieldItems()
        self.populateEditor()

        self.connectEvents()

        self.lockTable(setChecked=True)

        WaitPopup.closePopup()

        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def refresh(self):
        # self.loadData()
        self.loadFiles()
        self.populateFilesCombo()
        self.loadMetadata()
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
        icon_locked = QIcon(os.path.join(iconDir, "locked.png"))
        icon_filters = QIcon(os.path.join(iconDir, "sort.png"))
        icon_reset = QIcon(os.path.join(iconDir, "reset.png"))

        self.b_filters.setIcon(icon_filters)
        self.b_locked.setIcon(icon_locked)
        self.b_reset.setIcon(icon_reset)

        #   Configure Table
        self.tw_metaEditor.setColumnCount(4)
        self.tw_metaEditor.setHorizontalHeaderLabels(["Enabled", "Field", "Source", "Current"])
        self.tw_metaEditor.verticalHeader().setVisible(False)
        self.tw_metaEditor.setShowGrid(True)
        self.tw_metaEditor.setGridStyle(Qt.SolidLine)
        self.tw_metaEditor.setAlternatingRowColors(True)
        self.tw_metaEditor.horizontalHeader().setHighlightSections(False)
        self.tw_metaEditor.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tw_metaEditor.setStyleSheet("""
            QTableWidget {
                gridline-color: #555;
                background-color: #2f3136;
                color: #ccc;
                alternate-background-color: #313335;  /* darker, more subtle */
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

        tip = ("Table Lock\n\n"
               "Click to Enable Disable Locking to\n"
               "prevent Accidental Changes.")
        self.b_locked.setToolTip(tip)

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

        header_tooltips = [
            "Enable the Metadata Field\n\n(fields not enabled will not be written)",
            "Metadata Field Name",
            "Metadata Key Listing from the File (ffprobe)\n\n   - 'None' will be blank\n   - 'Custom' allows User Input in Current cell",
            "Value to be written to Metadata Field\n\n(Values from selected Source data will be used, or custom text)"
        ]

        for col, tooltip in enumerate(header_tooltips):
            item = self.tw_metaEditor.horizontalHeaderItem(col)
            if item:
                item.setToolTip(tooltip)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_locked.clicked.connect(self.lockTable)
        self.b_filters.clicked.connect(self.filterTable)
        self.b_reset.clicked.connect(self.resetTable)
        self.b_presets.clicked.connect(self.showPresetsMenu)
        self.b_sidecar_save.clicked.connect(self.saveSidecar)
        self.cb_fileList.currentIndexChanged.connect(lambda: self.changeFile())
        self.b_showMetadataPopup.clicked.connect(lambda: self.showMetaDataPopup())
        self.b_close.clicked.connect(self.closeWindow)
        

    #   Locks the Table to Prevent Accidental Changes
    @err_catcher(name=__name__)
    def lockTable(self, setChecked=None):
        try:
            if setChecked:
                self.b_locked.setChecked(setChecked)

            table = self.tw_metaEditor
            checked = self.b_locked.isChecked()

            if checked:
                table.setToolTip("Table is Locked.  Unlock with Button Above.")
                table.setEditTriggers(QAbstractItemView.NoEditTriggers)

            else:
                table.setToolTip("tip")
                table.setEditTriggers(
                    QAbstractItemView.DoubleClicked |
                    QAbstractItemView.SelectedClicked |
                    QAbstractItemView.EditKeyPressed |
                    QAbstractItemView.AnyKeyPressed
                )

            for row in range(table.rowCount()):
                for col in range(table.columnCount()):
                    widget = table.cellWidget(row, col)
                    if widget is not None:
                        #   Get Child Widgets inside Container
                        if isinstance(widget, QWidget) and not isinstance(widget, (QComboBox, QLineEdit, QCheckBox)):
                            children = widget.findChildren(QWidget)
                            if children:
                                inner_widget = children[0]
                            else:
                                inner_widget = None
                        else:
                            inner_widget = widget

                        if inner_widget is None:
                            continue

                        if isinstance(inner_widget, QComboBox):
                            inner_widget.setEnabled(not checked)
                        elif isinstance(inner_widget, QLineEdit):
                            inner_widget.setReadOnly(checked)

            logger.debug(f"Set Table Locked State to {checked}")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Lock or Unlock Table: {e}")



    @err_catcher(name=__name__)                                                 #   TODO
    def filterTable(self):
        pass


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


    #   Creates MetaFieldItem Instances from saved MetaMap
    @err_catcher(name=__name__)
    def createMetaFieldItems(self):
        for mData in self.metaMap:
            try:
                metaFieldItem = MetaFieldItem(self, mData)
                self.metaFieldItems[metaFieldItem.field] = metaFieldItem
            except Exception as e:
                logger.warning(f"ERROR: Unable to Create MetaFieldItem: {e}")
    

    @err_catcher(name=__name__)
    def changeFile(self):
        self.loadMetadata()
        self.populateEditor()


    #   Loads MetaFieldItems into the Table
    @err_catcher(name=__name__)
    def populateEditor(self):
        self.tw_metaEditor.setRowCount(len(self.metaMap))

        for row, mData in enumerate(self.metaMap):
            try:
                field = mData["MetaName"]
                metaFieldItem = self.metaFieldItems[field]

                self.tw_metaEditor.setCellWidget(row, 0, metaFieldItem.chb_enabled_container)
                self.tw_metaEditor.setCellWidget(row, 1, metaFieldItem.l_field)
                self.tw_metaEditor.setCellWidget(row, 2, metaFieldItem.cb_sourceField)
                self.tw_metaEditor.setCellWidget(row, 3, metaFieldItem.le_currentData)

            except Exception as e:
                logger.warning(f"ERROR: Unable to add Meta Item to Table: {e}")


    #   Loads Destination Files into MetaFiles
    @err_catcher(name=__name__)
    def loadFiles(self):
        #   Instantiate Metafiles
        self.metaFiles = MetaFileItems()
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

                self.metaFiles.addItem(filePath = file_path,
                                       fileName = file_name,
                                       tile = tile)
            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{tile}': {e}")


    #   Loads MetaFiles into Combo
    @err_catcher(name=__name__)
    def populateFilesCombo(self):
        self.cb_fileList.clear()
        try:
            for file in self.metaFiles.allItems():
                self.cb_fileList.addItem(file.fileName)
        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")


    #   Loads Metadata into MetadataModel
    @err_catcher(name=__name__)
    def loadMetadata(self, filePath=None):
        if filePath:
            path = filePath
        else:
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.metaFiles.getByName(fileName)
                path = fileItem.filePath
            except Exception as e:
                logger.warning(f"ERROR: Unable to get Selected File's Tile Data: {e}")
                return

        try:
            metadata_raw = Utils.getFFprobeMetadata(path)
            self.sourceMetadata = MetadataModel(metadata_raw)
        except Exception as e:
            logger.warning(f"ERROR: Unable to get Metadat from Selected File: {e}")


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
            fileItem = self.metaFiles.getByName(fileName)
            path = fileItem.filePath
            fileName = fileItem.fileName

        #   Get and format Metadata
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
            presetName = presetPopup.selectedPreset

            #   If Preset is passed back, load it
            if presetName:
                self.loadPreset(presetName, onlyExisting=False)
                logger.debug(f"Metadata Preset Selected: {presetName}")


    #   Loads Preset into the Table
    @err_catcher(name=__name__)
    def loadPreset(self, presetName, onlyExisting=True):
        pData = self.metaPresets[presetName]

        # Build a quick lookup of fields in the preset
        presetFields = {row["field"]: row for row in pData}

        for fieldName, fieldItem in self.metaFieldItems.items():
            if fieldName in presetFields:
                # Update with data from preset
                fieldItem.setFromInfo(presetFields[fieldName])
            else:
                if not onlyExisting:
                    # Reset to "- NONE -" if not in preset
                    fieldItem.reset()


    #   Returns Currently Configured Metadata
    @err_catcher(name=__name__)
    def getCurrentData(self, filterNone=False):
        mData = []

        for metaItem in self.metaFieldItems.values():
            if filterNone and metaItem.sourceField == "- NONE -":
                continue
            mData.append(metaItem.getInfo())

        return mData


    #   Resets Table to Default None's
    @err_catcher(name=__name__)
    def resetTable(self):
        # Confirmation dialog
        title = "Reset Metadata Table"

        text = ("Would you like to clear all existing data or changes loaded into the Editor?\n\n"
                "This will not alter any metadata in the file itself.")

        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            for metaItem in self.metaFieldItems.values():
                metaItem.reset()
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



#   For Each Metadata Field
class MetaFieldItem(QObject):
    def __init__(self, metaEditor, data:dict, parent=None):
        super().__init__(parent)

        self.metaEditor = metaEditor
        self.data = data
        self.metaName = data.get("MetaName", "")
        self.target = data.get("Target", "")
        self.alias = data.get("Alias", "")

        self.setUp()
    
    @property
    def field(self):
        return self.l_field.text()
    
    @property
    def sourceField(self):
        return self.cb_sourceField.currentText()
    
    @property
    def currentData(self):
        return self.le_currentData.text()
    

    def setUp(self):
        ##   Enabled Checkbox (centered)
        chb = QCheckBox()
        self.chb_enabled = chb
        self.chb_enabled_container = self.centeredWidget(chb)

        ##   Field Label
        self.l_field = QLabel(self.metaName)
        self.l_field.setStyleSheet("padding-left: 3px;")

        self.cb_sourceField = QComboBox()
        model = QStandardItemModel()
        self.combo_key_to_path = {}

        ##  Source Combobox 
        model.appendRow(QStandardItem("- NONE -"))
        model.appendRow(QStandardItem("- CUSTOM -"))

        font_bold = QFont()
        font_bold.setBold(True)

        for section in self.metaEditor.sourceMetadata.get_sections():
            header_item = QStandardItem(section.upper())
            header_item.setFont(font_bold)
            header_item.setEnabled(False)
            model.appendRow(header_item)

            keys = self.metaEditor.sourceMetadata.get_keys(section)
            for path, display_name in keys:
                indent = "  " * (len(path) - 1)
                key_display = f"{section} > {indent}{display_name}"
                key_item = QStandardItem(key_display)
                model.appendRow(key_item)
                self.combo_key_to_path[key_display.strip()] = (section, path)

        self.cb_sourceField.setModel(model)
        self.cb_sourceField.currentTextChanged.connect(self.updateLineEdit)

        ##  Current LineEdit
        self.le_currentData = QLineEdit()


    #   Centers Checkbox in Container Widget
    def centeredWidget(self, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    
    #   Adds Text to Current LineEdit
    def updateLineEdit(self, text: str):
        text = text.strip()
        if text in ("- NONE -", "- CUSTOM -") or text == "":
            self.le_currentData.setText("")
            return

        path_info = self.combo_key_to_path.get(text)
        if not path_info:
            self.le_currentData.setText("")
            return

        section, path = path_info
        value = self.metaEditor.sourceMetadata.get_value(section, path)

        if value is None:
            self.le_currentData.setText("")
        else:
            self.le_currentData.setText(str(value))


    def isEnabled(self):
        return self.chb_enabled.isChecked()
    

    #   Returns Dict of Item's Data
    def getInfo(self):
        info = {
            "field": self.field,
            "enabled": self.isEnabled(),
            "sourceField": self.sourceField,
            "currentData": self.currentData
        }
        return info


    #   Sets Item's Data from Dict
    def setFromInfo(self, info: dict):
        enabled = info.get("enabled", False)
        sourceField = info.get("sourceField", "")
        currentData = info.get("currentData", "")

        self.chb_enabled.setChecked(enabled)

        #   Set Data if Custom
        if sourceField == "- CUSTOM -":
            self.cb_sourceField.setCurrentText("- CUSTOM -")
            self.le_currentData.setText(currentData)
        else:
            #   Check if Source if in Current Metadata Sources
            valid_keys = self.combo_key_to_path.keys()

            if sourceField in valid_keys:
                self.cb_sourceField.setCurrentText(sourceField)
                
                self.updateLineEdit(sourceField)
            else:
                #   If Source not in Current Source, set to None
                self.cb_sourceField.setCurrentText("- NONE -")
                self.le_currentData.clear()


    #   Resets the MetaItem
    def reset(self):
        self.chb_enabled.setChecked(False)
        self.cb_sourceField.setCurrentIndex(0)
        self.le_currentData.clear()


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
