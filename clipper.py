import sys

from PySide6.QtWidgets import QApplication, QMainWindow


class ClipperWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rascal Clipper")
        self.resize(1200, 780)

def main():
    app = QApplication(sys.argv)

    window = ClipperWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()