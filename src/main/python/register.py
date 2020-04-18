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
import traceback
import re
import json
import time

class RegisterThread(QThread):
	done = pyqtSignal(int, str)

	def __init__(self, register_data):
		super().__init__()
		self.register_data = register_data

	def run(self):
		try:
			r = requests.post(webserver + "/api/Account/Register", \
				data=json.dumps(self.register_data),
				headers={'Content-type': 'application/json; charset=utf-8', "Referer": webserver})

			if r.status_code == 400 or r.status_code == 201:
				self.done.emit(r.status_code, r.json())
			else:
				self.done.emit(r.status_code, None)

		except requests.exceptions.ConnectionError:
			self.done.emit(0, None)

		except:
			self.done.emit(-1, None)

class SendMailThread(QThread):
	done = pyqtSignal(int)

	def __init__(self, token):
		super().__init__()		
		self.token = token
		print(self.token)		

	def run(self):
		try:
			r = requests.get(webserver + "/api/Account/RequestConfirmEmail", \
				headers={"Authorization": "Bearer " + self.token})
			
			if r.status_code == 200:
				self.done.emit(1)
			else:
				self.done.emit(0)
		except:
			traceback.print_exc()
			self.done.emit(0)

class RegisterForm(QWidget):
	def __init__(self, window):
		super().__init__()
		self.window = window
		layout = QGridLayout()

		self.setContentsMargins(100, 10, 100, 10)
		self.msg = QMessageBox(self)
		self.msg.setWindowTitle("Register Status")

		label_name = QLabel('<font size="4"> Email </font>')
		self.lineEdit_username = QLineEdit()
		self.lineEdit_username.setPlaceholderText('Please enter your username')
		layout.addWidget(label_name, 0, 0)
		layout.addWidget(self.lineEdit_username, 0, 1)

		label_password = QLabel('<font size="4"> Mật Khẩu </font>')
		self.lineEdit_password = QLineEdit()
		self.lineEdit_password.setEchoMode(QLineEdit.Password)
		self.lineEdit_password.setPlaceholderText('Please enter your password')
		layout.addWidget(label_password, 1, 0)
		layout.addWidget(self.lineEdit_password, 1, 1)

		label_company = QLabel('<font size="4"> Mã Công Ty </font>')
		self.lineEdit_company = QLineEdit()
		self.lineEdit_company.setPlaceholderText('E.g: infore')
		layout.addWidget(label_company, 2, 0)
		layout.addWidget(self.lineEdit_company, 2, 1)

		self.button_register = QPushButton('Đăng Ký')
		self.button_register.clicked.connect(self.register)
		layout.addWidget(self.button_register, 3, 0, 1, 1)

		self.button_login = QPushButton('Quay Lại Đăng Nhập')
		self.button_login.clicked.connect(self.login)
		layout.addWidget(self.button_login, 3, 1, 1, 1)

		self.warning = QLabel()
		self.warning.setStyleSheet("color: red")
		self.warning.setText("Password must contain at least 6 characters")
		self.warning.setAlignment(Qt.AlignCenter)
		layout.addWidget(self.warning, 4, 0, 1, 2)

		self.setLayout(layout)
		self.window.setFixedSize(self.sizeHint())		

	def login(self):
		self.window.navigate(LOGIN_SCREEN)

	def check_email(self, email):
		# pass the regualar expression
		# and the string in search() method
		if(re.search(regex,email)):
			return 1
		else:
			return 0

	def register(self):
		if self.lineEdit_username.text() == "" or self.lineEdit_company.text() == "" or self.lineEdit_password.text() == "":
			self.warning.setText("Vui lòng điền đầy đủ thông tin.")
			return

		if not self.check_email(self.lineEdit_username.text()):
			self.warning.setText("Email không hợp lệ.")
			return

		try:
			r = requests.get(webserver + "/api/Webcam/CheckCompany?Code={}".format(self.lineEdit_company.text()))
			if r.status_code == 200:
				if len(r.json()) == 0:
					self.warning.setText("Mã công ty không tồn tại! Vui lòng thử lại")
				else:
					company_id = r.json()[0]["ID"]
					print(company_id)
					self.register_thread = RegisterThread({
							"Email": self.lineEdit_username.text(),
							"Password": self.lineEdit_password.text(),
							"ConfirmPassword": self.lineEdit_password.text(),
							"CompanyID": company_id
						})

					self.register_thread.done.connect(self.register_callback)
					self.button_login.setEnabled(False)
					self.button_register.setEnabled(False)
					self.register_thread.start()

			elif r.status_code == 500:
				self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
				self.msg.setText("Lỗi server.")
				self.msg.exec_()

		except requests.exceptions.ConnectionError:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Lỗi kết nối. Vui lòng kiểm tra đường truyền.")
			self.msg.exec_()

		except:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Unknown Error.")
			self.msg.exec_()

	def send_mail_callback(self, sent):
		print("sent", sent)
		if sent:
			self.msg.setInformativeText("Đã gửi mail xác nhận. Xin hãy kiểm tra hòm thư.")
		else:
			self.msg.setInformativeText("Có lỗi xảy ra khi gửi thư. Vui lòng thử lại sau.")

	def register_callback(self, status_code, data):		
		self.button_login.setEnabled(True)
		self.button_register.setEnabled(True)

		if status_code == 0:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Lỗi kết nối. Vui lòng kiểm tra đường truyền.")
			self.msg.exec_()

		elif status_code == 201:
			self.send_mail_thread = SendMailThread(data)
			self.send_mail_thread.done.connect(self.send_mail_callback)
			self.send_mail_thread.start()

			self.msg.setWindowIcon(self.window.ctx.icons[SUCCESS_LOGO])
			self.msg.setText('Đăng ký thành công.')
			self.msg.setInformativeText("Đang gửi mail xác nhận ..")		
			self.msg.exec_()

			# back to login screen
			self.login()

		elif status_code == 400:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText(data)
			self.msg.exec_()

		elif status_code == 500:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Lỗi server.")
			self.msg.exec_()

		else:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Unknown Error.")
			self.msg.exec_()
