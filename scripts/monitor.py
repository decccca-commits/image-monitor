import os
import time
import json
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ImageMonitor:
    def __init__(self):
        self.url = "https://svc01.p-counter.jp/v4shr3svr/shinko-sports/hakata-gym-train.html"
        self.xpath = '/html/body/div[1]/img'
        self.valid_paths = [
            'image/Lv1-image.png',
            'image/Lv2-image.png',
            'image/Lv3-image.png',
            'image/Lv4-image.png'
        ]
    
    def setup_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        return webdriver.Chrome(options=options)
    
    def check_image(self):
        driver = self.setup_driver()
        try:
            print(f"アクセス中: {self.url}")
            driver.get(self.url)
            
            # 要素が読み込まれるまで待機
            wait = WebDriverWait(driver, 10)
            img_element = wait.until(
                EC.presence_of_element_located((By.XPATH, self.xpath))
            )
            
            current_src = img_element.get_attribute('src')
            print(f"取得したsrc: {current_src}")

                        # current_srcがNoneの場合はエラーを返す
            if current_src is None:
                print("エラー: srcがNoneです")
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Image src attribute is None',
                    'is_valid': False,
                    'current_src': '',
                    'matched_level': ''
                }
            
            # レベル判定
            matched_level = None
            for path in self.valid_paths:
                if path in current_src:
                    matched_level = path.split('/')[-1].replace('-image.png', '')
                    break
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'current_src': current_src,
                'matched_level': matched_level,
                'is_valid': matched_level is not None,
                'full_url': current_src
            }
            
            print(f"結果: {result}")
            return result
            
        except Exception as e:
            print(f"エラー発生: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'is_valid': False,
                'current_src': '',
                'matched_level': ''
            }
        finally:
            driver.quit()
    
    def save_results(self, result):
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
    print("=== Image Monitoring Start ===")
    monitor = ImageMonitor()
    result = monitor.check_image()
    monitor.save_results(result)
    
    # 結果をサマリー出力
    if result['is_valid']:
        print(f"✅ 成功: {result['matched_level']} を検出")
    else:
        print(f"❌ 失敗: {result.get('error', '不明なエラー')}")
    
    print("=== Image Monitoring End ===")

if __name__ == "__main__":
    main()
