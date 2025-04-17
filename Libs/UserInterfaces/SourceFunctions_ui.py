# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SourceFunctions.ui'
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
        w_sourceFunctions.resize(460, 480)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(w_sourceFunctions.sizePolicy().hasHeightForWidth())
        w_sourceFunctions.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(w_sourceFunctions)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceFunctions)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.w_functions = QWidget(self.splitter)
        self.w_functions.setObjectName(u"w_functions")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(8)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.w_functions.sizePolicy().hasHeightForWidth())
        self.w_functions.setSizePolicy(sizePolicy1)
        self.verticalLayout_8 = QVBoxLayout(self.w_functions)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.gb_functions = QGroupBox(self.w_functions)
        self.gb_functions.setObjectName(u"gb_functions")
        self.gb_functions.setEnabled(True)
        self.gb_lo_functions = QVBoxLayout(self.gb_functions)
        self.gb_lo_functions.setObjectName(u"gb_lo_functions")
        self.b_configure = QPushButton(self.gb_functions)
        self.b_configure.setObjectName(u"b_configure")

        self.gb_lo_functions.addWidget(self.b_configure)

        self.verticalSpacer = QSpacerItem(20, 50, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding)

        self.gb_lo_functions.addItem(self.verticalSpacer)

        self.chb_copyProxy = QCheckBox(self.gb_functions)
        self.chb_copyProxy.setObjectName(u"chb_copyProxy")

        self.gb_lo_functions.addWidget(self.chb_copyProxy)


        self.verticalLayout_8.addWidget(self.gb_functions)

        self.lo_transferButtons = QHBoxLayout()
        self.lo_transferButtons.setObjectName(u"lo_transferButtons")
        self.b_transfer_start = QPushButton(self.w_functions)
        self.b_transfer_start.setObjectName(u"b_transfer_start")

        self.lo_transferButtons.addWidget(self.b_transfer_start)

        self.b_transfer_pause = QPushButton(self.w_functions)
        self.b_transfer_pause.setObjectName(u"b_transfer_pause")

        self.lo_transferButtons.addWidget(self.b_transfer_pause)

        self.b_transfer_resume = QPushButton(self.w_functions)
        self.b_transfer_resume.setObjectName(u"b_transfer_resume")

        self.lo_transferButtons.addWidget(self.b_transfer_resume)

        self.b_transfer_cancel = QPushButton(self.w_functions)
        self.b_transfer_cancel.setObjectName(u"b_transfer_cancel")

        self.lo_transferButtons.addWidget(self.b_transfer_cancel)

        self.b_transfer_reset = QPushButton(self.w_functions)
        self.b_transfer_reset.setObjectName(u"b_transfer_reset")

        self.lo_transferButtons.addWidget(self.b_transfer_reset)


        self.verticalLayout_8.addLayout(self.lo_transferButtons)

        self.lo_progBar_total = QHBoxLayout()
        self.lo_progBar_total.setObjectName(u"lo_progBar_total")
        self.progBar_total = QProgressBar(self.w_functions)
        self.progBar_total.setObjectName(u"progBar_total")
        self.progBar_total.setMaximumSize(QSize(16777215, 10))
        self.progBar_total.setValue(24)
        self.progBar_total.setTextVisible(False)

        self.lo_progBar_total.addWidget(self.progBar_total)


        self.verticalLayout_8.addLayout(self.lo_progBar_total)

        self.lo_transferStats = QHBoxLayout()
        self.lo_transferStats.setObjectName(u"lo_transferStats")
        self.l_time_elapsed = QLabel(self.w_functions)
        self.l_time_elapsed.setObjectName(u"l_time_elapsed")

        self.lo_transferStats.addWidget(self.l_time_elapsed)

        self.l_time_elapsedText = QLabel(self.w_functions)
        self.l_time_elapsedText.setObjectName(u"l_time_elapsedText")

        self.lo_transferStats.addWidget(self.l_time_elapsedText)

        self.l_time_remain = QLabel(self.w_functions)
        self.l_time_remain.setObjectName(u"l_time_remain")

        self.lo_transferStats.addWidget(self.l_time_remain)

        self.l_time_remainText = QLabel(self.w_functions)
        self.l_time_remainText.setObjectName(u"l_time_remainText")

        self.lo_transferStats.addWidget(self.l_time_remainText)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_transferStats.addItem(self.horizontalSpacer)

        self.l_size_copied = QLabel(self.w_functions)
        self.l_size_copied.setObjectName(u"l_size_copied")

        self.lo_transferStats.addWidget(self.l_size_copied)

        self.l_size_dash = QLabel(self.w_functions)
        self.l_size_dash.setObjectName(u"l_size_dash")

        self.lo_transferStats.addWidget(self.l_size_dash)

        self.l_size_total = QLabel(self.w_functions)
        self.l_size_total.setObjectName(u"l_size_total")

        self.lo_transferStats.addWidget(self.l_size_total)


        self.verticalLayout_8.addLayout(self.lo_transferStats)

        self.splitter.addWidget(self.w_functions)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceFunctions)

        QMetaObject.connectSlotsByName(w_sourceFunctions)
    # setupUi

    def retranslateUi(self, w_sourceFunctions):
        w_sourceFunctions.setWindowTitle(QCoreApplication.translate("w_sourceFunctions", u"Media Browser", None))
        self.gb_functions.setTitle("")
        self.b_configure.setText(QCoreApplication.translate("w_sourceFunctions", u"Configure", None))
        self.chb_copyProxy.setText(QCoreApplication.translate("w_sourceFunctions", u"Copy Proxy", None))
        self.b_transfer_start.setText(QCoreApplication.translate("w_sourceFunctions", u"Start Transfer", None))
        self.b_transfer_pause.setText(QCoreApplication.translate("w_sourceFunctions", u"Pause Transfer", None))
        self.b_transfer_resume.setText(QCoreApplication.translate("w_sourceFunctions", u"Resume Transfer", None))
        self.b_transfer_cancel.setText(QCoreApplication.translate("w_sourceFunctions", u"Cancel Transfer", None))
        self.b_transfer_reset.setText(QCoreApplication.translate("w_sourceFunctions", u"Reset", None))
        self.l_time_elapsed.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_time_elapsedText.setText(QCoreApplication.translate("w_sourceFunctions", u"(elapsed)", None))
        self.l_time_remain.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_time_remainText.setText(QCoreApplication.translate("w_sourceFunctions", u"(remaining)", None))
        self.l_size_copied.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_size_dash.setText(QCoreApplication.translate("w_sourceFunctions", u"-", None))
        self.l_size_total.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
    # retranslateUi

