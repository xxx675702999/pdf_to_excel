from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QGraphicsPixmapItem, QGraphicsRectItem, \
    QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QBrush, QCursor
import weakref

from PyQt5.sip import isdeleted


class GraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self.current_rect = None
        self.start_pos = None
        self.selected_region_ref = None  # 使用弱引用
        self.rect_items = []
        self.drag_start_pos = QPointF()

    def load_image(self, pil_img):
        """加载图片并重置所有区域"""
        self.scene.clear()
        self.rect_items.clear()

        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')

        qimg = QImage(pil_img.tobytes(), pil_img.width, pil_img.height,
                      pil_img.width * 3, QImage.Format_RGB888)
        self.pixmap = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
        self.scene.addItem(self.pixmap)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def _add_region_number(self, item, number):
        """添加区域编号"""
        text = self.scene.addText(str(number))
        text.setDefaultTextColor(Qt.red)
        font = text.font()
        font.setPointSize(20)  # 增大字体
        font.setBold(True)  # 加粗
        text.setFont(font)
        # 居中显示
        text_rect = text.boundingRect()
        text.setPos(item.rect().center().x() - text_rect.width() / 2,
                    item.rect().center().y() - text_rect.height() / 2)
        text.setParentItem(item)
        text.setZValue(1)

    # region 核心区域操作逻辑
    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                item = self.itemAt(event.pos())
                if isinstance(item, (ResizableRectItem, QGraphicsEllipseItem)):
                    # 处理区域或手柄操作
                    if isinstance(item, QGraphicsEllipseItem):
                        self.selected_handle = item
                        self.original_rect = item.parentItem().rect()
                    else:
                        self.selected_region_ref = weakref.ref(item)
                        self.drag_start_pos = event.pos()
                    return
                else:
                    # 绘制新区域
                    self.start_pos = self.mapToScene(event.pos())
                    self.current_rect = ResizableRectItem(QRectF())
                    self.current_rect.setPen(QPen(Qt.gray, 2, Qt.DashLine))
                    self.scene.addItem(self.current_rect)
        except Exception as e:
            print(f"Press Error: {str(e)}")

    def mouseMoveEvent(self, event):
        try:
            # 处理区域移动
            if self.selected_region_ref:
                item = self.selected_region_ref()
                if item and not isdeleted(item):
                    delta = event.pos() - self.drag_start_pos
                    self.drag_start_pos = event.pos()
                    item.moveBy(delta.x(), delta.y())
                else:
                    self.selected_region_ref = None
                return

            # 处理区域绘制
            if self.start_pos:
                end_pos = self.mapToScene(event.pos())
                self.current_rect.setRect(QRectF(self.start_pos, end_pos).normalized())

        except Exception as e:
            print(f"Move Error: {str(e)}")

    def mouseReleaseEvent(self, event):
        try:
            if self.selected_region_ref:
                # 移动结束
                self.setDragMode(QGraphicsView.RubberBandDrag)  # 恢复拖拽模式
                self.selected_region_ref = None
                return
            if self.start_pos:
                # 完成区域绘制
                end_pos = self.mapToScene(event.pos())
                rect = QRectF(self.start_pos, end_pos).normalized()

                if rect.width() > 5 and rect.height() > 5:
                    # 替换为正式区域项
                    self.scene.removeItem(self.current_rect)
                    final_item = ResizableRectItem(rect)
                    final_item.setPen(QPen(Qt.red, 2))
                    self.scene.addItem(final_item)

                    # 添加到管理列表
                    self.rect_items.append(final_item)
                    self._add_region_number(final_item, len(self.rect_items))

                self.current_rect = None
                self.start_pos = None

            # 清除移动状态
            self.selected_region_ref = None

        except Exception as e:
            print(f"Release Error: {str(e)}")

    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        item = self.itemAt(event.pos())
        if isinstance(item, ResizableRectItem):
            menu = QMenu()
            delete_action = menu.addAction("删除区域")
            delete_action.triggered.connect(lambda: self._delete_region(item))
            menu.exec_(event.globalPos())
        else:
            super().contextMenuEvent(event)
    def _show_context_menu(self, item):
        """显示右键菜单"""
        menu = QMenu()
        delete_action = menu.addAction("删除区域")
        delete_action.triggered.connect(lambda: self._delete_region(item))
        menu.exec_(QCursor.pos())

    def _delete_region(self, item):
        try:
            if item in self.rect_items:
                # 删除所有子项（编号文本）
                for child in item.childItems():
                    self.scene.removeItem(child)
                # 从场景和列表中移除
                self.scene.removeItem(item)
                self.rect_items.remove(item)

                # 重新编号剩余区域
                for idx, remaining_item in enumerate(self.rect_items):
                    # 清理旧编号
                    for child in remaining_item.childItems():
                        if isinstance(child, QGraphicsTextItem):
                            self.scene.removeItem(child)
                    # 添加新编号
                    self._add_region_number(remaining_item, idx + 1)
        except Exception as e:
            print(f"删除区域失败: {str(e)}")

    def get_scaled_regions(self, img_w, img_h):
        """获取缩放后的区域坐标"""
        if not hasattr(self, 'pixmap') or not self.pixmap.pixmap().width():
            return []

        regions = []
        for item in self.rect_items:
            # 获取区域项在场景中的矩形
            scene_rect = item.sceneBoundingRect()
            # 转换为相对于图片项的坐标
            x1 = scene_rect.left() - self.pixmap.scenePos().x()
            y1 = scene_rect.top() - self.pixmap.scenePos().y()
            x2 = scene_rect.right() - self.pixmap.scenePos().x()
            y2 = scene_rect.bottom() - self.pixmap.scenePos().y()

            # 计算缩放比例（基于图片项的实际显示尺寸）
            display_width = self.pixmap.boundingRect().width()
            display_height = self.pixmap.boundingRect().height()
            if display_width == 0 or display_height == 0:
                continue

            scale_x = img_w / display_width
            scale_y = img_h / display_height

            orig_x1 = max(0, min(x1 * scale_x, img_w - 1))
            orig_y1 = max(0, min(y1 * scale_y, img_h - 1))
            orig_x2 = max(0, min(x2 * scale_x, img_w))
            orig_y2 = max(0, min(y2 * scale_y, img_h))

            regions.append((orig_x1, orig_y1, orig_x2, orig_y2))
        return regions


