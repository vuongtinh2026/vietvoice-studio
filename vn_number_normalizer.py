#!/usr/bin/env python3
"""
Voxly Studio — Bulletproof Vietnamese Spoken Number & Symbol Normalizer for TTS
Converts ALL numeric formats into 100% natural spoken Vietnamese BEFORE voice synthesis so
VieNeu-TTS / Piper / Private Cloned Voices NEVER misread numbers >= 1.000 as "không không không"!

Examples:
  "3.000 con"         -> "ba nghìn con"
  "1.820 năm"         -> "một nghìn tám trăm hai mươi năm"
  "800.000 tệ"        -> "tám trăm nghìn tệ"
  "1.005 điểm"        -> "một nghìn không trăm linh năm điểm"
  "1.250.000 đồng"    -> "một triệu hai trăm năm mươi nghìn đồng"
  "3,5 triệu"         -> "ba phẩy năm triệu"
  "45,5%"             -> "bốn mươi lăm phẩy năm phần trăm"
  "22/7/2026"         -> "hai mươi hai tháng bảy năm hai nghìn không trăm hai mươi sáu"
  "10-15 năm"         -> "mười đến mười lăm năm"
"""
import re

_DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
_GROUP_UNITS = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]


def _read_three_digits(n: int, full_hundreds: bool = False) -> str:
    """Reads an integer 0..999 into natural spoken Vietnamese."""
    n = int(n)
    if n == 0:
        return ""
    hundreds = n // 100
    tens = (n % 100) // 10
    ones = n % 10

    parts: list[str] = []
    if hundreds > 0 or full_hundreds:
        parts.append(f"{_DIGITS[hundreds]} trăm")

    if tens > 1:
        parts.append(f"{_DIGITS[tens]} mươi")
        if ones == 1:
            parts.append("mốt")
        elif ones == 4:
            parts.append("tư")
        elif ones == 5:
            parts.append("lăm")
        elif ones > 0:
            parts.append(_DIGITS[ones])
    elif tens == 1:
        parts.append("mười")
        if ones == 5:
            parts.append("lăm")
        elif ones > 0:
            parts.append(_DIGITS[ones])
    else:  # tens == 0
        if ones > 0:
            if hundreds > 0 or full_hundreds:
                parts.append(f"linh {_DIGITS[ones]}")
            else:
                parts.append(_DIGITS[ones])

    return " ".join(parts)


def int_to_vietnamese_words(num: int) -> str:
    """Converts any integer (including negative and multi-billion) into natural spoken Vietnamese."""
    if num < 0:
        return f"âm {int_to_vietnamese_words(-num)}"
    if num == 0:
        return "không"
    if num >= 10**18:
        return " ".join(_DIGITS[int(ch)] for ch in str(num))

    groups: list[int] = []
    temp = num
    while temp > 0:
        groups.append(temp % 1000)
        temp //= 1000

    parts: list[str] = []
    highest_idx = len(groups) - 1
    for idx in range(highest_idx, -1, -1):
        g = groups[idx]
        if g == 0:
            continue
        is_first = idx == highest_idx
        chunk_words = _read_three_digits(g, full_hundreds=(not is_first))
        unit = _GROUP_UNITS[idx] if idx < len(_GROUP_UNITS) else ""
        if unit:
            parts.append(f"{chunk_words} {unit}")
        else:
            parts.append(chunk_words)

    return " ".join(parts).strip()


def _read_decimal_fraction(frac_str: str) -> str:
    """Reads fractional part naturally (e.g. '5' -> 'năm', '25' -> 'hai mươi lăm', '05' -> 'không năm')."""
    if not frac_str:
        return ""
    if len(frac_str) <= 2 and not frac_str.startswith("0"):
        return int_to_vietnamese_words(int(frac_str))
    return " ".join(_DIGITS[int(c)] for c in frac_str if c.isdigit())


