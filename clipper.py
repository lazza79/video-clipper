import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QFileDialog


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
            "Video files (*.mp4 *.mov *.mkv);; All files (*)"
            )

        if path:
            self.label.setText(path)



def main():
    app = QApplication(sys.argv)

    window = ClipperWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()