class ResizableRectItem(QGraphicsRectItem):
    """可缩放区域项"""
    def __init__(self, rect):
        super().__init__(rect)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.handles = []
        self.resize_edge = None  # 新增：记录当前操作的边缘
        self._create_handles()

    def _create_handles(self):
        """创建四角缩放手柄并绑定事件"""
        handle_positions = [
            ('top-left', self.rect().topLeft()),
            ('top-right', self.rect().topRight()),
            ('bottom-left', self.rect().bottomLeft()),
            ('bottom-right', self.rect().bottomRight())
        ]

        for edge, pos in handle_positions:
            handle = QGraphicsEllipseItem(-5, -5, 10, 10, self)
            handle.setPos(pos)
            handle.setBrush(QBrush(Qt.blue))
            handle.setCursor(Qt.SizeFDiagCursor)
            handle.edge = edge  # 标识手柄位置

            # 绑定事件
            handle.mousePressEvent = lambda event, e=edge: self._handle_press(e, event)
            handle.mouseMoveEvent = lambda event, e=edge: self._handle_move(e, event)
            handle.mouseReleaseEvent = lambda event: self._handle_release(event)
            self.handles.append(handle)

    def _handle_press(self, edge, event):
        """手柄按下事件"""
        self.resize_edge = edge
        self.original_rect = self.rect()
        self.start_pos = event.scenePos()

    def _handle_move(self, edge, event):
        """手柄拖动事件"""
        if self.resize_edge is None:
            return

        current_pos = event.scenePos()
        dx = current_pos.x() - self.start_pos.x()
        dy = current_pos.y() - self.start_pos.y()

        # 根据操作边缘调整矩形
        new_rect = self.original_rect
        if edge == 'top-left':
            new_rect = QRectF(
                current_pos,
                self.original_rect.bottomRight()
            ).normalized()
        elif edge == 'top-right':
            new_rect = QRectF(
                QPointF(self.original_rect.left(), current_pos.y()),
                QPointF(current_pos.x(), self.original_rect.bottom())
            ).normalized()
        elif edge == 'bottom-left':
            new_rect = QRectF(
                QPointF(current_pos.x(), self.original_rect.top()),
                QPointF(self.original_rect.right(), current_pos.y())
            ).normalized()
        elif edge == 'bottom-right':
            new_rect = QRectF(
                self.original_rect.topLeft(),
                current_pos
            ).normalized()

        # 限制最小尺寸
        if new_rect.width() > 10 and new_rect.height() > 10:
            self.setRect(new_rect)

    def _handle_release(self, event):
        """手柄释放事件"""
        self.resize_edge = None

    def itemChange(self, change, value):
        """手柄位置同步更新"""
        if change == QGraphicsItem.ItemPositionHasChanged:
            for handle, pos in zip(self.handles, [
                self.rect().topLeft(),
                self.rect().topRight(),
                self.rect().bottomLeft(),
                self.rect().bottomRight()
            ]):
                handle.setPos(pos)
        return super().itemChange(change, value)

    def setRect(self, rect):
        super().setRect(rect)
        # 手动更新手柄位置
        for handle, pos in zip(self.handles, [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight()
        ]):
            handle.setPos(pos)

    def _resize_top_left(self, event):
        self._start_resize(event.scenePos(), 'top-left')

    def _resize_top_right(self, event):
        self._start_resize(event.scenePos(), 'top-right')

    def _resize_bottom_left(self, event):
        self._start_resize(event.scenePos(), 'bottom-left')

    def _resize_bottom_right(self, event):
        self._start_resize(event.scenePos(), 'bottom-right')

    def _start_resize(self, pos, edge):
        self.resize_data = {
            'start_pos': pos,
            'original_rect': self.rect(),
            'edge': edge
        }

    def mouseMoveEvent(self, event):
        """处理缩放操作"""
        if hasattr(self, 'resize_data'):
            new_pos = event.scenePos()
            old_rect = self.resize_data['original_rect']
            edge = self.resize_data['edge']

            # 计算新矩形
            if edge == 'top-left':
                new_rect = QRectF(new_pos, old_rect.bottomRight()).normalized()
            elif edge == 'top-right':
                new_rect = QRectF(old_rect.topLeft(), QPointF(new_pos.x(), old_rect.bottom())).normalized()
            elif edge == 'bottom-left':
                new_rect = QRectF(QPointF(old_rect.left(), new_pos.y()), old_rect.topRight()).normalized()
            else:
                new_rect = QRectF(old_rect.topLeft(), new_pos).normalized()

            # 限制最小尺寸并更新
            if new_rect.width() > 10 and new_rect.height() > 10:
                self.setRect(new_rect)