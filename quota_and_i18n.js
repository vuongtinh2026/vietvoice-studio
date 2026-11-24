/**
 * VoiceViet Studio Pro v6.2 — Real-Time Quota Manager, Generation Timer & Global i18n Engine
 * - Live Monthly Character Quota Tracking & Deduction across Studio, Audiobook, Dialogue & Word Queue
 * - Generation Elapsed Speed + Audio Duration + Timestamp Formatter
 * - 8-Language Global UI Localization (VI, EN, ZH, JA, KO, ES, FR, RU) + Multi-Currency Pricing (VND / USD)
 */
(function () {
  'use strict';

  const QUOTA_STORAGE_KEY = 'voiceviet_quota_state_v6';
  const LANG_STORAGE_KEY = 'voiceviet_ui_lang_v6';
  const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

  const PLANS = {
    free: {
      id: 'free',
      maxChars: 100000,
      unlimited: false,
      vndPrice: '0',
      usdPrice: '$0',
      nameVi: 'Gói Khởi Đầu',
      nameEn: 'Starter Plan'
    },
    basic: {
      id: 'basic',
      maxChars: 1000000,
      unlimited: false,
      vndPrice: '25.000',
      usdPrice: '$1.99',
      amountVnd: 25000,
      nameVi: 'Gói Thường',
      nameEn: 'Basic Creator'
    },
    standard: {
      id: 'standard',
      maxChars: 10000000,
      unlimited: false,
      vndPrice: '75.000',
      usdPrice: '$4.99',
      amountVnd: 75000,
      nameVi: 'Gói Phổ Thông',
      nameEn: 'Standard Pro'
    },
    vip: {
      id: 'vip',
      maxChars: 100000000,
      unlimited: false,
      vndPrice: '150.000',
      usdPrice: '$9.99',
      amountVnd: 150000,
      nameVi: 'Gói VIP',
      nameEn: 'VIP Studio'
    },
    unlimited: {
      id: 'unlimited',
      maxChars: Infinity,
      unlimited: true,
      vndPrice: '299.000',
      usdPrice: '$19.99',
      amountVnd: 299000,
      nameVi: 'Gói Không Giới Hạn',
      nameEn: 'Unlimited Enterprise'
    }
  };

  // =========================================================================
  // 1. MULTI-LANGUAGE DICTIONARY (8 LANGUAGES)
  // =========================================================================
  const I18N = {
    vi: {
      page_title: 'Voxly — Phòng Thu Giọng Nói AI, Nhân Bản Giọng & Dịch Audio/Video 48kHz',
      brand_sub: 'Phòng thu AI 48kHz • Dịch Audio/Video • 110 Quốc gia',
      tab_free: '✨ Phòng Thu AI 48kHz • 142 Ngôn Ngữ',
      quota_label: 'Còn lại:',
      chars_unit: 'ký tự',
      btn_upgrade_vip: 'Nâng Cấp Gói',
      btn_help_guide: 'Hướng Dẫn',
      sidebar_sec_studio: 'Phòng Thu Sáng Tạo',
      sidebar_sec_biz: 'Thương Mại & Hỗ Trợ',
      nav_studio: 'Studio Soạn Thảo',
      nav_dubbing: 'Dịch Audio & Video',
      nav_clone: 'Nhân Bản Giọng',
      nav_dialogue: 'Hội Thoại Đa Giọng',
      nav_batch: 'Hàng Đợi File Word',
      nav_voices: 'Thư Viện Toàn Cầu',
      nav_voices_badge: '110 Nước',
      nav_pricing: 'Bảng Giá & Gói Cước',
      nav_guide: 'Hướng Dẫn Sử Dụng',
      nav_admin: 'Quản Lý Key & Khách',
      quota_month_title: 'Hạn mức tháng',
      sidebar_upgrade_link: 'Nâng cấp →',
      hero_eyebrow: 'VOXLY AI MASTERING STUDIO • CHUẨN ĐIỆN ẢNH 48.000 Hz',
      hero_collapse: 'Thu gọn',
      hero_expand: 'Mở rộng giới thiệu',
      hero_title: 'Đánh Thức Mọi Câu Chữ & Video Thành Giọng Nói AI Đa Ngôn Ngữ Sống Động',
      hero_desc: 'Tạo Audiobook siêu tốc, dịch & lồng tiếng file MP3/MP4 sang 142 ngôn ngữ, nhân bản giọng chính chủ khóa mật mã riêng tư và tách vai hội thoại xuất thẳng CapCut chỉ trong tích tắc.',
      hero_btn_dub: 'Dịch File MP3 / MP4',
      hero_btn_clone: 'Giọng Độc Quyền Của Tôi',
      hero_btn_voices: 'Kho 1.055+ Giọng Quốc Tế',
      feat1_title: 'Dịch Audio & Video MP4',
      feat1_desc: 'Đưa file MP3/MP4 vào tự nhận diện, dịch & lồng tiếng quốc gia khác',
      feat2_title: 'Két Sắt Nhân Bản 48kHz',
      feat2_desc: 'Mã hóa PBKDF2-SHA256 độc quyền chỉ mình chủ sở hữu dùng',
      feat3_title: 'Đa Giọng & Stem CapCut',
      feat3_desc: 'Tự bóc lời thoại truyện dài & xuất riêng từng nhân vật',
      feat4_title: 'Audiobook Hàng Vạn Từ',
      feat4_desc: 'Nạp hàng loạt file Word .docx, tự chia chương & gộp MP3',
      editor_title: 'Bàn Soạn Thảo Kịch Bản & Truyện Chữ',
      editor_badge: 'Chuẩn hóa thông minh',
      btn_batch_word: 'Nạp nhiều Word',
      btn_import_txt: 'Đọc file (.docx/.txt)',
      btn_fix_caps: 'Sửa chữ IN HOA',
      btn_paste: 'Dán',
      btn_clear: 'Xóa',
      editor_placeholder: 'Nhập hoặc dán kịch bản video, lời bình, bài báo, hoặc toàn bộ tiểu thuyết hàng vạn từ vào đây...\n💡 Mẹo đạo diễn thanh âm: Dùng dấu ... để ngắt nghỉ sâu lắng (0.8s), hoặc chèn [cười], [thở dài], [hắng giọng] để giọng AI diễn xuất như người thật!',
      prosody_label: 'Đạo diễn biểu cảm:',
      cue_pause: 'Ngắt sâu (0.8s)',
      sample_label: 'Kịch bản mẫu:',
      sample_intro: 'Lời chào',
      sample_novel: 'Tiên hiệp (3 chương)',
      sample_news: 'Bản tin AI',
      stat_chars: 'ký tự',
      stat_words: 'từ',
      stat_est: 'Thời lượng ước tính:',
      drop_hint: 'Kéo thả trực tiếp file .docx hoặc .txt vào khung soạn thảo',
      idle_wave: 'Phổ âm Aurora 48kHz sẵn sàng — Nhấn Tạo Giọng Đọc AI để xuất bản âm thanh',
      btn_speak_free: '✨ Tạo Giọng Đọc AI',
      btn_speak_cloud: '✨ Tạo Giọng Đọc AI',
      btn_speak_web: '✨ Tạo Giọng Đọc AI',
      btn_stop: 'Dừng',
      shortcut_hint: 'xuất âm thanh tức thì',
      out_title: 'Bản Thu Master Đã Xuất Xưởng',
      btn_dl_wav: 'Tải .WAV Gốc 48kHz',
      btn_dl_mp3: 'Tải .MP3 (Siêu nhẹ)',
      right_title: 'Bàn Tinh Chỉnh Giọng AI',
      btn_reset: 'Mặc định',
      lbl_country_lang: 'Quốc Gia & Ngôn Ngữ',
      search_voice_ph: 'Gõ nhanh tên nước, ngôn ngữ, giọng...',
      lbl_selected_voice: 'Giọng Đọc Đang Chọn',
      btn_test_voice: 'Nghe Thử Tức Thì (<0.05s)',
      lbl_speed: 'Tốc độ đọc (Speed)',
      lbl_pauses: 'Độ nghỉ hết câu (Pauses)',
      lbl_volume: 'Âm lượng (Master Gain)',
      lbl_mp3: 'Chuẩn nén MP3',
      hist_title: 'Lịch Sử Bản Thu Gần Đây',
      btn_clear_hist: 'Xóa hết',
      pricing_eyebrow: 'Bảng Giá Chính Thức • Tự Động Kích Hoạt Toàn Cầu 24/7',
      pricing_title: 'Bảng Giá Gói Cước Voxly Studio',
      pricing_sub: 'Chi phí siêu tiết kiệm cho nhà sáng tạo YouTube, TikTok, Review Phim & Studio Audiobook — Hỗ trợ thanh toán VietQR (Việt Nam) & Quốc Tế (Visa / Mastercard / PayPal).',
      per_month_unit: 'VNĐ / 1 tháng',
      gen_done_in: 'Tạo xong trong',
      audio_len_label: 'Thời lượng đọc:',
      completed_at: 'Hoàn tất lúc',
      deducted_label: 'Đã trừ',
      remaining_label: 'Còn lại',
      quota_exceeded_msg: 'Hạn mức ký tự của bạn không đủ cho đoạn văn này! Vui lòng nâng cấp gói cước để tiếp tục.',
      unlimited_text: 'Không giới hạn'
    },
    en: {
      page_title: 'Voxly — 48kHz AI Voice Studio, Voice Cloning & Audio/Video Dubbing',
      brand_sub: '48kHz AI Studio • Audio/Video Dubbing • 110 Countries',
      tab_free: '✨ 48kHz AI Studio • 142 Languages',
      quota_label: 'Credits:',
      chars_unit: 'chars',
      btn_upgrade_vip: 'Upgrade Plan',
      btn_help_guide: 'User Guide',
      sidebar_sec_studio: 'Creative Studio',
      sidebar_sec_biz: 'Billing & Support',
      nav_studio: 'Studio Editor',
      nav_dubbing: 'Audio & Video Dubbing',
      nav_clone: 'Private Voice Clone',
      nav_dialogue: 'Multi-Speaker Studio',
      nav_batch: 'Word Batch Queue',
      nav_voices: 'Global Voice Library',
      nav_voices_badge: '110 Countries',
      nav_pricing: 'Pricing & Plans',
      nav_guide: 'How-To Guide',
      nav_admin: 'License & Client Admin',
      quota_month_title: 'Monthly Quota',
      sidebar_upgrade_link: 'Upgrade →',
      hero_eyebrow: 'VOXLY AI AUDIO STUDIO • CINEMATIC 48,000 Hz',
      hero_collapse: 'Collapse',
      hero_expand: 'Expand Banner',
      hero_title: 'Turn Scripts, Audio & Videos Into Lifelike 48kHz Multilingual AI Speech',
      hero_desc: 'Produce full-length Audiobooks, translate & dub MP3/MP4 files into 142 languages, lock your personal cloned voice in an encrypted vault, and export synced CapCut dialogue stems in seconds.',
      hero_btn_dub: 'Translate MP3 / MP4',
      hero_btn_clone: 'My Private Voice Vault',
      hero_btn_voices: 'Explore 1,055+ Global Voices',
      feat1_title: 'MP3 & MP4 AI Dubbing',
      feat1_desc: 'Upload audio or video to auto-transcribe, translate & dub in 142 languages',
      feat2_title: '48kHz Encrypted Clone',
      feat2_desc: 'PBKDF2-SHA256 owner-locked personal voice cloning vault',
      feat3_title: 'Multi-Speaker & CapCut',
      feat3_desc: 'Auto-detect story dialogues & export synced character stems',
      feat4_title: '70,000+ Word Audiobooks',
      feat4_desc: 'Batch import .docx files, auto-split chapters & merge MP3',
      editor_title: 'Script & Audiobook Editor',
      editor_badge: 'Smart Text Normalizer',
      btn_batch_word: 'Batch .docx',
      btn_import_txt: 'Import (.docx/.txt)',
      btn_fix_caps: 'Fix ALL CAPS',
      btn_paste: 'Paste',
      btn_clear: 'Clear',
      editor_placeholder: 'Type or paste your video script, article, narration, or entire novel in ANY of 142 languages...\n💡 Tip: Use ... for natural dramatic pauses (0.8s)! Select your target country/language on the right panel.',
      prosody_label: 'Expressive Cues:',
      cue_pause: 'Deep Pause (0.8s)',
      sample_label: 'Samples:',
      sample_intro: 'Welcome',
      sample_novel: 'Novel (3 Chaps)',
      sample_news: 'AI News',
      stat_chars: 'chars',
      stat_words: 'words',
      stat_est: 'Est. audio duration:',
      drop_hint: 'Drag & drop .docx or .txt files directly into the editor',
      idle_wave: '48kHz Aurora Spectrum Ready — Click Generate AI Voice to render audio',
      btn_speak_free: '✨ Generate AI Voice',
      btn_speak_cloud: '✨ Generate AI Voice',
      btn_speak_web: '✨ Generate AI Voice',
      btn_stop: 'Stop',
      shortcut_hint: 'instant render',
      out_title: 'Master Audio Rendered',
      btn_dl_wav: 'Download 48kHz .WAV',
      btn_dl_mp3: 'Download .MP3 (Compact)',
      right_title: 'Voice Mastering Controls',
      btn_reset: 'Reset',
      lbl_country_lang: 'Country & Language',
      search_voice_ph: 'Search country, language, voice...',
      lbl_selected_voice: 'Active AI Voice',
      btn_test_voice: 'Instant Preview (<0.05s)',
      lbl_speed: 'Speaking Speed',
      lbl_pauses: 'Sentence Pause',
      lbl_volume: 'Master Volume',
      lbl_mp3: 'MP3 Compression',
      hist_title: 'Recent Generations',
      btn_clear_hist: 'Clear all',
      pricing_eyebrow: 'Official Global Pricing • Instant 24/7 Activation',
      pricing_title: 'Voxly Studio Global Plans',
      pricing_sub: 'Ultra-affordable plans for YouTube Creators, TikTokers, Podcasters & Audiobook Studios — Instant checkout via Card / PayPal / VietQR.',
      per_month_unit: '/ month',
      gen_done_in: 'Generated in',
      audio_len_label: 'Audio length:',
      completed_at: 'Finished at',
      deducted_label: 'Used',
      remaining_label: 'Left',
      quota_exceeded_msg: 'Insufficient character quota for this text! Please upgrade your plan to continue.',
      unlimited_text: 'Unlimited'
    },
    zh: {
      brand_sub: '48kHz AI录音棚 • 专属加密声音克隆 • 覆盖110个国家',
      tab_free: '✨ 48kHz 录音棚与全球语音',
      tab_cheap: '云端语音库',
      tab_cheap_badge: '128 音色',
      tab_web: '浏览器语音',
      quota_label: '剩余额度:',
      chars_unit: '字符',
      btn_upgrade_vip: '升级 VIP',
      btn_help_guide: '使用指南',
      sidebar_sec_studio: '创作工作台',
      sidebar_sec_biz: '套餐与帮助',
      nav_studio: '智能配音工作台',
      nav_clone: '专属声音克隆',
      nav_dialogue: '多角色对话配音',
      nav_batch: 'Word 批量队列',
      nav_voices: '全球 110 国语音库',
      nav_voices_badge: '110 国家',
      nav_pricing: '套餐与价格',
      nav_guide: '新手教程',
      quota_month_title: '本月字符额度',
      sidebar_upgrade_link: '立即升级 →',
      hero_eyebrow: 'AI 影视级配音工作站 • 48,000 Hz 高保真母带',
      hero_collapse: '收起',
      hero_expand: '展开介绍',
      hero_title: '将任何文字与长篇小说瞬间转化为栩栩如生的 AI 真人配音',
      hero_desc: '支持数万字有声书自动分章合并、加密个人专属声音克隆、多角色对白分轨导出剪映/CapCut，支持全球 110 个国家与 142 种语言。',
      hero_btn_clone: '我的专属克隆音色',
      hero_btn_voices: '浏览 1,177 款全球音色',
      editor_title: '剧本与有声书编辑器',
      btn_batch_word: '批量导入 Word',
      btn_import_txt: '导入文件',
      btn_fix_caps: '修正大写',
      btn_paste: '粘贴',
      btn_clear: '清空',
      editor_placeholder: '在此输入或粘贴您的视频文案、文章或长篇小说（支持全球142种语言）...',
      btn_speak_free: '✨ 立即生成 AI 配音',
      btn_stop: '停止',
      out_title: '高保真音频已生成',
      btn_dl_wav: '下载 48kHz .WAV',
      btn_dl_mp3: '下载轻量 .MP3',
      right_title: '语音参数调音台',
      lbl_country_lang: '国家与语言',
      search_voice_ph: '搜索国家、语言或音色名...',
      lbl_selected_voice: '当前选中音色',
      btn_test_voice: '极速试听 (<0.05秒)',
      lbl_speed: '语速调节 (Speed)',
      lbl_pauses: '句间停顿 (Pauses)',
      lbl_volume: '音量增益 (Volume)',
      hist_title: '最近生成记录',
      pricing_title: 'Voxly Studio 会员套餐',
      per_month_unit: '/ 月',
      gen_done_in: '生成耗时',
      audio_len_label: '音频时长:',
      completed_at: '完成时间',
      deducted_label: '已扣',
      remaining_label: '剩余',
      quota_exceeded_msg: '当前剩余字符额度不足，请升级套餐后继续生成！',
      unlimited_text: '无限字符'
    },
    ja: {
      brand_sub: '48kHz AI音声スタジオ • 専用ボイスクローン • 世界110ヶ国対応',
      quota_label: '残り文字数:',
      chars_unit: '文字',
      btn_upgrade_vip: 'VIPアップグレード',
      btn_help_guide: '使い方ガイド',
      nav_studio: 'スタジオ編集',
      nav_clone: 'ボイスクローン',
      nav_dialogue: '複数話者スタジオ',
      nav_batch: 'Word一括処理',
      nav_voices: '世界110ヶ国ボイス',
      nav_pricing: '料金プラン',
      nav_guide: '利用ガイド',
      hero_title: 'あらゆる文章や長編小説を自然で感情豊かな 48kHz AI音声へ',
      editor_title: 'スクリプト＆オーディオブック編集',
      editor_placeholder: 'ここに原稿や動画スクリプト、小説を入力または貼り付けてください（142言語対応）...',
      btn_speak_free: '✨ AI音声を生成する',
      btn_test_voice: '瞬時プレビュー (<0.05秒)',
      right_title: 'ボイス調整パネル',
      lbl_country_lang: '国と言語を選択',
      pricing_title: 'Voxly Studio 料金プラン',
      per_month_unit: '/ 月',
      gen_done_in: '生成時間',
      audio_len_label: '音声の長さ:',
      completed_at: '完了時刻',
      deducted_label: '消費',
      remaining_label: '残り',
      unlimited_text: '無制限'
    },
    ko: {
      brand_sub: '48kHz AI 오디오 스튜디오 • 전용 보이스 클로닝 • 110개국 지원',
      quota_label: '남은 글자수:',
      chars_unit: '자',
      btn_upgrade_vip: 'VIP 업그레이드',
      btn_help_guide: '사용 가이드',
      nav_studio: '스튜디오 편집기',
      nav_clone: '나만의 보이스 복제',
      nav_dialogue: '다중 화자 대화',
      nav_batch: 'Word 일괄 변환',
      nav_voices: '글로벌 110개국 보이스',
      nav_pricing: '요금제 안내',
      nav_guide: '이용 가이드',
      hero_title: '모든 대본과 웹소설을 생생한 48kHz AI 성우 음성으로 변환하세요',
      editor_title: '대본 및 오디오북 편집기',
      editor_placeholder: '영상 대본, 기사, 소설 텍스트를 입력하세요 (전 세계 142개 언어 지원)...',
      btn_speak_free: '✨ AI 음성 생성하기',
      btn_test_voice: '즉시 미리듣기 (<0.05초)',
      right_title: '음성 마스터링 설정',
      lbl_country_lang: '국가 및 언어',
      pricing_title: 'Voxly Studio 글로벌 요금제',
      per_month_unit: '/ 월',
      gen_done_in: '생성 소요시간',
      audio_len_label: '오디오 길이:',
      completed_at: '완료 시각',
      deducted_label: '차감',
      remaining_label: '잔여',
      unlimited_text: '무제한'
    },
    es: {
      brand_sub: 'Estudio IA 48kHz • Clonación de Voz Privada • 110 Países',
      quota_label: 'Créditos:',
      chars_unit: 'caract.',
      btn_upgrade_vip: 'Mejorar a VIP',
      btn_help_guide: 'Guía',
      nav_studio: 'Editor de Estudio',
      nav_clone: 'Clonar Voz Privada',
      nav_dialogue: 'Diálogo Multivoz',
      nav_batch: 'Cola de Archivos Word',
      nav_voices: 'Biblioteca 110 Países',
      nav_pricing: 'Planes y Precios',
      nav_guide: 'Guía de Uso',
      hero_title: 'Convierte Cualquier Guion o Novela en Voz IA Realista de 48kHz',
      editor_title: 'Editor de Guiones y Audiolibros',
      editor_placeholder: 'Escribe o pega tu guion, artículo o novela aquí (compatible con 142 idiomas)...',
      btn_speak_free: '✨ Generar Voz IA 48kHz',
      btn_test_voice: 'Vista Previa (<0.05s)',
      right_title: 'Ajustes de Voz IA',
      lbl_country_lang: 'País e Idioma',
      pricing_title: 'Planes de Voxly Studio',
      per_month_unit: '/ mes',
      gen_done_in: 'Generado en',
      audio_len_label: 'Duración:',
      completed_at: 'Hora',
      deducted_label: 'Usado',
      remaining_label: 'Restante',
      unlimited_text: 'Ilimitado'
    },
    fr: {
      brand_sub: 'Studio Audio IA 48kHz • Clonage Vocal Privé • 110 Pays',
      quota_label: 'Crédits:',
      chars_unit: 'caract.',
      btn_upgrade_vip: 'Passer VIP',
      btn_help_guide: 'Guide',
      nav_studio: 'Studio d’Édition',
      nav_clone: 'Clonage Vocal Privé',
      nav_dialogue: 'Dialogue Multi-Voix',
      nav_batch: 'Lot Fichiers Word',
      nav_voices: 'Voix de 110 Pays',
      nav_pricing: 'Tarifs & Abonnements',
      nav_guide: 'Mode d’Emploi',
      hero_title: 'Transformez Vos Scripts et Romans en Voix IA Ultra-Réalistes 48kHz',
      editor_title: 'Éditeur de Scripts & Livres Audio',
      editor_placeholder: 'Saisissez ou collez votre texte dans l’une des 142 langues prises en charge...',
      btn_speak_free: '✨ Générer la Voix IA',
      btn_test_voice: 'Écoute Instantanée (<0.05s)',
      right_title: 'Réglages Vocaux',
      lbl_country_lang: 'Pays & Langue',
      pricing_title: 'Abonnements Voxly Studio',
      per_month_unit: '/ mois',
      gen_done_in: 'Généré en',
      audio_len_label: 'Durée audio:',
      completed_at: 'Terminé à',
      deducted_label: 'Déduit',
      remaining_label: 'Restant',
      unlimited_text: 'Illimité'
    },
    ru: {
      brand_sub: 'ИИ-студия 48 кГц • Приватное клонирование голоса • 110 стран',
      quota_label: 'Лимит:',
      chars_unit: 'симв.',
      btn_upgrade_vip: 'VIP Тарифы',
      btn_help_guide: 'Инструкция',
      nav_studio: 'Студия озвучки',
      nav_clone: 'Клонирование голоса',
      nav_dialogue: 'Мульти-диалоги',
      nav_batch: 'Пакет Word файлов',
      nav_voices: 'Голоса 110 стран',
      nav_pricing: 'Тарифы и цены',
      nav_guide: 'Руководство',
      hero_title: 'Озвучивайте тексты и книги живыми ИИ-голосами 48 кГц на 142 языках',
      editor_title: 'Редактор сценариев и аудиокниг',
      editor_placeholder: 'Введите или вставьте текст для озвучки на любом из 142 языков мира...',
      btn_speak_free: '✨ Создать ИИ-озвучку',
      btn_test_voice: 'Предпрослушивание (<0.05с)',
      right_title: 'Настройки голоса',
      lbl_country_lang: 'Страна и язык',
      pricing_title: 'Тарифные планы Voxly Studio',
      per_month_unit: '/ мес.',
      gen_done_in: 'Создано за',
      audio_len_label: 'Длительность:',
      completed_at: 'Готово в',
      deducted_label: 'Списано',
      remaining_label: 'Остаток',
      unlimited_text: 'Безлимит'
    }
  };

  function detectDefaultLang() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const qLang = (urlParams.get('lang') || '').toLowerCase().slice(0, 2);
      if (I18N[qLang]) {
        localStorage.setItem(LANG_STORAGE_KEY, qLang);
        return qLang;
      }
      const saved = localStorage.getItem(LANG_STORAGE_KEY);
      if (saved && I18N[saved]) return saved;

      // Keep Vietnamese for users in Vietnam timezone; auto-localize for visitors abroad!
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
      const navLang = (navigator.language || 'vi').toLowerCase();
      if (navLang.startsWith('vi') || tz.includes('Saigon') || tz.includes('Ho_Chi_Minh') || tz.includes('Bangkok')) {
        return 'vi';
      }
      const short = navLang.slice(0, 2);
      return I18N[short] ? short : 'en';
    } catch {
      return 'vi';
    }
  }

  let currentLang = detectDefaultLang();

  function t(key) {
    return (I18N[currentLang] && I18N[currentLang][key]) || (I18N.en && I18N.en[key]) || I18N.vi[key] || key;
  }

  // =========================================================================
  // 2. REAL-TIME CHARACTER QUOTA MANAGER
  // =========================================================================
  function loadQuotaState() {
    try {
      const raw = localStorage.getItem(QUOTA_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && PLANS[parsed.planId]) {
          // Auto reset every 30 days
          if (Date.now() - (parsed.periodStartMs || 0) >= THIRTY_DAYS_MS) {
            parsed.usedChars = 0;
            parsed.periodStartMs = Date.now();
            localStorage.setItem(QUOTA_STORAGE_KEY, JSON.stringify(parsed));
          }
          return parsed;
        }
      }
    } catch {}
    const initial = {
      planId: 'free',
      usedChars: 0,
      periodStartMs: Date.now(),
      totalGenerations: 0
    };
    localStorage.setItem(QUOTA_STORAGE_KEY, JSON.stringify(initial));
    return initial;
  }

  let quotaState = loadQuotaState();

  function saveQuotaState() {
    localStorage.setItem(QUOTA_STORAGE_KEY, JSON.stringify(quotaState));
  }

  function formatNumberLocale(num) {
    const loc = currentLang === 'vi' ? 'vi-VN' : 'en-US';
    return Math.max(0, Math.round(num)).toLocaleString(loc);
  }

  function getQuotaSnapshot() {
    const plan = PLANS[quotaState.planId] || PLANS.free;
    const used = Math.max(0, quotaState.usedChars || 0);
    if (plan.unlimited) {
      return {
        plan,
        used,
        max: Infinity,
        remaining: Infinity,
        percentRemaining: 100,
        unlimited: true
      };
    }
    const remaining = Math.max(0, plan.maxChars - used);
    const percentRemaining = plan.maxChars > 0 ? Math.max(0, Math.min(100, (remaining / plan.maxChars) * 100)) : 0;
    return {
      plan,
      used,
      max: plan.maxChars,
      remaining,
      percentRemaining,
      unlimited: false
    };
  }

  function renderQuotaUI(flashDeducted = 0) {
    const snap = getQuotaSnapshot();
    const pointsEl = document.getElementById('userPointsDisplay');
    const pctEl = document.getElementById('sidebarQuotaPercent');
    const barEl = document.getElementById('sidebarQuotaBar');
    const planTextEl = document.getElementById('sidebarQuotaPlanText');
    const usedSubEl = document.getElementById('sidebarQuotaUsedSub');

    const planDisplayName = currentLang === 'vi' ? snap.plan.nameVi : snap.plan.nameEn;

    if (pointsEl) {
      pointsEl.textContent = snap.unlimited ? `♾️ ${t('unlimited_text')}` : formatNumberLocale(snap.remaining);
      if (flashDeducted > 0) {
        pointsEl.classList.add('text-rose-300', 'scale-110');
        setTimeout(() => {
          pointsEl.classList.remove('text-rose-300', 'scale-110');
        }, 650);
      }
    }

    if (pctEl) {
      pctEl.textContent = snap.unlimited
        ? '♾️ 100%'
        : `${snap.percentRemaining >= 10 ? Math.round(snap.percentRemaining) : snap.percentRemaining.toFixed(1)}%`;
      pctEl.className = snap.percentRemaining > 35
        ? 'text-emerald-400 font-bold font-mono text-[11px]'
        : (snap.percentRemaining > 12 ? 'text-amber-300 font-bold font-mono text-[11px]' : 'text-rose-400 font-bold font-mono text-[11px]');
    }

    if (barEl) {
      barEl.style.width = `${snap.unlimited ? 100 : snap.percentRemaining}%`;
      barEl.className = snap.percentRemaining > 35
        ? 'bg-gradient-to-r from-purple-500 via-cyan-400 to-emerald-400 h-full rounded-full transition-all duration-500'
        : (snap.percentRemaining > 12
          ? 'bg-gradient-to-r from-amber-500 to-orange-400 h-full rounded-full transition-all duration-500'
          : 'bg-gradient-to-r from-rose-600 to-orange-500 h-full rounded-full transition-all duration-500');
    }

    if (planTextEl) {
      if (snap.unlimited) {
        planTextEl.innerHTML = `${planDisplayName}: <b class="text-amber-300">${t('unlimited_text')}</b>`;
      } else {
        planTextEl.innerHTML = `${planDisplayName}: <b class="text-slate-100">${formatNumberLocale(snap.remaining)}</b> / ${formatNumberLocale(snap.max)}`;
      }
    }

    if (usedSubEl) {
      usedSubEl.innerHTML = currentLang === 'vi'
        ? `Đã dùng: <b class="text-purple-300 font-mono">${formatNumberLocale(snap.used)}</b> ký tự`
        : `Used: <b class="text-purple-300 font-mono">${formatNumberLocale(snap.used)}</b> chars`;
    }

    // Update top header active plan badge (never display "FREE"!)
    const hdrPlanBadge = document.getElementById('headerActivePlanBadge');
    if (hdrPlanBadge) {
      const pid = snap.plan.id || 'free';
      const tierMapVi = { free: 'STARTER', basic: 'GÓI THƯỜNG', standard: 'PHỔ THÔNG', vip: 'GÓI VIP', unlimited: 'UNLIMITED' };
      const tierMapEn = { free: 'STARTER', basic: 'CREATOR', standard: 'PRO', vip: 'VIP', unlimited: 'UNLIMITED' };
      hdrPlanBadge.textContent = currentLang === 'vi' ? (tierMapVi[pid] || 'PRO') : (tierMapEn[pid] || 'PRO');
    }

    // Show/hide Owner Test Quota Controls inside VietQR Modal based on Owner Vault Token
    const ownerDemoBox = document.getElementById('ownerQuotaTestControls');
    if (ownerDemoBox) {
      const hasOwnerTok = typeof window.getOwnerToken === 'function' && Boolean(window.getOwnerToken());
      ownerDemoBox.classList.toggle('hidden', !hasOwnerTok);
    }
  }

  function checkCanGenerate(charCount) {
    const count = Math.max(0, Number(charCount) || 0);
    if (count === 0) return true;
    const snap = getQuotaSnapshot();
    if (snap.unlimited) return true;
    if (count > snap.remaining) {
      if (typeof window.showToast === 'function') {
        window.showToast(t('quota_exceeded_msg'), 'error');
      }
      if (typeof window.switchStudioView === 'function') {
        setTimeout(() => window.switchStudioView('viewPricing'), 400);
      }
      return false;
    }
    return true;
  }

  function deductCharacters(charCount) {
    const count = Math.max(0, Math.round(Number(charCount) || 0));
    if (count <= 0) return getQuotaSnapshot();
    quotaState.usedChars = Math.max(0, (quotaState.usedChars || 0) + count);
    quotaState.totalGenerations = (quotaState.totalGenerations || 0) + 1;
    saveQuotaState();
    renderQuotaUI(count);
    return getQuotaSnapshot();
  }

  function activatePlan(planId) {
    if (!PLANS[planId]) return;
    quotaState.planId = planId;
    quotaState.usedChars = 0;
    quotaState.periodStartMs = Date.now();
    saveQuotaState();
    renderQuotaUI(0);
  }

  // Format audio duration nicely: e.g. `18.4s` or `02:15 (135.2s)`
  function formatAudioDurationDetailed(secFloat) {
    const sec = Math.max(0.1, Number(secFloat) || 0);
    if (sec < 60) {
      return `${sec.toFixed(1)}s`;
    }
    const mins = Math.floor(sec / 60);
    const rem = Math.round(sec % 60);
    return `${String(mins).padStart(2, '0')}:${String(rem).padStart(2, '0')} (${sec.toFixed(1)}s)`;
  }

  function formatGenerationSpeed(ms) {
    const sec = Math.max(0.01, (Number(ms) || 0) / 1000);
    return sec < 10 ? `${sec.toFixed(2)}s` : `${sec.toFixed(1)}s`;
  }

  function formatClockTimestamp(dateObj = new Date()) {
    const loc = currentLang === 'vi' ? 'vi-VN' : 'en-US';
    return dateObj.toLocaleTimeString(loc, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  // =========================================================================
  // 3. APPLY LANGUAGE & MULTI-CURRENCY PRICING
  // =========================================================================
  function updatePricingCurrencyForLanguage(lang) {
    const isVi = lang === 'vi';
    const priceEls = {
      free: document.getElementById('planPriceFree'),
      basic: document.getElementById('planPriceBasic'),
      standard: document.getElementById('planPriceStandard'),
      vip: document.getElementById('planPriceVip'),
      unlimited: document.getElementById('planPriceUnlimited')
    };
    const unitEls = document.querySelectorAll('.plan-currency-unit');

    if (priceEls.free) priceEls.free.textContent = isVi ? PLANS.free.vndPrice : PLANS.free.usdPrice;
    if (priceEls.basic) priceEls.basic.textContent = isVi ? PLANS.basic.vndPrice : PLANS.basic.usdPrice;
    if (priceEls.standard) priceEls.standard.textContent = isVi ? PLANS.standard.vndPrice : PLANS.standard.usdPrice;
    if (priceEls.vip) priceEls.vip.textContent = isVi ? PLANS.vip.vndPrice : PLANS.vip.usdPrice;
    if (priceEls.unlimited) priceEls.unlimited.textContent = isVi ? PLANS.unlimited.vndPrice : PLANS.unlimited.usdPrice;

    unitEls.forEach(el => {
      el.textContent = t('per_month_unit');
    });

    // Toggle Vietnamese vs Global English pricing card details & Guide blocks
    document.querySelectorAll('.lang-only-vi').forEach(el => el.classList.toggle('hidden', !isVi));
    document.querySelectorAll('.lang-only-global').forEach(el => el.classList.toggle('hidden', isVi));

    const guideVi = document.getElementById('guideContentVi');
    const guideEn = document.getElementById('guideContentEn');
    if (guideVi && guideEn) {
      guideVi.classList.toggle('hidden', !isVi);
      guideEn.classList.toggle('hidden', isVi);
    }
  }

    // =======================================================================
    // VOICE, COUNTRY & REGION DYNAMIC LOCALIZATION HELPERS (ALL 8 LANGUAGES)
    // =======================================================================
    const REGION_LABELS = {
      vi: {
        all: '🌍 Tất cả Thế Giới (110 Nước • 142 Ngôn ngữ)',
        private: '🔒 Giọng Nhân Bản Độc Quyền Của Tôi',
        vi: '🇻🇳 Tiếng Việt (Studio 48kHz)',
        'region:east_asia': '🌏 Khu vực Đông Á (Trung / Đài / HK / Nhật / Hàn / Mông Cổ)',
        'region:sea': '🌴 Khu vực Đông Nam Á (Thái / Indo / Mã / Sing / Phil / Khmer / Lào / Myanmar)',
        'region:south_asia': '🇮🇳 Khu vực Nam Á & Ấn Độ (10 Ngôn ngữ Ấn Độ / Pakistan / Nepal / Sri Lanka)',
        'region:english_world': '🇺🇸🇬🇧 Khối Tiếng Anh Toàn Cầu (Mỹ / Anh / Úc / Canada / NZ / Ireland)',
        'region:europe_west': '🇪🇺 Tây & Nam Âu (Pháp / Đức / TBN / Ý / BĐN / Hà Lan / Bỉ / Thụy Sĩ)',
        'region:europe_north_east': '❄️ Nga, Bắc Âu & Đông Âu (Nga / Ukraina / Ba Lan / Thụy Điển / Na Uy / Séc / Hy Lạp...)',
        'region:americas_es_pt': '🌎 Mỹ Latinh & Brazil (Brazil / Mexico / Argentina / Colombia / Chile... 21 vùng)',
        'region:middle_east_central': '🕌 Trung Đông, 16 Nước Ả Rập & Trung Á (Thổ Nhĩ Kỳ / Iran / Israel / Dubai / Ai Cập...)',
        'region:africa': '🦁 Châu Phi (Nam Phi 3 ngôn ngữ / Nigeria / Kenya / Tanzania / Ethiopia...)'
      },
      en: {
        all: '🌍 All World (110 Countries • 142 Languages)',
        private: '🔒 My Private Cloned Voices',
        vi: '🇻🇳 Vietnamese (48kHz Studio)',
        'region:east_asia': '🌏 East Asia (China / Taiwan / HK / Japan / Korea / Mongolia)',
        'region:sea': '🌴 Southeast Asia (Thailand / Indonesia / Malaysia / SG / PH / Khmer / Lao)',
        'region:south_asia': '🇮🇳 South Asia & India (10 Indian Languages / Pakistan / Nepal / Sri Lanka)',
        'region:english_world': '🇺🇸🇬🇧 Global English (USA / UK / Australia / Canada / NZ / Ireland)',
        'region:europe_west': '🇪🇺 Western & Southern Europe (France / Germany / Spain / Italy / Portugal / NL)',
        'region:europe_north_east': '❄️ Russia, Nordic & Eastern Europe (Russia / Ukraine / Poland / Sweden / Norway)',
        'region:americas_es_pt': '🌎 Latin America & Brazil (Brazil / Mexico / Argentina / Colombia / Chile... 21 locales)',
        'region:middle_east_central': '🕌 Middle East, 16 Arab Nations & Central Asia (Turkey / UAE / Saudi / Egypt...)',
        'region:africa': '🦁 Africa (South Africa / Nigeria / Kenya / Tanzania / Ethiopia...)'
      }
    };

    const VI_VOICE_USECASE_EN = {
      'free-vi-ngoc-huyen': 'Natural expressive Northern Female — Movie Recap, Storytelling & Summaries',
      'free-vi-thien-tam': 'Warm calm Male narrator — Audiobook, Meditation & Late-night Stories',
      'free-vi-minh-quan': 'Clear authoritative Northern Male — Commentary, Tech & News',
      'free-vi-adam-tiktok': 'Humorous natural Male — TikTok / Reels / Shorts (supports [laugh])',
      'free-vi-hoaimy': 'Sweet Neural Female — Novels, Romance & Lifestyle',
      'free-vi-namminh': 'Authoritative Northern Male 48kHz — Documentary, Reportage & Narration',
      'free-vi-google': 'Iconic Classic Female — Memes, Quick News & Short Clips',
      'free-vi-truc-ly': 'Friendly conversational Northern Female — Podcast, Healing & Radio',
      'free-vi-pham-tuyen': 'Powerful heroic Northern Male — Martial Arts, Fantasy & Action',
      'free-vi-my-duyen': 'Gentle Southern Female — Romance & Short Stories',
      'free-vi-hai-dang': 'Broadcast News Anchor Male — News Bulletin & Corporate Presentation',
      'free-vi-mai-anh': 'Crisp News Anchor Female — Breaking News, Journalism & Finance',
      'free-vi-thien-minh': 'Warm Northern Male storyteller — Audiobooks & Bedtime Stories',
      'free-vi-thai-son': 'Deep warm Southern Male — History, Documentary & Memoir',
      'free-vi-ngoc-linh': 'Graceful Northern Female — Historical Drama & Classic Literature',
      'free-vi-adam-nam': 'Youthful natural Southern Male — Vlog, Review & Entertainment',
      'free-vi-quang-son': 'Authentic Central Accent Male — Cultural Stories & Travel',
      'free-vi-ngoc-tran': 'Sweet Central Accent Female — Essays, Travel & Storytelling',
      'free-vi-thuy-dung': 'Standard Southern Female — News Broadcast & IVR Assistant',
      'free-vi-duc-tri': 'Expressive Southern Male — Novels & Long-form Fiction',
      'free-vi-kim-thanh': 'Warm Southern Female — Family Stories & Psychology',
      'free-vi-quoc-tuan': 'Steady clear Northern Male — Documentary, Business Books & Guides',
      'free-vi-thanh-binh': 'Expressive Northern Male — Literature, Essays & Audiobooks',
      'free-vi-minh-triet': 'Modern Southern Male — Daily News, Economy & Reviews',
      'free-vi-quynh-anh': 'Gentle Northern Female — Audiobooks, Romance & Fiction',
      'free-vi-doan-trang': 'Polished Northern Female — Product Demo & E-Learning',
      'free-vi-thuc-doan': 'Expressive Southern Female — Late-night Radio & Storytelling',
      'free-vi-ngoc-ngan': 'Legendary Late-night Ghost & Mystery Storyteller (Turbo Offline)',
      'free-vi-tai-an': 'Historical, Geopolitics & Economic Analysis Male (Turbo Offline)',
      'free-vi-manh-dung': 'Energetic Commercial TVC & Promo Male (Turbo Offline)',
      'free-vi-ban-mai': 'Standard Northern Female for Long Articles & Books (Turbo Offline)',
      'free-vi-duy-oryx': 'Ultra-Deep Cinematic Bass Male — Trailers & Podcasts (Turbo Offline)',
      'free-vi-minh-khang': 'Science, Mystery & Discovery Narrator Male (Turbo Offline)'
    };

    const _dnCache = {};
    function getDisplayNames(lang, type) {
      const key = `${lang}:${type}`;
      if (!_dnCache[key]) {
        try {
          _dnCache[key] = new Intl.DisplayNames([lang === 'vi' ? 'vi' : (I18N[lang] ? lang : 'en'), 'en'], { type });
        } catch {
          _dnCache[key] = null;
        }
      }
      return _dnCache[key];
    }

    function extractFlagEmoji(str) {
      const m = String(str || '').match(/[\u{1F1E6}-\u{1F1FF}]{2}/u);
      return m ? m[0] : '🌐';
    }

    function formatCountryLocaleLabel(voiceObj, langOverride) {
      const lang = langOverride || currentLang;
      if (!voiceObj) return '';
      if (lang === 'vi') return voiceObj.country || voiceObj.language || '';

      const loc = String(voiceObj.language || 'en');
      const flag = extractFlagEmoji(voiceObj.country);
      if (loc === 'vi' || loc.startsWith('vi-')) {
        return '🇻🇳 Vietnam — Vietnamese';
      }

      const parts = loc.split('-');
      const langCode = parts[0].toLowerCase();
      let regionCode = (parts.find(p => p.length === 2 && p === p.toUpperCase()) || '').toUpperCase();
      const subDialect = parts.length >= 3 ? parts[parts.length - 1] : '';

      const regDN = getDisplayNames(lang, 'region');
      const langDN = getDisplayNames(lang, 'language');

      let countryName = '';
      if (regionCode && regDN) {
        try { countryName = regDN.of(regionCode) || regionCode; } catch { countryName = regionCode; }
      }
      let langName = '';
      if (langDN) {
        try { langName = langDN.of(langCode) || langCode.toUpperCase(); } catch { langName = langCode.toUpperCase(); }
      }
      const dialectMap = {
        liaoning: 'Northeast Liaoning',
        shaanxi: 'Shaanxi Xi’an',
        wuu: 'Shanghainese',
        yue: 'Cantonese'
      };
      const dialectNote = subDialect && dialectMap[subDialect.toLowerCase()] ? ` (${dialectMap[subDialect.toLowerCase()]})` : '';
      if (countryName && langName) {
        return `${flag} ${countryName} — ${langName}${dialectNote}`;
      }
      return `${flag} ${langName || countryName || loc}`;
    }

    function formatVoiceDisplayName(voiceObj, langOverride) {
      const lang = langOverride || currentLang;
      if (!voiceObj) return '';
      let n = String(voiceObj.name || '');
      if (lang === 'vi') return n;

      // Translate gender & Vietnamese descriptors inside voice name!
      n = n
        .replace(/\(Nam\)/g, '(Male)')
        .replace(/\(Nữ\)/g, '(Female)')
        .replace(/\(Đa Ngôn Ngữ\)/gi, '(Multilingual)')
        .replace(/\(Podcast 48kHz\)/gi, '(48kHz Podcast)')
        .replace(/\(Kiếm hiệp 48kHz\)/gi, '(48kHz Martial Arts)')
        .replace(/\(Ngôn tình 48kHz\)/gi, '(48kHz Romance)')
        .replace(/\(Thời sự 48kHz\)/gi, '(48kHz News Anchor)')
        .replace(/\(Tin tức 48kHz\)/gi, '(48kHz News)')
        .replace(/\(Tin tức Nam 48kHz\)/gi, '(48kHz Southern News)')
        .replace(/\(Kể chuyện 48kHz\)/gi, '(48kHz Storytelling)')
        .replace(/\(Miền Nam 48kHz\)/gi, '(48kHz Southern)')
        .replace(/\(Miền Trung 48kHz\)/gi, '(48kHz Central)')
        .replace(/\(Cổ trang 48kHz\)/gi, '(48kHz Historical)')
        .replace(/\(Đọc truyện 48kHz\)/gi, '(48kHz Audiobook)')
        .replace(/\(Thuyết minh 48kHz\)/gi, '(48kHz Documentary)')
        .replace(/\(Tự nhiên 48kHz\)/gi, '(48kHz Natural)')
        .replace(/\(Truyện ma đêm khuya\)/gi, '(Late-Night Mystery)')
        .replace(/\(CD Media Lịch sử\)/gi, '(History & Documentary)')
        .replace(/\(Quảng cáo TVC\)/gi, '(Commercial Promo)')
        .replace(/\(Chuẩn giọng Bắc\)/gi, '(Standard Northern)')
        .replace(/\(Nam Siêu Trầm\)/gi, '(Deep Bass Cinema)')
        .replace(/\(Kiến Giải Mã\)/gi, '(Science & Discovery)')
        .replace(/^Chị Google$/i, 'Classic Google Voice (VN)');

      // Replace trailing "• 🇨🇳 Trung Quốc" with localized "• 🇨🇳 China"
      if (n.includes('•') && voiceObj.language && voiceObj.language !== 'vi') {
        const leftPart = n.split('•')[0].trim();
        const flag = extractFlagEmoji(voiceObj.country || n);
        const parts = String(voiceObj.language).split('-');
        const regionCode = (parts.find(p => p.length === 2 && p === p.toUpperCase()) || '').toUpperCase();
        const regDN = getDisplayNames(lang, 'region');
        let cName = regionCode;
        if (regionCode && regDN) {
          try { cName = regDN.of(regionCode) || regionCode; } catch {}
        }
        if (cName) {
          n = `${leftPart} • ${flag} ${cName}`;
        }
      }
      return n;
    }

    function formatVoiceUseCase(voiceObj, langOverride) {
      const lang = langOverride || currentLang;
      if (!voiceObj) return '';
      const raw = String(voiceObj.useCase || '');
      if (lang === 'vi') return raw;

      if (VI_VOICE_USECASE_EN[voiceObj.id]) {
        return VI_VOICE_USECASE_EN[voiceObj.id];
      }
      if (voiceObj.isPrivate || String(voiceObj.id || '').startsWith('private-')) {
        return 'Encrypted Personal 48kHz Cloned Voice (Owner Protected)';
      }

      // International voices: "🇨🇳 Trung Quốc — ... • Nữ Bản Xứ — Warm"
      const locCountry = formatCountryLocaleLabel(voiceObj, lang);
      if (raw.includes('•')) {
        const afterBullet = raw.split('•').slice(1).join('•').trim();
        const translatedTrait = afterBullet
          .replace(/Nữ Bản Xứ/gi, 'Native Female')
          .replace(/Nam Bản Xứ/gi, 'Native Male')
          .replace(/Nam Flagship Polyglot/gi, 'Flagship Polyglot Male')
          .replace(/Nữ Flagship Polyglot/gi, 'Flagship Polyglot Female')
          .replace(/Nam Kể Chuyện Trầm Ấm Đa Ngôn Ngữ/gi, 'Warm Storytelling Multilingual Male')
          .replace(/Nữ Studio Ấm Áp Đa Ngôn Ngữ/gi, 'Warm Studio Multilingual Female')
          .replace(/Nam Trầm Điện Ảnh \/ Trailer Đa Ngôn Ngữ/gi, 'Deep Cinematic Trailer Multilingual Male')
          .replace(/Nữ Biểu Cảm Trẻ Trung Đa Ngôn Ngữ/gi, 'Expressive Youthful Multilingual Female')
          .replace(/Nam Lịch Lãm Đa Ngôn Ngữ/gi, 'Refined Multilingual Male')
          .replace(/Nam Phóng Sự \/ Tài Liệu Đa Ngôn Ngữ/gi, 'Documentary Multilingual Male')
          .replace(/Nữ Thanh Lịch Châu Âu Đa Ngôn Ngữ/gi, 'Elegant Multilingual Female')
          .replace(/Nữ Sôi Nổi Podcast Đa Ngôn Ngữ/gi, 'Upbeat Podcast Multilingual Female');
        return `${locCountry} • ${translatedTrait}`;
      }
      return locCountry || raw;
    }

    function localizeRegionSelectOptions(selectEl, langOverride) {
      if (!selectEl) return;
      const lang = langOverride || currentLang;
      const dict = lang === 'vi' ? REGION_LABELS.vi : REGION_LABELS.en;
      [...selectEl.options].forEach(opt => {
        if (dict[opt.value]) {
          opt.textContent = dict[opt.value];
        }
      });
    }

    function localizeStaticControls(lang) {
      const isVi = lang === 'vi';
      // 1. Country & Region Selects (#languageFilterSelect & #catalogLanguageFilter)
      localizeRegionSelectOptions(document.getElementById('languageFilterSelect'), lang);
      localizeRegionSelectOptions(document.getElementById('catalogLanguageFilter'), lang);

      // 2. MP3 Bitrate Select (#mp3BitrateSelect)
      const mp3Sel = document.getElementById('mp3BitrateSelect');
      if (mp3Sel) {
        const mp3Labels = isVi
          ? {
              '48k': 'Siêu nhẹ (48 kbps Mono - Giảm 65%)',
              '64k': 'Cân bằng (64 kbps Mono - Nét cao)',
              '32k': 'Cực nhẹ (32 kbps Mono - Tiết kiệm nhất)',
              '128k': 'Gốc phòng thu (128 kbps)'
            }
          : {
              '48k': 'Ultra Compact (48 kbps Mono - 65% smaller)',
              '64k': 'Balanced (64 kbps Mono - High Clarity)',
              '32k': 'Smallest Size (32 kbps Mono)',
              '128k': 'Studio Master (128 kbps)'
            };
        [...mp3Sel.options].forEach(o => {
          if (mp3Labels[o.value]) o.textContent = mp3Labels[o.value];
        });
      }

      // 3. Key Badge, Vault Badge, Batch Badge, Native Sample Button & Emotion Cue Buttons
      const hdrKeyLbl = document.getElementById('headerKeyStatusLabel');
      if (hdrKeyLbl && (hdrKeyLbl.textContent.trim() === 'Nhập Key' || hdrKeyLbl.textContent.trim() === 'License Key')) {
        hdrKeyLbl.textContent = isVi ? 'Nhập Key' : 'License Key';
      }
      const vaultBdg = document.getElementById('sidebarVaultBadge');
      if (vaultBdg && !vaultBdg.textContent.includes('Mở') && !vaultBdg.textContent.includes('Unlocked')) {
        vaultBdg.textContent = isVi ? '🔒 Khóa' : '🔒 Locked';
      }
      const btnSample = document.getElementById('btnLoadNativeSample');
      if (btnSample) {
        btnSample.textContent = isVi ? '📝 Mẫu bản ngữ' : '📝 Native Sample';
      }

      // Emotion cue buttons display label
      document.querySelectorAll('.insert-cue-btn, .insert-dialogue-cue-btn').forEach(btn => {
        const cue = (btn.getAttribute('data-cue') || '').trim();
        if (cue === '[cười]') btn.innerHTML = isVi ? '😄 <code>[cười]</code>' : '😄 <code>[cười]</code> Laugh';
        else if (cue === '[thở dài]') btn.innerHTML = isVi ? '😮‍💨 <code>[thở dài]</code>' : '😮‍💨 <code>[thở dài]</code> Sigh';
        else if (cue === '[hắng giọng]') btn.innerHTML = isVi ? '🎙️ <code>[hắng giọng]</code>' : '🎙️ <code>[hắng giọng]</code> Ahem';
      });

      // 4. Global Voice Library (#viewVoices) Header, Search & Sub-Tabs!
      const catSearch = document.getElementById('voiceSearchInput');
      if (catSearch) {
        catSearch.setAttribute('placeholder', isVi ? '🔍 Tìm tên nước, ngôn ngữ, giọng đọc...' : '🔍 Search country, language, or voice...');
      }
      document.querySelectorAll('.catalog-region-tab').forEach(tab => {
        const viTxt = tab.getAttribute('data-label-vi');
        const enTxt = tab.getAttribute('data-label-en');
        if (viTxt && enTxt) tab.textContent = isVi ? viTxt : enTxt;
      });

      // 5. Audiobook Splitter Selects + Voice Clone Gender Select + Placeholders!
      const splitSel = document.getElementById('splitModeSelect');
      if (splitSel) {
        [...splitSel.options].forEach(o => {
          if (o.value === 'auto') o.textContent = isVi ? 'Theo Chương (Tự tách nếu quá dài)' : 'By Chapter (Auto-split if long)';
          if (o.value === 'words') o.textContent = isVi ? 'Chia đều theo số từ (Bỏ qua tiêu đề)' : 'Equal Word Count (Ignore headings)';
        });
      }
      const wordsSel = document.getElementById('wordsPerPartSelect');
      if (wordsSel) {
        const wMap = isVi
          ? { '600': '600 từ (~2.5p - Siêu tốc)', '800': '800 từ (~3.5p - Nhanh)', '1000': '1.000 từ (~4.5p - Chuẩn khuyên dùng)', '1200': '1.200 từ (~5.5p)', '1500': '1.500 từ (~7.0p)', '2000': '2.000 từ (~9.0p - Dài)' }
          : { '600': '600 words (~2.5m - Ultra Fast)', '800': '800 words (~3.5m - Fast)', '1000': '1,000 words (~4.5m - Recommended)', '1200': '1,200 words (~5.5m)', '1500': '1,500 words (~7.0m)', '2000': '2,000 words (~9.0m - Long)' };
        [...wordsSel.options].forEach(o => { if (wMap[o.value]) o.textContent = wMap[o.value]; });
      }
      const cloneGen = document.getElementById('cloneVoiceGenderSelect');
      if (cloneGen) {
        [...cloneGen.options].forEach(o => {
          if (o.value === 'Nam') o.textContent = isVi ? 'Nam' : 'Male';
          if (o.value === 'Nữ') o.textContent = isVi ? 'Nữ' : 'Female';
        });
      }
      const setPh = (id, viPh, enPh) => {
        const el = document.getElementById(id);
        if (el) el.setAttribute('placeholder', isVi ? viPh : enPh);
      };
      setPh('ownerPinInput', 'Nhập Mã PIN / Mật khẩu Chủ Sở Hữu để mở khóa...', 'Enter Owner PIN / Password to unlock vault...');
      setPh('currentPinInput', 'Nhập PIN hiện tại...', 'Current Owner PIN...');
      setPh('newPinInput', 'Nhập mật khẩu bí mật mới...', 'New secret PIN / password...');
      setPh('cloneVoiceNameInput', 'Ví dụ: Giọng Của Tôi (Kể Truyện Độc Quyền)', 'e.g., My Studio Voice (Exclusive Narrator)');
      setPh('cloneVoiceDescInput', 'Ví dụ: Giọng chính chủ kênh YouTube — Cấm sử dụng trái phép', 'e.g., Official YouTube Channel Voice — Owner Protected');
      setPh('modalOwnerPinInput', 'Nhập Mã PIN Chủ Sở Hữu...', 'Enter Owner PIN...');
      setPh('clientLicenseKeyInput', 'Ví dụ: VVPRO-VIP8-8888-DEMO', 'e.g., VVPRO-VIP8-8888-DEMO');
      setPh('dialogueScriptInput',
        'Bạn có thể dán trực tiếp chương truyện dài có lời dẫn & dấu ngoặc kép “...”, hoặc viết theo vai:\nC: Buổi chiều cuối thu... gió thổi xào xạc qua khung cửa sổ nhỏ.\nA: Quân này... đã mười năm rồi chúng ta mới gặp lại nhau đúng không?\nB: [cười] Đúng vậy Huyền... thời gian trôi nhanh thật đấy!',
        'Paste a full story chapter with narration & quotes "...", or write role lines:\nC: Late autumn afternoon... a gentle breeze drifted through the window.\nA: It has been ten years since we last met, hasn\'t it?\nB: [cười] Indeed... time really flies!'
      );
      if (document && t('page_title')) {
        document.title = t('page_title');
      }
    }

  function applyLanguage(lang) {
    if (!I18N[lang]) lang = 'en';
    currentLang = lang;
    localStorage.setItem(LANG_STORAGE_KEY, lang);
    document.documentElement.lang = lang;

    const sel = document.getElementById('uiLangSelect');
    if (sel && sel.value !== lang) sel.value = lang;

    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (key) el.textContent = t(key);
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) el.setAttribute('placeholder', t(key));
    });

    updatePricingCurrencyForLanguage(lang);
    localizeStaticControls(lang);
    renderQuotaUI(0);

    // Notify app.js & studio_pro.js to re-render dynamic Voice Dropdowns, Country Lists, History & Voice Cards immediately!
    window.dispatchEvent(new CustomEvent('voiceviet:langchange', { detail: { lang } }));
  }

  // =========================================================================
  // 4. PAYMENT MODAL TABS (VIETQR + INTERNATIONAL PAYPAL / CARD)
  // =========================================================================
  function setupGlobalPaymentTabs() {
    const tabVn = document.getElementById('payTabVietQr');
    const tabIntl = document.getElementById('payTabGlobal');
    const panelVn = document.getElementById('payPanelVietQr');
    const panelIntl = document.getElementById('payPanelGlobal');

    function switchPayMethod(mode) {
      if (!panelVn || !panelIntl || !tabVn || !tabIntl) return;
      const isVn = mode === 'vn';
      panelVn.classList.toggle('hidden', !isVn);
      panelIntl.classList.toggle('hidden', isVn);
      tabVn.className = isVn
        ? 'flex-1 py-2 rounded-xl bg-purple-600 text-white text-xs font-bold transition cursor-pointer'
        : 'flex-1 py-2 rounded-xl text-slate-400 hover:text-white text-xs font-semibold transition cursor-pointer';
      tabIntl.className = !isVn
        ? 'flex-1 py-2 rounded-xl bg-cyan-500 text-slate-950 text-xs font-extrabold transition cursor-pointer'
        : 'flex-1 py-2 rounded-xl text-slate-400 hover:text-white text-xs font-semibold transition cursor-pointer';
    }

    if (tabVn) tabVn.addEventListener('click', () => switchPayMethod('vn'));
    if (tabIntl) tabIntl.addEventListener('click', () => switchPayMethod('intl'));

    // Auto-select International tab when non-VN language opens checkout
    document.querySelectorAll('.btn-buy-plan').forEach(btn => {
      btn.addEventListener('click', () => {
        const amount = parseInt(btn.getAttribute('data-amount') || '25000', 10);
        const planKey = amount >= 299000 ? 'unlimited' : (amount >= 150000 ? 'vip' : (amount >= 75000 ? 'standard' : 'basic'));
        window.__pendingCheckoutPlanKey = planKey;
        const planObj = PLANS[planKey];
        const intlPriceEl = document.getElementById('globalPayAmountUsd');
        const intlPlanEl = document.getElementById('globalPayPlanName');
        if (intlPriceEl && planObj) intlPriceEl.textContent = `${planObj.usdPrice} USD / month`;
        if (intlPlanEl && planObj) intlPlanEl.textContent = currentLang === 'vi' ? planObj.nameVi : planObj.nameEn;
        switchPayMethod(currentLang === 'vi' ? 'vn' : 'intl');
        renderQuotaUI(0);
      });
    });

    // Owner-only Plan Test Buttons (only visible when Private Owner Vault is unlocked!)
    const btnOwnerActivate = document.getElementById('btnOwnerSimulateActivate');
    const btnOwnerResetFree = document.getElementById('btnOwnerResetFreeQuota');
    if (btnOwnerActivate) {
      btnOwnerActivate.addEventListener('click', () => {
        const key = window.__pendingCheckoutPlanKey || 'vip';
        activatePlan(key);
        const modal = document.getElementById('vietqrModal');
        if (modal) modal.classList.add('hidden');
        if (typeof window.showToast === 'function') {
          window.showToast(`👑 [Chủ Web Test] Đã kích hoạt ${PLANS[key].nameVi}!`, 'success');
        }
      });
    }
    if (btnOwnerResetFree) {
      btnOwnerResetFree.addEventListener('click', () => {
        activatePlan('free');
        const modal = document.getElementById('vietqrModal');
        if (modal) modal.classList.add('hidden');
        if (typeof window.showToast === 'function') {
          window.showToast('🔄 [Chủ Web Test] Đã đặt lại Gói Miễn Phí (100.000 ký tự)!', 'info');
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const sel = document.getElementById('uiLangSelect');
    if (sel) {
      sel.value = currentLang;
      sel.addEventListener('change', () => {
        applyLanguage(sel.value);
      });
    }
    const btnHeaderGuide = document.getElementById('btnHeaderGuide');
    if (btnHeaderGuide) {
      btnHeaderGuide.addEventListener('click', () => {
        if (typeof window.switchStudioView === 'function') {
          window.switchStudioView('viewGuide');
        }
      });
    }
    setupGlobalPaymentTabs();
    applyLanguage(currentLang);
  });

  function syncFromServer({ planId = 'free', usedChars = 0, maxChars = 100000, unlimited = false }) {
    const resolvedPlan = unlimited ? 'unlimited' : (PLANS[planId] ? planId : 'free');
    quotaState.planId = resolvedPlan;
    quotaState.usedChars = Math.max(0, Number(usedChars) || 0);
    if (!unlimited && Number(maxChars) > 0 && PLANS[resolvedPlan]) {
      PLANS[resolvedPlan].maxChars = Number(maxChars);
    }
    saveQuotaState();
    renderQuotaUI(0);
    return getQuotaSnapshot();
  }

  // Expose Public API
  window.VoiceVietQuota = {
    t,
    getLang: () => currentLang,
    setLang: applyLanguage,
    getSnapshot: getQuotaSnapshot,
    checkCanGenerate,
    deductCharacters,
    activatePlan,
    syncFromServer,
    refreshUI: () => renderQuotaUI(0),
    formatAudioDurationDetailed,
    formatGenerationSpeed,
    formatClockTimestamp,
    formatNumberLocale,
    formatCountryLocaleLabel,
    formatVoiceDisplayName,
    formatVoiceUseCase,
    localizeRegionSelectOptions
  };
})();
