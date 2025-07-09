from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHeaderView, QMessageBox

from ..backend import crud
from .main_ui import Ui_main


class myApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_main()
        self.ui.setupUi(self)

        header = self.ui.TUsers.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.setWindowTitle("USER REGISTRATION")
        self.setWindowIcon(QIcon("mini_project_2/gui/icon.jpg"))

        self.lastSelectedRow = -1  # For toggling the selection :)
        self.row_clicked_flag = 0
        self.selected_row = -1

        self.del_button = QtWidgets.QPushButton("DELETE")

        self.display_users()

        self.ui.BSave.clicked.connect(self.add_or_update_item)
        self.ui.TUsers.cellClicked.connect(self.on_row_click)
        self.del_button.clicked.connect(self.on_del_click)

    def add_or_update_item(self):
        __sortingEnabled = self.ui.TUsers.isSortingEnabled()

        self.ui.TUsers.setSortingEnabled(False)

        if not self.ui.EditName.text() or not self.ui.EditEmail.text():
            if not self.ui.EditName.text() and not self.ui.EditEmail.text():
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Alert!!!")
                msg.setText("Name and Email cannot be empty")
                msg.setWindowIcon(QIcon("mini_project_2/gui/remove.png"))
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msg.exec()
            elif not self.ui.EditName.text():
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Alert!!!")
                msg.setText("Name cannot be empty")
                msg.setWindowIcon(QIcon("mini_project_2/gui/remove.png"))
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msg.exec()
            else:
                msg = QtWidgets.QMessageBox()
                msg.setWindowTitle("Alert!!!")
                msg.setText("Email cannot be empty")
                msg.setWindowIcon(QIcon("mini_project_2/gui/remove.png"))
                msg.setIcon(QtWidgets.QMessageBox.Icon.Warning)
                msg.exec()
            return

        if self.email_dup():
            msg = QMessageBox()
            msg.setWindowTitle("Error!!!")
            msg.setText("Email is already used!")
            msg.setWindowIcon(QIcon("mini_project_2/gui/remove.png"))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            return

        if self.email_invalid():
            self.ui.LEmailWarn.setText("Email is invalid...")
            return

        self.ui.LEmailWarn.setText("")

        if not self.row_clicked_flag:
            row = self.ui.TUsers.rowCount()
            self.ui.TUsers.setRowCount(row + 1)

            user = crud.insert_user(self.ui.EditName.text(), self.ui.EditEmail.text())

            item = QtWidgets.QTableWidgetItem()
            item.setText(str(user.id))
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 0, item)

            item = QtWidgets.QTableWidgetItem()
            item.setText(self.ui.EditName.text())
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 1, item)

            item = QtWidgets.QTableWidgetItem()
            item.setText(self.ui.EditEmail.text())
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 2, item)

            self.del_button = QtWidgets.QPushButton("DELETE")
            self.del_button.setStyleSheet("""
                QPushButton{
                    background-color: red;
                    border: 2px outset #8B0000;
                    padding: 2px;
                    font: 9pt Sans Serif Collection;
                    font-weight: bold;
                    border-radius:5px;
                }
                QPushButton:pressed{
                    background-color:#8B0000;
                    border:2px inset red;
                }
                QPushButton:hover{
                    background-color:#8B0000;
                }
        """)

            self.ui.TUsers.setCellWidget(
                row, self.ui.TUsers.columnCount() - 1, self.del_button
            )
            self.del_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            self.del_button.clicked.connect(self.on_del_click)

            # self.ui.EditName.clear()
            # self.ui.EditEmail.clear()
        else:
            item = QtWidgets.QTableWidgetItem()
            item.setText(self.ui.EditName.text())
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(self.selected_row, 1, item)

            item = QtWidgets.QTableWidgetItem()
            item.setText(self.ui.EditEmail.text())
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(self.selected_row, 2, item)

            crud.update_user(
                int(self.ui.TUsers.item(self.selected_row, 0).text()),
                self.ui.EditName.text(),
                self.ui.EditEmail.text()
            )

            self.ui.TUsers.clearSelection()
            self.lastSelectedRow = -1
            self.row_clicked_flag = 0
            self.ui.EditName.clear()
            self.ui.EditEmail.clear()

        self.ui.TUsers.setSortingEnabled(__sortingEnabled)

    def on_row_click(self, row, column):
        if self.lastSelectedRow == row:
            self.ui.TUsers.clearSelection()
            self.lastSelectedRow = -1
            self.ui.EditName.clear()
            self.ui.EditEmail.clear()
            self.row_clicked_flag = 0
            return

        self.row_clicked_flag = 1
        self.selected_row = row
        self.lastSelectedRow = row

        for i in range(3):
            self.ui.TUsers.item(row,i)

        RName = self.ui.TUsers.item(row, 1)
        REmail = self.ui.TUsers.item(row, 2)

        self.ui.EditName.setText(RName.text())
        self.ui.EditEmail.setText(REmail.text())

    def on_del_click(self):
        button = self.sender()
        for row in range(self.ui.TUsers.rowCount()):
            if self.ui.TUsers.cellWidget(row, 3) is button:
                crud.delete_user(int(self.ui.TUsers.item(row, 0).text()))
                self.ui.TUsers.removeRow(row)
                self.ui.TUsers.clearSelection()
                self.selected_row=-1
                self.row_clicked_flag=0

    def display_users(self):
        users = crud.get_all_users()
        no_of_rows = len(users)
        self.ui.TUsers.setRowCount(no_of_rows)
        row = 0
        for user in users:
            item = QtWidgets.QTableWidgetItem()
            item.setText(str(user.id))
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 0, item)

            item = QtWidgets.QTableWidgetItem()
            item.setText(user.name)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 1, item)

            item = QtWidgets.QTableWidgetItem()
            item.setText(user.email)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.TUsers.setItem(row, 2, item)

            self.del_button = QtWidgets.QPushButton("DELETE")
            self.del_button.setStyleSheet("""
                    QPushButton{
                        background-color: red;
                        border: 2px outset #8B0000;
                        padding: 2px;
                        font: 9pt Sans Serif Collection;
                        font-weight: bold;
                        border-radius:5px;
                    }
                    QPushButton:pressed{
                        background-color:#8B0000;
                        border:2px inset red;
                    }
                    QPushButton:hover{
                        background-color:#8B0000;
                    }
            """)
            self.del_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            self.ui.TUsers.setCellWidget(
                row, self.ui.TUsers.columnCount() - 1, self.del_button
            )
            self.del_button.clicked.connect(self.on_del_click)

            row += 1

    def email_dup(self):
        email = self.ui.EditEmail.text()
        return crud.check_dup_email(email)

    def email_invalid(self):
        email = self.ui.EditEmail.text()
        return crud.check_invalid_email(email)