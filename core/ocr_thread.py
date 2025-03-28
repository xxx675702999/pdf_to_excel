from PyQt5.QtCore import QThread, pyqtSignal
import traceback
import numpy as np
from paddleocr import paddleocr


class OCRThread(QThread):
    finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self,regions, image, field_names):
        super().__init__()
        self.ocr = paddleocr.PaddleOCR(use_gpu=False,cls_model_dir=".\ocrModel\cls\ch",det_model_dir=".\ocrModel\det\ch",rec_model_dir=".\ocrModel\\rec\ch",use_angle_cls=True, lang='ch')
        self.regions = regions
        self.image = image.copy()  # 使用图像副本
        self.field_names = field_names


    def run(self):
        try:
            results = []
            for region, name in zip(self.regions, self.field_names):
                # 增加区域有效性验证
                if not self._validate_region(region):
                    results.append((name, "无效区域"))
                    continue

                # 精确裁剪并转换为RGB
                cropped = self._crop_image(region)
                if cropped is None:
                    results.append((name, "裁剪失败"))
                    continue

                # 确保图像格式正确
                if cropped.mode != "RGB":
                    cropped = cropped.convert("RGB")

                # 执行OCR识别
                text = self._recognize_text(cropped)
                results.append((name, text))

            self.finished.emit(results)
        except Exception as e:
            self.error_occurred.emit(traceback.format_exc())

    def _validate_region(self, region):
        x1, y1, x2, y2 = region
        return x2 > x1 and y2 > y1 and (x2 - x1) >= 5 and (y2 - y1) >= 5

    def _crop_image(self, region):
        try:
            x1, y1, x2, y2 = map(int, region)
            # 添加边界检查
            x1 = max(0, min(x1, self.image.width - 1))
            y1 = max(0, min(y1, self.image.height - 1))
            x2 = max(x1 + 1, min(x2, self.image.width))
            y2 = max(y1 + 1, min(y2, self.image.height))
            return self.image.crop((x1, y1, x2, y2))
        except Exception as e:
            return None  # 返回空值由后续处理

    def _recognize_text(self, image):
        try:
            result = self.ocr.ocr(np.array(image), cls=False)
            return '\n'.join([line[1][0] for line in result[0]]) if result else ''
        except Exception as e:
            return f"识别错误: {str(e)}"