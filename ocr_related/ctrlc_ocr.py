import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from pdf2image import convert_from_path
import paddleocr
import os
import threading
import numpy as np


class OCRApp:
    def __init__(self, master):
        self.master = master
        self.master.title("小苏专用发票识别系统❤_V2")
        self.master.geometry("1200x800")

        # 初始化PaddleOCR
        self.ocr = paddleocr.PaddleOCR(use_gpu=False, cls_model_dir=".\ocrModel\cls\ch",
                                       det_model_dir=".\ocrModel\det\ch", rec_model_dir=".\ocrModel\\rec\ch",
                                       use_angle_cls=True, lang='ch')

        # 创建界面组件
        self.create_widgets()

        # 初始化变量
        self.images = []
        self.current_image = None
        self.current_image_index = -1
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.last_ocr_text = ''
        self.scale_factor = 1.0

        # 绑定快捷键
        self.master.bind('<Control-c>', self.copy_text)

    def create_widgets(self):
        # 创建菜单栏
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开文件", command=self.open_files)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.master.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        self.master.config(menu=menubar)

        # 创建主界面布局
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 图片列表
        self.listbox = tk.Listbox(main_frame, width=30)
        self.listbox.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)

        # Canvas区域
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 状态栏
        self.status = ttk.Label(self.master, text="就绪", anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        # 在列表区域添加操作按钮
        list_control_frame = ttk.Frame(self.listbox)
        list_control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        btn_remove = ttk.Button(
            list_control_frame,
            text="删除选中",
            command=self.remove_selected
        )
        btn_remove.pack(side=tk.LEFT, padx=2, pady=2)

        btn_clear = ttk.Button(
            list_control_frame,
            text="清空列表",
            command=self.clear_all
        )
        btn_clear.pack(side=tk.RIGHT, padx=2, pady=2)

    def open_files(self):
        filetypes = [("支持的文件", "*.pdf *.png *.jpg *.jpeg *.bmp")]
        paths = filedialog.askopenfilenames(filetypes=filetypes)
        if paths:
            threading.Thread(target=self.process_files, args=(paths,)).start()

    def process_files(self, paths):
        for path in paths:
            try:
                if path.lower().endswith('.pdf'):
                    images = convert_from_path(path, poppler_path=r"poppler/Library/bin")
                    for i, img in enumerate(images):
                        self.add_image(img, path, i + 1)
                else:
                    img = Image.open(path)
                    self.add_image(img, path)
            except Exception as e:
                self.update_status(f"错误：无法打开文件 {os.path.basename(path)} - {str(e)}")

    def add_image(self, img, path, page=1):
        self.images.append({
            'orig': img.copy(),
            'path': path,
            'page': page,
            'display': None,
            'scale': 1.0
        })
        self.master.after(0, self.update_image_list)

    def update_image_list(self):
        self.listbox.delete(0, tk.END)
        for img_info in self.images:
            name = f"{os.path.basename(img_info['path'])}"
            if img_info['page'] > 1:
                name += f" (Page {img_info['page']})"
            self.listbox.insert(tk.END, name)

        # 自动选择第一个项目（如果有）
        if self.images:
            self.listbox.selection_set(0)
            self.current_image_index = 0
            self.show_image(self.images[0])
        else:
            self.current_image = None

    def on_list_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.current_image_index = selection[0]
            self.show_image(self.images[self.current_image_index])

    def show_image(self, img_info):
        self.current_image = img_info
        orig_img = img_info['orig']
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 计算缩放比例
        width_ratio = canvas_width / orig_img.width
        height_ratio = canvas_height / orig_img.height
        scale = min(width_ratio, height_ratio, 1.0)
        self.scale_factor = scale

        new_size = (int(orig_img.width * scale), int(orig_img.height * scale))
        display_img = orig_img.resize(new_size, Image.Resampling.LANCZOS)
        img_info['display'] = ImageTk.PhotoImage(display_img)
        img_info['scale'] = scale

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=img_info['display'])
        self.update_status(f"已加载：{os.path.basename(img_info['path'])}")

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)

        # 创建半透明覆盖层（天蓝色带透明度）
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='#0078D7',  # 浅蓝色边框
            fill='#66ccff',  # 浅蓝色填充
            width=2,
            stipple='gray25',  # 使用点状图案实现半透明效果
            dash=(4, 4)  # 虚线样式
        )

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

        # 动态调整透明度效果
        alpha = min(0.5, abs(cur_x - self.start_x) / 500)
        self.canvas.itemconfig(
            self.rect,
            fill=self._rgba(135, 206, 250, alpha * 255)  # 动态调整透明度
        )

    def _rgba(self, r, g, b, a):
        """将RGBA转换为Tkinter兼容的颜色格式"""
        return f'#{r:02x}{g:02x}{b:02x}'

    def on_release(self, event):
        # 检查是否已选择图片
        if not self.current_image:
            self.update_status("错误：请先选择要操作的图片")
            return

        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        # 转换为原始图像坐标
        x0 = int(min(self.start_x, end_x) / self.scale_factor)
        y0 = int(min(self.start_y, end_y) / self.scale_factor)
        x1 = int(max(self.start_x, end_x) / self.scale_factor)
        y1 = int(max(self.start_y, end_y) / self.scale_factor)

        # 截取区域图像
        orig_img = self.current_image['orig']
        if x0 < x1 and y0 < y1:
            try:
                region = orig_img.crop((x0, y0, x1, y1))
                threading.Thread(target=self.async_ocr, args=(region,)).start()
            except Exception as e:
                self.update_status(f"错误：{str(e)}")

    def async_ocr(self, region):
        try:
            result = self.ocr.ocr(np.array(region), cls=True)
            texts = []
            for line in result:
                if line:
                    for word in line:
                        if word and len(word) >= 2:
                            texts.append(word[1][0])
            self.master.after(0, self.update_ocr_result, '\n'.join(texts))
        except Exception as e:
            self.master.after(0, self.update_status, f"OCR错误：{str(e)}")

    def update_ocr_result(self, text):
        self.last_ocr_text = text
        self.update_status("识别完成，按Ctrl+C复制文字")

    def copy_text(self, event=None):
        if self.last_ocr_text:
            self.master.clipboard_clear()
            self.master.clipboard_append(self.last_ocr_text)
            self.update_status("文字已复制到剪贴板")

    def on_canvas_resize(self, event):
        if self.current_image:
            self.show_image(self.current_image)

    def update_status(self, message):
        self.status.config(text=message)

    def remove_selected(self):
        if not self.images:
            return

        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择要删除的项目")
            return

        if messagebox.askyesno("确认", "确定要删除选中的文件吗？"):
            # 倒序删除避免索引变化问题
            for index in reversed(selection):
                del self.images[index]

            self.update_image_list()

            if self.images:
                self.listbox.selection_set(0)
                self.current_image_index = 0
                self.show_image(self.images[0])
            else:
                self.current_image = None
                self.canvas.delete("all")
                self.update_status("已清空所有文件")

    def clear_all(self):
        if not self.images:
            return

        if messagebox.askyesno("确认", "确定要清空所有文件吗？"):
            self.images.clear()
            self.update_image_list()
            self.current_image = None
            self.canvas.delete("all")
            self.update_status("已清空所有文件")


if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()