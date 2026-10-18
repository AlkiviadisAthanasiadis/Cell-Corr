import tkinter as tk
from tkinter import filedialog as fd
from tkinter import simpledialog
from tkinter import scrolledtext
import cv2
from PIL import Image, ImageTk
import numpy as np
import os
import pandas as pd
from tkinter import messagebox
from tkinter import ttk
from skimage.io import imread
from scipy.stats import pearsonr, t, normaltest
from scipy.optimize import curve_fit,  brentq
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.font_manager as fm
import webbrowser
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from scipy.stats import kruskal
import imageio.v3 as iio
import matplotlib.cm as cm
from matplotlib import patches

class Cell_Corr:
    def __init__(self, root):
        self.root = root
        self.root.geometry("500x70+100+100")
        self.root.title("Cell-Corr")
        # -- Menu --
        self.menuBar = tk.Menu(self.root)
        fileFunc = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="File", menu=fileFunc)
        fileFunc.add_command(label="Open Video", command=self.openVideoPlayer, accelerator="Ctrl+O")
        fileFunc.add_command(label="Exit", command=self.exit, accelerator="Ctrl+Q")
        analysis_list = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="Analysis", menu=analysis_list)
        analysis_list.add_command(label="Colocalization Analysis", command=self.ColocAnalyzer)
        analysis_list.add_command(label="Graphical Analysis", command= self.openActinDynamicsPage)
        imageList = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="Image", menu = imageList)
        imageList.add_command(label="Color Coded Hyperstack", command=self.openHyperstack)
        aboutList = tk.Menu(self.menuBar, tearoff=0)
        self.menuBar.add_cascade(label="About", menu=aboutList)
        aboutList.add_command(label="Documentation", command= self.openDocumentation)
        aboutList.add_command(label="Citation", command= self.showCitation)
        aboutList.add_command(label="License", command= self.openLicense)
        self.root.config(menu=self.menuBar)
        self.root.bind("<Control-q>", self.exit)
        self.root.bind("<Control-o>", self.openVideoPlayer)
        # Console
        self.consoleFrame = tk.Frame(self.root)
        self.consoleFrame.pack(fill="x")
        self.consoleLabel = tk.Label(self.consoleFrame, text="Ready.")
        self.consoleLabel.pack()
        # Version Name 
        self.versionFrame = tk.Frame(self.root)
        self.versionFrame.pack(fill="x")
        versLabel = tk.Label(self.versionFrame, text="Version 1.0.0")
        versLabel.pack()
        # Video attributes
        self.cap = None
        self.videoPlayer = None
        self.vCanvas = None
        self.canvas_image_id = None
        self.timeline = None
        self.total_frames = 0
        self.playing = False
        self.grayscale = False
        # Masking
        self.mask_mode = False
        self.mask_points = []
        self.mask = None

        self.sample = []
        #license appear
        self.openLicense()
    
    #------------- Video Editor ------------------
    def openVideoPlayer(self, event=None):
        self.playing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.videoPlayer and tk.Toplevel.winfo_exists(self.videoPlayer):
            self.videoPlayer.destroy()
            self.videoPlayer = None
        self.vCanvas = None
        self.canvas_image_id = None
        self.timeline = None
        self.total_frames = 0
        self.grayscale = False
        self.mask_mode = False
        self.mask_points = []
        self.mask = None
        self.sample = []
        self.videoPath = fd.askopenfilename(
            initialdir="/",
            title="Select a File",
            filetypes=(("AVI files", "*.avi"), ("MP4 files", "*.mp4")))
        if not self.videoPath:
            self.consoleLabel.config(text="No file selected.")
            return

        self.cap = cv2.VideoCapture(self.videoPath)
        if not self.cap.isOpened():
            self.consoleLabel.config(text="Failed to open video.")
            return
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.consoleLabel.config(text=f"Loaded: {self.videoPath} ({self.total_frames} frames)")
        self.videoPlayer = tk.Toplevel()
        self.videoPlayer.title("Video Player")
        filePathFrame = tk.Frame(self.videoPlayer)
        filePathFrame.grid(row=0, column=0, sticky="w")
        pathLabel = tk.Label(filePathFrame, text=self.videoPath, font="Arial 12")
        pathLabel.pack()
        videoScreen = tk.Frame(self.videoPlayer, width=605, height=505)
        videoScreen.grid(row=1, column=0)
        self.vCanvas = tk.Canvas(videoScreen, background="black", width=600, height=500)
        self.vCanvas.pack()
        self.vCanvas.bind("<Button-1>", self.addMaskPoint)
        self.timeline = tk.Scale(
            self.videoPlayer, from_=0, to=self.total_frames - 1,
            orient="horizontal", length=600, command=self.seekVideo)
        self.timeline.grid(row=2, column=0)
        controls = tk.Frame(self.videoPlayer)
        controls.grid(row=3, column=0, pady=5)
        self.play_button = tk.Button(controls, text="Play", command=self.togglePlayback)
        self.play_button.pack(side="left", padx=5)
        self.gray_button = tk.Button(controls, text="Grayscale OFF", command=self.toggleGrayscale)
        self.gray_button.pack(side="left", padx=5)
        self.mask_button = tk.Button(controls, text="Mask: OFF", command=self.toggleMaskMode)
        self.mask_button.pack(side="left", padx=5)
        self.save_button = tk.Button(controls, text="Save ALL Frames", command=self.saveAllFrames)
        self.save_button.pack(side="left", padx=5)
        self.seekVideo(0)
    def playVideo(self):
        if self.cap is None or not self.cap.isOpened() or not self.playing:
            return
        ret, frame = self.cap.read()
        if ret:
            processed = self.processFrame(frame)
            img = Image.fromarray(processed)
            img = img.resize((600, 500))
            self.photo = ImageTk.PhotoImage(image=img)
            if self.canvas_image_id is None:
                self.canvas_image_id = self.vCanvas.create_image(0, 0, anchor="nw", image=self.photo)
            else:
                self.vCanvas.itemconfig(self.canvas_image_id, image=self.photo)
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.timeline.set(current_frame)
            self.vCanvas.after(30, self.playVideo)
        else:
            self.consoleLabel.config(text="Video finished.")
            self.playing = False
            self.play_button.config(text="Play")
    def seekVideo(self, value):
        frame_number = int(value)
        if self.cap is None:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        if ret:
            processed = self.processFrame(frame)
            img = Image.fromarray(processed)
            img = img.resize((600, 500))
            self.photo = ImageTk.PhotoImage(image=img)
            if self.canvas_image_id is None:
                self.canvas_image_id = self.vCanvas.create_image(0, 0, anchor="nw", image=self.photo)
            else:
                self.vCanvas.itemconfig(self.canvas_image_id, image=self.photo)
    def togglePlayback(self):
        if self.playing:
            self.playing = False
            self.play_button.config(text="Play")
        else:
            self.playing = True
            self.play_button.config(text="Pause")
            self.playVideo()
    def toggleGrayscale(self):
        self.grayscale = not self.grayscale
        self.gray_button.config(text=f"Grayscale {'ON' if self.grayscale else 'OFF'}")
        self.seekVideo(self.timeline.get())
    def toggleMaskMode(self):
        if self.mask_mode:
            self.mask_mode = False
            self.mask_button.config(text="Mask: OFF")
        else:
            self.mask_mode = True
            self.mask_points = []
            self.mask = None
            self.vCanvas.delete("mask_line")
            self.mask_button.config(text="Mask: DRAWING")
    def addMaskPoint(self, event):
        if not self.mask_mode:
            return
        x, y = event.x, event.y
        if self.mask_points and self.near1point(x, y):
            self.mask_points.append(self.mask_points[0])
            self.vCanvas.create_line(
                self.mask_points[-2][0], self.mask_points[-2][1],
                self.mask_points[-1][0], self.mask_points[-1][1],
                fill="red", tags="mask_line")
            self.creatEmsk()
            self.mask_mode = False
            self.mask_button.config(text="Mask: OFF")
            self.consoleLabel.config(text="Mask closed.")
            self.seekVideo(self.timeline.get())
            return
        self.mask_points.append((x, y))
        if len(self.mask_points) > 1:
            self.vCanvas.create_line(
                self.mask_points[-2][0], self.mask_points[-2][1],
                self.mask_points[-1][0], self.mask_points[-1][1],
                fill="red", tags="mask_line")
    def near1point(self, x, y, threshold=10):
        first_x, first_y = self.mask_points[0]
        return (abs(x - first_x) < threshold) and (abs(y - first_y) < threshold)
    def creatEmsk(self):
        pts = np.array(self.mask_points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        mask = np.zeros((500, 600), dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        self.mask = mask
    def processFrame(self, frame):
        frame = cv2.resize(frame, (600, 500))
        if self.grayscale:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if self.mask is not None:
            mask_3 = cv2.merge([self.mask] * 3)
            frame = cv2.bitwise_and(frame, mask_3)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame
    def saveAllFrames(self):
        if self.cap is None:
            return
        save_dir = fd.askdirectory(title="Select Folder to Save Frames")
        if not save_dir:
            self.consoleLabel.config(text="Save canceled.")
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_num = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            processed = self.processFrame(frame)
            out_path = os.path.join(save_dir, f"frame_{frame_num:04d}.png")
            Image.fromarray(processed).save(out_path)
            frame_num += 1
        self.consoleLabel.config(text=f"Saved {frame_num} frames to {save_dir}")
    def exit(self, event=None):
        if self.cap:
            self.cap.release()
        self.root.destroy()
        exit()
    def ColocAnalyzer(self):
        self.colocWin = tk.Toplevel()
        self.colocWin.title("Colocalization Analysis")
        self.colocWin.geometry("1000x800")
        optionMenu = tk.Frame(self.colocWin)
        optionMenu.grid(row=0,column=0)
        self.openProject = tk.Button(optionMenu, text="New Project", command=self.newColProject)
        self.openProject.pack(side="left")
        self.oldProject = tk.Button(optionMenu, text="Open Project", command= self.openExistingCol)
        self.oldProject.pack(side="left")
        self.newColocData = tk.Button(optionMenu, text="Basic Colocalization Analysis", command= self.calculateColoc)
        self.newColocData.pack(side="left")
        self.avgColocButton = tk.Button(optionMenu, text= "Time interval Averaging Colocalization Analysis"
                                        , command= self.avgColoc)
        self.avgColocButton.pack(side="left")
        self.meanButton = tk.Button(optionMenu, text="Calculate Mean", command= self.calculateRowMean)
        self.meanButton.pack(side="left")
        self.semButton = tk.Button(optionMenu, text="Std Error", command=self.calculateRowSEM)
        self.semButton.pack(side="left")
        self.normTestButt = tk.Button(optionMenu, text="Normality Test", command= self.culculateNormality)
        self.normTestButt.pack(side="left")
        self.saveDataframe = tk.Button(optionMenu, text="Save", command= self.saveColoc)
        self.saveDataframe.pack(side="left")
        self.colSheet = tk.Frame(self.colocWin)
        self.colSheet.grid(row=1,column=0)
    
    #---------------- Coloc Project --------------
    def newColProject(self):
        newColocWin = tk.Toplevel()
        newColocWin.title("New Project")
        newColocWin.geometry("400x300")
        tk.Label(newColocWin, text="Number of Frames:").pack(anchor="w", padx=10, pady=5)
        frames_entry = tk.Entry(newColocWin)
        frames_entry.pack(fill="x", padx=10)
        tk.Label(newColocWin, text="Scanning Speed (frames/sec):").pack(anchor="w", padx=10, pady=5)
        speed_entry = tk.Entry(newColocWin)
        speed_entry.pack(fill="x", padx=10)
        def createShowDf():
            try:
                self.num_frames = int(frames_entry.get())
                speed = float(speed_entry.get())
                if self.num_frames <= 0 or speed <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Input error", "Please enter valid positive numbers for frames and speed.")
                return
            times = [i * speed for i in range(self.num_frames)]
            self.df = pd.DataFrame({"Time [sec]": times})
            save_path = fd.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Save CSV file")
            if save_path:
                self.df.to_csv(save_path, index=False)
                messagebox.showinfo("Saved", f"DataFrame saved to:\n{save_path}")
            else:
                messagebox.showinfo("Canceled", "Save canceled.")
            if not hasattr(self, "text_widget"):
                self.text_widget = scrolledtext.ScrolledText(
                    self.colSheet, wrap="none", width=120, height=45)
                self.text_widget.pack(fill="both", expand=True)
                self.x_scroll = tk.Scrollbar(
                    self.colSheet, orient="horizontal", command=self.text_widget.xview)
                self.x_scroll.pack(fill="x", side="bottom")
                self.text_widget.configure(xscrollcommand=self.x_scroll.set)
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert(tk.END, self.df.to_string(index=False))
            self.text_widget.config(state="disabled")
        save_button = tk.Button(newColocWin, text="Create & Save CSV", command=createShowDf)
        save_button.pack(pady=15)
    def openExistingCol(self):
        self.df = 0
        csv_path = fd.askopenfilename(title="Open CSV", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not csv_path:
            self.consoleLabel.config(text="No CSV selected.")
            return
        self.df = pd.read_csv(csv_path)
        self.consoleLabel.config(text=f"Loaded CSV: {os.path.basename(csv_path)}")
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
    def calculateColoc(self):
        folderPath = fd.askdirectory(title="Select Folder with Frames")
        if not folderPath:
            self.consoleLabel.config(text="No folder selected.")
            return
        self.sample = []
        ref_image_path = os.path.join(folderPath, "Frame_0000.png")
        if not os.path.exists(ref_image_path):
            self.consoleLabel.config(text=f"Reference frame not found: {ref_image_path}")
            return
        image_r = imread(ref_image_path, as_gray=True)
        for i in range(len(self.df)):
            image_g_path = os.path.join(folderPath, f"Frame_{i:04d}.png")
            if not os.path.exists(image_g_path):
                self.consoleLabel.config(text=f"Frame missing: {image_g_path}")
                continue
            image_g = imread(image_g_path, as_gray=True)
            r_flat = image_r.flatten()
            g_flat = image_g.flatten()
            r_p, _ = pearsonr(r_flat, g_flat)
            self.sample.append(r_p)
        self.consoleLabel.config(text=f"Colocalization calculated for {len(self.sample)} frames.")
        if hasattr(self, "df"):
            existing_samples = [col for col in self.df.columns if col.startswith("Sample")]
            next_index = len(existing_samples) + 1
            new_col_name = f"Sample {next_index}"
            if len(self.df) >= len(self.sample):
                self.df = self.df.iloc[:len(self.sample)].copy()
                self.df[new_col_name] = self.sample
                self.consoleLabel.config(text=f"Added {new_col_name} to DataFrame.")
            else:
                self.consoleLabel.config(text="DataFrame shorter than sample length; cannot add column.")
        else:
            self.consoleLabel.config(text="DataFrame (self.df) does not exist.")
        self.consoleLabel.config(text=f"Colocalization calculated for {len(self.sample)} frames.")
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(
                self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(
                self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
    def avgColoc(self):
        folderPath = fd.askdirectory(title="Select Folder with Frames")
        if not folderPath:
            self.consoleLabel.config(text="No folder selected.")
            return
        self.sample1 = {}
        self.data = pd.DataFrame(data= self.sample1)
        max_len = len(self.df)
        for tnx in range(len(self.df)-1):
            ref_image_path = os.path.join(folderPath, f"Frame_{tnx:04d}.png")
            if not os.path.exists(ref_image_path):
                self.consoleLabel.config(text=f"Reference frame not found: {ref_image_path}")
                return
            image_r = imread(ref_image_path, as_gray = True)
            column = []
            for tny in range(tnx, len(self.df),1):
                image_g_path = os.path.join(folderPath, f"Frame_{tny:04d}.png")
                if not os.path.exists(image_g_path):
                    self.consoleLabel.config(text=f"Frame missing: {image_g_path}")
                    return
                image_g = imread(image_g_path, as_gray=True)
                r_flat = image_r.flatten()
                g_flat = image_g.flatten()
                r_p, _ = pearsonr(r_flat, g_flat)
                column.append(r_p)
            if len(column) < max_len:
                column.extend([np.nan] * (max_len - len(column)))
            self.data[str(tnx)]= column
        self.data["Mean"] = self.data.mean(axis=1, skipna=True)
        self.consoleLabel.config(text=f"Average Colocalization calculated for {len(self.data)} frames.")
        if hasattr(self, "df"):
            existing_samples = [col for col in self.df.columns if col.startswith("Sample")]
            next_index = len(existing_samples) + 1
            new_col_name = f"Sample {next_index}"
            if len(self.df) >= len(self.data):
                self.df = self.df.iloc[:len(self.data)].copy()
                self.df.loc[self.df.index[:len(self.data)],new_col_name] = self.data["Mean"].values
                self.consoleLabel.config(text=f"Added {new_col_name} to DataFrame.")
            else:
                self.consoleLabel.config(text="DataFrame shorter than sample length; cannot add column.")
        else:
            self.consoleLabel.config(text="DataFrame (self.df) does not exist.")
        self.consoleLabel.config(text=f"Colocalization calculated for {len(self.data)} frames.")
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(
                self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(
                self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
    def saveColoc(self):
        save_path = fd.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV files", "*.csv")],title="Save CSV file")
        if save_path:
            self.df.to_csv(save_path, index=False)
            messagebox.showinfo("Saved", f"DataFrame saved to:\n{save_path}")
        else:
            messagebox.showinfo("Canceled", "Save canceled.")
    def calculateRowMean(self):
        if not hasattr(self, "df"):
            messagebox.showerror("Error", "No DataFrame loaded or created.")
            return
        if self.df.shape[1] <= 1:
            messagebox.showerror("Error", "Not enough columns to calculate mean.")
            return
        self.df["Mean"] = self.df.iloc[:, 1:].mean(axis=1)
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(
                self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(
                self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
        self.consoleLabel.config(text="Row means calculated and added as 'Mean' column.")
    def calculateRowSEM(self):
        if not hasattr(self, "df"):
            messagebox.showerror("Error", "No DataFrame loaded or created.")
            return
        if self.df.shape[1] <= 1:
            messagebox.showerror("Error", "Not enough columns to calculate SEM.")
            return
        numeric_df = self.df.iloc[:, 1:-1]  
        sem_series = numeric_df.std(axis=1, ddof=1) / (numeric_df.shape[1] ** 0.5)
        self.df["SEM"] = sem_series
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(
                self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(
                self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
        self.consoleLabel.config(text="Row SEM calculated and added as 'SEM' column.")
    def culculateNormality(self):
        if not hasattr(self, "df"):
            messagebox.showerror("Error", "No DataFrame loaded or created.")
            return
        if self.df.shape[1] <= 1:
            messagebox.showerror("Error", "Not enough columns to calculate Normality.")
            return
        numeric_df = self.df.iloc[:, 1:-2]
        normList = []
        for i in range(len(self.df)):
            rowData = numeric_df.loc[i, :].tolist()
            normality = normaltest(rowData)
            normList.append(normality.pvalue)
        self.df["Normality Test p_value"] = normList
        if not hasattr(self, "text_widget"):
            self.text_widget = scrolledtext.ScrolledText(
                self.colSheet, wrap="none", width=120, height=45)
            self.text_widget.pack(fill="both", expand=True)
            self.x_scroll = tk.Scrollbar(
                self.colSheet, orient="horizontal", command=self.text_widget.xview)
            self.x_scroll.pack(fill="x", side="bottom")
            self.text_widget.configure(xscrollcommand=self.x_scroll.set)
        else:
            self.text_widget.config(state="normal")
            self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, self.df.to_string(index=False))
        self.text_widget.config(state="disabled")
        self.consoleLabel.config(text="Normality calculated and added as 'Normality' column.")
    
    # -------------- Graph Analysis -----------------------------
    def openActinDynamicsPage(self):
        self.dfs = []
        self.distdata = []
        self.legdNames =[]
        self.ActinDynamicsWindow = tk.Toplevel()
        self.ActinDynamicsWindow.geometry("900x800+0+0")
        self.ActinDynamicsWindow.title("Gaphical Dynamics Analysis")
        self.actin_fig, self.actin_ax = plt.subplots(figsize=(5, 3))
        frame = tk.Frame(self.ActinDynamicsWindow)
        frame.pack(fill="both", expand=True)
        self.canvas = FigureCanvasTkAgg(self.actin_fig, master=frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        select_btn = tk.Button(
            self.ActinDynamicsWindow, 
            text="Select Sample", command=self.selectSample)
        select_btn.pack(side="left")
        fit_btn = tk.Button(self.ActinDynamicsWindow,text="Fit Exp Decay",command=self.fitDoubleExponentialDecay)
        fit_btn.pack(side="left")
        violoinPlotDistribution = tk.Button( self.ActinDynamicsWindow, text= "Data Distribution", command=self.violinPlot)
        violoinPlotDistribution.pack(side="left")
        anova_btn = tk.Button(self.ActinDynamicsWindow, text="Run ANOVA", command=app.annotateAnova)
        anova_btn.pack(side="left")
        Kruskal_Wallis = tk.Button(self.ActinDynamicsWindow, text="Run Kruskal-Wallis test", command= self.KrWallTest)
        Kruskal_Wallis.pack(side="left")
        multi_anova_btn = tk.Button(self.ActinDynamicsWindow,text="Run ANOVA with Post Hoc",command=self.multiAnovaPosthoc)
        multi_anova_btn.pack(side="left")
        multi_kruskal_btn = tk.Button(self.ActinDynamicsWindow,text="Run  Kruskal–Wallis With Post Hoc", command=self.multiKruskalPosthoc)
        multi_kruskal_btn.pack(side="left")
        available_fonts = sorted(set(f.name for f in fm.fontManager.ttflist))
        self.font_selector = ttk.Combobox(self.ActinDynamicsWindow, values=available_fonts)
        self.font_selector.set("Arial")  
        self.font_selector.bind("<<ComboboxSelected>>", self.changeFont)
        self.font_selector.pack(side="left")
        self.ActinDynamicsWindow.protocol("WM_DELETE_WINDOW", self.closeActinWindow)
    def closeActinWindow(self):
        try:
            plt.close(self.actin_fig)   # close matplotlib figure
        except:
            pass
        try:
            if hasattr(self, "vio_fig"):
                plt.close(self.vio_fig)
        except:
            pass
        self.ActinDynamicsWindow.destroy()
    def violinPlot(self):
        if not hasattr(self, "vio_fig") or not plt.fignum_exists(self.vio_fig.number):
            self.vio_fig, self.vio_ax = plt.subplots()
            self.vio_fig.canvas.mpl_connect("close_event", self._close_violin)
        else:
            self.vio_ax.clear()
        vio = self.vio_ax.violinplot(self.distdata, showmeans=True)
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        for i, body in enumerate(vio["bodies"]):
            body.set_facecolor(colors[i % len(colors)])
            body.set_edgecolor("black")
            body.set_alpha(0.8)
        self.vio_ax.set_ylabel("Correlation Coefficient", fontsize=18)
        self.vio_ax.set_xticks(range(1, len(self.legdNames)+1))
        self.vio_ax.set_xticklabels(self.legdNames)
        self.vio_ax.set_ylim(0,1.2)
        self.vio_ax.spines['top'].set_visible(False)
        self.vio_ax.spines['right'].set_visible(False)
        self.vio_ax.spines['bottom'].set_linewidth(2)
        self.vio_ax.spines['left'].set_linewidth(2)
        self.vio_ax.tick_params(width=2, length=6)
        self.addViolinStats()
        self.vio_fig.tight_layout()
        self.vio_fig.show()    
    def _close_violin(self, event):
        plt.close(self.vio_fig)
        self.vio_fig = None
    def selectSample(self):
        self.file_path = fd.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not self.file_path:
            return
        try:
            df = pd.read_csv(self.file_path)
            if not {"Time [sec]", "Mean", "SEM"}.issubset(df.columns):
                tk.Label(self.ActinDynamicsWindow, text=f"Missing required columns in {self.file_path}").pack()
                return
        except Exception as e:
            tk.Label(self.ActinDynamicsWindow, text=f"Error reading {self.file_path}: {e}").pack()
            return
        legend_name = simpledialog.askstring(
            "Legend Name",
            f"Enter a name for the legend (file: {self.file_path}):")
        self.distdata.append(df.iloc[-1].to_list()[1:-3]) # data for violin plots
        self.dfs.append(df) # data for statistical analysis
        self.legdNames.append(legend_name)
        if not legend_name:
            legend_name = f"Sample_{len(self.actin_ax.lines) + 1}"
        self.actin_ax.plot(df["Time [sec]"], df["Mean"], label=legend_name)
        self.actin_ax.fill_between(
            df["Time [sec]"],
            df["Mean"] - df["SEM"],
            df["Mean"] + df["SEM"],
            alpha=0.2)
        self.actin_ax.set_xlabel("Time [sec]", fontsize=18)
        self.actin_ax.set_ylabel("Correlation Coefficient", fontsize=18)
        self.actin_ax.tick_params(axis='both', which='major', labelsize=14)
        self.actin_ax.legend(fontsize=14)
        self.actin_ax.set_ylim(0,1)
        self.actin_ax.set_xlim(0)
        self.actin_ax.spines['top'].set_visible(False)
        self.actin_ax.spines['right'].set_visible(False)
        self.actin_ax.spines['bottom'].set_linewidth(2)
        self.actin_ax.spines['left'].set_linewidth(2)
        self.actin_ax.tick_params(width=2, length=6)  
        self.canvas.draw() 
    def fitDoubleExponentialDecay(self):
        def double_exp_decay(t, A1, k1, A2, k2, C):
            return A1 * np.exp(-k1 * t) + A2 * np.exp(-k2 * t) + C
        if not self.dfs:
            messagebox.showerror("Fit Error", "No datasets loaded.")
            return
        t_halfs = []
        for i, df in enumerate(self.dfs):
            legend_name = self.legdNames[i]
            xdata = df["Time [sec]"].values
            ydata = df["Mean"].values   
            if len(xdata) <= 5:
                continue
            try:
                p0 = [(max(ydata) - min(ydata)) / 2, 0.1,
                    (max(ydata) - min(ydata)) / 2, 0.01,
                    min(ydata)]
                popt, _ = curve_fit(double_exp_decay,
                    xdata, ydata,
                    p0=p0,
                    bounds=([0,0,0,0,-np.inf],[np.inf]*5),
                    maxfev=10000)
                A1, k1, A2, k2, C = popt
                # Half-life
                def compute_t_half(A1, k1, A2, k2, C, xdata):
                    def f(t):
                        return double_exp_decay(t, A1, k1, A2, k2, C) - ((A1 + A2)/2 + C)

                    try:
                        return brentq(f, 0, max(xdata))
                    except ValueError:
                        return np.nan

                t_half = compute_t_half(A1, k1, A2, k2, C, xdata)
                t_halfs.append((legend_name, t_half))
                # Fit_curve
                residuals = ydata - double_exp_decay(xdata, *popt)
                ss_res = np.sum(residuals**2)
                ss_tot = np.sum((ydata - np.mean(ydata))**2)
                r_squared = 1 - (ss_res / ss_tot)
                x_fit = np.linspace(min(xdata), max(xdata), 200)
                y_fit = double_exp_decay(x_fit, *popt)
                self.actin_ax.plot(x_fit, y_fit, '--',
                                    label=f"Double Exp Fit (t1/2={t_half:.2f}s, R²={r_squared:.3f})")
            except Exception as e:
                print(f"Fit failed for {legend_name}: {e}")

        self.actin_ax.legend()
        self.canvas.draw()
    def annotateAnova(self):
        from scipy.stats import f_oneway
        import numpy as np
        if len(self.dfs) < 2:
            messagebox.showerror("ANOVA Error", "Need at least two datasets loaded.")
            return
        df1 = self.dfs[0]
        df2 = self.dfs[1]
        exclude_cols = {"Time [sec]", "Mean", "SEM"}
        data_cols1 = [c for c in df1.columns if c not in exclude_cols]
        data_cols2 = [c for c in df2.columns if c not in exclude_cols]
        if not data_cols1 or not data_cols2:
            messagebox.showerror("ANOVA Error", "No valid numeric columns found after excluding Time, Mean, SEM.")
            return
        n1 = len(df1)
        idxs = [round(n1/4), round(n1/2), round(3*n1/4), n1-1]
        labtext= ' '
        for idx in idxs:
            try:
                group1 = df1.iloc[idx][data_cols1].dropna().values
                group2 = df2.iloc[idx][data_cols2].dropna().values
                if len(group1) < 2 or len(group2) < 2:
                    continue 
                f_stat, p_value = f_oneway(group1, group2)
                labtext = labtext + 'time' + str(idx) + ':' + str(p_value) + "\n"
                if p_value >= 0.05:
                    mark = '-'
                elif p_value < 0.001:
                    mark = '***'
                elif p_value < 0.01:
                    mark = '**'
                else:
                    mark = '*'
                x_pos = df1.iloc[idx]["Time [sec]"]
                y_max = max(df1.iloc[idx]["Mean"], df2.iloc[idx]["Mean"])
                self.actin_ax.annotate(
                    mark,
                    xy=(x_pos, y_max),                
                    xytext=(x_pos, y_max + 0.08),     
                    ha='center', va='bottom',
                    fontsize=12,
                    arrowprops=dict(arrowstyle='-', color='black', lw=1))
            except Exception as e:
                print(f"ANOVA failed at index {idx}: {e}")
        self.canvas.draw()
        resultWin = tk.Toplevel()
        resultWin.title("P_values")
        resultWin.geometry("300x200")
        label = tk.Label(resultWin, text= labtext)
        label.pack(fill="both")
    def KrWallTest(self):
        import numpy as np
        if len(self.dfs) < 2:
            messagebox.showerror("Kruskal Error", "Need at least two datasets loaded.")
            return
        df1 = self.dfs[0]
        df2 = self.dfs[1]
        exclude_cols = {"Time [sec]", "Mean", "SEM"}
        data_cols1 = [c for c in df1.columns if c not in exclude_cols]
        data_cols2 = [c for c in df2.columns if c not in exclude_cols]
        if not data_cols1 or not data_cols2:
            messagebox.showerror("Kruskal Error", "No valid numeric columns found after excluding Time, Mean, SEM.")
            return
        n1 = len(df1)
        idxs = [round(n1/4), round(n1/2), round(3*n1/4), n1-1]
        labtext= ' '
        for idx in idxs:
            try:
                group1 = df1.iloc[idx][data_cols1].dropna().values
                group2 = df2.iloc[idx][data_cols2].dropna().values
                if len(group1) < 2 or len(group2) < 2:
                    continue 
                f_stat, p_value = kruskal(group1, group2)
                labtext = labtext + 'time' + str(idx) + ':' + str(p_value) + "\n"
                if p_value >= 0.05:
                    mark = '-'
                elif p_value < 0.001:
                    mark = '***'
                elif p_value < 0.01:
                    mark = '**'
                else:
                    mark = '*'
                x_pos = df1.iloc[idx]["Time [sec]"]
                y_max = max(df1.iloc[idx]["Mean"], df2.iloc[idx]["Mean"])
                self.actin_ax.annotate(
                    mark,
                    xy=(x_pos, y_max),                
                    xytext=(x_pos, y_max + 0.08),     
                    ha='center', va='bottom',
                    fontsize=12,
                    arrowprops=dict(arrowstyle='-', color='black', lw=1))
            except Exception as e:
                print(f"Kruskal failed at index {idx}: {e}")
        self.canvas.draw()
        resultWin = tk.Toplevel()
        resultWin.title("P_values")
        resultWin.geometry("300x200")
        label = tk.Label(resultWin, text= labtext)
        label.pack(fill="both")
    def multiAnovaPosthoc(self):
        from scipy.stats import f_oneway
        import scikit_posthocs as sp
        if len(self.dfs) < 3:
            messagebox.showerror("ANOVA Error", "Need at least three datasets for multi-sample ANOVA.")
            return
        exclude_cols = {"Time [sec]", "Mean", "SEM"}
        n1 = len(self.dfs[0])
        idxs = [round(n1/4), round(n1/2), round(3*n1/4), n1-1]
        labtext = ""
        for idx in idxs:
            try:
                groups = []
                labels = []
                for i, df in enumerate(self.dfs):
                    data_cols = [c for c in df.columns if c not in exclude_cols]
                    group = df.iloc[idx][data_cols].dropna().values
                    if len(group) > 1:
                        groups.append(group)
                        labels.extend([f"Sample_{i+1}"] * len(group))
                if len(groups) < 2:
                    continue
                f_stat, p_value = f_oneway(*groups)
                labtext += f"Time {idx}: ANOVA p = {p_value:.4f}\n"
                if p_value < 0.05:
                    all_data = np.concatenate(groups)
                    group_labels = np.concatenate([[f"Sample_{i+1}"] * len(g) for i, g in enumerate(groups)])
                    tukey = pairwise_tukeyhsd(endog=all_data, groups=group_labels, alpha=0.05)
                    labtext += str(tukey.summary()) + "\n\n"
                    x_pos = self.dfs[0].iloc[idx]["Time [sec]"]
                    y_max = max(df.iloc[idx]["Mean"] for df in self.dfs)
                    self.actin_ax.annotate('†',  xy=(x_pos, y_max),xytext=(x_pos, y_max + 0.08),ha='center', va='bottom',
                        fontsize=12,arrowprops=dict(arrowstyle='-', color='black', lw=1))
                    if p_value < 0.05:
                        all_data = np.concatenate(groups)
                        df_posthoc = pd.DataFrame({'Value': all_data,'Group': np.concatenate([[f"Sample_{i+1}"] * len(g) for i, g in enumerate(groups)])})
                        dunn_res = sp.posthoc_dunn(df_posthoc, val_col='Value', group_col='Group', p_adjust='bonferroni')
                        labtext += "Dunn’s post hoc (Bonferroni):\n" + dunn_res.to_string() + "\n\n"
                        x_pos = self.dfs[0].iloc[idx]["Time [sec]"]
                        y_max = max(df.iloc[idx]["Mean"] for df in self.dfs)
                        self.actin_ax.annotate('‡',xy=(x_pos, y_max),xytext=(x_pos, y_max + 0.08),ha='center', va='bottom',
                        fontsize=12,arrowprops=dict(arrowstyle='-', color='black', lw=1))
            except Exception as e:
                print(f"Multi-ANOVA failed at index {idx}: {e}")
        self.canvas.draw()
        resultWin = tk.Toplevel()
        resultWin.title("Multi-sample ANOVA + Post Hoc Results")
        resultWin.geometry("600x400")
        text_box = tk.Text(resultWin, wrap="word", font=("Arial", 10))
        text_box.insert("1.0", labtext)
        text_box.pack(fill="both", expand=True)
        text_box.config(state="disabled")
    def multiKruskalPosthoc(self):
        from scipy.stats import kruskal
        import scikit_posthocs as sp
        import numpy as np
        import pandas as pd
        if len(self.dfs) < 3:
            messagebox.showerror("Kruskal Error", "Need at least three datasets for multi-sample Kruskal–Wallis test.")
            return
        exclude_cols = {"Time [sec]", "Mean", "SEM"}
        n1 = len(self.dfs[0])
        idxs = [round(n1/4), round(n1/2), round(3*n1/4), n1-1]
        labtext = ""
        for idx in idxs:
            try:
                groups = []
                group_labels = []
                for i, df in enumerate(self.dfs):
                    data_cols = [c for c in df.columns if c not in exclude_cols]
                    group = df.iloc[idx][data_cols].dropna().values
                    if len(group) > 1:
                        groups.append(group)
                        group_labels.extend([f"Sample_{i+1}"] * len(group))
                if len(groups) < 2:
                    continue
                H_stat, p_value = kruskal(*groups)
                labtext += f"Time {idx}: Kruskal–Wallis p = {p_value:.4f}\n"
                if p_value < 0.05:
                    all_data = np.concatenate(groups)
                    df_posthoc = pd.DataFrame({'Value': all_data,
                        'Group': np.concatenate([[f"Sample_{i+1}"] * len(g) for i, g in enumerate(groups)])})
                    dunn_res = sp.posthoc_dunn(df_posthoc, val_col='Value', group_col='Group', p_adjust='bonferroni')
                    labtext += "Dunn’s post hoc (Bonferroni):\n" + dunn_res.to_string() + "\n\n"
                    x_pos = self.dfs[0].iloc[idx]["Time [sec]"]
                    y_max = max(df.iloc[idx]["Mean"] for df in self.dfs)
                    self.actin_ax.annotate(
                        '‡', 
                        xy=(x_pos, y_max),
                        xytext=(x_pos, y_max + 0.08),
                        ha='center', va='bottom',
                        fontsize=12,
                        arrowprops=dict(arrowstyle='-', color='black', lw=1))
            except Exception as e:
                print(f"Kruskal–Wallis failed at index {idx}: {e}")
        self.canvas.draw()
        resultWin = tk.Toplevel()
        resultWin.title("Multi-sample Kruskal–Wallis + Post Hoc Results")
        resultWin.geometry("600x400")
        text_box = tk.Text(resultWin, wrap="word", font=("Arial", 10))
        text_box.insert("1.0", labtext)
        text_box.pack(fill="both", expand=True)
        text_box.config(state="disabled")
    def drawSigBar(self, x1, x2, y, p):  # significance bars for violin plots
        if p < 0.001:
            text = "***"
        elif p < 0.01:
            text = "**"
        elif p < 0.05:
            text = "*"
        else:
            text = "ns"
        self.vio_ax.plot([x1, x1, x2, x2], [y, y+0.02, y+0.02, y], lw=1.5, c='black')
        self.vio_ax.text((x1+x2)/2, y+0.02, text, ha='center', va='bottom')
    def addViolinStats(self):
        from scipy.stats import kruskal
        import itertools
        if len(self.distdata) < 2:
            return
        y = 0.95
        step = 0.1
        pairs = list(itertools.combinations(range(len(self.distdata)), 2))
        for i, j in pairs:
            stat, p = kruskal(self.distdata[i], self.distdata[j])
            if p < 0.05:
                self.drawSigBar(i+1, j+1, y, p)
                y += step
    def changeFont(self,event=None):
        selected_font = self.font_selector.get()
        self.actin_ax.set_xlabel("Time [sec]", fontsize=14, fontname=selected_font)
        self.actin_ax.set_ylabel("Correlation Coefficient", fontsize=14, fontname=selected_font)
        self.actin_ax.legend(fontsize=12, prop={'family': selected_font})
        self.canvas.draw()
    
    #------------ Image Section ----------
    def openHyperstack(self):
        folderPath = fd.askdirectory(title="Select Folder with Frames")
        if not folderPath:
            self.consoleLabel.config(text="No folder selected.")
            return
        self.sample = []
        ref_image_path = os.path.join(folderPath, "frame_0000.png")
        if not os.path.exists(ref_image_path):
            self.consoleLabel.config(text=f"Reference frame not found: {ref_image_path}")
            return
        files = sorted([f for f in os.listdir(folderPath) if f.lower().endswith('.png')])
        totalNum = len(files)
        self.consoleLabel.config(text=f"{totalNum} frames found")
        frameRelativePosition = [0, 0.25, 0.5, 0.75, 1]
        indices = [int(round(p * (totalNum - 1))) for p in frameRelativePosition]
        self.consoleLabel.config(text=f"Five frames selected")
        frames = []
        for i in indices:
            img = iio.imread(os.path.join(folderPath, files[i]))
            if img.ndim == 3:  
                img = np.mean(img[..., :3], axis=-1)
            frames.append(img)
        frames = np.stack(frames, axis=0)
        frames = (frames - frames.min(axis=(1, 2), keepdims=True)) / (frames.max(axis=(1, 2),
                 keepdims=True) - frames.min(axis=(1, 2), keepdims=True))
        colorVals = [0 , 0.25, 0.5, 0.75, 1.0]
        colors = [cm.get_cmap("rainbow_r")(c)[:3] for c in colorVals]
        maxIdx = np.argmax(frames, axis=0)
        maxVal = np.max(frames, axis=0)
        H, W = frames.shape[1:]
        composite = np.zeros((H, W, 3))
        for i in range(len(colors)):
            mask = (maxIdx == i)
            for c in range(3):
                composite[..., c][mask] = colors[i][c] * maxVal[mask]
        composite = np.clip(composite, 0, 1)
        compositeRGB = (composite * 255).astype(np.uint8)
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.imshow(composite)
        ax.axis('off')
        legend_colors = [colors[i] for i in range(len(colors))]
        time_labels = [f"{round(self.df['Time [sec]'][i], 2)} sec" for i in indices]
        patches_list = [patches.Patch(color=legend_colors[i], label=time_labels[i]) for i in range(len(colors))]
        ax.legend(handles=patches_list, frameon=True, fontsize=9, title="Time Points", loc='lower right')
        plotFrame = tk.Toplevel()
        plotFrame.title("Color Coded Hyperstack")
        canvas = FigureCanvasTkAgg(fig, master=plotFrame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both")
        toolbar = NavigationToolbar2Tk(canvas, plotFrame)
        toolbar.update()
        self.consoleLabel.config(text="Composite plotted in window.")
    
    # ---------- About Section------------
    def openDocumentation(self):
        try:
            webbrowser.open('https://github.com/AlkiviadisAthanasiadis/Cell-Corr')
        except:
            messagebox.showerror("Error", "Documentation file not found.")
    def showCitation(self):
        citationWindow = tk.Toplevel(root)
        citationWindow.title("How to cite Cell-corr")
        citationWindow.geometry("700x200")
        citionLabeL = tk.Label(citationWindow, text="This field is empty. \n The article has not been published.")
        citionLabeL.pack(fill="both")
    def openLicense(self):
        licenseWindow = tk.Toplevel(self.root)
        licenseWindow.title("GNU General Public License")
        licenseWindow.geometry("700x400")    
        text_area = scrolledtext.ScrolledText(licenseWindow, wrap="word", width=70, height=25)
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        license_text = """ 
            This program is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program. If not, see <https://www.gnu.org/licenses/>.
            """
        text_area.insert(tk.END, license_text)
        text_area.config(state="disabled")

if __name__ == '__main__':
    root = tk.Tk()
    app = Cell_Corr(root)
    root.mainloop()
