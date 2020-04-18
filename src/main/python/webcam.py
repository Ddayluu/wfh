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
from PyQt5.QtGui import QImage, QPixmap, QIcon
from pyqtgraph import PlotWidget, plot
from PyQt5.QtCore import Qt, QTimer
from datetime import datetime
from config import *

import pyqtgraph as pg
import cv2
import os
import time
import requests
import numpy as np
import json

def convert_seconds_to_time_label(seconds, count_down):
	hours = int(seconds // 3600)
	minutes = int((seconds - hours * 3600) // 60)
	seconds = int(seconds - hours * 3600 - minutes * 60)

	return "Tổng thời gian\n{:02d}:{:02d}:{:02d}\n{} giây tới lần kiểm tra tiếp".format(hours, minutes, seconds, count_down)

class TrackHistory(PlotWidget):
	def __init__(self, parent):
		super().__init__()
		#Add Background colour to white
		self.setBackground('w')
		self.parent = parent

		#Add Title
		self.setTitle("<span style=\"color:black;font-size:30px\">Lịch sử theo dõi</span>")

		#Add Axis Labels
		self.setLabel('left', 'Xuất Hiện', color='black', size=15)
		self.setLabel('bottom', 'Thời Gian', color='black', size=15)

		#Add grid
		self.showGrid(x=True, y=True)

		#Set Range
		# self.setXRange(0, 10, padding=0)
		self.setYRange(-1, 3, padding=0)

		self.ticky_s = []
		self.tickx_s = []

		self.x_s = []
		self.y_s = []

		self.time2label = lambda x: datetime.strftime(datetime.fromtimestamp(x + self.parent.start_time), "\n%H:%M:%S")

		self.pen = pg.mkPen(color=(0, 0, 255))
		self.data_line = self.plot(self.tickx_s, self.ticky_s, pen=self.pen)
		self.scatters = self.plot(self.x_s, self.y_s, pen=None, symbol='o', symbolSize=10, symbolBrush=('b'))

		self.make_axis()		

	def make_axis(self):
		xdict = [(self.x_s[i], self.time2label(self.x_s[i])) for i in range(len(self.x_s))]
		ax = self.getAxis("bottom")
		ax.setHeight(int(self.parent.window.ctx.screen_h / 15))
		ax.setTicks([xdict])

	def update(self, x, y, mode=1):
		self.tickx_s.append(x)
		if mode == 0:
			self.ticky_s.append(y)
		else:
			self.ticky_s.append(1 + np.random.uniform(-0.5, 0.5))

		if len(self.tickx_s) > self.parent.interval * 6:
			self.tickx_s = self.tickx_s[1:]

		if len(self.ticky_s) > self.parent.interval * 6:
			self.ticky_s = self.ticky_s[1:]

		self.data_line.setData(self.tickx_s, self.ticky_s)

		if mode == 0:
			self.x_s.append(x)
			self.y_s.append(y)

			if len(self.x_s) >= 6:
				self.x_s = self.x_s[1:]

			if len(self.y_s) >= 6:
				self.y_s = self.y_s[1:]

			self.scatters.setData(self.x_s, self.y_s)
			self.make_axis()

	def reset(self):
		self.ticky_s = []
		self.tickx_s = []

		self.x_s = []
		self.y_s = []

		self.data_line.setData(self.tickx_s, self.ticky_s)
		self.scatters.setData(self.x_s, self.y_s)
		self.make_axis()

class LogEventThread(QThread):
	done = pyqtSignal(int, list)

	def __init__(self, data, detect_data, token):
		super().__init__()
		self.data = data
		self.detect_data = detect_data
		self.token = token

	def run(self):
		try:
			if self.detect_data[1] > 0:
				r = requests.post(webserver + "/api/Webcam/LogEvent", \
					data=json.dumps(self.data),
					headers={'Content-type': 'application/json; charset=utf-8', "Authorization": "Bearer " + self.token})

				self.done.emit(r.status_code, self.detect_data)
			else:
				self.done.emit(200, self.detect_data)

		except requests.exceptions.ConnectionError:
			print("Timeout", self.data)
			self.done.emit(0, self.detect_data)

class Webcam(QWidget):
	def __init__(self, window):
		super().__init__()

		# Create a timer.
		self.timer = QTimer()
		self.timer.timeout.connect(self.nextFrameSlot)

		self.msgBox = QMessageBox()

		self.interval = 30
		self.elapsed = 0
		self.start_time = time.time()

		self.window = window
		self.detected_faces = []
		self.started = False
		self.total_time = 0

		# Create a layout.
		layout = QVBoxLayout()
		layout.setSpacing(20)

		warning_layout = QHBoxLayout()
		self.warning = QLabel()
		self.warning.setText(convert_seconds_to_time_label(self.total_time, self.interval - self.elapsed))
		self.warning.setStyleSheet("padding: 10px; font-size: 25px; text-align: center;")
		self.warning.setAlignment(Qt.AlignHCenter)

		warning_layout.addWidget(self.warning)
		warning_layout.alignment = "center"
		layout.addLayout(warning_layout)

		# Add a label
		camera_layout = QHBoxLayout()
		camera_layout.alignment = "center"

		self.cam_h = int(self.window.ctx.screen_h / 3)
		self.cam_w = int(self.cam_h * 4 / 3)

		self.label = QLabel()
		self.label.setAlignment(Qt.AlignHCenter)
		self.label.resize(self.cam_w, self.cam_h)
		# self.label.setFixedWidth(self.cam_w - 20)

		pixmap = self.resizeImage(self.window.ctx.greeting_image)
		self.label.setPixmap(pixmap)
		camera_layout.addWidget(self.label)
		layout.addLayout(camera_layout)

		# Add graph
		self.tracker = TrackHistory(self)
		self.tracker.setFixedHeight(self.window.ctx.screen_h / 4)
		layout.addWidget(self.tracker)

		# Add buttons
		button_layout = QHBoxLayout()
		self.btnCamera_start = QPushButton("Bắt Đầu")
		self.btnCamera_start .clicked.connect(self.openCamera)
		button_layout.addWidget(self.btnCamera_start )

		self.btnCamera_stop = QPushButton("Tạm Nghỉ")
		self.btnCamera_stop.clicked.connect(self.stopCamera)
		button_layout.addWidget(self.btnCamera_stop)
		self.btnCamera_stop.setEnabled(False)

		layout.addLayout(button_layout)
		# Set the layout
		self.setLayout(layout)
		self.window.setFixedSize(self.sizeHint())		

	# https://stackoverflow.com/questions/1414781/prompt-on-exit-in-pyqt-application
	def closeEvent(self, event):
		msg = "Tắt ứng dụng?"
		reply = QMessageBox.question(self, 'Message',
						msg, QMessageBox.Yes, QMessageBox.No)

		if reply == QMessageBox.Yes:
			event.accept()
			self.stopCamera()
		else:
			event.ignore()

	def resizeImage(self, pixmap):
		lwidth = self.label.width()
		pwidth = pixmap.width()
		lheight = self.label.height()
		pheight = pixmap.height()

		wratio = pwidth * 1.0 / lwidth
		hratio = pheight * 1.0 / lheight

		if pwidth > lwidth or pheight > lheight:
			if wratio > hratio:
				lheight = pheight / wratio
			else:
				lwidth = pwidth / hratio

			scaled_pixmap = pixmap.scaled(lwidth, lheight)
			return scaled_pixmap
		else:
			return pixmap

	def end_session(self):
		self.msgBox.setWindowIcon(self.window.ctx.icons[WINDOW_LOGO])
		self.msgBox.setText("Phiên làm việc của bạn đã hết.")
		self.msgBox.exec_()
		self.window.navigate(LOGIN_SCREEN)		

	def openCamera(self):
		try:
			# check is token is still valid
			r = requests.get(webserver + "/api/Camera/HelloWorld", headers={"Authorization": "Bearer " + self.window.ctx.token})
			if r.status_code != 200:
				self.end_session()
				return				
		except:
			self.msgBox.setWindowIcon(self.window.ctx.icons[ERROR_LOGO])
			self.msgBox.setText("Không thể kết nối. Vui lòng kiểm tra đường truyền.")
			self.msgBox.exec_()
			return

		if self.started:
			return

		self.start_time = time.time()
		self.started = True
		self.tracker.reset()

		self.btnCamera_start.setEnabled(False)
		self.btnCamera_stop.setEnabled(True)

		self.msgBox.setWindowIcon(self.window.ctx.icons[WINDOW_LOGO])
		self.msgBox.setText("Bắt đầu làm việc. Thỉnh thoảng tôi sẽ kiểm tra xem bạn có còn ở đó không. Chúc bạn làm việc hiệu quả!")
		self.msgBox.exec_()

		self.timer.start(1000)

	def stopCamera(self):
		self.timer.stop()
		self.started = False
		self.btnCamera_start.setEnabled(True)
		self.btnCamera_stop.setEnabled(False)

	def nextFrameSlot(self):
		self.elapsed += 1
		tick = time.time()
		if self.elapsed == self.interval:
			self.elapsed = 0
			video_cap = cv2.VideoCapture(0)
			video_cap.set(3, self.cam_w) #set width
			video_cap.set(4, self.cam_h) #set height
			if not video_cap.isOpened():
				self.warning.setText("Không thể mở camera.")
				self.warning.setStyleSheet("background-color: #ffc72b; padding: 10px; font-size: 25px; text-align: center;")
				self.tracker.update(tick - self.start_time, 0, 0)
				return

			start_stream = time.time()
			while 1:
				rval, frame = video_cap.read()	
				time.sleep(0.5)			
				if rval and time.time() - start_stream > 1:
					break

			video_cap.release()

			faces, confidences = self.window.ctx.detect_face(frame)
			# print("{}: {} face(s) detected".format(datetime.now(), len(faces)))
			self.log_thread = LogEventThread({
				"DateTime": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
			}, [tick - self.start_time, len(faces), self.interval], self.window.ctx.token
			)

			self.log_thread.done.connect(self.update_graph)
			self.log_thread.start()
			self.detected_faces = faces

			for face in self.detected_faces:
				startX, startY, endX, endY = face
				cv2.rectangle(frame, (startX, startY), (endX, endY), [0, 255, 0], 2)

			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			image = QImage(frame, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
			pixmap = QPixmap.fromImage(image)
			pixmap = self.resizeImage(pixmap)
			self.label.setPixmap(pixmap)
		else:
			self.tracker.update(tick - self.start_time, None)
			if self.warning.text() != "Lỗi Kết Nối":
				self.warning.setText(convert_seconds_to_time_label(self.total_time, self.interval - self.elapsed))

		# print("Elapsed:", self.elapsed)

	def update_graph(self, status_code, data):
		self.tracker.update(time.time() - self.start_time, data[1], 0)

		if status_code == 200:
			if data[1] > 0:
				self.total_time += data[2]
				print("Sent at {}. Total time: {}".format(data[0], self.total_time))
				self.warning.setText(convert_seconds_to_time_label(self.total_time, self.interval - self.elapsed))
				self.warning.setStyleSheet("padding: 10px; font-size: 25px; text-align: center;")
				
		elif status_code == 401:
			self.end_session()
		else:
			self.warning.setText("Lỗi Kết Nối")
			self.warning.setStyleSheet("background-color: #ffc72b; padding: 10px; font-size: 25px; text-align: center;")

