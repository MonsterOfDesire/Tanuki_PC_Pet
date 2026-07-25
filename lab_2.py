import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from tanuki_core.app_runtime import run_application


STARTUP_ERROR_TITLE = "Tanuki PC Pet 啟動失敗"


def report_missing_resource(exc):
    missing_path = str(exc)
    stderr_message = f"Required resource not found: {missing_path}"
    dialog_message = (
        "找不到啟動所需的素材，程式無法繼續執行。\n"
        "請確認發布壓縮檔已完整解壓縮，且素材資料夾沒有被移除。\n\n"
        f"缺少：{missing_path}"
    )
    print(stderr_message, file=sys.stderr)
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    QMessageBox.critical(None, STARTUP_ERROR_TITLE, dialog_message)
    return 1


def main():
    try:
        return int(run_application())
    except FileNotFoundError as exc:
        return report_missing_resource(exc)


if __name__ == "__main__":
    raise SystemExit(main())
