import sys
import time
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal
import pygame
import uuid

ROBOT_IP = "10.160.128.181"
ROBOT_PORT = 1448
CONTROL_URL = f"http://{ROBOT_IP}:{ROBOT_PORT}/api/core/motion/v1/actions"

class GamepadThread(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    axis_signal = pyqtSignal(float, float)
    buttons_signal = pyqtSignal(list)
    debug_signal = pyqtSignal(str)  # 新增

    def __init__(self, robot_ip=None, duration=100):
        super().__init__()
        self.running = True
        self.THRESHOLD = 0.5
        self.last_command_time = 0
        self.command_interval = 0.5
        self.poi_index = 1  # 新增：POI编号递增
        self.robot_ip = robot_ip or ROBOT_IP
        self.robot_port = ROBOT_PORT
        self.control_url = f"http://{self.robot_ip}:{self.robot_port}/api/core/motion/v1/actions"
        self.duration = duration  # 新增：可调 duration

    def set_duration(self, duration):
        self.duration = duration

    def update_ip(self, new_ip):
        self.robot_ip = new_ip
        self.control_url = f"http://{self.robot_ip}:{self.robot_port}/api/core/motion/v1/actions"

    def send_motion_command(self, direction, duration=None):
        data = {
            "action_name": "slamtec.agent.actions.MoveByAction",
            "options": {
                "direction": direction,
                "duration": duration if duration is not None else self.duration
            }
        }
        try:
            response = requests.post(self.control_url, json=data, timeout=1)
            self.log_signal.emit(f"Sent direction {direction}, duration: {data['options']['duration']}, status: {response.status_code}")
        except Exception as e:
            self.log_signal.emit(f"Error sending command: {e}")

    # 新增：回桩API
    def send_gohome_command(self):
        url = f"http://{self.robot_ip}:{self.robot_port}/api/multi-floor/motion/v1/gohomeaction"
        try:
            response = requests.post(url, json={}, timeout=2)
            self.log_signal.emit(f"回桩指令已发送，状态: {response.status_code}, 响应: {response.text}")
        except Exception as e:
            self.log_signal.emit(f"回桩指令发送失败: {e}")

    # 新增：创建POI API
    def send_create_poi(self):
        url = f"http://{self.robot_ip}:{self.robot_port}/api/core/artifact/v1/pois"
        max_retry = 5
        retry = 0
        while retry < max_retry:
            display_name = f"P{self.poi_index:03d}"
            poi_id = str(uuid.uuid4())
            data = {"id": poi_id, "metadata": {"display_name": display_name}}
            try:
                response = requests.post(url, json=data, timeout=2)
                if response.ok:
                    self.log_signal.emit(f"POI创建成功: {display_name}, id: {poi_id}, 响应: {response.text}")
                    self.poi_index += 1
                    break
                else:
                    self.log_signal.emit(f"POI创建失败: {display_name}, id: {poi_id}, 状态: {response.status_code}, 响应: {response.text}")
                    if response.status_code == 400:
                        self.poi_index += 1
                        retry += 1
                        continue
                    else:
                        break
            except Exception as e:
                self.log_signal.emit(f"POI创建异常: {e}")
                break

    # 新增：终止当前行为API
    def send_cancel_action(self):
        url = f"http://{self.robot_ip}:{self.robot_port}/api/core/motion/v1/actions/:current"
        try:
            response = requests.delete(url, timeout=2)
            self.log_signal.emit(f"终止当前行为指令已发送，状态: {response.status_code}, 响应: {response.text}")
        except Exception as e:
            self.log_signal.emit(f"终止当前行为指令发送失败: {e}")

    def run(self):
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            self.status_signal.emit("No gamepad detected.")
            return
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        self.status_signal.emit(f"Gamepad connected: {joystick.get_name()}")

        while self.running:
            pygame.event.pump()
            axis_x = joystick.get_axis(0)
            axis_y = joystick.get_axis(1)
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]

            self.axis_signal.emit(axis_x, axis_y)
            self.buttons_signal.emit(buttons)

            # 新增：调试信息
            axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            btns = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            debug_info = f"所有轴: {axes}\n所有按钮: {btns}"
            self.debug_signal.emit(debug_info)

            current_time = time.time()

            # 按钮优先控制
            if buttons[0]:
                self.send_motion_command(0, self.duration)
            elif buttons[1]:
                self.send_motion_command(1, self.duration)
            elif buttons[2]:
                self.send_motion_command(2, self.duration)
            elif buttons[3]:
                self.send_motion_command(3, self.duration)
            # 新增：按钮6创建POI
            elif len(buttons) > 6 and buttons[6]:
                self.send_create_poi()
                time.sleep(0.3)  # 防止多次触发
            # 新增：按钮7终止当前行为
            elif len(buttons) > 7 and buttons[7]:
                self.send_cancel_action()
                time.sleep(0.3)
            # 新增：按钮8回桩
            elif len(buttons) > 8 and buttons[8]:
                self.send_gohome_command()
                time.sleep(0.3)  # 防止多次触发
            else:
                if current_time - self.last_command_time > self.command_interval:
                    axis_duration = 500  # 摇杆动作时长，固定为500ms
                    if axis_y < -self.THRESHOLD:
                        self.send_motion_command(0, axis_duration)
                    elif axis_y > self.THRESHOLD:
                        self.send_motion_command(1, axis_duration)
                    elif axis_x < -self.THRESHOLD:
                        self.send_motion_command(3, axis_duration)  # 修正：左摇杆左为右转
                    elif axis_x > self.THRESHOLD:
                        self.send_motion_command(2, axis_duration)  # 修正：左摇杆右为左转
                    self.last_command_time = current_time

            time.sleep(0.03)

    def stop(self):
        self.running = False
        self.wait()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("游戏手柄机器人控制")
        self.resize(400, 700)

        layout = QVBoxLayout()

        # 新增：IP配置区
        ip_layout = QHBoxLayout()
        self.ip_label = QLabel("机器人IP:")
        self.ip_input = QTextEdit()
        self.ip_input.setFixedHeight(28)
        self.ip_input.setText(ROBOT_IP)
        self.ip_apply_btn = QPushButton("应用IP")
        ip_layout.addWidget(self.ip_label)
        ip_layout.addWidget(self.ip_input)
        ip_layout.addWidget(self.ip_apply_btn)
        layout.addLayout(ip_layout)

        # 新增：duration 配置区
        duration_layout = QHBoxLayout()
        self.duration_label = QLabel("动作时长(ms):")
        self.duration_input = QTextEdit()
        self.duration_input.setFixedHeight(28)
        self.duration_input.setText("100")
        self.duration_apply_btn = QPushButton("应用时长")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addWidget(self.duration_input)
        duration_layout.addWidget(self.duration_apply_btn)
        layout.addLayout(duration_layout)

        self.status_label = QLabel("手柄状态：未连接")
        layout.addWidget(self.status_label)

        axis_layout = QHBoxLayout()
        self.axis_x_label = QLabel("X轴: 0.00")
        self.axis_y_label = QLabel("Y轴: 0.00")
        axis_layout.addWidget(self.axis_x_label)
        axis_layout.addWidget(self.axis_y_label)
        layout.addLayout(axis_layout)

        self.buttons_label = QLabel("按钮状态: 无")
        layout.addWidget(self.buttons_label)

        # 新增：手柄调试区
        self.debug_label = QLabel("手柄调试：")
        layout.addWidget(self.debug_label)
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setFixedHeight(120)
        layout.addWidget(self.debug_text)

        btn_layout = QHBoxLayout()
        self.btn_forward = QPushButton("前进")
        self.btn_backward = QPushButton("后退")
        self.btn_left = QPushButton("左转")
        self.btn_right = QPushButton("右转")
        btn_layout.addWidget(self.btn_forward)
        btn_layout.addWidget(self.btn_backward)
        btn_layout.addWidget(self.btn_left)
        btn_layout.addWidget(self.btn_right)
        layout.addLayout(btn_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        self.setLayout(layout)

        self.gamepad_thread = GamepadThread(robot_ip=self.ip_input.toPlainText(), duration=int(self.duration_input.toPlainText()))
        self.gamepad_thread.log_signal.connect(self.append_log)
        self.gamepad_thread.status_signal.connect(self.update_status)
        self.gamepad_thread.axis_signal.connect(self.update_axis)
        self.gamepad_thread.buttons_signal.connect(self.update_buttons)
        self.gamepad_thread.debug_signal.connect(self.update_debug)
        self.gamepad_thread.start()

        self.btn_forward.clicked.connect(lambda: self.manual_send(0))
        self.btn_backward.clicked.connect(lambda: self.manual_send(1))
        self.btn_left.clicked.connect(lambda: self.manual_send(2))
        self.btn_right.clicked.connect(lambda: self.manual_send(3))
        # 新增：IP应用按钮事件
        self.ip_apply_btn.clicked.connect(self.apply_ip)
        # 新增：duration应用按钮事件
        self.duration_apply_btn.clicked.connect(self.apply_duration)

    def append_log(self, text):
        self.log_text.append(text)

    def update_status(self, status):
        self.status_label.setText(f"手柄状态：{status}")

    def update_axis(self, x, y):
        self.axis_x_label.setText(f"X轴: {x:.2f}")
        self.axis_y_label.setText(f"Y轴: {y:.2f}")

    def update_buttons(self, buttons):
        pressed = [str(i) for i, v in enumerate(buttons) if v]
        self.buttons_label.setText(f"按钮状态: {'无' if not pressed else ', '.join(pressed)}")

    # 新增：调试区内容更新
    def update_debug(self, text):
        self.debug_text.setPlainText(text)

    def manual_send(self, direction):
        self.append_log(f"手动发送方向 {direction} 指令")
        self.gamepad_thread.send_motion_command(direction)

    def apply_ip(self):
        new_ip = self.ip_input.toPlainText().strip()
        if new_ip:
            self.gamepad_thread.update_ip(new_ip)
            self.append_log(f"已切换机器人IP为: {new_ip}")

    def apply_duration(self):
        try:
            new_duration = int(self.duration_input.toPlainText().strip())
            self.gamepad_thread.set_duration(new_duration)
            self.append_log(f"已切换动作时长为: {new_duration} ms")
        except Exception as e:
            self.append_log(f"动作时长设置失败: {e}")

    def closeEvent(self, event):
        self.gamepad_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