def _is_thousand_grouped(raw: str, sep: str) -> bool:
    """
    Distinguishes thousand-grouped integers ('3.000', '1.820', '800.000', '1.250.000', '1,820')
    from genuine decimal numbers ('3.5', '1.25', '1,2', '99.9').
    Rule:
      - Multiple separators (e.g. '1.250.000', '20,000,000') where every trailing group has 3 digits -> ALWAYS thousand-grouped!
      - Single separator where left part is 1..3 digits (and doesn't start with '0') AND right part is EXACTLY 3 digits
        (e.g. '1.000', '3.000', '1.820', '800.000', '15.500', '1,300'):
        In Vietnamese prose/subtitles, '.' or ',' followed by EXACTLY 3 digits is a thousand separator!
    """
    parts = raw.split(sep)
    if len(parts) < 2:
        return False
    first = parts[0]
    rest = parts[1:]
    if not first.isdigit() or len(first) == 0 or len(first) > 3:
        return False
    if first.startswith("0"):
        return False
    return all(p.isdigit() and len(p) == 3 for p in rest)


def normalize_vietnamese_numbers_for_tts(text: str) -> str:
    """
    Converts all Arabic numbers, thousand-separated numbers, decimals, percentages, dates,
    times, ranges, and common Vietnamese abbreviations into crystal-clear spoken Vietnamese words.
    """
    if not text:
        return ""

    t = text

    # 1. Common abbreviations that TTS might spell letter-by-letter
    t = re.sub(r"\bv\.v\.?(?=\s|$|[.,!?;:])", "vân vân", t, flags=re.IGNORECASE)
    t = re.sub(r"\bTP\.\s*", "Thành phố ", t)
    t = re.sub(r"\bkm/h\b", "ki lô mét trên giờ", t, flags=re.IGNORECASE)
    t = re.sub(r"\bm/s\b", "mét trên giây", t, flags=re.IGNORECASE)
    t = re.sub(r"\bm²\b|\bm2\b", "mét vuông", t, flags=re.IGNORECASE)
    t = re.sub(r"\bm³\b|\bm3\b", "mét khối", t, flags=re.IGNORECASE)

    # 1b. Currency prefixes ($100, ¥500, €50) and trailing '+' (500+)
    t = re.sub(
        r"\$\s*(\d+(?:[.,]\d+)*)",
        lambda m: f"{_convert_single_number_token(m.group(1))} đô la",
        t,
    )
    t = re.sub(
        r"[¥￥]\s*(\d+(?:[.,]\d+)*)",
        lambda m: f"{_convert_single_number_token(m.group(1))} nhân dân tệ",
        t,
    )
    t = re.sub(
        r"(?<![A-Za-z0-9_])(\d+(?:[.,]\d+)*)\+",
        lambda m: f"hơn {_convert_single_number_token(m.group(1))}",
        t,
    )

    # 2. Full dates: dd/mm/yyyy or dd-mm-yyyy
    def _repl_full_date(m: re.Match) -> str:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1 <= mo <= 12 and 1000 <= y <= 2999:
            return f"{int_to_vietnamese_words(d)} tháng {int_to_vietnamese_words(mo)} năm {int_to_vietnamese_words(y)}"
        return m.group(0)

    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", _repl_full_date, t)

    # 3. Short dates: dd/mm (only when valid calendar day/month)
    def _repl_short_date(m: re.Match) -> str:
        d, mo = int(m.group(1)), int(m.group(2))
        if 1 <= d <= 31 and 1 <= mo <= 12:
            return f"{int_to_vietnamese_words(d)} tháng {int_to_vietnamese_words(mo)}"
        return m.group(0)

    t = re.sub(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d|/)", _repl_short_date, t)

    # 4. Clock times: 18:30 or 08:05
    def _repl_time(m: re.Match) -> str:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            if mm == 0:
                return f"{int_to_vietnamese_words(hh)} giờ"
            return f"{int_to_vietnamese_words(hh)} giờ {int_to_vietnamese_words(mm)} phút"
        return m.group(0)

    t = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d|:)", _repl_time, t)

    # 5. Percentages with optional decimal/thousand formatting: 45,5% / 100% / 1.000%
    def _repl_pct(m: re.Match) -> str:
        num_str = m.group(1)
        spoken = _convert_single_number_token(num_str)
        return f"{spoken} phần trăm"

    t = re.sub(r"(?<!\d)(\d+(?:[.,]\d+)*)\s*%", _repl_pct, t)

    # 6. Numeric ranges: 10-15, 100-200, 1.000-2.000 (not negative or IDs)
    def _repl_range(m: re.Match) -> str:
        a = _convert_single_number_token(m.group(1))
        b = _convert_single_number_token(m.group(2))
        return f"{a} đến {b}"

    t = re.sub(
        r"(?<![\w\d])(\d+(?:[.,]\d+)*)\s*[-–—~]\s*(\d+(?:[.,]\d+)*)(?![\w\d])",
        _repl_range,
        t,
    )

    # 7. Standalone numbers (thousand-grouped integers, decimals, plain integers)
    # Avoid touching version/model tokens glued to letters (e.g. '48kHz' or 'MP3' handled separately)
    def _repl_any_num(m: re.Match) -> str:
        tok = m.group(1)
        return _convert_single_number_token(tok)

    t = re.sub(r"(?<![A-Za-z0-9_])(\d+(?:[.,]\d+)*)(?![A-Za-z0-9_])", _repl_any_num, t)

    # 8. Numbers glued before common units (e.g. '500m', '20kg', '10km', '30s', '100tr')
    unit_map = {
        "km": "ki lô mét",
        "kg": "ki lô gam",
        "cm": "xen ti mét",
        "mm": "mi li mét",
        "m": "mét",
        "g": "gam",
        "tr": "triệu",
        "k": "nghìn",
        "s": "giây",
    }

    def _repl_num_unit(m: re.Match) -> str:
        num_w = _convert_single_number_token(m.group(1))
        u_key = m.group(2).lower()
        return f"{num_w} {unit_map[u_key]}"

    t = re.sub(
        r"(?<![A-Za-z0-9_])(\d+(?:[.,]\d+)*)(km|kg|cm|mm|tr|m|g|k|s)\b",
        _repl_num_unit,
        t,
        flags=re.IGNORECASE,
    )

    return re.sub(r"[ \t]{2,}", " ", t).strip()


