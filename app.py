import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# Часовой пояс МСК
MSK_TZ = ZoneInfo('Europe/Moscow')

# КРЕДЕНШИНАЛЫ
BITRIX_WEBHOOK = "https://topfranchise.bitrix24.ru/rest/255/4eqdp6ssove27c7m/"
CATEGORY_ID = 17  # Воронка сопровождения

# ИЕРАРХИЯ КАСАНИЙ
CATEGORIES_HIERARCHY = [
    ("Негатив", ["претенз", "иск", "суд", "жалоб", "негатив", "проблем", "недоволь"]),
    ("Отказ", ["отказ", "неинтерес", "неактуальн", "передум", "небудем", "нерассматрив"]),
    ("Счет / оплата", ["счет", "оплат", "платеж", "реквизит", "плат", "назначен", "ндс"]),
    ("Позитив", ["интерес", "готов", "соглас", "устраив", "подход", "оплатим"]),
    ("Пролонгация", ["продл", "пролонг", "продолж", "период", "сотруднич"]),
    ("Апсел", ["продвиж", "реклам", "стать", "спецпроект", "расширен", "рекомендац", "усил", "увелич", "оптимиз", "вовлеч", "охват", "доп"]),
    ("Цена", ["дорог", "скид", "бюджет", "цен", "дешев", "торг", "уступ", "рассрочк"]),
    ("КП", ["кп", "коммерч", "предлож", "тариф", "пакет", "прайс", "расчет", "смет"]),
    ("Дожим / реактивация", ["актуальн", "ознаком", "рассмотр", "повторн", "возвращ", "потерял", "архив"]),
    ("Документы / юристы", ["договор", "оферт", "юрист", "эдо", "упд", "документ", "возврат", "закрыва"]),
    ("Follow-up", ["обсужд", "подтвержд", "резюм", "бонус"]),
    ("Акт запуска", ["акт", "соглас", "срок", "подпис", "реализац", "опц", "период", "скан"]),
    ("Запуск размещения", ["размещен", "опублик", "индексац", "поисков", "выдач", "активност"]),
    ("Личный Кабинет", ["лк", "кабинет", "доступ", "логин", "пароль", "авториз", "регистрац", "вход"]),
    ("Техподдержка", ["поддерж", "технич", "инструкц", "запрос", "помощ"]),
    ("Знакомство / start", ["курир", "сопровожд", "старт", "запуск", "аккаунт", "куратор", "работ", "поддержк"]),
    ("Баннеры", ["баннер", "размер", "визуал", "реклам", "требован", "формат"]),
    ("Апдейт карточки", ["актуализ", "обновл", "апгрейд", "апдейт", "веж", "изменен", "услов", "переход"]),
    ("Категории / сортировки", ["категор", "сортиров", "подборк", "позици", "видимост", "раздел", "размещени"]),
    ("Анкета / материалы", ["анкет", "заполн", "материал", "фото", "видео", "логотип", "текст", "описан", "карточк", "контент", "макет", "правк", "seo", "уникальн", "презентац", "отзыв", "кейс", "верст", "картинк", "блок", "страниц"]),
    ("Лиды / эффективность", ["лид", "трафик", "отклик", "результат", "выхлоп", "спад", "падени"]),
    ("Аналитика / отчет", ["отчет", "статист", "аналит", "эффектив", "показ", "просмотр", "переход", "динамик", "рост", "паден", "заявк", "конверси"]),
    ("Обратная связь", ["обратн", "оценк", "мнен", "впечатл", "опрос", "nps"]),
    ("Созвон", ["звон", "созвон", "переговор", "разговор", "обсуд", "телемос", "зум", "zoom", "слот", "встреч", "врем", "назнач", "планир"])
]

