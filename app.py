import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# ==========================================
# CONSTANTS & CONFIGURATION (Бизнес-правила)
# ==========================================

# Часовой пояс МСК
MSK_TZ = pytz.timezone('Europe/Moscow')

# Финалный упорядоченный список категорий по приоритету (Подход А)
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
    # Оперативные этапы (в часах)
    "Передача аккаунт-менеджеру": {"value": 3, "unit": "hours"},
    "Подготовка к размещению": {"value": 3, "unit": "hours"},
    "Создание и согласование страницы": {"value": 3, "unit": "hours"},
    "Акт по запуску рекламы": {"value": 3, "unit": "hours"},
    "Активация страницы": {"value": 3, "unit": "hours"},
    
    # Долгие и сервисные этапы
    "Размещение": {"value": 21, "unit": "days"},  # 3 недели
    "Апдейт карточки": {"value": 21, "unit": "days"},
    "НФ Размещение": {"value": 21, "unit": "days"},
    "Реализация доп.услуг": {"value": 21, "unit": "days"},
    "Акт запуска доп опций": {"value": 21, "unit": "days"},
    "Отчёт по реализованным услугам": {"value": 21, "unit": "days"},
    "Сверка по сортировкам": {"value": 21, "unit": "days"},
    "Опрос NPS": {"value": 21, "unit": "days"},
    "Подготовка к пролонгации": {"value": 14, "unit": "days"},  # 2 недели
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
    """
    Вычисляет, сколько РАБОЧИХ часов (9:00 - 18:00, Пн-Пт) прошло между двумя датами.
    Используется для точной проверки 3-часового SLA по МСК.
    """
    if start_dt > end_dt:
        return 0.0
        
    # Приводим к МСК на всякий случай
    start_dt = start_dt.astimezone(MSK_TZ)
    end_dt = end_dt.astimezone(MSK_TZ)
    
    total_work_hours = 0.0
    current_day = start_dt.date()
    end_day = end_dt.date()
    
    # Если события произошли в один день
    if current_day == end_day:
        if current_day.weekday() >= 5: # Выходной
            return 0.0
        # Ограничиваем рамками рабочего дня
        day_start = datetime.combine(current_day, datetime.min.time()).replace(hour=9, tzinfo=MSK_TZ)
        day_end = datetime.combine(current_day, datetime.min.time()).replace(hour=18, tzinfo=MSK_TZ)
        
        actual_start = max(start_dt, day_start)
        actual_end = min(end_dt, day_end)
        
        if actual_start < actual_end:
            total_work_hours += (actual_end - actual_start).total_seconds() / 3600.0
        return total_work_hours

    # Если события разбиты на несколько дней (цикл по дням)
    while current_day <= end_day:
        if current_day.weekday() < 5: # Будний день
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
# DATA CACHING & FETCHING (Загрузка данных)
# ==========================================

# Кэшируем загрузку данных на 24 часа (86400 секунд)
@st.cache_data(ttl=86400)
def fetch_crm_data_all():
    """
    ФУНКЦИЯ-ЗАГЛУШКА. Сюда разработчик вставит выгрузку ВСЕХ сделок,
    сообщений и звонков из вашей CRM (без лимита в 50 штук).
    Сейчас она генерирует реалистичные Mock-данные для демонстрации.
    """
    now = datetime.now(MSK_TZ)
    
    # 1. Справочник менеджеров (ФИО вместо Номер 1 / Номер 2)
    managers = {
        101: "Алексей Богатов",
        102: "Мария Смирнова",
        103: "Константин Куратор",
        104: "Ирина Аккаунт"
    }
    
    # 2. Генерируем сделки (Вся база воронки)
    stages = list(STAGE_THRESHOLDS.keys())
    deals_data = []
    
    for i in range(1, 120): # Генерируем 119 активных сделок для проверки объема
        stage = stages[i % len(stages)]
        manager_id = 101 + (i % 4)
        
        # Специально делаем часть сделок "заброшенными" для теста Красной Зоны
        if i % 5 == 0:
            last_touch_time = now - timedelta(days=i % 10, hours=4) # Просроченные
        else:
            last_touch_time = now - timedelta(hours=i % 5) # Свежие
            
        deals_data.append({
            "deal_id": 2000 + i,
            "deal_name": f"Франшиза Клиент #{i}",
            "stage": stage,
            "responsible_id": manager_id,
            "responsible_name": managers[manager_id],
            "observer": "Петр Петров (РОП)" if i % 3 == 0 else "—",
            "last_outgoing_touch_at": last_touch_time,
            "crm_link": f"https://yourcrm.ru/leads/detail/{2000 + i}"
        })
    df_deals = pd.DataFrame(deals_data)
    
    # 3. Генерируем звонки и сообщения (касания) за последние 30 дней
    touches_data = []
    calls_data = []
    
    for i in range(1, 1000):
        touch_date = now - timedelta(days=i % 30, hours=i % 24)
        is_outgoing = (i % 3 != 0) # 66% исходящих, 33% входящих от клиентов
        
        # Тексты для проверки классификатора
        texts = [
            "Выставил счет по договору, ждем оплату на реквизиты",
            "Клиент высказал негатив по поводу сроков, у них претензия",
            "Направили КП и новые тарифы на рассмотрение",
            "Договорились созвониться завтра в зуме через телемост в 14:00",
            "Заполнили анкету, прислали логотип и фото для карточки",
            "Обсудили пролонгацию сотрудничества на следующий период",
            "Звонок сброшен / автоответчик"
        ]
        chosen_text = texts[i % len(texts)]
        
        # Если это звонок
        if i % 2 == 0:
            duration = 5 if "сброшен" in chosen_text else (20 + (i % 120)) # длительность звонка
            calls_data.append({
                "call_id": 9000 + i,
                "responsible_name": managers[101 + (i % 4)],
                "duration": duration,
                "created_at": touch_date
            })
            
        # Касания для текстового анализа (учитываем только ИСХОДЯЩИЕ менеджера)
        if is_outgoing:
            touches_data.append({
                "deal_id": 2000 + (i % 119 + 1),
                "text": chosen_text,
                "created_at": touch_date,
                "manager_name": managers[101 + (i % 4)]
            })
            
    df_touches = pd.DataFrame(touches_data)
    df_calls = pd.DataFrame(calls_data)
    
    return df_deals, df_touches, df_calls

