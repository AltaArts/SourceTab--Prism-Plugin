# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SourceBrowser.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

class Ui_w_sourceBrowser(object):
    def setupUi(self, w_sourceBrowser):
        if not w_sourceBrowser.objectName():
            w_sourceBrowser.setObjectName(u"w_sourceBrowser")
        w_sourceBrowser.resize(961, 521)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(w_sourceBrowser.sizePolicy().hasHeightForWidth())
        w_sourceBrowser.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(w_sourceBrowser)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceBrowser)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.w_source = QWidget(self.splitter)
        self.w_source.setObjectName(u"w_source")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(8)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.w_source.sizePolicy().hasHeightForWidth())
        self.w_source.setSizePolicy(sizePolicy1)
        self.verticalLayout_8 = QVBoxLayout(self.w_source)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lo_source_title = QHBoxLayout()
        self.lo_source_title.setObjectName(u"lo_source_title")
        self.lo_source_title.setContentsMargins(4, -1, -1, -1)
        self.b_tips_source = QPushButton(self.w_source)
        self.b_tips_source.setObjectName(u"b_tips_source")
        sizePolicy2 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.b_tips_source.sizePolicy().hasHeightForWidth())
        self.b_tips_source.setSizePolicy(sizePolicy2)
        self.b_tips_source.setMinimumSize(QSize(30, 0))
        self.b_tips_source.setMaximumSize(QSize(30, 16777215))

        self.lo_source_title.addWidget(self.b_tips_source)

        self.horizontalSpacer = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_source_title.addItem(self.horizontalSpacer)

        self.l_source_title = QLabel(self.w_source)
        self.l_source_title.setObjectName(u"l_source_title")
        font = QFont()
        font.setBold(True)
        self.l_source_title.setFont(font)

        self.lo_source_title.addWidget(self.l_source_title)


        self.verticalLayout_8.addLayout(self.lo_source_title)

        self.gb_sourceHeader = QGroupBox(self.w_source)
        self.gb_sourceHeader.setObjectName(u"gb_sourceHeader")
        self.lo_sourceHeader = QVBoxLayout(self.gb_sourceHeader)
        self.lo_sourceHeader.setObjectName(u"lo_sourceHeader")
        self.lo_sourceHeader.setContentsMargins(0, 0, 0, 0)
        self.lo_source_path = QHBoxLayout()
        self.lo_source_path.setObjectName(u"lo_source_path")
        self.b_sourcePathUp = QPushButton(self.gb_sourceHeader)
        self.b_sourcePathUp.setObjectName(u"b_sourcePathUp")
        sizePolicy2.setHeightForWidth(self.b_sourcePathUp.sizePolicy().hasHeightForWidth())
        self.b_sourcePathUp.setSizePolicy(sizePolicy2)
        self.b_sourcePathUp.setMinimumSize(QSize(30, 0))
        self.b_sourcePathUp.setMaximumSize(QSize(30, 16777215))
        self.b_sourcePathUp.setCheckable(False)

        self.lo_source_path.addWidget(self.b_sourcePathUp)

        self.le_sourcePath = QLineEdit(self.gb_sourceHeader)
        self.le_sourcePath.setObjectName(u"le_sourcePath")

        self.lo_source_path.addWidget(self.le_sourcePath)

        self.b_browseSource = QPushButton(self.gb_sourceHeader)
        self.b_browseSource.setObjectName(u"b_browseSource")
        sizePolicy2.setHeightForWidth(self.b_browseSource.sizePolicy().hasHeightForWidth())
        self.b_browseSource.setSizePolicy(sizePolicy2)
        self.b_browseSource.setMinimumSize(QSize(30, 0))
        self.b_browseSource.setMaximumSize(QSize(30, 16777215))

        self.lo_source_path.addWidget(self.b_browseSource)

        self.b_refreshSource = QPushButton(self.gb_sourceHeader)
        self.b_refreshSource.setObjectName(u"b_refreshSource")
        sizePolicy2.setHeightForWidth(self.b_refreshSource.sizePolicy().hasHeightForWidth())
        self.b_refreshSource.setSizePolicy(sizePolicy2)
        self.b_refreshSource.setMinimumSize(QSize(30, 0))
        self.b_refreshSource.setMaximumSize(QSize(30, 16777215))

        self.lo_source_path.addWidget(self.b_refreshSource)


        self.lo_sourceHeader.addLayout(self.lo_source_path)

        self.lo_source_sorting = QHBoxLayout()
        self.lo_source_sorting.setObjectName(u"lo_source_sorting")
        self.b_source_sorting_sort = QPushButton(self.gb_sourceHeader)
        self.b_source_sorting_sort.setObjectName(u"b_source_sorting_sort")
        sizePolicy2.setHeightForWidth(self.b_source_sorting_sort.sizePolicy().hasHeightForWidth())
        self.b_source_sorting_sort.setSizePolicy(sizePolicy2)
        self.b_source_sorting_sort.setMinimumSize(QSize(30, 0))
        self.b_source_sorting_sort.setMaximumSize(QSize(30, 16777215))
        self.b_source_sorting_sort.setCheckable(False)

        self.lo_source_sorting.addWidget(self.b_source_sorting_sort)

        self.b_source_sorting_duration = QPushButton(self.gb_sourceHeader)
        self.b_source_sorting_duration.setObjectName(u"b_source_sorting_duration")
        sizePolicy2.setHeightForWidth(self.b_source_sorting_duration.sizePolicy().hasHeightForWidth())
        self.b_source_sorting_duration.setSizePolicy(sizePolicy2)
        self.b_source_sorting_duration.setMinimumSize(QSize(30, 0))
        self.b_source_sorting_duration.setMaximumSize(QSize(30, 16777215))
        self.b_source_sorting_duration.setCheckable(True)

        self.lo_source_sorting.addWidget(self.b_source_sorting_duration)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_source_sorting.addItem(self.horizontalSpacer_2)

        self.b_source_sorting_filtersEnable = QPushButton(self.gb_sourceHeader)
        self.b_source_sorting_filtersEnable.setObjectName(u"b_source_sorting_filtersEnable")
        sizePolicy2.setHeightForWidth(self.b_source_sorting_filtersEnable.sizePolicy().hasHeightForWidth())
        self.b_source_sorting_filtersEnable.setSizePolicy(sizePolicy2)
        self.b_source_sorting_filtersEnable.setMinimumSize(QSize(30, 0))
        self.b_source_sorting_filtersEnable.setMaximumSize(QSize(30, 16777215))
        self.b_source_sorting_filtersEnable.setCheckable(True)

        self.lo_source_sorting.addWidget(self.b_source_sorting_filtersEnable)

        self.b_source_sorting_combineSeqs = QPushButton(self.gb_sourceHeader)
        self.b_source_sorting_combineSeqs.setObjectName(u"b_source_sorting_combineSeqs")
        sizePolicy2.setHeightForWidth(self.b_source_sorting_combineSeqs.sizePolicy().hasHeightForWidth())
        self.b_source_sorting_combineSeqs.setSizePolicy(sizePolicy2)
        self.b_source_sorting_combineSeqs.setMinimumSize(QSize(30, 0))
        self.b_source_sorting_combineSeqs.setMaximumSize(QSize(30, 16777215))
        self.b_source_sorting_combineSeqs.setCheckable(True)

        self.lo_source_sorting.addWidget(self.b_source_sorting_combineSeqs)


        self.lo_sourceHeader.addLayout(self.lo_source_sorting)


        self.verticalLayout_8.addWidget(self.gb_sourceHeader)

        self.lw_source = QListWidget(self.w_source)
        self.lw_source.setObjectName(u"lw_source")
        self.lw_source.setContextMenuPolicy(Qt.NoContextMenu)
        self.lw_source.setSelectionMode(QAbstractItemView.NoSelection)

        self.verticalLayout_8.addWidget(self.lw_source)

        self.splitter.addWidget(self.w_source)
        self.w_destination = QWidget(self.splitter)
        self.w_destination.setObjectName(u"w_destination")
        sizePolicy1.setHeightForWidth(self.w_destination.sizePolicy().hasHeightForWidth())
        self.w_destination.setSizePolicy(sizePolicy1)
        self.verticalLayout_11 = QVBoxLayout(self.w_destination)
        self.verticalLayout_11.setSpacing(0)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.lo_dest_title = QHBoxLayout()
        self.lo_dest_title.setObjectName(u"lo_dest_title")
        self.lo_dest_title.setContentsMargins(4, -1, -1, -1)
        self.b_tips_dest = QPushButton(self.w_destination)
        self.b_tips_dest.setObjectName(u"b_tips_dest")
        sizePolicy2.setHeightForWidth(self.b_tips_dest.sizePolicy().hasHeightForWidth())
        self.b_tips_dest.setSizePolicy(sizePolicy2)
        self.b_tips_dest.setMinimumSize(QSize(30, 0))
        self.b_tips_dest.setMaximumSize(QSize(30, 16777215))

        self.lo_dest_title.addWidget(self.b_tips_dest)

        self.horizontalSpacer_3 = QSpacerItem(10, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_dest_title.addItem(self.horizontalSpacer_3)

        self.l_dest_title = QLabel(self.w_destination)
        self.l_dest_title.setObjectName(u"l_dest_title")
        sizePolicy.setHeightForWidth(self.l_dest_title.sizePolicy().hasHeightForWidth())
        self.l_dest_title.setSizePolicy(sizePolicy)
        self.l_dest_title.setFont(font)

        self.lo_dest_title.addWidget(self.l_dest_title)


        self.verticalLayout_11.addLayout(self.lo_dest_title)

        self.gb_destHeader = QGroupBox(self.w_destination)
        self.gb_destHeader.setObjectName(u"gb_destHeader")
        self.lo_destHeader = QVBoxLayout(self.gb_destHeader)
        self.lo_destHeader.setObjectName(u"lo_destHeader")
        self.lo_destHeader.setContentsMargins(0, 0, 0, 0)
        self.lo_dest_path = QHBoxLayout()
        self.lo_dest_path.setObjectName(u"lo_dest_path")
        self.b_destPathUp = QPushButton(self.gb_destHeader)
        self.b_destPathUp.setObjectName(u"b_destPathUp")
        sizePolicy2.setHeightForWidth(self.b_destPathUp.sizePolicy().hasHeightForWidth())
        self.b_destPathUp.setSizePolicy(sizePolicy2)
        self.b_destPathUp.setMinimumSize(QSize(30, 0))
        self.b_destPathUp.setMaximumSize(QSize(30, 16777215))

        self.lo_dest_path.addWidget(self.b_destPathUp)

        self.le_destPath = QLineEdit(self.gb_destHeader)
        self.le_destPath.setObjectName(u"le_destPath")

        self.lo_dest_path.addWidget(self.le_destPath)

        self.b_browseDest = QPushButton(self.gb_destHeader)
        self.b_browseDest.setObjectName(u"b_browseDest")
        sizePolicy2.setHeightForWidth(self.b_browseDest.sizePolicy().hasHeightForWidth())
        self.b_browseDest.setSizePolicy(sizePolicy2)
        self.b_browseDest.setMinimumSize(QSize(30, 0))
        self.b_browseDest.setMaximumSize(QSize(30, 16777215))

        self.lo_dest_path.addWidget(self.b_browseDest)

        self.b_refreshDest = QPushButton(self.gb_destHeader)
        self.b_refreshDest.setObjectName(u"b_refreshDest")
        sizePolicy2.setHeightForWidth(self.b_refreshDest.sizePolicy().hasHeightForWidth())
        self.b_refreshDest.setSizePolicy(sizePolicy2)
        self.b_refreshDest.setMinimumSize(QSize(30, 0))
        self.b_refreshDest.setMaximumSize(QSize(30, 16777215))

        self.lo_dest_path.addWidget(self.b_refreshDest)


        self.lo_destHeader.addLayout(self.lo_dest_path)

        self.lo_dest_sorting = QHBoxLayout()
        self.lo_dest_sorting.setObjectName(u"lo_dest_sorting")
        self.b_dest_sorting_sort = QPushButton(self.gb_destHeader)
        self.b_dest_sorting_sort.setObjectName(u"b_dest_sorting_sort")
        sizePolicy2.setHeightForWidth(self.b_dest_sorting_sort.sizePolicy().hasHeightForWidth())
        self.b_dest_sorting_sort.setSizePolicy(sizePolicy2)
        self.b_dest_sorting_sort.setMinimumSize(QSize(30, 0))
        self.b_dest_sorting_sort.setMaximumSize(QSize(30, 16777215))
        self.b_dest_sorting_sort.setCheckable(False)

        self.lo_dest_sorting.addWidget(self.b_dest_sorting_sort)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_dest_sorting.addItem(self.horizontalSpacer_4)

        self.b_dest_sorting_filtersEnable = QPushButton(self.gb_destHeader)
        self.b_dest_sorting_filtersEnable.setObjectName(u"b_dest_sorting_filtersEnable")
        sizePolicy2.setHeightForWidth(self.b_dest_sorting_filtersEnable.sizePolicy().hasHeightForWidth())
        self.b_dest_sorting_filtersEnable.setSizePolicy(sizePolicy2)
        self.b_dest_sorting_filtersEnable.setMinimumSize(QSize(30, 0))
        self.b_dest_sorting_filtersEnable.setMaximumSize(QSize(30, 16777215))
        self.b_dest_sorting_filtersEnable.setCheckable(True)

        self.lo_dest_sorting.addWidget(self.b_dest_sorting_filtersEnable)

        self.b_dest_sorting_combineSeqs = QPushButton(self.gb_destHeader)
        self.b_dest_sorting_combineSeqs.setObjectName(u"b_dest_sorting_combineSeqs")
        sizePolicy2.setHeightForWidth(self.b_dest_sorting_combineSeqs.sizePolicy().hasHeightForWidth())
        self.b_dest_sorting_combineSeqs.setSizePolicy(sizePolicy2)
        self.b_dest_sorting_combineSeqs.setMinimumSize(QSize(30, 0))
        self.b_dest_sorting_combineSeqs.setMaximumSize(QSize(30, 16777215))
        self.b_dest_sorting_combineSeqs.setCheckable(True)

        self.lo_dest_sorting.addWidget(self.b_dest_sorting_combineSeqs)


        self.lo_destHeader.addLayout(self.lo_dest_sorting)


        self.verticalLayout_11.addWidget(self.gb_destHeader)

        self.lw_destination = QListWidget(self.w_destination)
        self.lw_destination.setObjectName(u"lw_destination")
        self.lw_destination.setMaximumSize(QSize(16777215, 16777215))
        self.lw_destination.setContextMenuPolicy(Qt.NoContextMenu)
        self.lw_destination.setSelectionMode(QAbstractItemView.NoSelection)

        self.verticalLayout_11.addWidget(self.lw_destination)

        self.splitter.addWidget(self.w_destination)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceBrowser)

        QMetaObject.connectSlotsByName(w_sourceBrowser)
    # setupUi

    def retranslateUi(self, w_sourceBrowser):
        w_sourceBrowser.setWindowTitle(QCoreApplication.translate("w_sourceBrowser", u"Media Browser", None))
        self.b_tips_source.setText("")
        self.l_source_title.setText(QCoreApplication.translate("w_sourceBrowser", u"Source", None))
        self.b_sourcePathUp.setText("")
        self.b_browseSource.setText("")
        self.b_refreshSource.setText("")
        self.b_source_sorting_sort.setText("")
        self.b_source_sorting_duration.setText("")
        self.b_source_sorting_filtersEnable.setText("")
        self.b_source_sorting_combineSeqs.setText("")
        self.b_tips_dest.setText("")
        self.l_dest_title.setText(QCoreApplication.translate("w_sourceBrowser", u"Destination", None))
        self.b_destPathUp.setText("")
        self.b_browseDest.setText("")
        self.b_refreshDest.setText("")
        self.b_dest_sorting_sort.setText("")
        self.b_dest_sorting_filtersEnable.setText("")
        self.b_dest_sorting_combineSeqs.setText("")
    # retranslateUi