STAGE_THRESHOLDS = {
    "Передача аккаунт-менеджеру": {"value": 3, "unit": "hours"},
    "Подготовка к размещению": {"value": 3, "unit": "hours"},
    "Создание и согласование страницы": {"value": 3, "unit": "hours"},
    "Акт по запуску рекламы": {"value": 3, "unit": "hours"},
    "Активация страницы": {"value": 3, "unit": "hours"},
    "Размещение": {"value": 21, "unit": "days"},
    "Апдейт карточки": {"value": 21, "unit": "days"},
    "НФ Размещение": {"value": 21, "unit": "days"},
    "Реализация доп.услуг": {"value": 21, "unit": "days"},
    "Акт запуска доп опций": {"value": 21, "unit": "days"},
    "Отчёт по реализованным услугам": {"value": 21, "unit": "days"},
    "Сверка по сортировкам": {"value": 21, "unit": "days"},
    "Опрос NPS": {"value": 21, "unit": "days"},
    "Подготовка к пролонгации": {"value": 14, "unit": "days"},
    "Переговоры о пролонгации": {"value": 3, "unit": "days"},
    "Выставлен счет": {"value": 2, "unit": "days"},
    "Поставщики": {"value": 40, "unit": "days"},
    "РАЗРАБОТКА": {"value": 60, "unit": "days"},
    "Отказ от пролонгации": {"value": 60, "unit": "days"}
}

def parse_bx_date(date_str):
    if not date_str or pd.isna(date_str):
        return datetime.now(MSK_TZ)
    dt = pd.to_datetime(date_str)
    if dt.tz is None:
        dt = dt.tz_localize('UTC')
    return dt.tz_convert('Europe/Moscow').to_pydatetime()

def calculate_working_hours_elapsed(start_dt, end_dt):
    if start_dt > end_dt: return 0.0
    total_work_hours = 0.0
    current_day = start_dt.date()
    end_day = end_dt.date()
    while current_day <= end_day:
        if current_day.weekday() < 5:
            day_start = datetime.combine(current_day, datetime.min.time(), tzinfo=MSK_TZ).replace(hour=9)
            day_end = datetime.combine(current_day, datetime.min.time(), tzinfo=MSK_TZ).replace(hour=18)
            actual_start = max(start_dt, day_start) if current_day == start_dt.date() else day_start
            actual_end = min(end_dt, day_end) if current_day == end_day else day_end
            if actual_start < actual_end:
                total_work_hours += (actual_end - actual_start).total_seconds() / 3600.0
        current_day += timedelta(days=1)
    return round(total_work_hours, 1)

def classify_touch_final(text):
    if not text or pd.isna(text): return "Без текста"
    text = str(text).lower()
    for category, keywords in CATEGORIES_HIERARCHY:
        if any(word in text for word in keywords): return category
    return "Другое касание"

@st.cache_data(ttl=300)
def load_all_bitrix_data(start_date, end_date):
    debug_sample = {}
    try:
        # 1. Загрузка пользователей
        user_map = {}
        start = 0
        while True:
            u_resp = requests.get(f"{BITRIX_WEBHOOK}user.get", params={"start": start}).json()
            for u in u_resp.get("result", []):
                name = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
                user_map[str(u["ID"])] = name if name else f"ID {u['ID']}"
            if "next" in u_resp: start = u_resp["next"]
            else: break

        # 2. Справочник стадий
        s_resp = requests.post(f"{BITRIX_WEBHOOK}crm.status.list", json={"filter": {"ENTITY_ID": f"DEAL_STAGE_{CATEGORY_ID}"}}).json()
        stage_map = {s["STATUS_ID"]: s["NAME"] for s in s_resp.get("result", [])}

        # 3. Загрузка ВСЕХ активных сделок
        raw_deals = []
        start = 0
        while True:
            d_resp = requests.post(f"{BITRIX_WEBHOOK}crm.deal.list", json={
                "filter": {"CATEGORY_ID": CATEGORY_ID, "STAGE_SEMANTIC_ID": "P"},
                "select": ["ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID", "DATE_MODIFY"],
                "start": start
            }).json()
            raw_deals.extend(d_resp.get("result", []
