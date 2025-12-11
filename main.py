import cv2
import numpy as np
import subprocess
import os
import json
from pathlib import Path

# Global GUI reference
gui_instance = None

def load_config():
    """Load settings from config file"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        # Default values
        return {
            'INPUT_FOLDER': 'input_videos',
            'OUTPUT_FOLDER': 'kills',
            'TEMPLATE_PATH': 'killfeed_template.jpg',
            'THRESHOLD': 0.55,
            'BUFFER_BEFORE': 3.0,
            'BUFFER_AFTER': 2.0,
            'MIN_KILL_GAP': 2.0,
            'FRAME_SKIP': 120,
            'KILL_COOLDOWN': 2.0,
            'USE_EDGE_DETECTION': True,
            'USE_COLOR_FILTER': True,
            'USE_ROI': True,
            'ROI_X_START': 0.72,
            'ROI_Y_START': 0.02,
            'ROI_X_END': 0.98,
            'ROI_Y_END': 0.28,
            'KILL_COLOR_LOWER': [0, 120, 80],
            'KILL_COLOR_UPPER': [10, 255, 255],
            'KILL_COLOR_LOWER2': [170, 120, 80],
            'KILL_COLOR_UPPER2': [180, 255, 255],
            'MIN_COLOR_PIXELS': 150,
            'CANNY_THRESHOLD1': 150,
            'CANNY_THRESHOLD2': 250
        }

# Load configuration
config = load_config()

# Get settings from config
INPUT_FOLDER = config['INPUT_FOLDER']
OUTPUT_FOLDER = config['OUTPUT_FOLDER']
TEMPLATE_PATH = config['TEMPLATE_PATH']
PROCESSED_LOG = "processed_videos.json"
THRESHOLD = config['THRESHOLD']
BUFFER_BEFORE = config['BUFFER_BEFORE']
BUFFER_AFTER = config['BUFFER_AFTER']
MIN_KILL_GAP = config['MIN_KILL_GAP']
FRAME_SKIP = config['FRAME_SKIP']
KILL_COOLDOWN = config['KILL_COOLDOWN']
USE_EDGE_DETECTION = config['USE_EDGE_DETECTION']
USE_COLOR_FILTER = config['USE_COLOR_FILTER']
USE_ROI = config['USE_ROI']
ROI_X_START = config['ROI_X_START']
ROI_Y_START = config['ROI_Y_START']
ROI_X_END = config['ROI_X_END']
ROI_Y_END = config['ROI_Y_END']
KILL_COLOR_LOWER = np.array(config['KILL_COLOR_LOWER'])
KILL_COLOR_UPPER = np.array(config['KILL_COLOR_UPPER'])
KILL_COLOR_LOWER2 = np.array(config['KILL_COLOR_LOWER2'])
KILL_COLOR_UPPER2 = np.array(config['KILL_COLOR_UPPER2'])
MIN_COLOR_PIXELS = config['MIN_COLOR_PIXELS']
CANNY_THRESHOLD1 = config.get('CANNY_THRESHOLD1', 150)
CANNY_THRESHOLD2 = config.get('CANNY_THRESHOLD2', 250)
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

def log_message(message, level='info'):
    """Send log message to GUI"""
    if gui_instance:
        gui_instance.add_log(message, level)

def update_progress(current, total, text=""):
    """Update progress"""
    if gui_instance:
        gui_instance.update_progress(current, total, text)

def show_preview(frame):
    """Show preview"""
    if gui_instance:
        gui_instance.update_preview(frame)

def create_output_folder():
    """Create output folder"""
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
    log_message(f"✓ Çıktı klasörü hazır: {OUTPUT_FOLDER}", "success")

def load_processed_videos():
    """Load list of processed videos"""
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_processed_video(video_name, clips_count):
    """Save processed video to log"""
    processed = load_processed_videos()
    processed[video_name] = {
        'clips_count': clips_count,
        'processed_date': str(Path(video_name).stat().st_mtime) if os.path.exists(video_name) else None
    }
    with open(PROCESSED_LOG, 'w', encoding='utf-8') as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

def get_video_files(folder):
    """Find all video files in folder"""
    if not os.path.exists(folder):
        log_message(f"✓ Input klasörü oluşturuluyor: {folder}", "success")
        Path(folder).mkdir(exist_ok=True)
        return []
    
    processed_videos = load_processed_videos()
    video_files = []
    skipped_videos = []
    
    for file in os.listdir(folder):
        if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
            video_path = os.path.join(folder, file)
            
            # Check if already processed
            if file in processed_videos:
                skipped_videos.append(file)
            else:
                video_files.append(video_path)
    
    if skipped_videos:
        log_message(f"\n⏭️  {len(skipped_videos)} video zaten işlenmiş (atlanıyor):", "warning")
        for video in skipped_videos:
            log_message(f"   - {video}", "warning")
    
    return sorted(video_files)

def detect_kills_in_video(video_path, template_path):
    """Detect killfeeds in video"""
    log_message(f"\n{'='*60}", "info")
    log_message(f"📹 Video analiz ediliyor: {os.path.basename(video_path)}", "info")
    log_message(f"{'='*60}", "info")
    
    cap = cv2.VideoCapture(video_path)
    template = cv2.imread(template_path)
    
    if template is None:
        log_message(f"❌ HATA: Template bulunamadı: {template_path}", "error")
        return [], 0
    
    template_h, template_w = template.shape[:2]
    
    # Prepare for edge detection
    if USE_EDGE_DETECTION:
        template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        template_edges = cv2.Canny(template_gray, CANNY_THRESHOLD1, CANNY_THRESHOLD2)
        log_message(f"🔍 Tespit modu: Edge Detection (Canny {CANNY_THRESHOLD1}-{CANNY_THRESHOLD2})", "info")
    else:
        log_message(f"🔍 Tespit modu: Normal Template Matching", "info")
    
    if USE_COLOR_FILTER:
        log_message(f"🎨 Renk filtresi: AÇIK (sadece kırmızı çerçeveli killer)", "info")
    
    if USE_ROI:
        log_message(f"📍 ROI: AÇIK (sadece sağ üst köşe taranacak)", "info")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    # Calculate ROI coordinates
    if USE_ROI:
        roi_x1 = int(frame_width * ROI_X_START)
        roi_y1 = int(frame_height * ROI_Y_START)
        roi_x2 = int(frame_width * ROI_X_END)
        roi_y2 = int(frame_height * ROI_Y_END)
    
    log_message(f"📊 Video bilgileri:", "info")
    log_message(f"   - FPS: {fps:.2f}", "info")
    log_message(f"   - Süre: {duration:.2f} saniye", "info")
    log_message(f"   - Frame sayısı: {total_frames}", "info")
    log_message(f"   - Çözünürlük: {frame_width}x{frame_height}", "info")
    if USE_ROI:
        log_message(f"   - ROI bölgesi: [{roi_x1},{roi_y1}] -> [{roi_x2},{roi_y2}]", "info")
    log_message(f"   - Tarama hızı: {FRAME_SKIP}x (her {FRAME_SKIP} frame'de bir kontrol)", "info")
    log_message(f"   - Threshold: {THRESHOLD}", "info")
    log_message(f"\n🔍 Kill taraması başlıyor...", "info")
    
    kill_times = []
    frame_count = 0
    last_kill_print_time = -999
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        current_time = frame_count / fps
        
        # FRAME_SKIP kadar frame atla
        if frame_count % FRAME_SKIP != 0:
            continue
        
        # Show progress
        if frame_count % (50 * FRAME_SKIP) == 0:
            update_progress(frame_count, total_frames, f"Tarama: {current_time:.1f}s / {duration:.1f}s")
        
        # Use ROI (only check killfeed region)
        if USE_ROI:
            search_frame = frame[roi_y1:roi_y2, roi_x1:roi_x2]
        else:
            search_frame = frame
        
        # Template matching
        if USE_EDGE_DETECTION:
            frame_gray = cv2.cvtColor(search_frame, cv2.COLOR_BGR2GRAY)
            frame_edges = cv2.Canny(frame_gray, CANNY_THRESHOLD1, CANNY_THRESHOLD2)
            res = cv2.matchTemplate(frame_edges, template_edges, cv2.TM_CCOEFF_NORMED)
        else:
            res = cv2.matchTemplate(search_frame, template, cv2.TM_CCOEFF_NORMED)
        
        loc = np.where(res >= THRESHOLD)
        
        if len(loc[0]) > 0:
            # Killfeed found - now check red border
            for pt in zip(*loc[::-1]):
                # Adjust coordinates if using ROI
                if USE_ROI:
                    x, y = pt[0] + roi_x1, pt[1] + roi_y1
                else:
                    x, y = pt[0], pt[1]
                
                # Get killfeed region
                roi = frame[y:y+template_h, x:x+template_w]
                
                # Color filter - check border only (edges)
                if USE_COLOR_FILTER:
                    # Convert BGR to HSV
                    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    
                    # Find red pixels (two ranges)
                    mask1 = cv2.inRange(hsv_roi, KILL_COLOR_LOWER, KILL_COLOR_UPPER)
                    mask2 = cv2.inRange(hsv_roi, KILL_COLOR_LOWER2, KILL_COLOR_UPPER2)
                    mask = cv2.bitwise_or(mask1, mask2)
                    
                    color_pixel_count = cv2.countNonZero(mask)
                    
                    # Skip if not enough red pixels (enemy kill - gray border)
                    if color_pixel_count < MIN_COLOR_PIXELS:
                        continue
                
                # Valid kill
                if not kill_times or (current_time - kill_times[-1]) > 0.5:
                    kill_times.append(current_time)
                    
                    if current_time - last_kill_print_time > KILL_COOLDOWN:
                        color_info = f" (🔴 {color_pixel_count} red pixels)" if USE_COLOR_FILTER else ""
                        log_message(f"✓ Kill found: {current_time:.2f}s{color_info}", "success")
                        last_kill_print_time = current_time
                        
                        # Show preview - draw ROI rectangle
                        preview_frame = frame.copy()
                        if USE_ROI:
                            cv2.rectangle(preview_frame, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 255, 255), 2)
                        cv2.rectangle(preview_frame, (x, y), (x+template_w, y+template_h), (0, 0, 255), 3)
                        show_preview(preview_frame)
                
                break  # Got first match, continue
    
    cap.release()
    log_message(f"\n🎯 Toplam {len(kill_times)} kill tespit edildi!", "success")
    return kill_times, fps

def merge_close_kills(kill_times, min_gap):
    """Merge consecutive kills"""
    if not kill_times:
        return []
    
    merged = []
    current_start = kill_times[0]
    current_end = kill_times[0]
    
    for i in range(1, len(kill_times)):
        if kill_times[i] - current_end <= min_gap:
            # This kill is close to previous, merge
            current_end = kill_times[i]
        else:
            # Start new group
            merged.append((current_start, current_end))
            current_start = kill_times[i]
            current_end = kill_times[i]
    
    # Add last group
    merged.append((current_start, current_end))
    
    return merged

def extract_clips(video_path, kill_segments, fps, video_name):
    """Extract kill clips with FFmpeg"""
    log_message(f"\n✂️  {len(kill_segments)} clip çıkarılıyor...", "info")
    
    for i, (start_time, end_time) in enumerate(kill_segments, 1):
        # Add buffer
        clip_start = max(0, start_time - BUFFER_BEFORE)
        clip_end = end_time + BUFFER_AFTER
        
        # Add video name to filename
        base_name = os.path.splitext(video_name)[0]
        output_file = os.path.join(OUTPUT_FOLDER, f"{base_name}_kill_{i:03d}_{clip_start:.1f}s-{clip_end:.1f}s.mp4")
        
        # FFmpeg command - preserve all audio channels
        cmd = [
            'ffmpeg',
            '-ss', str(clip_start),  # Put -ss first (faster)
            '-i', video_path,
            '-to', str(clip_end - clip_start),  # Relative duration
            '-map', '0',  # Copy ALL streams (video + all audio channels)
            '-c', 'copy',  # Copy everything as-is
            '-avoid_negative_ts', 'make_zero',  # Fix video freeze/sync issues
            '-fflags', '+genpts',  # Regenerate timestamps
            '-y',  # Overwrite
            output_file
        ]
        
        log_message(f"📹 Clip {i}/{len(kill_segments)} çıkarılıyor: {clip_start:.1f}s - {clip_end:.1f}s", "info")
        update_progress(i, len(kill_segments), f"Clip çıkarma: {i}/{len(kill_segments)}")
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            log_message(f"✓ Kaydedildi: {os.path.basename(output_file)}", "success")
        else:
            log_message(f"❌ Hata: {os.path.basename(output_file)}", "error")
    
    log_message(f"\n✓ {len(kill_segments)} clip başarıyla kaydedildi!", "success")

def process_video(video_path, template_path):
    """Process single video"""
    video_name = os.path.basename(video_path)
    
    # Detect kills
    kill_times, fps = detect_kills_in_video(video_path, template_path)
    
    if not kill_times:
        log_message("⚠️  No kills found!", "warning")
        # Save anyway to avoid reprocessing
        save_processed_video(video_name, 0)
        return 0
    
    # Merge consecutive kills
    kill_segments = merge_close_kills(kill_times, MIN_KILL_GAP)
    log_message(f"🔗 {len(kill_times)} kills merged into {len(kill_segments)} segments", "info")
    
    # Extract clips
    extract_clips(video_path, kill_segments, fps, video_name)
    
    # Save as processed
    save_processed_video(video_name, len(kill_segments))
    
    return len(kill_segments)

def run_with_gui(gui):
    """Run with GUI"""
    global gui_instance, config, INPUT_FOLDER, OUTPUT_FOLDER, TEMPLATE_PATH
    global THRESHOLD, BUFFER_BEFORE, BUFFER_AFTER, MIN_KILL_GAP, FRAME_SKIP
    global KILL_COOLDOWN, USE_EDGE_DETECTION, USE_COLOR_FILTER, USE_ROI
    global ROI_X_START, ROI_Y_START, ROI_X_END, ROI_Y_END
    global KILL_COLOR_LOWER, KILL_COLOR_UPPER, KILL_COLOR_LOWER2, KILL_COLOR_UPPER2
    global MIN_COLOR_PIXELS, CANNY_THRESHOLD1, CANNY_THRESHOLD2
    
    gui_instance = gui
    
    # Reload config (settings may have changed)
    config = load_config()
    
    # Update global variables
    INPUT_FOLDER = config['INPUT_FOLDER']
    OUTPUT_FOLDER = config['OUTPUT_FOLDER']
    TEMPLATE_PATH = config['TEMPLATE_PATH']
    THRESHOLD = config['THRESHOLD']
    BUFFER_BEFORE = config['BUFFER_BEFORE']
    BUFFER_AFTER = config['BUFFER_AFTER']
    MIN_KILL_GAP = config['MIN_KILL_GAP']
    FRAME_SKIP = config['FRAME_SKIP']
    KILL_COOLDOWN = config['KILL_COOLDOWN']
    USE_EDGE_DETECTION = config['USE_EDGE_DETECTION']
    USE_COLOR_FILTER = config['USE_COLOR_FILTER']
    USE_ROI = config['USE_ROI']
    ROI_X_START = config['ROI_X_START']
    ROI_Y_START = config['ROI_Y_START']
    ROI_X_END = config['ROI_X_END']
    ROI_Y_END = config['ROI_Y_END']
    KILL_COLOR_LOWER = np.array(config['KILL_COLOR_LOWER'])
    KILL_COLOR_UPPER = np.array(config['KILL_COLOR_UPPER'])
    KILL_COLOR_LOWER2 = np.array(config['KILL_COLOR_LOWER2'])
    KILL_COLOR_UPPER2 = np.array(config['KILL_COLOR_UPPER2'])
    MIN_COLOR_PIXELS = config['MIN_COLOR_PIXELS']
    CANNY_THRESHOLD1 = config.get('CANNY_THRESHOLD1', 150)
    CANNY_THRESHOLD2 = config.get('CANNY_THRESHOLD2', 250)
    
    # Start processing
    log_message("\n" + "="*60, "info")
    log_message("🎮 FPS AUTO EDITOR - KILL CLIP EXTRACTOR", "info")
    log_message("="*60, "info")
    
    create_output_folder()
    video_files = get_video_files(INPUT_FOLDER)
    
    if not video_files:
        log_message(f"\n⚠️  '{INPUT_FOLDER}' klasöründe video bulunamadı!", "warning")
        log_message(f"📁 Desteklenen formatlar: {', '.join(VIDEO_EXTENSIONS)}", "info")
        log_message(f"💡 Video dosyalarını '{INPUT_FOLDER}' klasörüne atın ve tekrar çalıştırın.", "info")
        gui_instance.root.after(0, gui_instance.refresh_videos)
        return
    
    log_message(f"\n📁 {len(video_files)} video bulundu:", "info")
    for i, video in enumerate(video_files, 1):
        log_message(f"   {i}. {os.path.basename(video)}", "info")
    
    # Process each video
    total_clips = 0
    for i, video_path in enumerate(video_files, 1):
        log_message(f"\n{'='*60}", "info")
        log_message(f"🎬 Video {i}/{len(video_files)} işleniyor...", "info")
        log_message(f"{'='*60}", "info")
        update_progress(i-1, len(video_files), f"Video {i}/{len(video_files)}")
        
        clips_count = process_video(video_path, TEMPLATE_PATH)
        total_clips += clips_count
    
    # Summary
    log_message(f"\n{'='*60}", "info")
    log_message(f"✅ İŞLEM TAMAMLANDI!", "success")
    log_message(f"{'='*60}", "info")
    log_message(f"📊 Özet:", "info")
    log_message(f"   - İşlenen video: {len(video_files)}", "info")
    log_message(f"   - Toplam clip: {total_clips}", "info")
    log_message(f"   - Çıktı klasörü: {OUTPUT_FOLDER}", "info")
    log_message(f"{'='*60}\n", "info")
    update_progress(len(video_files), len(video_files), "Completed!")
    
    # Refresh GUI
    gui_instance.root.after(0, gui_instance.refresh_videos)
    gui_instance.root.after(0, gui_instance.refresh_clips)