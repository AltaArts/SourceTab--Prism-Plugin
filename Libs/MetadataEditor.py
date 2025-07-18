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


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
sys.path.append(uiPath)

from PrismUtils.Decorators import err_catcher

import SourceTab_Utils as Utils

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


        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)
        self.setToolTips()
        self.configureUI()
        self.connectEvents()

        self.updateUI()

        self.metaFieldItems = {}

        self.loadData()

        self.loadFiles()

        self.populateFilesCombo()

        self.createMetaFieldItems()

        self.populateEditor()


        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def setToolTips(self):
        pass
        


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.b_preset_save.clicked.connect(self.savePreset)
        self.b_preset_load.clicked.connect(self.loadPreset)
        self.b_sidecar_save.clicked.connect(self.saveSidecar)


        self.b_close.clicked.connect(self.closeWindow)


    @err_catcher(name=__name__)
    def configureUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1700, min(2500, calc_width))
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

        #   Configure Table
        self.tw_metaEditor.setColumnCount(4)
        self.tw_metaEditor.setHorizontalHeaderLabels(["Enabled", "Field", "Source", "Current"])
        self.tw_metaEditor.verticalHeader().setVisible(False)
        self.tw_metaEditor.setShowGrid(True)
        self.tw_metaEditor.setGridStyle(Qt.SolidLine)
        self.tw_metaEditor.setAlternatingRowColors(True)
        self.tw_metaEditor.horizontalHeader().setHighlightSections(False)
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


    #   Set Column Widths After Launch
    def setInitialColumnWidths(self):
        table_width = self.tw_metaEditor.viewport().width()
        self.tw_metaEditor.setColumnWidth(0, int(table_width * 0.05))
        self.tw_metaEditor.setColumnWidth(1, int(table_width * 0.30))
        self.tw_metaEditor.setColumnWidth(2, int(table_width * 0.30))
        self.tw_metaEditor.horizontalHeader().setStretchLastSection(True)


    @err_catcher(name=__name__)
    def updateUI(self):
        pass


    @err_catcher(name=__name__)
    def loadData(self):
        with open(self.metaMapPath, "r", encoding="utf-8") as f:
            mData = json.load(f)
        self.metaMap = mData["metaMap"]
        self.metaPresets = mData["metaPresets"]


    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def closeWindow(self):
        self.close()


    @err_catcher(name=__name__)
    def savePreset(self):
        presetName = "zCam"                         #   TESTING - HARDCODED



        # Collect current editor state
        presetData = [
            metaFieldItem.getInfo()
            for metaFieldItem in self.metaFieldItems.values()
            if metaFieldItem.sourceField != "- NONE -" and metaFieldItem.isEnabled()
        ]

        # Load the current JSON file
        with open(self.metaMapPath, "r", encoding="utf-8") as f:
            pData = json.load(f)

        # Ensure metaPresets exists and is a dict
        if "metaPresets" not in pData or not isinstance(pData["metaPresets"], dict):
            pData["metaPresets"] = {}

        # Save or overwrite this preset
        pData["metaPresets"][presetName] = presetData

        # Write back to the same file
        with open(self.metaMapPath, "w", encoding="utf-8") as f:
            json.dump(pData, f, indent=4, ensure_ascii=False)

        print(f"✅ Preset '{presetName}' saved.")                           #   TODO



    @err_catcher(name=__name__)
    def loadPreset(self):
        pData = self.metaPresets["zCam"]

        for row in pData:
            field = row["field"]
            if field in self.metaFieldItems:
                self.metaFieldItems[field].setFromInfo(row)


    @err_catcher(name=__name__)
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



    def loadFiles(self):
        self.destFiles = []

        tiles = self.sourceBrowser.getAllDestTiles()

        for tile in tiles:
            file_path = tile.data.get("source_mainFile_path", "")
            file_name = Utils.getBasename(file_path)

            self.destFiles.append({
                "filePath": file_path,
                "fileName": file_name,
                "tile": tile
            })



    def getMetaData(self, filePath=None):
        if filePath:
            path = filePath
        else:
            path = None

        metadata_raw = test_firstTile.getFFprobeMetadata(test_filePath)
        self.sourceMetadata = MetadataModel(metadata_raw)




    def populateFilesCombo(self):
        for file in self.destFiles:
            self.cb_fileList.addItem(file["fileName"])





    @err_catcher(name=__name__)
    def createMetaFieldItems(self):
        for mData in self.metaMap:
            metaFieldItem = MetaFieldItem(self, mData)
            self.metaFieldItems[metaFieldItem.field] = metaFieldItem

    

    @err_catcher(name=__name__)
    def populateEditor(self):
        self.tw_metaEditor.setRowCount(len(self.metaMap))

        for row, mData in enumerate(self.metaMap):
            field = mData["MetaName"]
            metaFieldItem = self.metaFieldItems[field]

            self.tw_metaEditor.setCellWidget(row, 0, metaFieldItem.chb_enabled_container)
            self.tw_metaEditor.setCellWidget(row, 1, metaFieldItem.l_field)
            self.tw_metaEditor.setCellWidget(row, 2, metaFieldItem.cb_sourceField)
            self.tw_metaEditor.setCellWidget(row, 3, metaFieldItem.le_currentData)






class MetaFieldItem(QObject):
    def __init__(self, metaEditor, data: dict, parent=None):
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
        # Checkbox (centered)
        chb = QCheckBox()
        self.chb_enabled = chb
        self.chb_enabled_container = self.centeredWidget(chb)

        # Label
        self.l_field = QLabel(self.metaName)
        self.l_field.setStyleSheet("padding-left: 3px;")

        self.cb_sourceField = QComboBox()
        model = QStandardItemModel()
        self.combo_key_to_path = {}

        # Add special
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

        self.le_currentData = QLineEdit()


    def centeredWidget(self, widget):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addStretch()
        layout.addWidget(widget)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    
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
    


    

    def getInfo(self):
        info = {
            "field": self.field,
            "enabled": self.isEnabled(),
            "sourceField": self.sourceField,
            "currentData": self.currentData
        }
        return info


    def setFromInfo(self, info: dict):
        enabled = info.get("enabled", False)
        source_field = info.get("sourceField", "")
        current_data = info.get("currentData", "")

        self.chb_enabled.setChecked(enabled)

        # If sourceField is "- CUSTOM -" -> leave it
        if source_field == "- CUSTOM -":
            self.cb_sourceField.setCurrentText("- CUSTOM -")
            self.le_currentData.setText(current_data)
        else:
            # Otherwise, check if sourceField is still valid in the metadata
            valid_keys = self.combo_key_to_path.keys()

            if source_field in valid_keys:
                self.cb_sourceField.setCurrentText(source_field)
                # 👇 manually trigger update
                self.updateLineEdit(source_field)
            else:
                # Not found in metadata anymore
                self.cb_sourceField.setCurrentText("- NONE -")
                self.le_currentData.clear()






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
