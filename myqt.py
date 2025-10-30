import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal  # 导入线程相关模块
from PyQt5.QtGui import QDoubleValidator
import qt_designer
import time
import re
from PyQt5.QtCore import QTimer
# 1. 定义一个子线程类，用于执行外部脚本（不阻塞主线程）
class ScriptThread(QThread):
    # 定义信号：用于向主线程发送执行结果（成功/失败信息）
    result_signal = pyqtSignal(bool, str)  # (是否成功, 信息)  pyqtSignal(bool, str) 定义的是信号返回给主线程的参数类型
    log_signal = pyqtSignal(str)  # 实时日志信号
    need_retry_signal = pyqtSignal()  # 无参数，仅通知需要重试

    def __init__(self, script_path, *args):
        super().__init__()
        self.script_path = script_path
        self.args = args  # 保存需要传递给外部脚本的参数

    def run(self):
        """子线程执行的逻辑（自动在新线程中运行）"""
        try:

            self.log_signal.emit(f"开始执行外部脚本，外部脚本的路径为：{self.script_path}")
            self.log_signal.emit(f"向外部程序传递的参数为：{self.args}")

            # 构造命令行：["当前Python解释器路径","外部脚本路径","参数1",...,"参数N"]
            cmd = [sys.executable, self.script_path] + list(self.args)
            # 执行外部脚本
            process = subprocess.Popen(
                cmd,  # 命令行列表
                stdout=subprocess.PIPE,  # 让你的代码可以通过 process.stdout 读取外部脚本的输出（如日志信息）
                stderr=subprocess.STDOUT,  # 将标准错误合并到标准输出，通过同一管道（process.stdout）读取所有输出（正常日志和错误信息）
                text=True,  # 将外部程序的输出以字符串（str） 形式返回   universal_newlines=True(版本较早的写法)
                bufsize=1,  # 控制缓冲区大小：bufsize=1 表示使用行缓冲（按行读取输出），确保外部程序输出一行内容后，你的代码能尽快通过 readline() 读取到
                encoding='utf-8'  # 指定外部程序输出的编码格式为 utf-8
            )

            buffer = ""
            last_emit_time = time.time()  # 记录当前时间
            need_retry = False  # 标记是否需要重试  用于download.py重新执行
            # 实时读取输出并发送信号
            while True:
                output = process.stdout.readline()  # 读取外部程序输出的一行内容
                if output == '' and process.poll() is not None:  # 外部程序的输出流已读完且外部程序本身已完全终止 则跳出循环
                    break
                if output:
                    # 检查当前输出是否包含目标字符串
                    if re.search(r"订单状态.*准备中", output):
                        need_retry = True  # 标记需要重试

                    buffer += output.strip() + "\n"
                    # 每隔1秒才发一次信号
                    if time.time() - last_emit_time > 1:
                        self.log_signal.emit(buffer.strip())
                        buffer = ""
                        last_emit_time = time.time()
            # 剩余输出发送 (如果输出流读完并外部程序终止了，缓冲区可能还有数据)
            if buffer.strip():
                self.log_signal.emit(buffer.strip())

            # 获取最终返回码    【先等着退出 再发送重试信号】
            return_code = process.wait()  # 等待外部程序（通过subprocess.Popen启动的进程）执行完毕，并获取其退出状态码。

            # 判断是否需要重新执行程序，如果需要重新执行程序，则发出信号
            if need_retry:
                self.need_retry_signal.emit()  # 发送需要重试的信号

            if return_code == 0:  # 外部程序正常执行并成功结束
                self.result_signal.emit(True, "脚本执行成功！")
            else:  # 外部程序异常终止
                self.result_signal.emit(False, f"脚本执行失败，返回码: {return_code}")

        except FileNotFoundError:
            self.result_signal.emit(False, f"找不到路径下的脚本文件，路径：{self.script_path}")
        except Exception as e:
            self.result_signal.emit(False, f"run函数运行出错：{str(e)}")



