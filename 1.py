import sys
import subprocess  # 导入 subprocess 模块
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
import qt_designer  # 你的 UI 模块


class myMainWindow(QMainWindow, qt_designer.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


        self.pushButton_2.clicked.connect(self.run_other_script)  # 绑定点击事件

    def run_other_script(self):
        """点击按钮时执行另一个 .py 文件，实时输出日志到控制台"""
        try:
            script_path = "D:/Pycharmcode/test/submit_order.py"

            # 关键修改：不捕获 stdout 和 stderr，让输出直接到主控制台
            result = subprocess.run(
                [sys.executable, script_path],
                check=True,
                # 移除 stdout 和 stderr 参数（默认 None，即输出到主控制台）
                text=True,
                encoding='utf-8'
            )

            # 脚本执行完成后提示成功
            print("=" * 50)
            print("脚本执行成功！所有步骤已完成")
            print("=" * 50)

        except subprocess.CalledProcessError as e:
            print("=" * 50)
            print(f"脚本执行失败！错误码：{e.returncode}")
            print(f"失败原因：{e.stderr}")  # 若仍需捕获错误信息，保留 stderr
            print("=" * 50)
        except FileNotFoundError:
            print(f"找不到脚本文件：{script_path}")
        except Exception as e:
            print(f"运行脚本时出错：{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = myMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())