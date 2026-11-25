#!/usr/bin/env python3
"""
Voxly Cinema Script Translator — Contextual Movie, Drama & Wuxia/Xianxia Adaptation Engine
- Uses Qwen3-8B-4bit on Apple Silicon Metal GPU (non-thinking fast mode, greedy decoding)
  for human-grade Vietnamese & multilingual cinema dubbing scripts with rolling scene context.
- Fixes ASR homophones, enforces proper Sino-Vietnamese (Hán-Việt) names/titles for Chinese
  historical/xianxia/wuxia dramas, natural interpersonal pronouns (anh/em, ta/ngươi, lão phu/các hạ)
  for movies, and strictly blocks foreign character or English-pivot leaks.
- Includes cross-platform contextual NMT fallback for non-Apple-Silicon environments.
"""
import hashlib
import json
import os
import platform
import re
import threading
from typing import Callable

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_MLX_LOCK = threading.Lock()
_MLX_MODEL = None
_MLX_TOKENIZER = None
_MLX_SAMPLER = None
_MLX_LOAD_FAILED = False

_MLX_MODEL_ID = os.environ.get("VOXLY_CINEMA_LLM", "mlx-community/Qwen3-8B-4bit")

_LANG_NAMES_VI = {
    "vi": "Tiếng Việt (Vietnamese)",
    "en": "Tiếng Anh (English)",
    "zh": "Tiếng Trung Giản Thể (Simplified Chinese)",
    "zh-cn": "Tiếng Trung Giản Thể (Simplified Chinese)",
    "zh-tw": "Tiếng Trung Phồn Thể (Traditional Chinese)",
    "ja": "Tiếng Nhật (Japanese)",
    "ko": "Tiếng Hàn (Korean)",
    "fr": "Tiếng Pháp (French)",
    "de": "Tiếng Đức (German)",
    "es": "Tiếng Tây Ban Nha (Spanish)",
    "pt": "Tiếng Bồ Đào Nha (Portuguese)",
    "ru": "Tiếng Nga (Russian)",
    "it": "Tiếng Ý (Italian)",
    "th": "Tiếng Thái (Thai)",
    "id": "Tiếng Indonesia (Indonesian)",
    "ms": "Tiếng Mã Lai (Malay)",
    "km": "Tiếng Khmer (Khmer)",
    "lo": "Tiếng Lào (Lao)",
    "my": "Tiếng Myanmar (Burmese)",
    "tl": "Tiếng Philippines (Filipino)",
    "hi": "Tiếng Ấn Độ (Hindi)",
    "ar": "Tiếng Ả Rập (Arabic)",
    "tr": "Tiếng Thổ Nhĩ Kỳ (Turkish)",
    "nl": "Tiếng Hà Lan (Dutch)",
    "pl": "Tiếng Ba Lan (Polish)",
    "uk": "Tiếng Ukraina (Ukrainian)",
    "sv": "Tiếng Thụy Điển (Swedish)",
    "cs": "Tiếng Séc (Czech)",
    "el": "Tiếng Hy Lạp (Greek)",
    "he": "Tiếng Do Thái (Hebrew)",
    "iw": "Tiếng Do Thái (Hebrew)",
}