# Вызов функции кэширования
df_deals, df_touches, df_calls = fetch_crm_data_all()

# ==========================================
# SIDEBAR (Панель управления и фильтры)
# ==========================================

st.sidebar.title("🎛️ Фильтры управления")

# Кнопка принудительного обновления данных (сброс кэша)
if st.sidebar.button("🔄 Обновить данные из CRM"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# 1. Настройка диапазона дат (Умный Date Picker с пресетами)
st.sidebar.subheader("📅 Выбор периода анализа")
date_preset = st.sidebar.selectbox(
    "Быстрый выбор периода", 
    ["Сегодня", "Вчера", "Текущая неделя", "Текущий месяц", "Произвольный диапазон"]
)

now_date = datetime.now(MSK_TZ).date()

if date_preset == "Сегодня":
    start_date = now_date
    end_date = now_date
elif date_preset == "Вчера":
    start_date = now_date - timedelta(days=1)
    end_date = now_date - timedelta(days=1)
elif date_preset == "Текущая неделя":
    start_date = now_date - timedelta(days=now_date.weekday())
    end_date = now_date
elif date_preset == "Текущий месяц":
    start_date = now_date.replace(day=1)
    end_date = now_date
else:
    start_date = st.sidebar.date_input("Начало периода", now_date - timedelta(days=7))
    st.sidebar.caption("По умолчанию показаны последние 7 дней")
    end_date = st.sidebar.date_input("Конец периода", now_date)

# Переводим даты фильтра в формат datetime с временной зоной МСК для сравнения
filter_start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=MSK_TZ)
filter_end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=MSK_TZ)

# 2. Фильтр по конкретным менеджерам (Реальные ФИО)
st.sidebar.subheader("👤 Ответственный менеджер")
all_managers = ["Все менеджеры"] + list(df_deals["responsible_name"].unique())
selected_manager = st.sidebar.selectbox("Выберите сотрудника", all_managers)

# Применение глобальных фильтров к данным
if selected_manager != "Все менеджеры":
    filtered_deals = df_deals[df_deals["responsible_name"] == selected_manager]
    filtered_touches = df_touches[(df_touches["manager_name"] == selected_manager) & (df_touches["created_at"] >= filter_start_dt) & (df_touches["created_at"] <= filter_end_dt)]
    filtered_calls = df_calls[(df_calls["responsible_name"] == selected_manager) & (df_calls["created_at"] >= filter_start_dt) & (df_calls["created_at"] <= filter_end_dt)]
else:
    filtered_deals = df_deals
    filtered_touches = df_touches[(df_touches["created_at"] >= filter_start_dt) & (df_touches["created_at"] <= filter_end_dt)]
    filtered_calls = df_calls[(df_calls["created_at"] >= filter_start_dt) & (df_calls["created_at"] <= filter_end_dt)]


# ==========================================
# MAIN INTERFACE: BLOCK 1 (Метрики звонков)
# ==========================================

st.title("📊 Сквозная Аналитика Касаний и Воронки Продаж")
st.markdown(f"Показаны данные за период: **{start_date}** по **{end_date}** | Менеджер: **{selected_manager}**")

st.subheader("📞 Контроль и качество телефонных звонков (Пункт 3)")

total_calls_count = len(filtered_calls)
# Фильтр мусорных звонков: строго от 15 секунд
valid_calls = filtered_calls[filtered_calls["duration"] >= 15]
valid_calls_count = len(valid_calls)
# Конверсия полезного дозвона
call_conversion = (valid_calls_count / total_calls_count * 100) if total_calls_count > 0 else 0.0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Всего набранных номеров / звонков", value=total_calls_count)
with col2:
    st.metric(label="Целевые созвоны (от 15 секунд)", value=valid_calls_count, delta=f"{valid_calls_count} разговоров")
