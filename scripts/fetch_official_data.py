#!/usr/bin/env python3
"""Скачивает официальные bulk CSV с Dubai Pulse (транзакции DLD + договоры аренды).

Из-за пределов ОАЭ dubaipulse.gov.ae обычно недоступен (гео-блок) — этот
скрипт нужно запускать из сети внутри ОАЭ. Не требует установки пакетов:
используется только стандартная библиотека Python 3 (urllib).

Запуск:
    python fetch_official_data.py            # проверить доступность и скачать оба файла
    python fetch_official_data.py --check    # только проверить доступность, не скачивать
    python fetch_official_data.py --out ./data   # скачать в указанную папку

После скачивания пришли получившиеся файлы (transactions.csv, rent_contracts.csv)
тому, кто прислал этот скрипт.
"""
import argparse
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    # Консоль Windows часто не в UTF-8 — без этого кириллица превращается в кракозябры
    os.system("chcp 65001 >nul")
    sys.stdout.reconfigure(encoding="utf-8")

SOURCES = {
    "transactions.csv": (
        "https://www.dubaipulse.gov.ae/dataset/3b25a6f5-9077-49d7-8a1e-bc6d5dea88fd/"
        "resource/a37511b0-ea36-485d-bccd-2d6cb24507e7/download/transactions.csv"
    ),
    "rent_contracts.csv": (
        "https://www.dubaipulse.gov.ae/dataset/00768c45-f014-4cc6-937d-2b17dcab53fb/"
        "resource/765b5a69-ca16-4bfd-9852-74612f3c4ea6/download/rent_contracts.csv"
    ),
}

CHECK_URLS = {
    "Dubai Pulse (dubaipulse.gov.ae)": "https://www.dubaipulse.gov.ae",
    "Data.Dubai (data.dubai)": "https://data.dubai/en/",
}

CONNECT_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 120
CHUNK_SIZE = 1024 * 1024  # 1 MB
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def check_reachability() -> bool:
    print("Проверяю доступность официальных порталов...\n")
    any_ok = False
    for name, url in CHECK_URLS.items():
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT) as resp:
                print(f"  [OK]      {name}: доступен (HTTP {resp.status})")
                any_ok = True
        except urllib.error.HTTPError as exc:
            print(f"  [БЛОК]    {name}: сайт отвечает, но блокирует запрос (HTTP {exc.code})")
        except Exception as exc:  # noqa: BLE001 — нужен любой сетевой сбой, не только известные
            print(f"  [НЕДОСТ.] {name}: недоступен ({exc})")
    print()
    return any_ok


def download(url: str, dest: Path) -> bool:
    print(f"Скачиваю {dest.name}...")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            total = resp.getheader("Content-Length")
            total_bytes = int(total) if total else None
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    mb = downloaded / 1e6
                    if total_bytes:
                        pct = downloaded * 100 // total_bytes
                        print(f"\r  {mb:.1f} / {total_bytes / 1e6:.1f} МБ ({pct}%)", end="", flush=True)
                    else:
                        print(f"\r  {mb:.1f} МБ", end="", flush=True)
        print(f"\n  [OK] Готово: {dest} ({dest.stat().st_size / 1e6:.1f} МБ)\n")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"\n  [ОШИБКА] Не удалось скачать: {exc}\n")
        if dest.exists():
            dest.unlink()
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Скачивание официальных DLD bulk CSV с Dubai Pulse")
    parser.add_argument("--check", action="store_true", help="только проверить доступность")
    parser.add_argument("--out", default=".", help="папка для сохранения файлов")
    args = parser.parse_args()

    reachable = check_reachability()

    if args.check:
        return 0 if reachable else 1

    if not reachable:
        print("Оба портала не отвечают на проверку — попробую скачать всё равно")
        print("(возможно, заблокирован только один из них).\n")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {name: download(url, out_dir / name) for name, url in SOURCES.items()}

    print("=" * 50)
    print("Итог:")
    for name, ok in results.items():
        print(f"  {name}: {'скачан' if ok else 'НЕ скачан'}")

    if all(results.values()):
        print("\nВсё получилось. Отправь оба файла обратно тому, кто прислал этот скрипт.")
        return 0
    print("\nЧто-то не скачалось — пришли скриншот этого вывода целиком.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
