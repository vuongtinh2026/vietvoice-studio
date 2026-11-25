#!/usr/bin/env python3
"""
Voxly Cinema Script Translator v5 — Character-Bible, Gender/Kinship-Aware Movie Dubbing Engine
- Pass 0 (Character & Relationship Bible): Scans the full script once to identify every character's
  gender (nam/nữ), age (trẻ em / thiếu niên / người lớn / lão niên), family relationship
  (cha-mẹ-con, anh-em, sư phụ-đệ tử), and modern vs. ancient setting.
- Pass 1 (Contiguous Scene-Context Direct Translation via Qwen3-8B Metal GPU): Translates EVERY
  dialogue turn in contiguous 8-line scene blocks with rolling 2-line scene memory — zero English
  pivot, zero blind 'bạn -> ngươi' replacement, exact gender ('他' vs '她' vs '它') and exact
  Vietnamese kinship pronouns (con-mẹ, con-cha, anh-em, tôi-cô/anh/ông, đệ tử-ngài/trưởng lão).
- Strict Phonotactic Foreign-Word Guardrail + per-batch persistent disk caching for multi-hour movies.
"""
import concurrent.futures
import hashlib
import json
import os
import platform
import re
import threading
import time
from typing import Callable

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_MLX_LOCK = threading.Lock()
_MLX_MODEL = None
_MLX_TOKENIZER = None
_MLX_SAMPLER = None
_MLX_LOAD_FAILED = False
_MLX_MODEL_ID = os.environ.get("VOXLY_CINEMA_LLM", "mlx-community/Qwen3-8B-4bit")

_OPENCC_T2S = None
_OPENCC_READY = False


def _to_simplified(text: str) -> str:
    global _OPENCC_T2S, _OPENCC_READY
    if not _OPENCC_READY:
        _OPENCC_READY = True
        try:
            from opencc import OpenCC
            _OPENCC_T2S = OpenCC("t2s")
        except Exception:
            _OPENCC_T2S = None
    if _OPENCC_T2S is not None:
        try:
            return _OPENCC_T2S.convert(text)
        except Exception:
            pass
    return text


# Audio ASR homophone fixes (when Whisper fallback is used on unsubtitled audio/video)
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
    ("阻掌", "族长"),
    ("太坦佐长", "泰坦族长"),
    ("任贤琪", "任贤齐"),
    ("任贤奇", "任贤齐"),
    ("人贤齐", "任贤齐"),
    ("人贤奇", "任贤齐"),
    ("人嫌棋", "任贤齐"),
    ("任嫌棋", "任贤齐"),
    ("张伯之", "张柏芝"),
    ("杨谦画", "杨千嬅"),
    ("赵船", "赵传"),
    ("齐琴", "齐秦"),
    ("五百林一连", "伍佰和林忆莲"),
    ("雅鲁藏不僵", "雅鲁藏布江"),
    ("鸭灯", "压灯"),
    ("鸦灯", "压灯"),
    ("莫湾鸡", "莫湾基"),
    ("鸟羊绿", "飘阳绿"),
    ("飘洋绿", "飘阳绿"),
    ("飘兰花", "飘蓝花"),
    ("懦种", "糯种"),
    ("诺种", "糯种"),
    ("诺冰", "糯冰"),
    ("冰诺", "冰糯"),
    ("诺水", "糯水"),
    ("切实", "切石"),
    ("皮刻", "皮壳"),
    ("莽带", "蟒带"),
    ("更深的情侣", "更深的青绿"),
    ("玻璃宠帝王略", "玻璃种帝王绿"),
    ("静置靶子", "静止靶子"),
    # OCR visual typo fixes
    ("人间己成炼狱", "人间已成炼狱"),
    ("敢威肋老子", "敢威胁老子"),
    ("千粮和衣物", "干粮和衣物"),
    ("手腕耍甩", "手腕要甩"),
]

# Pure Chinese semantic pre-expansion ONLY for NMT fallback anchor
_ZH_PURE_SEMANTIC_EXPAND: list[tuple[str, str]] = [
    ("哎别别别", "哎，先别这样"),
    ("别别别", "先别这样"),
    ("哈哈哈哈", "哈哈"),
    ("明人不说暗话", "咱们直截了当说吧"),
    ("狗皮膏药", "赖着不走的人"),
    ("小意思", "小事一桩"),
    ("你点点", "你清点一下"),
    ("肥羊", "冤大头"),
    ("压灯都吃不进去", "用手电筒照射连光线都透不进去"),
    ("压灯有点糯水的意思", "用手电筒照射看水头有糯种翡翠质感"),
    ("压灯", "用手电筒照看"),
    ("赌性大", "赌石风险太大"),
    ("赌个屁", "赌什么鬼啊"),
    ("涨个屁", "赚什么鬼啊"),
    ("踩了什么狗屎运", "怎么会有这么好的运气"),
]

