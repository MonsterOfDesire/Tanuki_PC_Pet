import os
import sys
import random
import math
import time
import json
import re

# --- 環境路徑初始化 ---
def get_base_path():
    # 判定程式是純 py 執行還是被 Nuitka 編譯後的環境
    if "__compiled__" in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, QPoint, QSize, QTimer, QPropertyAnimation, QRect, QObject, QEasingCurve, QVariantAnimation, \
    pyqtSignal
from PyQt6.QtGui import QMovie, QPainter, QColor, QPixmap, QImage
from pynput import mouse

def check_assets_integrity(required_folders):
    assets_dir = AssetManager.get_resource_path("assets_cropped")
    missing = []
    for folder in required_folders:
        path = os.path.join(assets_dir, folder)
        if not os.path.exists(path):
            missing.append(folder)
    if missing:
        msg = f"偵測到關鍵素材缺失：\n{', '.join(missing)}\n\n請確保 assets_cropped 資料夾完整！"
        QMessageBox.critical(None, "系統錯誤", msg)
        sys.exit()

def get_total_virtual_geometry():
    rect = QRect()
    for screen in QApplication.screens():
        rect = rect.united(screen.geometry())
    return rect

class GlobalMouseListener(QObject):
    request_slide_out = pyqtSignal()
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.request_slide_out.connect(self.dashboard.slide_out, Qt.ConnectionType.QueuedConnection)
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()
    def on_click(self, x, y, button, pressed):
        if pressed and self.dashboard.is_expanded:
            ratio = self.dashboard.devicePixelRatio()
            logic_point = QPoint(int(x / ratio), int(y / ratio))
            if not self.dashboard.geometry().contains(logic_point):
                self.request_slide_out.emit()

