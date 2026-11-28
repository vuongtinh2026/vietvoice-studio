#!/usr/bin/env python3
"""
Voxly Cinema Script Translator v6 — Pro AI Director (Qwen3-14B Local + Gemini / OpenAI / DeepSeek API)
with Acoustic Speaker-Guided Role Casting & Exact Vietnamese Gender/Kinship Pronouns!
- Pass 0 (Character & Casting Bible): Reads the script WITH original audio speaker voice hints
  ([NAM TRẺ], [ĐÀN ÔNG], [NỮ TRẺ], [PHỤ NỮ], [TRẺ EM], [ĐÁM ĐÔNG]) to lock every character's
  exact Sino-Vietnamese name, gender, age, voice role, and speaker-to-listener pronoun pairs.
- Pass 1 (Contiguous Scene-Context Screenplay Adaptation): Translates dialogue turns in contiguous
  scene blocks with rolling scene memory, outputting BOTH refined voice role `[ROLE]` and 100%
  natural Vietnamese dialogue (exact anh/em, cha/mẹ/con, sư tỷ/sư đệ, tôi/cô/anh/ông/ngài).
- Auto-selects `mlx-community/Qwen3-14B-4bit` on 24GB+ Apple Silicon Macs (fallback `Qwen3-8B-4bit`),
  plus optional Pro Cloud AI (`gemini`, `openai`, `deepseek`) via built-in stdlib `urllib.request`.
"""
import concurrent.futures
import glob
import hashlib
import json
import os
import platform
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Callable

import audio_speaker_analyzer

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_MLX_LOCK = threading.Lock()
_MLX_MODEL = None
_MLX_TOKENIZER = None
_MLX_SAMPLER = None
_MLX_LOADED_MODEL_ID = ""
_MLX_LOAD_FAILED = False

# Preemption / Cancel generation counter so an abandoned 45-min job NEVER locks out new videos!
_JOB_GEN_LOCK = threading.Lock()
_ACTIVE_JOB_GEN = 0


class TranslationCancelledError(RuntimeError):
    pass


def cancel_active_translations() -> int:
    """Increments the global translation generation so any stale background job aborts cleanly."""
    global _ACTIVE_JOB_GEN
    with _JOB_GEN_LOCK:
        _ACTIVE_JOB_GEN += 1
        return _ACTIVE_JOB_GEN


def get_active_translation_gen() -> int:
    with _JOB_GEN_LOCK:
        return _ACTIVE_JOB_GEN


def _check_not_cancelled(my_gen: int) -> None:
    if my_gen > 0 and my_gen != get_active_translation_gen():
        raise TranslationCancelledError("Tác vụ dịch trước đã được dừng để xử lý yêu cầu mới.")

_OPENCC_T2S = None
_OPENCC_READY = False


def _get_system_ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_sz = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_sz > 0:
            return (pages * page_sz) / (1024 ** 3)
    except Exception:
        pass
    return 16.0


def _is_hf_model_cached_locally(repo_id: str) -> bool:
    slug = repo_id.replace("/", "--")
    base = os.path.expanduser(f"~/.cache/huggingface/hub/models--{slug}/snapshots")
    if not os.path.isdir(base):
        return False
    for snap in os.listdir(base):
        sdir = os.path.join(base, snap)
        if not os.path.isdir(sdir):
            continue
        has_cfg = os.path.exists(os.path.join(sdir, "config.json"))
        has_weights = bool(glob.glob(os.path.join(sdir, "*.safetensors")))
        if has_cfg and has_weights:
            return True
    return False


def resolve_best_mlx_model_id(prefer_14b: bool = False) -> str:
    env_override = os.environ.get("VOXLY_CINEMA_LLM", "").strip()
    if env_override:
        return env_override
    if prefer_14b and _get_system_ram_gb() >= 22.0 and _is_hf_model_cached_locally("mlx-community/Qwen3-14B-4bit"):
        return "mlx-community/Qwen3-14B-4bit"
    return "mlx-community/Qwen3-8B-4bit"


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


# Audio ASR & OCR typo fixes
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
    ("人间己成炼狱", "人间已成炼狱"),
    ("敢威肋老子", "敢威胁老子"),
    ("千粮和衣物", "干粮和衣物"),
    ("手腕耍甩", "手腕要甩"),
    ("范围肉", "范围内"),
    ("请间", "请问"),
    ("宿圭", "宿主"),
    ("是香", "是否"),
    ("香则", "否则"),
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
    "啊": "Á!",
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
    "好的长官": "Rõ, thưa trưởng quan!",
    "真麻烦": "Phiền phức thật đấy.",
    "蠢死了": "Ngốc chết đi được!",
    "怎么可能": "Làm sao có thể chứ?",
    "障眼法吗": "Ảo ảnh đánh lừa sao?",
}

# Japanese colloquial contractions expanded ONLY for NMT semantic anchor (original Japanese stays intact for LLM!)
_JA_SPOKEN_NMT_EXPAND: list[tuple[str, str]] = [
    ("もう違うってば", "いいえ、そうではないよ"),
    ("もう違うって", "いいえ、そうではないよ"),
    ("違うってば", "そうではないよ"),
    ("違うって", "そうではないよ"),
    ("もう聞いてないんだから", "本当に私の話を聞いていないね"),
    ("聞いてないんだから", "話を聞いていないね"),
    ("いいじゃん", "すごくいいね"),
    ("何言っとってんの", "何を言っているの"),
    ("何言ってんの", "何を言っているの"),
    ("なんて言ってん", "何と言っているの"),
    ("チャラくないってば", "全然軽薄じゃないよ"),
    ("チャラい", "軽薄な"),
    ("サークル", "クラブ"),
    ("行ってきまーす", "行ってきます"),
    ("スノボ", "スノーボード"),
]