# Common Chinese ASR homophone fixes in wuxia / xianxia / drama dialogue
_ZH_ASR_HOMOPHONE_FIXES: list[tuple[str, str]] = [
    ("是敌非有", "是敌非友"),
    ("北方有家人", "北方有佳人"),
    ("结成道旅", "结成道侣"),
    ("结成道律", "结成道侣"),
    ("无节无哉", "无劫无灾"),
    ("无结无灾", "无劫无灾"),
    ("前路再无波者", "前路再无波折"),
    ("全路再无波者", "前路再无波折"),
    ("寻便心臣", "寻遍星辰"),
    ("共复心臣之愿", "共赴星辰之约"),
    ("大动奔甘", "大动干戈"),
    ("救地解决", "就地解决"),
    ("如此笑中", "如此效忠"),
    ("别人的家囊", "别人的家奴"),
    ("小三少主", "唐三少主"),
    ("伤害小三的母亲", "伤害唐三的母亲"),
    ("唐浩", "唐昊"),
    ("耗天宗", "昊天宗"),
    ("好天空", "昊天宗"),
    ("提浩天", "提昊天宗"),
    ("权力的一拳", "全力的一拳"),
    ("一儿在伤害", "一而再地伤害"),
    ("一而在伤害", "一而再地伤害"),
    ("神格下", "神阁下"),
    ("盛格下", "盛阁下"),
    ("长生格下", "长生阁下"),
    ("長生格下", "长生阁下"),
    ("阻掌", "族长"),
    ("太坦佐长", "泰坦族长"),
    ("任贤琪", "任贤齐"),
    ("人贤齐", "任贤齐"),
    ("人嫌棋", "任贤齐"),
    ("任嫌棋", "任贤齐"),
    ("张伯之", "张柏芝"),
    ("杨谦画", "杨千嬅"),
    ("赵船", "赵传"),
]

# Common English words that must NEVER appear inside a Chinese/Japanese/Korean -> Vietnamese translation
_CJK_TO_VI_FORBIDDEN_EN_RE = re.compile(
    r"\b(?:Soul-broken|Circle|Hercules|Goldman|Sachs|Shrek|Titan|Tang\s+Hao|Xiao\s+San|Xiangxiang|"
    r"Wang\s+Sheng|Chang\s+Sheng|Lizhi|Erlong|the|with|broken|hard|master|clan|sect|spirit)\b",
    re.IGNORECASE,
)

_NON_LATIN_LEAK_IN_VI_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]")


def preclean_source_dialogue_line(text: str, source_lang: str = "auto") -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if not t:
        return ""
    is_zh = str(source_lang).lower().startswith("zh") or bool(re.search(r"[\u4e00-\u9fff]", t))
    if is_zh:
        try:
            from opencc import OpenCC
            t = OpenCC("t2s").convert(t)
        except Exception:
            pass
        for wrong, right in _ZH_ASR_HOMOPHONE_FIXES:
            if wrong in t:
                t = t.replace(wrong, right)
    return t


def _can_use_mlx_cinema_llm() -> bool:
    global _MLX_LOAD_FAILED
    if _MLX_LOAD_FAILED:
        return False
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    if os.environ.get("VOXLY_DISABLE_MLX_LLM") == "1":
        return False
    return True


def _get_mlx_engine():
    global _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER, _MLX_LOAD_FAILED
    if _MLX_MODEL is not None and _MLX_TOKENIZER is not None:
        return _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER
    if not _can_use_mlx_cinema_llm():
        return None, None, None
    try:
        from mlx_lm import load
        from mlx_lm.sample_utils import make_sampler

        model, tokenizer = load(_MLX_MODEL_ID)
        sampler = make_sampler(temp=0.0)
        _MLX_MODEL = model
        _MLX_TOKENIZER = tokenizer
        _MLX_SAMPLER = sampler
        return _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER
    except Exception as e:
        _MLX_LOAD_FAILED = True
        print(f"[CinemaTranslator] MLX LLM unavailable, using NMT fallback: {e}")
        return None, None, None