class myMainWindow(QMainWindow, qt_designer.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)  # 初始化 UI（来自转换后的类Ui_MainWindow）
        self.init_combobox()   # 初始化ComboBox选项(选择FY3E FY3D)

        # 绑定信号和槽
        self.pushButton_3.clicked.connect(self.choose_folder)  # 绑定“选择路径”  选择文件夹
        self.submit.clicked.connect(self.get_ui_content)  # 点击“提交”  执行第二个程序(下载程序)
        self.pushButton_2.clicked.connect(self.run_other_script)  # 点击”确认启动下载程序“  执行第一个程序(提交订单)

        # 初始化重试定时器
        self.retry_timer = QTimer(self)
        self.retry_timer.setInterval(5 * 60 * 1000)  # 5分钟（毫秒）
        self.retry_timer.timeout.connect(self.retry_download)  # 一旦timeout信号触发，执行retry_download函数

        # 设置窗体大小
        self.setFixedSize(1000, 800)  # 宽度=800，高度=600

        # 设置LineEdit的验证
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_2)  #南
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_6)  #北
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_5)  #东
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_7)  #西

    """
    限制输入空间范围函数
    在__init__被调用
    """
    def setup_lineedit_validation(self,min,max,lineEdit):
        # 使用验证器 + 文本变化信号
        validator = QDoubleValidator(min, max,6, self)  # 创建一个 QDoubleValidator 实例（浮点数验证器）
        validator.setNotation(QDoubleValidator.StandardNotation)  # 设置数值的表示方式普通小数形式，如 3.141592
        lineEdit.setValidator(validator)  # 将创建的验证器绑定到目标 QLineEdit 输入框
        # 信号和槽 文本变化 窗口的颜色变化
        lineEdit.textChanged.connect(lambda text:self.validate_latitude_input(text, lineEdit,min,max))

    """
    根据度数，显示不同的颜色
    槽函数
    信号：setup_lineedit_validation
    """
    def validate_latitude_input(self, text,lineEdit,min,max):
        """实时验证纬度输入"""
        if text:  # 确保文本不为空
            try:
                value = float(text)
                if value < min or value > max:
                    # 超出范围时设置红色边框提示
                    lineEdit.setStyleSheet("border: 2px solid red; background-color: #FFE6E6;")
                else:
                    # 在范围内时恢复默认样式
                    lineEdit.setStyleSheet("border: 1px solid green;")
            except ValueError:
                # 无法转换为数字时设置红色边框
               lineEdit.setStyleSheet("border: 2px solid red; background-color: #FFE6E6;")
        else:
            # 为空时恢复默认样式
            lineEdit.setStyleSheet("")

    """
    执行第二个程序
    """
    def get_ui_content(self):
        """执行第二个独立外部程序"""

        script_path = "D:/Pycharmcode/test/download.py"  # 第二个程序的路径
        txt_path = "D:/Pycharmcode/test/download.txt"    # 第二个程序的参数(保存的是提交的订单号)

        # 保存download.py的参数（用于重试）
        self.download_args = (script_path, txt_path)

        # 如果上一个线程还在运行，避免资源冲突
        if hasattr(self, 'second_thread') and self.second_thread.isRunning():
            QMessageBox.warning(self, "警告", "第二个程序正在运行，请稍后再试。")
            return

        # 创建独立线程实例
        self.second_thread = ScriptThread(script_path, txt_path)

        # 绑定信号槽
        self.second_thread.result_signal.connect(self.on_second_finished)
        self.second_thread.log_signal.connect(self.on_second_log)
        self.second_thread.need_retry_signal.connect(self.prepare_retry_download)  # 绑定“需要重试download.py”的信号
        self.second_thread.start()  # 启动线程

        QMessageBox.information(self, "提示", "第二个外部程序已启动。")

    def on_second_finished(self, success, message):
        """第二个脚本执行完毕后的处理"""
        print(f"[第二脚本完成] 成功: {success}, 消息: {message}")
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)

        # 清理线程资源
        self.second_thread.quit()
        self.second_thread.wait()
        self.second_thread.deleteLater()
        self.second_thread = None  # 清除引用，防止野指针

    def on_second_log(self, log_message):
        """第二脚本的实时日志"""
        print(f"[下载数据脚本日志] {log_message}")

    def prepare_retry_download(self):
        """ 准备重试：收到信号后提示并启动定时器"""
        if not self.download_args:
            QMessageBox.warning(self, "警告", "未找到download.py的执行参数，无法重试")
            return
        # 显示提示并启动定时器
        self.statusBar().showMessage("订单未准备成功，5分钟后自动重试下载程序...")
        QMessageBox.information(self, "提示", "订单未准备成功，将在5分钟后自动执行download.py...")
        self.retry_timer.start()  # 启动5分钟定时器

    def retry_download(self):
        """定时器触发后，执行download.py"""
        self.retry_timer.stop()  # 停止定时器
        if not self.download_args:
            self.statusBar().showMessage("无download.py参数，重试失败")
            return

        # 从保存的参数中获取路径和参数
        script_path, txt_path = self.download_args
        # 启动download.py
        self.second_thread = ScriptThread(script_path, txt_path)
        self.second_thread.result_signal.connect(self.on_second_finished)
        self.second_thread.log_signal.connect(self.on_second_log)
        self.second_thread.start()
        self.statusBar().showMessage("正在重试执行download.py...")

    """
    执行第一个程序
    """
    def run_other_script(self):

        script_path = "D:/Pycharmcode/test/submit_order.py"

        # 准备参数
        time_param = self.dateEdit_2.text().strip()  # 开始时间参数
        time_param2 = self.dateEdit.text().strip()   # 结束时间
        North = self.lineEdit_2.text().strip()  # 获取范围信息
        South = self.lineEdit_6.text().strip()
        East = self.lineEdit_5.text().strip()
        West = self.lineEdit_7.text().strip()
        external_save_dir = self.lineEdit.text().strip()  # 保存位置
        selected_text_comboBox = self.comboBox.currentText().strip()  # 获取卫星类型信息(FY3D 还是FY3E)


        # 创建子线程实例
        self.script_thread = ScriptThread(script_path,time_param,time_param2,North,South,East,West,selected_text_comboBox,external_save_dir)   # 这个参数由ScriptThread init 上面的定义的
        self.script_thread.result_signal.connect(self.on_script_finished)  # 绑定信号：子线程执行完毕后，调用回调函数处理结果
        self.script_thread.log_signal.connect(self.on_script_log)
        self.script_thread.start()  # 启动子线程（会自动调用 run 方法）

        # 可以显示一个提示，告知用户脚本已开始执行
        QMessageBox.information(self, "提示", "外部下载程序已启动，正在后台运行...")

    def on_script_finished(self, success, message):
        """子线程执行完毕后的回调函数（在主线程中运行，可安全操作GUI）"""
        print(f"[脚本执行完成] 成功: {success}, 消息: {message}")
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        # 线程结束后清理资源
        self.script_thread.quit()
        self.script_thread.wait()
        self.script_thread.deleteLater()
        self.script_thread = None

    def on_script_log(self, log_message):
        """处理实时日志输出"""
        print(f"[提交订单脚本日志] {log_message}")

    """文件选择 槽 """
    def choose_folder(self):
        """弹出文件夹选择对话框，并将选中路径显示到输入框"""
        # 弹出文件夹选择对话框，初始路径设为桌面（可自定义）
        folder_path = QFileDialog.getExistingDirectory(
            self,  # 父窗口
            "选择文件夹",  # 对话框标题
            "C:/Users/jiage/Desktop"  # 初始目录
        )

        # 如果用户选择了文件夹（非取消），则更新输入框
        if folder_path:
            self.lineEdit.setText(folder_path)






    """初始化ComboBox选项"""
    def init_combobox(self):
        # 清除可能存在的默认选项
        self.comboBox.clear()
        # 添加选项
        self.comboBox.addItem("请选择你要下载的卫星型号及数据类型")
        self.comboBox.addItem("FY-3D:MERSI")
        self.comboBox.addItem("FY-3E:MERSI")
        # 设置默认选中项
        self.comboBox.setCurrentIndex(0)


if __name__ == '__main__':
    # 创建一个QApplication实例
    app = QApplication(sys.argv)
    # 创建窗口实例
    mainWindow = myMainWindow()
    mainWindow.show()
    # 进入程序的主循环
    sys.exit(app.exec_())