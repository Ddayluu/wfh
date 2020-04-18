from PyQt5.QtWidgets import (
	QWidget,
	QPushButton,
	QLabel,
	QLineEdit,
	QGridLayout,
	QMessageBox,
	QVBoxLayout,
	QHBoxLayout,
	QDesktopWidget
)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtCore import Qt
from config import *

import requests
import json

class LoginThread(QThread):
	done = pyqtSignal(str)

	def __init__(self, login_data):
		super().__init__()
		self.login_data = login_data

	def run(self):
		try:
			r = requests.post(webserver + "/api/Account/Login", \
				data=json.dumps(self.login_data),
				headers={'Content-type': 'application/json; charset=utf-8', "Referer": webserver})

			if r.status_code == 200:
				self.done.emit(r.json()["access_token"])
			else:
				self.done.emit("invalid")

		except requests.exceptions.ConnectionError:
			self.done.emit("timeout")

class LoginForm(QWidget):
	def __init__(self, window):
		super().__init__()
		self.window = window

		layout = QGridLayout()

		self.setContentsMargins(100, 10, 100, 10)
		label_name = QLabel('<font size="4"> Email </font>')
		self.lineEdit_username = QLineEdit()
		self.lineEdit_username.setPlaceholderText('Please enter your email')
		layout.addWidget(label_name, 0, 0)
		layout.addWidget(self.lineEdit_username, 0, 1)

		label_password = QLabel('<font size="4"> Password </font>')
		self.lineEdit_password = QLineEdit()
		self.lineEdit_password.setEchoMode(QLineEdit.Password)
		self.lineEdit_password.setPlaceholderText('Please enter your password')
		layout.addWidget(label_password, 1, 0)
		layout.addWidget(self.lineEdit_password, 1, 1)

		self.button_login = QPushButton('Đăng Nhập')
		self.button_login.clicked.connect(self.check_password)
		layout.addWidget(self.button_login, 2, 0, 1, 2)

		self.button_register = QPushButton('Đăng Ký Tài Khoản')
		self.button_register.clicked.connect(self.register)
		layout.addWidget(self.button_register, 3, 0, 1, 2)

		self.setLayout(layout)
		self.window.setFixedSize(self.sizeHint())		

	def register(self):
		self.window.navigate(REGISTER_SCREEN)

	@pyqtSlot()
	def check_password(self):
		self.login_thread = LoginThread({
			"Email": self.lineEdit_username.text(),
			"Password": self.lineEdit_password.text()})

		self.login_thread.done.connect(self.login_callback)

		self.button_login.setEnabled(False)
		self.button_register.setEnabled(False)
		self.login_thread.start()

	def	login_callback(self, data):

		self.button_login.setEnabled(True)
		self.button_register.setEnabled(True)

		msg = QMessageBox(self)
		msg.setWindowTitle("Login Status")
		msg.resize(500, 800)

		if data == "timeout":
			msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			msg.setText("Lỗi kết nối. Vui lòng kiểm tra đường truyền.")
			msg.exec_()

		elif data == "unknown":
			msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			msg.setText("Unknown Error.")
			msg.exec_()

		elif data == "invalid":
			msg.setWindowIcon(self.window.ctx.icons[DENIED_LOGO])
			msg.setText('Mật khẩu hoặc email sai.\nVui lòng thử lại.')
			msg.exec_()
		else:
			self.window.ctx.token = data
			self.window.ctx.email = self.lineEdit_username.text()
			print(self.window.ctx.token)
			msg.setWindowIcon(self.window.ctx.icons[SUCCESS_LOGO])
			msg.setText('Đăng nhập thành công.')
			msg.exec_()
			self.window.sign_in()
