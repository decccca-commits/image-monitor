import os
import time
import json
import csv
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def retry_on_failure(func, max_retries=3, delay=5):
    """リトライ機構を持つラッパー関数"""
    for attempt in range(max_retries):
        try:
            print(f"試行 {attempt + 1}/{max_retries}")
            return func()
        except Exception as e:
            print(f"エラー発生 (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print(f"{delay}秒後にリトライします...")
                time.sleep(delay)
            else:
                print("最大リトライ回数に達しました")
                raise


class ImageMonitor:
    def __init__(self):
        self.url = "https://svc01.p-counter.jp/v4shr3svr/shinko-sports/hakata-gym-train.html"
        self.xpath = '//img[@id="logo"]'
        self.valid_paths = [
            'image/Lv1-image.png',
            'image/Lv2-image.png',
            'image/Lv3-image.png',
            'image/Lv4-image.png'
        ]

    def setup_driver(self):
        """Chrome WebDriverをセットアップ"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        return webdriver.Chrome(options=options)

    def check_image(self):
        """画像をチェックする"""
        driver = None
        try:
            print(f"アクセス中: {self.url}")
            driver = self.setup_driver()
            driver.get(self.url)

            # 要素が読み込まれるまで待機
            wait = WebDriverWait(driver, 30)
            img_element = wait.until(
                EC.presence_of_element_located((By.XPATH, self.xpath))
            )

            # 画像読み込みを追加で待つ
            time.sleep(2)

            current_src = img_element.get_attribute('src')
            print(f"取得したsrc: {current_src}")

            if current_src is None:
                raise ValueError("Image src attribute is None")

            # レベル判定
            matched_level = None
            for path in self.valid_paths:
                if path in current_src:
                    matched_level = path.split('/')[-1].replace('-image.png', '')
                    break

            result = {
                'timestamp': datetime.now(timezone(timedelta(hours=9))).isoformat(),
                'current_src': current_src,
                'matched_level': matched_level or '',
                'is_valid': matched_level is not None,
                'error': ''
            }

            print(f"結果: レベル={result['matched_level']}, 有効={result['is_valid']}")
            return result

        except Exception as e:
            print(f"エラー発生: {e}")
            return {
                'timestamp': datetime.now(timezone(timedelta(hours=9))).isoformat(),
                'error': str(e),
                'is_valid': False,
                'current_src': '',
                'matched_level': ''
            }
        finally:
            if driver:
                driver.quit()

    def save_results(self, result):
        """結果をCSVとJSONに保存"""
        # 結果ディレクトリの作成
        os.makedirs('results', exist_ok=True)

        # CSVファイルに保存
        csv_file = 'results/monitor_log.csv'
        file_exists = os.path.isfile(csv_file)

        with open(csv_file, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['timestamp', 'matched_level', 'is_valid', 'current_src', 'error']
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            writer.writerow({
                'timestamp': result['timestamp'],
                'matched_level': result.get('matched_level', ''),
                'is_valid': result['is_valid'],
                'current_src': result.get('current_src', ''),
                'error': result.get('error', '')
            })

        # 最新結果をJSONでも保存
        with open('results/latest.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"結果を保存しました: {csv_file}")


def main():
    """メイン処理"""
    print("=== 画像監視システム開始 ===")

    monitor = ImageMonitor()

    # リトライ機構付きでチェック実行
    try:
        result = retry_on_failure(monitor.check_image, max_retries=3, delay=5)
        monitor.save_results(result)

        # 結果をサマリー出力
        if result['is_valid']:
            print(f"✅ 成功: {result['matched_level']} を検出")
        else:
            print(f"⚠️ 警告: 有効な画像が検出されませんでした")

    except Exception as e:
        # 最終的に失敗した場合もエラー情報を保存
        error_result = {
            'timestamp': datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'error': str(e),
            'is_valid': False,
            'current_src': '',
            'matched_level': ''
        }
        monitor.save_results(error_result)
        print(f"❌ 失敗: {e}")

    print("=== 画像監視システム終了 ===")


if __name__ == "__main__":
    main()
