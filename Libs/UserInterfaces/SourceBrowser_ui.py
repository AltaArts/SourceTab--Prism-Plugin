# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SourceBrowser.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_w_sourceBrowser(object):
    def setupUi(self, w_sourceBrowser):
        if not w_sourceBrowser.objectName():
            w_sourceBrowser.setObjectName(u"w_sourceBrowser")
        w_sourceBrowser.resize(714, 393)
        self.horizontalLayout = QHBoxLayout(w_sourceBrowser)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceBrowser)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.w_source = QWidget(self.splitter)
        self.w_source.setObjectName(u"w_source")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_source.sizePolicy().hasHeightForWidth())
        self.w_source.setSizePolicy(sizePolicy)
        self.verticalLayout_8 = QVBoxLayout(self.w_source)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lo_sourceHeader = QHBoxLayout()
        self.lo_sourceHeader.setObjectName(u"lo_sourceHeader")
        self.l_identifier = QLabel(self.w_source)
        self.l_identifier.setObjectName(u"l_identifier")

        self.lo_sourceHeader.addWidget(self.l_identifier)


        self.verticalLayout_8.addLayout(self.lo_sourceHeader)

        self.lo_sourcePath = QHBoxLayout()
        self.lo_sourcePath.setObjectName(u"lo_sourcePath")
        self.b_sourcePathUp = QPushButton(self.w_source)
        self.b_sourcePathUp.setObjectName(u"b_sourcePathUp")
        self.b_sourcePathUp.setCheckable(False)

        self.lo_sourcePath.addWidget(self.b_sourcePathUp)

        self.l_sourcePath = QLineEdit(self.w_source)
        self.l_sourcePath.setObjectName(u"l_sourcePath")

        self.lo_sourcePath.addWidget(self.l_sourcePath)

        self.b_browseSource = QPushButton(self.w_source)
        self.b_browseSource.setObjectName(u"b_browseSource")

        self.lo_sourcePath.addWidget(self.b_browseSource)


        self.verticalLayout_8.addLayout(self.lo_sourcePath)

        self.tw_source = QTableWidget(self.w_source)
        self.tw_source.setObjectName(u"tw_source")
        self.tw_source.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_source.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.verticalLayout_8.addWidget(self.tw_source)

        self.lo_sourceFooter = QHBoxLayout()
        self.lo_sourceFooter.setObjectName(u"lo_sourceFooter")
        self.b_source_checkAll = QPushButton(self.w_source)
        self.b_source_checkAll.setObjectName(u"b_source_checkAll")

        self.lo_sourceFooter.addWidget(self.b_source_checkAll)

        self.b_source_uncheckAll = QPushButton(self.w_source)
        self.b_source_uncheckAll.setObjectName(u"b_source_uncheckAll")

        self.lo_sourceFooter.addWidget(self.b_source_uncheckAll)

        self.b_source_addSel = QPushButton(self.w_source)
        self.b_source_addSel.setObjectName(u"b_source_addSel")

        self.lo_sourceFooter.addWidget(self.b_source_addSel)


        self.verticalLayout_8.addLayout(self.lo_sourceFooter)

        self.splitter.addWidget(self.w_source)
        self.w_destination = QWidget(self.splitter)
        self.w_destination.setObjectName(u"w_destination")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(9)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.w_destination.sizePolicy().hasHeightForWidth())
        self.w_destination.setSizePolicy(sizePolicy1)
        self.verticalLayout_11 = QVBoxLayout(self.w_destination)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.lo_DestHeader = QHBoxLayout()
        self.lo_DestHeader.setObjectName(u"lo_DestHeader")
        self.l_version = QLabel(self.w_destination)
        self.l_version.setObjectName(u"l_version")

        self.lo_DestHeader.addWidget(self.l_version)


        self.verticalLayout_11.addLayout(self.lo_DestHeader)

        self.lo_destPath = QHBoxLayout()
        self.lo_destPath.setObjectName(u"lo_destPath")
        self.b_destPathUp = QPushButton(self.w_destination)
        self.b_destPathUp.setObjectName(u"b_destPathUp")

        self.lo_destPath.addWidget(self.b_destPathUp)

        self.l_destPath = QLineEdit(self.w_destination)
        self.l_destPath.setObjectName(u"l_destPath")

        self.lo_destPath.addWidget(self.l_destPath)

        self.b_browseDest = QPushButton(self.w_destination)
        self.b_browseDest.setObjectName(u"b_browseDest")

        self.lo_destPath.addWidget(self.b_browseDest)


        self.verticalLayout_11.addLayout(self.lo_destPath)

        self.tw_destination = QTableWidget(self.w_destination)
        self.tw_destination.setObjectName(u"tw_destination")
        self.tw_destination.setMaximumSize(QSize(16777215, 9999))
        self.tw_destination.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tw_destination.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.verticalLayout_11.addWidget(self.tw_destination)

        self.lo_destFooter = QHBoxLayout()
        self.lo_destFooter.setObjectName(u"lo_destFooter")
        self.b_dest_checkAll = QPushButton(self.w_destination)
        self.b_dest_checkAll.setObjectName(u"b_dest_checkAll")

        self.lo_destFooter.addWidget(self.b_dest_checkAll)

        self.b_dest_uncheckAll = QPushButton(self.w_destination)
        self.b_dest_uncheckAll.setObjectName(u"b_dest_uncheckAll")

        self.lo_destFooter.addWidget(self.b_dest_uncheckAll)

        self.b_clearList = QPushButton(self.w_destination)
        self.b_clearList.setObjectName(u"b_clearList")

        self.lo_destFooter.addWidget(self.b_clearList)


        self.verticalLayout_11.addLayout(self.lo_destFooter)

        self.splitter.addWidget(self.w_destination)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceBrowser)

        QMetaObject.connectSlotsByName(w_sourceBrowser)
    # setupUi

    def retranslateUi(self, w_sourceBrowser):
        w_sourceBrowser.setWindowTitle(QCoreApplication.translate("w_sourceBrowser", u"Media Browser", None))
        self.l_identifier.setText(QCoreApplication.translate("w_sourceBrowser", u"Source", None))
        self.b_sourcePathUp.setText("")
        self.b_browseSource.setText("")
        self.b_source_checkAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Select All", None))
        self.b_source_uncheckAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Unselect All", None))
        self.b_source_addSel.setText(QCoreApplication.translate("w_sourceBrowser", u"Add Selected", None))
        self.l_version.setText(QCoreApplication.translate("w_sourceBrowser", u"Destination", None))
        self.b_destPathUp.setText("")
        self.b_browseDest.setText("")
        self.b_dest_checkAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Select All", None))
        self.b_dest_uncheckAll.setText(QCoreApplication.translate("w_sourceBrowser", u"Unselect All", None))
        self.b_clearList.setText(QCoreApplication.translate("w_sourceBrowser", u"Clear List", None))
    # retranslateUi