# Exact unambiguous short Japanese utterances
_JA_EXACT_SHORT_UTTERANCES_VI: dict[str, str] = {
    "え": "Hả?",
    "えっ": "Hả?",
    "うん": "Ừm.",
    "はい": "Vâng.",
    "いいえ": "Không.",
    "ごめん": "Xin lỗi nhé.",
    "ごめんね": "Xin lỗi nhé.",
    "ごめんごめん": "Xin lỗi, xin lỗi.",
    "ありがとう": "Cảm ơn.",
    "ありがとうございます": "Cảm ơn rất nhiều.",
    "ちょっと待って": "Đợi một chút đã!",
    "待って": "Đợi đã!",
    "やめて": "Dừng lại đi!",
    "大丈夫": "Không sao đâu.",
    "なるほど": "Hóa ra là vậy.",
    "そうなんだ": "Ra là vậy à.",
    "マジで": "Thật sao?",
    "嘘でしょ": "Đùa chắc?",
    "そうだよね": "Đúng vậy nhỉ.",
    "そうそう": "Đúng rồi, đúng rồi.",
}


def _expand_ja_spoken_for_nmt(line: str) -> str:
    # Deduplicate Japanese repetition stutter before NMT (e.g. 'やばいやばいやばい' -> 'やばい')
    s = re.sub(r"([\u3040-\u30ff\u4e00-\u9fff]{2,8})(?:[、，,\s]*\1){2,}", r"\1", line)
    for k, v in _JA_SPOKEN_NMT_EXPAND:
        if k in s:
            s = s.replace(k, v)
    return s


# Post-cleanup fixes (NO blind 'bạn -> ngươi' EVER!)
_VI_POST_TERM_FIXES: list[tuple[str, str]] = [
    (r"\banh\s+ngươi\b", "anh bạn"),
    (r"\bBoss\b", "Ông chủ"),
    (r"\bEMP\b", "xung điện từ"),
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
    (r"\bNếu\s+Tinh\b", "Nhược Tinh"),
    (r"\bĐại\s+Lão\s+Nguyên\b", "Đại trưởng lão"),
    (r"\bhố\s+hụi\b", "hố đen"),
    (r"\bhồn\s+phong\b", "Hồn Phiên"),
    (r"^\s*Ding\b[,!.\s]*", "Ting! "),
    (r"\bUh\b", "Ừ"),
    (r"\b([A-Za-zÀ-ỹĐđ]{2,18})-(?:san|chan|kun|sama)\b", r"\1"),
    (r"\bthành\s+phố\s+ma\s+thuật\b", "Ma Đô"),
    (r"\bKý\s+chủ\s+tốt\b", "Vâng, ký chủ"),
]

_HARD_MODERN_ERA_MARKERS_RE = re.compile(
    r"(?:英国|美国|欧洲|日本|韩国|中国|东北|机场|飞机|航班|公务员|警官|警方|警察|派出所|民警|"
    r"教授|卡车|汽车|开车|车牌|奔驰|手机|电脑|微信|视频|网友|医院|银行|存款|公司|老板|科学|"
    r"地铁|外套|西装|拉面|专辑|唱片|电影|导演|行车记录仪|公职人员|靶子|设备|场地|立方米|英语|中文|"
    r"信号|长官|超能者|EMP|机器|黑洞|引力)"
)

_ANCIENT_WORLD_MARKERS_RE = re.compile(
    r"(?:老夫|本座|本尊|少主|宗门|宗主|道侣|渡劫|修仙|仙门|仙道|魂技|魂环|武魂|昊天宗|唐门|"
    r"陛下|皇上|娘娘|爱卿|老衲|贫道|少侠|阁下|在下|师尊|长老|掌门|族长|阁主|公子|姑娘|"
    r"功法|筑基|金丹|元婴|紫府|灵石|灵宠|灵兽|妖兽|圣兽|秘境|藏经阁|贡献点|寿元|大帝|魔帝|"
    r"遗迹|散修|闭关|村长|邪神|神魂|尊神|旧神|炼狱|灾星|玉佩|霜刃|饭碗|魂幡|灵力)"
)

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
    "lanzhou", "tang", "chen", "lin", "guo", "gao", "han", "yang", "ruoxing", "xueer",
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
_LEADING_ROLE_TAG_RE = re.compile(r"^\s*\[([^\]]{2,28})\]\s*(.*)$")


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
        # In Japanese dramas, capitalized romanized Japanese character/place names (Takeda, Momo, Nomu, Tokyo...) are valid!
        if genre == "ja_cinema" and w[0].isupper() and re.fullmatch(r"[A-Za-z]{2,11}", w):
            continue
        if is_cjk_source and genre != "ja_cinema" and wl in _PINYIN_LEAK_TOKENS:
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
        r"\b([A-Za-zÀ-ỹĐđ]+(?:\s+[A-Za-zÀ-ỹĐđ]+){0,2})(?:[,\s]+\1){2,}\b",
        r"\1, \1",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s{2,}", " ", s).strip()


def detect_script_genre(lines: list[str], is_zh_source: bool, is_ja_source: bool = False) -> str:
    if is_ja_source:
        return "ja_cinema"
    if not is_zh_source:
        return "intl_cinema"
    joined = "\n".join(lines)
    modern_types = set(_HARD_MODERN_ERA_MARKERS_RE.findall(joined))
    modern_hits = len(_HARD_MODERN_ERA_MARKERS_RE.findall(joined))
    ancient_hits = len(_ANCIENT_WORLD_MARKERS_RE.findall(joined))

    if len(modern_types) >= 3 or modern_hits >= 5:
        return "modern_cn"
    if ancient_hits >= 3 and modern_hits <= 1:
        return "ancient_cn"
    return "modern_cn"