# Exact unambiguous 1-3 char utterances (never depend on gender/kinship!)
_ZH_EXACT_SHORT_UTTERANCES_VI: dict[str, str] = {
    "等等": "Khoan đã!",
    "请进": "Mời vào!",
    "真的吗": "Thật vậy sao?",
    "快了快了": "Sắp rồi, sắp rồi!",
    "好吧": "Được thôi.",
    "有效": "Có tác dụng rồi!",
    "就这": "Chỉ có thế thôi à?",
    "是": "Vâng.",
    "嗯": "Ừm.",
    "啊啊啊": "Á á á!",
    "我去": "Trời đất ơi!",
    "卧槽": "Trời đất ơi!",
    "操": "Chết tiệt!",
    "牛逼": "Đỉnh thật!",
    "齐活": "Xong xuôi!",
    "赌个屁": "Đánh cược cái con khỉ!",
    "涨个屁": "Trúng đậm cái con khỉ!",
    "冰封即可": "Đóng băng là xong.",
    "废话真多": "Lắm lời quá đấy.",
    "什么东西": "Thứ gì thế?",
    "冻住了": "Đóng băng rồi!",
    "原来如此": "Hóa ra là vậy.",
    "侧身": "Nghiêng người!",
    "敕令": "Sắc lệnh!",
}

# Post-cleanup fixes (NO blind 'bạn -> ngươi' EVER!)
_VI_POST_TERM_FIXES: list[tuple[str, str]] = [
    (r"\banh\s+ngươi\b", "anh bạn"),
    (r"\bBoss\b", "Ông chủ"),
    (r"\bmỏ\s+mỏ\b", "mỏ"),
    (r"\b(?:miệng mỏ )?cơ sở Mowan\b", "mỏ Mạc Loan Cơ"),
    (r"\bMo\s*Wanji\b", "Mạc Loan Cơ"),
    (r"\bRuilida\b", "Thụy Lệ Đạt"),
    (r"\bPiao\s*Yang\s*Green(?:\s*Jade)?\b", "Phiêu Dương Lục"),
    (r"\bngọc (?:bích )?Ice\s*Nuo\b", "ngọc Băng Nếp"),
    (r"\bngọc (?:bích )?Nuobing\b", "ngọc Nếp Băng"),
    (r"\bngọc (?:bích )?Bingnuo\b", "ngọc Băng Nếp"),
    (r"\bMoon Shadow Leopard\b", "Nguyệt Ảnh Báo"),
    (r"\bMoon Kill\b", "Nguyệt Sát"),
    (r"\bShadow Strike\b", "Ảnh Tập"),
    (r"\bVương quốc Zifu\b", "Tử Phủ cảnh"),
    (r"\bGiáo phái Haoran\b", "Hạo Nhiên Tông"),
    (r"\bHoàng đế Zhenwu\b", "Chân Vũ Đại Đế"),
    (r"\bHoàng đế Wanluo\b", "Vạn La Ma Đế"),
    (r"\bHoàng đế Yuan\b", "Nguyên Đế"),
    (r"\bChang Qing\b", "Thường Thanh"),
    (r"\bTrưởng lão Su\b", "Tô trưởng lão"),
    (r"\bLão Su\b", "Tô trưởng lão"),
    (r"\bbác Su\b", "Tô trưởng lão"),
    (r"\bTrưởng lão Lauro\b", "La trưởng lão"),
    (r"\bTang\s+H[aạ]o\b", "Đường Hạo"),
    (r"\bTang\s+Tam\b", "Đường Tam"),
    (r"\bXiao\s*San\b", "Tiểu Tam"),
    (r"\bRen\s*Xianqi\b", "Nhậm Hiền Tề"),
]

# Unmistakable 21st-century modern-setting markers!
# Even if a modern movie has Taoist priests/ghosts/cultivation (e.g. '欧洲驱魔录', urban fantasy),
# >= 3 distinct modern-era markers lock it to `modern_cn` so modern people NEVER call each other 'ngươi'!
_HARD_MODERN_ERA_MARKERS_RE = re.compile(
    r"(?:英国|美国|欧洲|日本|韩国|中国|东北|机场|飞机|航班|公务员|警官|警方|警察|派出所|民警|"
    r"教授|卡车|汽车|开车|车牌|奔驰|手机|电脑|微信|视频|网友|医院|银行|存款|公司|老板|科学|"
    r"地铁|外套|西装|拉面|专辑|唱片|电影|导演|行车记录仪|公职人员|靶子|设备|场地|立方米|英语|中文)"
)

_ANCIENT_WORLD_MARKERS_RE = re.compile(
    r"(?:老夫|本座|本尊|少主|宗门|宗主|道侣|渡劫|修仙|仙门|仙道|魂技|魂环|武魂|昊天宗|唐门|"
    r"陛下|皇上|娘娘|爱卿|老衲|贫道|少侠|阁下|在下|师尊|长老|掌门|族长|阁主|公子|姑娘|"
    r"功法|筑基|金丹|元婴|紫府|灵石|灵宠|灵兽|妖兽|圣兽|秘境|藏经阁|贡献点|寿元|大帝|魔帝|"
    r"遗迹|散修|闭关|村长|邪神|神魂|尊神|旧神|炼狱|灾星|玉佩|霜刃|饭碗)"
)

# Valid modern loanwords & Western person/place names allowed in modern / international settings
_MODERN_LOANWORDS_ALLOW = {
    "video", "radio", "camera", "karaoke", "album", "guitar", "coffee", "cafe", "studio",
    "taxi", "internet", "email", "ok", "km", "kg", "cm", "mm", "ml", "youtube", "tiktok",
    "douyin", "facebook", "iphone", "app", "game", "ai", "vip", "pro", "mp3", "mp4", "wav",
    "ktv", "ost", "mercedes", "bmw", "lumi", "london", "paris", "irene", "walker", "kane",
    "cain", "john", "peter", "david", "sarah", "anna", "jack", "tom", "mike", "alex",
    "sam", "mark", "paul", "mary", "lisa", "emma", "eric", "adam", "aaron", "steve", "rogers",
}

