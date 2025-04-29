import json
import datetime
import logging
import threading

#Debug code 0:disable, 1:enable
_IS_DEBUG = 0

#----------------------------------------
# function
#----------------------------------------
#for debug
def dbgprint(message):
    if _IS_DEBUG:
        # date time string
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        # print message
        print(f"[{timestamp}] {message}")

#json形式の設定ファイルから指定されたキーの値を読み込む（初期値指定あり）
def read_value_from_config(config_file, key, defvalue=None):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        result = config_data.get(key, None)
        if result == None and defvalue != None:
            result = defvalue
        return result

    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {config_file}")
        return None
    except json.JSONDecodeError:
        print(f"エラー: 設定ファイルが正しいjson形式ではありません: {config_file}")
        return None

#json形式の設定ファイルへ指定されたキーの値を書き込む
def write_value_to_config(config_file, key, value):
    try:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}
        config_data[key] = value
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True

    except Exception as e:
        print(f"エラー: 設定ファイルへの書き込み中に問題が発生しました: {e}")
        return False

#json形式の設定ファイルから指定されたlistの値を読み込む
def read_list_from_config(config_file, key):
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        if key not in config_data:
            print(f"エラー: キー '{key}' が設定ファイルに存在しません")
            return None
        if not isinstance(config_data[key], list):
            print(f"エラー: キー '{key}' の内容がリスト型ではありません")
            return None

        return config_data.get(key, None)

    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {config_file}")
        return None
    except json.JSONDecodeError:
        print(f"エラー: 設定ファイルが正しいjson形式ではありません: {config_file}")
        return None

#json形式の設定ファイルへ指定されたキーの値を書き込む
def write_list_from_config(config_file, key, datalist):
    if not isinstance(datalist, list):
        print(f"エラー: data_listはリスト型である必要があります: {e}")
        return False

    try:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}
        config_data[key] = datalist
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"エラー: 設定ファイルへの書き込み中に問題が発生しました: {e}")
        return False

#----------------------------------------
# class
#----------------------------------------
class ThreadSafeLogger:
    def __init__(self, log_file: str):
        self.log_lock = threading.Lock()

        self.logger = logging.getLogger(log_file)
        self.logger.setLevel(logging.INFO)
        log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)

    def log(self, level: str, message: str):
        with self.log_lock:
            if level.lower() == "info":
                self.logger.info(message)
            elif level.lower() == "warning":
                self.logger.warning(message)
            elif level.lower() == "error":
                self.logger.error(message)
            elif level.lower() == "debug":
                self.logger.debug(message)
            else:
                self.logger.info(f"Unknown level: {message}")

    def errlog(self, message: str):
        self.log("error", message)
"""
スレッドセーフなログ書き出し
# 使用例
logger = ThreadSafeLogger("example.log")
#logger.setLevel(logging.WARNING ) # ログレベルをWARNINGに設定（デフォルト）
#logger.setLevel(logging.DEBUG) # ログレベルをDEBUGに設定
logger.log("info", f"hoge-info.")
logger.log("debug", f"hoge-debug.")
logger.log("warning", f"hoge-warning.")
logger.log("error", f"hoge-error.")
logger.errlog(f"hogehoge-error.")

# 結果
※DEBUGはログレベルをDEBUGに設定しないと出力されない
2025-01-02 18:41:14,632 [INFO] hoge-info.
2025-01-02 18:41:14,636 [WARNING] hoge-warning.
2025-01-02 18:41:14,643 [ERROR] hoge-error.
2025-01-02 18:41:14,643 [ERROR] hogehoge-error.
"""
