import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# Часовой пояс МСК
MSK_TZ = pytz.timezone('Europe/Moscow')

# =========================================================================
#  СТЫК ДЛЯ РАЗРАБОТЧИКА: ПОДКЛЮЧЕНИЕ РЕАЛЬНОГО БИТРИКС24 (ВМЕСТО ДЕМО)
# =========================================================================
# Твой программист должен удалить функцию fetch_demo_data() ниже и написать 
# получение данных через вебхук. Примерный формат того, что должен отдавать Битрикс:
# deal_id (int), deal_name (str), stage (str), responsible_name (str), observer (str), 
# last_outgoing_touch_at (datetime с таймзоной МСК).

USE_REAL_BITRIX = False # Переключить на True, когда разработчик напишет интеграцию

def get_real_bitrix24_data():
    """Сюда разработчик вставит код запроса к API https://topfranchise.bitrix24.ru/rest/..."""
    # Пример:
    # response = requests.get("https://topfranchise.bitrix24.ru/rest/1/webhook/crm.deal.list...")
    # return df_deals, df_touches, df_calls
    pass

# =========================================================================
#  БИЗНЕС-ПРАВИЛА (ИЕРАРХИЯ КАСАНИЙ И СРОКИ SLA)
# =========================================================================

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
    ("Знакомство / старт", ["курир", "сопровожд", "старт", "запуск", "аккаунт", "куратор", "работ", "поддержк"]),
    ("Баннеры", ["баннер", "размер", "визуал", "реклам", "требован", "формат"]),
    ("Апдейт карточки", ["актуализ", "обновл", "апгрейд", "апдейт", "свеж", "изменен", "услов", "переход"]),
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

def classify_touch_final(text):
    if not text or pd.isna(text): return "Без текста"
    text = str(text).lower()
    for category, keywords in CATEGORIES_HIERARCHY:
        if any(word in text for word in keywords): return category
    return "Другое касание"

def calculate_working_hours_elapsed(start_dt, end_dt):
    """Расчет рабочих часов (9-18, Пн-Пт)"""
    if start_dt > end_dt: return 0.0
    start_dt = start_dt.astimezone(MSK_TZ)
    end_dt = end_dt.astimezone(MSK_TZ)
    total_work_hours = 0.0
    current_day = start_dt.date()
    end_day = end_dt.date()
    
    while current_day <= end_day:
        if current_day.weekday() < 5:
            day_start = datetime.combine(current_day, datetime.min.time()).replace(hour=9, tzinfo=MSK_TZ)
            day_end = datetime.combine(current_day, datetime.min.time()).replace(hour=18, tzinfo=MSK_TZ)
            if current_day == start_dt.date():
                actual_start = max(start_dt, day_start)
                actual_end = day_end
            elif current_day == end_day:
                actual_start = day_start
                actual_end = min(end_dt, day_end)
            else:
                actual_start = day_start
                actual_end = day_end
            if actual_start < actual_end:
                total_work_hours += (actual_end - actual_start).total_seconds() / 3600.0
        current_day += timedelta(days=1)
    return round(total_work_hours, 1)

# ==========================================
#  ГЕНЕРАТОР ДЕМО-ДАННЫХ (ЭСКИЗ)
# ==========================================

@st.cache_data(ttl=86400)
def fetch_demo_data():
    now = datetime.now(MSK_TZ)
    real_managers = ["Валерия Крамаренко", "Елена Булгакова", "Алина Алексеева", "Ирина Шклова", "Наталья Семенова", "Анастасия Салогуб"]
    real_deal_names = ["Суши репаблик", "Бетховен", "Эксперт клининг", "Додо Пицца", "Кофе Хауз", "Шоколадница", "Пятерочка Компакт", "ТопФраншиз Сервис", "ВкусВилл Партнер", "Цветочный Ряд", "Гемотест Лаб", "Долина Детства", "English Точка", "Чио Чио"]
    stages = list(STAGE_THRESHOLDS.keys())
    
    deals_data = []
    for i in range(1, 101):
        stage = stages[i % len(stages)]
        responsible = real_managers[i % len(real_managers)]
        observer = real_managers[(i + 2) % len(real_managers)]
        # УБРАНЫ ПРИПИСКИ МСК-ЦИФРЫ
        deal_name = f"«{random.choice(real_deal_names)}»"
        deal_id = 450000 + i
        
        if i % 3 == 0:
            last_touch_time = now - timedelta(days=random.randint(4, 60), hours=random.randint(1, 10))
        else:
            last_touch_time = now - timedelta(hours=random.randint(1, 12))
            
        deals_data.append({
            "deal_id": deal_id,
            "deal_name": deal_name,
            "stage": stage,
            "responsible_name": responsible,
            "observer": observer,
            "last_outgoing_touch_at": last_touch_time,
            "crm_link": f"https://topfranchise.bitrix24.ru/crm/deal/details/{deal_id}/"
        })
        
    touches_data = []
    calls_data = []
    texts = ["Выставил счет по договору", "Претензия и негатив от клиента", "Направили КП", "Договорились созвониться в zoom", "Прислали анкету и материалы"]
    
    for i in range(1, 500):
        touch_date = now - timedelta(days=i % 15, hours=i % 24)
        manager = real_managers[i % len(real_managers)]
        d_id = 450000 + (i % 100 + 1)
        
        if i % 2 == 0:
            calls_data.append({"call_id": 8000+i, "responsible_name": manager, "duration": random.randint(5, 120), "created_at": touch_date})
        touches_data.append({"deal_id": d_id, "text": random.choice(texts), "created_at": touch_date, "manager_name": manager})
        
    return pd.DataFrame(deals_data), pd.DataFrame(touches_data), pd.DataFrame(calls_data)

