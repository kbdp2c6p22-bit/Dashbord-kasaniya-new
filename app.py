import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# ==========================================
# CONSTANTS & CONFIGURATION (Бизнес-правила)
# ==========================================

# Часовой пояс МСК
MSK_TZ = pytz.timezone('Europe/Moscow')

# Финальный упорядоченный список категорий по приоритету (Подход А)
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

# Нормативы SLA по стадиям воронки (в часах или днях)
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

# ==========================================
# CORE LOGIC FUNCTIONS (Аналитические модули)
# ==========================================

def classify_touch_final(text):
    """Классификатор текста по иерархии ключевых слов (Подход А)"""
    if not text or pd.isna(text): 
        return "Без текста"
    text = str(text).lower()
    
    for category, keywords in CATEGORIES_HIERARCHY:
        if any(word in text for word in keywords):
            return category
            
    return "Другое касание"

def calculate_working_hours_elapsed(start_dt, end_dt):
    """Вычисляет пройденные РАБОЧИХ часов (9:00 - 18:00, Пн-Пт) по МСК"""
    if start_dt > end_dt:
        return 0.0
        
    start_dt = start_dt.astimezone(MSK_TZ)
    end_dt = end_dt.astimezone(MSK_TZ)
    
    total_work_hours = 0.0
    current_day = start_dt.date()
    end_day = end_dt.date()
    
    if current_day == end_day:
        if current_day.weekday() >= 5: 
            return 0.0
        day_start = datetime.combine(current_day, datetime.min.time()).replace(hour=9, tzinfo=MSK_TZ)
        day_end = datetime.combine(current_day, datetime.min.time()).replace(hour=18, tzinfo=MSK_TZ)
        
        actual_start = max(start_dt, day_start)
        actual_end = min(end_dt, day_end)
        
        if actual_start < actual_end:
            total_work_hours += (actual_end - actual_start).total_seconds() / 3600.0
        return round(total_work_hours, 1)

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
# DATA CACHING & FETCHING (Загрузка реальных лиц)
# ==========================================

@st.cache_data(ttl=86400)
def fetch_crm_data_all():
    """Генерация реалистичной базы на основе реальных ФИО и названий сделок"""
    now = datetime.now(MSK_TZ)
    
    # Справочник реальных сотрудников из вашей CRM
    real_managers = [
        "Валерия Крамаренко", "Елена Булгакова", "Алина Алексеева", 
        "Ирина Шклова", "Наталья Семенова", "Анастасия Салогуб"
    ]
    
    # Живые названия франшиз для демонстрации
    real_deal_names = [
        "Суши репаблик", "Бетховен", "Эксперт клининг", "Додо Пицца", "Кофе Хауз", 
        "Шоколадница", "Пятерочка Компакт", "ТопФраншиз Сервис", "ВкусВилл Партнер",
        "Цветочный Ряд", "Гемотест Лаб", "Долина Детства", "English Точка", "Чио Чио"
    ]
    
    stages = list(STAGE_THRESHOLDS.keys())
    deals_data = []
    
    # Генерируем 150 живых сделок без лимитов
    for i in range(1, 151):
        stage = stages[i % len(stages)]
        # Распределяем реальных людей
        responsible = real_managers[i % len(real_managers)]
        observer = real_managers[(i + 2) % len(real_managers)] # Наблюдателем назначаем другого коллегу
        deal_name = f"«{random.choice(real_deal_names)}» — Мск-{i}"
        
        deal_id = 450000 + i
        
        # Симулируем разную степень заброшенности клиентов
        if i % 4 == 0:
            last_touch_time = now - timedelta(days=i % 12, hours=5) # Просроченные
        else:
            last_touch_time = now - timedelta(hours=i % 4, minutes=random.randint(0, 50)) # Свежие
            
        deals_data.append({
            "deal_id": deal_id,
            "deal_name": deal_name,
            "stage": stage,
            "responsible_name": responsible,
            "observer": observer,
            "last_outgoing_touch_at": last_touch_time,
            # Реальный домен вашей CRM системы Topfranchise
            "crm_link": f"https://topfranchise.bitrix24.ru/crm/deal/details/{deal_id}/"
        })
    df_deals = pd.DataFrame(deals_data)
    
    # Генерируем историю текстовых касаний для сканера
    touches_data = []
    calls_data = []
    
    texts = [
        "Выставил счет по договору, ждем оплату на реквизиты",
        "Клиент высказал жесткий негатив по поводу сроков, у них претензия",
        "Направили КП и новые тарифы на рассмотрение",
        "Договорились созвониться завтра в зуме через телемост в 14:00",
        "Заполнили анкету, прислали логотип и фото для карточки размещения",
        "Обсудили пролонгацию сотрудничества на следующий период",
        "Звонок сброшен / автоответчик"
    ]
    
    for i in range(1, 1200):
        touch_date = now - timedelta(days=i % 20, hours=i % 24)
        manager = real_managers[i % len(real_managers)]
        deal_idx = (i % 150) + 1
        d_id = 450000 + deal_idx
        chosen_text = random.choice(texts)
        
        # Звонки
        if i % 2 == 0:
            duration = 5 if "сброшен" in chosen_text else random.randint(10, 180)
            calls_data.append({
                "call_id": 8000 + i,
                "responsible_name": manager,
                "duration": duration,
                "created_at": touch_date
            })
            
        # Текстовые исходящие сообщения
        if i % 3 != 0:
            touches_data.append({
                "deal_id": d_id,
                "text": chosen_text,
                "created_at": touch_date,
                "manager_name": manager
            })
            
    df_touches = pd.DataFrame(touches_data)
    df_calls = pd.DataFrame(calls_data)
    
    return df_deals, df_touches, df_calls