with col3:
    st.metric(label="Качество базы (Процент дозвона %)", value=f"{call_conversion:.1f}%")

st.markdown("---")

# ==========================================
# MAIN INTERFACE: BLOCK 2 (Красная Зона)
# ==========================================

st.subheader("🚨 КРАСНАЯ ЗОНА: Клиенты без исходящих касаний (Пункт 1 и 2)")
st.caption("Расчёт просрочки ведется с учетом стадий воронки и рабочих часов МСК (9:00 - 18:00, Пн-Пт) для оперативных этапов.")

red_zone_leads = []
current_time_msk = datetime.now(MSK_TZ)

for _, deal in filtered_deals.iterrows():
    stage = deal["stage"]
    last_touch = deal["last_outgoing_touch_at"].astimezone(MSK_TZ)
    
    if stage in STAGE_THRESHOLDS:
        rule = STAGE_THRESHOLDS[stage]
        is_breached = False
        time_display = ""
        
        if rule["unit"] == "hours":
            # Вычисляем пройденные РАБОЧИЕ часы
            elapsed_work_hours = calculate_working_hours_elapsed(last_touch, current_time_msk)
            if elapsed_work_hours > rule["value"]:
                is_breached = True
                time_display = f"{elapsed_work_hours} раб. ч. (Лимит {rule['value']}ч)"
        else:
            # Для долгосрочных этапов считаем календарные дни
            elapsed_days = (current_time_msk.date() - last_touch.date()).days
            if elapsed_days > rule["value"]:
                is_breached = True
                time_display = f"{elapsed_days} дн. (Лимит {rule['value']}дн)"
                
        if is_breached:
            # Ищем последнее сообщение/действие по этой сделке для вывода контекста
            deal_touches = df_touches[df_touches["deal_id"] == deal["deal_id"]]
            last_touch_text = "Нет зафиксированных касаний"
            if not deal_touches.empty:
                last_touch_text = deal_touches.sort_values(by="created_at", ascending=False).iloc[0]["text"]
            
            last_touch_category = classify_touch_final(last_touch_text)
            
            red_zone_leads.append({
                "Название сделки": deal["deal_name"],
                "Текущая стадия": stage,
                "Ответственный": deal["responsible_name"],
                "Наблюдатель": deal["observer"],
                "Без связи": time_display,
                "Последний тип контакта": last_touch_category,
                "Ссылка на CRM": deal["crm_link"]
            })

if red_zone_leads:
    df_red_zone = pd.DataFrame(red_zone_leads)
    
    # Визуальное выделение таблицы с помощью кастомных стилей Streamlit
    st.error(f"Внимание! Обнаружено {len(df_red_zone)} заброшенных клиентов, требующих немедленной реакции.")
    st.dataframe(
        df_red_zone,
        column_config={
            "Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")
        },
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("🎉 Отлично! Все менеджеры соблюдают регламенты частоты касаний. Заброшенных клиентов нет.")

st.markdown("---")

# ==========================================
# MAIN INTERFACE: BLOCK 3 (Аналитика текстов касаний)
# ==========================================

st.subheader("🎯 Направления и классификация тем общения (Пункт 5)")

if not filtered_touches.empty:
    # Применяем финальный классификатор Подхода А к текстам
    filtered_touches["Категория касания"] = filtered_touches["text"].apply(classify_touch_final)
    
    # Считаем распределение категорий
    category_counts = filtered_touches["Категория касания"].value_counts().reset_index()
    category_counts.columns = ["Категория касания", "Количество действий"]
    
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        st.write("📈 Общий объем коммуникаций по бизнес-категориям")
        # Стандартный горизонтальный график Streamlit
        st.bar_chart(data=category_counts, x="Категория касания", y="Количество действий", color="#2980b9")
        
    with col_table:
        st.write("📋 Детальный разрез")
        st.dataframe(category_counts, use_container_width=True, hide_index=True)
        
    # Блок Матрицы Эффективности (Аналитическое предложение №4)
    st.markdown("#### 🧠 Аналитическая оценка качества работы")
    
    critical_touches = category_counts[category_counts["Категория касания"].isin(["Негатив", "Отказ"])]
    money_touches = category_counts[category_counts["Категория касания"].isin(["Счет / оплата", "Позитив", "Апсел"])]
    
    c_col1, c_col2 = st.columns(2)
    with c_col1:
        sum_money = money_touches["Количество действий"].sum() if not money_touches.empty else 0
        st.info(f"💰 **Коммерческие касания (Деньги/Удержание): {sum_money}** — показывают высокую вовлеченность в закрытие сделок.")
    with c_col2:
        sum_crit = critical_touches["Количество действий"].sum() if not critical_touches.empty else 0
        if sum_crit > 0:
            st.warning(f"⚠️ **Флаги риска (Негатив/Отказ): {sum_crit}** — требуют личного контроля РОПа.")
        else:
            st.success("👌 Риски минимальны: за выбранный период критических маркеров отказа не обнаружено.")
else:
    st.info("За выбранный диапазон дат у менеджера не зафиксировано текстовых сообщений или заметок в CRM.")
