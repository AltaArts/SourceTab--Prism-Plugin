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

if "PRISM_SYSPATH" in os.environ:
    prism_path_list = os.environ["PRISM_SYSPATH"].split(os.pathsep)
    sys.path = prism_path_list + sys.path

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


def main():
    app = QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
    dialog.setAttribute(Qt.WA_TranslucentBackground)

    layout = QVBoxLayout()
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setAlignment(Qt.AlignCenter)

    label = QLabel()
    label.setAlignment(Qt.AlignCenter)

    gif_path = sys.argv[1]
    movie = QMovie(gif_path)
    label.setMovie(movie)
    movie.start()

    layout.addWidget(label)
    dialog.setLayout(layout)
    dialog.adjustSize()

    if len(sys.argv) >= 6:
        try:
            x, y, w, h = map(int, sys.argv[2:6])
            center_x = x + w // 2
            center_y = y + h // 2

            popup_rect = dialog.frameGeometry()
            dialog.move(center_x - popup_rect.width() // 2, center_y - popup_rect.height() // 2)

        except Exception as e:
            print("[WAITPOPUP]: Failed to center popup:", e)

    dialog.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
