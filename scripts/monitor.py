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
    for attempt in range(max_retries):
        try:
            result = func()
            if result:
                return result
            print(f"Attempt {attempt + 1} failed, retrying...")
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    return None

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=chrome_options)

def extract_text_from_screenshot(driver):
    screenshot = driver.get_screenshot_as_png()
    image = Image.open(io.BytesIO(screenshot))
    text = pytesseract.image_to_string(image, lang='jpn')
    print(f"Extracted text: {text}")
    return text

def analyze_occupancy_from_text(text):
    main_text = text[:500]
    
    # メンテナンス中の判定を最優先
    if "メンテナンス" in main_text or "メンテナンス中" in main_text or "maintenance" in main_text.lower():
        return None, "メンテナンス中のため判定不可"
    
    if "HALF-FULL" in text or "HALF FULL" in text:
        return "Lv3", "混雑しています"
    
    # 日本語表記を優先して判定
    if "非常に混雑" in main_text:
        return "Lv4", "非常に混雑しています"
    elif "混雑しています" in main_text and "やや" not in main_text:
        return "Lv3", "混雑しています"
    elif "やや混雑" in main_text:
        return "Lv2", "やや混雑しています"
    elif "空いてます" in main_text or "EMPTY" in main_text:
        return "Lv1", "空いてます"
    
    return None, "判定できませんでした"

def monitor_page():
    driver = None
    try:
        driver = setup_driver()
        url = "https://svc01.p-counter.jp/v4shr3svr/shinko-sports/hakata-gym-train.html"
        print(f"Navigating to {url}")
        driver.get(url)
        
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(10)
        
        extracted_text = extract_text_from_screenshot(driver)
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
    csv_file = "results/monitor_log.csv"
    os.makedirs("results", exist_ok=True)
    
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
    print("Starting gym occupancy monitoring (screenshot text extraction method)...")
    
    # メンテナンス中の場合のリトライ設定
    max_maintenance_retries = 3
    maintenance_retry_delay = 30  # 30秒待機
    
    for maintenance_attempt in range(max_maintenance_retries):
        result = retry_on_failure(monitor_page, max_retries=3, delay=5)
        
        if result is None:
            result = {
                "is_valid": False,
                "matched_level": "AllRetriesFailed",
                "status_text": "全てのリトライが失敗しました",
                "extracted_text_preview": ""
            }
        
        # メンテナンス中でない場合は結果を保存して終了
        if result["is_valid"] or result["matched_level"] == "Error" or result["matched_level"] == "AllRetriesFailed":
            save_to_csv(result)
            print(f"Monitoring complete. Result: {result}")
            break
        
        # メンテナンス中の場合
        if "メンテナンス中" in result["status_text"]:
            print(f"メンテナンス中を検出 (試行 {maintenance_attempt + 1}/{max_maintenance_retries})")
            
            # 最後の試行の場合は結果を保存して終了
            if maintenance_attempt == max_maintenance_retries - 1:
                save_to_csv(result)
                print(f"メンテナンス中のため、{max_maintenance_retries}回の試行後に終了します")
                print(f"Monitoring complete. Result: {result}")
            else:
                # 次の試行まで待機
                print(f"{maintenance_retry_delay}秒後に再試行します...")
                time.sleep(maintenance_retry_delay)
        else:
            # その他の判定不可の場合は結果を保存して終了
            save_to_csv(result)
            print(f"Monitoring complete. Result: {result}")
            break

if __name__ == "__main__":
    main()
