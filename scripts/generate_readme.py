#!/usr/bin/env python3
"""Генератор README.md для репозитория awesome-ai-tools-ru из публичного API ai-webcatalog.space."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any

BASE_URL = "https://ai-webcatalog.space"
USER_AGENT = "awesome-ai-tools-ru-generator/1.0"
MIN_TOOLS_REQUIRED = 40

ADULT_CATEGORY_SLUGS = {"adult-18-plus", "uncategorized", "companions"}
STOP_WORDS = (
    "18+",
    "взрослых",
    "nsfw",
    "adult",
    "эротик",
    "порно",
    "секс",
    "undress",
    "hentai",
    "персональные ии и компаньоны",
    "lovix",
    "wildgrl",
    "erosai",
    "noxie",
    "caichat",
    "yollo",
    "crushon",
)

SECTIONS: list[dict[str, Any]] = [
    {
        "title": "Чат-боты и ИИ-ассистенты",
        "anchor": "чат-боты-и-ии-ассистенты",
        "categories": ["chatbots"],
        "primary_category": "chatbots",
        "limit": 10,
        "priority": [
            "chatgpt-com",
            "claude-ai",
            "deepseek-com",
            "perplexity-ai",
            "alice-yandex-ru",
            "giga-chat",
            "chat-qwen-ai",
            "poe-com",
            "x-ai",
            "chat-z-ai",
        ],
    },
    {
        "title": "Универсальные ИИ-платформы",
        "anchor": "универсальные-ии-платформы",
        "categories": ["universal-ai-platforms"],
        "primary_category": "universal-ai-platforms",
        "limit": 10,
        "priority": [
            "syntx-ai",
            "chadgpt-ru",
            "mashagpt-ru",
            "stiva-ai",
            "iskrabot-ru",
            "leingpt-ru",
            "starproai-ru",
            "uniset-ai",
            "study24-ai",
            "imigo-ai",
        ],
    },
    {
        "title": "Изображения и дизайн",
        "anchor": "изображения-и-дизайн",
        "categories": ["image-generation", "design"],
        "primary_category": "image-generation",
        "limit": 10,
        "priority": [
            "midjourney-com",
            "recraft-ai",
            "krea-ai",
            "magnific-com",
            "shedevrum-ai",
            "spectrkit-ru",
            "seaart-ai",
            "fotee-ru",
            "faceai-art",
            "flux-ai",
        ],
    },
    {
        "title": "Видео и монтаж",
        "anchor": "видео-и-монтаж",
        "categories": ["video-generation", "video-editing"],
        "primary_category": "video-generation",
        "limit": 10,
        "priority": [
            "pika-art",
            "lumalabs-ai",
            "colossyan-com",
            "deepbrain-io",
            "magiclight-ai",
            "artlist-io",
            "frameo-ai",
            "cliptrend-ai",
            "pixmax-ai",
            "heygen-com",
        ],
    },
    {
        "title": "Музыка, голос и расшифровка",
        "anchor": "музыка-голос-и-расшифровка",
        "categories": ["audio-music", "voice-speech", "transcription"],
        "primary_category": "audio-music",
        "limit": 10,
        "priority": [
            "suno-ai",
            "udio-com",
            "speech2text-ru",
            "aiva-ai",
            "soundraw-io",
            "songhit-ru",
            "easysong-ru",
            "freesong-ai",
            "tunee-ai",
            "speaktor-com",
        ],
    },
    {
        "title": "Кодинг и LLM-агрегаторы",
        "anchor": "кодинг-и-llm-агрегаторы",
        "categories": ["coding", "llm-aggregators", "no-code"],
        "primary_category": "coding",
        "limit": 10,
        "priority": [
            "cursor-com",
            "kiro-dev",
            "replit-com",
            "opencode-ai",
            "antigravity-google",
            "routerai-ru",
            "polza-ai",
            "caila-io",
            "gen-api-ru",
            "together-ai",
        ],
    },
    {
        "title": "ИИ-агенты и автоматизация",
        "anchor": "ии-агенты-и-автоматизация",
        "categories": ["ai-agents", "automation"],
        "primary_category": "ai-agents",
        "limit": 9,
        "priority": [
            "manus-im",
            "albato-ru",
            "langfuse-com",
            "chatbase-co",
            "cognee-ai",
            "dokaai-ru",
            "kodacode-ru",
            "agentx-so",
            "aionlabs-ai",
            "kimi-com",
        ],
    },
    {
        "title": "Текст, презентации и поиск",
        "anchor": "текст-презентации-и-поиск",
        "categories": [
            "text-generation",
            "presentations",
            "research-search",
            "meetings-notes",
            "documents-ocr",
            "marketing-seo",
        ],
        "primary_category": "text-generation",
        "limit": 9,
        "priority": [
            "elicit-com",
            "gamma-app",
            "notion-so",
            "jasper-ai",
        ],
    },
]

PRICING_LABELS = {
    "free": "Бесплатно",
    "freemium": "Фримиум",
    "trial": "Триал",
    "paid": "Платно",
    "pay_as_you_go": "По факту",
    "one_time": "Разово",
    "contact": "По запросу",
}

PERIOD_SUFFIX = {
    "month": "/мес",
    "year": "/год",
}

CURRENCY_FORMATS = {
    "RUB": ("", " ₽"),
    "USD": ("$", ""),
    "EUR": ("€", ""),
}

RU_PAYMENT_PRIORITY = [
    ("sbp", "СБП"),
    ("mir", "Мир"),
    ("sberpay", "SberPay"),
    ("tpay", "T-Pay"),
    ("yoomoney", "ЮMoney"),
    ("alfa_pay", "Alfa Pay"),
    ("yandex_pay", "Яндекс Пэй"),
    ("crypto", "Крипта"),
    ("telegram_stars", "TG Stars"),
]

FOREIGN_PAYMENT_SLUGS = {
    "visa",
    "mastercard",
    "amex",
    "jcb",
    "discover",
    "diners_club",
    "unionpay",
    "card",
    "paypal",
    "apple_pay",
    "google_pay",
    "link",
    "cashapp",
    "alipay",
    "wechat_pay",
    "klarna",
    "afterpay_clearpay",
    "amazon_pay",
    "revolut_pay",
    "ideal",
    "bancontact",
    "sepa_direct_debit",
    "blik",
    "pix",
    "upi",
    "ach_direct_debit",
    "bank_transfer",
}


def fetch_json(path: str, retries: int = 2) -> Any:
    """Выполняет GET-запрос к публичному API и декодирует JSON."""
    url = f"{BASE_URL}{path}"
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_err = err
            if attempt == retries:
                raise
    raise RuntimeError(f"Не удалось получить {url}: {last_err}")


def contains_stop_word(*parts: Any) -> bool:
    """Проверяет строки и списки строк на наличие 18+/NSFW-маркеров."""
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, list):
            chunks.extend(str(item) for item in part if item)
        elif part:
            chunks.append(str(part))
    haystack = " ".join(chunks).lower()
    return any(word in haystack for word in STOP_WORDS)


def is_clean_category(cat: dict[str, Any]) -> bool:
    slug = str(cat.get("slug") or "").lower()
    name = str(cat.get("name") or "")
    if slug in ADULT_CATEGORY_SLUGS:
        return False
    return not contains_stop_word(slug, name)


def is_clean_collection(col: dict[str, Any]) -> bool:
    slug = str(col.get("slug") or "").lower()
    name = str(col.get("name") or "")
    return not contains_stop_word(slug, name)


def is_clean_tool(item: dict[str, Any]) -> bool:
    return not contains_stop_word(
        item.get("slug"),
        item.get("name"),
        item.get("short_description"),
        item.get("description"),
        item.get("categories"),
    )


def fetch_category_tools(cat_slug: str, max_pages: int = 2) -> list[dict[str, Any]]:
    """Загружает до max_pages страниц инструментов из категории."""
    collected: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        data = fetch_json(f"/api/catalog/tools?lang=ru&category={cat_slug}&page={page}")
        items = data.get("items") or []
        collected.extend(items)
        total_pages = int(data.get("total_pages") or 1)
        if page >= total_pages:
            break
    return collected


def select_candidates(
    category_pools: dict[str, list[dict[str, Any]]],
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Отбирает кандидатов по 8 разделам без дублей и с запасом под дофильтрацию."""
    used_slugs: set[str] = set()
    section_candidates: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    for section in SECTIONS:
        by_slug: dict[str, dict[str, Any]] = {}
        ordered: list[dict[str, Any]] = []
        for cat_slug in section["categories"]:
            for item in category_pools.get(cat_slug, []):
                slug = item.get("slug")
                if not slug or slug in used_slugs or slug in by_slug:
                    continue
                if not is_clean_tool(item):
                    continue
                if not ((item.get("short_description") or item.get("description") or "").strip()):
                    continue
                by_slug[slug] = item
                ordered.append(item)

        picked: list[dict[str, Any]] = []
        picked_slugs: set[str] = set()

        for p_slug in section["priority"]:
            if p_slug in by_slug and p_slug not in picked_slugs:
                picked.append(by_slug[p_slug])
                picked_slugs.add(p_slug)

        for item in ordered:
            slug = item["slug"]
            if slug not in picked_slugs:
                picked.append(item)
                picked_slugs.add(slug)
            if len(picked) >= section["limit"] + 6:
                break

        for item in picked:
            used_slugs.add(item["slug"])

        section_candidates.append((section, picked))

    return section_candidates