def _strip_llm_artifacts(raw: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _clean_single_numbered_line(line_body: str, is_zh_source: bool = False, target_lang: str = "vi") -> str:
    s = (line_body or "").strip()
    s = re.sub(r"^(?:Bản dịch|Lời thoại|Dịch)\s*[:：-]\s*", "", s, flags=re.IGNORECASE).strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "“" and s[-1] == "”")):
        s = s[1:-1].strip()
    if is_zh_source and (target_lang or "vi").lower().startswith("vi"):
        s = re.sub(r"\bTang\s+H[aạ]o\b", "Đường Hạo", s)
        s = re.sub(r"\bTang\s+Tam\b", "Đường Tam", s)
        s = re.sub(r"\b(?:Tang|Tam)\s+Môn\b", "Đường Môn", s)
        s = re.sub(r"\bXiao\s*San\b", "Tiểu Tam", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNhân\s+Hiên\s+Kỳ\b", "Nhậm Hiền Tề", s, flags=re.IGNORECASE)
        s = re.sub(r"\bNhậm\s+Hiền\s+Kỳ\b", "Nhậm Hiền Tề", s, flags=re.IGNORECASE)
        s = re.sub(r"\bhữu\s+gia\s+nhân\b", "có giai nhân", s, flags=re.IGNORECASE)
        s = re.sub(r"\bCha,\s*ngươi\b", "Phụ thân, người", s)
        s = re.sub(r"\bPhụ thân,\s*ngươi\b", "Phụ thân, người", s)
    elif (target_lang or "vi").lower().startswith("vi"):
        # Never allow crude "tao / mày" or mismatched "anh - tớ" in dramatic/romantic cinema dubbing
        s = re.sub(r"\bcủa\s+tao\b", "của ta", s, flags=re.IGNORECASE)
        s = re.sub(r"\bĐối\s+với\s+tao\b", "Đối với anh", s, flags=re.IGNORECASE)
        s = re.sub(r"\btao\b", "tôi", s)
        s = re.sub(r"\bTao\b", "Tôi", s)
        if not re.search(r"\bcậu\b", s, flags=re.IGNORECASE):
            if re.search(r"\b(?:mang thai|tộc trưởng của tớ)\b", s, flags=re.IGNORECASE):
                s = re.sub(r"\btớ\b", "em", s)
                s = re.sub(r"\bTớ\b", "Em", s)
            else:
                s = re.sub(r"\btớ\b", "tôi", s)
                s = re.sub(r"\bTớ\b", "Tôi", s)
    return re.sub(r"\s+", " ", s).strip()


def _is_valid_translated_line(cand: str, source_line: str, is_cjk_source: bool, target_lang: str) -> bool:
    if not cand or len(cand.strip()) < 1:
        return False
    tl = (target_lang or "vi").lower()
    if tl.startswith("vi"):
        # Zero Chinese, Japanese, Korean, or Russian characters allowed in Vietnamese dubbing!
        if _NON_LATIN_LEAK_IN_VI_RE.search(cand):
            return False
        # Block English/Pinyin leaks when source was Chinese/Japanese/Korean
        if is_cjk_source and _CJK_TO_VI_FORBIDDEN_EN_RE.search(cand):
            return False
    return True


def _build_cinema_system_prompt(source_lang: str, target_lang: str, is_zh_source: bool) -> str:
    tl_lower = (target_lang or "vi").lower()
    if tl_lower.startswith("vi"):
        if is_zh_source:
            return (
                "Bạn là đạo diễn biên kịch dịch phim và thuyết minh lồng tiếng Việt Nam hàng đầu, chuyên dịch phim Trung Quốc (cổ trang, tiên hiệp, huyền huyễn, kiếm hiệp và tâm lý hiện đại).\n"
                "Nhiệm vụ: Dịch từng câu thoại đánh số sang Tiếng Việt mượt mà, chuẩn xác 100% nội dung, câu văn trôi chảy giàu cảm xúc để diễn viên lồng tiếng đọc khớp hình.\n"
                "Quy tắc bắt buộc:\n"
                "1. Dịch chuẩn xác tên nhân vật, nghệ sĩ, tác phẩm, tông môn, địa danh sang Hán-Việt chuẩn (VD: 任贤齐=Nhậm Hiền Tề, 周华健=Châu Hoa Kiện, 李宗盛=Lý Tông Thịnh, 罗大佑=La Đại Hữu, 周杰伦=Châu Kiệt Luân, 张柏芝=Trương Bá Chi, 神雕侠侣=Thần Điêu Đại Hiệp, 杨过=Dương Quá, 笑傲江湖=Tiếu Ngạo Giang Hồ, 令狐冲=Lệnh Hồ Xung, 李长生=Lý Trường Sinh, 唐昊=Đường Hạo, 唐三=Đường Tam, 唐门=Đường Môn, 昊天宗=Hạo Thiên Tông, 泰坦族长=Thái Thản tộc trưởng, 佳人=giai nhân, 道侣=đạo lữ). Không dịch sai tên riêng và tuyệt đối không dùng Pinyin tiếng Anh.\n"
                "2. Đại từ xưng hô chuẩn lễ nghi phim ảnh: bề trên xưng \"lão phu / ta - ngươi\"; con cái gọi cha mẹ là \"Phụ thân / Mẫu thân, người...\" (TUYỆT ĐỐI KHÔNG gọi cha mẹ là \"ngươi\"); nam nữ tiên hiệp/tình cảm xưng \"ta - nàng\" hoặc \"thiếp - chàng\"; đối tác tôn trọng gọi \"các hạ / ngài\". Không dùng \"bạn - tôi\" hay \"mày - tao\".\n"
                "3. Dịch sang câu Tiếng Việt tự nhiên, dễ hiểu với khán giả Việt (ví dụ: \"北方有佳人，绝世而独立，原来这才是你本来的模样\" dịch mượt là \"Phương Bắc có giai nhân tuyệt thế độc lập, hóa ra đây mới là dung mạo thật của nàng\").\n"
                "4. Viết 100% bằng Tiếng Việt chuẩn, tuyệt đối không để sót chữ Hán hay từ Tiếng Anh nào.\n"
                "5. Giữ nguyên đúng đánh số [1], [2]... tương ứng 1-đối-1 với từng dòng cần dịch. Không gộp dòng, không bỏ dòng, không giải thích thêm."
            )
        return (
            "Bạn là đạo diễn biên kịch dịch phim truyện và lồng tiếng Việt Nam chuyên nghiệp.\n"
            "Nhiệm vụ: Dịch từng câu thoại phim đánh số dưới đây sang Tiếng Việt tự nhiên, mượt mà, đúng trọn vẹn ý nghĩa và giàu cảm xúc điện ảnh để diễn viên lồng tiếng đọc.\n"
            "Quy tắc bắt buộc:\n"
            "1. Xưng hô lịch sự, đi theo cặp chuẩn Tiếng Việt đúng quan hệ nhân vật: vợ chồng / người yêu xưng \"anh - em\"; cha mẹ nói về đứa con / thai nhi (he, him, his mother, our son) dịch \"he / him\" là \"con / thằng bé\"; giữa người trưởng thành / chiến binh / thủ lĩnh xưng \"tôi - anh/cô/ông\" hoặc \"ta - ngươi\". TUYỆT ĐỐI CẤM dùng \"tao - mày\", KHÔNG dùng \"tớ\" lẻ loi không có \"cậu\", và tránh \"bạn - tôi\" máy móc.\n"
            "2. Dịch thoát ý trôi chảy, tròn câu rõ nghĩa, đúng ngữ cảnh điện ảnh (\"chief\" là \"tộc trưởng / thủ lĩnh\"; \"Order\" đi cùng \"Law, Blood\" là \"Trật tự\"; \"elf\" là \"tộc Tinh Linh\").\n"
            "3. Câu văn gọn gàng, liền mạch, nhịp nhàng vừa khớp khẩu hình nói, tuyệt đối không chêm từ Tiếng Anh thừa (chỉ giữ tên riêng nhân vật như Aaron, Varic, Steve Rogers).\n"
            "4. Giữ nguyên đúng đánh số [1], [2]... tương ứng 1-đối-1 với từng dòng cần dịch. Không gộp dòng, không bỏ dòng, không giải thích thêm."
        )

    tgt_display = _LANG_NAMES_VI.get(tl_lower, target_lang)
    return (
        f"You are an expert movie & drama dubbing script translator.\n"
        f"Translate each numbered dialogue line naturally, smoothly, and faithfully into {tgt_display} for voice acting.\n"
        f"Rules:\n"
        f"1. Preserve full dramatic meaning, natural spoken flow, and context-appropriate pronouns/register.\n"
        f"2. Keep exact [1], [2]... numbering 1-to-1 with the input lines. Do not merge or skip lines, and output only the numbered translations."
    )


def _run_mlx_prompt(model, tokenizer, sampler, sys_msg: str, user_msg: str, max_tokens: int = 1600) -> str:
    from mlx_lm import generate

    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": user_msg},
    ]
    try:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        ) + "<think>\n\n</think>\n\n"

    raw = generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, sampler=sampler, verbose=False)
    try:
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass
    return _strip_llm_artifacts(raw)


