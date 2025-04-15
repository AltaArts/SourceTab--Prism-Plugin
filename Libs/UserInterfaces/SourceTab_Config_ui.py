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

class Ui_w_sourceConfig(object):
    def setupUi(self, w_sourceConfig):
        if not w_sourceConfig.objectName():
            w_sourceConfig.setObjectName(u"w_sourceConfig")
        w_sourceConfig.resize(608, 650)
        self.horizontalLayout = QHBoxLayout(w_sourceConfig)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceConfig)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.w_config = QWidget(self.splitter)
        self.w_config.setObjectName(u"w_config")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(8)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.w_config.sizePolicy().hasHeightForWidth())
        self.w_config.setSizePolicy(sizePolicy)
        self.verticalLayout_8 = QVBoxLayout(self.w_config)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.lo_thumbThreads = QHBoxLayout()
        self.lo_thumbThreads.setObjectName(u"lo_thumbThreads")
        self.l_thumbThreads = QLabel(self.w_config)
        self.l_thumbThreads.setObjectName(u"l_thumbThreads")

        self.lo_thumbThreads.addWidget(self.l_thumbThreads)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_thumbThreads.addItem(self.horizontalSpacer)

        self.sb_thumbThreads = QSpinBox(self.w_config)
        self.sb_thumbThreads.setObjectName(u"sb_thumbThreads")
        self.sb_thumbThreads.setMinimum(1)

        self.lo_thumbThreads.addWidget(self.sb_thumbThreads)


        self.verticalLayout_8.addLayout(self.lo_thumbThreads)

        self.lo_copyThreads = QHBoxLayout()
        self.lo_copyThreads.setObjectName(u"lo_copyThreads")
        self.l_copyThreads = QLabel(self.w_config)
        self.l_copyThreads.setObjectName(u"l_copyThreads")

        self.lo_copyThreads.addWidget(self.l_copyThreads)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_copyThreads.addItem(self.horizontalSpacer_2)

        self.sb_copyThreads = QSpinBox(self.w_config)
        self.sb_copyThreads.setObjectName(u"sb_copyThreads")
        self.sb_copyThreads.setMinimum(1)

        self.lo_copyThreads.addWidget(self.sb_copyThreads)


        self.verticalLayout_8.addLayout(self.lo_copyThreads)

        self.lo_copyChunks = QHBoxLayout()
        self.lo_copyChunks.setObjectName(u"lo_copyChunks")
        self.l_copyChunks = QLabel(self.w_config)
        self.l_copyChunks.setObjectName(u"l_copyChunks")

        self.lo_copyChunks.addWidget(self.l_copyChunks)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_copyChunks.addItem(self.horizontalSpacer_8)

        self.sb_copyChunks = QSpinBox(self.w_config)
        self.sb_copyChunks.setObjectName(u"sb_copyChunks")
        self.sb_copyChunks.setMinimum(1)

        self.lo_copyChunks.addWidget(self.sb_copyChunks)


        self.verticalLayout_8.addLayout(self.lo_copyChunks)

        self.lo_progUpdateRate = QHBoxLayout()
        self.lo_progUpdateRate.setObjectName(u"lo_progUpdateRate")
        self.l_progUpdateRate = QLabel(self.w_config)
        self.l_progUpdateRate.setObjectName(u"l_progUpdateRate")

        self.lo_progUpdateRate.addWidget(self.l_progUpdateRate)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.lo_progUpdateRate.addItem(self.horizontalSpacer_3)

        self.sp_progUpdateRate = QDoubleSpinBox(self.w_config)
        self.sp_progUpdateRate.setObjectName(u"sp_progUpdateRate")
        self.sp_progUpdateRate.setDecimals(1)
        self.sp_progUpdateRate.setMinimum(0.100000000000000)
        self.sp_progUpdateRate.setSingleStep(0.100000000000000)
        self.sp_progUpdateRate.setValue(0.500000000000000)

        self.lo_progUpdateRate.addWidget(self.sp_progUpdateRate)


        self.verticalLayout_8.addLayout(self.lo_progUpdateRate)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer)

        self.bb_saveCancel = QDialogButtonBox(self.w_config)
        self.bb_saveCancel.setObjectName(u"bb_saveCancel")
        self.bb_saveCancel.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)

        self.verticalLayout_8.addWidget(self.bb_saveCancel)

        self.splitter.addWidget(self.w_config)

        self.horizontalLayout.addWidget(self.splitter)


        self.retranslateUi(w_sourceConfig)

        QMetaObject.connectSlotsByName(w_sourceConfig)
    # setupUi

    def retranslateUi(self, w_sourceConfig):
        w_sourceConfig.setWindowTitle(QCoreApplication.translate("w_sourceConfig", u"Transfer Configuration", None))
        self.l_thumbThreads.setText(QCoreApplication.translate("w_sourceConfig", u"Maximum Thumbnail Threads", None))
        self.l_copyThreads.setText(QCoreApplication.translate("w_sourceConfig", u"Maximum Transfer Threads", None))
        self.l_copyChunks.setText(QCoreApplication.translate("w_sourceConfig", u"Transfer Chunk Size (megabytes)", None))
        self.l_progUpdateRate.setText(QCoreApplication.translate("w_sourceConfig", u"Progress Bars Update Rate (seconds)", None))
    # retranslateUi

