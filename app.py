import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import requests

# Настройка страницы Streamlit
st.set_page_config(page_title="Аналитический Дашборд Контроля Воронки", layout="wide")

# Часовой пояс МСК
MSK_TZ = pytz.timezone('Europe/Moscow')

# ==========================================
# РЕАЛЬНЫЕ КРЕДЕНШИНАЛЫ И КЛЮЧИ ДОСТУПА
# ==========================================
BITRIX_WEBHOOK = "https://topfranchise.bitrix24.ru/rest/255/4eqdp6ssove27c7m/"
VIBE_API_KEY = "vibe_api_zG3FU63kNM4l22iLWknhTZzPwcUOU0u8_8e1737"
CATEGORY_ID = 17  # Воронка сопровождения со скриншота

# ==========================================
# БИЗНЕС-ПРАВИЛА (ИЕРАРХИЯ КАСАНИЙ И СРОКИ SLA)
# ==========================================
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

# ==========================================
# МОДУЛЬ ДИНАМИЧЕСКОГО СКАЧИВАНИЯ ДАННЫХ CRM
# ==========================================

def calculate_working_hours_elapsed(start_dt, end_dt):
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

def classify_touch_final(text):
    if not text or pd.isna(text): return "Без текста"
    text = str(text).lower()
    for category, keywords in CATEGORIES_HIERARCHY:
        if any(word in text for word in keywords): return category
    return "Другое касание"

