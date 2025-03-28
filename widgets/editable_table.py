from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QInputDialog
from PyQt5.QtCore import Qt

class EditableTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setRowCount(0)
        self.setColumnCount(1)
        self.setHorizontalHeaderLabels(["默认字段"])
        self.setMinimumSize(400, 600)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.remove_selected_rows()
        else:
            super().keyPressEvent(event)

    def remove_selected_rows(self):
        # 获取唯一行索引并倒序删除
        rows = sorted({index.row() for index in self.selectedIndexes()}, reverse=True)
        for row in rows:
            self.removeRow(row)  # 直接按行号删除