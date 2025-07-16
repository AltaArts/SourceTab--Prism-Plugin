# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MetadataEditor.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QSplitter, QVBoxLayout, QWidget)

class Ui_w_metadataEditor(object):
    def setupUi(self, w_metadataEditor):
        if not w_metadataEditor.objectName():
            w_metadataEditor.setObjectName(u"w_metadataEditor")
        w_metadataEditor.resize(1000, 900)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
        self.b_PLACEHOLDER = QPushButton(w_metadataEditor)
        self.b_PLACEHOLDER.setObjectName(u"b_PLACEHOLDER")

        self.lo_top.addWidget(self.b_PLACEHOLDER)


        self.lo_main.addLayout(self.lo_top)

        self.splitter = QSplitter(w_metadataEditor)
        self.splitter.setObjectName(u"splitter")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy1)
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.w_target = QWidget(self.splitter)
        self.w_target.setObjectName(u"w_target")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(8)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.w_target.sizePolicy().hasHeightForWidth())
        self.w_target.setSizePolicy(sizePolicy2)
        self.verticalLayout_8 = QVBoxLayout(self.w_target)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lw_target = QListWidget(self.w_target)
        self.lw_target.setObjectName(u"lw_target")
        self.lw_target.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.lw_target.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.verticalLayout_8.addWidget(self.lw_target)

        self.splitter.addWidget(self.w_target)
        self.w_source = QWidget(self.splitter)
        self.w_source.setObjectName(u"w_source")
        sizePolicy2.setHeightForWidth(self.w_source.sizePolicy().hasHeightForWidth())
        self.w_source.setSizePolicy(sizePolicy2)
        self.verticalLayout_11 = QVBoxLayout(self.w_source)
        self.verticalLayout_11.setSpacing(0)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.lw_source = QListWidget(self.w_source)
        self.lw_source.setObjectName(u"lw_source")
        self.lw_source.setMaximumSize(QSize(16777215, 16777215))
        self.lw_source.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.lw_source.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.verticalLayout_11.addWidget(self.lw_source)

        self.splitter.addWidget(self.w_source)
        self.verticalWidget = QWidget(self.splitter)
        self.verticalWidget.setObjectName(u"verticalWidget")
        sizePolicy1.setHeightForWidth(self.verticalWidget.sizePolicy().hasHeightForWidth())
        self.verticalWidget.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.verticalWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.listWidget = QListWidget(self.verticalWidget)
        self.listWidget.setObjectName(u"listWidget")

        self.verticalLayout.addWidget(self.listWidget)

        self.splitter.addWidget(self.verticalWidget)

        self.lo_main.addWidget(self.splitter)

        self.lo_bottom = QHBoxLayout()
        self.lo_bottom.setObjectName(u"lo_bottom")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

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
        self.b_PLACEHOLDER.setText(QCoreApplication.translate("w_metadataEditor", u"PushButton", None))
        self.b_save.setText(QCoreApplication.translate("w_metadataEditor", u"SAVE", None))
        self.b_close.setText(QCoreApplication.translate("w_metadataEditor", u"CLOSE", None))
    # retranslateUi

