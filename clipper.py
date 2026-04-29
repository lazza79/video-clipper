import sys
import subprocess
import json
import os
import tempfile

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QFileDialog
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import Qt, Signal, QThread, QRectF
from dataclasses import dataclass
from typing import Optional

THUMBNAILS = 50
TIMELINE_MIN_HEIGHT = 80
THUMBNAIL_HEIGHT = 80

@dataclass
class VideoInfo:
    path: str
    width: int
    height: int
    fps: float
    duration: float
    frame_count: int
    codec: str

def probe_video(path: str) -> VideoInfo:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)

    # 1. Pick out the video stream from the streams list
    video_streams = [s for s in data["streams"] if s.get("codec_type") == "video"]
    if not video_streams:
        raise RuntimeError(f"No video stream found in {path}")
    vs = video_streams[0]
    codec = vs["codec_name"]

    # 2. Compute fps
    num, den = vs["r_frame_rate"].split("/")
    fps = float(num) / float(den)

    # 3. Pull duration and frame count
    duration = float(data["format"]["duration"])
    frame_count = int(vs["nb_frames"])

    # 4. dimensions
    width = vs["width"]
    height = vs["height"]

    info = VideoInfo(
        path=path,
        width=width,
        height=height,
        fps=fps,
        duration=duration,
        frame_count=frame_count,
        codec=codec,        
        )
    return info


def extract_frame(video_path: str, time_seconds:float) -> QImage:
    pre = max(0.0, time_seconds - 1.0)
    fine = time_seconds - pre
    cmd = [
        "ffmpeg", "-loglevel", "error",
        "-ss", f"{pre:.6f}",        # coarse seek (fast, snaps to keyframe)
        "-i", video_path,
        "-ss", f"{fine:.6f}",       # fine seek (slow, frame-accurate)
        "-vframes", "1",            # output exactly one frame
        "-f", "image2pipe",         # pipe output, don't write a file
        "-c:v", "ppm",              # PPM is uncompressed — Qt parses it natively
        "-",                        # "-" means "write to stdout"
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    return QImage.fromData(result.stdout, "PPM")


class TimelineWidget(QWidget):
    frame_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(TIMELINE_MIN_HEIGHT)
        self.video_info: Optional[VideoInfo] = None
        self.current_frame: int = 0
        self.thumbnails: list = []
        self.thumbnails_count: int = 0

    def _x_for_frame(self, frame: int) -> int:
        if self.video_info is None or self.video_info.frame_count <= 1:
            return 0.0
        ratio = frame / (self.video_info.frame_count - 1)
        x = int(ratio * (self.width() - 1))
        return x
    
    def _frame_for_x(self, x: float) -> int:
        if self.video_info is None:
            return 0
        
        ratio = max(0.0, min(1.0, x / max(1, self.width() - 1)))
        frame = int(round(ratio * (self.video_info.frame_count - 1)))
        return frame

    def set_video(self, info: VideoInfo, thumbnail_count: int):
        self.video_info = info
        self.current_frame = 0
        self.thumbnails_count = thumbnail_count
        self.thumbnails = [None] * thumbnail_count
        self.update()
    
    def set_thumbnail(self, index: int, img: QImage):
        if 0 <= index < len(self.thumbnails):
            self.thumbnails[index] = img
            self.update()

    def set_current_frame(self, frame: int):
        if self.video_info is None:
            return
        new = max(0, min(int(frame), self.video_info.frame_count - 1))
        if new != self.current_frame:
            self.current_frame = new
            self.update()
            self.frame_changed.emit(new)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(40, 40, 50))

        # Draw Thumbnails
        if self.thumbnails_count > 0:
            slot_width = self.width() / self.thumbnails_count
            for i, img in enumerate(self.thumbnails):
                if img is not None:
                    rect = QRectF(i * slot_width, 0, slot_width + 1, self.height())
                    painter.drawImage(rect, img)
        
        # Draw Playhead
        x = self._x_for_frame(self.current_frame)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.position().x()

            self.set_current_frame(self._frame_for_x(x))
        
        

class ClipperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Rascal Clipper")
        self.resize(1200, 780)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        self.label = QLabel("No Video Loaded")
        layout.addWidget(self.label)

        self.preview = QLabel()
        self.preview.setFixedSize(640, 360)
        self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview)

        self.timeline = TimelineWidget()
        self.timeline.frame_changed.connect(self._on_frame_changed)
        layout.addWidget(self.timeline)
        
        self.button = QPushButton("Load Video")
        layout.addWidget(self.button)
        self.button.clicked.connect(self._on_load_clicked)


    def _on_frame_changed(self, frame: int):
        info = self.timeline.video_info
        if info is None:
            return
        self._update_preview(info, frame)

    def _on_load_clicked(self):
        
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Video", 
            "", 
            "Video files (*.mp4 *.mov *.mkv);;All files (*)"
            )

        if path:
            self._load_video(path)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        self._load_video(path)
        event.acceptProposedAction()    


    def _update_preview(self, info: VideoInfo, frame: int):
        img = extract_frame(info.path, frame / info.fps)
        pix = QPixmap.fromImage(img)
        scaled = pix.scaled(
            self.preview.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)
        

    def _load_video(self, path:str):
        info = probe_video(path)
        self.label.setText(
            f"{os.path.basename(info.path)} | "
            f"{info.width}x{info.height} | "
            f"{info.fps:.2f} fps | "
            f"{info.frame_count} frames | "
            f"{info.duration:.2f}s | "
            f"{info.codec}"
        )

        self._update_preview(info, info.frame_count*0.15)

        self.timeline.set_video(info, THUMBNAILS)

        self.worker = ThumbnailWorker(info.path, THUMBNAILS, THUMBNAIL_HEIGHT, info.duration)
        self.worker.thumbnail_ready.connect(self.timeline.set_thumbnail)
        self.worker.start()   


class ThumbnailWorker(QThread):
    thumbnail_ready = Signal(int, QImage)

    def __init__(self, video_path: str, count: int, height: int, duration: float):
        super().__init__()
        self.video_path = video_path
        self.count = count
        self.height = height
        self.duration = duration

    def run(self):
        with tempfile.TemporaryDirectory(prefix="rascal_clipper_thumbs_") as tmp:
            #info = probe_video(self.video_path)
            rate = self.count / self.duration
            pattern = os.path.join(tmp, "thumb_%05d.jpg")
            cmd = [
                "ffmpeg", "-loglevel", "error", "-y",
                "-i", self.video_path,
                "-vf", f"fps={rate:.6f},scale=-1:{self.height}",
                "-q:v", "5",
                pattern,
            ]
            proc = subprocess.Popen(cmd)

            emitted = set()
            while proc.poll() is None:
                self._scan(tmp, emitted, drop_last=True)
                self.msleep(150)
            self._scan(tmp, emitted, drop_last=False)

    def _scan(self, tmp: str, emitted: set, drop_last:bool):
        files = sorted(f for f in os.listdir(tmp) if f.endswith(".jpg"))
        if drop_last and files:
            files = files[:-1]
        for fname in files:
            if fname in emitted:
                continue
            idx = int(fname.split("_")[1].split(".")[0]) - 1
            img = QImage(os.path.join(tmp, fname))
            if not img.isNull():
                self.thumbnail_ready.emit(idx, img.copy())
                emitted.add(fname)
    
    




def main():
    app = QApplication(sys.argv)

    window = ClipperWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()