class AssetManager:
    """
    負責解析檔名、載入 GIF 幀、縮放並快取素材。
    檔名規則解析：purpose_action-mood.gif (例如: move_walk-happy.gif)
    """
    def __init__(self, character_path, scale_factor=0.4):
        self.character_path = character_path
        self.scale_factor = scale_factor
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = {}
        self.refresh_assets()

    def load_manifest(self):
        manifest_path = os.path.join(self.character_path, "manifest_edit.json")
        if not os.path.exists(manifest_path):
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw = f.read()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                sanitized = re.sub(r",(\s*[}\]])", r"\1", raw)
                data = json.loads(sanitized)
            manifest = {}
            for file_name, meta in data.items():
                if isinstance(meta, dict):
                    manifest[file_name] = self.normalize_manifest_entry(meta)
            return manifest
        except Exception as e:
            print(f"讀取 manifest 失敗 {manifest_path}: {e}")
            return {}

    def normalize_manifest_entry(self, meta):
        bands = []
        for raw_band in meta.get("band", []):
            if not isinstance(raw_band, str):
                continue
            normalized = raw_band.replace(".", ",")
            for token in normalized.split(","):
                band = token.strip()
                if band in {"normal", "low", "severe"} and band not in bands:
                    bands.append(band)
        contexts = []
        for raw_context in meta.get("contexts", []):
            if not isinstance(raw_context, str):
                continue
            context = raw_context.strip()
            if context and context not in contexts:
                contexts.append(context)
        try:
            weight = float(meta.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        return {
            "band": bands,
            "contexts": contexts,
            "weight": max(0.0, weight),
        }

    def get_mood_band(self, mood_score):
        if mood_score < 20:
            return "severe"
        if mood_score < 50:
            return "low"
        return "normal"

    def get_record(self, purpose, action_type, mood):
        return self.asset_records.get(purpose, {}).get(action_type, {}).get(mood)

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        keys = []
        for action_type, mood_map in self.asset_records.get(purpose, {}).items():
            for mood_tag in mood_map.keys():
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    keys.append(action_type)
                    break
        return keys

    def get_record_weight(self, record):
        if not record:
            return 1.0
        meta = record.get("manifest") or {}
        return max(0.0, float(meta.get("weight", 1.0) or 0.0))

    def is_record_eligible(self, record, mood_score=None, context=None):
        if not record:
            return False
        meta = record.get("manifest") or {}
        bands = meta.get("band") or []
        if mood_score is not None and bands:
            if self.get_mood_band(mood_score) not in bands:
                return False
        contexts = meta.get("contexts") or []
        if context and contexts and context not in contexts:
            return False
        return True

    def choose_weighted_result(self, results):
        if not results:
            return None
        weights = [max(0.0, result[3]) for result in results]
        if any(weight > 0 for weight in weights):
            chosen = random.choices(results, weights=weights, k=1)[0]
        else:
            chosen = random.choice(results)
        return chosen[0], chosen[1], chosen[2]

    def get_safe_frames(self, purpose, mood_list, forbidden=None):
        if forbidden is None: forbidden = []
        if purpose not in self.assets: return self.get_any_available_frames()
        available_types = self.assets[purpose]
        type_keys = list(available_types.keys())
        random.shuffle(type_keys)
        for mood_tag in mood_list:
            for t_key in type_keys:
                mood_map = available_types[t_key]
                if mood_tag in mood_map:
                    return mood_map[mood_tag]
        for t_key in type_keys:
            mood_map = available_types[t_key]
            safe_keys = [k for k in mood_map.keys() if k not in forbidden]
            if safe_keys:
                if "normal" in safe_keys: return mood_map["normal"]
                return mood_map[random.choice(safe_keys)]
        return self.get_any_available_frames()

    def get_mood_rules(self, mood_score, is_adult=False):
        if mood_score < 20:
            if is_adult:
                return (
                    ["scold", "sad", "angry", "exhausted"],
                    ["awkward", "think", "hurry", "effort", "sleep"],
                    ["happy", "smile", "confidence", "cool", "cry", "hard-cry", "scared"],
                )
            return (
                ["scold", "hard-cry", "cry", "exhausted", "scared"],
                ["sad", "angry", "awkward", "think", "hurry", "effort", "sleep"],
                ["happy", "smile", "confidence", "cool"],
            )
        if mood_score < 50:
            return (
                ["angry", "sad", "think", "awkward", "hurry", "effort", "sleep"],
                ["cry", "hard-cry", "scold", "exhausted", "scared"],
                ["happy", "smile", "confidence", "cool"],
            )
        return (
            ["happy", "smile", "confidence", "cool", "glance"],
            ["awkward", "think"],
            ["cry", "hard-cry", "sad", "angry", "scold"],
        )

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets:
            return self.get_any_available_frames(), "default", ""

        available_types = self.assets[purpose]
        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        if action_type in available_types:
            for mood_tag in priority_chain + fallback_chain:
                record = self.get_record(purpose, action_type, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    return record["frames"], action_type, mood_tag

        type_keys = list(available_types.keys())
        if action_type in type_keys:
            type_keys.remove(action_type)
            type_keys.insert(0, action_type)
        for mood_tag in priority_chain + fallback_chain:
            matches = []
            for t_key in type_keys:
                record = self.get_record(purpose, t_key, mood_tag)
                if self.is_record_eligible(record, mood_score=mood_score, context=context):
                    matches.append((record["frames"], t_key, mood_tag, self.get_record_weight(record)))
            weighted = self.choose_weighted_result(matches)
            if weighted:
                return weighted

        target_action = action_type if action_type in available_types else random.choice(list(available_types.keys()))
        safe_results = []
        normal_result = None
        for mood_tag in available_types[target_action].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, target_action, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], target_action, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        if self.manifest_data:
            return None
        return self.get_any_available_frames(), "default", ""

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None

        priority_chain, fallback_chain, forbidden = self.get_mood_rules(mood_score, is_adult=is_adult)

        for mood_tag in priority_chain + fallback_chain:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag

        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted

        return None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None, context=None):
        if purpose not in self.assets or action_type not in self.assets[purpose]:
            return None
        for mood_tag in preferred_moods:
            record = self.get_record(purpose, action_type, mood_tag)
            if self.is_record_eligible(record, mood_score=mood_score, context=context):
                return record["frames"], action_type, mood_tag
        if forbidden is None:
            forbidden = []
        safe_results = []
        normal_result = None
        for mood_tag in self.assets[purpose][action_type].keys():
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if not self.is_record_eligible(record, mood_score=mood_score, context=context):
                continue
            result = (record["frames"], action_type, mood_tag, self.get_record_weight(record))
            if mood_tag == "normal":
                normal_result = result
            safe_results.append(result)
        if normal_result:
            return normal_result[0], normal_result[1], normal_result[2]
        weighted = self.choose_weighted_result(safe_results)
        if weighted:
            return weighted
        return None

    @staticmethod
    def get_resource_path(relative_path):
        base = get_base_path()
        return os.path.join(base, relative_path)

    # 修改 AssetManager 內的 refresh_assets
    def refresh_assets(self):
        # 遍歷資料夾，將 GIF 拆解為 (目的, 動作, 情緒) 三層字典
        # 這是優化的重點：讓之後的 AI 邏輯可以精確查找「對應」的動作
        if not os.path.exists(self.character_path): return
        self.assets = {}
        self.asset_records = {}
        self.manifest_data = self.load_manifest()
        files = [f for f in os.listdir(self.character_path) if f.endswith(".gif")]
        for file in files:
            try:
                base_name, _ = os.path.splitext(file)
                mood = base_name.split("-", 1)[1] if "-" in base_name else ""
                name_part = base_name.split("-", 1)[0]

                parts = name_part.split("_")
                purpose = parts[0]
                action_type = "_".join(parts[1:]) if len(parts) > 1 else "default"

                frames = self.extract_frames(os.path.join(self.character_path, file))
                if frames:
                    if purpose not in self.assets: self.assets[purpose] = {}
                    if purpose not in self.asset_records: self.asset_records[purpose] = {}
                    if action_type not in self.assets[purpose]: self.assets[purpose][action_type] = {}
                    if action_type not in self.asset_records[purpose]: self.asset_records[purpose][action_type] = {}
                    self.assets[purpose][action_type][mood] = frames
                    self.asset_records[purpose][action_type][mood] = {
                        "frames": frames,
                        "file_name": file,
                        "manifest": self.manifest_data.get(file, {}),
                    }
            except Exception as e:
                print(f"解析失敗 {file}: {e}")

    def extract_frames(self, gif_path):
        movie = QMovie(gif_path)
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.jumpToFrame(0)
        frames = []
        count = movie.frameCount()
        for i in range(max(1, count)):
            movie.jumpToFrame(i)
            img = movie.currentImage()
            if img.isNull(): break
            scaled_img = img.scaled(
                img.size() * self.scale_factor,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            frames.append(QPixmap.fromImage(scaled_img))
        return frames

    def get_any_available_frames(self):
        for p in self.assets.values():
            for t in p.values():
                for f in t.values(): return f
        return []

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        """嚴格匹配：只有當目的、動作、情緒完全一致時才回傳"""
        record = self.get_record(purpose, action_type, mood)
        if self.is_record_eligible(record, mood_score=mood_score, context=context):
            return record["frames"]
        return None

    def get_action_keys(self, purpose):
        return list(self.assets.get(purpose, {}).keys())

    def has_action(self, purpose, action_type):
        return action_type in self.assets.get(purpose, {})

class Dashboard(QWidget):
    DURATION_BTN_STYLE = (
        "QPushButton { background: #f3f3f3; color: #222; border-radius: 8px; padding: 6px 10px; border: 1px solid #999; }"
        "QPushButton:checked { background: #91e08f; border: 1px solid #4a8f48; font-weight: bold; }"
    )
    SECTION_LABEL_STYLE = "color: white; background: rgba(0,0,0,150); padding: 6px 8px; border-radius: 6px;"

    def __init__(self, target_rect, pets_dict):
        super().__init__()
        self.is_expanded = False
        self.care_feature_enabled = True  # c. 開啟/關閉大人照護功能
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.teio_dur_idx = 3  # 預設 20s (索引3)
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.tsuyoshi_dur_idx = 2  # 預設 20s (索引2)
        self.teio_duration_buttons = []
        self.tsuyoshi_duration_buttons = []
        self.target_rect = target_rect
        self.pets_dict = pets_dict
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(10)  # 拉開組件間距
        self.layout.setContentsMargins(15, 15, 15, 15)
        label = QLabel("狸貓控制中心")
        label.setStyleSheet("color: white; background: rgba(0,0,0,150); padding: 5px; border-radius: 5px;")
        self.layout.addWidget(label)
        # --- 新增功能按鈕區 ---
        self.layout.addWidget(self.make_section_label("全域設定"))

        self.btn_care = QPushButton("照護功能: 開啟")
        self.btn_care.clicked.connect(self.toggle_care)
        self.layout.addWidget(self.btn_care)

        self.layout.addWidget(self.make_section_label("帝寶社交冷卻"))
        teio_row = self.create_duration_selector("teio", self.teio_dur_list)
        self.layout.addLayout(teio_row)

        self.layout.addWidget(self.make_section_label("鶴寶社交冷卻"))
        tsuyoshi_row = self.create_duration_selector("tsuyoshi", self.tsuyoshi_dur_list)
        self.layout.addLayout(tsuyoshi_row)
        for folder_name, info in self.pets_dict.items():
            container = QWidget()
            v_box = QVBoxLayout(container)
            v_box.setSpacing(4)
            v_box.setContentsMargins(0, 0, 0, 0)

            btn = QPushButton(f"召喚 {info['name']}")
            btn.setFixedHeight(35)
            btn.setCheckable(True)
            btn.setChecked(info["pet"].isVisible())
            btn.toggled.connect(lambda checked, p=info["pet"]: p.show() if checked else p.hide())
            btn.setStyleSheet(
                "QPushButton { background: white; border-radius: 8px; padding: 8px; } QPushButton:checked { background: #aaffaa; }")

            # 1. 先建立實體
            mood_bar = QProgressBar()
            mood_bar.setRange(0, 100)
            mood_bar.setTextVisible(False)
            mood_bar.setFixedHeight(6)
            mood_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4444, stop:1 #44ff44); } QProgressBar { background-color: #333; border-radius: 3px; }")

            # 2. 【關鍵修正】先存入字典
            info["mood_bar"] = mood_bar

            # 3. 再從字典讀取並加入佈局 (或是直接加入 mood_bar 變數也可以)
            v_box.addWidget(btn)
            v_box.addWidget(mood_bar)
            self.layout.addWidget(container)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_mood_bars)
        self.update_timer.start(500)
        self.btn_exit = QPushButton("關閉系統")
        self.btn_exit.clicked.connect(QApplication.quit)
        self.layout.addWidget(self.btn_exit)
        self.setLayout(self.layout)
        # 調整面板整體尺寸
        ratio = self.devicePixelRatio()
        base_w, base_h = 360, 620  # 定義基準寬高
        self.setFixedSize(int(base_w * ratio), int(base_h * ratio))
        self.update_positions(target_rect)
        self.move(self.hide_pos)
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.update_duration_buttons()
    def refresh_mood_bars(self):
        for info in self.pets_dict.values():
            info["mood_bar"].setValue(int(info["pet"].mood_score))

    def make_section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(self.SECTION_LABEL_STYLE)
        return label

    def toggle_care(self):
        self.care_feature_enabled = not self.care_feature_enabled
        self.btn_care.setText(f"照護功能: {'開啟' if self.care_feature_enabled else '關閉'}")

    def create_duration_selector(self, char, durations):
        row = QHBoxLayout()
        row.setSpacing(6)
        button_bucket = self.teio_duration_buttons if char == "teio" else self.tsuyoshi_duration_buttons
        for idx, seconds in enumerate(durations):
            btn = QPushButton(f"{seconds}s")
            btn.setCheckable(True)
            btn.setMinimumWidth(48)
            btn.setStyleSheet(self.DURATION_BTN_STYLE)
            btn.clicked.connect(lambda checked=False, c=char, i=idx: self.set_duration(c, i))
            button_bucket.append(btn)
            row.addWidget(btn)
        return row

    def set_duration(self, char, index):
        if char == "teio":
            self.teio_dur_idx = index
        else:
            self.tsuyoshi_dur_idx = index
        self.update_duration_buttons()
        self.apply_social_settings()

    def update_duration_buttons(self):
        for idx, btn in enumerate(self.teio_duration_buttons):
            btn.setChecked(idx == self.teio_dur_idx)
        for idx, btn in enumerate(self.tsuyoshi_duration_buttons):
            btn.setChecked(idx == self.tsuyoshi_dur_idx)

    def get_social_cooldown_label_seconds(self, pet_name):
        if pet_name == "Tokai Teio":
            return self.teio_dur_list[self.teio_dur_idx]
        if pet_name == "Tsurumaru Tsuyoshi":
            return self.tsuyoshi_dur_list[self.tsuyoshi_dur_idx]
        return 0

    def get_social_cooldown_seconds(self, pet_name):
        duration = self.get_social_cooldown_label_seconds(pet_name)
        return float(duration) if duration else 0.0

    def apply_social_settings(self):
        teio = self.pets_dict.get("Tokai Teio", {}).get("pet")
        tsuyoshi = self.pets_dict.get("Tsurumaru Tsuyoshi", {}).get("pet")
        if teio:
            teio.social_cooldown_duration = self.get_social_cooldown_seconds("Tokai Teio")
        if tsuyoshi:
            tsuyoshi.social_cooldown_duration = self.get_social_cooldown_seconds("Tsurumaru Tsuyoshi")
    def update_positions(self, rect):
        # 使用 self.width() 和 self.height() 獲取當前實際像素大小
        w = self.width()
        h = self.height()

        # 計算顯示位置 (貼齊工作列上方)
        self.show_pos = QPoint(rect.left(), rect.bottom() - h)
        # 計算隱藏位置 (縮到左側螢幕外)
        self.hide_pos = QPoint(rect.left() - w - 10, rect.bottom() - h)
    def slide_in(self, pets, sensor):
        self.is_expanded = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.anim.setEndValue(self.show_pos); self.anim.start(); self.raise_()
    def slide_out(self):
        if self.is_expanded:
            self.is_expanded = False
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.anim.setEndValue(self.hide_pos); self.anim.start()

