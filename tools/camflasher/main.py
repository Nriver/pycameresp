#!/usr/bin/python3
""" Tools to flash the firmware of pycameresp """
# Requirements :
#	- pip3 install serial
#	- pip3 install pyinstaller
#	- pip3 install esptool
#	- pip3 install pyserial
# For windows seven
#	- pip3 install pyqt5
# For windows 10, 11, linux, osx
#	- pip3 install pyqt6
#
# pylint:disable=no-name-in-module
import sys
import os.path
import os
from platform import uname
try:
	from PyQt6 import uic
	from PyQt6.QtCore import QTimer, QEvent, Qt, QSettings
	from PyQt6.QtWidgets import QFileDialog, QColorDialog, QMainWindow, QDialog, QMenu, QApplication, QMessageBox, QErrorMessage
	from PyQt6.QtGui import QCursor,QAction,QFont,QColor
except:
	from PyQt5 import uic
	from PyQt5.QtCore import QTimer, QEvent, Qt, QSettings
	from PyQt5.QtWidgets import QFileDialog, QColorDialog, QMainWindow, QDialog, QMenu, QApplication, QMessageBox, QErrorMessage, QAction
	from PyQt5.QtGui import QCursor, QFont,QColor
from serial.tools import list_ports
from flasher import Flasher
from qstdoutvt100 import QStdoutVT100

# Settings
SETTINGS_FILENAME  = "CamFlasher.ini"
FONT_FAMILY        = "camflasher.font.family"
FONT_SIZE          = "camflasher.font.size"
WORKING_DIRECTORY  = "camflasher.working_directory"
WIN_GEOMETRY       = "camflasher.window.geometry"
FIRMWARE_FILENAME  = "camflasher.firmware.filename"
DEVICE_RTS_DTR     = "camflasher.device.rts_dtr"
TEXT_BACKCOLOR     = "camflasher.text.backcolor"
TEXT_FORECOLOR     = "camflasher.text.forecolor"
CURSOR_BACKCOLOR   = "camflasher.cursor.backcolor"
CURSOR_FORECOLOR   = "camflasher.cursor.textcolor"
REVERSE_BACKCOLOR  = "camflasher.reverse.backcolor"
REVERSE_FORECOLOR  = "camflasher.reverse.textcolor"

DEFAULT_TEXT_BACKCOLOR    = QColor(255,255,255)
DEFAULT_TEXT_FORECOLOR    = QColor(0,0,0)
DEFAULT_CURSOR_BACKCOLOR  = QColor(0xAA,0xAA,0XAA)
DEFAULT_CURSOR_FORECOLOR  = QColor(0,0,0)
DEFAULT_REVERSE_BACKCOLOR = QColor(0,0,0)
DEFAULT_REVERSE_FORECOLOR = QColor(255,255,255)

OUTPUT_TEXT = """
<html>
	<head/>
	<body style="background-color : %(text_backcolor)s">
		<p style="color : %(text_forecolor)s" >	
			def function(self):<br>
			&nbsp;&nbsp;&nbsp;&nbsp;for j in range(10):<br>
			&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;print(j)<br>
			&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="background-color : %(cursor_backcolor)s;color : %(cursor_forecolor)s">#</span> &lt;- Cursor <br>
			&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="background-color : %(reverse_backcolor)s;color : %(reverse_forecolor)s"># Text in reverse video</span>
		</p>
	</body>
</html>"""

class AboutDialog(QDialog):
	""" Dialog about """
	def __init__(self, parent):
		""" Dialog box constructor """
		QDialog.__init__(self, parent)
		try:
			self.dialog = uic.loadUi('dialogabout.ui', self)
		except Exception as err:
			from dialogabout import Ui_DialogAbout
			self.dialog = Ui_DialogAbout()
			self.dialog.setupUi(self)
		self.setModal(True)

	def accept(self):
		""" Accept about dialog """
		self.close()

def get_settings():
	""" Return the QSettings class according to the os """
	if sys.platform == "darwin":
		result = QSettings()
	elif sys.platform == "win32":
		if uname() == "7":
			result = QSettings(SETTINGS_FILENAME, QSettings.IniFormat)
		else:
			result = QSettings(SETTINGS_FILENAME)
	else:
		result = QSettings()
	return result

