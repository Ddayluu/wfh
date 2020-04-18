from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property
from fbs_runtime.application_context import is_frozen
from fbs_runtime.excepthook.sentry import SentryExceptionHandler
from PyQt5.QtWidgets import QMainWindow, QCheckBox, QApplication, QDesktopWidget
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt

from datetime import datetime
from config import *
from login import *
from register import *
from webcam import *

import webbrowser
import platform
import sys
import os
import numpy as np
import pkg_resources.py2_warn
import atexit

class CheckConfirmThread(QThread):
	done = pyqtSignal(bool)

	def __init__(self, token):
		super().__init__()
		self.token = token

	def run(self):
		try:
			r = requests.get(webserver + "/api/Account/HasConfirmedEmail",
							headers={"Authorization": "Bearer " + self.token})

			if r.status_code == 200:
				confirmed = r.json()
				self.done.emit(confirmed)

			else:
				self.done.emit(-1)

		except requests.exceptions.ConnectionError:
			self.done.emit(-2)

class CheckUpdateThread(QThread):
	done = pyqtSignal(str, str)

	def __init__(self, token):
		super().__init__()
		self.token = token

	def run(self):
		try:
			r = requests.get(webserver + "/api/Webcam/GetLatestVersion",
							headers={"Authorization": "Bearer " + self.token})

			if r.status_code == 200:
				verions = r.json()
				current_os = None

				if platform.system() == "Windows":
					current_os = "window"
				elif platform.system() == "Darwin":
					current_os = "mac"
				else:
					current_os = "linux"

				for ver in verions:
					if ver["OS"] == current_os:
						self.done.emit(current_os, ver["Version"])
						return

				self.done.emit(current_os, "0.0.0")

			else:
				self.done.emit("invalid", "0.0.0")

		except requests.exceptions.ConnectionError:
			self.done.emit("timeout", "0.0.0")

class MainWindow(QMainWindow):	
	def __init__(self, ctx):
		super(MainWindow, self).__init__()

		self.ctx = ctx
		self.setWindowIcon(self.ctx.icons[WINDOW_LOGO])
		self.msg = QMessageBox(self)
		self.msg.setWindowTitle("Thông báo")

		qtRectangle = self.frameGeometry()
		centerPoint = QDesktopWidget().availableGeometry().center()
		qtRectangle.moveCenter(centerPoint)
		self.move(qtRectangle.topLeft())

		self.navigate(LOGIN_SCREEN)
		# self.navigate(WEBCAM_SCREEN)
		self.setWindowTitle("Insite - Work From Home")
		self.show()

	def sign_in(self):
		self.navigate(WEBCAM_SCREEN)

	def navigate(self, screen):
		if screen == LOGIN_SCREEN:
			self.login_form = LoginForm(self)
			self.setCentralWidget(self.login_form)
			self.centerization()

		elif screen == WEBCAM_SCREEN:
			self.login_form.button_login.setEnabled(False)
			self.login_form.button_register.setEnabled(False)

			self.check_confirm_thread = CheckConfirmThread(self.ctx.token)
			self.check_confirm_thread.done.connect(self.check_confirm_callback)
			self.check_confirm_thread.start()

		elif screen == REGISTER_SCREEN:
			self.register_form = RegisterForm(self)
			self.setCentralWidget(self.register_form)
			self.centerization()		

	def send_email(self):
		self.login_form.button_login.setEnabled(False)
		self.login_form.button_register.setEnabled(False)
		self.send_email_thread = SendMailThread(self.ctx.token)
		self.send_email_thread.done.connect(self.send_email_callback)
		self.send_email_thread.start()

	def send_email_callback(self, sent):
		print(sent)
		if sent:
			self.msg.setText("Đã gửi mail xác nhận. Xin hãy kiểm tra hòm thư.")
		else:
			self.msg.setText("Có lỗi xảy ra khi gửi thư. Vui lòng thử lại sau.")

		self.send_email_btn.setEnabled(True)
		self.msg.exec_()
		self.login_form.button_login.setEnabled(True)
		self.login_form.button_register.setEnabled(True)

	def check_confirm_callback(self, confirmed):
		print(confirmed)
		if confirmed < 0:
			self.msg.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msg.setText("Lỗi kết nối. Vui lòng kiểm tra đường truyền.")
			self.msg.exec_()

		else:
			if not confirmed:
				if not hasattr(self, "send_email_btn"):
					self.send_email_btn = QPushButton("Gửi lại mail")
					self.send_email_btn.clicked.connect(self.send_email)
					self.msg.addButton(self.send_email_btn, QMessageBox.YesRole)

				self.msg.setText("Bạn cần phải xác nhận mail để tiếp tục")
				self.msg.setIcon(QMessageBox.Warning)
				self.msg.setStandardButtons(QMessageBox.Ok)
				self.msg.setDefaultButton(QMessageBox.Ok)
				self.msg.exec_()

				self.login_form.button_login.setEnabled(True)
				self.login_form.button_register.setEnabled(True)
			else:
				self.check_update_thread = CheckUpdateThread(self.ctx.token)
				self.check_update_thread.done.connect(self.check_update_callback)
				self.check_update_thread.start()

	def check_update_callback(self, current_os, latest_version):
		self.current_os = current_os
		self.latest_version = latest_version
		print("Current OS:", current_os)
		print("Latest version:", latest_version)
		print("Current version:", self.ctx.build_settings["version"])
		if latest_version != "0.0.0" and latest_version != self.ctx.build_settings["version"] and not os.path.isfile("ignore.txt"):
			self.check_box = QCheckBox("Không hiện lại tin này nữa", self)
			self.msg.setText("Chúng tôi có bản cập nhật mới")
			self.msg.setInformativeText("Bạn có muốn tải bản cập nhật bây giờ không?")
			self.msg.setIcon(QMessageBox.Question)
			self.msg.setCheckBox(self.check_box)
			self.msg.setStandardButtons(QMessageBox.Cancel|QMessageBox.Ok)
			self.msg.setDefaultButton(QMessageBox.Cancel)

			self.msg.buttonClicked.connect(self.popup_button)
			self.msg.exec_()

		self.webcam = Webcam(self)
		self.setCentralWidget(self.webcam)

		self.closeEvent = self.webcam.closeEvent
		self.centerization()

	def popup_button(self, i):
		answer = i.text().lower()
		print(answer)
		if answer == 'ok':
			webbrowser.open_new_tab("https://www.insite.vn/Content/portable_app/{}/{}.zip".format(self.current_os, self.latest_version))
			print("Downloading ...")
		elif answer == "cancel":
			print("Canceling ...")

		if self.check_box.checkState() > 0:
			with open("ignore.txt", "w") as f:
				f.write("1")
	
	def centerization(self):
		qtRectangle = self.frameGeometry()
		centerPoint = QDesktopWidget().availableGeometry().center()
		qtRectangle.moveCenter(centerPoint)
		self.move(qtRectangle.topLeft())		