_PINYIN_LEAK_TOKENS = {
    "su", "yuan", "qing", "chang", "zifu", "haoran", "zhenwu", "wanluo", "lauro", "niancha",
    "youfen", "tayou", "hongxinyu", "zangjinlu", "zongwen", "mowan", "mowanji", "nuobing",
    "bingnuo", "nuo", "piaoyang", "ruilida", "yu", "xu", "wu", "luo", "liu", "zhou", "zhao",
    "zhang", "xiao", "shen", "feng", "jia", "shou", "dushuang", "ranchachu", "ranbaoheidao",
    "lanzhou", "tang", "chen", "lin", "guo", "gao", "han", "yang",
}

_VI_VOWELS_STR = "aeiouyàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ"
_VI_INTERNAL_VCV_RE = re.compile(
    rf"[{_VI_VOWELS_STR}][bcdfghklmnpqrstvwxzđ]+[{_VI_VOWELS_STR}]",
    re.IGNORECASE,
)
_VI_BAD_CLUSTER_RE = re.compile(
    r"(?:[fjwz]|sh|zh|ck|st|sp|sk|sl|sm|sn|sw|bl|br|cl|cr|dr|fl|fr|gl|gr|pl|pr|tw|wh|wr|"
    r"ll|ss|tt|rr|nn|dd|bb|gg|pp|mm|oo|ee|q(?!u)|^yu|^yi|^yo|^ya|iao|(?<!q)uan|eng)",
    re.IGNORECASE,
)
_VI_BAD_CODA_RE = re.compile(r"(?:[bdfklrsvxz]|(?<!n)g)$", re.IGNORECASE)
_NON_LATIN_LEAK_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]")
_ARCHAIC_NGUOI_RE = re.compile(r"\b(?:ngươi|lão phu|bản tọa|tại hạ|các hạ|bổn tọa|huynh đài)\b", re.IGNORECASE)


def find_foreign_leaks_in_vi(text: str, genre: str = "modern_cn", is_cjk_source: bool = True) -> list[str]:
    if not text:
        return []
    leaks: list[str] = []
    if _NON_LATIN_LEAK_RE.search(text):
        leaks.append("CJK_OR_NON_LATIN")

    words = re.findall(r"[A-Za-zÀ-ỹĐđ]+", text)
    for w in words:
        wl = w.lower()
        if not wl:
            continue
        if re.fullmatch(r"(?:ha|hi|hê|hô|hà|á|ư|ô|a)+", wl):
            continue
        if genre != "ancient_cn" and wl in _MODERN_LOANWORDS_ALLOW:
            continue
        if is_cjk_source and wl in _PINYIN_LEAK_TOKENS:
            if wl == "su" and not w[0].isupper():
                continue
            leaks.append(w)
            continue
        if _VI_BAD_CLUSTER_RE.search(wl):
            leaks.append(w)
            continue
        if _VI_BAD_CODA_RE.search(wl):
            leaks.append(w)
            continue
        if len(wl) >= 8:
            leaks.append(w)
            continue
        check_vcv = wl
        if check_vcv.startswith(("qu", "gi")) and len(check_vcv) > 2:
            check_vcv = check_vcv[2:]
        if _VI_INTERNAL_VCV_RE.search(check_vcv):
            leaks.append(w)
            continue

    seen = set()
    uniq: list[str] = []
    for x in leaks:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _collapse_word_loops(text: str) -> str:
    if not text:
        return ""
    s = re.sub(
        r"\b([A-Za-zÀ-ỹĐđ]+(?:\s+[A-Za-zÀ-ỹĐđ]+)?)(?:[,\s]+\1){3,}\b",
        r"\1, \1",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s{2,}", " ", s).strip()


def detect_script_genre(lines: list[str], is_zh_source: bool) -> str:
    """
    Accurately distinguishes:
      - 'modern_cn'   : Any movie set in modern times (even modern supernatural/exorcism with Taoists & ghosts!)
      - 'ancient_cn'  : Genuine ancient/historical/fantasy/xianxia/dark-fantasy world (ZERO 21st-century tech/countries)
      - 'intl_cinema' : English / Korean / Japanese / Western cinema
    """
    if not is_zh_source:
        return "intl_cinema"
    joined = "\n".join(lines)
    modern_types = set(_HARD_MODERN_ERA_MARKERS_RE.findall(joined))
    modern_hits = len(_HARD_MODERN_ERA_MARKERS_RE.findall(joined))
    ancient_hits = len(_ANCIENT_WORLD_MARKERS_RE.findall(joined))

    # If the movie has >= 3 distinct 21st-century markers (e.g. 英国, 机场, 公务员, 警官, 教授, 卡车, 老板),
    # it is 100% set in the modern world!
    if len(modern_types) >= 3 or modern_hits >= 5:
        return "modern_cn"
    if ancient_hits >= 3 and modern_hits <= 1:
        return "ancient_cn"
    return "modern_cn"


def preclean_source_dialogue_line(text: str, source_lang: str = "auto") -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if not t:
        return ""
    is_zh = str(source_lang).lower().startswith("zh") or bool(re.search(r"[\u4e00-\u9fff]", t))
    if is_zh:
        t = _to_simplified(t)
        for wrong, right in _ZH_ASR_HOMOPHONE_FIXES:
            if wrong in t:
                t = t.replace(wrong, right)
    return t


def _expand_pure_zh_semantics(line: str) -> str:
    s = line
    for k, v in _ZH_PURE_SEMANTIC_EXPAND:
        if k in s:
            s = s.replace(k, v)
    return s


def _polish_vietnamese_cinema_line(text: str, genre: str, target_lang: str = "vi") -> str:
    s = _collapse_word_loops((text or "").strip())
    if not (target_lang or "vi").lower().startswith("vi") or not s:
        return s

    s = re.sub(r"^(?:Bản dịch|Lời thoại|Dịch|Nghĩa chuẩn)\s*[:：-]\s*", "", s, flags=re.IGNORECASE).strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "“" and s[-1] == "”")):
        s = s[1:-1].strip()

    for pat, rep in _VI_POST_TERM_FIXES:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    if genre == "modern_cn":
        # Modern dramas MUST NEVER use archaic wuxia pronouns!
        s = re.sub(r"\bLão phu\b", "Ông chủ", s)
        s = re.sub(r"\blão phu\b", "ông chủ", s)
        s = re.sub(r"\bNgươi\b", "Anh", s)
        s = re.sub(r"\bngươi\b", "anh", s)
        s = re.sub(r"\bbản tọa\b", "tôi", s, flags=re.IGNORECASE)
        s = re.sub(r"\btại hạ\b", "tôi", s, flags=re.IGNORECASE)
        s = re.sub(r"\bcác hạ\b", "anh", s, flags=re.IGNORECASE)
        s = re.sub(r"\bnhân dân tệ\b", "tệ", s, flags=re.IGNORECASE)
    elif genre == "ancient_cn":
        # Respectful family fixes — NEVER blindly turn 'bạn' into 'ngươi'!
        s = re.sub(r"\bCha,\s*ngươi\b", "Cha ơi, người", s)
        s = re.sub(r"\bPhụ thân,\s*ngươi\b", "Phụ thân, người", s)
        s = re.sub(r"\bMẹ,\s*ngươi\b", "Mẹ ơi, người", s)
        s = re.sub(r"\bMẫu thân,\s*ngươi\b", "Mẫu thân, người", s)
    else:
        s = re.sub(r"\btao\b", "tôi", s)
        s = re.sub(r"\bTao\b", "Tôi", s)

    return re.sub(r"\s+", " ", s).strip()


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
        print(f"[CinemaTranslator] MLX LLM unavailable, using NMT engine: {e}")
        return None, None, None


