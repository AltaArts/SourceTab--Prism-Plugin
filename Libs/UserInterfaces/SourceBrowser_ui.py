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
        w_sourceBrowser.resize(901, 521)
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
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lo_sourceHeader = QHBoxLayout()
        self.lo_sourceHeader.setObjectName(u"lo_sourceHeader")
        self.l_sourceText = QLabel(self.w_source)
        self.l_sourceText.setObjectName(u"l_sourceText")

        self.lo_sourceHeader.addWidget(self.l_sourceText)


        self.verticalLayout_8.addLayout(self.lo_sourceHeader)

        self.gb_sourcePath = QGroupBox(self.w_source)
        self.gb_sourcePath.setObjectName(u"gb_sourcePath")
        self.lo_sourcePath = QHBoxLayout(self.gb_sourcePath)
        self.lo_sourcePath.setObjectName(u"lo_sourcePath")
        self.lo_sourcePath.setContentsMargins(0, 0, 0, 0)
        self.b_sourcePathUp = QPushButton(self.gb_sourcePath)
        self.b_sourcePathUp.setObjectName(u"b_sourcePathUp")
        sizePolicy2 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.b_sourcePathUp.sizePolicy().hasHeightForWidth())
        self.b_sourcePathUp.setSizePolicy(sizePolicy2)
        self.b_sourcePathUp.setMinimumSize(QSize(30, 0))
        self.b_sourcePathUp.setMaximumSize(QSize(30, 16777215))
        self.b_sourcePathUp.setCheckable(False)

        self.lo_sourcePath.addWidget(self.b_sourcePathUp)

        self.le_sourcePath = QLineEdit(self.gb_sourcePath)
        self.le_sourcePath.setObjectName(u"le_sourcePath")

        self.lo_sourcePath.addWidget(self.le_sourcePath)

        self.b_browseSource = QPushButton(self.gb_sourcePath)
        self.b_browseSource.setObjectName(u"b_browseSource")
        sizePolicy2.setHeightForWidth(self.b_browseSource.sizePolicy().hasHeightForWidth())
        self.b_browseSource.setSizePolicy(sizePolicy2)
        self.b_browseSource.setMinimumSize(QSize(30, 0))
        self.b_browseSource.setMaximumSize(QSize(30, 16777215))

        self.lo_sourcePath.addWidget(self.b_browseSource)

        self.b_refreshSource = QPushButton(self.gb_sourcePath)
        self.b_refreshSource.setObjectName(u"b_refreshSource")
        sizePolicy2.setHeightForWidth(self.b_refreshSource.sizePolicy().hasHeightForWidth())
        self.b_refreshSource.setSizePolicy(sizePolicy2)
        self.b_refreshSource.setMinimumSize(QSize(30, 0))
        self.b_refreshSource.setMaximumSize(QSize(30, 16777215))

        self.lo_sourcePath.addWidget(self.b_refreshSource)


        self.verticalLayout_8.addWidget(self.gb_sourcePath)

        self.lo_sourceFilters = QHBoxLayout()
        self.lo_sourceFilters.setObjectName(u"lo_sourceFilters")
        self.b_sourceFilter_filtersEnable = QPushButton(self.w_source)
        self.b_sourceFilter_filtersEnable.setObjectName(u"b_sourceFilter_filtersEnable")
        sizePolicy2.setHeightForWidth(self.b_sourceFilter_filtersEnable.sizePolicy().hasHeightForWidth())
        self.b_sourceFilter_filtersEnable.setSizePolicy(sizePolicy2)
        self.b_sourceFilter_filtersEnable.setMinimumSize(QSize(30, 0))
        self.b_sourceFilter_filtersEnable.setMaximumSize(QSize(30, 16777215))
        self.b_sourceFilter_filtersEnable.setCheckable(True)

        self.lo_sourceFilters.addWidget(self.b_sourceFilter_filtersEnable)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_sourceFilters.addItem(self.horizontalSpacer_2)

        self.b_sourceFilter_combineSeqs = QPushButton(self.w_source)
        self.b_sourceFilter_combineSeqs.setObjectName(u"b_sourceFilter_combineSeqs")
        sizePolicy2.setHeightForWidth(self.b_sourceFilter_combineSeqs.sizePolicy().hasHeightForWidth())
        self.b_sourceFilter_combineSeqs.setSizePolicy(sizePolicy2)
        self.b_sourceFilter_combineSeqs.setMinimumSize(QSize(30, 0))
        self.b_sourceFilter_combineSeqs.setMaximumSize(QSize(30, 16777215))
        self.b_sourceFilter_combineSeqs.setCheckable(True)

        self.lo_sourceFilters.addWidget(self.b_sourceFilter_combineSeqs)


        self.verticalLayout_8.addLayout(self.lo_sourceFilters)

        self.tw_source = QTableWidget(self.w_source)
        self.tw_source.setObjectName(u"tw_source")
        self.tw_source.setContextMenuPolicy(Qt.NoContextMenu)
        self.tw_source.setSelectionMode(QAbstractItemView.NoSelection)

        self.verticalLayout_8.addWidget(self.tw_source)

        self.gb_sourceFooter = QGroupBox(self.w_source)
        self.gb_sourceFooter.setObjectName(u"gb_sourceFooter")
        self.lo_sourceFooter = QHBoxLayout(self.gb_sourceFooter)
        self.lo_sourceFooter.setObjectName(u"lo_sourceFooter")
        self.lo_sourceFooter.setContentsMargins(20, 0, 20, 0)
        self.b_tips_source = QPushButton(self.gb_sourceFooter)
        self.b_tips_source.setObjectName(u"b_tips_source")
        sizePolicy2.setHeightForWidth(self.b_tips_source.sizePolicy().hasHeightForWidth())
        self.b_tips_source.setSizePolicy(sizePolicy2)
        self.b_tips_source.setMinimumSize(QSize(20, 0))
        self.b_tips_source.setMaximumSize(QSize(20, 16777215))

        self.lo_sourceFooter.addWidget(self.b_tips_source)

        self.horizontalSpacer = QSpacerItem(30, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_sourceFooter.addItem(self.horizontalSpacer)

        self.b_source_checkAll = QPushButton(self.gb_sourceFooter)
        self.b_source_checkAll.setObjectName(u"b_source_checkAll")
        sizePolicy3 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.b_source_checkAll.sizePolicy().hasHeightForWidth())
        self.b_source_checkAll.setSizePolicy(sizePolicy3)
        self.b_source_checkAll.setMinimumSize(QSize(100, 0))

        self.lo_sourceFooter.addWidget(self.b_source_checkAll)

        self.b_source_uncheckAll = QPushButton(self.gb_sourceFooter)
        self.b_source_uncheckAll.setObjectName(u"b_source_uncheckAll")
        sizePolicy3.setHeightForWidth(self.b_source_uncheckAll.sizePolicy().hasHeightForWidth())
        self.b_source_uncheckAll.setSizePolicy(sizePolicy3)
        self.b_source_uncheckAll.setMinimumSize(QSize(100, 0))

        self.lo_sourceFooter.addWidget(self.b_source_uncheckAll)

        self.b_source_addSel = QPushButton(self.gb_sourceFooter)
        self.b_source_addSel.setObjectName(u"b_source_addSel")
        sizePolicy3.setHeightForWidth(self.b_source_addSel.sizePolicy().hasHeightForWidth())
        self.b_source_addSel.setSizePolicy(sizePolicy3)
        self.b_source_addSel.setMinimumSize(QSize(100, 0))

        self.lo_sourceFooter.addWidget(self.b_source_addSel)


        self.verticalLayout_8.addWidget(self.gb_sourceFooter)

        self.splitter.addWidget(self.w_source)
        self.w_destination = QWidget(self.splitter)
        self.w_destination.setObjectName(u"w_destination")
        sizePolicy1.setHeightForWidth(self.w_destination.sizePolicy().hasHeightForWidth())
        self.w_destination.setSizePolicy(sizePolicy1)
        self.verticalLayout_11 = QVBoxLayout(self.w_destination)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.lo_DestHeader = QHBoxLayout()
        self.lo_DestHeader.setObjectName(u"lo_DestHeader")
        self.l_destText = QLabel(self.w_destination)
        self.l_destText.setObjectName(u"l_destText")
        sizePolicy.setHeightForWidth(self.l_destText.sizePolicy().hasHeightForWidth())
        self.l_destText.setSizePolicy(sizePolicy)

        self.lo_DestHeader.addWidget(self.l_destText)


        self.verticalLayout_11.addLayout(self.lo_DestHeader)

        self.gb_destPath = QGroupBox(self.w_destination)
        self.gb_destPath.setObjectName(u"gb_destPath")
        sizePolicy.setHeightForWidth(self.gb_destPath.sizePolicy().hasHeightForWidth())
        self.gb_destPath.setSizePolicy(sizePolicy)
        self.lo_destPath = QHBoxLayout(self.gb_destPath)
        self.lo_destPath.setObjectName(u"lo_destPath")
        self.lo_destPath.setContentsMargins(0, 0, 0, 0)
        self.b_destPathUp = QPushButton(self.gb_destPath)
        self.b_destPathUp.setObjectName(u"b_destPathUp")
        sizePolicy2.setHeightForWidth(self.b_destPathUp.sizePolicy().hasHeightForWidth())
        self.b_destPathUp.setSizePolicy(sizePolicy2)
        self.b_destPathUp.setMinimumSize(QSize(30, 0))
        self.b_destPathUp.setMaximumSize(QSize(30, 16777215))

        self.lo_destPath.addWidget(self.b_destPathUp)

        self.le_destPath = QLineEdit(self.gb_destPath)
        self.le_destPath.setObjectName(u"le_destPath")

        self.lo_destPath.addWidget(self.le_destPath)

        self.b_browseDest = QPushButton(self.gb_destPath)
        self.b_browseDest.setObjectName(u"b_browseDest")
        sizePolicy2.setHeightForWidth(self.b_browseDest.sizePolicy().hasHeightForWidth())
        self.b_browseDest.setSizePolicy(sizePolicy2)
        self.b_browseDest.setMinimumSize(QSize(30, 0))
        self.b_browseDest.setMaximumSize(QSize(30, 16777215))

        self.lo_destPath.addWidget(self.b_browseDest)

        self.b_refreshDest = QPushButton(self.gb_destPath)
        self.b_refreshDest.setObjectName(u"b_refreshDest")
        sizePolicy2.setHeightForWidth(self.b_refreshDest.sizePolicy().hasHeightForWidth())
        self.b_refreshDest.setSizePolicy(sizePolicy2)
        self.b_refreshDest.setMinimumSize(QSize(30, 0))
        self.b_refreshDest.setMaximumSize(QSize(30, 16777215))

        self.lo_destPath.addWidget(self.b_refreshDest)


        self.verticalLayout_11.addWidget(self.gb_destPath)

        self.lo_destFilters = QHBoxLayout()
        self.lo_destFilters.setObjectName(u"lo_destFilters")
        self.b_destFilter_filtersEnable = QPushButton(self.w_destination)
        self.b_destFilter_filtersEnable.setObjectName(u"b_destFilter_filtersEnable")
        sizePolicy2.setHeightForWidth(self.b_destFilter_filtersEnable.sizePolicy().hasHeightForWidth())
        self.b_destFilter_filtersEnable.setSizePolicy(sizePolicy2)
        self.b_destFilter_filtersEnable.setMinimumSize(QSize(30, 0))
        self.b_destFilter_filtersEnable.setMaximumSize(QSize(30, 16777215))
        self.b_destFilter_filtersEnable.setCheckable(True)

        self.lo_destFilters.addWidget(self.b_destFilter_filtersEnable)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_destFilters.addItem(self.horizontalSpacer_4)

        self.b_destFilter_combineSeqs = QPushButton(self.w_destination)
        self.b_destFilter_combineSeqs.setObjectName(u"b_destFilter_combineSeqs")
        sizePolicy2.setHeightForWidth(self.b_destFilter_combineSeqs.sizePolicy().hasHeightForWidth())
        self.b_destFilter_combineSeqs.setSizePolicy(sizePolicy2)
        self.b_destFilter_combineSeqs.setMinimumSize(QSize(30, 0))
        self.b_destFilter_combineSeqs.setMaximumSize(QSize(30, 16777215))
        self.b_destFilter_combineSeqs.setCheckable(True)

        self.lo_destFilters.addWidget(self.b_destFilter_combineSeqs)


        self.verticalLayout_11.addLayout(self.lo_destFilters)

        self.tw_destination = QTableWidget(self.w_destination)
        self.tw_destination.setObjectName(u"tw_destination")
        self.tw_destination.setMaximumSize(QSize(16777215, 16777215))
        self.tw_destination.setContextMenuPolicy(Qt.NoContextMenu)
        self.tw_destination.setSelectionMode(QAbstractItemView.NoSelection)

        self.verticalLayout_11.addWidget(self.tw_destination)

        self.gb_destFooter = QGroupBox(self.w_destination)
        self.gb_destFooter.setObjectName(u"gb_destFooter")
        self.lo_destFooter = QHBoxLayout(self.gb_destFooter)
        self.lo_destFooter.setObjectName(u"lo_destFooter")
        self.lo_destFooter.setContentsMargins(20, 0, 20, 0)
        self.b_tips_dest = QPushButton(self.gb_destFooter)
        self.b_tips_dest.setObjectName(u"b_tips_dest")
        sizePolicy2.setHeightForWidth(self.b_tips_dest.sizePolicy().hasHeightForWidth())
        self.b_tips_dest.setSizePolicy(sizePolicy2)
        self.b_tips_dest.setMinimumSize(QSize(20, 0))
        self.b_tips_dest.setMaximumSize(QSize(20, 16777215))

        self.lo_destFooter.addWidget(self.b_tips_dest)

        self.horizontalSpacer_3 = QSpacerItem(30, 20, QSizePolicy.Fixed, QSizePolicy.Minimum)

        self.lo_destFooter.addItem(self.horizontalSpacer_3)

        self.b_dest_checkAll = QPushButton(self.gb_destFooter)
        self.b_dest_checkAll.setObjectName(u"b_dest_checkAll")
        sizePolicy3.setHeightForWidth(self.b_dest_checkAll.sizePolicy().hasHeightForWidth())
        self.b_dest_checkAll.setSizePolicy(sizePolicy3)
        self.b_dest_checkAll.setMinimumSize(QSize(100, 0))

        self.lo_destFooter.addWidget(self.b_dest_checkAll)

        self.b_dest_uncheckAll = QPushButton(self.gb_destFooter)
        self.b_dest_uncheckAll.setObjectName(u"b_dest_uncheckAll")
        sizePolicy3.setHeightForWidth(self.b_dest_uncheckAll.sizePolicy().hasHeightForWidth())
        self.b_dest_uncheckAll.setSizePolicy(sizePolicy3)
        self.b_dest_uncheckAll.setMinimumSize(QSize(100, 0))

        self.lo_destFooter.addWidget(self.b_dest_uncheckAll)

        self.b_dest_clearSel = QPushButton(self.gb_destFooter)
        self.b_dest_clearSel.setObjectName(u"b_dest_clearSel")
        sizePolicy3.setHeightForWidth(self.b_dest_clearSel.sizePolicy().hasHeightForWidth())
        self.b_dest_clearSel.setSizePolicy(sizePolicy3)
        self.b_dest_clearSel.setMinimumSize(QSize(100, 0))

        self.lo_destFooter.addWidget(self.b_dest_clearSel)

        self.b_dest_clearAll = QPushButton(self.gb_destFooter)
        self.b_dest_clearAll.setObjectName(u"b_dest_clearAll")
        sizePolicy3.setHeightForWidth(self.b_dest_clearAll.sizePolicy().hasHeightForWidth())
        self.b_dest_clearAll.setSizePolicy(sizePolicy3)
        self.b_dest_clearAll.setMinimumSize(QSize(100, 0))

        self.lo_destFooter.addWidget(self.b_dest_clearAll)


        self.verticalLayout_11.addWidget(self.gb_destFooter)

        self.splitter.addWidget(self.w_destination)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceBrowser)

        QMetaObject.connectSlotsByName(w_sourceBrowser)
    # setupUi

    def retranslateUi(self, w_sourceBrowser):
        w_sourceBrowser.setWindowTitle(QCoreApplication.translate("w_sourceBrowser", u"Source Browser", None))
        self.l_sourceText.setText(QCoreApplication.translate("w_sourceBrowser", u"Source", None))
        self.b_sourcePathUp.setText("")
        self.b_browseSource.setText("")
        self.b_refreshSource.setText("")
        self.b_sourceFilter_filtersEnable.setText("")
        self.b_sourceFilter_combineSeqs.setText("")
        self.b_tips_source.setText("")
        self.b_source_checkAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Select All", None))
        self.b_source_uncheckAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Unselect All", None))
        self.b_source_addSel.setText(QCoreApplication.translate("w_sourceBrowser", u"Add Selected", None))
        self.l_destText.setText(QCoreApplication.translate("w_sourceBrowser", u"Destination", None))
        self.b_destPathUp.setText("")
        self.b_browseDest.setText("")
        self.b_refreshDest.setText("")
        self.b_destFilter_filtersEnable.setText("")
        self.b_destFilter_combineSeqs.setText("")
        self.b_tips_dest.setText("")
        self.b_dest_checkAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Select All", None))
        self.b_dest_uncheckAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Unselect All", None))
        self.b_dest_clearSel.setText(QCoreApplication.translate("w_sourceBrowser", u"Remove Selected", None))
        self.b_dest_clearAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Remove All", None))
    # retranslateUi