def fetch_details_parallel(slugs: list[str]) -> dict[str, dict[str, Any]]:
    """Параллельно подгружает карточки инструментов для получения URL, тарифов и способов оплаты."""
    details: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        future_map = {
            pool.submit(fetch_json, f"/api/catalog/tools/{slug}?lang=ru"): slug
            for slug in slugs
        }
        for future in as_completed(future_map):
            slug = future_map[future]
            try:
                details[slug] = future.result()
            except Exception as err:
                print(f"Предупреждение: не удалось загрузить {slug}: {err}", file=sys.stderr)
    return details


def clean_markdown_cell(text: str) -> str:
    """Убирает переносы строк, markdown-разметку и вертикальные черты для таблицы."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`]+", "", text)
    text = text.replace("|", "/").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def plural_services(n: int) -> str:
    """Возвращает корректное склонение слова «сервис»."""
    mod100 = abs(n) % 100
    mod10 = abs(n) % 10
    if 11 <= mod100 <= 14:
        return f"{n} сервисов"
    if mod10 == 1:
        return f"{n} сервис"
    if 2 <= mod10 <= 4:
        return f"{n} сервиса"
    return f"{n} сервисов"


def format_summary(short_desc: str) -> str:
    """Оставляет 1–2 понятных законченных предложения до ~155 символов."""
    cleaned = clean_markdown_cell(short_desc)
    if not cleaned:
        return "—"

    sentences = re.split(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z0-9«\"])", cleaned)
    first = sentences[0].strip()
    if len(first) < 50 and len(sentences) > 1:
        combined = f"{first} {sentences[1].strip()}"
        if len(combined) <= 165:
            return combined

    if len(first) <= 155:
        return first

    cut = first[:152].rsplit(" ", 1)[0].rstrip(",;:-")
    return f"{cut}…"


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_pricing(detail: dict[str, Any]) -> str:
    """Форматирует модель тарификации и минимальную платную цену."""
    pricing_code = str(detail.get("pricing") or "").lower()
    base_label = PRICING_LABELS.get(pricing_code, "—")

    plans = detail.get("pricing_plans") or []
    paid_plans = [
        p
        for p in plans
        if not p.get("is_free")
        and isinstance(p.get("price"), (int, float))
        and float(p["price"]) > 0
    ]

    if not paid_plans:
        return base_label

    currency_rank = {"RUB": 0, "USD": 1, "EUR": 2}
    paid_plans.sort(
        key=lambda p: (
            currency_rank.get(str(p.get("currency") or "").upper(), 9),
            float(p["price"]),
        )
    )
    best = paid_plans[0]
    currency = str(best.get("currency") or "").upper()
    prefix, suffix = CURRENCY_FORMATS.get(currency, ("", f" {currency}" if currency else ""))
    period = PERIOD_SUFFIX.get(str(best.get("period") or "").lower(), "")
    price_str = f"от {prefix}{format_number(float(best['price']))}{suffix}{period}"

    if base_label == "—":
        return price_str
    return f"{base_label}, {price_str}"


def format_payments(detail: dict[str, Any]) -> str:
    """Форматирует доступные способы оплаты из России."""
    methods = detail.get("payment_methods") or []
    slugs = {str(m.get("slug") or "").lower() for m in methods if m.get("slug")}

    ru_labels = [label for key, label in RU_PAYMENT_PRIORITY if key in slugs]
    if ru_labels:
        return ", ".join(ru_labels[:3])

    if detail.get("resellers"):
        return "Посредники"

    if slugs & FOREIGN_PAYMENT_SLUGS:
        return "Зарубежные карты"

    if str(detail.get("pricing") or "").lower() == "free":
        return "Не требуется"

    return "—"


def format_vpn(detail: dict[str, Any]) -> str:
    return "Да" if detail.get("no_vpn") else "Нет"


def valid_website_url(url: Any) -> str | None:
    if not isinstance(url, str):
        return None
    u = url.strip()
    if u.startswith("https://") or u.startswith("http://"):
        return u
    return None


def build_readme() -> tuple[str, int]:
    """Собирает итоговый README.md и возвращает (текст, число сервисов в таблицах)."""
    categories = fetch_json("/api/catalog/categories?lang=ru")
    collections = fetch_json("/api/catalog/best?lang=ru")
    pricing_index = fetch_json("/api/catalog/pricing-index?lang=ru")
    access = fetch_json("/api/catalog/access?lang=ru")
    payment_methods = fetch_json("/api/catalog/payment-methods?lang=ru")

    adult_count = 0
    clean_categories: list[dict[str, Any]] = []
    cat_by_slug: dict[str, dict[str, Any]] = {}
    for cat in categories:
        slug = str(cat.get("slug") or "").lower()
        if slug == "adult-18-plus":
            adult_count = int(cat.get("count") or 0)
        if is_clean_category(cat):
            clean_categories.append(cat)
            cat_by_slug[slug] = cat

    clean_collections = [c for c in collections if is_clean_collection(c)]

    needed_categories: list[str] = []
    for section in SECTIONS:
        for cat_slug in section["categories"]:
            if cat_slug not in needed_categories:
                needed_categories.append(cat_slug)

    category_pools: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        fmap = {pool.submit(fetch_category_tools, cs, 2): cs for cs in needed_categories}
        for fut in as_completed(fmap):
            cs = fmap[fut]
            category_pools[cs] = fut.result()

    section_candidates = select_candidates(category_pools)
    all_candidate_slugs = [
        item["slug"] for _, items in section_candidates for item in items
    ]
    details_by_slug = fetch_details_parallel(all_candidate_slugs)

    sections_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    total_table_tools = 0
    for section, candidates in section_candidates:
        final_items: list[dict[str, Any]] = []
        for item in candidates:
            slug = item["slug"]
            detail = details_by_slug.get(slug)
            if not detail or not is_clean_tool(detail):
                continue
            site_url = valid_website_url(detail.get("website_url"))
            if not site_url:
                continue
            raw_summary = str(item.get("short_description") or item.get("description") or "")
            final_items.append(
                {
                    "slug": slug,
                    "name": clean_markdown_cell(str(detail.get("name") or item["name"])),
                    "website_url": site_url,
                    "summary": format_summary(raw_summary),
                    "pricing": format_pricing(detail),
                    "vpn": format_vpn(detail),
                    "payment": format_payments(detail),
                }
            )
            if len(final_items) >= section["limit"]:
                break
        total_table_tools += len(final_items)
        sections_rows.append((section, final_items))

    if total_table_tools < MIN_TOOLS_REQUIRED:
        raise RuntimeError(
            f"Собрано слишком мало чистых инструментов ({total_table_tools} < {MIN_TOOLS_REQUIRED})"
        )

    overall = pricing_index.get("overall") or {}
    raw_total = int(overall.get("tools_total") or 0)
    clean_total = max(raw_total - adult_count, total_table_tools)
    with_free_tier = int(overall.get("with_free_tier") or 0)
    with_trial = int(pricing_index.get("with_trial") or 0)
    no_vpn_total = int(access.get("no_vpn") or 0)

    pay_counts = {str(pm.get("slug")): int(pm.get("count") or 0) for pm in payment_methods}
    sbp_total = pay_counts.get("sbp", 0)
    mir_total = pay_counts.get("mir", 0)

    medians = {
        str(m.get("currency")): m for m in (overall.get("price_medians") or [])
    }
    rub_med = medians.get("RUB") or {}
    usd_med = medians.get("USD") or {}
    eur_med = medians.get("EUR") or {}

    updated_date = str(
        pricing_index.get("updated_at")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    updated_badge = updated_date.replace("-", "--")

    lines: list[str] = [
        "# Awesome AI Tools RU",
        "",
        f"[![Сервисов в каталоге](https://img.shields.io/badge/%D0%A1%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D0%BE%D0%B2-{clean_total}-blue?style=flat-square)]({BASE_URL}/ru)",
        f"[![Без VPN](https://img.shields.io/badge/%D0%91%D0%B5%D0%B7%20VPN-{no_vpn_total}-brightgreen?style=flat-square)]({BASE_URL}/ru?access=no_vpn)",
        f"[![Оплата по СБП](https://img.shields.io/badge/%D0%A1%D0%91%D0%9F-{sbp_total}-teal?style=flat-square)]({BASE_URL}/ru)",
        f"[![Индекс цен](https://img.shields.io/badge/%D0%98%D0%BD%D0%B4%D0%B5%D0%BA%D1%81%20%D1%86%D0%B5%D0%BD-{updated_badge}-orange?style=flat-square)]({BASE_URL}/ru/pricing-index)",
        "[![License: CC0-1.0](https://img.shields.io/badge/License-CC0%201.0-lightgrey?style=flat-square)](LICENSE)",
        "",
        "Проверенные нейросети и ИИ-сервисы для пользователей из России: какие работают **без VPN**, где принимают **СБП и карты «Мир»** и сколько на самом деле стоит подписка.",
        "",
        f"Ниже — выжимка из {total_table_tools} популярных сервисов по основным задачам. Полный каталог ({plural_services(clean_total)}), фильтры по платформам и подбор аналогов доступны на [ai-webcatalog.space]({BASE_URL}/ru).",
        "",
        "## Содержание",
        "",
        "- [Индекс цен и доступность](#-индекс-цен-и-доступность)",
        "- [Готовые подборки под задачи](#-готовые-подборки-под-задачи)",
    ]

    for section, _ in sections_rows:
        lines.append(f"- [{section['title']}](#{section['anchor']})")

    lines.extend(
        [
            "- [Все категории каталога](#-все-категории-каталога)",
            "- [Как добавить сервис или обновить данные](#-как-добавить-сервис-или-обновить-данные)",
            "",
            "## 📊 Индекс цен и доступность",
            "",
            f"Сводка обновляется автоматически по данным [Индекса цен нейросетей]({BASE_URL}/ru/pricing-index) ([методология расчёта]({BASE_URL}/ru/methodology/pricing)).",
            "",
            "| Показатель | Значение | Подробнее |",
            "| --- | --- | --- |",
            f"| Медианная цена в рублях | **{format_number(float(rub_med.get('median') or 0))} ₽/мес** ({plural_services(int(rub_med.get('tools') or 0))}) | [Индекс цен]({BASE_URL}/ru/pricing-index) |",
            f"| Медианная цена в долларах | **${format_number(float(usd_med.get('median') or 0))}/мес** ({plural_services(int(usd_med.get('tools') or 0))}) | [Все тарифы]({BASE_URL}/ru/prices) |",
            f"| Медианная цена в евро | **€{format_number(float(eur_med.get('median') or 0))}/мес** ({plural_services(int(eur_med.get('tools') or 0))}) | [Все тарифы]({BASE_URL}/ru/prices) |",
            f"| С бесплатным тарифом / с триалом | **{with_free_tier}** / **{with_trial}** | [Каталог]({BASE_URL}/ru) |",
            f"| Работают без VPN | **{no_vpn_total}** | [Фильтр «Без VPN»]({BASE_URL}/ru?access=no_vpn) |",
            f"| Оплата по СБП / картами «Мир» | **{sbp_total}** / **{mir_total}** | [Каталог]({BASE_URL}/ru) |",
            "",
            "## 🎯 Готовые подборки под задачи",
            "",
        ]
    )

    for col in clean_collections:
        col_slug = col["slug"]
        col_name = clean_markdown_cell(str(col.get("name") or col_slug))
        col_count = int(col.get("count") or 0)
        lines.append(
            f"- [{col_name}]({BASE_URL}/ru/best/{col_slug}) — {plural_services(col_count)}"
        )

    lines.append("")

    for section, rows in sections_rows:
        cat_slug = section["primary_category"]
        cat_info = cat_by_slug.get(cat_slug) or {}
        cat_count = int(cat_info.get("count") or len(rows))
        if cat_count > len(rows):
            cat_link = f"[Смотреть все ({cat_count}) на сайте]({BASE_URL}/ru/category/{cat_slug})"
        else:
            cat_link = f"[Смотреть разделы на сайте]({BASE_URL}/ru/categories)"
        lines.extend(
            [
                f"## {section['title']}",
                "",
                f"Показано: {plural_services(len(rows))} · {cat_link}",
                "",
                "| Сервис | Что делает | Тариф | Без VPN | Оплата из РФ | Карточка |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            lines.append(
                f"| [{row['name']}]({row['website_url']}) | {row['summary']} | {row['pricing']} | {row['vpn']} | {row['payment']} | [Подробнее]({BASE_URL}/ru/tool/{row['slug']}) |"
            )
        lines.append("")

    lines.extend(
        [
            "## 📂 Все категории каталога",
            "",
            f"Полный список разделов на [ai-webcatalog.space/ru/categories]({BASE_URL}/ru/categories):",
            "",
            "| Категория | Сервисов |",
            "| --- | ---: |",
        ]
    )

    visible_cats = [c for c in clean_categories if int(c.get("count") or 0) > 0]
    visible_cats.sort(key=lambda c: -int(c.get("count") or 0))
    for cat in visible_cats:
        c_slug = cat["slug"]
        c_name = clean_markdown_cell(str(cat.get("name") or c_slug))
        c_count = int(cat.get("count") or 0)
        lines.append(f"| [{c_name}]({BASE_URL}/ru/category/{c_slug}) | {c_count} |")

    lines.extend(
        [
            "",
            "## 🤝 Как добавить сервис или обновить данные",
            "",
            f"- **Быстрый способ:** отправьте заявку через бесплатную форму на [ai-webcatalog.space/ru/submit]({BASE_URL}/ru/submit) — после проверки карточка появится и на сайте, и здесь при следующем обновлении.",
            "- **Через GitHub:** откройте Issue с указанием сервиса или изменением тарифа (правки вручную в `README.md` перезаписываются при автоматической синхронизации, детали в [CONTRIBUTING.md](CONTRIBUTING.md)).",
            "",
            "## 📄 Лицензия",
            "",
            "Данные и структура списка распространяются по лицензии [CC0 1.0 Universal](LICENSE).",
            "",
        ]
    )

    return "\n".join(lines), total_table_tools


def main() -> int:
    parser = argparse.ArgumentParser(description="Генератор README.md для awesome-ai-tools-ru")
    parser.add_argument("--output", default="README.md", help="Путь к выходному файлу README.md")
    args = parser.parse_args()

    try:
        content, count = build_readme()
    except Exception as err:
        print(f"Ошибка генерации README.md: {err}", file=sys.stderr)
        return 1

    tmp_path = f"{args.output}.tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    os.replace(tmp_path, args.output)
    print(f"OK: {args.output} обновлён ({count} сервисов в таблицах)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