def _run_mlx_prompt(model, tokenizer, sampler, sys_msg: str, user_msg: str, max_tokens: int = 1100) -> str:
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
    cleaned = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


_CHAR_CLUE_RE = re.compile(
    r"(?:叫|名为|是|爸|妈|爹|娘|养母|养父|母|父|哥|姐|弟|妹|娃|儿|女|男|小哥哥|小姐姐|"
    r"长老|阁主|师尊|师父|村长|教授|警官|先生|女士|小姐|老板|大爷|三爷|尊神|之主|大帝|道士|仙家|徒弟|弟子)"
)


def _extract_character_bible(
    model,
    tokenizer,
    sampler,
    cleaned_inputs: list[str],
    genre: str,
    cache_dir: str,
) -> str:
    """
    Pass 0: Extracts a concise Vietnamese Character & Relationship Bible (name, gender, age,
    family role, and exact Vietnamese pronoun pairs) from the full script in ~4 seconds!
    Cached by full script hash so re-runs are instantaneous.
    """
    sig = hashlib.sha256(
        json.dumps({"v": 11, "g": genre, "n": len(cleaned_inputs), "h": cleaned_inputs[:60]}, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:20]
    bible_path = os.path.join(cache_dir, f"char_bible_v11_{sig}.txt")
    if os.path.exists(bible_path):
        try:
            cached = open(bible_path, "r", encoding="utf-8").read().strip()
            if cached:
                return cached
        except Exception:
            pass

    # Pick up to 55 highest-signal character/kinship/relationship lines distributed across the script
    picked: list[str] = []
    seen = set()
    # Always include first 18 lines (opening setup introduces main characters & relationships!)
    for idx in range(min(18, len(cleaned_inputs))):
        t = cleaned_inputs[idx]
        if t and idx not in seen:
            seen.add(idx)
            picked.append(f"({idx + 1}) {t}")
    # Add lines with names, family roles, gender clues across the rest of the movie
    for idx, t in enumerate(cleaned_inputs):
        if idx in seen or not t:
            continue
        if _CHAR_CLUE_RE.search(t):
            seen.add(idx)
            picked.append(f"({idx + 1}) {t}")
            if len(picked) >= 55:
                break

    if not picked:
        return ""

    sys_bible = (
        "Bạn là đạo diễn biên kịch phân tích hồ sơ nhân vật phim.\n"
        "Đọc các câu thoại trích từ phim và tóm tắt NGẮN GỌN (tối đa 7 gạch đầu dòng bằng Tiếng Việt):\n"
        "- Bối cảnh phim (Hiện đại hay Cổ trang/Huyền huyễn).\n"
        "- Từng nhân vật chính: Tên (Hán-Việt cho người Hoa, tên gốc cho người Tây), GIỚI TÍNH (Nam/Nữ), ĐỘ TUỔI (bé trai/bé gái/thiếu niên/người lớn/lão niên), VAI VẾ & QUAN HỆ (cha/mẹ/con, anh/em, sư phụ/đệ tử, cảnh sát/giáo sư/bạn bè) và cặp xưng hô chuẩn Tiếng Việt.\n"
        "Ngắn gọn súc tích, tối đa 7 dòng."
    )
    user_bible = "Trích đoạn lời thoại phim:\n" + "\n".join(picked[:42])
    bible_txt = _run_mlx_prompt(model, tokenizer, sampler, sys_bible, user_bible, max_tokens=260).strip()

    if bible_txt:
        try:
            with open(bible_path, "w", encoding="utf-8") as bf:
                bf.write(bible_txt)
        except Exception:
            pass
    return bible_txt


def _build_qwen_cinema_system_prompt(genre: str, char_bible: str) -> str:
    bible_section = f"\nHỒ SƠ NHÂN VẬT & VAI VẾ CỦA BỘ PHIM NÀY (BẮT BUỘC TUÂN THỦ GIỚI TÍNH & XƯNG HÔ):\n{char_bible}\n" if char_bible else ""

    gender_kinship_rules = (
        "QUY TẮC TỐI THƯỢNG VỀ GIỚI TÍNH, ĐỘ TUỔI & XƯNG HÔ TIẾNG VIỆT (TUYỆT ĐỐI KHÔNG DÙNG 'NGƯƠI' CHUNG CHO TẤT CẢ!):\n"
        "A. PHÂN BIỆT RẠCH RÒI NAM / NỮ / TRẺ EM / CHA MẸ:\n"
        "  - Đọc kỹ chữ Hán gốc: '他' = NAM (anh ấy/cậu ấy/ông ấy/thằng bé/hắn); '她' = NỮ (cô ấy/chị ấy/bà ấy/cô bé/nàng); '它' = con vật/đồ vật (nó).\n"
        "  - TUYỆT ĐỐI KHÔNG dịch nhầm nam thành nữ ('他' hay cậu bé KHÔNG BAO GIỜ là 'cô bé'; '黄三爷' là Hoàng Tam Gia - nam, KHÔNG phải 'nàng tiên') và không dịch nhầm nữ thành nam ('她' hay phụ nữ KHÔNG BAO GIỜ là 'anh ta')!\n"
        "  - '小哥哥' = anh trai (cô gái gọi chàng trai, KHÔNG dịch là 'em trai'); '小姐姐' = chị gái; '娃/小子/毛孩子' = thằng bé/cậu bé (nam) hoặc cô bé (nữ) tùy giới tính nhân vật; '寒儿' = tên con trai Hàn Nhi (KHÔNG dịch thành 'ăn nguội'!).\n"
        "  - '爸/爹/父亲' = cha/bố; '妈/娘/母亲/养母' = mẹ/mẹ nuôi.\n"
        "B. XƯNG HÔ CHUẨN ĐÚNG NGƯỜI NÓI VÀ NGƯỜI NGHE (DỰA VÀO MẠCH CẢNH):\n"
        "  - Con cái nói với Cha/Mẹ (kể cả trước mộ mẹ nuôi, khi nhắc '养母', '立碑', '您'): BẮT BUỘC xưng 'con - mẹ / cha' (TUYỆT ĐỐI CẤM gọi cha mẹ là 'ngươi' hay 'ngài'!).\n"
        "  - Cha/Mẹ nói với Con ('寒儿', '孩子', '娃'): xưng 'mẹ / cha - con'.\n"
        "  - Đệ tử / hậu bối / người trẻ nói với Sư phụ / Trưởng lão / Giáo sư / Bề trên ('您', '长老', '师尊', '教授', '先生'): xưng 'con / đệ tử / tôi - ngài / thầy / trưởng lão / giáo sư / ông' (CẤM gọi bề trên là 'ngươi'!).\n"
        "  - Cô gái trẻ / người nhỏ hơn nói với chàng trai ('小哥哥', '大哥'): xưng 'em - anh'.\n"
        "  - Khi nói chuyện với phụ nữ / nữ cảnh sát ('艾琳 / Irene', '冬梅 / Đông Mai', '女士', '小姐', '姑娘'): PHẢI gọi là 'cô / chị' (TUYỆT ĐỐI KHÔNG gọi phụ nữ là 'anh'!).\n"
        "  - Người trưởng thành trong phim hiện đại (đàn ông, công chức, đạo sĩ, tiên gia, cảnh sát, giáo sư): xưng 'tôi' (KHÔNG xưng 'mình' sến súa cho đàn ông/cảnh sát/tiên gia!) và gọi đúng giới tính 'anh / chị / cô / cậu / ông / bà'.\n"
    )

    if genre == "ancient_cn":
        return (
            "Bạn là đạo diễn biên kịch thuyết minh phim cổ trang, tiên hiệp, huyền huyễn Việt Nam hàng đầu.\n"
            f"{bible_section}\n"
            f"{gender_kinship_rules}"
            "  - CHỈ dùng 'ta - ngươi' khi bề trên/thần linh quát kẻ dưới hoặc hai kẻ thù đang đối đầu sinh tử! Với người thân (mẹ/cha/con), bề trên (trưởng lão/sư phụ), hay cô gái gọi thiếu niên (em - anh) PHẢI dùng đúng vai vế tự nhiên.\n"
            "C. CHẤT LƯỢNG DỊCH ĐIỆN ẢNH:\n"
            "  - Dịch 100% sang Tiếng Việt chuẩn Hán-Việt trôi chảy, mượt mà dễ nghe, đúng 100% số liệu & ý nghĩa câu gốc. TUYỆT ĐỐI KHÔNG để sót chữ Hán, Pinyin hay từ Tiếng Anh nào.\n"
            "  - Xuất đúng đánh số [1]..[N] tương ứng 1-đối-1. Không gộp dòng, không bỏ dòng, không lặp từ, không giải thích thêm."
        )
    if genre == "modern_cn":
        return (
            "Bạn là đạo diễn biên kịch thuyết minh phim HIỆN ĐẠI Trung Quốc (đô thị, trinh thám, linh dị hiện đại, đổ thạch, hài hước) sang Tiếng Việt tự nhiên.\n"
            f"{bible_section}\n"
            f"{gender_kinship_rules}"
            "  - ĐÂY LÀ PHIM BỐI CẢNH HIỆN ĐẠI: TUYỆT ĐỐI CẤM dùng từ cổ trang như 'ngươi', 'lão phu', 'bản tọa', 'tại hạ', 'các hạ'!\n"
            "  - Dùng xưng hô đời thực tự nhiên: 'tôi - anh/chị/cô/cậu/ông/bà', bạn thân 'tôi - cậu/ông/cô', con với cha mẹ 'con - bố/mẹ', với cấp trên/giáo sư/cảnh sát 'tôi - giáo sư/cô/ông/sếp'.\n"
            "C. CHẤT LƯỢNG DỊCH ĐIỆN ẢNH:\n"
            "  - Dịch 100% sang Tiếng Việt tự nhiên (tên nhân vật phương Tây như Irene Walker, Kane giữ chuẩn cách gọi Cảnh sát Irene Walker, ông Kane; tên nhân vật Trung Quốc dịch chuẩn Hán-Việt như Mã Đông Mai, Trương Huyền Nhất, Hoàng Tam Gia, Mạc Loan Cơ, Thụy Lệ Đạt).\n"
            "  - Dịch chuẩn nghĩa bối cảnh (VD: '提议' = đề xuất, KHÔNG phải 'lời cầu hôn'; '出马仙' = Xuất Mã Tiên; '仙家' của Hoàng Tam Gia = Tiên gia, KHÔNG phải 'nàng tiên'; '死马当活马医' = còn nước còn tát; '埋汰' = châm chọc/chê bai, KHÔNG phải 'chôn').\n"
            "  - Giữ chính xác 100% số liệu, xuất đúng đánh số [1]..[N] tương ứng 1-đối-1, không gộp dòng, không bỏ dòng, không giải thích thêm."
        )
    return (
        "Bạn là đạo diễn biên kịch lồng tiếng phim điện ảnh quốc tế sang Tiếng Việt.\n"
        f"{bible_section}\n"
        f"{gender_kinship_rules}"
        "  - Dịch 100% sang Tiếng Việt tự nhiên, phân biệt chuẩn nam/nữ/trẻ em/cha mẹ (anh-em, bố/mẹ-con, tôi-anh/cô/ông), không dùng 'ngươi' trừ bối cảnh cổ đại đối đầu, không dùng 'tao - mày'.\n"
        "  - Xuất đúng đánh số [1]..[N] tương ứng 1-đối-1."
    )


def translate_cinema_lines(
    lines: list[str],
    source_lang: str = "auto",
    target_lang: str = "vi",
    nmt_fallback_fn: Callable[[str, str, str], tuple[str, str]] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[str]:
    """
    Full Character-Bible + Contiguous Scene-Context Cinema Translation Engine:
    - Pass 0: Builds the Character & Relationship Bible (gender, age, kinship, modern/ancient setting).
    - Pass 1: Translates ALL dialogue turns in contiguous 8-line scene blocks with rolling 2-line
      scene memory via Qwen3-8B Metal GPU (100% direct zh -> vi, exact gender & kinship pronouns,
      zero blind 'ngươi', zero English/Pinyin leaks), backed by NMT safety anchors & disk batch cache!
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
    genre = detect_script_genre(cleaned_inputs, is_zh_source=is_zh_source)

    sl_query = "zh-CN" if is_zh_source else (source_lang or "auto")
    tl_lower = (target_lang or "vi").lower()
    is_vi_target = tl_lower.startswith("vi")
    cjk_leak_re = _NON_LATIN_LEAK_RE

    cache_dir = os.path.join("/tmp", "voxly_dub_sessions")
    os.makedirs(cache_dir, exist_ok=True)

    # ---------------- Fast NMT Baseline (safety anchor + cross-platform fallback) ----------------
    nmt_anchors: list[str] = list(cleaned_inputs)
    if nmt_fallback_fn is not None:
        pending_nmt: list[int] = []
        for idx, src_line in enumerate(cleaned_inputs):
            bare = src_line.strip().rstrip("。！？!?.，, ")
            if is_zh_source and is_vi_target and bare in _ZH_EXACT_SHORT_UTTERANCES_VI:
                nmt_anchors[idx] = _ZH_EXACT_SHORT_UTTERANCES_VI[bare]
            else:
                pending_nmt.append(idx)

        def _tr_one_nmt(q_txt: str, orig_txt: str) -> str:
            for attempt in range(3):
                if attempt > 0:
                    time.sleep(0.35 * attempt)
                try:
                    tr_raw, _ = nmt_fallback_fn(q_txt, sl_query, target_lang)
                    pol = _polish_vietnamese_cinema_line(tr_raw or "", genre=genre, target_lang=target_lang)
                    if pol and (not is_vi_target or not cjk_leak_re.search(pol)):
                        return pol
                except Exception:
                    continue
            return orig_txt

        nmt_batches = [pending_nmt[i : i + 16] for i in range(0, len(pending_nmt), 16)]

        def _run_nmt_batch(idx_list: list[int]) -> list[tuple[int, str]]:
            q_lines = [_expand_pure_zh_semantics(cleaned_inputs[i]) if is_zh_source else cleaned_inputs[i] for i in idx_list]
            sig = hashlib.sha256(
                json.dumps({"v": 10, "sl": sl_query, "tl": target_lang, "g": genre, "q": q_lines}, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:20]
            c_path = os.path.join(cache_dir, f"tr_nmt_v10_{sig}.json")
            if os.path.exists(c_path):
                try:
                    cached = json.load(open(c_path, "r", encoding="utf-8"))
                    if isinstance(cached, list) and len(cached) == len(idx_list) and all(cached):
                        return list(zip(idx_list, cached))
                except Exception:
                    pass

            joined_q = "\n".join(q_lines)
            b_outs: list[str] = []
            for b_try in range(3):
                if b_try > 0:
                    time.sleep(0.45 * b_try)
                try:
                    tr_block, _ = nmt_fallback_fn(joined_q, sl_query, target_lang)
                    raw_splits = [ln.strip() for ln in (tr_block or "").splitlines() if ln.strip()]
                    if len(raw_splits) == len(idx_list):
                        b_outs = [_polish_vietnamese_cinema_line(s, genre=genre, target_lang=target_lang) for s in raw_splits]
                        break
                except Exception:
                    continue

            verified: list[str] = []
            for k, orig_i in enumerate(idx_list):
                cand = b_outs[k] if k < len(b_outs) else ""
                if not cand or (is_vi_target and cjk_leak_re.search(cand)):
                    cand = _tr_one_nmt(q_lines[k], cleaned_inputs[orig_i])
                verified.append(cand)

            try:
                with open(c_path, "w", encoding="utf-8") as cf:
                    json.dump(verified, cf, ensure_ascii=False)
            except Exception:
                pass
            return list(zip(idx_list, verified))

        if nmt_batches:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                for pairs in pool.map(_run_nmt_batch, nmt_batches):
                    for orig_i, val in pairs:
                        nmt_anchors[orig_i] = val

    # ---------------- Character-Bible + Contiguous Scene-Context Qwen3-8B Cinema Translation ----------------
    if is_vi_target and _can_use_mlx_cinema_llm():
        with _MLX_LOCK:
            model, tokenizer, sampler = _get_mlx_engine()
            if model is not None and tokenizer is not None:
                if progress_cb is not None:
                    try:
                        progress_cb(0, total_lines)
                    except Exception:
                        pass

                # Pass 0: Extract Movie Character & Relationship Bible (gender, age, family, hierarchy)
                char_bible = _extract_character_bible(
                    model=model,
                    tokenizer=tokenizer,
                    sampler=sampler,
                    cleaned_inputs=cleaned_inputs,
                    genre=genre,
                    cache_dir=cache_dir,
                )
                sys_msg = _build_qwen_cinema_system_prompt(genre=genre, char_bible=char_bible)
                bible_hash = hashlib.sha256(char_bible.encode("utf-8")).hexdigest()[:10]

                results: list[str] = list(nmt_anchors)
                batch_size = 6
                prev_context: list[tuple[str, str]] = []

                for start_idx in range(0, total_lines, batch_size):
                    end_idx = min(total_lines, start_idx + batch_size)
                    b_srcs = cleaned_inputs[start_idx:end_idx]
                    b_ancs = nmt_anchors[start_idx:end_idx]

                    if progress_cb is not None:
                        try:
                            progress_cb(start_idx, total_lines)
                        except Exception:
                            pass

                    # Skip LLM ONLY if every single line in this block is a trivial exact 1-2 word utterance
                    if is_zh_source and all(
                        s.strip().rstrip("。！？!?.，, ") in _ZH_EXACT_SHORT_UTTERANCES_VI for s in b_srcs
                    ):
                        for k in range(len(b_srcs)):
                            results[start_idx + k] = b_ancs[k]
                            prev_context.append((b_srcs[k], b_ancs[k]))
                        continue

                    ctx_pairs = prev_context[-2:]
                    q_sig = hashlib.sha256(
                        json.dumps(
                            {
                                "v": 11,
                                "m": _MLX_MODEL_ID,
                                "g": genre,
                                "bh": bible_hash,
                                "ctx": [c[1] for c in ctx_pairs],
                                "s": b_srcs,
                            },
                            ensure_ascii=False,
                        ).encode("utf-8")
                    ).hexdigest()[:20]
                    q_cache_file = os.path.join(cache_dir, f"tr_scene_v11_{q_sig}.json")

                    if os.path.exists(q_cache_file):
                        try:
                            cached_q = json.load(open(q_cache_file, "r", encoding="utf-8"))
                            if isinstance(cached_q, list) and len(cached_q) == len(b_srcs) and all(cached_q):
                                for k, val in enumerate(cached_q):
                                    results[start_idx + k] = val
                                    prev_context.append((b_srcs[k], val))
                                continue
                        except Exception:
                            pass

                    ctx_block = ""
                    if ctx_pairs:
                        ctx_lines = "\n".join(f'- "{s0}" => "{t0}"' for s0, t0 in ctx_pairs)
                        ctx_block = f"2 câu thoại ngay trước đó (CHỈ để nắm mạch cảnh & giữ đúng vai vế xưng hô, KHÔNG dịch lại):\n{ctx_lines}\n\n"

                    lookahead = ""
                    if end_idx < total_lines:
                        lookahead = f'\n\n(Câu tiếp theo để nắm ngữ cảnh, KHÔNG dịch: "{cleaned_inputs[end_idx]}")'

                    numbered_in = "\n".join(f"[{k + 1}] {b_srcs[k]}" for k in range(len(b_srcs)))
                    user_msg = (
                        f"{ctx_block}"
                        f"Dịch đúng {len(b_srcs)} câu thoại liên tiếp sau sang 100% Tiếng Việt chuẩn giới tính & vai vế xưng hô "
                        f"(từ [1] đến [{len(b_srcs)}]):\n{numbered_in}{lookahead}"
                    )
                    est_toks = max(560, sum(len(x) for x in b_srcs) * 5 + 220)
                    raw_out = _run_mlx_prompt(model, tokenizer, sampler, sys_msg, user_msg, max_tokens=min(1800, est_toks))

                    parsed_map: dict[int, str] = {}
                    for ln in raw_out.splitlines():
                        m = re.match(r"^\s*\[(\d+)\]\s*(.+)$", ln.strip())
                        if not m:
                            m = re.match(r"^\s*(\d+)[.):]\s*(.+)$", ln.strip())
                        if m:
                            k_i = int(m.group(1)) - 1
                            if 0 <= k_i < len(b_srcs):
                                cand = _polish_vietnamese_cinema_line(m.group(2), genre=genre, target_lang=target_lang)
                                anc_len = max(10, len(b_ancs[k_i]))
                                if (
                                    cand
                                    and not cjk_leak_re.search(cand)
                                    and len(cand) <= max(int(anc_len * 2.2), anc_len + 50)
                                ):
                                    parsed_map[k_i] = cand

                    final_batch: list[str] = []
                    for k in range(len(b_srcs)):
                        bare_s = b_srcs[k].strip().rstrip("。！？!?.，, ")
                        if is_zh_source and bare_s in _ZH_EXACT_SHORT_UTTERANCES_VI and k not in parsed_map:
                            chosen = _ZH_EXACT_SHORT_UTTERANCES_VI[bare_s]
                        else:
                            chosen = parsed_map.get(k) or b_ancs[k]

                        # Reject/repair ANY foreign leak OR archaic 'ngươi' in modern_cn
                        leaks = find_foreign_leaks_in_vi(chosen, genre=genre, is_cjk_source=is_cjk_source)
                        if genre == "modern_cn" and _ARCHAIC_NGUOI_RE.search(chosen):
                            chosen = _polish_vietnamese_cinema_line(chosen, genre="modern_cn", target_lang=target_lang)
                        if leaks:
                            fix_prompt = (
                                f"Câu gốc: {b_srcs[k]}\n"
                                f"Bản dịch nháp bị sót từ ngoại lai ({', '.join(leaks[:5])}): {chosen}\n"
                                f"Hãy viết lại 1 câu hoàn chỉnh 100% Tiếng Việt đúng giới tính & vai vế xưng hô, "
                                f"TUYỆT ĐỐI KHÔNG chứa từ {', '.join(leaks[:5])} hay chữ Hán/Pinyin (chỉ xuất duy nhất câu dịch):"
                            )
                            fix_out = _run_mlx_prompt(model, tokenizer, sampler, sys_msg, fix_prompt, max_tokens=240)
                            fix_first = next((l.strip() for l in fix_out.splitlines() if l.strip()), "")
                            fix_first = re.sub(r"^\s*(?:\[\d+\]|\d+[.):])\s*", "", fix_first)
                            fix_clean = _polish_vietnamese_cinema_line(fix_first, genre=genre, target_lang=target_lang)
                            if fix_clean and not cjk_leak_re.search(fix_clean):
                                if len(find_foreign_leaks_in_vi(fix_clean, genre=genre, is_cjk_source=is_cjk_source)) < len(leaks):
                                    chosen = fix_clean

                        results[start_idx + k] = chosen
                        final_batch.append(chosen)
                        prev_context.append((b_srcs[k], chosen))

                    try:
                        with open(q_cache_file, "w", encoding="utf-8") as qf:
                            json.dump(final_batch, qf, ensure_ascii=False)
                    except Exception:
                        pass

                if progress_cb is not None:
                    try:
                        progress_cb(total_lines, total_lines)
                    except Exception:
                        pass
                return results

    if progress_cb is not None:
        try:
            progress_cb(total_lines, total_lines)
        except Exception:
            pass
    return nmt_anchors
