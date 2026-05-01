# -*- coding: utf-8 -*-
"""
translations.py
================
i18n dictionary for Sovereign Mind :: MENA Command.

Supported locales:
    - en : English          (LTR)
    - fr : Français         (LTR)
    - ar : العربية الفصحى   (RTL — injects CSS direction:rtl)

Every UI string in app.py routes through `t(key, lang)`.
Add new keys here ONLY — never hard-code UI strings in app.py.
"""

# ---------------------------------------------------------------------------
# Persona metadata is multilingual too — kept here to stay co-located with i18n
# ---------------------------------------------------------------------------
PERSONAS = {
    "MA": {
        "flag": "🇲🇦",
        "code": "MA",
        "capital": {"name": "Rabat", "lat": 34.0209, "lon": -6.8416},
        "colors": {"primary": "#C1272D", "accent": "#006233", "glow": "#FF3B47"},
        "names": {
            "en": "Morocco — The Atlas Strategist",
            "fr": "Maroc — Le Stratège de l’Atlas",
            "ar": "المغرب — استراتيجي الأطلس",
        },
        "doctrine": {
            "en": "Patient, pragmatic positioning. Bridge between Africa, Europe, and the Atlantic.",
            "fr": "Positionnement patient et pragmatique. Pont entre l’Afrique, l’Europe et l’Atlantique.",
            "ar": "تموضع صبور وبراغماتي. جسرٌ بين إفريقيا وأوروبا والمحيط الأطلسي.",
        },
        "pillars": [
            "Green Hydrogen & Renewables",
            "Automotive & Aerospace Manufacturing",
            "Phosphates & Food Security",
            "Africa Gateway / Atlantic Initiative",
            "Tourism & Soft Power",
        ],
    },
    "SA": {
        "flag": "🇸🇦",
        "code": "SA",
        "capital": {"name": "Riyadh", "lat": 24.7136, "lon": 46.6753},
        "colors": {"primary": "#006C35", "accent": "#FFFFFF", "glow": "#00E676"},
        "names": {
            "en": "Saudi Arabia — The Visionary Architect",
            "fr": "Arabie Saoudite — L’Architecte Visionnaire",
            "ar": "المملكة العربية السعودية — المهندس صاحب الرؤية",
        },
        "doctrine": {
            "en": "Ambitious diversification. Re-engineer the economy beyond hydrocarbons.",
            "fr": "Diversification ambitieuse. Réingénierie de l’économie au-delà des hydrocarbures.",
            "ar": "تنويع طموح. إعادة هندسة الاقتصاد إلى ما بعد المحروقات.",
        },
        "pillars": [
            "Vision 2030 / Giga-projects (NEOM, Diriyah)",
            "Energy Transition & PIF Deployment",
            "Tourism & Cultural Soft Power",
            "AI & Semiconductor Sovereignty",
            "Regional Security Architecture",
        ],
    },
    "AE": {
        "flag": "🇦🇪",
        "code": "AE",
        "capital": {"name": "Abu Dhabi", "lat": 24.4539, "lon": 54.3773},
        "colors": {"primary": "#000000", "accent": "#FF0000", "glow": "#00D4FF"},
        "names": {
            "en": "UAE — The Global Connector",
            "fr": "ÉAU — Le Connecteur Mondial",
            "ar": "الإمارات — الرابط العالمي",
        },
        "doctrine": {
            "en": "Hyper-connected, capital-light, talent-magnet. The world’s neutral switchboard.",
            "fr": "Hyper-connecté, peu capitalistique, aimant à talents. Le standard téléphonique neutre du monde.",
            "ar": "فائق الترابط، خفيف رأس المال، مغناطيس للمواهب. مقسّم العالم المحايد.",
        },
        "pillars": [
            "AI Finance & Sovereign Tech (G42, MGX)",
            "Logistics & Aviation Hubs",
            "Crypto / Digital Asset Regulation",
            "Energy Diplomacy (ADNOC, Masdar)",
            "Talent Visas & Global Capital",
        ],
    },
}


