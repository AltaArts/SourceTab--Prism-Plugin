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
