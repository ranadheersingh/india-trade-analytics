#!/usr/bin/env python3
"""
TRADESTAT Auto-Downloader (FINAL VERSION)
==========================================
Downloads ALL data automatically:
- All 8 years (2017-18 to 2024-25)
- All ~50 regions (auto-detected)
- Both EXPORT and IMPORT directions

Total: 8 × 51 × 2 = 816 files
Time: ~2-3 hours

USAGE:
    python3 tradestat_downloader.py                    # Download everything
    python3 tradestat_downloader.py --resume           # Skip existing files
    python3 tradestat_downloader.py --no-regions       # World only (16 files)
    python3 tradestat_downloader.py --max-regions 5    # Test with 5 regions
"""

import argparse
import csv
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("tradestat")

PROJECT_ROOT = Path(__file__).resolve().parent
# If running from auto_run/, go up one level
if PROJECT_ROOT.name in ('auto_run', 'scripts'):
    PROJECT_ROOT = PROJECT_ROOT.parent

# Always use absolute path for data dir
DATA_DIR = PROJECT_ROOT / "backend" / "app" / "data" / "tradestat"

ALL_YEARS = [
    "2020-2021","2021-2022", "2022-2023", "2023-2024", "2024-2025"
]

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@india-trade.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

WAIT_TIMEOUT = 60
DOWNLOAD_TIMEOUT = 30


# ============================================================================
# DRIVER
# ============================================================================

def create_driver(headless: bool = False):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_dir = str(DATA_DIR.absolute())
    
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ============================================================================
# DROPDOWN HELPERS
# ============================================================================

def find_year_dropdown(driver) -> Optional[str]:
    return driver.execute_script("""
        var selects = document.querySelectorAll('select');
        for (var i = 0; i < selects.length; i++) {
            var s = selects[i];
            var name = s.getAttribute('name') || '';
            var id = s.id || '';
            if (name.toLowerCase().includes('year') || 
                id.toLowerCase().includes('year')) {
                return id || name;
            }
        }
        return null;
    """)


def find_region_dropdown(driver) -> Optional[str]:
    """Region dropdown has many options and isn't year/level/value"""
    return driver.execute_script("""
        var selects = document.querySelectorAll('select');
        for (var i = 0; i < selects.length; i++) {
            var s = selects[i];
            var name = (s.getAttribute('name') || '').toLowerCase();
            var id = (s.id || '').toLowerCase();
            
            if (name.includes('year') || id.includes('year')) continue;
            if (name.includes('level') || id.includes('level') ||
                name.includes('digit') || id.includes('digit')) continue;
            if (name.includes('value') || id.includes('value') ||
                name.includes('unit') || id.includes('unit')) continue;
            
            // Region dropdown has many options
            if (s.options.length > 5) {
                return s.id || s.getAttribute('name');
            }
        }
        return null;
    """)


def get_all_regions(driver, region_dd: str) -> List[Dict]:
    """Get all options - filter out group headers"""
    return driver.execute_script(f"""
        var sel = document.getElementById('{region_dd}') ||
                  document.querySelector('select[name="{region_dd}"]');
        if (!sel) return [];
        var opts = [];
        for (var i = 0; i < sel.options.length; i++) {{
            var opt = sel.options[i];
            var html = opt.innerHTML;
            var isGroup = html.includes('<strong>') || html.includes('<b>');
            opts.push({{
                value: opt.value,
                text: opt.text.trim(),
                isGroup: isGroup
            }});
        }}
        return opts;
    """)


def select_dropdown(driver, dropdown_id: str, value: str) -> bool:
    js = f"""
    var sel = document.getElementById('{dropdown_id}');
    if (!sel) sel = document.querySelector('select[name="{dropdown_id}"]');
    if (!sel) return 'not_found';
    
    sel.value = '{value}';
    if (sel.value !== '{value}') return 'value_not_set:' + sel.value;
    
    sel.dispatchEvent(new Event('input', {{ bubbles: true }}));
    sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
    
    if (typeof Livewire !== 'undefined') {{
        try {{
            var wireId = sel.closest('[wire\\\\:id]')?.getAttribute('wire:id');
            if (wireId) {{
                Livewire.find(wireId).set('{dropdown_id}', '{value}');
            }}
        }} catch(e) {{}}
    }}
    return 'success:' + sel.value;
    """
    try:
        result = driver.execute_script(js)
        logger.debug(f"   {dropdown_id}={value}: {result}")
        return result.startswith('success')
    except Exception as e:
        logger.debug(f"   Exception in select_dropdown: {e}")
        return False


def submit_form(driver) -> bool:
    js = """
    var form = document.querySelector('form[action*="commodities"]') ||
               document.querySelector('form');
    if (!form) return 'no_form';
    var btn = form.querySelector('button[type="submit"]') ||
              form.querySelector('button');
    if (btn) { btn.click(); return 'clicked'; }
    form.submit();
    return 'submitted';
    """
    try:
        return driver.execute_script(js) in ['clicked', 'submitted']
    except:
        return False