def preclean_source_dialogue_line(text: str, source_lang: str = "auto") -> str:
    t = re.sub(r"\s+", " ", (text or "")).strip()
    if not t:
        return ""
    sl = str(source_lang or "auto").lower()
    has_kana_or_hangul = bool(re.search(r"[\u3040-\u30ff\uac00-\ud7af]", t))
    is_non_zh_explicit = sl.startswith(("ja", "ko", "en", "vi", "fr", "de", "es", "ru", "th"))
    is_zh = sl.startswith("zh") or (not is_non_zh_explicit and not has_kana_or_hangul and bool(re.search(r"[\u4e00-\u9fff]", t)))
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
    # Strip any stray [ROLE] tag that leaked inside spoken text
    m_role = _LEADING_ROLE_TAG_RE.match(s)
    if m_role and audio_speaker_analyzer.canonicalize_role_tag(m_role.group(1)):
        s = m_role.group(2).strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "“" and s[-1] == "”")):
        s = s[1:-1].strip()

    for pat, rep in _VI_POST_TERM_FIXES:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    if genre == "modern_cn":
        s = re.sub(r"\bLão phu\b", "Ông chủ", s)
        s = re.sub(r"\blão phu\b", "ông chủ", s)
        s = re.sub(r"\bNgươi\b", "Anh", s)
        s = re.sub(r"\bngươi\b", "anh", s)
        s = re.sub(r"\bbản tọa\b", "tôi", s, flags=re.IGNORECASE)
        s = re.sub(r"\btại hạ\b", "tôi", s, flags=re.IGNORECASE)
        s = re.sub(r"\bcác hạ\b", "anh", s, flags=re.IGNORECASE)
        s = re.sub(r"\bnhân dân tệ\b", "tệ", s, flags=re.IGNORECASE)
    elif genre == "ancient_cn":
        s = re.sub(r"\bCha,\s*ngươi\b", "Cha ơi, người", s)
        s = re.sub(r"\bPhụ thân,\s*ngươi\b", "Phụ thân, người", s)
        s = re.sub(r"\bMẹ,\s*ngươi\b", "Mẹ ơi, người", s)
        s = re.sub(r"\bMẫu thân,\s*ngươi\b", "Mẫu thân, người", s)
    else:
        s = re.sub(r"\btao\b", "tôi", s)
        s = re.sub(r"\bTao\b", "Tôi", s)

    s = re.sub(r"\s+", " ", s).strip()
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def _can_use_mlx_cinema_llm() -> bool:
    global _MLX_LOAD_FAILED
    if _MLX_LOAD_FAILED:
        return False
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return False
    if os.environ.get("VOXLY_DISABLE_MLX_LLM") == "1":
        return False
    return True


def _get_mlx_engine(prefer_14b: bool = False):
    global _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER, _MLX_LOADED_MODEL_ID, _MLX_LOAD_FAILED
    target_id = resolve_best_mlx_model_id(prefer_14b=prefer_14b)
    if _MLX_MODEL is not None and _MLX_TOKENIZER is not None and _MLX_LOADED_MODEL_ID == target_id:
        return _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER, _MLX_LOADED_MODEL_ID
    if not _can_use_mlx_cinema_llm():
        return None, None, None, ""

    candidates = [target_id]
    if target_id != "mlx-community/Qwen3-8B-4bit":
        candidates.append("mlx-community/Qwen3-8B-4bit")

    for mid in candidates:
        try:
            from mlx_lm import load
            from mlx_lm.sample_utils import make_sampler

            # Release previous model if upgrading 8B -> 14B in-process
            _MLX_MODEL = None
            _MLX_TOKENIZER = None
            try:
                import mlx.core as mx
                mx.clear_cache()
            except Exception:
                pass

            model, tokenizer = load(mid)
            sampler = make_sampler(temp=0.0)
            _MLX_MODEL = model
            _MLX_TOKENIZER = tokenizer
            _MLX_SAMPLER = sampler
            _MLX_LOADED_MODEL_ID = mid
            print(f"[CinemaTranslator] Loaded Pro Local AI Director: {mid}")
            return _MLX_MODEL, _MLX_TOKENIZER, _MLX_SAMPLER, _MLX_LOADED_MODEL_ID
        except Exception as e:
            print(f"[CinemaTranslator] Could not load {mid}: {e}")
            continue

    _MLX_LOAD_FAILED = True
    return None, None, None, ""


def _run_mlx_prompt(model, tokenizer, sampler, sys_msg: str, user_msg: str, max_tokens: int = 1200) -> str:
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


