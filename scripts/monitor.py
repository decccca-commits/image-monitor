import os
import time
import csv
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pytesseract
from PIL import Image
import io

def retry_on_failure(func, max_retries=3, delay=5):
    """リトライ機能を持つラッパー関数"""
    for attempt in range(max_retries):
        try:
            result = func()
            if result:  # 成功した場合
                return result
            print(f"Attempt {attempt + 1} failed, retrying...")
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(delay)
    
    return None  # 全試行失敗

def setup_driver():
    """Chromeドライバーのセットアップ"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(options=chrome_options)

def extract_text_from_screenshot(driver):
    """スクリーンショットからテキストを抽出"""
    # スクリーンショットを取得
    screenshot = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(screenshot))
    
    # OCRでテキスト抽出
    text = pytesseract.image_to_string(image, lang='jpn')
    print(f"Extracted text: {text}")
    
    return text

53
def analyze_occupancy_from_text(text):
    """抽出テキストから混雑状況を判定"""
    text = text.lower()
    
 def analyze_occupancy_from_text(text):
    """抽出テキストから混雑状況を判定"""
    # テキストを最初の500文字に限定（メインコンテンツのみ）
    # これにより凡例部分を除外
    main_text = text[:500]
    
    # 大文字の英語表記を優先的にチェック（より確実）
    if "HALF-FULL" in text or "HALF FULL" in text:
        return "Lv3", "混雑しています"
    elif "ALMOST EMPTY" in text or "ALMOST-EMPTY" in text:
        return "Lv2", "やや混雑しています"
    elif "EMPTY" in text and "ALMOST" not in text:
        return "Lv1", "空いてます"
    elif "VERY CROWDED" in text or "FULL" in text and "HALF" not in text:
        return "Lv4", "非常に混雑しています"
    
    # 日本語でのフォールバックチェック（メインテキスト部分のみ）
    main_text_lower = main_text.lower()
    
    # 「現在の状況」の直後のテキストをチェック
    if "非常に混雑" in main_text or "非常に混" in main_text:
        return "Lv4", "非常に混雑しています"
    elif "混雑しています" in main_text and "やや" not in main_text.split("混雑しています")[0][-10:]:
        return "Lv3", "混雑しています"
    elif "やや混雑" in main_text:
        return "Lv2", "やや混雑しています"
    elif "空いてます" in main_text or "空いています" in main_text:
        return "Lv1", "空いてます"
    
    return None, "判定できませんでした"   try:
        driver = setup_driver()
        url = "https://svc01.p-counter.jp/v4shr3svr/shinko-sports/hakata-gym-train.html"
        
        print(f"Navigating to {url}")
        driver.get(url)
        
        # ページ読み込み待機
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # JavaScriptの実行完了を待つ
        time.sleep(10)
        
        # スクリーンショットからテキスト抽出
        extracted_text = extract_text_from_screenshot(driver)
        
        # 混雑状況の判定
        level, status = analyze_occupancy_from_text(extracted_text)
        
        return {
            "is_valid": level is not None,
            "matched_level": level if level else "Unknown",
            "status_text": status,
            "extracted_text_preview": extracted_text[:200] if extracted_text else ""
        }
        
    except Exception as e:
        print(f"Error occurred: {e}")
        return {
            "is_valid": False,
            "matched_level": "Error",
            "status_text": str(e),
            "extracted_text_preview": ""
        }
    finally:
        if driver:
            driver.quit()

def save_to_csv(data):
    """結果をCSVに保存"""
    csv_file = "results/monitor_log.csv"
    os.makedirs("results", exist_ok=True)
    
    # JST (UTC+9) のタイムゾーン
    jst = timezone(timedelta(hours=9))
    timestamp = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "is_valid", "matched_level", "status_text", "text_preview"])
        
        writer.writerow([
            timestamp,
            data["is_valid"],
            data["matched_level"],
            data["status_text"],
            data["extracted_text_preview"]
        ])
    
    print(f"Results saved to {csv_file}")

def main():
    """メイン実行関数"""
    print("Starting gym occupancy monitoring (screenshot text extraction method)...")
    
    # リトライ機能付きで監視実行
    result = retry_on_failure(monitor_page, max_retries=3, delay=5)
    
    if result is None:
        # 全試行失敗時のフォールバック
        result = {
            "is_valid": False,
            "matched_level": "AllRetriesFailed",
            "status_text": "全てのリトライが失敗しました",
            "extracted_text_preview": ""
        }
    
    # 結果を保存（成功・失敗に関わらず）
    save_to_csv(result)
    
    print(f"Monitoring complete. Result: {result}")

if __name__ == "__main__":
    main()
