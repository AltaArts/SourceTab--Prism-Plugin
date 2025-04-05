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

class Ui_w_sourceFunctions(object):
    def setupUi(self, w_sourceFunctions):
        if not w_sourceFunctions.objectName():
            w_sourceFunctions.setObjectName(u"w_sourceFunctions")
        w_sourceFunctions.resize(417, 399)
        self.horizontalLayout = QHBoxLayout(w_sourceFunctions)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceFunctions)
        self.splitter.setObjectName(u"splitter")
        self.w_functions = QWidget(self.splitter)
        self.w_functions.setObjectName(u"w_functions")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_functions.sizePolicy().hasHeightForWidth())
        self.w_functions.setSizePolicy(sizePolicy)
        self.verticalLayout_8 = QVBoxLayout(self.w_functions)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer)

        self.chb_copyProxy = QCheckBox(self.w_functions)
        self.chb_copyProxy.setObjectName(u"chb_copyProxy")

        self.verticalLayout_8.addWidget(self.chb_copyProxy)

        self.b_startTransfer = QPushButton(self.w_functions)
        self.b_startTransfer.setObjectName(u"b_startTransfer")

        self.verticalLayout_8.addWidget(self.b_startTransfer)

        self.progBar_total = QProgressBar(self.w_functions)
        self.progBar_total.setObjectName(u"progBar_total")
        self.progBar_total.setMaximumSize(QSize(16777215, 10))
        self.progBar_total.setValue(24)
        self.progBar_total.setTextVisible(False)

        self.verticalLayout_8.addWidget(self.progBar_total)

        self.splitter.addWidget(self.w_functions)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceFunctions)

        QMetaObject.connectSlotsByName(w_sourceFunctions)
    # setupUi

    def retranslateUi(self, w_sourceFunctions):
        w_sourceFunctions.setWindowTitle(QCoreApplication.translate("w_sourceFunctions", u"Media Browser", None))
        self.chb_copyProxy.setText(QCoreApplication.translate("w_sourceFunctions", u"Copy Proxy", None))
        self.b_startTransfer.setText(QCoreApplication.translate("w_sourceFunctions", u"Start Transfer", None))
    # retranslateUi