def click_excel_button(driver) -> bool:
    js = """
    var buttons = document.querySelectorAll('button, a.dt-button');
    for (var i = 0; i < buttons.length; i++) {
        if (buttons[i].textContent.trim() === 'Excel') {
            buttons[i].click(); return 'clicked';
        }
    }
    var ex = document.querySelector('.buttons-excel');
    if (ex) { ex.click(); return 'clicked'; }
    return 'not_found';
    """
    try:
        return driver.execute_script(js) == 'clicked'
    except:
        return False


def wait_for_table(driver, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if driver.execute_script("""
            return document.querySelector('table tbody tr') !== null;
        """):
            return True
        time.sleep(1)
    return False


def wait_for_download(timeout: int = 30) -> Optional[Path]:
    start = time.time()
    while time.time() - start < timeout:
        crdownload = list(DATA_DIR.glob("*.crdownload"))
        if not crdownload:
            files = list(DATA_DIR.glob("TradeStat*.xlsx"))
            if files:
                latest = max(files, key=lambda p: p.stat().st_mtime)
                if time.time() - latest.stat().st_mtime < 60:
                    return latest
        time.sleep(1)
    return None


def safe_filename(s: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', s.lower()).strip('-')


# ============================================================================
# DOWNLOAD ONE
# ============================================================================

def download_one(driver, year: str, direction: str,
                 region_value: Optional[str] = None,
                 region_name: Optional[str] = None,
                 resume: bool = False) -> bool:
    
    short_year = f"{year[:4]}-{year[-2:]}"
    
    if region_name and region_value:
        region_slug = safe_filename(region_name)
        target_xlsx = DATA_DIR / f"{direction}_{short_year}_{region_slug}.xlsx"
        target_csv = DATA_DIR / f"{direction}_{short_year}_{region_slug}.csv"
    else:
        target_xlsx = DATA_DIR / f"{direction}_{short_year}.xlsx"
        target_csv = DATA_DIR / f"{direction}_{short_year}.csv"
    
    # Resume: skip if both files exist
    if resume and target_xlsx.exists() and target_csv.exists():
        logger.info(f"   ⏭️  exists: {target_xlsx.name}")
        return True
    
    url = f"https://tradestat.commerce.gov.in/eidb/region_wise_all_commodities_{direction}"
    year_value = year.split("-")[0]
    
    try:
        region_str = f" / {region_name}" if region_name else " / WORLD"
        logger.info(f"   📥 {direction.upper()} {year}{region_str}...")
        driver.get(url)
        time.sleep(5)
        
        # Year
        year_dd = find_year_dropdown(driver)
        if not year_dd:
            logger.error("   ❌ Year dropdown not found")
            return False
        
        if not select_dropdown(driver, year_dd, year_value):
            logger.error(f"   ❌ Year selection failed")
            return False
        time.sleep(1)
        
        # Region (if specified)
        if region_value:
            region_dd = find_region_dropdown(driver)
            if region_dd:
                if not select_dropdown(driver, region_dd, region_value):
                    logger.error(f"   ❌ Region selection failed")
                    return False
                time.sleep(1)
        
        # Submit
        if not submit_form(driver):
            logger.error("   ❌ Submit failed")
            return False
        
        if not wait_for_table(driver, timeout=60):
            logger.error("   ❌ Table never loaded")
            return False
        time.sleep(3)
        
        if not click_excel_button(driver):
            logger.error("   ❌ Excel button failed")
            return False
        
        downloaded = wait_for_download(timeout=DOWNLOAD_TIMEOUT)
        
        if downloaded:
            shutil.move(str(downloaded), str(target_xlsx))
            logger.info(f"   ✅ Saved: {target_xlsx.name}")
            
            # Convert immediately
            if convert_xlsx_to_csv(target_xlsx, target_csv):
                logger.debug(f"   📝 Converted to CSV")
            return True
        else:
            logger.error(f"   ❌ Download timeout")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ {type(e).__name__}: {str(e)[:100]}")
        return False


# ============================================================================
# CONVERTER (inline so it runs immediately after each download)
# ============================================================================

def convert_xlsx_to_csv(xlsx_path: Path, csv_path: Path) -> bool:
    import openpyxl
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=True))
        
        header_idx = None
        for i, row in enumerate(all_rows):
            row_str = ' '.join(str(c).upper() for c in row if c is not None)
            if 'HSCODE' in row_str or 'HS CODE' in row_str:
                header_idx = i
                break
        
        if header_idx is None:
            return False
        
        clean_rows = all_rows[header_idx:]
        clean_rows = [r for r in clean_rows if any(c is not None and str(c).strip() for c in r)]
        
        if len(clean_rows) < 2:
            return False
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in clean_rows:
                writer.writerow(['' if c is None else str(c) for c in row])
        return True
    except Exception:
        return False


# ============================================================================
# DETECT REGIONS
# ============================================================================

