import customtkinter as ctk
from tkinter import messagebox, Canvas, PhotoImage, Menu, filedialog
import json
import threading
import os
from pathlib import Path
import subprocess
from PIL import Image, ImageTk, ImageDraw
import cv2
import queue
import urllib.request
import urllib.error
import sys
import shutil

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(relative_path):
    """Get path for data files that need to be writable (processed_videos.json, etc)"""
    # If running as EXE, save to AppData instead of exe directory
    try:
        if getattr(sys, 'frozen', False):
            # Running as bundled EXE - use AppData
            appdata = os.getenv('APPDATA') or os.path.expanduser('~')
            data_dir = os.path.join(appdata, 'EZClips')
        else:
            # Running as script - use current directory
            data_dir = os.path.abspath(".")
    except Exception:
        data_dir = os.path.abspath(".")
    
    data_path = os.path.join(data_dir, relative_path)
    
    # For processed_videos.json: if it doesn't exist in data_dir, try to copy from resource
    if 'processed_videos.json' in relative_path:
        if not os.path.exists(data_path):
            # Try to get from bundled resources
            try:
                resource_path = get_resource_path(relative_path)
                if os.path.exists(resource_path):
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(data_path), exist_ok=True)
                    # Copy bundled file to writable location
                    shutil.copy2(resource_path, data_path)
            except Exception as e:
                print(f"Could not copy processed_videos.json from resources: {e}")
    
    return data_path

# Modern tema ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Supported video formats (sync with main.py)
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

# App version
APP_VERSION = "1.0.0"

def check_for_updates():
    """Check for updates on GitHub"""
    try:
        # GitHub API endpoint - replace with your repo
        url = "https://api.github.com/repos/corp14x3/EZClips/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'EZClips'})
        response = urllib.request.urlopen(req, timeout=5)
        data = json.loads(response.read().decode())
        latest_version = data.get('tag_name', '').lstrip('v')
        
        if latest_version and latest_version > APP_VERSION:
            return {
                'has_update': True,
                'version': latest_version,
                'url': data.get('html_url', ''),
                'notes': data.get('body', '')
            }
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception):
        pass
    return {'has_update': False}

# Load language file
def load_languages():
    try:
        lang_path = get_resource_path('req/jsons/languages.json')
        with open(lang_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"tr": {}, "en": {}}

LANGUAGES = load_languages()

class VideoProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1400x900")
        # Uygulama iconu
        try:
            icon_path = get_resource_path('req/ico.ico')
            if os.path.exists(icon_path):
                # Windows .ico desteği
                self.root.iconbitmap(default=icon_path)
        except Exception:
            pass
        
        # Config dosyasını yükle
        self.load_config()
        
        # Version'ı config'ten al (tek kaynak - sadece config.json güncelle)
        global APP_VERSION
        APP_VERSION = self.config.get('APP_VERSION', '1.0.0')
        
        # Dil ayarla
        self.current_lang = self.config.get('LANGUAGE', 'tr')
        self.texts = LANGUAGES.get(self.current_lang, LANGUAGES['tr'])
        
        self.root.title(self.texts.get('app_title'))
        
        # Queue'lar (main.py'den mesajları almak için)
        self.log_queue = queue.Queue()
        self.preview_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        
        # İşlem durumu
        self.is_processing = False
        self.process_thread = None
        
        # Ana layout
        self.create_ui()
        
        # Check for updates on startup
        self.check_updates_on_startup()
        
        # Queue'ları kontrol et (her 100ms)
        self.check_queues()
        
    def load_config(self):
        """Load settings from config file"""
        try:
            # Öncelik: Kullanıcı config (AppData) varsa onu yükle, yoksa paket içi
            user_cfg = None
            if getattr(sys, 'frozen', False):
                appdata = os.getenv('APPDATA') or os.path.expanduser('~')
                user_cfg = os.path.join(appdata, 'EZClips', 'config.json')
            if user_cfg and os.path.exists(user_cfg):
                config_path = user_cfg
            else:
                config_path = get_resource_path("req/jsons/config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            messagebox.showerror("Hata", f"config.json dosyası bulunamadı!\n{e}")
            self.root.quit()
    
    def save_config(self):
        """Save settings to config file"""
        try:
            # Yazılabilir config yolu: geliştirmede repo içi, EXE'de AppData
            if getattr(sys, 'frozen', False):
                appdata = os.getenv('APPDATA') or os.path.expanduser('~')
                cfg_dir = os.path.join(appdata, 'EZClips')
                os.makedirs(cfg_dir, exist_ok=True)
                cfg_path = os.path.join(cfg_dir, 'config.json')
            else:
                cfg_path = get_resource_path('req/jsons/config.json')

            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            self.add_log("✓ Ayarlar kaydedildi", "success")
        except Exception as e:
            messagebox.showerror("Hata", f"Ayarlar kaydedilemedi: {e}")
    
    def check_updates_on_startup(self):
        """Check for updates in background"""
        def check():
            try:
                update_info = check_for_updates()
                if update_info.get('has_update'):
                    def show_update():
                        response = messagebox.askyesno(
                            "Update Available / Güncelleme Mevcut",
                            f"New version {update_info['version']} is available!\n"
                            f"Yeni sürüm {update_info['version']} mevcut!\n\n"
                            f"Download: {update_info['url']}"
                        )
                        if response:
                            os.startfile(update_info['url'])
                    self.root.after(0, show_update)
            except:
                pass
        
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def t(self, key):
        """Get translation"""
        return self.texts.get(key, key)
    
    def create_ui(self):
        """Create main UI"""
        # Ana tabview
        self.tabview = ctk.CTkTabview(self.root, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Tabları ekle
        self.tabview.add(self.t('tab_process'))
        self.tabview.add(self.t('tab_videos'))
        self.tabview.add(self.t('tab_clips'))
        self.tabview.add(self.t('tab_settings'))
        
        # Tab içeriklerini oluştur
        self.create_process_tab()
        self.create_videos_tab()
        self.create_clips_tab()
        self.create_settings_tab()
    
    def create_process_tab(self):
        """Process tab"""
        tab = self.tabview.tab(self.t('tab_process'))
        
        # Sol panel - Log
        left_frame = ctk.CTkFrame(tab, corner_radius=15)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Başlık
        title_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(title_frame, text=self.t('process_history'), 
                    font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        # Kontrol butonları
        button_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_btn = ctk.CTkButton(button_frame, text=self.t('start_processing'),
                                       command=self.start_processing,
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       height=40, corner_radius=10,
                                       fg_color="#4CAF50", hover_color="#45a049")
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(button_frame, text=self.t('stop'),
                                      command=self.stop_processing,
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      height=40, corner_radius=10,
                                      fg_color="#f44336", hover_color="#da190b",
                                      state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # İlerleme
        progress_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress_label = ctk.CTkLabel(progress_frame, text=self.t('ready'),
                                          font=ctk.CTkFont(size=12))
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=20, corner_radius=10)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        # Log alanı
        self.log_text = ctk.CTkTextbox(left_frame, font=ctk.CTkFont(family="Consolas", size=11),
                                       corner_radius=10, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # Sağ panel - Preview
        right_frame = ctk.CTkFrame(tab, corner_radius=15, width=450)
        right_frame.pack(side="right", fill="both", padx=(10, 0))
        right_frame.pack_propagate(False)
        
        ctk.CTkLabel(right_frame, text=self.t('preview_title'),
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        # Preview container
        preview_container = ctk.CTkFrame(right_frame, corner_radius=10)
        preview_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.preview_label = ctk.CTkLabel(preview_container, text="",
                                         font=ctk.CTkFont(size=12))
        self.preview_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.preview_label.configure(text=self.t('preview_waiting'))
    
    def create_videos_tab(self):
        """Videos tab"""
        tab = self.tabview.tab(self.t('tab_videos'))
        
        # Üst panel
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_frame, text=self.t('videos_title'),
                    font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.pack(side="right")
        
        ctk.CTkButton(button_frame, text="➕ " + self.t('add_videos'), command=self.add_videos_dialog,
                     width=140, height=35, corner_radius=10).pack(side="left", padx=5)
        
        ctk.CTkButton(button_frame, text=self.t('refresh'), command=self.refresh_videos,
                     width=120, height=35, corner_radius=10).pack(side="left", padx=5)
        
        ctk.CTkButton(button_frame, text=self.t('open_folder'), command=self.open_input_folder,
                     width=140, height=35, corner_radius=10).pack(side="left")
        
        # Video kartları container
        self.videos_scroll = ctk.CTkScrollableFrame(tab, corner_radius=10)
        self.videos_scroll.pack(fill="both", expand=True)
        
        self.refresh_videos()
    
    def create_clips_tab(self):
        """Clips tab"""
        tab = self.tabview.tab(self.t('tab_clips'))
        
        # Üst panel
        top_frame = ctk.CTkFrame(tab, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_frame, text=self.t('clips_title'),
                    font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.pack(side="right")
        
        ctk.CTkButton(button_frame, text=self.t('refresh'), command=self.refresh_clips,
                     width=120, height=35, corner_radius=10).pack(side="left", padx=5)
        
        ctk.CTkButton(button_frame, text=self.t('open_folder'), command=self.open_output_folder,
                     width=140, height=35, corner_radius=10).pack(side="left")
        
        # Klip kartları container
        self.clips_scroll = ctk.CTkScrollableFrame(tab, corner_radius=10)
        self.clips_scroll.pack(fill="both", expand=True)
        
        self.refresh_clips()
    
    def create_settings_tab(self):
        """Settings tab"""
        tab = self.tabview.tab(self.t('tab_settings'))
        
        # Üst panel - Save butonu ve Version
        top_frame = ctk.CTkFrame(tab, fg_color="transparent", height=60)
        top_frame.pack(fill="x", pady=(0, 10))
        top_frame.pack_propagate(False)
        
        ctk.CTkLabel(top_frame, text=self.t('tab_settings'),
                    font=ctk.CTkFont(size=20, weight="bold")).pack(side="left", padx=20)
        
        # Version bilgisi
        version_info = f"v{self.config.get('APP_VERSION', '1.0.0')}"
        update_check = check_for_updates()
        if update_check.get('has_update'):
            version_label = ctk.CTkLabel(top_frame, 
                                        text=f"🔄 New update available: v{update_check['version']}",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color="#FFA726")
        else:
            version_label = ctk.CTkLabel(top_frame,
                                        text=f"✓ {version_info}",
                                        font=ctk.CTkFont(size=12),
                                        text_color="gray60")
        version_label.pack(side="right", padx=20)
        
        ctk.CTkButton(top_frame, text=self.t('save_settings'),
                     command=self.save_settings,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     width=180, height=40, corner_radius=10,
                     fg_color="#4CAF50", hover_color="#45a049").pack(side="right", padx=20)
        
        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(tab, corner_radius=10)
        scroll.pack(fill="both", expand=True)
        
        self.setting_vars = {}
        
        settings_groups = [
            (self.t('settings_general'), [
                ('LANGUAGE', self.t('language'), 'choice'),
            ]),
            (self.t('settings_detection'), [
                ('THRESHOLD', self.t('threshold'), 'float'),
                ('FRAME_SKIP', self.t('frame_skip'), 'int'),
                ('KILL_COOLDOWN', self.t('kill_cooldown'), 'float'),
            ]),
            (self.t('settings_buffer'), [
                ('BUFFER_BEFORE', self.t('buffer_before'), 'float'),
                ('BUFFER_AFTER', self.t('buffer_after'), 'float'),
                ('MIN_KILL_GAP', self.t('min_kill_gap'), 'float'),
            ]),
            (self.t('settings_roi'), [
                ('USE_ROI', self.t('use_roi'), 'bool'),
                ('ROI_X_START', self.t('roi_x_start'), 'float'),
                ('ROI_Y_START', self.t('roi_y_start'), 'float'),
                ('ROI_X_END', self.t('roi_x_end'), 'float'),
                ('ROI_Y_END', self.t('roi_y_end'), 'float'),
            ]),
            (self.t('settings_filter'), [
                ('USE_EDGE_DETECTION', self.t('use_edge'), 'bool'),
                ('USE_COLOR_FILTER', self.t('use_color'), 'bool'),
                ('KILL_COLOR_LOWER', 'Red Color Range 1 (HSV Lower)', 'color_hsv'),
                ('KILL_COLOR_UPPER', 'Red Color Range 1 (HSV Upper)', 'color_hsv'),
                ('KILL_COLOR_LOWER2', 'Red Color Range 2 (HSV Lower)', 'color_hsv'),
                ('KILL_COLOR_UPPER2', 'Red Color Range 2 (HSV Upper)', 'color_hsv'),
                ('CANNY_THRESHOLD1', self.t('canny_threshold1'), 'int'),
                ('CANNY_THRESHOLD2', self.t('canny_threshold2'), 'int'),
                ('MIN_COLOR_PIXELS', self.t('min_color_pixels'), 'int'),
            ]),
        ]
        
        for group_name, settings in settings_groups:
            # Grup başlığı
            group_frame = ctk.CTkFrame(scroll, corner_radius=10, fg_color=("gray90", "gray20"))
            group_frame.pack(fill="x", padx=10, pady=(20, 10))
            
            ctk.CTkLabel(group_frame, text=group_name,
                        font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=15)
            
            # ROI ayarları için özel layout
            if group_name == self.t('settings_roi'):
                roi_container = ctk.CTkFrame(scroll, fg_color="transparent")
                roi_container.pack(fill="x", padx=10, pady=10)
                
                # Sol - ayarlar
                roi_left = ctk.CTkFrame(roi_container, fg_color="transparent")
                roi_left.pack(side="left", fill="both", expand=True, padx=(20, 10))
                
                for key, label, type_ in settings:
                    setting_row = ctk.CTkFrame(roi_left, fg_color="transparent")
                    setting_row.pack(fill="x", pady=12)
                    
                    if type_ == 'bool':
                        var = ctk.BooleanVar(value=self.config.get(key, False))
                        
                        ctk.CTkLabel(setting_row, text=label,
                                   font=ctk.CTkFont(size=13),
                                   width=250, anchor="w").pack(side="left", padx=(0, 20))
                        
                        switch = ctk.CTkSwitch(setting_row, text="", variable=var,
                                              width=60, height=28,
                                              command=self.update_roi_preview)
                        switch.pack(side="left")
                        self.setting_vars[key] = (var, type_)
                    else:
                        # Float değerler için slider
                        var = ctk.DoubleVar(value=float(self.config.get(key, 0.0)))
                        
                        # Label ve değer göstergesi
                        label_frame = ctk.CTkFrame(setting_row, fg_color="transparent")
                        label_frame.pack(fill="x")
                        
                        ctk.CTkLabel(label_frame, text=label,
                                   font=ctk.CTkFont(size=13),
                                   anchor="w").pack(side="left")
                        
                        value_label = ctk.CTkLabel(label_frame, text=f"{var.get():.2f}",
                                                  font=ctk.CTkFont(size=12),
                                                  text_color="#4CAF50")
                        value_label.pack(side="right")
                        
                        # Slider
                        slider = ctk.CTkSlider(setting_row, from_=0.0, to=1.0,
                                             variable=var,
                                             width=300, height=20,
                                             command=lambda val, lbl=value_label: [
                                                 lbl.configure(text=f"{val:.2f}"),
                                                 self.update_roi_preview()
                                             ])
                        slider.pack(fill="x", pady=(5, 0))
                        
                        self.setting_vars[key] = (var, type_)
                
                # Sağ - ROI önizleme
                roi_right = ctk.CTkFrame(roi_container, corner_radius=10, width=500, height=300)
                roi_right.pack(side="right", padx=(10, 20))
                roi_right.pack_propagate(False)
                
                ctk.CTkLabel(roi_right, text=self.t('roi_preview'),
                           font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
                
                # Önizleme için label
                self.roi_preview_label = ctk.CTkLabel(roi_right, text="")
                self.roi_preview_label.pack(padx=10, pady=10)
                
                self.update_roi_preview()
                continue
            
            # Diğer ayarlar
            for key, label, type_ in settings:
                setting_row = ctk.CTkFrame(scroll, fg_color="transparent")
                setting_row.pack(fill="x", padx=30, pady=8)
                
                ctk.CTkLabel(setting_row, text=label,
                           font=ctk.CTkFont(size=13),
                           width=300, anchor="w").pack(side="left", padx=(0, 20))
                
                if type_ == 'bool':
                    var = ctk.BooleanVar(value=self.config.get(key, False))
                    switch = ctk.CTkSwitch(setting_row, text="", variable=var,
                                          width=60, height=28)
                    switch.pack(side="left")
                elif type_ == 'choice':
                    var = ctk.StringVar(value=str(self.config.get(key, 'tr')))
                    combo = ctk.CTkOptionMenu(setting_row, variable=var,
                                              values=["tr", "en"],
                                              width=150, height=35, corner_radius=8,
                                              command=self.change_language)
                    combo.pack(side="left")
                elif type_ == 'color_hsv':
                    # HSV renk değerlerini göster
                    hsv_values = self.config.get(key, [0, 0, 0])
                    var = ctk.StringVar(value=str(hsv_values))
                    
                    # Renk örneği (HSV -> RGB dönüştürüp göster)
                    try:
                        import numpy as np
                        hsv_color = np.uint8([[[hsv_values[0], hsv_values[1], hsv_values[2]]]])
                        rgb_color = cv2.cvtColor(hsv_color, cv2.COLOR_HSV2RGB)[0][0]
                        color_hex = f"#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}"
                        
                        color_preview = ctk.CTkLabel(setting_row, text="  ", width=40, height=30,
                                                   fg_color=color_hex, corner_radius=5)
                        color_preview.pack(side="left", padx=5)
                    except:
                        pass
                    
                    entry = ctk.CTkEntry(setting_row, textvariable=var,
                                        width=200, height=35, corner_radius=8,
                                        font=ctk.CTkFont(size=11))
                    entry.pack(side="left")
                else:
                    var = ctk.StringVar(value=str(self.config.get(key, '')))
                    entry = ctk.CTkEntry(setting_row, textvariable=var,
                                        width=150, height=35, corner_radius=8,
                                        font=ctk.CTkFont(size=13))
                    entry.pack(side="left")
                
                self.setting_vars[key] = (var, type_)
    
    def update_roi_preview(self):
        """Show ROI preview on example.jpg"""
        if not hasattr(self, 'roi_preview_label'):  
            return
        
        try:
            # example.jpg'yi yükle
            img_path = Path(get_resource_path('req/roi/example.jpg'))
            if not img_path.exists():
                return
            
            # Ayarları al
            x_start = float(self.setting_vars.get('ROI_X_START', (ctk.DoubleVar(value=0.72), 'float'))[0].get())
            y_start = float(self.setting_vars.get('ROI_Y_START', (ctk.DoubleVar(value=0.02), 'float'))[0].get())
            x_end = float(self.setting_vars.get('ROI_X_END', (ctk.DoubleVar(value=0.98), 'float'))[0].get())
            y_end = float(self.setting_vars.get('ROI_Y_END', (ctk.DoubleVar(value=0.28), 'float'))[0].get())
            
            # Resmi aç
            img = Image.open(img_path)
            img_width, img_height = img.size
            
            # Önizleme boyutu - en fazla 480x270
            max_width = 480
            max_height = 270
            scale = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Resmi yeniden boyutlandır
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # ROI koordinatlarını hesapla
            roi_x1 = int(x_start * new_width)
            roi_y1 = int(y_start * new_height)
            roi_x2 = int(x_end * new_width)
            roi_y2 = int(y_end * new_height)
            
            # Resmin üzerine ROI çerçevesi çiz
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # ROI dışı alanları karart (yarı saydam overlay)
            # Üst
            if roi_y1 > 0:
                draw.rectangle([0, 0, new_width, roi_y1], fill=(0, 0, 0, 150))
            # Alt
            if roi_y2 < new_height:
                draw.rectangle([0, roi_y2, new_width, new_height], fill=(0, 0, 0, 150))
            # Sol
            if roi_x1 > 0:
                draw.rectangle([0, roi_y1, roi_x1, roi_y2], fill=(0, 0, 0, 150))
            # Sağ
            if roi_x2 < new_width:
                draw.rectangle([roi_x2, roi_y1, new_width, roi_y2], fill=(0, 0, 0, 150))
            
            # Kırmızı çerçeve - kalın
            for i in range(4):
                draw.rectangle([roi_x1-i, roi_y1-i, roi_x2+i, roi_y2+i], 
                              outline=(255, 51, 51, 255), width=1)
            
            # Köşe işaretleri
            corner_size = 20
            corner_width = 3
            corner_color = (255, 51, 51, 255)
            
            # Sol üst
            draw.line([roi_x1, roi_y1, roi_x1+corner_size, roi_y1], 
                     fill=corner_color, width=corner_width)
            draw.line([roi_x1, roi_y1, roi_x1, roi_y1+corner_size], 
                     fill=corner_color, width=corner_width)
            
            # Sağ üst
            draw.line([roi_x2, roi_y1, roi_x2-corner_size, roi_y1], 
                     fill=corner_color, width=corner_width)
            draw.line([roi_x2, roi_y1, roi_x2, roi_y1+corner_size], 
                     fill=corner_color, width=corner_width)
            
            # Sol alt
            draw.line([roi_x1, roi_y2, roi_x1+corner_size, roi_y2], 
                     fill=corner_color, width=corner_width)
            draw.line([roi_x1, roi_y2, roi_x1, roi_y2-corner_size], 
                     fill=corner_color, width=corner_width)
            
            # Sağ alt
            draw.line([roi_x2, roi_y2, roi_x2-corner_size, roi_y2], 
                     fill=corner_color, width=corner_width)
            draw.line([roi_x2, roi_y2, roi_x2, roi_y2-corner_size], 
                     fill=corner_color, width=corner_width)
            
            # CTkImage'e çevir ve göster
            ctk_image = ctk.CTkImage(light_image=img, dark_image=img, 
                                     size=(new_width, new_height))
            self.roi_preview_label.configure(image=ctk_image)
            self.roi_preview_label.image = ctk_image  # Referansı tut
            
        except Exception as e:
            print(f"ROI preview error: {e}")
    
    def change_language(self, lang):
        """Change language"""
        self.current_lang = lang
        self.texts = LANGUAGES.get(lang, LANGUAGES['tr'])
        messagebox.showinfo(self.t('success_title'), 
                           "Please restart the application to apply language changes.\n\nUygulamayı yeniden başlatın.")
    
    def save_settings(self):
        """Save settings"""
        try:
            for key, (var, type_) in self.setting_vars.items():
                if type_ == 'bool':
                    self.config[key] = var.get()
                elif type_ == 'int':
                    self.config[key] = int(var.get())
                elif type_ == 'float':
                    self.config[key] = float(var.get())
                elif type_ == 'color_hsv':
                    # String'i list'e dönüştür: "[0, 120, 80]" -> [0, 120, 80]
                    import ast
                    self.config[key] = ast.literal_eval(var.get())
                else:
                    self.config[key] = var.get()
            
            self.save_config()
            messagebox.showinfo(self.t('success_title'), self.t('settings_saved'))
        except Exception as e:
            messagebox.showerror("Error / Hata", f"Settings could not be saved / Ayarlar kaydedilemedi: {e}")
    
    def get_video_thumbnail(self, video_path, size=(120, 68)):
        """Extract thumbnail from video"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            # Get middle frame
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to thumbnail size
                img = Image.fromarray(frame_rgb)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except:
            pass
        return None
    
    def refresh_videos(self):
        """Refresh video list"""
        # Eski kartları temizle
        for widget in self.videos_scroll.winfo_children():
            widget.destroy()
        
        input_folder = Path(self.config['INPUT_FOLDER'])
        if not input_folder.exists():
            ctk.CTkLabel(self.videos_scroll, 
                        text=self.t('no_videos'),
                        font=ctk.CTkFont(size=14)).pack(pady=50)
            return
        
        # İşlenmiş videoları oku
        processed = set()
        processed_log_path = get_data_path('req/jsons/processed_videos.json')
        if os.path.exists(processed_log_path):
            try:
                with open(processed_log_path, 'r', encoding='utf-8') as f:
                    processed = set(json.load(f).keys())
            except:
                pass
        
        videos = []
        for ext in VIDEO_EXTENSIONS:
            videos.extend(input_folder.glob(f'*{ext}'))
        videos = sorted(videos)
        if not videos:
            ctk.CTkLabel(self.videos_scroll,
                        text=self.t('no_videos'),
                        font=ctk.CTkFont(size=14)).pack(pady=50)
            return
        
        # Video kartları
        for video_file in sorted(videos):
            is_processed = video_file.name in processed
            size = video_file.stat().st_size / (1024*1024)  # MB
            
            card = ctk.CTkFrame(self.videos_scroll, corner_radius=10,
                               fg_color=("gray85", "gray25") if is_processed else ("gray90", "gray20"))
            card.pack(fill="x", padx=10, pady=8)
            
            # Sağ tık menüsü ekle
            video_name = video_file.name
            card.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            # İçerik
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=15)
            
            # Sağ tık menüsünü content'e de ekle
            content.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            # Thumbnail (sol)
            thumbnail = self.get_video_thumbnail(video_file)
            if thumbnail:
                thumb_label = ctk.CTkLabel(content, image=thumbnail, text="")
                thumb_label.pack(side="left", padx=(0, 15))
                thumb_label.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            # Bilgi (orta)
            info_frame = ctk.CTkFrame(content, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            info_frame.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            name_label = ctk.CTkLabel(info_frame, text=video_file.name,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        anchor="w")
            name_label.pack(anchor="w")
            name_label.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            size_label = ctk.CTkLabel(info_frame, text=f"💾 {size:.1f} MB",
                        font=ctk.CTkFont(size=12),
                        text_color="gray60")
            size_label.pack(anchor="w", pady=(5, 0))
            size_label.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
            
            # Sağ - durum
            status_text = self.t('processed') if is_processed else self.t('waiting')
            status_color = "#4CAF50" if is_processed else "#FFA726"
            
            status_label = ctk.CTkLabel(content, text=status_text,
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color=status_color)
            status_label.pack(side="right")
            status_label.bind("<Button-3>", lambda e, vn=video_name, ip=is_processed: self.show_video_context_menu(e, vn, ip))
    
    def refresh_clips(self):
        """Refresh clip list"""
        # Eski kartları temizle
        for widget in self.clips_scroll.winfo_children():
            widget.destroy()
        
        output_folder = Path(self.config['OUTPUT_FOLDER'])
        if not output_folder.exists():
            ctk.CTkLabel(self.clips_scroll,
                        text=self.t('no_clips'),
                        font=ctk.CTkFont(size=14)).pack(pady=50)
            return
        
        clips = []
        for ext in VIDEO_EXTENSIONS:
            clips.extend(output_folder.glob(f'*{ext}'))
        clips = sorted(clips, key=lambda x: x.stat().st_mtime, reverse=True)
        if not clips:
            ctk.CTkLabel(self.clips_scroll,
                        text=self.t('no_clips'),
                        font=ctk.CTkFont(size=14)).pack(pady=50)
            return
        
        # Klip kartları
        for clip_file in clips:
            size = clip_file.stat().st_size / (1024*1024)  # MB
            source = clip_file.stem.rsplit('_kill_', 1)[0] if '_kill_' in clip_file.stem else "Bilinmiyor"
            
            card = ctk.CTkFrame(self.clips_scroll, corner_radius=10,
                               fg_color=("gray90", "gray20"))
            card.pack(fill="x", padx=10, pady=8)
            
            # İçerik
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=20, pady=15)
            
            # Thumbnail (sol)
            thumbnail = self.get_video_thumbnail(clip_file)
            if thumbnail:
                thumb_label = ctk.CTkLabel(content, image=thumbnail, text="")
                thumb_label.pack(side="left", padx=(0, 15))
            
            # Bilgi (orta)
            info_frame = ctk.CTkFrame(content, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            
            ctk.CTkLabel(info_frame, text=clip_file.name,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        anchor="w").pack(anchor="w")
            
            details_text = f"💾 {size:.1f} MB  •  📹 {source}"
            ctk.CTkLabel(info_frame, text=details_text,
                        font=ctk.CTkFont(size=12),
                        text_color="gray60").pack(anchor="w", pady=(5, 0))
            
            # Sağ - butonlar
            button_frame = ctk.CTkFrame(content, fg_color="transparent")
            button_frame.pack(side="right")
            
            play_btn = ctk.CTkButton(button_frame, text=self.t('play'),
                                    command=lambda f=clip_file: self.play_clip(f),
                                    width=100, height=35, corner_radius=8,
                                    fg_color="#2196F3", hover_color="#1976D2")
            play_btn.pack(side="left", padx=5)
            
            delete_btn = ctk.CTkButton(button_frame, text="🗑️",
                                      command=lambda f=clip_file: self.delete_clip(f),
                                      width=50, height=35, corner_radius=8,
                                      fg_color="#f44336", hover_color="#da190b")
            delete_btn.pack(side="left")
    
    def play_clip(self, filepath):
        """Play clip"""
        if filepath.exists():
            os.startfile(str(filepath))
    
    def delete_clip(self, filepath):
        """Delete clip"""
        if messagebox.askyesno("Delete / Sil", f"Are you sure you want to delete this clip?\nBu klipi silmek istediğinizden emin misiniz?\n\n{filepath.name}"):
            try:
                filepath.unlink()
                messagebox.showinfo("Success / Başarılı", "Clip deleted successfully!\nKlip başarıyla silindi!")
                # Run refresh in background thread to avoid UI freeze
                refresh_thread = threading.Thread(target=self.refresh_clips, daemon=True)
                refresh_thread.start()
            except Exception as e:
                messagebox.showerror("Error / Hata", f"Could not delete clip / Klip silinemedi: {e}")
    
    def toggle_video_processed(self, video_name, mark_as_processed):
        """Toggle video processed status"""
        processed_log_path = get_data_path('req/jsons/processed_videos.json')
        
        # Load current processed videos
        processed = {}
        if os.path.exists(processed_log_path):
            try:
                with open(processed_log_path, 'r', encoding='utf-8') as f:
                    processed = json.load(f)
            except:
                pass
        
        # Update status
        if mark_as_processed:
            # Mark as processed
            processed[video_name] = {
                'clips_count': 0,
                'processed_date': None,
                'manually_marked': True
            }
            message = f"Video marked as processed!\nVideo işlenmiş olarak işaretlendi!\n\n{video_name}"
        else:
            # Mark as not processed
            if video_name in processed:
                del processed[video_name]
            message = f"Video marked as not processed!\nVideo işlenmemiş olarak işaretlendi!\n\n{video_name}"
        
        # Save
        try:
            os.makedirs(os.path.dirname(processed_log_path), exist_ok=True)
            with open(processed_log_path, 'w', encoding='utf-8') as f:
                json.dump(processed, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success / Başarılı", message)
            self.refresh_videos()
        except Exception as e:
            messagebox.showerror("Error / Hata", f"Could not update status / Durum güncellenemedi: {e}")
    
    def show_video_context_menu(self, event, video_name, is_processed):
        """Show right-click context menu for video"""
        menu = Menu(self.root, tearoff=0,
                   bg="#2B2B2B",  # Dark background
                   fg="white",  # White text
                   activebackground="#1F538D",  # Blue hover
                   activeforeground="white",
                   font=("Segoe UI", 10),
                   borderwidth=1,
                   relief="solid")
        
        if is_processed:
            menu.add_command(label="❌ İşlenmemiş Olarak İşaretle / Mark as Not Processed",
                           command=lambda: self.toggle_video_processed(video_name, False))
        else:
            menu.add_command(label="✅ İşlenmiş Olarak İşaretle / Mark as Processed",
                           command=lambda: self.toggle_video_processed(video_name, True))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def add_videos_dialog(self):
        """Open file dialog to add videos"""
        filetypes = [("Video files", " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS)), ("All files", "*.*")]
        files = filedialog.askopenfilenames(title="Select videos to add / Eklenecek videoları seçin", 
                                           filetypes=filetypes)
        
        if not files:
            return
        
        input_folder = Path(self.config['INPUT_FOLDER'])
        input_folder.mkdir(exist_ok=True)
        
        moved_count = 0
        skipped_count = 0
        
        for file_path in files:
            file_path = Path(file_path)
            dest = input_folder / file_path.name
            
            # Check if already exists
            if dest.exists():
                skipped_count += 1
                continue
            
            try:
                # Move file to input folder
                shutil.move(str(file_path), str(dest))
                moved_count += 1
            except Exception as e:
                print(f"Error moving {file_path}: {e}")
        
        if moved_count > 0:
            msg = f"✓ {moved_count} video(s) moved to input folder!\n✓ {moved_count} video taşındı!"
            if skipped_count > 0:
                msg += f"\n\n⏭ {skipped_count} already existed (skipped)\n⏭ {skipped_count} zaten vardı (atlandı)"
            messagebox.showinfo("Success / Başarılı", msg)
            self.refresh_videos()
        elif skipped_count > 0:
            messagebox.showinfo("Info / Bilgi",
                              f"All {skipped_count} videos already exist!\n"
                              f"Tüm {skipped_count} video zaten mevcut!")
    
    def open_input_folder(self):
        """Open input folder"""
        folder = self.config['INPUT_FOLDER']
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)
    
    def open_output_folder(self):
        """Open output folder"""
        folder = self.config['OUTPUT_FOLDER']
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)
    
    def start_processing(self):
        """Start processing"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        
        # main.py'yi thread'de çalıştır
        self.process_thread = threading.Thread(target=self.run_processor, daemon=True)
        self.process_thread.start()
    
    def stop_processing(self):
        """Stop processing"""
        self.is_processing = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.add_log("⚠️ İşlem durduruldu", "warning")
    
    def run_processor(self):
        """Run main.py"""
        try:
            import main
            main.run_with_gui(self)
        except Exception as e:
            self.add_log(f"❌ Hata: {e}", "error")
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.start_btn.configure(state="normal"))
            self.root.after(0, lambda: self.stop_btn.configure(state="disabled"))
    
    def add_log(self, message, level='info'):
        """Add log message (thread-safe)"""
        self.log_queue.put((message, level))
    
    def update_progress(self, current, total, text=""):
        """Update progress (thread-safe)"""
        self.progress_queue.put((current, total, text))
    
    def update_preview(self, frame):
        """Update preview (thread-safe)"""
        self.preview_queue.put(frame)
    
    def check_queues(self):
        """Check queues and update GUI"""
        # Log queue
        try:
            while True:
                message, level = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")  # Geçici olarak düzenlenebilir yap
                self.log_text.insert("end", message + '\n')
                self.log_text.see("end")
                self.log_text.configure(state="disabled")  # Tekrar readonly yap
        except queue.Empty:
            pass
        
        # Progress queue
        try:
            current, total, text = self.progress_queue.get_nowait()
            if total > 0:
                progress = current / total
                self.progress_bar.set(progress)
                self.progress_label.configure(text=f"{text} ({current}/{total}) - %{progress*100:.1f}")
        except queue.Empty:
            pass
        
        # Preview queue
        try:
            frame = self.preview_queue.get_nowait()
            # OpenCV BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Resize
            h, w = frame_rgb.shape[:2]
            max_w, max_h = 410, 600
            scale = min(max_w/w, max_h/h)
            new_w, new_h = int(w*scale), int(h*scale)
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
            # PIL -> ImageTk
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            self.preview_label.configure(image=imgtk, text="")
            self.preview_label.image = imgtk
        except queue.Empty:
            pass
        
        # 100ms sonra tekrar kontrol et
        self.root.after(100, self.check_queues)

def run_gui():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    app = VideoProcessorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
