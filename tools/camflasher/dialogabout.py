# Form implementation generated from reading ui file 'dialogabout.ui'
#
# Created by: PyQt6 UI code generator 6.2.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_DialogAbout(object):
    def setupUi(self, DialogAbout):
        DialogAbout.setObjectName("DialogAbout")
        DialogAbout.resize(276, 112)
        self.gridLayout = QtWidgets.QGridLayout(DialogAbout)
        self.gridLayout.setObjectName("gridLayout")
        self.text = QtWidgets.QLabel(DialogAbout)
        self.text.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.text.setOpenExternalLinks(False)
        self.text.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByKeyboard|QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.text.setObjectName("text")
        self.gridLayout.addWidget(self.text, 0, 0, 1, 1)

        self.retranslateUi(DialogAbout)
        QtCore.QMetaObject.connectSlotsByName(DialogAbout)

    def retranslateUi(self, DialogAbout):
        _translate = QtCore.QCoreApplication.translate
        DialogAbout.setWindowTitle(_translate("DialogAbout", "About camflasher"))
        self.text.setText(_translate("DialogAbout", "<html><head/><body><p align=\"justify\">Camflasher used to flash the pycameresp</p><p align=\"justify\"> firmware and interact with esp32 device. </p><p align=\"justify\">See git here : <a href=\"https://github.com/remibert/pycameresp\"><span style=\" text-decoration: underline; color:#0000ff;\">Pycameresp project</span></a><br/></p></body></html>"))
