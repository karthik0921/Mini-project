import sys

from PyQt6.QtWidgets import QApplication

from .main_app import myApp

if __name__=="__main__":
    app=QApplication(sys.argv)
    window=myApp()
    window.show()
    sys.exit(app.exec())