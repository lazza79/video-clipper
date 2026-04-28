import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget


class ClipperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rascal Clipper")
        self.resize(1200, 780)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        #layout.addWidget(QLabel("No Video Loaded"))
        label = QLabel("No Video Loaded")
        label.setStyleSheet("background-color: red;")
        layout.addWidget(label)

def main():
    app = QApplication(sys.argv)

    window = ClipperWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()