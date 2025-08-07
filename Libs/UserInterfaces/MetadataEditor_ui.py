# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MetadataEditor.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

class Ui_w_metadataEditor(object):
    def setupUi(self, w_metadataEditor):
        if not w_metadataEditor.objectName():
            w_metadataEditor.setObjectName(u"w_metadataEditor")
        w_metadataEditor.resize(1000, 900)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(w_metadataEditor.sizePolicy().hasHeightForWidth())
        w_metadataEditor.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(w_metadataEditor)
        self.horizontalLayout.setSpacing(4)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(4, 4, 4, 4)
        self.lo_main = QVBoxLayout()
        self.lo_main.setObjectName(u"lo_main")
        self.lo_top = QHBoxLayout()
        self.lo_top.setObjectName(u"lo_top")
        self.cb_fileList = QComboBox(w_metadataEditor)
        self.cb_fileList.setObjectName(u"cb_fileList")

        self.lo_top.addWidget(self.cb_fileList)

        self.b_showMetadataPopup = QPushButton(w_metadataEditor)
        self.b_showMetadataPopup.setObjectName(u"b_showMetadataPopup")

        self.lo_top.addWidget(self.b_showMetadataPopup)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_top.addItem(self.horizontalSpacer_3)

        self.b_filters = QPushButton(w_metadataEditor)
        self.b_filters.setObjectName(u"b_filters")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.b_filters.sizePolicy().hasHeightForWidth())
        self.b_filters.setSizePolicy(sizePolicy1)
        self.b_filters.setMinimumSize(QSize(30, 0))
        self.b_filters.setMaximumSize(QSize(30, 16777215))
        self.b_filters.setCheckable(True)

        self.lo_top.addWidget(self.b_filters)

        self.b_reset = QPushButton(w_metadataEditor)
        self.b_reset.setObjectName(u"b_reset")
        sizePolicy1.setHeightForWidth(self.b_reset.sizePolicy().hasHeightForWidth())
        self.b_reset.setSizePolicy(sizePolicy1)
        self.b_reset.setMinimumSize(QSize(30, 0))
        self.b_reset.setMaximumSize(QSize(30, 16777215))

        self.lo_top.addWidget(self.b_reset)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_top.addItem(self.horizontalSpacer_2)

        self.cb_presets = QComboBox(w_metadataEditor)
        self.cb_presets.setObjectName(u"cb_presets")

        self.lo_top.addWidget(self.cb_presets)

        self.horizontalSpacer_4 = QSpacerItem(20, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_top.addItem(self.horizontalSpacer_4)

        self.b_presets = QPushButton(w_metadataEditor)
        self.b_presets.setObjectName(u"b_presets")

        self.lo_top.addWidget(self.b_presets)


        self.lo_main.addLayout(self.lo_top)

        self.tw_metaEditor = QTableView(w_metadataEditor)
        self.tw_metaEditor.setObjectName(u"tw_metaEditor")

        self.lo_main.addWidget(self.tw_metaEditor)

        self.lo_bottom = QHBoxLayout()
        self.lo_bottom.setObjectName(u"lo_bottom")
        self.b_sidecarMenu = QPushButton(w_metadataEditor)
        self.b_sidecarMenu.setObjectName(u"b_sidecarMenu")

        self.lo_bottom.addWidget(self.b_sidecarMenu)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_bottom.addItem(self.horizontalSpacer_5)

        self.b_sidecar_save = QPushButton(w_metadataEditor)
        self.b_sidecar_save.setObjectName(u"b_sidecar_save")

        self.lo_bottom.addWidget(self.b_sidecar_save)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_bottom.addItem(self.horizontalSpacer)

        self.b_save = QPushButton(w_metadataEditor)
        self.b_save.setObjectName(u"b_save")

        self.lo_bottom.addWidget(self.b_save)

        self.b_close = QPushButton(w_metadataEditor)
        self.b_close.setObjectName(u"b_close")

        self.lo_bottom.addWidget(self.b_close)


        self.lo_main.addLayout(self.lo_bottom)


        self.horizontalLayout.addLayout(self.lo_main)


        self.retranslateUi(w_metadataEditor)

        QMetaObject.connectSlotsByName(w_metadataEditor)
    # setupUi

    def retranslateUi(self, w_metadataEditor):
        w_metadataEditor.setWindowTitle(QCoreApplication.translate("w_metadataEditor", u"Metadata Editor", None))
        self.b_showMetadataPopup.setText(QCoreApplication.translate("w_metadataEditor", u"View Metadata", None))
        self.b_filters.setText("")
        self.b_reset.setText("")
        self.b_presets.setText(QCoreApplication.translate("w_metadataEditor", u"Edit", None))
        self.b_sidecarMenu.setText(QCoreApplication.translate("w_metadataEditor", u"Metadata Sidecar Types", None))
        self.b_sidecar_save.setText(QCoreApplication.translate("w_metadataEditor", u"Generate Sidecar Now", None))
        self.b_save.setText(QCoreApplication.translate("w_metadataEditor", u"SAVE", None))
        self.b_close.setText(QCoreApplication.translate("w_metadataEditor", u"CLOSE", None))
    # retranslateUi

