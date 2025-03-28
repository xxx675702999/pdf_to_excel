import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext


class FileMoverGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("文件迁移工具")
        self.window.geometry("600x400")

        # 初始化路径变量
        self.src_folder = tk.StringVar()
        self.root_dir = tk.StringVar()

        # 创建界面组件
        self.create_widgets()
        self.window.mainloop()

    def create_widgets(self):
        """创建所有GUI组件"""
        # 源文件夹选择
        ttk.Label(self.window, text="源文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        src_entry = ttk.Entry(self.window, textvariable=self.src_folder, width=50)
        src_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self.window, text="浏览...", command=self.select_source).grid(row=0, column=2, padx=5)

        # 目标文件夹选择
        ttk.Label(self.window, text="目标文件夹:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        dest_entry = ttk.Entry(self.window, textvariable=self.root_dir, width=50)
        dest_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.window, text="浏览...", command=self.select_destination).grid(row=1, column=2, padx=5)

        # 操作按钮
        action_frame = ttk.Frame(self.window)
        action_frame.grid(row=2, column=0, columnspan=3, pady=10)
        ttk.Button(action_frame, text="开始移动文件", command=self.start_moving).pack(side="left", padx=10)

        # 日志显示区域
        self.log_area = scrolledtext.ScrolledText(self.window, height=10, wrap=tk.WORD)
        self.log_area.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

        # 配置网格布局权重
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(3, weight=1)

    def select_source(self):
        """选择源文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.src_folder.set(folder)
            self.log(f"选择源文件夹: {folder}")

    def select_destination(self):
        """选择目标文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.root_dir.set(folder)
            self.log(f"选择目标文件夹: {folder}")

    def start_moving(self):
        """执行文件移动操作"""
        if not self.src_folder.get() or not self.root_dir.get():
            self.log("错误：请先选择源文件夹和目标文件夹！")
            return

        try:
            self.log("\n开始移动文件...")
            self.move_files_to_root(self.src_folder.get(), self.root_dir.get())
            self.log("操作完成！")
        except Exception as e:
            self.log(f"发生错误：{str(e)}")

    def move_files_to_root(self, src_folder, root_dir):
        """实际移动文件的逻辑"""
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                src_path = os.path.join(root, file)
                dest_path = os.path.join(root_dir, file)

                if os.path.exists(dest_path):
                    self.log(f"跳过已存在文件: {file}")
                    continue

                shutil.move(src_path, dest_path)
                self.log(f"已移动 {file}")

    def log(self, message):
        """在日志区域显示信息"""
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)


if __name__ == "__main__":
    app = FileMoverGUI()