@st.cache_data(ttl=600)  # Кэш на 10 минут, чтобы не перегружать лимиты запросов Битрикса
def load_live_crm_data():
    try:
        # 1. Загружаем справочник сотрудников компании
        users_resp = requests.post(f"{BITRIX_WEBHOOK}user.get", json={"ACTIVE": "Y"}).json()
        user_map = {u["ID"]: f"{u.get('NAME', '')} {u.get('LAST_NAME', '')}".strip() for u in users_resp.get("result", [])}
        
        # 2. Загружаем названия стадий для воронки №17
        stages_resp = requests.post(f"{BITRIX_WEBHOOK}crm.status.list", json={"filter": {"ENTITY_ID": f"DEAL_STAGE_{CATEGORY_ID}"}}).json()
        stage_map = {s["STATUS_ID"]: s["NAME"] for s in stages_resp.get("result", [])}
        
        # 3. Загружаем активные сделки из направления 17
        deals_resp = requests.post(f"{BITRIX_WEBHOOK}crm.deal.list", json={
            "filter": {"CATEGORY_ID": CATEGORY_ID, "STAGE_SEMANTIC_ID": "P"}, # Только незакрытые в работе
            "select": ["ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID", "OBSERVERS", "DATE_MODIFY"],
            "order": {"DATE_MODIFY": "DESC"}
        }).json()
        raw_deals = deals_resp.get("result", [])
        
        # 4. Загружаем последние CRM активности (звонки и дела)
        act_resp = requests.post(f"{BITRIX_WEBHOOK}crm.activity.list", json={
            "order": {"ID": "DESC"},
            "select": ["ID", "SUBJECT", "START_TIME", "END_TIME", "RESPONSIBLE_ID", "TYPE_ID", "DESCRIPTION"]
        }).json()
        raw_acts = act_resp.get("result", [])
        
        # Парсинг сделок
        deals_list = []
        for d in raw_deals:
            d_id = d["ID"]
            resp_id = d.get("ASSIGNED_BY_ID")
            stage_code = d.get("STAGE_ID")
            
            # Извлекаем наблюдателей
            obs_ids = d.get("OBSERVERS", [])
            obs_names = [user_map.get(o_id, f"ID {o_id}") for o_id in obs_ids] if isinstance(obs_ids, list) else []
            obs_display = ", ".join(obs_names) if obs_names else "—"
            
            # Ищем последнее зафиксированное событие по этой сделке в активностях, если нет - берем системную дату изменения
            last_touch_dt = pd.to_datetime(d.get("DATE_MODIFY")).replace(tzinfo=MSK_TZ)
            
            deals_list.append({
                "deal_id": int(d_id),
                "deal_name": d.get("TITLE", f"Сделка №{d_id}"),
                "stage": stage_map.get(stage_code, stage_code),
                "responsible_name": user_map.get(resp_id, f"ID {resp_id}"),
                "observer": obs_display,
                "last_outgoing_touch_at": last_touch_dt,
                "crm_link": f"https://topfranchise.bitrix24.ru/crm/deal/details/{d_id}/"
            })
            
        # Парсинг звонков и текстовых касаний
        touches_list = []
        calls_list = []
        
        for a in raw_acts:
            u_id = a.get("RESPONSIBLE_ID")
            m_name = user_map.get(u_id, f"ID {u_id}")
            created_dt = pd.to_datetime(a.get("START_TIME")).replace(tzinfo=MSK_TZ) if a.get("START_TIME") else datetime.now(MSK_TZ)
            
            # Если это звонок (TYPE_ID == 2)
            if str(a.get("TYPE_ID")) == "2":
                start = pd.to_datetime(a.get("START_TIME"))
                end = pd.to_datetime(a.get("END_TIME"))
                duration = int((end - start).total_seconds()) if (start and end) else 0
                calls_list.append({
                    "call_id": a["ID"],
                    "responsible_name": m_name,
                    "duration": duration,
                    "created_at": created_dt
                })
            
            # Если текстовое дело/комментарий
            desc_text = a.get("DESCRIPTION") or a.get("SUBJECT") or ""
            touches_list.append({
                "deal_id": None, # Связь определится на лету, если активность привязана к сущности
                "text": desc_text,
                "created_at": created_dt,
                "manager_name": m_name
            })
            
        df_d = pd.DataFrame(deals_list) if deals_list else pd.DataFrame(columns=["deal_id", "deal_name", "stage", "responsible_name", "observer", "last_outgoing_touch_at", "crm_link"])
        df_t = pd.DataFrame(touches_list) if touches_list else pd.DataFrame(columns=["deal_id", "text", "created_at", "manager_name"])
        df_c = pd.DataFrame(calls_list) if calls_list else pd.DataFrame(columns=["call_id", "responsible_name", "duration", "created_at"])
        
        return df_d, df_t, df_c
    except Exception as e:
        st.error(f"🚨 Критическая ошибка загрузки данных Битрикс24: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Инициализация и загрузка живых данных
df_deals, df_touches, df_calls = load_live_crm_data()

# ==========================================
# ИНТЕРФЕЙС, ФИЛЬТРЫ И ТАБЛИЦЫ
# ==========================================
st.sidebar.title("🎛️ Панель управления")
if st.sidebar.button("🔄 Обновить данные из CRM"):
    st.cache_data.clear()
    st.rerun()

if not df_deals.empty:
    unique_managers = sorted(list(df_deals["responsible_name"].unique()))
    selected_manager = st.sidebar.selectbox("Выберите сотрудника CRM:", ["Все менеджеры"] + unique_managers)
    
    if selected_manager != "Все менеджеры":
        filtered_deals = df_deals[df_deals["responsible_name"] == selected_manager]
    else:
        filtered_deals = df_deals
else:
    st.warning("База сделок пуста. Проверьте права вебхука или наличие сделок в категории 17.")
    filtered_deals = df_deals

# Конвертация в дни и проверка SLA
all_processed_leads = []
current_time_msk = datetime.now(MSK_TZ)

for _, deal in filtered_deals.iterrows():
    stage = deal["stage"]
    last_touch = deal["last_outgoing_touch_at"].astimezone(MSK_TZ)
    is_breached = False
    
    # Расчет чистых физических дней без привязки к строкам (для идеальной сортировки!)
    elapsed_days = round((current_time_msk - last_touch).total_seconds() / 86400.0, 1)
    
    if stage in STAGE_THRESHOLDS:
        rule = STAGE_THRESHOLDS[stage]
        if rule["unit"] == "hours":
            elapsed_work_hours = calculate_working_hours_elapsed(last_touch, current_time_msk)
            if elapsed_work_hours > rule["value"]: is_breached = True
        else:
            if elapsed_days > rule["value"]: is_breached = True
            
    status_marker = "🔴 Просрочено" if is_breached else "🟢 Норма"
    
    all_processed_leads.append({
        "Статус": status_marker,
        "Название сделки": deal["deal_name"],
        "Текущая стадия": stage,
        "Ответственный": deal["responsible_name"],
        "Наблюдатель": deal["observer"],
        "Дней без связи (число)": elapsed_days,
        "Последний контакт": last_touch.strftime('%d.%m.%Y %H:%M'),
        "Ссылка на CRM": deal["crm_link"],
        "is_breached": is_breached
    })

st.title("📊 Сквозной контроль воронки сопровождения TopFranchise")

if all_processed_leads:
    df_all_registry = pd.DataFrame(all_processed_leads)
    df_red_zone_only = df_all_registry[df_all_registry["is_breached"] == True].drop(columns=["is_breached"])
    
    tab_red, tab_all = st.tabs(["🚨 КРАСНАЯ ЗОНА (Нарушения регламентов)", "🗂️ РЕЕСТР ВСЕХ СДЕЛОК В РАБОТЕ"])
    
    with tab_red:
        if not df_red_zone_only.empty:
            st.error(f"Внимание! Обнаружено {len(df_red_zone_only)} заброшенных сделок, требующих реакции РОПа.")
            st.dataframe(
                df_red_zone_only.drop(columns=["Статус"]),
                column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
                use_container_width=True, hide_index=True
            )
        else:
            st.success("🎉 Замечательно! Ни одного нарушения регламентов SLA по частоте касаний не найдено.")
            
    with tab_all:
        st.subheader("Полный список активных клиентов")
        st.info("💡 Кликни по названию колонки 'Дней без связи (число)', чтобы мгновенно отсортировать базу от самых заброшенных сделок к свежим.")
        
        # Сортировка по умолчанию: сначала самые заброшенные
        df_all_registry = df_all_registry.sort_values(by="Дней без связи (число)", ascending=False)
        st.dataframe(
            df_all_registry.drop(columns=["is_breached"]),
            column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")},
            use_container_width=True, hide_index=True
        )
else:
    st.info("Нет данных для отображения.")