def _convert_single_number_token(tok: str) -> str:
    raw = tok.strip()
    if not raw:
        return ""

    # Pure digits (no dot/comma)
    if raw.isdigit():
        # Preserve phone-like leading zeros (e.g. '0987654321') as digit-by-digit
        if len(raw) >= 4 and raw.startswith("0"):
            return " ".join(_DIGITS[int(c)] for c in raw)
        return int_to_vietnamese_words(int(raw))

    # Contains BOTH '.' and ',' (e.g. '1.250,50' Vietnamese style or '1,250.50' US style)
    if "." in raw and "," in raw:
        last_dot = raw.rfind(".")
        last_comma = raw.rfind(",")
        if last_comma > last_dot:
            int_part = raw[:last_comma].replace(".", "")
            frac_part = raw[last_comma + 1 :]
        else:
            int_part = raw[:last_dot].replace(",", "")
            frac_part = raw[last_dot + 1 :]
        if int_part.isdigit() and frac_part.isdigit():
            return f"{int_to_vietnamese_words(int(int_part))} phẩy {_read_decimal_fraction(frac_part)}"

    # Contains only '.'
    if "." in raw:
        if _is_thousand_grouped(raw, "."):
            return int_to_vietnamese_words(int(raw.replace(".", "")))
        parts = raw.split(".")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int_to_vietnamese_words(int(parts[0]))} phẩy {_read_decimal_fraction(parts[1])}"
        # Multi-dot non-thousand (e.g. '2.0.1') -> read each part
        return " chấm ".join(int_to_vietnamese_words(int(p)) if p.isdigit() else p for p in parts)

    # Contains only ','
    if "," in raw:
        if _is_thousand_grouped(raw, ","):
            return int_to_vietnamese_words(int(raw.replace(",", "")))
        parts = raw.split(",")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f"{int_to_vietnamese_words(int(parts[0]))} phẩy {_read_decimal_fraction(parts[1])}"
        return " phẩy ".join(int_to_vietnamese_words(int(p)) if p.isdigit() else p for p in parts)

    return raw
