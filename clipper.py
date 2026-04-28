import sys
import subprocess
import json
import os

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QFileDialog
from dataclasses import dataclass


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


class ClipperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rascal Clipper")
        self.resize(1200, 780)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        self.label = QLabel("No Video Loaded")
        layout.addWidget(self.label)
        
        self.button = QPushButton("Load Video")
        layout.addWidget(self.button)
        self.button.clicked.connect(self._on_load_clicked)

    def _on_load_clicked(self):
        
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Video", 
            "", 
            "Video files (*.mp4 *.mov *.mkv);;All files (*)"
            )

        if path:
            info = probe_video(path)
            self.label.setText(
                f"{os.path.basename(info.path)} | "
                f"{info.width}x{info.height} | "
                f"{info.fps:.2f} fps | "
                f"{info.frame_count} frames | "
                f"{info.duration:.2f}s | "
                f"{info.codec}"
            )



def main():
    app = QApplication(sys.argv)

    window = ClipperWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()