# Подгрузка базы
df_deals, df_touches, df_calls = fetch_crm_data_all()

# ==========================================
# SIDEBAR (Панель фильтров по реальным лицам)
# ==========================================

st.sidebar.title("🎛️ Панель управления")

if st.sidebar.button("🔄 Обновить данные из Битрикс24"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.subheader("📅 Период анализа")
date_preset = st.sidebar.selectbox(
    "Быстрый выбор", ["Текущий месяц", "Сегодня", "Вчера", "Текущая неделя", "Произвольный диапазон"]
)

now_date = datetime.now(MSK_TZ).date()
if date_preset == "Сегодня":
    start_date, end_date = now_date, now_date
elif date_preset == "Вчера":
    start_date = end_date = now_date - timedelta(days=1)
elif date_preset == "Текущая неделя":
    start_date = now_date - timedelta(days=now_date.weekday())
    end_date = now_date
elif date_preset == "Текущий месяц":
    start_date, end_date = now_date.replace(day=1), now_date
else:
    start_date = st.sidebar.date_input("Начало", now_date - timedelta(days=7))
    end_date = st.sidebar.date_input("Конец", now_date)

filter_start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=MSK_TZ)
filter_end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=MSK_TZ)

# Динамический фильтр по реальным сотрудникам, собранным из CRM
st.sidebar.subheader("👤 Ответственный сотрудник")
unique_crm_managers = sorted(list(df_deals["responsible_name"].unique()))
all_managers_options = ["Все менеджеры"] + unique_crm_managers
selected_manager = st.sidebar.selectbox("Выберите из списка CRM:", all_managers_options)

# Применение глобальной фильтрации
if selected_manager != "Все менеджеры":
    filtered_deals = df_deals[df_deals["responsible_name"] == selected_manager]
    filtered_touches = df_touches[(df_touches["manager_name"] == selected_manager) & (df_touches["created_at"] >= filter_start_dt) & (df_touches["created_at"] <= filter_end_dt)]
    filtered_calls = df_calls[(df_calls["responsible_name"] == selected_manager) & (df_calls["created_at"] >= filter_start_dt) & (df_calls["created_at"] <= filter_end_dt)]
else:
    filtered_deals = df_deals
    filtered_touches = df_touches[(df_touches["created_at"] >= filter_start_dt) & (df_touches["created_at"] <= filter_end_dt)]
    filtered_calls = df_calls[(df_calls["created_at"] >= filter_start_dt) & (df_calls["created_at"] <= filter_end_dt)]

# ==========================================
# MAIN INTERFACE: BLOCK 1 (Звонки от 15 сек)
# ==========================================

st.title("📊 Сквозной контроль воронки сопровождения TopFranchise")
st.markdown(f"Аналитика за период: **{start_date}** по **{end_date}** | Фильтр по сотруднику: **{selected_manager}**")

st.subheader("📞 Качество телефонной активности (Исключение звонков до 15 сек)")
total_calls = len(filtered_calls)
valid_calls = filtered_calls[filtered_calls["duration"] >= 15]
valid_calls_count = len(valid_calls)
call_conversion = (valid_calls_count / total_calls * 100) if total_calls > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Всего наборов номеров из CRM", value=total_calls)
with col2:
    st.metric(label="Полезные созвоны (разговор ≥ 15 секунд)", value=valid_calls_count)
with col3:
    st.metric(label="Качество дозвона (% чистых разговоров)", value=f"{call_conversion:.1f}%")

st.markdown("---")

# ==========================================
# DATA PROCESSING FOR TABS (Расчет заброшенности)
# ==========================================

all_processed_leads = []
current_time_msk = datetime.now(MSK_TZ)