def translate_cinema_lines(
    lines: list[str],
    source_lang: str = "auto",
    target_lang: str = "vi",
    nmt_fallback_fn: Callable[[str, str, str], tuple[str, str]] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[str]:
    """
    Translates a list of movie dialogue turns 1-to-1 with full rolling scene context
    and per-batch disk caching so resuming or re-running long 10-30 minute videos is instant!
    """
    if not lines:
        return []
    if not target_lang or target_lang == "same":
        return list(lines)

    cleaned_inputs = [preclean_source_dialogue_line(x, source_lang=source_lang) for x in lines]
    total_lines = len(cleaned_inputs)
    is_zh_source = str(source_lang).lower().startswith("zh") or any(
        re.search(r"[\u4e00-\u9fff]", x) for x in cleaned_inputs
    )
    is_cjk_source = is_zh_source or str(source_lang).lower().startswith(("ja", "ko")) or any(
        re.search(r"[\u3040-\u30ff\uac00-\ud7af]", x) for x in cleaned_inputs
    )

    cache_dir = os.path.join("/tmp", "voxly_dub_sessions")
    os.makedirs(cache_dir, exist_ok=True)

    with _MLX_LOCK:
        model, tokenizer, sampler = _get_mlx_engine()
        if model is not None and tokenizer is not None:
            sys_msg = _build_cinema_system_prompt(source_lang, target_lang, is_zh_source)
            results: list[str] = [""] * total_lines
            avg_len = sum(len(x) for x in cleaned_inputs) / max(1, total_lines)
            batch_size = 8 if avg_len > 52 else 12
            prev_context_pairs: list[tuple[str, str]] = []

            for start_idx in range(0, total_lines, batch_size):
                batch = cleaned_inputs[start_idx : start_idx + batch_size]
                if progress_cb is not None:
                    try:
                        progress_cb(start_idx, total_lines)
                    except Exception:
                        pass

                batch_sig = hashlib.sha256(
                    json.dumps(
                        {"v": 2, "m": _MLX_MODEL_ID, "sl": source_lang, "tl": target_lang, "b": batch},
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()[:20]
                batch_cache_file = os.path.join(cache_dir, f"tr_batch_{batch_sig}.json")

                if os.path.exists(batch_cache_file):
                    try:
                        cached_arr = json.load(open(batch_cache_file, "r", encoding="utf-8"))
                        if isinstance(cached_arr, list) and len(cached_arr) == len(batch) and all(cached_arr):
                            for k, val in enumerate(cached_arr):
                                results[start_idx + k] = val
                                prev_context_pairs.append((batch[k], val))
                            continue
                    except Exception:
                        pass

                numbered = "\n".join(f"[{k + 1}] {txt}" for k, txt in enumerate(batch))

                ctx_header = ""
                if prev_context_pairs:
                    ctx_lines = "\n".join(
                        f"- \"{src}\" -> \"{trn}\"" for src, trn in prev_context_pairs[-2:]
                    )
                    ctx_header = (
                        f"Ngữ cảnh câu trước (chỉ để tham khảo giữ thống nhất tên riêng & xưng hô, KHÔNG dịch lại):\n"
                        f"{ctx_lines}\n\n"
                    )

                lookahead_footer = ""
                if start_idx + batch_size < total_lines:
                    nxt_preview = cleaned_inputs[start_idx + batch_size]
                    lookahead_footer = f"\n\n(Câu kế tiếp để tham khảo ngữ cảnh, KHÔNG dịch: \"{nxt_preview}\")"

                user_msg = f"{ctx_header}Các dòng thoại cần dịch (từ [1] đến [{len(batch)}]):\n{numbered}{lookahead_footer}"
                est_max_toks = max(900, sum(len(x) for x in batch) * 4 + 360)
                out_txt = _run_mlx_prompt(
                    model,
                    tokenizer,
                    sampler,
                    sys_msg,
                    user_msg,
                    max_tokens=min(3600, est_max_toks),
                )

                parsed_batch: dict[int, str] = {}
                for ln in out_txt.splitlines():
                    m = re.match(r"^\s*\[(\d+)\]\s*(.+)$", ln.strip())
                    if not m:
                        m = re.match(r"^\s*(\d+)[.):]\s*(.+)$", ln.strip())
                    if m:
                        b_idx = int(m.group(1)) - 1
                        if 0 <= b_idx < len(batch):
                            cand = _clean_single_numbered_line(m.group(2), is_zh_source, target_lang)
                            if _is_valid_translated_line(cand, batch[b_idx], is_cjk_source, target_lang):
                                parsed_batch[b_idx] = cand

                # Focused single-line retry for any line missing or containing foreign leak
                final_batch_list: list[str] = []
                for k, src_line in enumerate(batch):
                    if k not in parsed_batch:
                        retry_msg = (
                            f"Dịch duy nhất câu thoại sau sang {_LANG_NAMES_VI.get(target_lang.lower(), target_lang)} "
                            f"chuẩn ngữ cảnh phim truyện (viết đúng định dạng [1] ...):\n[1] {src_line}"
                        )
                        retry_out = _run_mlx_prompt(model, tokenizer, sampler, sys_msg, retry_msg, max_tokens=360)
                        cand_retry = ""
                        for rln in retry_out.splitlines():
                            rm = re.match(r"^\s*(?:\[1\]|1[.))])?\s*(.+)$", rln.strip())
                            if rm:
                                c_try = _clean_single_numbered_line(rm.group(1), is_zh_source, target_lang)
                                if _is_valid_translated_line(c_try, src_line, is_cjk_source, target_lang):
                                    cand_retry = c_try
                                    break
                        if cand_retry:
                            parsed_batch[k] = cand_retry
                        elif nmt_fallback_fn is not None:
                            fb_tr, _ = nmt_fallback_fn(src_line, source_lang, target_lang)
                            parsed_batch[k] = _clean_single_numbered_line(fb_tr or src_line, is_zh_source, target_lang)
                        else:
                            parsed_batch[k] = src_line

                    results[start_idx + k] = parsed_batch[k]
                    final_batch_list.append(parsed_batch[k])
                    prev_context_pairs.append((src_line, parsed_batch[k]))

                try:
                    with open(batch_cache_file, "w", encoding="utf-8") as bf:
                        json.dump(final_batch_list, bf, ensure_ascii=False)
                except Exception:
                    pass

            if progress_cb is not None:
                try:
                    progress_cb(total_lines, total_lines)
                except Exception:
                    pass
            return results

    # Cross-platform NMT fallback when MLX is unavailable
    if nmt_fallback_fn is None:
        return cleaned_inputs

    fallback_out: list[str] = []
    for src_line in cleaned_inputs:
        tr_one, _ = nmt_fallback_fn(src_line, source_lang, target_lang)
        fallback_out.append((tr_one or src_line).strip())
    return fallback_out
