# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SourceFunctions.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGroupBox, QHBoxLayout,
    QLabel, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)

class Ui_w_sourceFunctions(object):
    def setupUi(self, w_sourceFunctions):
        if not w_sourceFunctions.objectName():
            w_sourceFunctions.setObjectName(u"w_sourceFunctions")
        w_sourceFunctions.resize(617, 480)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(w_sourceFunctions.sizePolicy().hasHeightForWidth())
        w_sourceFunctions.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(w_sourceFunctions)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.splitter = QSplitter(w_sourceFunctions)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.w_functions = QWidget(self.splitter)
        self.w_functions.setObjectName(u"w_functions")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        self.lo_ovr_proxy = QHBoxLayout()
        self.lo_ovr_proxy.setObjectName(u"lo_ovr_proxy")
        self.chb_ovr_proxy = QCheckBox(self.gb_functions)
        self.chb_ovr_proxy.setObjectName(u"chb_ovr_proxy")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.chb_ovr_proxy.sizePolicy().hasHeightForWidth())
        self.chb_ovr_proxy.setSizePolicy(sizePolicy2)
        self.chb_ovr_proxy.setMinimumSize(QSize(100, 0))
        self.chb_ovr_proxy.setMaximumSize(QSize(100, 16777215))

        self.lo_ovr_proxy.addWidget(self.chb_ovr_proxy)

        self.l_proxyMode = QLabel(self.gb_functions)
        self.l_proxyMode.setObjectName(u"l_proxyMode")

        self.lo_ovr_proxy.addWidget(self.l_proxyMode)

        self.b_ovr_config_proxy = QPushButton(self.gb_functions)
        self.b_ovr_config_proxy.setObjectName(u"b_ovr_config_proxy")
        sizePolicy2.setHeightForWidth(self.b_ovr_config_proxy.sizePolicy().hasHeightForWidth())
        self.b_ovr_config_proxy.setSizePolicy(sizePolicy2)
        self.b_ovr_config_proxy.setMinimumSize(QSize(30, 0))
        self.b_ovr_config_proxy.setMaximumSize(QSize(30, 16777215))

        self.lo_ovr_proxy.addWidget(self.b_ovr_config_proxy)


        self.gb_lo_functions.addLayout(self.lo_ovr_proxy)

        self.lo_ovr_fileNaming = QHBoxLayout()
        self.lo_ovr_fileNaming.setObjectName(u"lo_ovr_fileNaming")
        self.chb_ovr_fileNaming = QCheckBox(self.gb_functions)
        self.chb_ovr_fileNaming.setObjectName(u"chb_ovr_fileNaming")
        sizePolicy2.setHeightForWidth(self.chb_ovr_fileNaming.sizePolicy().hasHeightForWidth())
        self.chb_ovr_fileNaming.setSizePolicy(sizePolicy2)
        self.chb_ovr_fileNaming.setMinimumSize(QSize(100, 0))
        self.chb_ovr_fileNaming.setMaximumSize(QSize(100, 16777215))

        self.lo_ovr_fileNaming.addWidget(self.chb_ovr_fileNaming)

        self.l_enabledNameMods = QLabel(self.gb_functions)
        self.l_enabledNameMods.setObjectName(u"l_enabledNameMods")

        self.lo_ovr_fileNaming.addWidget(self.l_enabledNameMods)

        self.b_ovr_config_fileNaming = QPushButton(self.gb_functions)
        self.b_ovr_config_fileNaming.setObjectName(u"b_ovr_config_fileNaming")
        sizePolicy2.setHeightForWidth(self.b_ovr_config_fileNaming.sizePolicy().hasHeightForWidth())
        self.b_ovr_config_fileNaming.setSizePolicy(sizePolicy2)
        self.b_ovr_config_fileNaming.setMinimumSize(QSize(30, 0))
        self.b_ovr_config_fileNaming.setMaximumSize(QSize(30, 16777215))

        self.lo_ovr_fileNaming.addWidget(self.b_ovr_config_fileNaming)


        self.gb_lo_functions.addLayout(self.lo_ovr_fileNaming)

        self.lo_ovr_metadata = QHBoxLayout()
        self.lo_ovr_metadata.setObjectName(u"lo_ovr_metadata")
        self.chb_ovr_metadata = QCheckBox(self.gb_functions)
        self.chb_ovr_metadata.setObjectName(u"chb_ovr_metadata")
        sizePolicy2.setHeightForWidth(self.chb_ovr_metadata.sizePolicy().hasHeightForWidth())
        self.chb_ovr_metadata.setSizePolicy(sizePolicy2)
        self.chb_ovr_metadata.setMinimumSize(QSize(100, 0))
        self.chb_ovr_metadata.setMaximumSize(QSize(100, 16777215))

        self.lo_ovr_metadata.addWidget(self.chb_ovr_metadata)

        self.l_enabledMetaData = QLabel(self.gb_functions)
        self.l_enabledMetaData.setObjectName(u"l_enabledMetaData")

        self.lo_ovr_metadata.addWidget(self.l_enabledMetaData)

        self.b_ovr_config_metadata = QPushButton(self.gb_functions)
        self.b_ovr_config_metadata.setObjectName(u"b_ovr_config_metadata")
        sizePolicy2.setHeightForWidth(self.b_ovr_config_metadata.sizePolicy().hasHeightForWidth())
        self.b_ovr_config_metadata.setSizePolicy(sizePolicy2)
        self.b_ovr_config_metadata.setMinimumSize(QSize(30, 0))
        self.b_ovr_config_metadata.setMaximumSize(QSize(30, 16777215))

        self.lo_ovr_metadata.addWidget(self.b_ovr_config_metadata)


        self.gb_lo_functions.addLayout(self.lo_ovr_metadata)

        self.verticalSpacer = QSpacerItem(50, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gb_lo_functions.addItem(self.verticalSpacer)

        self.lo_options = QHBoxLayout()
        self.lo_options.setObjectName(u"lo_options")
        self.chb_overwrite = QCheckBox(self.gb_functions)
        self.chb_overwrite.setObjectName(u"chb_overwrite")

        self.lo_options.addWidget(self.chb_overwrite)


        self.gb_lo_functions.addLayout(self.lo_options)


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

        self.b_openDestDir = QPushButton(self.w_functions)
        self.b_openDestDir.setObjectName(u"b_openDestDir")

        self.lo_transferButtons.addWidget(self.b_openDestDir)


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

        self.horizontalSpacer = QSpacerItem(40, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

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
        self.chb_ovr_fileNaming.toggled.connect(self.b_ovr_config_fileNaming.setEnabled)
        self.chb_ovr_proxy.toggled.connect(self.b_ovr_config_proxy.setEnabled)
        self.chb_ovr_metadata.toggled.connect(self.b_ovr_config_metadata.setEnabled)

        QMetaObject.connectSlotsByName(w_sourceFunctions)
    # setupUi

    def retranslateUi(self, w_sourceFunctions):
        w_sourceFunctions.setWindowTitle(QCoreApplication.translate("w_sourceFunctions", u"Media Browser", None))
        self.gb_functions.setTitle("")
        self.chb_ovr_proxy.setText(QCoreApplication.translate("w_sourceFunctions", u"Proxy:", None))
        self.l_proxyMode.setText("")
        self.b_ovr_config_proxy.setText("")
        self.chb_ovr_fileNaming.setText(QCoreApplication.translate("w_sourceFunctions", u"File Naming:", None))
        self.l_enabledNameMods.setText("")
        self.b_ovr_config_fileNaming.setText("")
        self.chb_ovr_metadata.setText(QCoreApplication.translate("w_sourceFunctions", u"MetatData:", None))
        self.l_enabledMetaData.setText("")
        self.b_ovr_config_metadata.setText("")
        self.chb_overwrite.setText(QCoreApplication.translate("w_sourceFunctions", u"Allow Overwrite", None))
        self.b_transfer_start.setText(QCoreApplication.translate("w_sourceFunctions", u"Start Transfer", None))
        self.b_transfer_pause.setText(QCoreApplication.translate("w_sourceFunctions", u"Pause Transfer", None))
        self.b_transfer_resume.setText(QCoreApplication.translate("w_sourceFunctions", u"Resume Transfer", None))
        self.b_transfer_cancel.setText(QCoreApplication.translate("w_sourceFunctions", u"Cancel Transfer", None))
        self.b_transfer_reset.setText(QCoreApplication.translate("w_sourceFunctions", u"Reset", None))
        self.b_openDestDir.setText(QCoreApplication.translate("w_sourceFunctions", u"Open Destination Directory", None))
        self.l_time_elapsed.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_time_elapsedText.setText(QCoreApplication.translate("w_sourceFunctions", u"(elapsed)", None))
        self.l_time_remain.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_time_remainText.setText(QCoreApplication.translate("w_sourceFunctions", u"(remaining)", None))
        self.l_size_copied.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
        self.l_size_dash.setText(QCoreApplication.translate("w_sourceFunctions", u"-", None))
        self.l_size_total.setText(QCoreApplication.translate("w_sourceFunctions", u"--", None))
    # retranslateUi