def detect_all_regions(driver) -> List[Dict]:
    logger.info("🔍 Detecting available regions...")
    
    driver.get("https://tradestat.commerce.gov.in/eidb/region_wise_all_commodities_export")
    time.sleep(5)
    
    region_dd = find_region_dropdown(driver)
    if not region_dd:
        logger.error("   ❌ Could not find region dropdown")
        return []
    
    logger.info(f"   Region dropdown: {region_dd}")
    
    all_opts = get_all_regions(driver, region_dd)
    leaf_regions = [
        o for o in all_opts 
        if not o['isGroup'] and o['text'] and o['value']
    ]
    
    logger.info(f"   Total options: {len(all_opts)}")
    logger.info(f"   Group headers (skipped): {len([o for o in all_opts if o['isGroup']])}")
    logger.info(f"   Downloadable regions: {len(leaf_regions)}")
    
    return leaf_regions


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def download_all(years: List[str], regions: List[Dict],
                 include_world: bool = True, resume: bool = False,
                 headless: bool = False) -> Tuple[int, int]:
    
    logger.info("=" * 70)
    logger.info("📥 DOWNLOADING TRADESTAT DATA")
    logger.info("=" * 70)
    
    driver = create_driver(headless=headless)
    
    try:
        directions = ["export", "import"]
        tasks = []
        
        # World totals first
        if include_world:
            for year in years:
                for direction in directions:
                    tasks.append((year, direction, None, None))
        
        # Then regions
        for year in years:
            for region in regions:
                for direction in directions:
                    tasks.append((year, direction, region['value'], region['text']))
        
        total = len(tasks)
        n_world = len(years) * len(directions) if include_world else 0
        n_regional = len(years) * len(regions) * len(directions)
        
        logger.info(f"   Years: {len(years)}")
        logger.info(f"   Regions: {len(regions)}")
        logger.info(f"   WORLD totals: {n_world}")
        logger.info(f"   Regional files: {n_regional}")
        logger.info(f"   TOTAL: {total} files")
        logger.info(f"   Estimated time: {total * 12 / 60:.0f} minutes")
        logger.info("")
        
        success = 0
        for i, (year, direction, region_value, region_name) in enumerate(tasks, 1):
            logger.info(f"[{i}/{total}]")
            if download_one(driver, year, direction, region_value, region_name, resume):
                success += 1
            time.sleep(2)
            
            # Progress update every 20 files
            if i % 20 == 0:
                pct = 100 * success / i
                eta = (total - i) * 12 / 60
                logger.info(f"\n   📊 Progress: {success}/{i} ({pct:.0f}%) | ETA: {eta:.0f} min\n")
        
        logger.info(f"\n   📊 FINAL: {success}/{total}")
        return success, total
        
    except KeyboardInterrupt:
        logger.warning("Interrupted by user - resume with --resume flag")
        return 0, 0
    finally:
        try:
            driver.quit()
        except:
            pass


def trigger_pipeline() -> bool:
    import requests
    logger.info("=" * 70)
    logger.info("🚀 TRIGGERING DATABASE LOAD")
    logger.info("=" * 70)
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10
        )
        token = resp.json()["access_token"]
        logger.info("   🔐 Authenticated")
        
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/admin/ingestion/trigger/tradestat",
            headers={"Authorization": f"Bearer {token}"}, timeout=30
        )
        logger.info(f"   ✅ Triggered")
        
        # Wait based on file count (more files = more time)
        n_files = len(list(DATA_DIR.glob("*.csv")))
        wait_time = max(60, n_files * 2)  # 2s per file minimum
        logger.info(f"   ⏳ Waiting {wait_time}s for pipeline...")
        time.sleep(wait_time)
        return True
    except Exception as e:
        logger.error(f"   ❌ {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="TRADESTAT Auto-Downloader")
    parser.add_argument("--year", help="Specific year (e.g., 2024-2025)")
    parser.add_argument("--years", nargs="+")
    parser.add_argument("--no-regions", action="store_true",
                       help="Skip regional data, world only")
    parser.add_argument("--max-regions", type=int,
                       help="Limit regions (for testing)")
    parser.add_argument("--resume", action="store_true",
                       help="Skip already-downloaded files")
    parser.add_argument("--no-trigger", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info("")
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║   TRADESTAT - FULL AUTOMATION                                ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info(f"📁 Data dir: {DATA_DIR.absolute()}")
    logger.info("")
    
    # Determine years
    years = [args.year] if args.year else (args.years or ALL_YEARS)
    
    # Determine regions
    regions = []
    if not args.no_regions:
        # Detect regions
        driver = create_driver(headless=args.headless)
        try:
            regions = detect_all_regions(driver)
            if args.max_regions:
                regions = regions[:args.max_regions]
                logger.info(f"   Limited to {args.max_regions} regions")
        finally:
            driver.quit()
        
        if not regions:
            logger.warning("No regions detected, downloading WORLD only")
    
    # Download everything
    download_all(years, regions, 
                 include_world=True, 
                 resume=args.resume,
                 headless=args.headless)
    logger.info("")
    
    # Trigger pipeline
    if not args.no_trigger:
        trigger_pipeline()
    
    logger.info("")
    logger.info("🎉 DOWNLOAD COMPLETE")


if __name__ == "__main__":
    sys.exit(main())
