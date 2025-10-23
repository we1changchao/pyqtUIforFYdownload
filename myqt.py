import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal  # 导入线程相关模块
from PyQt5.QtGui import QDoubleValidator
import qt_designer

# 1. 定义一个子线程类，用于执行外部脚本（不阻塞主线程）
class ScriptThread(QThread):
    # 定义信号：用于向主线程发送执行结果（成功/失败信息）
    result_signal = pyqtSignal(bool, str)  # (是否成功, 信息)  pyqtSignal(bool, str) 定义的是信号返回给主线程的参数类型

    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path

    def run(self):
        """子线程执行的逻辑（自动在新线程中运行）"""
        try:
            # 执行外部脚本
            result = subprocess.run(
                [sys.executable, self.script_path],
                check=True,
                text=True,
                encoding='utf-8',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # 执行成功，发送信号给主线程
            self.result_signal.emit(True, f"脚本执行成功！输出：\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            # 脚本运行出错
            self.result_signal.emit(False, f"执行失败（错误码：{e.returncode}）\n错误信息：{e.stderr}")
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
        # 点击提交的信号与槽
        self.submit.clicked.connect(self.get_ui_content)
        self.setFixedSize(800, 600)  # 宽度=800，高度=600
        self.pushButton_2.clicked.connect(self.run_other_script)  # 绑定按钮事件


        # 设置LineEdit的验证
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_2)  #南
        self.setup_lineedit_validation(-90.0,90.0,self.lineEdit_6)  #北
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_5)  #东
        self.setup_lineedit_validation(-180.0,180.0,self.lineEdit_7)  #西

    # setup_lineedit_validation validate_latitude_input  用来限制地理空间范围的输入
    def setup_lineedit_validation(self,min,max,lineEdit):
        """设置LineEdit的验证"""
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

    def get_ui_content(self):
        """获取UI内容"""
        # 获取ComboBox的值
        selected_text = self.comboBox.currentText()
        selected_index = self.comboBox.currentIndex()
        print(f"选中的选项: {selected_text}")
        print(f"选中的索引: {selected_index}")


    def init_combobox(self):
        """初始化ComboBox选项"""
        # 清除可能存在的默认选项
        self.comboBox.clear()

        # 添加选项
        self.comboBox.addItem("请选择")
        self.comboBox.addItem("FY-3D:MERSI")
        self.comboBox.addItem("FY-3E:MERSI")

        # 设置默认选中项
        self.comboBox.setCurrentIndex(0)

    #run_other_script  on_script_finished  启动别的程序
    def run_other_script(self):
        """点击按钮时，启动子线程执行外部脚本（不阻塞主线程）"""
        script_path = "D:/Pycharmcode/test/submit_order.py"

        # 创建子线程实例
        self.script_thread = ScriptThread(script_path)   # 这个参数由ScriptThread init 上面的定义的
        # 绑定信号：子线程执行完毕后，调用回调函数处理结果
        self.script_thread.result_signal.connect(self.on_script_finished)
        # 启动子线程（会自动调用 run 方法）
        self.script_thread.start()

        # 可以显示一个提示，告知用户脚本已开始执行
        QMessageBox.information(self, "提示", "外部下载程序已启动，正在后台运行...")

    def on_script_finished(self, success, message):
        """子线程执行完毕后的回调函数（在主线程中运行，可安全操作GUI）"""
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)
        # 线程结束后清理资源
        self.script_thread.quit()
        self.script_thread.wait()














if __name__ == '__main__':
    # 创建一个QApplication实例
    app = QApplication(sys.argv)
    # 创建窗口实例
    mainWindow = myMainWindow()
    mainWindow.show()
    # 进入程序的主循环
    sys.exit(app.exec_())