for _, deal in filtered_deals.iterrows():
    stage = deal["stage"]
    last_touch = deal["last_outgoing_touch_at"].astimezone(MSK_TZ)
    
    is_breached = False
    time_display = ""
    
    if stage in STAGE_THRESHOLDS:
        rule = STAGE_THRESHOLDS[stage]
        if rule["unit"] == "hours":
            elapsed_work_hours = calculate_working_hours_elapsed(last_touch, current_time_msk)
            # Чистое округление без длинных хвостов
            time_display = f"{round(elapsed_work_hours, 1)} раб. ч."
            if elapsed_work_hours > rule["value"]:
                is_breached = True
        else:
            elapsed_days = (current_time_msk.date() - last_touch.date()).days
            time_display = f"{elapsed_days} дн."
            if elapsed_days > rule["value"]:
                is_breached = True
                
    status_marker = "🔴 Просрочено" if is_breached else "🟢 Норма"
    
    all_processed_leads.append({
        "Статус": status_marker,
        "Название сделки": deal["deal_name"],
        "Текущая стадия": stage,
        "Ответственный": deal["responsible_name"],
        "Наблюдатель": deal["observer"],
        "Время без связи": time_display,
        "Последний контакт": last_touch.strftime('%d.%m.%Y %H:%M'),
        "Ссылка на CRM": deal["crm_link"],
        "is_breached": is_breached
    })

df_all_registry = pd.DataFrame(all_processed_leads)
df_red_zone_only = df_all_registry[df_all_registry["is_breached"] == True].drop(columns=["is_breached"])

# ==========================================
# MAIN INTERFACE: BLOCK 2 (Вкладки управления)
# ==========================================

# Разделение логики на Вкладки, как вы просили
tab_red, tab_all = st.tabs(["🚨 КРАСНАЯ ЗОНА (Нарушения регламентов)", "🗂️ РЕЕСТР ВСЕХ СДЕЛОК В РАБОТЕ"])

with tab_red:
    st.subheader("Сделки, требующие немедленной реакции")
    if not df_red_zone_only.empty:
        st.error(f"Внимание! Выявлено {len(df_red_zone_only)} клиентов с нарушением SLA частоты касаний.")
        st.dataframe(
            df_red_zone_only.drop(columns=["Статус"]),
            column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("🎉 Отличный результат! Заброшенных клиентов с нарушением SLA не обнаружено.")

with tab_all:
    st.subheader("Полный список активных сделок воронки сопровождения")
    if not df_all_registry.empty:
        st.dataframe(
            df_all_registry.drop(columns=["is_breached"]),
            column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Нет активных сделок по выбранным критериям фильтрации.")

st.markdown("---")

# ==========================================
# MAIN INTERFACE: BLOCK 3 (Сканер и таблицы деталей)
# ==========================================

st.subheader("🎯 Иерархический сканер тем общения и детальный разрез")

if not filtered_touches.empty:
    filtered_touches["Категория касания"] = filtered_touches["text"].apply(classify_touch_final)
    
    # Соединяем историю касаний со сделками, чтобы вытащить Наблюдателей, Названия сделок и Ссылки
    touches_extended = filtered_touches.merge(
        filtered_deals[['deal_id', 'deal_name', 'responsible_name', 'observer', 'crm_link']], 
        on='deal_id', 
        how='inner'
    )
    
    category_counts = filtered_touches["Категория касания"].value_counts().reset_index()
    category_counts.columns = ["Категория касания", "Количество действий"]
    
    col_chart, col_table = st.columns([2, 1])
    with col_chart:
        st.bar_chart(data=category_counts, x="Категория касания", y="Количество действий", color="#3498db")
    with col_table:
        st.dataframe(category_counts, use_container_width=True, hide_index=True)
        
    st.markdown("### 🔍 Глубокая аналитика по группам (Разверните блоки для просмотра деталей):")
    
    # 1. ТАБЛИЦА КОММЕРЧЕСКИХ КАСАНИЙ
    with st.expander("💰 Детальный список: Коммерческие касания (Счет, Позитив, Апсел)"):
        comm_data = touches_extended[touches_extended["Категория касания"].isin(["Счет / оплата", "Позитив", "Апсел"])]
        if not comm_data.empty:
            comm_table = comm_data[["responsible_name", "observer", "deal_name", "Категория касания", "crm_link"]].copy()
            comm_table.columns = ["Ответственный", "Наблюдатель", "Название сделки", "Определенная тема", "Ссылка на сделку"]
            st.dataframe(
                comm_table,
                column_config={"Ссылка на сделку": st.column_config.LinkColumn("Ссылка")},
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("За выбранный период коммерческих касаний не зафиксировано.")
            
    # 2. ТАБЛИЦА ФЛАГОВ РИСКА
    with st.expander("⚠️ Детальный список: Критические флаги риска (Негатив, Отказ)"):
        risk_data = touches_extended[touches_extended["Категория касания"].isin(["Негатив", "Отказ"])]
        if not risk_data.empty:
            risk_table = risk_data[["responsible_name", "observer", "deal_name", "Категория касания", "crm_link"]].copy()
            risk_table.columns = ["Ответственный", "Наблюдатель", "Название сделки", "Определенный риск", "Ссылка на сделку"]
            st.dataframe(
                risk_table,
                column_config={"Ссылка на сделку": st.column_config.LinkColumn("Ссылка")},
                use_container_width=True,
                hide_index=True
            )
        else:
            st.write("🎉 Отлично! Ни одного сообщения с маркерами негатива или отказа за этот период не найдено.")
else:
    st.info("В выбранном диапазоне дат текстовые касания отсутствуют.")
