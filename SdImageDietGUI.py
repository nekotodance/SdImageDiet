import sys
import os
import time
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, QTimer
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSpinBox, QListWidget, QComboBox, QStatusBar, QCheckBox, QLineEdit
from PyQt5.QtMultimedia import QSound
from PIL import Image
import SdImageDiet
import pvsubfunc

# 設定ファイル
SETTINGS_FILE = "SdImageDietGUI_settings.json"
GEOMETRY_X = "geometry-x"
GEOMETRY_Y = "geometry-y"
GEOMETRY_W = "geometry-w"
GEOMETRY_H = "geometry-h"
IMG_TYPE = "setting-imgtype"
JPG_QUALITY = "setting-jpgquality"
THREADS_NUM = "setting-threadsnum"
KEEP_TIMESTAMP = "setting-keeptimestamp"
OUTPUT_DIRNAME = "setting-outputdirname"
SOUND_NG = "sound-ng"
SOUND_OK = "sound-ok"

# マルチスレッド用ワーカークラス
class Worker(QRunnable):
    def __init__(self, infile, outdir, imgtype, quality, keepTimestamp, on_complete):
        super().__init__()
        self.infile = infile
        self.outdir = outdir
        self.imgtype = imgtype
        self.quality = quality
        self.keepTimestamp = keepTimestamp
        self.on_complete = on_complete
        self._is_cancelled = False

    def run(self):
        # 画像の変換処理
        try:
            if self._is_cancelled:
                return  # キャンセルされた場合は処理を終了
            indir, infile = os.path.split(self.infile)
            fbase, fext = os.path.splitext(infile)
            #outdir = os.path.join(indir, self.outdir)
            outdir = f"{indir}/{self.outdir}"
            os.makedirs(outdir, exist_ok=True)
            #outfile = os.path.join(outdir, f"{fbase}.{self.imgtype}")
            outfile = f"{outdir}/{fbase}.{self.imgtype}"
            imgext = f".{self.imgtype}"
            SdImageDiet.convert_imgfile(self.infile, outfile, imgext, self.quality, self.keepTimestamp)
            if self._is_cancelled:
                return  # キャンセルされた場合は処理を終了
            self.on_complete(True)
        except Exception as e:
            print(f"Error converting {self.infile}: {e}")
            if self._is_cancelled:
                return  # キャンセルされた場合は処理を終了
            self.on_complete(False)

    def cancel(self):
        self._is_cancelled = True

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.imgtype = "jpg"  # デフォルトのファイル形式
        self.quality = 85  # デフォルトの品質
        self.threadsnum = 11  # デフォルトのスレッド数
        self.keepTimestamp = True  # Time stampの維持
        self.outputdir = "__outputdir"  # 出力フォルダ名称
        self.soundok = "ok.wav"
        self.soundng = "ng.wav"

        self.totalfilenum = 0   # 変換対象のトータルファイル数
        self.totalfilestrlen = 0    # 変換対象のトータルファイル数を文字列化した時の桁数
        self.pydir = os.path.dirname(os.path.abspath(__file__))

        self.setWindowTitle('SD Image Filesize Diet')
        self.setGeometry(100, 100, 640, 480)
        # 設定ファイルが存在しない場合初期値で作成する
        if not os.path.exists(SETTINGS_FILE):
            self.createSettingFile()
        # 起動時にウィンドウ設定を復元
        self.load_settings()

        self.setAcceptDrops(True)

        # UIの設定
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.layout = QVBoxLayout(self.centralWidget)

        self.label = QLabel('Drag and Drop image files or folders here.')
        self.layout.addWidget(self.label)

        self.fileListWidget = QListWidget()
        self.layout.addWidget(self.fileListWidget)

        # 設定値レイアウト１（横並び）
        self.settingLayout1 = QHBoxLayout()
        # 品質設定のラベルとスピンボックス
        self.settingLayout1.addWidget(QLabel('Quality def:85'))
        self.qualitySpinBox = QSpinBox()
        self.qualitySpinBox.setMinimum(1)  # 最小1
        self.qualitySpinBox.setMaximum(100)  # 最大100
        self.qualitySpinBox.setValue(self.quality)  # 初期値85
        self.settingLayout1.addWidget(self.qualitySpinBox)
        # スレッド数設定のラベルとスピンボックス
        self.settingLayout1.addWidget(QLabel('Number of Threads'))
        self.threadSpinBox = QSpinBox()
        self.threadSpinBox.setMinimum(1)
        self.threadSpinBox.setMaximum(os.cpu_count())  # 最大PCのCPUコア数
        self.threadSpinBox.setValue(self.threadsnum)  # デフォルト値はCPUコア数-1
        self.settingLayout1.addWidget(self.threadSpinBox)
        # タイムスタンプ維持のチェックボックス
        self.keepTimestampCheckBox = QCheckBox('keep timestamp')
        self.keepTimestampCheckBox.setChecked(self.keepTimestamp)
        self.settingLayout1.addWidget(self.keepTimestampCheckBox)
        self.layout.addLayout(self.settingLayout1)

        # 設定値レイアウト２（横並び）
        self.settingLayout2 = QHBoxLayout()
        # 画像種別設定のラベルとリストボックス
        self.settingLayout2.addWidget(QLabel('ImgType'))
        self.imgTypeComboBox = QComboBox()
        self.imgTypeComboBox.addItems(["jpg", "webp"])
        self.imgTypeComboBox.setCurrentText(self.imgtype)
        self.settingLayout2.addWidget(self.imgTypeComboBox)
        # 出力フォルダ名のラベルとテキストボックス
        self.settingLayout2.addWidget(QLabel('Output Dir'))
        self.outdirLineEdit = QLineEdit()
        self.outdirLineEdit.setText(self.outputdir)
        self.settingLayout2.addWidget(self.outdirLineEdit)
        self.layout.addLayout(self.settingLayout2)

        # ボタンレイアウト（横並び）
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addStretch()  # ボタンの押し間違いがたまにあったのでスペースを追加
        # 変換ボタン
        self.convertButton = QPushButton('Convert')
        self.convertButton.setFixedHeight(40)  # ボタンの高さを調整
        self.convertButton.setStyleSheet(
            """
            QPushButton {
                background-color: #22DD00;  /* 背景色 */
                color: black;  /* 文字色 */
            }
            QPushButton:disabled {
                background-color: lightgray;  /* 無効状態の背景色 */
                color: #222222;  /* 無効状態の文字色 */
            }
            """
        )
        self.buttonLayout.addWidget(self.convertButton)
        # キャンセルボタン
        self.cancelButton = QPushButton('Cancel')
        self.cancelButton.setFixedHeight(40)  # ボタンの高さを調整
        self.cancelButton.setStyleSheet(
            """
            QPushButton {
                background-color: #DD2200;  /* 背景色 */
                color: black;  /* 文字色 */
            }
            QPushButton:disabled {
                background-color: lightgray;  /* 無効状態の背景色 */
                color: #222222;  /* 無効状態の文字色 */
            }
            """
        )
        self.cancelButton.setEnabled(False)  # 初期状態では無効化
        self.buttonLayout.addWidget(self.cancelButton)
        # クリアボタン
        self.clearButton = QPushButton('Clear')
        self.clearButton.setFixedHeight(40)  # ボタンの高さを調整
        self.buttonLayout.addWidget(self.clearButton)
        self.layout.addLayout(self.buttonLayout)

        # ステータスバーを追加
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("color: white; font-size: 14px; background-color: #31363b;")
        self.setStatusBar(self.statusBar)

        # ボタン押下処理
        self.convertButton.clicked.connect(self.start_conversion)
        self.cancelButton.clicked.connect(self.cancel_conversion)
        self.clearButton.clicked.connect(self.clear_conversion)

        # 値変更時に変数を更新
        self.qualitySpinBox.valueChanged.connect(self.update_jpgquality_values)
        self.threadSpinBox.valueChanged.connect(self.update_threadsnum_values)
        self.keepTimestampCheckBox.stateChanged.connect(self.update_keeptimestamp_check)
        self.imgTypeComboBox.currentIndexChanged.connect(self.update_imgtype_changed)
        self.outdirLineEdit.textChanged.connect(self.update_outdir_changed)

        # スレッドプールの初期化
        self.thread_pool = QThreadPool()

        self.file_paths = []  # 変換するファイルのリスト
        self.converted_files = 0  # 変換したファイル数
        self.start_time = 0  # 変換開始時間

        self.workers = []  # Workerのリスト

    # アプリ終了時に位置とサイズ、設定値を保存する
    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    # 変換ボタン処理
    def start_conversion(self):
        pass
        # 変換ボタンが押されたときにファイルリストから変換処理を開始
        self.file_paths = [self.fileListWidget.item(i).text() for i in range(self.fileListWidget.count())]

        if not self.file_paths:
            self.statusBar.showMessage('No files to convert.')
            self.play_wave(self.soundng)
            return

        self.converted_files = 0
        self.start_time = time.time()  # 変換開始時刻

        self.totalfilenum = len(self.file_paths)    # 変換対象ファイル数
        self.totalfilestrlen = len(str(self.totalfilenum)) #変換対象ファイル数を文字列にした時の桁数（表示用）

        self.cancelButton.setEnabled(True)  # キャンセルボタンを有効化
        self.convertButton.setEnabled(False)  # 変換ボタンを無効化

        self.statusBar.showMessage('Converting...')
        self.convert_files(self.file_paths)

    # キャンセルボタン処理
    def cancel_conversion(self):
        # キャンセルボタンが押された場合、すべてのWorkerをキャンセル
        for worker in self.workers:
            worker.cancel()

        self.statusBar.showMessage('Conversion cancelled.')
        self.convertButton.setEnabled(True)
        self.cancelButton.setEnabled(False)

    # クリアボタン処理
    def clear_conversion(self):
        self.fileListWidget.clear()  # リストをクリア
        self.statusBar.showMessage('Clear lists.')

    # 変換処理
    def convert_files(self, file_paths):
        # スレッド数を指定して変換処理をマルチスレッドで行う
        self.thread_pool.setMaxThreadCount(self.threadsnum)  # スレッドプールの最大スレッド数を設定
        for file_path in file_paths:
            worker = Worker(file_path, self.outputdir, self.imgtype, self.quality, self.keepTimestamp, self.on_complete)
            self.workers.append(worker)  # Workerをリストに追加
            self.thread_pool.start(worker)  # スレッドプールにタスクを追加

    # 完了時処理
    def on_complete(self, success):
        # 変換が完了した後に呼ばれるコールバック
        if success:
            self.converted_files += 1

        # すべてのファイルが変換されたか確認
        if self.converted_files == self.totalfilenum:
            elapsed_time = time.time() - self.start_time  # 経過時間
            mes = f'Conversion complete! {self.converted_files} files converted in {elapsed_time:.2f} seconds.'
            self.statusBar.showMessage(mes)
            print(mes)
            self.convertButton.setEnabled(True)
            self.cancelButton.setEnabled(False)
            self.play_wave(self.soundok)
        else:
            mes = f'Converting... [{self.converted_files:0{self.totalfilestrlen}}/{self.totalfilenum:0{self.totalfilestrlen}}]'
            self.statusBar.showMessage(mes)
            pvsubfunc.dbgprint(mes)

    # 設定値更新時処理
    def update_jpgquality_values(self):
        self.quality = self.qualitySpinBox.value()
    def update_threadsnum_values(self):
        self.threadsnum = self.threadSpinBox.value()
    def update_keeptimestamp_check(self):
        self.keepTimestamp = self.keepTimestampCheckBox.isChecked()
    def update_imgtype_changed(self):
        self.imgtype = self.imgTypeComboBox.currentText()
    def update_outdir_changed(self):
        self.outputdir = self.outdirLineEdit.text()

    # ドラッグエンター
    def dragEnterEvent(self, event: QDragEnterEvent):
        event.acceptProposedAction()

    # ドラッグ＆ドロップ時
    def dropEvent(self, event: QDropEvent):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
        all_files = []
        self.fileListWidget.clear()  # リストをクリア

        # 似たような処理で二度手間になるが、ファイルの重複チェックを事前に行う
        duplicatefile = SdImageDiet.check_duplicate_file(file_paths, self.outputdir)
        if duplicatefile:
            self.statusBar.showMessage(f'Error : Duplicate output files. {duplicatefile}')
            self.play_wave(self.soundng)
            return

        # ドラッグ＆ドロップで受け取ったファイルまたはフォルダの処理
        for path in file_paths:
            if os.path.isdir(path):  # フォルダの場合
                all_files.extend(self.get_img_files_in_folder(path))
            elif path.lower().endswith(SdImageDiet.SUPPORT_INPUT_EXT):  # 対象画像ファイルの場合
                all_files.append(path)

        if all_files:
            self.fileListWidget.addItems(all_files)  # リストに追加

        self.statusBar.showMessage(f'Droped {len(all_files)} files.')
        if len(all_files) == 0:
            self.play_wave(self.soundng)

    def get_img_files_in_folder(self, folder_path):
        # フォルダ内の全ての画像ファイルを再帰的に取得
        img_files = []
        if os.path.basename(os.path.normpath(folder_path)) == self.outputdir:
            return img_files
        # 出力フォルダが含まれる場合には対象外とする
        for root, dirs, files in os.walk(folder_path):
            if os.path.basename(os.path.normpath(root)) == self.outputdir:
                continue
            for file in files:
                if file.lower().endswith(SdImageDiet.SUPPORT_INPUT_EXT):
                    #png_files.append(os.path.join(root, file))
                    img_files.append(f"{root}/{file}") #ファイルのドラッグドロップ時のパスセパレータに合わせる
        return img_files

    def play_wave(self, file_name):
        file_path = os.path.join(self.pydir, file_name)
        if not os.path.isfile(file_path): return
        sound = QSound(file_path)
        sound.play()
        while sound.isFinished() is False:
            app.processEvents()

    #設定ファイルの初期値作成
    def createSettingFile(self):
        self.save_settings()

    #設定ファイルの読込
    def load_settings(self):
        try:
            self.quality = int(str(pvsubfunc.read_value_from_config(SETTINGS_FILE, JPG_QUALITY)))
        except Exception as e:
            self.quality = 85
        if self.quality < 1 or self.quality > 100:
            self.quality = 85
        try:
            self.threadsnum = int(str(pvsubfunc.read_value_from_config(SETTINGS_FILE, THREADS_NUM)))
        except Exception as e:
            self.threadsnum = os.cpu_count() - 1
        if self.threadsnum < 1 or self.threadsnum > os.cpu_count():
            self.threadsnum = os.cpu_count() - 1
        if self.threadsnum < 1:
            self.threadsnum = 1 #今どき、1スレッドのCPUはないでしょうけど念の為
        self.keepTimestamp = pvsubfunc.read_value_from_config(SETTINGS_FILE, KEEP_TIMESTAMP)
        if self.keepTimestamp is None:
            self.keepTimestamp = True
        self.imgtype = pvsubfunc.read_value_from_config(SETTINGS_FILE, IMG_TYPE)
        if self.imgtype is None:
            self.imgtype = "jpg"
        self.outputdir = pvsubfunc.read_value_from_config(SETTINGS_FILE, OUTPUT_DIRNAME)
        if self.outputdir is None:
            self.outputdir = "__outputdir"
        self.soundok = pvsubfunc.read_value_from_config(SETTINGS_FILE, SOUND_OK)
        if self.soundok is None:
            self.soundok = "ok.wav"
        self.soundng = pvsubfunc.read_value_from_config(SETTINGS_FILE, SOUND_NG)
        if self.soundng is None:
            self.soundng = "ng.wav"

        #self.setGeometry(100, 100, 640, 480)    #位置とサイズ
        try:
            geox = pvsubfunc.read_value_from_config(SETTINGS_FILE, GEOMETRY_X)
            geoy = pvsubfunc.read_value_from_config(SETTINGS_FILE, GEOMETRY_Y)
            geow = pvsubfunc.read_value_from_config(SETTINGS_FILE, GEOMETRY_W)
            geoh = pvsubfunc.read_value_from_config(SETTINGS_FILE, GEOMETRY_H)
        except Exception as e:
            self.setGeometry(0, 0, 640, 480)    #位置とサイズ
        if any(val is None for val in [geox, geoy, geow, geoh]):
            self.setGeometry(0, 0, 640, 480)    #位置とサイズ
        else:
            self.setGeometry(geox, geoy, geow, geoh)    #位置とサイズ

    #設定ファイルの保存
    def save_settings(self):
        pvsubfunc.write_value_to_config(SETTINGS_FILE, IMG_TYPE, self.imgtype)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, JPG_QUALITY, self.quality)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, THREADS_NUM, self.threadsnum)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, KEEP_TIMESTAMP, self.keepTimestamp)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, OUTPUT_DIRNAME, self.outputdir)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, SOUND_OK, self.soundok)
        pvsubfunc.write_value_to_config(SETTINGS_FILE, SOUND_NG, self.soundng)

        pvsubfunc.write_value_to_config(SETTINGS_FILE, GEOMETRY_X, self.geometry().x())
        pvsubfunc.write_value_to_config(SETTINGS_FILE, GEOMETRY_Y, self.geometry().y())
        pvsubfunc.write_value_to_config(SETTINGS_FILE, GEOMETRY_W, self.geometry().width())
        pvsubfunc.write_value_to_config(SETTINGS_FILE, GEOMETRY_H, self.geometry().height())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