class AppContext(ApplicationContext):
	token = None
	email = None

	def run(self):
		screen = self.app.primaryScreen()
		rect = screen.availableGeometry()

		self.screen_w = rect.width()
		self.screen_h = rect.height()
		print(self.screen_w, self.screen_h)

		self.main_window.show()
		self.main_window.setWindowTitle(self.build_settings["app_name"] + " - version " + self.build_settings["version"])
		return self.app.exec_()

	@cached_property
	def exception_handlers(self):
		result = super().exception_handlers
		if is_frozen():
			result.append(self.sentry_exception_handler)
		return result

	@cached_property
	def sentry_exception_handler(self):
		return SentryExceptionHandler(
			self.build_settings['sentry_dsn'],
			self.build_settings['version'],
			self.build_settings['environment'],
			callback=self._on_sentry_init
		)

	def _on_sentry_init(self):
		scope = self.sentry_exception_handler.scope
		from fbs_runtime import platform
		scope.set_extra('os', platform.name())
		if self.email is not None:
			scope.set_extra('user', self.email)

	@cached_property
	def main_window(self):
		return MainWindow(self)

	@cached_property
	def greeting_image(self):
		return QPixmap(self.get_resource('images/headphone.jpg'))

	@cached_property
	def net(self):
		prototxt = self.get_resource("face_detection/deploy.prototxt")
		caffemodel = self.get_resource("face_detection/res10_300x300_ssd_iter_140000.caffemodel")

		net = cv2.dnn.readNetFromCaffe(prototxt, caffemodel)
		return net

	@cached_property
	def icons(self):
		return {
			WINDOW_LOGO: QIcon(self.get_resource("images/key-logo.png")),
			ERROR_LOGO: QIcon(self.get_resource("images/warning.png")),
			SUCCESS_LOGO: QIcon(self.get_resource("images/check.png")),
			DENIED_LOGO: QIcon(self.get_resource("images/denied.png"))
		}

	def detect_face(self, image, threshold=0.5):

		if image is None:
			return None

		(h, w) = image.shape[:2]

		# preprocessing input image
		blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
		self.net.setInput(blob)

		# apply face detection
		detections = self.net.forward()

		faces = []
		confidences = []

		# loop through detected faces
		for i in range(0, detections.shape[2]):
			conf = detections[0,0,i,2]

			# ignore detections with low confidence
			if conf < threshold:
				continue

			# get corner points of face rectangle
			box = detections[0,0,i,3:7] * np.array([w,h,w,h])
			(startX, startY, endX, endY) = box.astype('int')

			faces.append([startX, startY, endX, endY])
			confidences.append(conf)

		# return all detected faces and
		# corresponding confidences
		return faces, confidences


if __name__ == '__main__':
	appctxt = AppContext()       # 1. Instantiate ApplicationContext
	exit_code = appctxt.run()      # 2. Invoke appctxt.app.exec_()
	sys.exit(exit_code)