class SensorZone(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.progress = 0.0
        self.glow_anim = QVariantAnimation(self)
        self.glow_anim.setDuration(2000)
        self.glow_anim.setStartValue(0.0); self.glow_anim.setEndValue(1.0)
        self.glow_anim.valueChanged.connect(self.update_progress)
        self.glow_anim.finished.connect(self.on_finished)
    def update_progress(self, value):
        self.progress = value; self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(40, 40, 40, 80)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        if self.progress > 0:
            fill_h = int(self.height() * self.progress)
            painter.setBrush(QColor(100, 255, 100, 200))
            painter.drawRect(0, self.height() - fill_h, self.width(), fill_h)
    def on_finished(self):
        if self.progress >= 0.99: self.dashboard.slide_in([], self)
        self.progress = 0.0; self.update()
    def enterEvent(self, event):
        if not self.dashboard.is_expanded: self.glow_anim.start()
    def leaveEvent(self, event):
        self.glow_anim.stop(); self.progress = 0.0; self.update()

class TanukiPet(QWidget):
    """
    使用明確的優先序來處理 AI，避免救助 / 模仿 / 隨機行為互相覆蓋。
    """
    ADULT_NAMES = {"Symboli Rudolf", "Sirius Symboli", "Air Groove"}
    CHILD_NAMES = {"Tokai Teio", "Tsurumaru Tsuyoshi"}
    CHILD_TOKEN_MAP = {
        "Tokai Teio": ["Teio"],
        "Tsurumaru Tsuyoshi": ["Tsuyoshi"],
    }
    DISTRESS_MOODS = {"sad", "cry", "hard-cry"}
    SEVERE_MOODS = {"scold", "hard-cry", "cry", "exhausted", "scared"}
    ADULT_SEVERE_MOODS = {"scold", "sad", "angry", "exhausted"}

    def __init__(self, char_id, char_folder, scale=0.8, dashboard_instance=None):
        super().__init__()
        self.char_id = char_id; self.name = char_id
        self.asset_manager = AssetManager(char_folder, scale_factor=scale)
        self.current_frames = []; self.frame_index = 0; self.direction = 1
        self.dragging = False; self.original_face_left = True
        self.mood_score = 60.0; self.mood_state = "normal"; self.drag_start_time = 0
        self.click_count = 0
        self.is_angry_locked = False
        self.click_reset_timer = QTimer(self)
        self.click_reset_timer.setSingleShot(True)
        self.click_reset_timer.timeout.connect(self.reset_clicks)
        self.lock_timer = QTimer(self)
        self.lock_timer.setSingleShot(True)
        self.lock_timer.timeout.connect(self.unlock_interaction)
        self.state = "idle"
        self.state_timer = 0
        self.current_purpose = ""
        self.is_adult = self.name in self.ADULT_NAMES
        self.lonely_timer = 0
        self.setFixedSize(int(600 * scale), int(600 * scale))
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0
        self.social_cooldown_end = 0.0
        # --- 性格差異化參數設定 ---
        self.social_distance = 600  # 預設感應距離
        self.social_cooldown_duration = 5.0  # 預設冷卻時間(秒)

        if self.name == "Tokai Teio":  # 帝寶：愛湊熱鬧，感應遠，冷卻短
            self.social_distance = 600
            self.social_cooldown_duration = 10.0
        elif self.name == "Tsurumaru Tsuyoshi":  # 鶴寶：害羞體弱，感應近，冷卻長
            self.social_distance = 350
            self.social_cooldown_duration = 10.0
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"

        # --- 星星相關 ---
        self.star_pixmap = QPixmap(AssetManager.get_resource_path("star.png"))
        self.star_opacity = 0.0
        self.star_y_offset = 0
        self.star_anim_counter = 0
        self.star_timer = QTimer(self)
        self.star_timer.timeout.connect(self.update_star_animation)

        # --- 抱抱飲料互動相關 ---
        self.dashboard = dashboard_instance  # 傳入 dashboard 引用以讀取設定
        self.is_recovering = False
        self.recovery_end_time = 0.0
        self.recovery_motion_mode = "stay"
        self.stationary_move_mode = False
        self.stationary_move_key = ""
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_cooldown_end = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

        self.bar_opacity = 0.0
        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.setDuration(300)
        self.fade_anim.valueChanged.connect(self.update_bar_opacity)
        self.heart_pixmap = QPixmap(AssetManager.get_resource_path("heart.png"))
        self.show_heart = False; self.heart_opacity = 0.0; self.heart_y_offset = 0
        self.heart_anim = QVariantAnimation(self)
        self.heart_anim.setDuration(1000)
        self.heart_anim.setStartValue(0.0); self.heart_anim.setEndValue(1.0)
        self.heart_anim.valueChanged.connect(self.animate_heart)
        self.heart_anim.finished.connect(lambda: setattr(self, 'show_heart', False))
        self.vy = 0.0; self.gravity = 1.2; self.bounce = -0.3
        self.radius = (100 * scale); self.mass = 2 if self.is_adult else 0.8
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self.next_frame); self.anim_timer.start(80)
        self.change_state("idle", "stand")
        self.last_x = self.x()
        self.stuck_count = 0
        self.show()

    def reset_clicks(self): self.click_count = 0
    def unlock_interaction(self):
        self.is_angry_locked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.change_state("idle", "stand")
    def update_bar_opacity(self, value): self.bar_opacity = value; self.update()
    def animate_heart(self, value): self.heart_opacity = 1.0 - (value ** 2); self.heart_y_offset = int(value * 60); self.update()
    def pop_heart(self):
        if not self.heart_pixmap.isNull(): self.show_heart = True; self.heart_anim.start()

    def get_social_cooldown_seconds(self):
        if self.dashboard:
            cooldown = self.dashboard.get_social_cooldown_seconds(self.name)
            if cooldown:
                return cooldown
        return self.social_cooldown_duration

    def get_social_duration_frames(self, mode):
        if mode == "following":
            return random.randint(200, 400)
        if mode == "mimicking":
            return random.randint(60, 80)
        return 0

    def get_child_tokens(self):
        return self.CHILD_TOKEN_MAP.get(self.name, [self.name])

    def distance_to(self, other):
        return math.hypot(
            self.geometry().center().x() - other.geometry().center().x(),
            self.geometry().center().y() - other.geometry().center().y()
        )

    def is_distressed(self):
        if self.current_mood_tag in self.DISTRESS_MOODS:
            return True
        return self.mood_state == "depressed" and self.current_mood_tag not in {"happy", "smile", "confidence", "cool"}

    def is_under_care(self, now):
        return self.care_partner is not None and self.care_lock_mode != "none" and now < self.care_lock_end_time

    def clear_care_lock(self):
        if self.care_lock_mode == "hidden" and not self.isVisible():
            self.show()
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

    def get_care_release_padding(self):
        return 24

    def clamp_x_to_virtual_geometry(self, x, width, padding=0):
        vr = get_total_virtual_geometry()
        min_x = vr.left() + padding
        max_x = vr.right() - width - padding
        if max_x < min_x:
            min_x = vr.left()
            max_x = vr.right() - width
        return max(min_x, min(max_x, x))

    def get_child_release_position(self, child, direction=None, offset=None):
        if direction is None:
            direction = self.care_move_direction or self.direction or 1
        if offset is None:
            offset = random.randint(40, 60)
        adult_center_x = self.x() + (self.width() // 2)
        child_x = int(adult_center_x + (direction * offset) - (child.width() / 2))
        child_x = self.clamp_x_to_virtual_geometry(
            child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        geom = screen.availableGeometry()
        child_y = geom.bottom() - child.height()
        return child_x, child_y

    def should_finish_moving_interaction_at_edge(self, child, step):
        direction = self.care_move_direction or self.direction or 1
        vr = get_total_virtual_geometry()
        projected_x = self.x() + (step * direction)
        if projected_x < vr.left() or projected_x + self.width() > vr.right():
            return True
        projected_center_x = projected_x + (self.width() // 2)
        projected_child_x = int(projected_center_x + (direction * 60) - (child.width() / 2))
        clamped_child_x = self.clamp_x_to_virtual_geometry(
            projected_child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        return projected_child_x != clamped_child_x

    def release_hidden_child_nearby(self, child):
        child_x, child_y = self.get_child_release_position(child)
        child.move(child_x, child_y)

    def should_ignore_collision(self):
        now = time.time()
        return (
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.is_hugging or
            self.care_mode != "none" or
            self.care_partner is not None or
            self.is_under_care(now)
        )

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood = result
        if not frames:
            return False
        self.current_frames = frames
        self.frame_index = 0
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood
        return True

    def change_state_candidates(self, candidates, context=None):
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                self.mood_score,
                is_adult=self.is_adult,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        for mood_tag in preferred_moods:
            for purpose, action_type in candidates:
                frames = self.asset_manager.get_specific_frames(
                    purpose,
                    action_type,
                    mood_tag,
                    mood_score=self.mood_score,
                    context=context,
                )
                if frames and self.apply_animation_result(purpose, (frames, action_type, mood_tag)):
                    return True
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred_moods,
                forbidden=forbidden,
                mood_score=self.mood_score,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def get_severe_moods(self):
        return self.ADULT_SEVERE_MOODS if self.is_adult else self.SEVERE_MOODS

    def get_speed_for_mood_score(self, mood_score):
        if mood_score < 20:
            return 1.1 + (mood_score / 20.0) * 0.6
        if mood_score < 50:
            return 1.5 + ((mood_score - 20.0) / 30.0) * 0.9
        return 0.4 + (mood_score / 100.0) * 2.6

    def get_base_speed(self):
        return self.get_speed_for_mood_score(self.mood_score)

    def get_distressed_move_speed(self):
        return self.get_speed_for_mood_score(35.0)

    def get_care_approach_speed(self):
        return max(2.8, self.get_base_speed() + 0.6)

    def reset_stationary_move_mode(self):
        self.stationary_move_mode = False
        self.stationary_move_key = ""

    def is_stationary_move_candidate(self):
        return (
            self.name == "Tokai Teio" and
            self.current_purpose == "move" and
            self.current_action_tag in {"jog", "walk_drink"}
        )

    def configure_stationary_move_mode(self, context="random", force=False):
        if context != "random" or not self.is_stationary_move_candidate():
            self.reset_stationary_move_mode()
            return
        current_key = f"{context}:{self.current_action_tag}"
        if not force and self.stationary_move_key == current_key:
            return
        self.stationary_move_key = current_key
        stationary_chances = {
            "jog": 0.35,
            "walk_drink": 0.65,
        }
        self.stationary_move_mode = random.random() < stationary_chances.get(self.current_action_tag, 0.0)

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        expanded = list(candidates)
        seen = set(expanded)
        extra_actions = self.asset_manager.get_action_keys_for_context(
            purpose,
            mood_score=self.mood_score,
            context=context,
        )
        for action_type in extra_actions:
            candidate = (purpose, action_type)
            if candidate not in seen:
                expanded.append(candidate)
                seen.add(candidate)
        return expanded

    def ensure_candidate_animation(self, candidates, context=None):
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if frames:
                return True
        return self.change_state_candidates(candidates, context=context)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if self.current_mood_tag in preferred_moods and frames:
                return True
        return self.change_state_candidates_with_preferences(
            candidates,
            preferred_moods,
            forbidden=forbidden,
            context=context,
        )

    def get_child_comfort_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("idle", "drink"),
                ("idle", "eat"),
                ("idle", "side_eat_candy"),
                ("idle", "sit"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "side_hug"),
            ]
        return [
            ("idle", "drink"),
            ("idle", "eat"),
            ("idle", "side_hug"),
            ("idle", "side_rub"),
            ("idle", "sit_no"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_child_recovery_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("move", "walk_drink"),
                ("idle", "dance_uma_drink"),
                ("idle", "side_eat_candy"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "sit"),
            ]
        return self.get_child_comfort_candidates()

    def get_adult_companion_candidates(self):
        return [
            ("idle", "sit"),
            ("idle", "sit_talk"),
            ("idle", "sit_read"),
            ("idle", "rest"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_move_candidates(self):
        return [
            ("move", "walk"),
            ("move", "run"),
            ("move", "jog"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_care_move_candidates(self):
        return [
            ("move", "run"),
            ("move", "jog"),
            ("move", "walk"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_idle_candidates(self):
        return [
            ("idle", "stand"),
            ("idle", "side"),
            ("idle", "sit"),
            ("idle", "rest"),
            ("idle", "lie"),
            ("idle", "squat"),
            ("idle", "observe"),
            ("idle", "photo"),
            ("idle", "photo_ready"),
            ("idle", "dance_three"),
            ("idle", "dance_uma"),
            ("idle", "hear"),
            ("idle", "knock"),
            ("idle", "get"),
            ("idle", "sleep"),
        ]

    def get_randomized_candidates(self, candidates):
        randomized = list(candidates)
        random.shuffle(randomized)
        return randomized

    def start_recovery(self, now):
        self.stop_social_mode(now, apply_cooldown=False)
        self.is_recovering = True
        self.recovery_end_time = now + 8.0
        self.recovery_motion_mode = "stay"
        self.reset_stationary_move_mode()
        self.clear_care_lock()
        self.state = "idle"
        recovery_candidates = self.get_randomized_candidates(self.get_child_recovery_candidates())
        if not self.change_state_candidates(recovery_candidates):
            self.change_state("idle", "stand")
        elif self.current_purpose == "move":
            if self.name == "Tokai Teio" and random.random() < 0.4:
                self.recovery_motion_mode = "walk"
                self.state = "move"

    def maintain_care_lock(self, now):
        if self.care_partner and self.social_mode != "none":
            self.stop_social_mode(now, apply_cooldown=False)
        if self.care_partner and self.care_lock_mode == "none":
            self.state = "idle"
            return True
        if not self.is_under_care(now):
            self.clear_care_lock()
            return False
        if self.care_lock_mode == "hidden":
            if self.isVisible():
                self.hide()
            return True
        if not self.isVisible():
            self.show()
        if self.care_partner:
            self.direction = -1 if self.care_partner.x() < self.x() else 1
        self.state = "idle"
        self.ensure_candidate_animation(self.get_child_comfort_candidates())
        self.mood_score = min(100, self.mood_score + 0.05)
        return True

    def paintEvent(self, event):
        if not self.current_frames: return
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pixmap = self.current_frames[self.frame_index]
        draw_x = (self.width() - pixmap.width()) // 2
        draw_y = self.height() - pixmap.height()
        painter.save()
        should_flip = (self.direction == 1) if self.original_face_left else (self.direction == -1)
        if should_flip:
            painter.translate(self.width(), 0); painter.scale(-1, 1)
            painter.drawPixmap(self.width() - draw_x - pixmap.width(), draw_y, pixmap)
        else:
            painter.drawPixmap(draw_x, draw_y, pixmap)
        painter.restore()

        if self.bar_opacity > 0:
            painter.setOpacity(self.bar_opacity)
            bar_w, bar_h = 60, 5
            bar_x, bar_y = (self.width() - bar_w) // 2, draw_y - 12
            painter.setBrush(QColor(0, 0, 0, 120)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)
            color = QColor(255, 50, 50) if self.mood_score < 20 else QColor(255, 200, 50) if self.mood_score < 50 else QColor(80, 255, 80)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_x, bar_y, int(bar_w * (self.mood_score / 100)), bar_h, 2, 2)

        if self.show_heart and not self.heart_pixmap.isNull():
            painter.setOpacity(self.heart_opacity)
            h_s = 35
            painter.drawPixmap((self.width() - h_s) // 2, draw_y - 20 - self.heart_y_offset, h_s, h_s, self.heart_pixmap)

        # --- 星星繪製 (修正位置：正確放在馬娘身上) ---
        if self.star_opacity > 0 and not self.star_pixmap.isNull():
            painter.setOpacity(self.star_opacity)
            s_size, spacing, num_stars = 25, 30, 3
            start_x = (self.width() - (num_stars * s_size)) // 2
            star_base_y = draw_y - 50 + self.star_y_offset
            for i in range(num_stars):
                individual_offset = int(math.sin((self.star_anim_counter + i * 20) * 0.1) * 3)
                painter.drawPixmap(start_x + i * spacing, star_base_y + individual_offset, s_size, s_size, self.star_pixmap)
        painter.setOpacity(1.0)

    def next_frame(self):
        if self.current_frames: self.frame_index = (self.frame_index + 1) % len(self.current_frames); self.update()

    def update_mood(self, all_pets):
        nearby = []
        my_center = self.geometry().center()
        for other in all_pets:
            if other == self or not other.isVisible(): continue
            if math.hypot(my_center.x() - other.geometry().center().x(), my_center.y() - other.geometry().center().y()) < 250: nearby.append(other)
        rec = 0.5 + (0.5 if not self.is_adult else 0.0)
        if nearby:
            rec += 0.5
            if not self.is_adult and any(p.is_adult for p in nearby): rec += 2.0
        if not self.is_adult:
            if not nearby:
                self.lonely_timer += 3
                if self.lonely_timer >= 10: rec -= 2.0
            else: self.lonely_timer = 0
        self.mood_score = max(0, min(100, self.mood_score + rec + random.uniform(-1, 1)))
        old_s = self.mood_state
        self.mood_state = "depressed" if self.mood_score < 20 else "unhappy" if self.mood_score < 50 else "normal"
        if old_s != self.mood_state:
            target_purpose = self.current_purpose or ("move" if self.state == "move" else "idle")
            self.change_state(target_purpose, self.current_action_tag)

    def tick(self, all_pets):
        if not self.dragging:
            self.apply_gravity()
            self.check_boundary_stuck()
            if self.vy == 0: self.update_ai_behavior(all_pets)

    def apply_gravity(self):
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        floor_y = screen.availableGeometry().bottom()
        if self.geometry().bottom() < floor_y:
            self.vy += self.gravity; self.move(self.x(), self.y() + int(self.vy))
            if self.geometry().bottom() >= floor_y:
                imp = self.vy; self.move(self.x(), floor_y - self.height())
                if abs(imp) > 15:
                    self.mood_score -= 15
                    self.apply_reaction(["scared", "exhausted", "cry"], is_negative=True)
                    self.vy = imp * self.bounce
                elif abs(imp) > 3: self.vy *= -0.4
                else: self.vy = 0
        elif self.geometry().bottom() > floor_y: self.move(self.x(), floor_y - self.height())

    def update_star_animation(self):
        target_opacity = 1.0 if self.social_mode in ["following", "mimicking"] else 0.0
        if self.star_opacity < target_opacity: self.star_opacity = min(1.0, self.star_opacity + 0.1)
        elif self.star_opacity > target_opacity: self.star_opacity = max(0.0, self.star_opacity - 0.1)
        self.star_anim_counter = (self.star_anim_counter + 1) % 360
        self.star_y_offset = int(math.sin(self.star_anim_counter * 0.1) * 5)
        if self.star_opacity > 0: self.update()
        else: self.star_timer.stop()

    def start_social_mode(self, mode, target, now):
        self.social_mode = mode
        self.social_target = target
        self.social_started_at = now
        self.social_timer_frames = self.get_social_duration_frames(mode)
        self.star_timer.start(30)

    def stop_social_mode(self, now, apply_cooldown=True):
        if apply_cooldown and self.social_mode != "none":
            self.social_cooldown_end = now + self.get_social_cooldown_seconds()
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0

    def can_strictly_mimic(self, target):
        return bool(self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        ))

    def sync_mimic_animation(self, target):
        frames = self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        )
        if not frames:
            return False
        if (
            self.current_purpose != target.current_purpose or
            self.current_action_tag != target.current_action_tag or
            self.current_mood_tag != target.current_mood_tag
        ):
            self.current_frames = frames
            self.frame_index = 0
            self.current_purpose = target.current_purpose
            self.current_action_tag = target.current_action_tag
            self.current_mood_tag = target.current_mood_tag
        return True

    def parse_interaction_action(self, action_key):
        if action_key.startswith("move_"):
            motion = "move"
            rest = action_key[len("move_"):]
        elif action_key.startswith("idle_"):
            motion = "idle"
            rest = action_key[len("idle_"):]
        else:
            return None
        if "_" not in rest:
            return None
        action_desc, child_token = rest.rsplit("_", 1)
        return motion, action_desc, child_token

    def get_distress_mood_candidates(self, child):
        moods = []
        for mood in [child.current_mood_tag, "sad", "cry", "hard-cry", "happy"]:
            if mood and mood not in moods:
                moods.append(mood)
        return moods

    def select_interaction_animation(self, child):
        child_tokens = set(child.get_child_tokens())
        actions = self.asset_manager.get_action_keys("interaction")
        if not actions:
            return None

        preferred_motion = "move" if self.state == "move" else "idle"
        motion_order = [preferred_motion, "idle" if preferred_motion == "move" else "move"]
        for motion in motion_order:
            for mood in self.get_distress_mood_candidates(child):
                matches = []
                for action_key in actions:
                    parsed = self.parse_interaction_action(action_key)
                    if not parsed:
                        continue
                    action_motion, _, child_token = parsed
                    if action_motion != motion or child_token not in child_tokens:
                        continue
                    interaction_context = "moving_interaction" if action_motion == "move" else "interaction"
                    frames = self.asset_manager.get_specific_frames(
                        "interaction",
                        action_key,
                        mood,
                        mood_score=child.mood_score,
                        context=interaction_context,
                    )
                    if frames:
                        matches.append((action_key, mood, frames))
                if matches:
                    return random.choice(matches)
        return None

    def start_care_approach(self, child):
        self.stop_social_mode(time.time(), apply_cooldown=False)
        self.care_mode = "approach"
        self.care_target = child
        self.care_plan = "auto"
        child.care_partner = self

    def decide_care_plan(self, child, has_interaction):
        if not has_interaction:
            return "companion"
        interaction_weights = {
            "Symboli Rudolf": 0.65,
            "Sirius Symboli": 0.50,
            "Air Groove": 0.40,
        }
        interaction_chance = interaction_weights.get(self.name, 0.50)
        if random.random() < interaction_chance:
            return "interaction"
        return "companion"

    def begin_hidden_interaction(self, child, animation_spec, now):
        action_key, mood, frames = animation_spec
        parsed = self.parse_interaction_action(action_key)
        motion = parsed[0] if parsed else "idle"
        self.care_mode = "moving_interaction" if motion == "move" else "interaction"
        self.care_end_time = now + 3.0
        self.is_hugging = True
        self.care_move_direction = self.direction or 1
        child.care_partner = self
        child.care_lock_mode = "hidden"
        child.care_lock_end_time = self.care_end_time
        child.hide()
        self.current_frames = frames
        self.frame_index = 0
        self.current_purpose = "interaction"
        self.current_action_tag = action_key
        self.current_mood_tag = mood
        self.state = "move" if self.care_mode == "moving_interaction" else "idle"

    def begin_companion_care(self, child, now):
        self.care_mode = "sit"
        self.care_end_time = now + 5.0
        child.care_partner = self
        child.care_lock_mode = "comfort"
        child.care_lock_end_time = self.care_end_time
        child.show()
        self.state = "idle"
        self.ensure_candidate_animation(self.get_adult_companion_candidates())
        child.state = "idle"
        child.ensure_candidate_animation(child.get_child_comfort_candidates())

    def finish_care_mode(self, success=True):
        now = time.time()
        child = self.care_target
        previous_mode = self.care_mode
        if child:
            if previous_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
            if success:
                child.mood_score = min(100, child.mood_score + 25)
                child.pop_heart()
                child.start_recovery(now)
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_cooldown_end = now + 4.0
        self.state = "idle"
        self.change_state("idle", "stand")

    def cancel_care_mode(self):
        child = self.care_target
        if child:
            if self.care_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        delta = target_x - self.x()
        if abs(delta) <= 4:
            return True

        self.direction = 1 if delta > 0 else -1
        base_speed = self.get_base_speed()
        if min_speed is not None:
            base_speed = max(base_speed, min_speed)
        step = max(1, int(base_speed * speed_scale))
        nx = self.x() + (step * self.direction)
        vr = get_total_virtual_geometry()
        if nx < vr.left():
            nx = vr.left()
            self.direction = 1
        elif nx + self.width() > vr.right():
            nx = vr.right() - self.width()
            self.direction = -1
        self.move(nx, self.y())
        return abs(target_x - self.x()) <= step

    def update_care_behavior(self, now, all_pets):
        if not self.is_adult or not self.isVisible():
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        care_enabled = self.dashboard.care_feature_enabled if self.dashboard else True
        if not care_enabled:
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        if self.care_mode != "none":
            child = self.care_target
            if (
                not child or
                child not in all_pets or
                child.care_partner not in (None, self) or
                (not child.isVisible() and self.care_mode not in {"interaction", "moving_interaction"})
            ):
                self.cancel_care_mode()
                return False

            if self.care_mode == "interaction":
                if now >= self.care_end_time:
                    self.finish_care_mode(success=True)
                else:
                    child.mood_score = min(100, child.mood_score + 0.18)
                return True

            if self.care_mode == "moving_interaction":
                self.direction = self.care_move_direction or self.direction or 1
                self.state = "move"
                child.mood_score = min(100, child.mood_score + 0.18)
                step = max(1, int(round(self.get_distressed_move_speed())))
                if now >= self.care_end_time or self.should_finish_moving_interaction_at_edge(child, step):
                    self.finish_care_mode(success=True)
                else:
                    self.move(self.x() + (step * self.direction), self.y())
                return True

            if self.care_mode == "sit":
                self.direction = -1 if child.x() < self.x() else 1
                child.direction = -1 if self.x() < child.x() else 1
                self.ensure_candidate_animation(self.get_adult_companion_candidates())
                child.ensure_candidate_animation(child.get_child_comfort_candidates())
                child.mood_score = min(100, child.mood_score + 0.10)
                if now >= self.care_end_time or child.mood_score >= 70:
                    self.finish_care_mode(success=True)
                return True

            if not child.is_distressed() and child.mood_score >= 55:
                self.finish_care_mode(success=False)
                return False

            interaction_spec = self.select_interaction_animation(child)
            if self.care_plan == "auto":
                self.care_plan = self.decide_care_plan(child, interaction_spec is not None)
            elif self.care_plan == "interaction" and not interaction_spec:
                self.care_plan = "companion"

            use_interaction = self.care_plan == "interaction" and interaction_spec is not None
            offset = 120 if self.x() <= child.x() else -120
            target_x = child.x() if use_interaction else child.x() - offset
            self.state = "move"
            self.ensure_candidate_animation_with_preferences(
                self.expand_candidates_with_context("move", self.get_care_move_candidates(), context="care_approach"),
                ["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
                context="care_approach",
            )
            arrived = self.move_toward_x(
                target_x,
                speed_scale=1.6,
                min_speed=self.get_care_approach_speed(),
            )
            if arrived or self.distance_to(child) < 140:
                if use_interaction:
                    self.begin_hidden_interaction(child, interaction_spec, now)
                else:
                    self.begin_companion_care(child, now)
            return True

        if now < self.care_cooldown_end:
            return False

        radius = None if self.name == "Sirius Symboli" else 1000
        candidates = []
        for pet in all_pets:
            if pet == self or pet.is_adult or not pet.isVisible():
                continue
            if pet.care_partner not in (None, self):
                continue
            if pet.is_recovering or not pet.is_distressed():
                continue
            dist = self.distance_to(pet)
            if radius is not None and dist > radius:
                continue
            candidates.append((dist, pet))

        if not candidates:
            return False

        candidates.sort(key=lambda item: item[0])
        self.start_care_approach(candidates[0][1])
        return True

    def update_social_behavior(self, now, all_pets):
        if self.name not in self.CHILD_NAMES or self.dragging:
            return False

        rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)
        if self.social_mode != "none":
            if not rudolf or self.social_target != rudolf:
                self.stop_social_mode(now)
                return False

            dist = self.distance_to(rudolf)
            self.social_timer_frames -= 1
            timed_out = self.social_timer_frames <= 0
            if timed_out or dist > (self.social_distance + 150):
                self.stop_social_mode(now)
                return False

            if self.social_mode == "following":
                if rudolf.current_purpose != "move":
                    self.stop_social_mode(now)
                    return False
                self.state = "move"
                follow_x = rudolf.x() + (rudolf.direction * 120)
                self.move_toward_x(follow_x, speed_scale=1.25)
                self.ensure_candidate_animation(self.get_move_candidates())
                return True

            if self.social_mode == "mimicking":
                if not self.sync_mimic_animation(rudolf):
                    self.stop_social_mode(now)
                    return False
                self.direction = rudolf.direction
                self.state = "move" if rudolf.current_purpose == "move" else "idle"
                if rudolf.current_purpose == "move":
                    self.move_toward_x(rudolf.x(), speed_scale=1.05)
                return True

        if not rudolf or now < self.social_cooldown_end:
            return False

        dist = self.distance_to(rudolf)
        is_behind = (self.x() - rudolf.x()) * rudolf.direction < 0
        if dist >= self.social_distance:
            return False

        if rudolf.current_purpose == "move" and is_behind:
            self.start_social_mode("following", rudolf, now)
            return True

        if self.can_strictly_mimic(rudolf):
            self.start_social_mode("mimicking", rudolf, now)
            return True

        return False

    def update_random_behavior(self):
        if self.mood_score < 20 and self.current_purpose != "interaction":
            self.last_x = self.x()
            self.state_timer -= 1
            if self.current_mood_tag not in self.get_severe_moods() or self.state_timer <= 0:
                self.state = random.choice(["idle", "move"])
                self.state_timer = random.randint(60, 110)
                self.current_purpose = ""
                self.reset_stationary_move_mode()
                if random.random() < 0.25:
                    self.direction *= -1

            severe_candidates = self.expand_candidates_with_context(
                "move" if self.state == "move" else "idle",
                self.get_move_candidates() if self.state == "move" else self.get_idle_candidates(),
                context="random",
            )
            if self.current_purpose != ("move" if self.state == "move" else "idle"):
                if self.change_state_candidates(self.get_randomized_candidates(severe_candidates), context="random"):
                    self.configure_stationary_move_mode("random", force=True)

            if self.state == "move":
                if not self.stationary_move_mode:
                    self.move_logic()
                if self.current_purpose != "move":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.expand_candidates_with_context("move", self.get_move_candidates(), context="random")
                        ),
                        context="random",
                    ):
                        self.configure_stationary_move_mode("random", force=True)
            else:
                self.reset_stationary_move_mode()
                if self.current_purpose != "idle":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.expand_candidates_with_context("idle", self.get_idle_candidates(), context="random")
                        ),
                        context="random",
                    ):
                        self.reset_stationary_move_mode()
            return

        if self.state == "move":
            if self.stationary_move_mode:
                self.stuck_count = 0
            elif abs(self.x() - self.last_x) < 0.5:
                self.stuck_count += 1
            else:
                self.stuck_count = max(0, self.stuck_count - 1)
            if self.stuck_count > 60:
                self.direction *= -1
                self.state_timer = random.randint(30, 80)
                self.stuck_count = 0

        self.last_x = self.x()
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.state = random.choice(["idle", "move"])
            self.state_timer = random.randint(100, 150)
            self.current_purpose = ""
            self.reset_stationary_move_mode()
            if random.random() < 0.3:
                self.direction *= -1

        base_speed = self.get_base_speed()
        visual_p = "move" if (self.state == "move" and base_speed > 0.8) else "idle"
        if self.current_purpose != visual_p:
            candidates = self.expand_candidates_with_context(
                visual_p,
                self.get_move_candidates() if visual_p == "move" else self.get_idle_candidates(),
                context="random",
            )
            if self.change_state_candidates(self.get_randomized_candidates(candidates), context="random"):
                self.configure_stationary_move_mode("random", force=True)

        if self.state == "move":
            if not self.stationary_move_mode:
                self.move_logic()
            if self.current_purpose != "move":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.expand_candidates_with_context("move", self.get_move_candidates(), context="random")
                    ),
                    context="random",
                ):
                    self.configure_stationary_move_mode("random", force=True)
        else:
            self.reset_stationary_move_mode()
            if self.current_purpose != "idle":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.expand_candidates_with_context("idle", self.get_idle_candidates(), context="random")
                    ),
                    context="random",
                ):
                    self.reset_stationary_move_mode()

    def update_ai_behavior(self, all_pets):
        now = time.time()
        if self.is_angry_locked:
            return

        if self.is_recovering:
            if now > self.recovery_end_time:
                self.is_recovering = False
                self.recovery_motion_mode = "stay"
                self.reset_stationary_move_mode()
                self.change_state("idle", "stand")
            else:
                if self.recovery_motion_mode == "walk" and self.current_purpose == "move":
                    self.move_logic()
                return

        if self.maintain_care_lock(now):
            return

        if self.update_care_behavior(now, all_pets):
            return

        if self.update_social_behavior(now, all_pets):
            return

        self.update_random_behavior()

    def move_logic(self):
        base_speed = self.get_base_speed()
        nx = self.x() + int(base_speed * self.direction); vr = get_total_virtual_geometry()
        if nx < vr.left() or nx + self.width() > vr.right(): self.direction *= -1
        else: self.move(nx, self.y())

    def check_boundary_stuck(self):
        vr = get_total_virtual_geometry()
        if self.x() < vr.left(): self.move(vr.left() + 5, self.y()); self.direction = 1
        elif self.x() + self.width() > vr.right(): self.move(vr.right() - self.width() - 5, self.y()); self.direction = -1

    def apply_reaction(self, p_list, is_negative=False):
        forbidden = ["happy", "smile", "confidence", "cool", "glance"] if is_negative else []
        fs = self.asset_manager.get_safe_frames("idle", p_list, forbidden=forbidden)
        if fs: self.current_frames, self.frame_index, self.state, self.state_timer = fs, 0, "idle", 80

    def change_state(self, p, a=None):
        result = self.asset_manager.get_frames_by_score(p, a, self.mood_score, is_adult=self.is_adult)
        self.apply_animation_result(p, result)

    def resolve_collision(self, all_pets):
        if self.should_ignore_collision():
            return
        my_c = self.geometry().center(); repel_x = 0.0; repel_weight = 0.2 if self.mood_score >= 20 else 0.05
        for other in all_pets:
            if other == self or other.should_ignore_collision(): continue
            dist_v = my_c - other.geometry().center(); dist = math.hypot(dist_v.x(), dist_v.y())
            eff_rad = self.radius + other.radius
            if dist < eff_rad:
                overlap = eff_rad - dist
                if overlap > 5.0:
                    total_mass = self.mass + other.mass
                    repel_x += (dist_v.x() / (dist if dist > 0 else 1)) * overlap * (other.mass / total_mass)
                    if not self.is_adult and other.is_adult: other.mood_score = min(100, other.mood_score + 0.01)
        if abs(repel_x) > 0.5: self.move(self.x() + int(repel_x * repel_weight), self.y())

    def trigger_care_event(self, child):
        spec = self.select_interaction_animation(child)
        if spec:
            self.begin_hidden_interaction(child, spec, time.time())
        else:
            self.begin_companion_care(child, time.time())

    def finish_care(self, child=None):
        self.finish_care_mode(success=True)

    def enterEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(1.0); self.fade_anim.start()
    def leaveEvent(self, event): self.fade_anim.setStartValue(self.bar_opacity); self.fade_anim.setEndValue(0.0); self.fade_anim.start()
    def mousePressEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(time.time()): return
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging, self.vy, self.drag_start_time = True, 0, time.time()
            self.drag_pos = event.globalPosition().toPoint() - self.pos(); self.change_state("drag")
    def mouseMoveEvent(self, event):
        if self.dragging: self.move(event.globalPosition().toPoint() - self.drag_pos)
    def mouseReleaseEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(time.time()): return
        if event.button() == Qt.MouseButton.LeftButton:
            dur, self.dragging = time.time() - self.drag_start_time, False
            if dur < 0.2:
                self.click_count += 1; self.click_reset_timer.start(3000); self.state, self.state_timer = "idle", 100
                if self.click_count >= 5:
                    self.is_angry_locked, self.mood_score = True, max(0, self.mood_score - 60)
                    self.setCursor(Qt.CursorShape.ForbiddenCursor); self.apply_reaction(["scold", "angry"], is_negative=True); self.lock_timer.start(5000)
                else: self.mood_score = min(100, self.mood_score + 8); self.pop_heart(); self.apply_reaction(["happy", "smile"])
            elif dur > 5.0:
                self.mood_score = max(0, self.mood_score - 25); self.apply_reaction(["scold", "hard-cry", "exhausted"], is_negative=True)
            else: self.change_state("idle")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir): sys.exit()

    configs = [
        ("Symboli Rudolf", 0.45, "滷豆腐"),
        ("Tokai Teio", 0.35, "帝寶"),
        ("Sirius Symboli", 0.4, "天狼星"),
        ("Tsurumaru Tsuyoshi", 0.3, "鶴寶"),
        ("Air Groove", 0.4, "氣槽")
    ]

    pets_dict, pets_list = {}, []
    # 1. 建立寵物
    for i, (fn, sc, dn) in enumerate(configs):
        path = os.path.join(assets_dir, fn)
        if os.path.exists(path):
            p = TanukiPet(fn, path, sc)
            p.move(500 + i * 100, 600)
            if fn != "Symboli Rudolf": p.hide()
            pets_dict[fn] = {"pet": p, "name": dn}
            pets_list.append(p)

    # 2. 建立面板
    l_screen = min(QApplication.screens(), key=lambda s: s.geometry().x())
    av_rect = l_screen.availableGeometry()
    dash = Dashboard(av_rect, pets_dict)

    # 3. 重要：將 dash 實體回填給所有寵物，防止閃退
    for p in pets_list:
        p.dashboard = dash
    dash.apply_social_settings()

    # 4. 其他組件
    sensor = SensorZone(dash)
    sensor.setGeometry(av_rect.left(), av_rect.bottom() - 300, 20, 300)
    monitor = GlobalMouseListener(dash)

    # 5. 計時器設定
    mood_t = QTimer();
    mood_t.timeout.connect(lambda: [p.update_mood(pets_list) for p in pets_list]);
    mood_t.start(3000)
    phys_t = QTimer();
    phys_t.timeout.connect(lambda: [p.resolve_collision(pets_list) for p in pets_list]);
    phys_t.start(30)
    logic_t = QTimer();
    logic_t.timeout.connect(lambda: [p.tick(pets_list) for p in pets_list]);
    logic_t.start(30)

    dash.show()
    sensor.show()
    sys.exit(app.exec())
