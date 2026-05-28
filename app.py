import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# Часовой пояс МСК
MSK_TZ = pytz.timezone('Europe/Moscow')

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

def calculate_working_hours_elapsed(start_dt, end_dt):
    if start_dt > end_dt: return 0.0
    total_work_hours = 0.0
    current_day = start_dt.date()
    end_day = end_dt.date()
    while current_day <= end_day:
        if current_day.weekday() < 5:
            day_start = datetime.combine(current_day, datetime.min.time()).replace(hour=9, tzinfo=MSK_TZ)
            day_end = datetime.combine(current_day, datetime.min.time()).replace(hour=18, tzinfo=MSK_TZ)
            actual_start = max(start_dt, day_start) if current_day == start_dt.date() else day_start
            actual_end = min(end_dt, day_end) if current_day == end_day.date() else day_end
            if actual_start < actual_end:
                total_work_hours += (actual_end - actual_start).total_seconds() / 3600.0
    return round(total_work_hours, 1)

def classify_touch_final(text):
    if not text or pd.isna(text): return "Без текста"
    text = str(text).lower()
    for category, keywords in CATEGORIES_HIERARCHY:
        if any(word in text for word in keywords): return category
    return "Другое касание"

@st.cache_data(ttl=300)
def load_all_bitrix_data():
    try:
        # 1. Загрузка ВСЕХ пользователей (с пагинацией)
        user_map = {}
        start = 0
        while True:
            u_resp = requests.post(f"{BITRIX_WEBHOOK}user.get", json={"ACTIVE": "Y", "start": start}).json()
            for u in u_resp.get("result", []):
                user_map[str(u["ID"])] = f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip()
            if "next" in u_resp: start = u_resp["next"]
            else: break

        # 2. Справочник стадий
        s_resp = requests.post(f"{BITRIX_WEBHOOK}crm.status.list", json={"filter": {"ENTITY_ID": f"DEAL_STAGE_{CATEGORY_ID}"}}).json()
        stage_map = {s["STATUS_ID"]: s["NAME"] for s in s_resp.get("result", [])}

        # 3. Загрузка ВСЕХ сделок (Выкачиваем абсолютно все страницы Битрикса)
        raw_deals = []
        start = 0
        while True:
            d_resp = requests.post(f"{BITRIX_WEBHOOK}crm.deal.list", json={
                "filter": {"CATEGORY_ID": CATEGORY_ID, "STAGE_SEMANTIC_ID": "P"},
                "select": ["ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID", "OBSERVERS", "DATE_MODIFY"],
                "start": start
            }).json()
            raw_deals.extend(d_resp.get("result", []))
            if "next" in d_resp: start = d_resp["next"]
            else: break

        # 4. Загрузка активностей (последние 300 штук для анализа касаний и звонков)
        raw_acts = []
        for start_act in [0, 50, 100, 150, 200, 250]:
            a_resp = requests.post(f"{BITRIX_WEBHOOK}crm.activity.list", json={
                "order": {"ID": "DESC"},
                "select": ["ID", "SUBJECT", "START_TIME", "END_TIME", "RESPONSIBLE_ID", "TYPE_ID", "DESCRIPTION", "OWNER_ID", "OWNER_TYPE_ID"],
                "start": start_act
            }).json()
            raw_acts.extend(a_resp.get("result", []))

        # Сборка таблиц
        deals_list = []
        for d in raw_deals:
            d_id = str(d["ID"])
            obs_ids = d.get("OBSERVERS", [])
            obs_names = [user_map.get(str(o), f"ID {o}") for o in obs_ids] if isinstance(obs_ids, list) else []
            
            deals_list.append({
                "deal_id": int(d["ID"]),
                "deal_name": d.get("TITLE", f"Сделка №{d_id}"),
                "stage": stage_map.get(d.get("STAGE_ID"), d.get("STAGE_ID")),
                "responsible_name": user_map.get(str(d.get("ASSIGNED_BY_ID")), f"ID {d.get('ASSIGNED_BY_ID')}"),
                "observer": ", ".join(obs_names) if obs_names else "—",
                "last_outgoing_touch_at": pd.to_datetime(d.get("DATE_MODIFY")).replace(tzinfo=pytz.utc).astimezone(MSK_TZ),
                "crm_link": f"https://topfranchise.bitrix24.ru/crm/deal/details/{d_id}/"
            })

        touches_list = []
        calls_list = []
        for a in raw_acts:
            created_dt = pd.to_datetime(a.get("START_TIME")).replace(tzinfo=pytz.utc).astimezone(MSK_TZ) if a.get("START_TIME") else datetime.now(MSK_TZ)
            m_name = user_map.get(str(a.get("RESPONSIBLE_ID")), f"ID {a.get('RESPONSIBLE_ID')}")
            d_owner_id = int(a["OWNER_ID"]) if (a.get("OWNER_TYPE_ID") == "2" and a.get("OWNER_ID")) else None
            
            if str(a.get("TYPE_ID")) == "2":  # Звонок
                start_c = pd.to_datetime(a.get("START_TIME"))
                end_c = pd.to_datetime(a.get("END_TIME"))
                duration = int((end_c - start_c).total_seconds()) if (start_c and end_c) else 0
                calls_list.append({"call_id": a["ID"], "responsible_name": m_name, "duration": duration, "created_at": created_dt, "deal_id": d_owner_id})
            
            desc = a.get("DESCRIPTION") or a.get("SUBJECT") or ""
            if desc:
                touches_list.append({"deal_id": d_owner_id, "text": desc, "created_at": created_dt, "manager_name": m_name, "Категория": classify_touch_final(desc)})

        return pd.DataFrame(deals_list), pd.DataFrame(touches_list), pd.DataFrame(calls_list)
    except Exception as e:
        st.error(f"Ошибка запроса к API: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_deals, df_touches, df_calls = load_all_bitrix_data()

# ==========================================
# ИНТЕРФЕЙС БАР (ФИЛЬТРЫ И ДАТЫ СНОВА ТУТ!)
# ==========================================
st.sidebar.title("🎛️ Панель управления")
if st.sidebar.button("🔄 Сбросить кэш и обновить"):
    st.cache_data.clear()
    st.rerun()

# Фильтр диапазона дат (ВОЗВРАЩЕН)
today = datetime.now(MSK_TZ).date()
start_date = st.sidebar.date_input("Начальная дата", today - timedelta(days=14))
end_date = st.sidebar.date_input("Конечная дата", today)

# Фильтр менеджеров
if not df_deals.empty:
    unique_m = sorted(list(df_deals["responsible_name"].unique()))
    selected_m = st.sidebar.selectbox("Выберите сотрудника:", ["Все менеджеры"] + unique_m)
else:
    selected_m = "Все менеджеры"

# Фильтрация данных на основе дат и менеджеров
if selected_m != "Все менеджеры":
    df_deals = df_deals[df_deals["responsible_name"] == selected_m]
    if not df_calls.empty: df_calls = df_calls[df_calls["responsible_name"] == selected_m]
    if not df_touches.empty: df_touches = df_touches[df_touches["manager_name"] == selected_m]

# Фильтр активностей по датам
if not df_calls.empty:
    df_calls = df_calls[(df_calls["created_at"].dt.date >= start_date) & (df_calls["created_at"].dt.date <= end_date)]
if not df_touches.empty:
    df_touches = df_touches[(df_touches["created_at"].dt.date >= start_date) & (df_touches["created_at"].dt.date <= end_date)]

# ==========================================
# СЧЕТЧИКИ И ВЕРХНИЕ МЕТРИКИ (ВОЗВРАЩЕНЫ!)
# ==========================================
st.title("📊 Сквозной контроль воронки сопровождения TopFranchise")

valid_calls_count = len(df_calls[df_calls["duration"] >= 15]) if not df_calls.empty else 0

m1, m2, m3 = st.columns(3)
m1.metric("Всего активных сделок", len(df_deals))
m2.metric("Успешных звонков (от 15 сек)", valid_calls_count)
m3.metric("Зафиксировано текстовых касаний", len(df_touches))

# Обработка таймингов SLA
all_processed = []
current_time = datetime.now(MSK_TZ)

for _, deal in df_deals.iterrows():
    stage = deal["stage"]
    last_touch = deal["last_outgoing_touch_at"]
    is_breached = False
    
    # Считаем точную разницу в часах и днях
    delta = current_time - last_touch
    total_hours = delta.total_seconds() / 3600.0
    total_days = delta.total_seconds() / 86400.0
    
    # Логика подбора красивого отображения времени
    if total_hours < 24:
        readable_time = f"{round(total_hours, 1)} ч."
    else:
        readable_time = f"{round(total_days, 1)} дн."
        
    # Сортировочный маркер (чистый float дней), чтобы клик по шапке работал идеально
    sort_index = round(total_days, 2)

    if stage in STAGE_THRESHOLDS:
        rule = STAGE_THRESHOLDS[stage]
        if rule["unit"] == "hours":
            elapsed_work_hours = calculate_working_hours_elapsed(last_touch, current_time)
            if elapsed_work_hours > rule["value"]: is_breached = True
        else:
            if total_days > rule["value"]: is_breached = True

    all_processed.append({
        "Статус": "🔴 Просрочено" if is_breached else "🟢 Норма",
        "Название сделки": deal["deal_name"],
        "Текущая стадия": stage,
        "Ответственный": deal["responsible_name"],
        "Наблюдатель": deal["observer"],
        "Без связи": readable_time,
        "sort_days": sort_index,
        "Последний контакт": last_touch.strftime('%d.%m.%Y %H:%M'),
        "Ссылка на CRM": deal["crm_link"],
        "is_breached": is_breached
    })

if all_processed:
    df_res = pd.DataFrame(all_processed)
    df_red = df_res[df_res["is_breached"] == True].sort_values(by="sort_days", ascending=False).drop(columns=["is_breached", "sort_days", "Статус"])
    df_all = df_res.sort_values(by="sort_days", ascending=False).drop(columns=["is_breached", "sort_days"])

    tab_red, tab_all = st.tabs(["🚨 КРАСНАЯ ЗОНА (Нарушения регламентов)", "🗂️ РЕЕСТР ВСЕХ СДЕЛОК В РАБОТЕ"])
    
    with tab_red:
        if not df_red.empty:
            st.error(f"Внимание! Обнаружено {len(df_red)} заброшенных сделок по правилам SLA.")
            st.dataframe(df_red, column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку")}, use_container_width=True, hide_index=True)
        else:
            st.success("Все сделки ведутся вовремя!")
            
    with tab_all:
        st.dataframe(df_all, column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку")}, use_container_width=True, hide_index=True)
else:
    st.info("Нет данных для анализа.")

# ==========================================
# ХРОНОЛОГИЯ КАСАНИЙ ВНИЗУ (ВОЗВРАЩЕНА!)
# ==========================================
st.markdown("---")
st.subheader("📑 Лента последних касаний и дел из CRM")
if not df_touches.empty:
    df_show_touches = df_touches.sort_values(by="created_at", ascending=False).copy()
    df_show_touches["Время"] = df_show_touches["created_at"].dt.strftime('%d.%m.%Y %H:%M')
    st.dataframe(
        df_show_touches[["Время", "manager_name", "Категория", "text"]].rename(columns={"manager_name": "Кто сделал", "text": "Содержание дела"}),
        use_container_width=True, hide_index=True
    )
else:
    st.info("За выбранный диапазон дат в Битриксе не зафиксировано текстовых дел.")
