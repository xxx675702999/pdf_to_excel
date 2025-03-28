import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QFileDialog,
    QMessageBox, QScrollArea, QInputDialog, QTableWidgetItem, QListWidgetItem, QTableWidget, QLineEdit
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QIcon
from paddleocr import paddleocr
from pdf2image import convert_from_path
from PIL import Image
import pandas as pd
from widgets.graphics_view import GraphicsView
from widgets.editable_table import EditableTable
from core.ocr_thread import OCRThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._setup_data()
        self._setup_autosave()

    def _init_ui(self):
        self.setWindowTitle("小苏专用发票识别系统❤_V2")
        self.setGeometry(100, 100, 1200, 800)
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _create_widgets(self):
        self.file_list = QListWidget()
        self.graphics_view = GraphicsView()
        self.table = EditableTable()
        self.del_row_btn = QPushButton("删除选中行")
        self.open_btn = QPushButton("打开文件")
        self.recognize_btn = QPushButton("识别区域")
        self.export_btn = QPushButton("导出表格")

    def _setup_layout(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 左侧布局
        left_panel = self._create_left_panel()
        # 右侧布局
        right_panel = self._create_right_panel()

        layout.addWidget(left_panel, 3)
        layout.addWidget(right_panel, 2)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("文件列表:"))
        layout.addWidget(self.file_list)
        layout.addWidget(QLabel("图片预览:"))
        layout.addWidget(self.graphics_view)
        return panel

    def _create_right_panel(self):
        scroll = QScrollArea()
        content = QWidget()
        layout = QVBoxLayout(content)

        # 表格区域
        layout.addWidget(QLabel("数据表格:"))
        layout.addWidget(self.table)
        layout.addWidget(self.del_row_btn)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.recognize_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        return scroll

    def _setup_data(self):
        self.current_image = None
        self.images = []
        self.current_regions = []
        self.field_names = []
        self.ocr_thread = None

    def _setup_autosave(self):
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.auto_save)
        self.autosave_timer.start(30000)

    def _connect_signals(self):
        self.file_list.itemClicked.connect(self.load_image)
        self.del_row_btn.clicked.connect(self.delete_selected_rows)
        self.open_btn.clicked.connect(self.open_files)
        self.recognize_btn.clicked.connect(self.start_ocr)
        self.export_btn.clicked.connect(self.export_table)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.edit_header)

    # 以下为业务逻辑方法（内容与之前版本类似，但需要适配新的模块化结构）
    # [open_files, add_file_item, load_image, start_ocr, handle_error,
    #  export_table, auto_save, edit_header, delete_selected_rows 等方法]
    # 注意保持信号连接和异常处理逻辑
    class EditableTable(QTableWidget):
        def __init__(self):
            super().__init__()
            self.setSelectionBehavior(QTableWidget.SelectRows)
            self.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
            # 启用表头编辑
            self.horizontalHeader().setSectionsMovable(True)
            self.horizontalHeader().setSectionsClickable(True)

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Delete:
                self.remove_selected_rows()
            else:
                super().keyPressEvent(event)

        def remove_selected_rows(self):
            for idx in reversed([i.row() for i in self.selectedIndexes()]):
                self.removeRow(idx)

        def mouseDoubleClickEvent(self, event):
            """处理表头双击事件"""
            if self.horizontalHeader().geometry().contains(event.pos()):
                index = self.horizontalHeader().logicalIndexAt(event.pos())
                self.horizontalHeader().editSection(index)
            else:
                super().mouseDoubleClickEvent(event)
        # 新增方法：编辑表头

    def edit_header(self, section):
        old_name = self.table.horizontalHeaderItem(section).text()
        new_name, ok = QInputDialog.getText(
            self, "编辑字段名称", "输入新字段名称：", text=old_name)
        if ok and new_name:
            self.table.setHorizontalHeaderItem(section, QTableWidgetItem(new_name))
            if section < len(self.field_names):
                self.field_names[section] = new_name

        # 新增方法：删除选中行

    def delete_selected_rows(self):
        self.table.remove_selected_rows()

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", "PDF及图片 (*.pdf *.png *.jpg *.jpeg)")
        if not paths:
            return

        for path in paths:
            if path.lower().endswith('.pdf'):
                images = convert_from_path(path, poppler_path=r"poppler/Library/bin", dpi=300)
                for img in images:
                    self.images.append((path, img))
                    self.add_file_item(path, img)
            else:
                img = Image.open(path)
                self.images.append((path, img))
                self.add_file_item(path, img)

    def add_file_item(self, path, img):
        thumb = img.copy()
        thumb.thumbnail((100, 100))
        qimg = QImage(thumb.tobytes(), thumb.width, thumb.height,
                      thumb.width * 3, QImage.Format_RGB888)
        item = QListWidgetItem(QIcon(QPixmap.fromImage(qimg)), path)
        self.file_list.addItem(item)

    def handle_error(self, error_msg):
        QMessageBox.critical(self, "识别错误", f"发生错误：\n{error_msg}")
        self.export_table(autosave=True)

    def auto_save(self):
        if self.table.rowCount() > 0:
            self.export_table(autosave=True)

    def load_image(self):
        try:
            idx = self.file_list.currentRow()
            if 0 <= idx < len(self.images):
                self.current_image = self.images[idx][1]
                # 转换为RGB格式防止通道问题
                if self.current_image.mode != 'RGB':
                    self.current_image = self.current_image.convert('RGB')
                self.graphics_view.load_image(self.current_image)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"图片加载失败: {str(e)}")

    def start_ocr(self):
        if not self.current_image or len(self.graphics_view.rect_items) == 0:
            QMessageBox.warning(self, "警告", "请先选择图片并框选区域")
            return

            # 自动生成字段名称
        self.field_names = [f"区域 {i + 1}" for i in range(len(self.graphics_view.rect_items))]

        # 获取缩放后的坐标
        self.current_regions = self.graphics_view.get_scaled_regions(
            self.current_image.width,
            self.current_image.height
        )

        # 启动OCR线程
        self.ocr_thread = OCRThread(
            self.current_regions,
            self.current_image,
            self.field_names
        )
        self.ocr_thread.finished.connect(self.update_table)
        self.ocr_thread.error_occurred.connect(self.handle_error)
        self.ocr_thread.start()

    def update_table(self, results):
        """更新表格数据（保留历史列数据）"""
        current_cols = self.table.columnCount()
        new_cols = len(results)

        # 动态扩展列数为历史最大值
        max_cols = max(current_cols, new_cols)
        if max_cols > current_cols:
            self.table.setColumnCount(max_cols)

        # 添加新行数据
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 填充数据（新数据填充到前N列，其他列留空）
        for col in range(max_cols):
            if col < new_cols:
                name, text = results[col]
                self.table.setItem(row, col, QTableWidgetItem(text))
            else:
                self.table.setItem(row, col, QTableWidgetItem(""))

        # 更新表头（仅扩展，不缩短）
        if new_cols > current_cols:
            headers = [f"区域 {i + 1}" for i in range(new_cols)]
            self.table.setHorizontalHeaderLabels(headers)
            self.field_names = headers.copy()

    def _init_table_columns(self, results):
        """初始化表格列"""
        try:
            self.table.horizontalHeader().sectionDoubleClicked.disconnect()
        except TypeError:
            pass
        self.table.setColumnCount(len(results))
        headers = [name for name, _ in results]
        self.table.setHorizontalHeaderLabels(headers)

        # 启用表头直接编辑
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.edit_header)

    def _edit_header_directly(self, logicalIndex):
        """直接编辑表头"""
        # 获取当前表头项
        header_item = self.table.horizontalHeaderItem(logicalIndex)
        current_text = header_item.text() if header_item else ""

        # 创建编辑器
        self.table.editItem(header_item)  # 自动激活单元格编辑器

        # 监听编辑完成事件
        def on_edit_finished():
            new_text = header_item.text()
            if logicalIndex < len(self.field_names):
                self.field_names[logicalIndex] = new_text
            self.table.disconnect(editor)  # 清理信号连接

        editor = self.table.findChild(QLineEdit)
        if editor:
            editor.editingFinished.connect(on_edit_finished)

    def export_table(self, autosave=False):
        if autosave:
            path = f"autosave_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "导出表格", "", "Excel文件 (*.xlsx)")
            if not path:
                return

        try:
            headers = [self.table.horizontalHeaderItem(i).text()
                       for i in range(self.table.columnCount())]
            data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            df = pd.DataFrame(data, columns=headers)
            df.to_excel(path, index=False)

            if not autosave:
                QMessageBox.information(self, "成功", f"文件已保存到：{path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

# 保持其他辅助方法不变