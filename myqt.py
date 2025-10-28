import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal  # 导入线程相关模块
from PyQt5.QtGui import QDoubleValidator
import qt_designer

# 1. 定义一个子线程类，用于执行外部脚本（不阻塞主线程）
class ScriptThread(QThread):
    # 定义信号：用于向主线程发送执行结果（成功/失败信息）
    result_signal = pyqtSignal(bool, str)  # (是否成功, 信息)  pyqtSignal(bool, str) 定义的是信号返回给主线程的参数类型
    log_signal = pyqtSignal(str)  # 实时日志信号

    def __init__(self, script_path, *args):
        super().__init__()
        self.script_path = script_path
        self.args = args  # 保存需要传递给外部脚本的参数

    def run(self):
        """子线程执行的逻辑（自动在新线程中运行）"""
        try:
            # 执行外部脚本，实时捕获输出
            self.log_signal.emit(f"开始执行脚本: {self.script_path}")
            self.log_signal.emit(f"传递的参数: {self.args}")

            # 构造命令行：[python解释器, 脚本路径, 参数1, 参数2, ...]
            cmd = [sys.executable, self.script_path] + list(self.args)
            # 执行外部脚本
            process = subprocess.Popen(
                cmd,  # 使用带参数的命令行
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将标准错误合并到标准输出
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )

            # 实时读取输出并发送信号
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    # 发送实时日志到主线程
                    self.log_signal.emit(output.strip())
            # 获取最终返回码
            return_code = process.wait()

            if return_code == 0:
                self.result_signal.emit(True, "脚本执行成功！")
            else:
                self.result_signal.emit(False, f"脚本执行失败，返回码: {return_code}")

        except FileNotFoundError:
            self.result_signal.emit(False, f"找不到脚本文件：{self.script_path}")
        except Exception as e:
            self.result_signal.emit(False, f"运行出错：{str(e)}")











class myMainWindow(QMainWindow, qt_designer.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        # 初始化 UI（来自转换后的类）
        self.setupUi(self)
        # 初始化ComboBox选项
        self.init_combobox()
        # 初始化QFrame内的文件夹选择控件
        self.pushButton_3.clicked.connect(self.choose_folder)  # 绑定点击事件
        # 点击提交的信号与槽
        self.submit.clicked.connect(self.get_ui_content)
        self.pushButton_2.clicked.connect(self.run_other_script)  # 绑定按钮事件

        self.setFixedSize(1000, 800)  # 宽度=800，高度=600

        # 设置LineEdit的验证
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_2)  #南
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_6)  #北
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_5)  #东
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_7)  #西


    """设置LineEdit的验证""" # setup_lineedit_validation validate_latitude_input  用来限制地理空间范围的输入
    def setup_lineedit_validation(self,min,max,lineEdit):
        # 使用验证器 + 文本变化信号（推荐这种方式）
        validator = QDoubleValidator(min, max,6, self)  # 改为6位小数更精确
        validator.setNotation(QDoubleValidator.StandardNotation)
        lineEdit.setValidator(validator)

        # 连接文本变化信号进行实时验证
        lineEdit.textChanged.connect(lambda text:self.validate_latitude_input(text, lineEdit,min,max))
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

    """获取UI内容"""
    def get_ui_content(self):

        # 获取ComboBox的值
        selected_text_comboBox = self.comboBox.currentText()
        print(f"选中的选项: {selected_text_comboBox}")
        # 获取时间范围
        selected_text_dateEdit_2 = self.dateEdit_2.text()
        print(f"想要的开始时间: {selected_text_dateEdit_2}")

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

    # run_other_script  on_script_finished  启动别的程序
    """点击按钮时，启动子线程执行外部脚本（不阻塞主线程）"""
    def run_other_script(self):

        script_path = "D:/Pycharmcode/test/submit_order.py"

        # 获取 dateEdit_2 中的时间值（开始时间）
        time_param = self.dateEdit_2.text().strip()  # 获取用户输入的时间
        # 结束时间
        time_param2 = self.dateEdit.text().strip()

        # if not time_param or not time_param2:
        #     QMessageBox.warning(self, "警告", "请输入开始或结束时间参数！")
        #     return
        # 获取范围信息
        North = self.lineEdit_2.text().strip()
        South = self.lineEdit_6.text().strip()
        East = self.lineEdit_5.text().strip()
        West = self.lineEdit_7.text().strip()

        external_save_dir = self.lineEdit.text().strip()
        # 获取卫星类型信息
        selected_text_comboBox = self.comboBox.currentText().strip()\


        # 创建子线程实例
        self.script_thread = ScriptThread(script_path,time_param,time_param2,North,South,East,West,selected_text_comboBox,external_save_dir)   # 这个参数由ScriptThread init 上面的定义的
        # 绑定信号：子线程执行完毕后，调用回调函数处理结果
        self.script_thread.result_signal.connect(self.on_script_finished)

        self.script_thread.log_signal.connect(self.on_script_log)
        # 启动子线程（会自动调用 run 方法）
        self.script_thread.start()

        # 可以显示一个提示，告知用户脚本已开始执行
        QMessageBox.information(self, "提示", "外部下载程序已启动，正在后台运行...")
    # run_other_script 中的槽函数
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
    # run_other_script 中的槽函数
    def on_script_log(self, log_message):
        """处理实时日志输出"""
        print(f"[外部脚本日志] {log_message}")

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







if __name__ == '__main__':
    # 创建一个QApplication实例
    app = QApplication(sys.argv)
    # 创建窗口实例
    mainWindow = myMainWindow()
    mainWindow.show()
    # 进入程序的主循环
    sys.exit(app.exec_())