class FlashDialog(QDialog):
	""" Dialog box to select firmware """
	def __init__(self, parent):
		""" Dialog box constructor """
		QDialog.__init__(self, parent)
		try:
			self.dialog = uic.loadUi('dialogflash.ui', self)
		except Exception as err:
			from dialogflash import Ui_DialogFlash
			self.dialog = Ui_DialogFlash()
			self.dialog.setupUi(self)
		settings = get_settings()
		firmware = settings.value(FIRMWARE_FILENAME, "")
		if not os.path.exists(firmware):
			firmware = ""
		self.dialog.firmware.setText(firmware)
		self.dialog.select_firmware.clicked.connect(self.on_firmware_clicked)
		self.dialog.baud.addItems(["9600","57600","74880","115200","230400","460800"])
		self.dialog.baud.setCurrentIndex(5)
		self.setModal(True)

	def accept(self):
		""" Called when ok pressed """
		if os.path.exists(self.dialog.firmware.text()) is False:
			msg = QMessageBox()
			w = self.geometry().width()
			h = self.geometry().height()
			x = self.geometry().x()
			y = self.geometry().y()
			msg.setGeometry(x + w//3,y + h//3,w,h)
			msg.setIcon(QMessageBox.Icon.Critical)
			msg.setText("Firmware not found")
			msg.exec()
		else:
			settings = get_settings()
			settings.setValue(FIRMWARE_FILENAME, self.dialog.firmware.text())
			super().accept()

	def on_firmware_clicked(self, event):
		""" Selection of firmware button clicked """
		firmware = QFileDialog.getOpenFileName(self, 'Select firmware file', '',"Firmware files (*.bin)")
		if firmware != ('', ''):
			self.dialog.firmware.setText(firmware[0])

class OptionDialog(QDialog):
	""" Dialog for options """
	def __init__(self, parent):
		""" Dialog box constructor """
		QDialog.__init__(self, parent)
		try:
			self.dialog = uic.loadUi('dialogoption.ui', self)
		except Exception as err:
			from dialogoption import Ui_DialogOption
			self.dialog = Ui_DialogOption()
			self.dialog.setupUi(self)

		settings = get_settings()
		self.dialog.working_directory.setText(settings.value(WORKING_DIRECTORY,"."))

		self.dialog.spin_font_size.setValue(int(settings.value(FONT_SIZE   ,12)))
		self.dialog.combo_font.setCurrentFont(QFont(settings.value(FONT_FAMILY ,"Courier")))
		self.text_backcolor    = settings.value(TEXT_BACKCOLOR   ,DEFAULT_TEXT_BACKCOLOR)
		self.text_forecolor    = settings.value(TEXT_FORECOLOR   ,DEFAULT_TEXT_FORECOLOR)
		self.cursor_backcolor  = settings.value(CURSOR_BACKCOLOR ,DEFAULT_CURSOR_BACKCOLOR)
		self.cursor_forecolor  = settings.value(CURSOR_FORECOLOR ,DEFAULT_CURSOR_FORECOLOR)
		self.reverse_backcolor = settings.value(REVERSE_BACKCOLOR,DEFAULT_REVERSE_BACKCOLOR)
		self.reverse_forecolor = settings.value(REVERSE_FORECOLOR,DEFAULT_REVERSE_FORECOLOR)

		self.dialog.select_directory.clicked.connect(self.on_directory_clicked)
		self.dialog.button_forecolor.clicked.connect(self.on_forecolor_clicked)
		self.dialog.button_backcolor.clicked.connect(self.on_backcolor_clicked)
		self.dialog.button_cursor_forecolor.clicked.connect(self.on_cursor_forecolor_clicked)
		self.dialog.button_cursor_backcolor.clicked.connect(self.on_cursor_backcolor_clicked)
		self.dialog.button_reverse_forecolor.clicked.connect(self.on_reverse_forecolor_clicked)
		self.dialog.button_reverse_backcolor.clicked.connect(self.on_reverse_backcolor_clicked)
		self.dialog.reset_color.clicked.connect(self.on_reset_color_clicked)

		self.dialog.combo_font.currentTextChanged.connect(self.on_font_changed)
		self.dialog.spin_font_size.valueChanged.connect(self.on_font_changed)
		self.refresh_output()
		self.setModal(True)

	def refresh_output(self):
		""" Refresh the output """
		font = QFont()
		font.setFamily    (self.dialog.combo_font.currentFont().family())
		font.setPointSize (int(self.dialog.spin_font_size.value()))
		self.dialog.label_output.setFont(font)
		# pylint:disable=possibly-unused-variable
		text_backcolor     = "rgb(%d,%d,%d)"%self.text_backcolor.getRgb()[:3]
		text_forecolor     = "rgb(%d,%d,%d)"%self.text_forecolor.getRgb()[:3]
		cursor_backcolor   = "rgb(%d,%d,%d)"%self.cursor_backcolor.getRgb()[:3]
		cursor_forecolor   = "rgb(%d,%d,%d)"%self.cursor_forecolor.getRgb()[:3]
		reverse_backcolor  = "rgb(%d,%d,%d)"%self.reverse_backcolor.getRgb()[:3]
		reverse_forecolor  = "rgb(%d,%d,%d)"%self.reverse_forecolor.getRgb()[:3]
		self.dialog.label_output.setHtml(OUTPUT_TEXT%locals())

	def on_reset_color_clicked(self):
		""" Reset the default color """
		self.text_backcolor    = DEFAULT_TEXT_BACKCOLOR
		self.text_forecolor    = DEFAULT_TEXT_FORECOLOR
		self.cursor_backcolor  = DEFAULT_CURSOR_BACKCOLOR
		self.cursor_forecolor  = DEFAULT_CURSOR_FORECOLOR
		self.reverse_backcolor = DEFAULT_REVERSE_BACKCOLOR
		self.reverse_forecolor = DEFAULT_REVERSE_FORECOLOR
		self.refresh_output()

	def on_font_changed(self, event):
		""" Font family changed """
		self.refresh_output()

	def on_directory_clicked(self, event):
		""" Selection of directory button clicked """
		settings = get_settings()
		directory = QFileDialog.getExistingDirectory(self, 'Select working directory', directory =settings.value(WORKING_DIRECTORY,"."))
		if directory != '':
			self.dialog.working_directory.setText(directory)

	def on_forecolor_clicked(self, event):
		""" Select the forecolor """
		color = QColorDialog.getColor(parent=self, initial=self.text_forecolor, title="Text color")
		if color.isValid():
			self.text_forecolor = color
			self.refresh_output()

	def on_backcolor_clicked(self, event):
		""" Select the backcolor """
		color = QColorDialog.getColor(parent=self, initial=self.text_backcolor, title="Background color")
		if color.isValid():
			self.text_backcolor = color
			self.refresh_output()

	def on_cursor_forecolor_clicked(self, event):
		""" Select the cursor forecolor """
		color = QColorDialog.getColor(parent=self, initial=self.cursor_forecolor, title="Cursor text color")
		if color.isValid():
			self.cursor_forecolor = color
			self.refresh_output()

	def on_cursor_backcolor_clicked(self, event):
		""" Select the cursor backcolor """
		color = QColorDialog.getColor(parent=self, initial=self.cursor_backcolor, title="Cursor background color")
		if color.isValid():
			self.cursor_backcolor = color
			self.refresh_output()

	def on_reverse_forecolor_clicked(self, event):
		""" Select the reverse forecolor """
		color = QColorDialog.getColor(parent=self, initial=self.reverse_forecolor, title="Reverse text color")
		if color.isValid():
			self.reverse_forecolor = color
			self.refresh_output()

	def on_reverse_backcolor_clicked(self, event):
		""" Select the reverse backcolor """
		color = QColorDialog.getColor(parent=self, initial=self.reverse_backcolor, title="Reverse background color")
		if color.isValid():
			self.reverse_backcolor = color
			self.refresh_output()

	def accept(self):
		""" Accept about dialog """
		font = self.dialog.combo_font.currentFont()
		settings = get_settings()
		settings.setValue(FONT_FAMILY , font.family())
		settings.setValue(FONT_SIZE   , self.dialog.spin_font_size.value())
		settings.setValue(WORKING_DIRECTORY, self.dialog.working_directory.text())
		settings.setValue(TEXT_FORECOLOR   , self.text_forecolor)
		settings.setValue(TEXT_BACKCOLOR   , self.text_backcolor)
		settings.setValue(CURSOR_FORECOLOR , self.cursor_forecolor)
		settings.setValue(CURSOR_BACKCOLOR , self.cursor_backcolor)
		settings.setValue(REVERSE_FORECOLOR, self.reverse_forecolor)
		settings.setValue(REVERSE_BACKCOLOR, self.reverse_backcolor)
		super().accept()

class Ports:
	""" List of all serial ports """
	def __init__(self):
		""" Constructor """
		self.rts_dtr = {}
		self.status = {}
		self.settings = get_settings()
		self.rts_dtr = self.settings.value(DEVICE_RTS_DTR,{})
		for key in self.rts_dtr.keys():
			self.status[key] = False

	def update(self, detected_ports):
		""" Update ports with detected connected port """
		result = False
		connected = []

		# For all ports connected
		for detected_port in sorted(detected_ports):
			# If current port is usb
			if detected_port.hwid != "n/a" and detected_port.vid is not None:
				key = (detected_port.device, detected_port.vid, detected_port.pid)
				if key in self.status:
					connected.append(detected_port.device)
					if self.status[key] is False:
						self.status[key] = True
						result = True
				else:
					# Create new port
					self.status[key] = True
					self.rts_dtr[key] = False
					self.settings.setValue(DEVICE_RTS_DTR,self.rts_dtr)
					connected.append(detected_port.device)
					result = True

		# For all ports already registered
		for key in self.status:
			# For all ports connected
			for detected_port in sorted(detected_ports):
				# If port is yet connected
				if key[0] == detected_port.device and key[1] == detected_port.vid and key[2] == detected_port.pid:
					break
			else:
				# The port is disconnected
				self.status[key] = False
				result = True
		if result is True:
			return connected
		return None

	def get_rts_dtr(self, name):
		""" Get the value of rts dtr for the selected port """
		result = False
		for key in self.rts_dtr:
			if name == key[0]:
				result = self.rts_dtr[key]
				break
		return result

	def set_rts_dtr(self, name, value):
		""" Set the value of rts dtr for the selected port """
		for key in self.rts_dtr:
			if name == key[0]:
				self.rts_dtr[key] = value
				self.settings.setValue(DEVICE_RTS_DTR,self.rts_dtr)
				break

class CamFlasher(QMainWindow):
	""" Tools to flash the firmware of pycameresp """
	def __init__(self):
		""" Main window contructor """
		super(CamFlasher, self).__init__()
		self.stdout = sys.stdout
		try:
			self.window = uic.loadUi('camflasher.ui', self)
			self.geometry_ = self.window
		except Exception as err:
			from camflasher import Ui_CamFlasher
			self.window = Ui_CamFlasher()
			self.window.setupUi(self)
			self.geometry_ = self

		# Select font
		self.update_font()
		settings = get_settings()
		self.geometry_.setGeometry(settings.value(WIN_GEOMETRY, self.geometry_.geometry()))

		self.window.output.setAcceptDrops(False)
		self.window.output.setReadOnly(True)
		self.window.output.installEventFilter(self)

		self.flash_dialog = FlashDialog(self)

		# Start stdout redirection vt100 console
		self.window.output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.window.output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
		self.console = QStdoutVT100(self.window.output)

		# Serial listener thread
		self.flasher = Flasher(self.stdout, settings.value(WORKING_DIRECTORY))
		self.flasher.start()

		# Refresher of the console content
		self.timer_refresh_console = QTimer(active=True, interval=100)
		self.timer_refresh_console.timeout.connect(self.on_refresh_console)
		self.timer_refresh_console.start()

		# Refresher of the list of serial port available
		self.timer_refresh_port = QTimer(active=True, interval=1000)
		self.timer_refresh_port.timeout.connect(self.on_refresh_port)
		self.timer_refresh_port.start()
		self.serial_ports = []

		self.port_selected = None
		self.window.combo_port.currentTextChanged.connect(self.on_port_changed)

		self.show()
		self.resize_console()
		self.window.output.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.window.output.customContextMenuRequested.connect(self.context_menu)

		self.window.action_paste.triggered.connect(self.paste)
		self.window.action_copy.triggered.connect(self.copy)
		self.window.action_resume.setDisabled(True)
		self.window.action_flash.triggered.connect(self.on_flash_clicked)
		self.window.action_about.triggered.connect(self.on_about_clicked)
		self.window.action_option.triggered.connect(self.on_option_clicked)
		self.window.chk_rts_dtr.stateChanged.connect(self.on_rts_dtr_changed)
		self.ports = Ports()
		self.clear_selection = True

	def update_font(self):
		""" Update console font """
		settings = get_settings()
		font = QFont()
		font.setFamily    (settings.value(FONT_FAMILY ,"Courier"))
		font.setPointSize (int(settings.value(FONT_SIZE   ,12)))
		self.window.output.setFont(font)

	def on_about_clicked(self):
		""" About menu clicked """
		about_dialog = AboutDialog(self)
		about_dialog.show()
		about_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
		about_dialog.exec()

	def context_menu(self, pos):
		""" Customization of the context menu """
		context = QMenu(self)

		copy = QAction("Copy", self)
		copy.triggered.connect(self.copy)
		context.addAction(copy)

		paste = QAction("Paste", self)
		paste.triggered.connect(self.paste)
		context.addAction(paste)

		cls = QAction("Cls", self)
		cls.triggered.connect(self.cls)
		context.addAction(cls)
		context.exec(QCursor.pos())

	def cls(self):
		""" Clear screen """
		print("\x1B[2J\x1B[1;1f",end="")

	def copy(self):
		""" Copy to clipboard the text selected """
		text_selected = self.window.output.textCursor().selectedText()
		text_selected = text_selected.replace("\xa0"," ")
		text_selected = text_selected.replace("\u2028","\n")
		QApplication.clipboard().setText(text_selected)

	def paste(self):
		""" Paste to console the content of clipboard """
		paste = QApplication.clipboard().text()
		paste = paste.replace("\n","\r")
		paste = paste.encode("utf-8")
		self.flasher.send_key(paste)

	def eventFilter(self, obj, event):
		""" Treat key pressed on console """
		if event.type() == QEvent.Type.KeyPress:
			key = self.console.convert_key_to_vt100(event)
			if key is not None:
				self.clear_selection = True
				self.flasher.send_key(key)
			return True
		return super(CamFlasher, self).eventFilter(obj, event)

	def resize_console(self):
		""" Resize console """
		# Save the position
		settings = get_settings()
		geometry = self.geometry_.geometry()
		settings.setValue(WIN_GEOMETRY, geometry)
		self.console.set_color(
			settings.value(TEXT_BACKCOLOR,    DEFAULT_TEXT_BACKCOLOR),
			settings.value(TEXT_FORECOLOR,    DEFAULT_TEXT_FORECOLOR),
			settings.value(CURSOR_BACKCOLOR,  DEFAULT_CURSOR_BACKCOLOR),
			settings.value(CURSOR_FORECOLOR,  DEFAULT_CURSOR_FORECOLOR),
			settings.value(REVERSE_BACKCOLOR, DEFAULT_REVERSE_BACKCOLOR),
			settings.value(REVERSE_FORECOLOR, DEFAULT_REVERSE_FORECOLOR))

		# Calculate the dimension in pixels of a text of 200 lines with 200 characters
		line = "W"*200 + "\n"
		line = line*200
		line = line[:-1]
		size = self.window.output.fontMetrics().size(Qt.TextFlag.TextWordWrap,line)

		# Deduce the size of console visible in the window
		width  = (self.window.output.contentsRect().width()  * 200)// size.width() -  1
		height = int((self.window.output.contentsRect().height() * 200)/ size.height() - 0.3)
		self.console.set_size(width, height)

	def moveEvent(self, _):
		""" Treat the window move event"""
		self.resize_console()

	def resizeEvent(self, _):
		""" Treat the window resize event """
		self.resize_console()

	def on_option_clicked(self):
		""" On option menu clicked """
		option_dialog = OptionDialog(self)
		option_dialog.show()
		option_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
		result = option_dialog.exec()
		if result == 1:
			settings = get_settings()
			self.flasher.set_directory(settings.value(WORKING_DIRECTORY,"."))
			self.update_font()
			self.resize_console()

	def on_refresh_port(self):
		""" Refresh the combobox content with the serial ports detected """
		# self.console.test()
		ports_connected = self.ports.update(list_ports.comports())
		if ports_connected is not None:
			for i in range(self.window.combo_port.count()):
				if not self.window.combo_port.itemText(i) in ports_connected:
					self.window.combo_port.removeItem(i)

			for port in ports_connected:
				for i in range(self.window.combo_port.count()):
					if self.window.combo_port.itemText(i) == port:
						break
				else:
					self.window.combo_port.addItem(port)

	def on_rts_dtr_changed(self, event):
		""" On change of DTR/STR check box """
		rts_dtr = self.window.chk_rts_dtr.isChecked()
		self.ports.set_rts_dtr(self.get_port(), rts_dtr)
		self.flasher.set_info(port = self.get_port(), rts_dtr=rts_dtr)

	def on_port_changed(self, event):
		""" On port changed event """
		rts_dtr = self.ports.get_rts_dtr(self.get_port())
		self.window.chk_rts_dtr.setChecked(rts_dtr)
		self.flasher.set_info(port = self.get_port(), rts_dtr=rts_dtr)

	def on_flash_clicked(self, event):
		""" Flash of firmware button clicked """
		self.flash_dialog.show()
		self.flash_dialog.dialog.erase.setChecked(False)
		self.flash_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
		result = self.flash_dialog.exec()
		if result == 1 and self.window.combo_port.currentText() != "":
			try:
				port      = self.window.combo_port.currentText()
				baud      = self.flash_dialog.dialog.baud.currentText()
				rts_dtr   = self.window.chk_rts_dtr.isChecked()
				firmware  = self.flash_dialog.dialog.firmware.text()
				erase     = self.flash_dialog.dialog.erase.isChecked()
				self.flasher.flash(port, baud, rts_dtr, firmware, erase)
			except Exception as err:
				print(err)

	def get_port(self):
		""" Get the name of serial port """
		try:
			result = self.window.combo_port.currentText()
		except:
			result = None
		return result

	def on_refresh_console(self):
		""" Refresh the console content """
		self.window.output.viewport().setProperty("cursor", QCursor(Qt.CursorShape.ArrowCursor))
		if self.clear_selection is True:
			cursor = self.window.output.textCursor()
			cursor.removeSelectedText()
			self.clear_selection = False

		cursor = self.window.output.textCursor()
		if cursor.selectionEnd() == cursor.selectionStart():
			output = self.console.refresh()
			if output != "":
				self.flasher.send_key(output.encode("utf-8"))

	def closeEvent(self, event):
		""" On close window event """
		# Terminate stdout redirection
		self.console.close()

		# Stop serial thread
		self.flasher.quit()

def except_hook(cls, exception, traceback):
	""" Exception hook """
	from traceback import extract_tb
	msg = QErrorMessage()
	text = '<code>' + str(exception) + "<br>"
	for filename, line, method, content in extract_tb(traceback) :
		text += '&nbsp;&nbsp;&nbsp;&nbsp;<FONT COLOR="#ff0000">File "%s", line %d, in %s</FONT><br>'%(filename,line,method)
		text += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s<br>'%(content)
	text += "</code>"
	msg.resize(800, 400)
	msg.showMessage(text)
	msg.exec()
	sys.__excepthook__(cls, exception, traceback)

def main():
	""" Main application """
	app = QApplication(sys.argv)
	sys.excepthook = except_hook
	window = CamFlasher()
	app.exec()

if __name__ == "__main__":
	main()
