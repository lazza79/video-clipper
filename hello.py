import sys

from PySide6.QtWidgets import QApplication, QWidget


def main():
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Hello Rascal!")
    window.resize(400,300)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    