# ---------------------------------------------------------------------------
# Master translation dictionary
# ---------------------------------------------------------------------------
TRANSLATIONS = {
    # ---- App chrome ------------------------------------------------------
    "app_title": {
        "en": "SOVEREIGN MIND",
        "fr": "ESPRIT SOUVERAIN",
        "ar": "العقل السيادي",
    },
    "app_subtitle": {
        "en": "MENA Command · Geopolitical Intelligence Console",
        "fr": "Commandement MENA · Console de Renseignement Géopolitique",
        "ar": "قيادة الشرق الأوسط وشمال إفريقيا · منصة الاستخبارات الجيوسياسية",
    },
    "tagline": {
        "en": "See the global event. Decode the hidden link. Act sovereign.",
        "fr": "Voir l’événement mondial. Décoder le lien caché. Agir en souverain.",
        "ar": "ارصد الحدث العالمي. فكّ الرابط الخفي. تصرّف بسيادة.",
    },

    # ---- Sidebar ---------------------------------------------------------
    "sidebar_command": {"en": "COMMAND DECK", "fr": "POSTE DE COMMANDEMENT", "ar": "غرفة القيادة"},
    "sidebar_persona": {
        "en": "Select Sovereign Persona",
        "fr": "Sélectionner la Persona Souveraine",
        "ar": "اختر الشخصية السيادية",
    },
    "sidebar_lang": {"en": "Interface Language", "fr": "Langue de l’interface", "ar": "لغة الواجهة"},
    "sidebar_horizon": {
        "en": "Time Horizon (hours)",
        "fr": "Horizon temporel (heures)",
        "ar": "الأفق الزمني (ساعات)",
    },
    "sidebar_refresh": {"en": "Refresh Intelligence", "fr": "Actualiser le renseignement", "ar": "تحديث الاستخبارات"},
    "sidebar_autorefresh": {
        "en": "Auto-refresh",
        "fr": "Actualisation auto",
        "ar": "التحديث التلقائي",
    },
    "sidebar_autorefresh_interval": {
        "en": "Interval (seconds)",
        "fr": "Intervalle (secondes)",
        "ar": "الفاصل الزمني (ثوانٍ)",
    },
    "sidebar_next_refresh": {
        "en": "Next refresh in",
        "fr": "Prochaine actualisation dans",
        "ar": "التحديث التالي خلال",
    },
    "sidebar_status": {"en": "System Status", "fr": "État du système", "ar": "حالة النظام"},
    "sidebar_last_sync": {"en": "Last sync", "fr": "Dernière sync", "ar": "آخر مزامنة"},
    "sidebar_articles_loaded": {
        "en": "Articles in window",
        "fr": "Articles en mémoire",
        "ar": "المقالات في النافذة",
    },

    # ---- Tabs ------------------------------------------------------------
    "tab_pulse": {"en": "PULSE", "fr": "PULSATION", "ar": "النبض"},
    "tab_butterfly": {"en": "BUTTERFLY MAP", "fr": "CARTE PAPILLON", "ar": "خريطة الفراشة"},
    "tab_network": {"en": "HIDDEN LINKS", "fr": "LIENS CACHÉS", "ar": "الروابط الخفية"},
    "tab_lens": {"en": "SOVEREIGN LENS", "fr": "PRISME SOUVERAIN", "ar": "العدسة السيادية"},
    "tab_decisions": {"en": "DECISIONS", "fr": "DÉCISIONS", "ar": "القرارات"},

    # ---- Pulse tab -------------------------------------------------------
    "pulse_header": {"en": "Live Signal Stream", "fr": "Flux de signaux en direct", "ar": "تدفق الإشارات المباشر"},
    "pulse_caption": {
        "en": "Top events filtered through your sovereign lens.",
        "fr": "Principaux événements filtrés par votre prisme souverain.",
        "ar": "أهم الأحداث مُرشَّحة عبر عدستك السيادية.",
    },

    # ---- Butterfly tab ---------------------------------------------------
    "butterfly_header": {"en": "Butterfly Effect Map", "fr": "Carte de l’effet papillon", "ar": "خريطة أثر الفراشة"},
    "butterfly_caption": {
        "en": "Arcs connect global hotspots to MENA capitals — thicker means stronger inferred linkage.",
        "fr": "Les arcs relient les foyers mondiaux aux capitales MENA — plus épais = lien plus fort.",
        "ar": "الأقواس تربط البؤر العالمية بعواصم منطقتنا — السماكة تعني قوة الارتباط المُستنتَج.",
    },

    # ---- Network tab -----------------------------------------------------
    "network_header": {"en": "Hidden Link Graph", "fr": "Graphe des liens cachés", "ar": "مخطط الروابط الخفية"},
    "network_caption": {
        "en": "Entities → Events → Sovereign Impacts. Pinch to zoom, drag nodes.",
        "fr": "Entités → Événements → Impacts souverains. Pincez pour zoomer, glissez les nœuds.",
        "ar": "الكيانات ← الأحداث ← التأثيرات السيادية. اقرص للتكبير، اسحب العقد.",
    },

    # ---- Lens tab --------------------------------------------------------
    "lens_header": {"en": "Sovereign Lens Analysis", "fr": "Analyse au Prisme Souverain", "ar": "تحليل العدسة السيادية"},
    "lens_caption": {
        "en": "Llama-4-Scout interprets each event against your country’s strategic pillars.",
        "fr": "Llama-4-Scout interprète chaque événement face aux piliers stratégiques de votre pays.",
        "ar": "يفسّر Llama-4-Scout كل حدث في ضوء الركائز الاستراتيجية لبلدك.",
    },

    # ---- Decisions tab ---------------------------------------------------
    "decisions_header": {
        "en": "Strategic Recommendations",
        "fr": "Recommandations stratégiques",
        "ar": "التوصيات الاستراتيجية",
    },
    "advantage_meter": {"en": "National Advantage", "fr": "Avantage national", "ar": "الميزة الوطنية"},
    "risk_meter": {"en": "Geopolitical Risk", "fr": "Risque géopolitique", "ar": "الخطر الجيوسياسي"},
    "recommend_card": {"en": "Recommendation", "fr": "Recommandation", "ar": "توصية"},

    # ---- Generic ---------------------------------------------------------
    "no_data": {
        "en": "No intelligence in window. Run processor.py or wait for next refresh.",
        "fr": "Aucun renseignement dans la fenêtre. Lancez processor.py ou attendez la prochaine actualisation.",
        "ar": "لا توجد استخبارات في النافذة. شغّل processor.py أو انتظر التحديث القادم.",
    },
    "loading": {"en": "Decoding signals…", "fr": "Décodage des signaux…", "ar": "جارٍ فكّ الإشارات…"},
    "footer": {
        "en": "Sovereign Mind · Built for decision-makers · Data is illustrative — verify before acting",
        "fr": "Sovereign Mind · Conçu pour les décideurs · Données illustratives — vérifier avant d’agir",
        "ar": "Sovereign Mind · مُصمَّم لصانعي القرار · البيانات إيضاحية — تحقّق قبل التصرّف",
    },

    # ---- Score labels ----------------------------------------------------
    "score_critical": {"en": "CRITICAL", "fr": "CRITIQUE", "ar": "حرج"},
    "score_high": {"en": "HIGH", "fr": "ÉLEVÉ", "ar": "مرتفع"},
    "score_moderate": {"en": "MODERATE", "fr": "MODÉRÉ", "ar": "متوسط"},
    "score_low": {"en": "LOW", "fr": "FAIBLE", "ar": "منخفض"},

    # ---- Buttons ---------------------------------------------------------
    "btn_open_source": {"en": "Open source", "fr": "Ouvrir la source", "ar": "فتح المصدر"},
    "btn_copy": {"en": "Copy briefing", "fr": "Copier le briefing", "ar": "نسخ الإحاطة"},
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
LANG_LABELS = {
    "en": "English",
    "fr": "Français",
    "ar": "العربية",
}

RTL_LANGS = {"ar"}


def t(key: str, lang: str = "en") -> str:
    """Translate a UI key. Falls back to English, then to the key itself."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGS


def persona_name(code: str, lang: str = "en") -> str:
    p = PERSONAS.get(code)
    if not p:
        return code
    return p["names"].get(lang, p["names"]["en"])


def persona_doctrine(code: str, lang: str = "en") -> str:
    p = PERSONAS.get(code)
    if not p:
        return ""
    return p["doctrine"].get(lang, p["doctrine"]["en"])