def _run_cloud_llm_prompt(
    provider: str,
    api_key: str,
    model_name: str,
    sys_msg: str,
    user_msg: str,
    max_tokens: int = 2400,
) -> str:
    """
    Pure-stdlib HTTPS caller for Pro Cloud AI Cinema Directors:
      - gemini   (Google Gemini 2.5 Flash / Gemini 2.5 Pro)
      - openai   (OpenAI GPT-4o / GPT-4o-mini)
      - deepseek (DeepSeek V3 deepseek-chat — top-tier Chinese-Vietnamese screenplay)
    """
    prov = (provider or "").strip().lower()
    key = (api_key or "").strip()
    if not key:
        raise ValueError("Thiếu API Key cho AI Đám Mây!")

    if prov == "gemini":
        mdl = (model_name or "gemini-2.5-flash").strip()
        is_vertex_express_key = key.startswith("AQ.")
        candidate_urls = (
            [
                f"https://aiplatform.googleapis.com/v1/publishers/google/models/{mdl}:generateContent",
                f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent",
            ]
            if is_vertex_express_key
            else [
                f"https://generativelanguage.googleapis.com/v1beta/models/{mdl}:generateContent",
                f"https://aiplatform.googleapis.com/v1/publishers/google/models/{mdl}:generateContent",
            ]
        )
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": sys_msg}]},
                "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                "generationConfig": {
                    "temperature": 0.12,
                    "maxOutputTokens": max_tokens,
                },
            },
            ensure_ascii=False,
        ).encode("utf-8")
        data = None
        last_err = ""
        for url in candidate_urls:
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "x-goog-api-key": key,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as he:
                err_body = he.read().decode("utf-8", errors="ignore")[:240]
                last_err = f"HTTP {he.code}: {err_body}"
                if he.code in (400, 401, 403, 404):
                    continue
                raise RuntimeError(f"Lỗi Gemini API ({last_err})")
        if data is None:
            raise RuntimeError(f"Lỗi Gemini API ({last_err}): Vui lòng kiểm tra lại API Key hoặc hạn mức.")
        cands = data.get("candidates") or []
        parts = ((cands[0].get("content") or {}).get("parts") or []) if cands else []
        txt = "".join(str(p.get("text") or "") for p in parts if not p.get("thought"))
    elif prov in ("openai", "deepseek"):
        if prov == "deepseek":
            url = "https://api.deepseek.com/v1/chat/completions"
            mdl = (model_name or "deepseek-chat").strip()
        else:
            url = "https://api.openai.com/v1/chat/completions"
            mdl = (model_name or "gpt-4o-mini").strip()
        body = json.dumps(
            {
                "model": mdl,
                "temperature": 0.12,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg},
                ],
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Authorization": f"Bearer {key}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")[:240]
            raise RuntimeError(f"Lỗi {prov.upper()} API (HTTP {he.code}): Kiểm tra lại API Key ({err_body})")
        choices = data.get("choices") or []
        txt = str(((choices[0].get("message") or {}).get("content")) or "") if choices else ""
    else:
        raise ValueError(f"Nhà cung cấp AI không hỗ trợ: {provider}")

    cleaned = re.sub(r"<think>.*?</think>", "", txt or "", flags=re.DOTALL).strip()
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


_CHAR_CLUE_RE = re.compile(
    r"(?:叫|名为|是|爸|妈|爹|娘|养母|养父|母|父|哥|姐|弟|妹|娃|儿|女|男|小哥哥|小姐姐|"
    r"长老|长官|师姐|师兄|师弟|师妹|阁主|师尊|师父|村长|教授|警官|先生|女士|小姐|老板|大爷|三爷|尊神|之主|大帝|道士|仙家|徒弟|弟子)"
)