# Переключение источников данных
if USE_REAL_BITRIX:
    df_deals, df_touches, df_calls = get_real_bitrix24_data()
else:
    df_deals, df_touches, df_calls = fetch_demo_data()

# ==========================================
#  ИНТЕРФЕЙС И ФИЛЬТРЫ
# ==========================================

st.sidebar.title("🎛️ Панель управления")
if st.sidebar.button("🔄 Обновить данные из CRM"):
    st.cache_data.clear()
    st.rerun()

unique_crm_managers = sorted(list(df_deals["responsible_name"].unique()))
selected_manager = st.sidebar.selectbox("Выберите сотрудника:", ["Все менеджеры"] + unique_crm_managers)

if selected_manager != "Все менеджеры":
    filtered_deals = df_deals[df_deals["responsible_name"] == selected_manager]
else:
    filtered_deals = df_deals

# ==========================================
#  ОБРАБОТКА ИСПРАВЛЕНИЙ СОРТИРОВКИ (В ДНЯХ)
# ==========================================

all_processed_leads = []
current_time_msk = datetime.now(MSK_TZ)

for _, deal in filtered_deals.iterrows():
    stage = deal["stage"]
    last_touch = deal["last_outgoing_touch_at"].astimezone(MSK_TZ)
    
    is_breached = False
    
    # ТЕПЕРЬ ВСЁ СЧИТАЕТСЯ В КЛАССИЧЕСКИХ КАЛЕНДАРНЫХ ДНЯХ ДЛЯ ИДЕАЛЬНОЙ СОРТИРОВКИ В РЕЕСТРЕ
    elapsed_days = round((current_time_msk - last_touch).total_seconds() / 86400.0, 1)
    
    if stage in STAGE_THRESHOLDS:
        rule = STAGE_THRESHOLDS[stage]
        if rule["unit"] == "hours":
            elapsed_work_hours = calculate_working_hours_elapsed(last_touch, current_time_msk)
            if elapsed_work_hours > rule["value"]:
                is_breached = True
        else:
            if elapsed_days > rule["value"]:
                is_breached = True
                
    status_marker = "🔴 Просрочено" if is_breached else "🟢 Норма"
    
    all_processed_leads.append({
        "Статус": status_marker,
        "Название сделки": deal["deal_name"],
        "Текущая стадия": stage,
        "Ответственный": deal["responsible_name"],
        "Наблюдатель": deal["observer"],
        "Дней без связи (число)": elapsed_days, # Числовая колонка для идеальной фильтрации!
        "Последний контакт": last_touch.strftime('%d.%m.%Y %H:%M'),
        "Ссылка на CRM": deal["crm_link"],
        "is_breached": is_breached
    })

df_all_registry = pd.DataFrame(all_processed_leads)
df_red_zone_only = df_all_registry[df_all_registry["is_breached"] == True].drop(columns=["is_breached"])

# Вкладки
st.title("📊 Сквозной контроль воронки сопровождения TopFranchise")
tab_red, tab_all = st.tabs(["🚨 КРАСНАЯ ЗОНА (Нарушения)", "🗂️ РЕЕСТР ВСЕХ СДЕЛОК В РАБОТЕ"])

with tab_red:
    if not df_red_zone_only.empty:
        st.error(f"Внимание! Обнаружено {len(df_red_zone_only)} заброшенных сделок.")
        st.dataframe(
            df_red_zone_only.drop(columns=["Статус"]),
            column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
            use_container_width=True, hide_index=True
        )
    else:
        st.success("Нарушений SLA не обнаружено!")

with tab_all:
    st.subheader("Список всех сделок компании")
    st.info("💡 Кликни на название колонки 'Дней без связи (число)', чтобы мгновенно отсортировать клиентов от самых заброшенных к самым свежим.")
    if not df_all_registry.empty:
        # Автоматическая сортировка по убыванию дней без связи для удобства РОПа
        df_all_registry = df_all_registry.sort_values(by="Дней без связи (число)", ascending=False)
        st.dataframe(
            df_all_registry.drop(columns=["is_breached"]),
            column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
            use_container_width=True, hide_index=True
        )