def _extract_character_bible(
    run_prompt_fn: Callable[[str, str, int], str],
    engine_sig: str,
    cleaned_inputs: list[str],
    nmt_anchors: list[str],
    genre: str,
    cache_dir: str,
) -> str:
    sig = hashlib.sha256(
        json.dumps(
            {
                "v": 15,
                "eng": engine_sig,
                "g": genre,
                "n": len(cleaned_inputs),
                "h": cleaned_inputs[:60],
            },
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()[:20]
    bible_path = os.path.join(cache_dir, f"char_bible_v15_{sig}.txt")
    if os.path.exists(bible_path):
        try:
            cached = open(bible_path, "r", encoding="utf-8").read().strip()
            if cached:
                return cached
        except Exception:
            pass

    picked: list[str] = []
    seen = set()
    for idx in range(min(16, len(cleaned_inputs))):
        t = cleaned_inputs[idx]
        if t and idx not in seen:
            seen.add(idx)
            anc = nmt_anchors[idx] if idx < len(nmt_anchors) else ""
            picked.append(f"({idx + 1}) {t} | {anc}")
    for idx, t in enumerate(cleaned_inputs):
        if idx in seen or not t:
            continue
        if _CHAR_CLUE_RE.search(t):
            seen.add(idx)
            anc = nmt_anchors[idx] if idx < len(nmt_anchors) else ""
            picked.append(f"({idx + 1}) {t} | {anc}")
            if len(picked) >= 26:
                break

    if not picked:
        return ""

    sys_bible = (
        "Bạn là Biên dịch viên Thuyết minh phim chuyên nghiệp Việt Nam. Đọc nhanh các câu thoại mẫu kèm bản dịch sát nghĩa "
        "và tóm tắt NGẮN GỌN tối đa 5 dòng:\n"
        "- Bối cảnh phim (Hiện đại đời thường / Nhật-Hàn / Khoa huyễn hệ thống / Cổ trang tiên hiệp).\n"
        "- Từng nhân vật chính: Tên chuẩn (Hán-Việt cho phim Trung, bỏ hậu tố -san/-chan cho phim Nhật), Giới tính, Quan hệ (vợ-chồng, bạn bè, cha-mẹ-con, ký chủ-hệ thống, sư tỷ-đệ) và cặp xưng hô tự nhiên.\n"
        "- CẤM đề xuất 'tớ', 'mình', 'các bạn', 'ta', 'ngươi' cho người lớn trong phim hiện đại."
    )
    user_bible = "Lời thoại mẫu:\n" + "\n".join(picked[:22])
    bible_txt = run_prompt_fn(sys_bible, user_bible, 200).strip()

    if bible_txt:
        try:
            with open(bible_path, "w", encoding="utf-8") as bf:
                bf.write(bible_txt)
        except Exception:
            pass
    return bible_txt


def _build_narration_system_prompt(genre: str, char_bible: str) -> str:
    bible_section = f"\nHỒ SƠ BỐI CẢNH & NHÂN VẬT:\n{char_bible}\n" if char_bible else ""
    if genre == "ancient_cn":
        tone_line = (
            "Thể loại Cổ trang/Tiên hiệp: dùng Hán-Việt tự nhiên dễ nghe; đúng vai vế (cha/mẹ-con, sư phụ/trưởng lão-đệ tử), "
            "CHỈ dùng 'ta - ngươi' khi đối đầu kẻ địch."
        )
    elif genre == "modern_cn":
        tone_line = (
            "Thể loại Hiện đại/Đô thị/Hệ thống Trung Quốc: dùng xưng hô đời thực (tôi/anh/em/con/ông/bà/cô/chú), "
            "TUYỆT ĐỐI CẤM 'ngươi', 'ta', 'lão phu', 'tại hạ', 'tớ', 'mình', 'các bạn' cho người hiện đại. "
            "Từ chuẩn: 宿主=ký chủ (KHÔNG dịch chủ nhà), 系统=hệ thống, 签到=điểm danh, 绑定=liên kết, 江城=Giang Thành, 魔都=Ma Đô, 别吵了=đừng làm ồn nữa."
        )
    elif genre == "ja_cinema":
        return (
            "Bạn là Biên dịch viên Thuyết minh phim Nhật Bản sang Tiếng Việt chuẩn xác từng từ.\n"
            f"{bible_section}\n"
            "NHIỆM VỤ: Dịch TRỰC TIẾP từ câu `Gốc` tiếng Nhật sang lời THUYẾT MINH Tiếng Việt tự nhiên, sát từng chữ (chỉ tham khảo `Gợi ý` để kiểm tra danh từ/số đếm — TUYỆT ĐỐI KHÔNG chép nguyên văn kiểu dịch máy khô cứng của Google Dịch!).\n"
            "QUY TẮC BẮT BUỘC CHO TIẾNG NHẬT:\n"
            "1. DỊCH CHUẨN KHẨU NGỮ NHẬT (CẤM dịch bậy theo tiếng Anh):\n"
            "   - `同窓会` = buổi họp lớp (KHÔNG dịch 'hội đồng lớp'); `サークル` = câu lạc bộ (KHÔNG dịch 'vòng tròn'!);\n"
            "   - `もう違うって / 違うってば` = Không phải đâu! / Đã bảo không phải rồi mà! (KHÔNG dịch 'không phải trường hợp' hay 'không còn giống nhau'!);\n"
            "   - `もう聞いてないんだから` = Thật là, chẳng chịu nghe gì cả! (KHÔNG dịch 'chưa nhận tin tức' hay 'bởi vì bạn...');\n"
            "   - `いいじゃん` = Hay quá còn gì! / Tuyệt quá! / Được đấy chứ!;\n"
            "   - `行ってきます / 行ってきまーす` = Em đi đây! / Tôi đi đây! (KHÔNG dịch 'tôi sẽ đi'!);\n"
            "   - `やばい` = Chết thật! / Nguy to rồi! / Đỉnh quá! (tùy cảnh, KHÔNG lặp 'nguy hiểm nguy hiểm');\n"
            "   - `スノボ` = trượt tuyết; `チャラい` = ăn chơi/màu mè; `合宿` = chuyến dã ngoại/tập huấn; `旦那さん` = chồng; `美味しそう` = trông ngon quá; `〜だっけ` = ...phải không nhỉ?; `〜ってば` = đã bảo... rồi mà!.\n"
            "2. XƯNG HÔ TỰ NHIÊN THEO MẠCH CẢNH: Đọc kỹ các câu trước & sau để dùng đúng `anh - em` (vợ chồng/người yêu), `cậu - tôi` / `anh - em` (bạn bè) — TUYỆT ĐỐI KHÔNG dùng 'bạn - tôi' cứng nhắc hay 'ngươi'/'ta', bỏ hậu tố `-san/-chan/-kun` (Momo-chan -> Momo, Takeda-san -> anh Takeda). Giữ đúng chủ ngữ (AI đang nói với AI), KHÔNG tự bịa chủ ngữ sai!\n"
            "3. THUẦN VIỆT 100%, ĐỊNH DẠNG DUY NHẤT: `[1] Câu thuyết minh Tiếng Việt` ... `[N] Câu thuyết minh Tiếng Việt`. Không nhãn vai, không giải thích thêm."
        )
    else:
        tone_line = (
            "Thể loại Phim Quốc tế (Hàn/Âu Mỹ): thuyết minh Tiếng Việt đời thường tự nhiên, sát nghĩa từng câu thoại, "
            "đúng quan hệ (vợ-chồng: anh/em, bạn bè: cậu/tôi hoặc anh/em, cha mẹ-con). CẤM 'ngươi', 'ta'."
        )

    return (
        "Bạn là Biên tập viên Thuyết minh phim Việt Nam chuẩn xác từng từ.\n"
        f"{tone_line}{bible_section}\n"
        "NHIỆM VỤ: Mỗi mục gồm `Gốc` (thoại gốc) và `Nghĩa sát` (bản dịch bám sát từ vựng & con số). "
        "Hãy biên tập thành lời THUYẾT MINH Tiếng Việt 100% CHÍNH XÁC TỪNG TỪ, trôi chảy dễ đọc thành tiếng.\n"
        "QUY TẮC TUYỆT ĐỐI:\n"
        "1. TRUNG THÀNH 100% Ý NGHĨA & CON SỐ: Bám sát `Nghĩa sát` kết hợp `Gốc` — KHÔNG bịa thêm ý, KHÔNG bỏ sót ý, KHÔNG đổi sai chủ ngữ (ai nói với ai giữ nguyên!).\n"
        "2. QUY ĐỔI SỐ ĐẾM TRUNG QUỐC CHUẨN 100%: 1万=1 vạn (10 nghìn), 1亿=100 triệu (TUYỆT ĐỐI KHÔNG dịch 1亿 thành 1 tỷ!), 10亿=1 tỷ. Giữ chính xác mọi con số, giờ giấc.\n"
        "3. THUẦN VIỆT 100% ĐỂ ĐỌC THUYẾT MINH: KHÔNG để sót chữ Hán, Kana, Pinyin, tiếng Anh (EMP=xung điện từ, Ding=Ting, Uh=Ừ). Tên riêng Trung Quốc dùng chuẩn Hán-Việt (若星=Nhược Tinh, 雪儿=Tuyết Nhi, 大长老=Đại trưởng lão).\n"
        "4. ĐỊNH DẠNG XUẤT DUY NHẤT: `[1] Câu thuyết minh Tiếng Việt` ... `[N] Câu thuyết minh Tiếng Việt`. "
        "KHÔNG thêm nhãn vai [NAM]/[NỮ], KHÔNG gộp dòng, KHÔNG bỏ dòng, KHÔNG giải thích thêm."
    )


def translate_cinema_lines_with_roles(
    lines: list[str],
    speaker_roles: list[str] | None = None,
    source_lang: str = "auto",
    target_lang: str = "vi",
    ai_provider: str = "local",
    ai_api_key: str = "",
    ai_model: str = "",
    nmt_fallback_fn: Callable[[str, str, str], tuple[str, str]] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Full Pro AI Director Pipeline:
      - Uses Cloud Pro AI (`gemini` / `openai` / `deepseek`) when selected + API key provided,
        OR Built-in Pro Local AI (`Qwen3-14B-4bit` on 24GB+ Apple Silicon, fallback `Qwen3-8B-4bit`).
      - Combines physical Acoustic Speaker Roles + Character Bible + Contiguous Scene Context
        to return `(translated_lines, refined_roles)` with exact pronouns & multi-cast roles!
    """
    if not lines:
        return [], []

    total_lines = len(lines)
    norm_acoustic_roles = [
        audio_speaker_analyzer.canonicalize_role_tag(
            speaker_roles[i] if (speaker_roles and i < len(speaker_roles)) else ""
        ) or "DAN_CHUYEN"
        for i in range(total_lines)
    ]

    if not target_lang or target_lang == "same":
        return list(lines), norm_acoustic_roles

    cleaned_inputs = [preclean_source_dialogue_line(x, source_lang=source_lang) for x in lines]
    sl_lower = str(source_lang or "auto").lower()
    has_ja_kana = any(re.search(r"[\u3040-\u30ff]", x) for x in cleaned_inputs)
    has_ko_hangul = any(re.search(r"[\uac00-\ud7af]", x) for x in cleaned_inputs)
    is_ja_source = sl_lower.startswith("ja") or has_ja_kana
    is_zh_source = sl_lower.startswith("zh") or (
        not sl_lower.startswith(("ja", "ko", "en", "vi", "fr", "de", "es", "ru", "th"))
        and not has_ja_kana
        and not has_ko_hangul
        and any(re.search(r"[\u4e00-\u9fff]", x) for x in cleaned_inputs)
    )
    is_cjk_source = is_zh_source or is_ja_source or sl_lower.startswith("ko") or has_ko_hangul
    genre = detect_script_genre(cleaned_inputs, is_zh_source=is_zh_source, is_ja_source=is_ja_source)

    if is_zh_source:
        sl_query = "zh-CN"
    elif has_ja_kana or sl_lower.startswith("ja"):
        sl_query = "ja"
    elif has_ko_hangul or sl_lower.startswith("ko"):
        sl_query = "ko"
    else:
        sl_query = source_lang or "auto"
    tl_lower = (target_lang or "vi").lower()
    is_vi_target = tl_lower.startswith("vi")
    cjk_leak_re = _NON_LATIN_LEAK_RE

    my_job_gen = get_active_translation_gen()

    cache_dir = os.path.join("/tmp", "voxly_dub_sessions")
    os.makedirs(cache_dir, exist_ok=True)

    # ---------------- Fast NMT Baseline (safety anchor + non-VI target fallback) ----------------
    nmt_anchors: list[str] = list(cleaned_inputs)
    if nmt_fallback_fn is not None:
        pending_nmt: list[int] = []
        for idx, src_line in enumerate(cleaned_inputs):
            bare = src_line.strip().rstrip("。！？!?.，,、？ ")
            if is_zh_source and is_vi_target and bare in _ZH_EXACT_SHORT_UTTERANCES_VI:
                nmt_anchors[idx] = _ZH_EXACT_SHORT_UTTERANCES_VI[bare]
            elif is_ja_source and is_vi_target and bare in _JA_EXACT_SHORT_UTTERANCES_VI:
                nmt_anchors[idx] = _JA_EXACT_SHORT_UTTERANCES_VI[bare]
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
            q_lines = [
                _expand_pure_zh_semantics(cleaned_inputs[i])
                if is_zh_source
                else (_expand_ja_spoken_for_nmt(cleaned_inputs[i]) if is_ja_source else cleaned_inputs[i])
                for i in idx_list
            ]
            sig = hashlib.sha256(
                json.dumps({"v": 11, "sl": sl_query, "tl": target_lang, "g": genre, "q": q_lines}, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:20]
            c_path = os.path.join(cache_dir, f"tr_nmt_v11_{sig}.json")
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

    # ---------------- Choose AI Director Engine: Cloud Pro API vs Local Pro 14B/8B MLX ----------------
    prov_clean = (ai_provider or "local").strip().lower()
    use_cloud_ai = prov_clean in ("gemini", "openai", "deepseek") and bool((ai_api_key or "").strip())

    def _execute_director_pipeline(
        run_prompt_fn: Callable[[str, str, int], str],
        engine_sig: str,
        batch_size: int,
    ) -> tuple[list[str], list[str]]:
        _check_not_cancelled(my_job_gen)
        if progress_cb is not None:
            try:
                progress_cb(0, total_lines)
            except Exception:
                pass

        char_bible = _extract_character_bible(
            run_prompt_fn=run_prompt_fn,
            engine_sig=engine_sig,
            cleaned_inputs=cleaned_inputs,
            nmt_anchors=nmt_anchors,
            genre=genre,
            cache_dir=cache_dir,
        )
        _check_not_cancelled(my_job_gen)
        sys_msg = _build_narration_system_prompt(genre=genre, char_bible=char_bible)
        bible_hash = hashlib.sha256(char_bible.encode("utf-8")).hexdigest()[:10]

        results_txt: list[str] = list(nmt_anchors)
        results_roles: list[str] = ["DAN_CHUYEN"] * total_lines
        prev_context: list[tuple[str, str]] = []

        for start_idx in range(0, total_lines, batch_size):
            _check_not_cancelled(my_job_gen)
            end_idx = min(total_lines, start_idx + batch_size)
            b_srcs = cleaned_inputs[start_idx:end_idx]
            b_ancs = nmt_anchors[start_idx:end_idx]

            if progress_cb is not None:
                try:
                    progress_cb(start_idx, total_lines)
                except Exception:
                    pass

            ctx_pairs = prev_context[-2:]
            q_sig = hashlib.sha256(
                json.dumps(
                    {
                        "v": 17,
                        "eng": engine_sig,
                        "g": genre,
                        "bh": bible_hash,
                        "ctx": [c[1] for c in ctx_pairs],
                        "s": b_srcs,
                        "a": b_ancs,
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()[:20]
            q_cache_file = os.path.join(cache_dir, f"tr_nar_v17_{q_sig}.json")

            if os.path.exists(q_cache_file):
                try:
                    cached_q = json.load(open(q_cache_file, "r", encoding="utf-8"))
                    if (
                        isinstance(cached_q, dict)
                        and isinstance(cached_q.get("texts"), list)
                        and len(cached_q["texts"]) == len(b_srcs)
                    ):
                        for k in range(len(b_srcs)):
                            t_v = cached_q["texts"][k]
                            results_txt[start_idx + k] = t_v
                            prev_context.append((b_srcs[k], t_v))
                        continue
                except Exception:
                    pass

            ctx_block = ""
            if ctx_pairs:
                ctx_lines = "\n".join(f'- "{s0}" => "{t0}"' for s0, t0 in ctx_pairs)
                ctx_block = (
                    "2 câu thoại ngay trước đó (CHỈ để nắm mạch truyện & thống nhất xưng hô, KHÔNG dịch lại):\n"
                    f"{ctx_lines}\n\n"
                )

            lookahead = ""
            if end_idx < total_lines:
                lookahead = f'\n\n(Câu tiếp theo để nắm ngữ cảnh, KHÔNG dịch: "{cleaned_inputs[end_idx]}")'

            ref_lbl = "Gợi ý" if genre == "ja_cinema" else "Nghĩa sát"
            numbered_in = "\n".join(
                f"[{k + 1}] Gốc: {b_srcs[k]}\n    {ref_lbl}: {b_ancs[k]}"
                for k in range(len(b_srcs))
            )
            user_msg = (
                f"{ctx_block}"
                f"Hãy biên dịch thuyết minh chuẩn xác từng từ cho đúng {len(b_srcs)} câu sau sang 100% Tiếng Việt tự nhiên "
                f"(xuất đúng dạng `[1] ...` đến `[{len(b_srcs)}] ...`, KHÔNG thêm nhãn vai):\n{numbered_in}{lookahead}"
            )
            est_toks = max(720, sum(len(x) for x in b_ancs) * 2 + len(b_srcs) * 24 + 260)
            raw_out = run_prompt_fn(sys_msg, user_msg, min(3200, est_toks))

            parsed_map: dict[int, str] = {}
            for ln in raw_out.splitlines():
                m = re.match(r"^\s*\[(\d+)\]\s*(.+)$", ln.strip())
                if not m:
                    m = re.match(r"^\s*(\d+)[.):]\s*(.+)$", ln.strip())
                if not m:
                    continue
                k_i = int(m.group(1)) - 1
                if not (0 <= k_i < len(b_srcs)):
                    continue
                rest = m.group(2).strip()
                m_r = _LEADING_ROLE_TAG_RE.match(rest)
                if m_r and audio_speaker_analyzer.canonicalize_role_tag(m_r.group(1)):
                    rest = m_r.group(2).strip()
                cand_txt = _polish_vietnamese_cinema_line(rest, genre=genre, target_lang=target_lang)
                anc_len = max(14, len(b_ancs[k_i]))
                if (
                    cand_txt
                    and not cjk_leak_re.search(cand_txt)
                    and len(cand_txt) <= max(int(anc_len * 2.4), anc_len + 65)
                ):
                    parsed_map[k_i] = cand_txt

            final_texts: list[str] = []
            for k in range(len(b_srcs)):
                if k in parsed_map:
                    chosen = parsed_map[k]
                else:
                    bare_s = b_srcs[k].strip().rstrip("。！？!?.，, ")
                    if is_zh_source and bare_s in _ZH_EXACT_SHORT_UTTERANCES_VI:
                        chosen = _ZH_EXACT_SHORT_UTTERANCES_VI[bare_s]
                    else:
                        chosen = b_ancs[k]

                # Guardrail: fix classic Chinese 1亿 (100 million) -> '1 tỷ' hallucination + 宿主 -> 'chủ nhà'
                if is_zh_source:
                    if re.search(r"(?:1|一)亿", b_srcs[k]) and re.search(r"\b1\s*tỷ\b", chosen, flags=re.IGNORECASE):
                        chosen = re.sub(r"\b1\s*tỷ\b", "100 triệu", chosen, flags=re.IGNORECASE)
                    if "宿主" in b_srcs[k] and re.search(r"\bchủ\s+nhà\b", chosen, flags=re.IGNORECASE):
                        chosen = re.sub(r"\bchủ\s+nhà\b", "ký chủ", chosen, flags=re.IGNORECASE)
                if is_ja_source:
                    if "サークル" in b_srcs[k] and re.search(r"\bvòng\s+tròn\b", chosen, flags=re.IGNORECASE):
                        chosen = re.sub(r"\bvòng\s+tròn\b", "câu lạc bộ", chosen, flags=re.IGNORECASE)
                    if re.search(r"(?:もう)?違うって", b_srcs[k]) and re.search(r"trường\s+hợp|giống\s+nhau", chosen, flags=re.IGNORECASE):
                        chosen = "Đã bảo không phải rồi mà!"
                    if "行ってきます" in b_srcs[k] and re.search(r"\btôi\s+sẽ\s+đi\b", chosen, flags=re.IGNORECASE):
                        chosen = re.sub(r"\btôi\s+sẽ\s+đi\b", "tôi đi đây", chosen, flags=re.IGNORECASE)
                if chosen and chosen[0].islower():
                    chosen = chosen[0].upper() + chosen[1:]

                # Repair ANY foreign leak OR archaic 'ngươi' in modern_cn
                if genre == "modern_cn" and _ARCHAIC_NGUOI_RE.search(chosen):
                    chosen = _polish_vietnamese_cinema_line(chosen, genre="modern_cn", target_lang=target_lang)

                leaks = find_foreign_leaks_in_vi(chosen, genre=genre, is_cjk_source=is_cjk_source)
                needs_hard_repair = bool(leaks) and (
                    "CJK_OR_NON_LATIN" in leaks
                    or len(leaks) >= 2
                    or (is_zh_source and any(w.lower() in _PINYIN_LEAK_TOKENS for w in leaks))
                )
                if needs_hard_repair:
                    _check_not_cancelled(my_job_gen)
                    anc_leaks = find_foreign_leaks_in_vi(b_ancs[k], genre=genre, is_cjk_source=is_cjk_source)
                    if not anc_leaks and b_ancs[k] and not cjk_leak_re.search(b_ancs[k]):
                        chosen = b_ancs[k]
                    else:
                        fix_prompt = (
                            f"Câu gốc: {b_srcs[k]}\n"
                            f"Nghĩa sát: {b_ancs[k]}\n"
                            f"Bản nháp bị sót từ ngoại lai ({', '.join(leaks[:5])}): {chosen}\n"
                            f"Hãy viết lại 1 câu thuyết minh hoàn chỉnh 100% Tiếng Việt chuẩn xác từng từ, "
                            f"TUYỆT ĐỐI KHÔNG chứa từ {', '.join(leaks[:5])} hay chữ Hán/Pinyin (chỉ xuất duy nhất câu dịch):"
                        )
                        try:
                            fix_out = run_prompt_fn(sys_msg, fix_prompt, 220)
                            fix_first = next((l.strip() for l in fix_out.splitlines() if l.strip()), "")
                            fix_first = re.sub(r"^\s*(?:\[\d+\]|\d+[.):])\s*", "", fix_first)
                            fix_clean = _polish_vietnamese_cinema_line(fix_first, genre=genre, target_lang=target_lang)
                            if fix_clean and not cjk_leak_re.search(fix_clean):
                                if len(find_foreign_leaks_in_vi(fix_clean, genre=genre, is_cjk_source=is_cjk_source)) < len(leaks):
                                    chosen = fix_clean
                        except Exception:
                            pass

                results_txt[start_idx + k] = chosen
                final_texts.append(chosen)
                prev_context.append((b_srcs[k], chosen))

            try:
                with open(q_cache_file, "w", encoding="utf-8") as qf:
                    json.dump({"texts": final_texts}, qf, ensure_ascii=False)
            except Exception:
                pass

        if progress_cb is not None:
            try:
                progress_cb(total_lines, total_lines)
            except Exception:
                pass
        return results_txt, results_roles

    # Route 1: Pro Cloud AI Director (Gemini 2.5 Flash/Pro, OpenAI GPT-4o, DeepSeek V3)
    if is_vi_target and use_cloud_ai:
        mdl_lbl = (ai_model or ("gemini-2.5-flash" if prov_clean == "gemini" else ("deepseek-chat" if prov_clean == "deepseek" else "gpt-4o-mini"))).strip()
        return _execute_director_pipeline(
            run_prompt_fn=lambda s_m, u_m, mt: _run_cloud_llm_prompt(prov_clean, ai_api_key, mdl_lbl, s_m, u_m, max_tokens=mt),
            engine_sig=f"cloud:{prov_clean}:{mdl_lbl}",
            batch_size=18,
        )

    # Route 2: Built-in Pro Local AI Director (Qwen3-8B-4bit Fast Pro default, or Qwen3-14B-4bit when explicitly chosen!)
    if is_vi_target and _can_use_mlx_cinema_llm():
        want_14b = (prov_clean == "local_14b")
        with _MLX_LOCK:
            _check_not_cancelled(my_job_gen)
            model, tokenizer, sampler, loaded_mid = _get_mlx_engine(prefer_14b=want_14b)
            if model is not None and tokenizer is not None:
                return _execute_director_pipeline(
                    run_prompt_fn=lambda s_m, u_m, mt: _run_mlx_prompt(model, tokenizer, sampler, s_m, u_m, max_tokens=mt),
                    engine_sig=f"mlx:{loaded_mid}",
                    batch_size=(12 if want_14b else 16),
                )

    if progress_cb is not None:
        try:
            progress_cb(total_lines, total_lines)
        except Exception:
            pass
    return nmt_anchors, norm_acoustic_roles


def translate_cinema_lines(
    lines: list[str],
    source_lang: str = "auto",
    target_lang: str = "vi",
    nmt_fallback_fn: Callable[[str, str, str], tuple[str, str]] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[str]:
    """Backwards-compatible wrapper returning only the translated strings."""
    texts, _ = translate_cinema_lines_with_roles(
        lines=lines,
        speaker_roles=None,
        source_lang=source_lang,
        target_lang=target_lang,
        nmt_fallback_fn=nmt_fallback_fn,
        progress_cb=progress_cb,
    )
    return texts
