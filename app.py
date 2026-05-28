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
            raw_deals.extend(d_resp.get("result", []))
            if "next" in d_resp: start = d_resp["next"]
            else: break

        # 🔥 СВЕРХНАДЕЖНЫЙ ПАРСИНГ НАБЛЮДАТЕЛЕЙ (МНОГОУРОВНЕВЫЙ)
        deal_observers_map = {}
        if raw_deals:
            deal_ids = [d["ID"] for d in raw_deals]
            for i in range(0, len(deal_ids), 50):
                chunk = deal_ids[i:i+50]
                cmd = {f"deal_{d_id}": f"crm.deal.get?id={d_id}" for d_id in chunk}
                
                try:
                    b_resp = requests.post(f"{BITRIX_WEBHOOK}batch", json={"halt": 0, "cmd": cmd}).json()
                    
                    # Сохраняем первый ответ для технического аудита внизу страницы
                    if not debug_sample and b_resp:
                        debug_sample = b_resp
                        
                    b_results = b_resp.get("result", {}).get("result", {})
                    for k, v in b_results.items():
                        d_id_str = k.split("_")[1]
                        
                        # Разворачиваем данные, если они лежат внутри дополнительного ключа 'result'
                        deal_fields = v.get("result") if (isinstance(v, dict) and "result" in v) else v
                        
                        if isinstance(deal_fields, dict):
                            # Ищем массив наблюдателей в любом регистре
                            obs_data = None
                            for key_variant in ["OBSERVERS", "observers", "OBSERVER", "observer"]:
                                if key_variant in deal_fields:
                                    obs_data = deal_fields[key_variant]
                                    break
                            if obs_data:
                                deal_observers_map[int(d_id_str)] = obs_data
                except:
                    pass

        # 4. Загрузка активностей
        raw_acts = []
        start_act = 0
        while True:
            a_resp = requests.post(f"{BITRIX_WEBHOOK}crm.activity.list", json={
                "order": {"ID": "DESC"},
                "filter": {
                    ">=START_TIME": f"{start_date} 00:00:00",
                    "<=START_TIME": f"{end_date} 23:59:59"
                },
                "select": ["ID", "SUBJECT", "START_TIME", "END_TIME", "RESPONSIBLE_ID", "TYPE_ID", "DESCRIPTION", "OWNER_ID", "OWNER_TYPE_ID"],
                "start": start_act
            }).json()
            
            acts = a_resp.get("result", [])
            raw_acts.extend(acts)
            if "next" in a_resp: start_act = a_resp["next"]
            else: break

        # Сборка карты последних типов контактов
        deal_last_act_map = {}
        for a in raw_acts:
            if a.get("OWNER_TYPE_ID") == "2" and a.get("OWNER_ID"):
                d_id_key = int(a["OWNER_ID"])
                if d_id_key not in deal_last_act_map:
                    t_id = str(a.get("TYPE_ID"))
                    deal_last_act_map[d_id_key] = "Телефонный звонок" if t_id == "2" else "Текстовое сообщение"

        # Сборка сделок
        deals_list = []
        for d in raw_deals:
            d_id = str(d["ID"])
            d_id_int = int(d["ID"])
            
            obs_ids = deal_observers_map.get(d_id_int)
            obs_names = []
            if obs_ids:
                if isinstance(obs_ids, dict): id_list = list(obs_ids.values())
                elif isinstance(obs_ids, list): id_list = obs_ids
                else: id_list = [obs_ids]
                
                for o in id_list:
                    if isinstance(o, dict):
                        o_id = str(o.get('USER_ID') or o.get('ID') or o.get('id') or '')
                    else:
                        o_id = str(o).strip()
                    if o_id:
                        obs_names.append(user_map.get(o_id, f"ID {o_id}"))
            
            deals_list.append({
                "deal_id": d_id_int,
                "deal_name": d.get("TITLE", f"Сделка №{d_id}"),
                "stage": stage_map.get(d.get("STAGE_ID"), d.get("STAGE_ID")),
                "responsible_name": user_map.get(str(d.get("ASSIGNED_BY_ID")), f"ID {d.get('ASSIGNED_BY_ID')}"),
                "observer": ", ".join(obs_names) if obs_names else "—",
                "last_outgoing_touch_at": parse_bx_date(d.get("DATE_MODIFY")),
                "crm_link": f"https://topfranchise.bitrix24.ru/crm/deal/details/{d_id}/",
                "last_touch_type": deal_last_act_map.get(d_id_int, "—")
            })

        touches_list = []
        calls_list = []
        for a in raw_acts:
            created_dt = parse_bx_date(a.get("START_TIME"))
            m_name = user_map.get(str(a.get("RESPONSIBLE_ID")), f"ID {a.get('RESPONSIBLE_ID')}")
            d_owner_id = int(a["OWNER_ID"]) if (a.get("OWNER_TYPE_ID") == "2" and a.get("OWNER_ID")) else None
            
            if str(a.get("TYPE_ID")) == "2":  # Звонок
                start_c = parse_bx_date(a.get("START_TIME"))
                end_c = parse_bx_date(a.get("END_TIME"))
                duration = int((end_c - start_c).total_seconds()) if (start_c and end_c) else 0
                calls_list.append({"call_id": a["ID"], "responsible_name": m_name, "duration": duration, "created_at": created_dt, "deal_id": d_owner_id})
            
            desc = a.get("DESCRIPTION") or a.get("SUBJECT") or ""
            if desc:
                touches_list.append({"deal_id": d_owner_id, "text": desc, "created_at": created_dt, "manager_name": m_name, "Категория": classify_touch_final(desc)})

        return pd.DataFrame(deals_list), pd.DataFrame(touches_list), pd.DataFrame(calls_list), debug_sample
    except Exception as e:
        st.error(f"Ошибка работы скрипта: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"error": str(e)}


# ==========================================
# ИНТЕРФЕЙС И ФИЛЬТРЫ
# ==========================================
st.sidebar.title("🎛️ Панель управления")
if st.sidebar.button("🔄 Сбросить кэш и обновить"):
    st.cache_data.clear()
    st.rerun()

today = datetime.now(MSK_TZ).date()
start_date = st.sidebar.date_input("Начальная дата", today - timedelta(days=14))
end_date = st.sidebar.date_input("Конечная дата", today)

df_deals, df_touches, df_calls, debug_payload = load_all_bitrix_data(start_date, end_date)

all_managers = set()
if not df_deals.empty: all_managers.update(df_deals["responsible_name"].unique())
if not df_calls.empty: all_managers.update(df_calls["responsible_name"].unique())
if not df_touches.empty: all_managers.update(df_touches["manager_name"].unique())

if all_managers:
    unique_m = sorted(list(all_managers))
    selected_m = st.sidebar.selectbox("Выберите сотрудника CRM:", ["Все менеджеры"] + unique_m)
else:
    selected_m = "Все менеджеры"

if selected_m != "Все менеджеры":
    if not df_deals.empty: df_deals = df_deals[df_deals["responsible_name"] == selected_m]
    if not df_calls.empty: df_calls = df_calls[df_calls["responsible_name"] == selected_m]
    if not df_touches.empty: df_touches = df_touches[df_touches["manager_name"] == selected_m]


# ==========================================
# СЧЕТЧИКИ ВЕРХНЕГО УРОВНЯ
# ==========================================
st.title("📊 Сквозной контроль воронки сопровождения TopFranchise")

valid_calls_count = len(df_calls[df_calls["duration"] >= 15]) if not df_calls.empty else 0

m1, m2, m3 = st.columns(3)
m1.metric("Всего активных сделок", len(df_deals) if not df_deals.empty else 0)
m2.metric("Успешных звонков (от 15 сек)", valid_calls_count)
m3.metric("Зафиксировано текстовых касаний", len(df_touches) if not df_touches.empty else 0)


# ==========================================
# АНАЛИТИЧЕСКАЯ ОЦЕНКА КАЧЕСТВА РАБОТЫ
# ==========================================
st.markdown("---")
st.subheader("🧠 Аналитическая оценка качества работы")

comm_cats = ["Счет / оплата", "Позитив", "Пролонгация", "Апсел", "Цена", "КП"]
risk_cats = ["Негатив", "Отказ"]

comm_count = len(df_touches[df_touches["Категория"].isin(comm_cats)]) if not df_touches.empty else 0
risk_count = len(df_touches[df_touches["Категория"].isin(risk_cats)]) if not df_touches.empty else 0

col_comm, col_risk = st.columns(2)
with col_comm:
    st.info(f"💰 **Коммерческие касания (Деньги/Удержание): {comm_count}** — показывают высокую вовлеченность в закрытие сделок.")
with col_risk:
    st.warning(f"⚠️ **Флаги риска (Негатив/Отказ): {risk_count}** — требуют личного контроля РОПа.")


# ==========================================
# КОНТРОЛЬ КАЧЕСТВА ТЕЛЕФОННЫХ ЗВОНКОВ
# ==========================================
st.subheader("📞 Контроль качества телефонных звонков")
if not df_calls.empty:
    df_call_stats = df_calls.groupby("responsible_name").agg(
        Всего_звонков=("call_id", "count"),
        Успешных_звонков=("duration", lambda x: int(sum(x >= 15))),
        Средняя_длительность_сек=("duration", lambda x: round(float(x.mean()), 1))
    ).reset_index().rename(columns={"responsible_name": "Менеджер", "Всего_звонков": "Всего звонков", "Успешных_звонков": "Успешных (от 15 сек)", "Средняя_длительность_сек": "Ср. длительность (сек)"})
    st.dataframe(df_call_stats, use_container_width=True, hide_index=True)
else:
    st.info("Нет звонков за выбранный период.")


# ==========================================
# SLA КОНТРОЛЬ И РЕЕСТРЫ
# ==========================================
st.markdown("---")
all_processed = []
current_time = datetime.now(MSK_TZ)

if not df_deals.empty:
    for _, deal in df_deals.iterrows():
        stage = deal["stage"]
        last_touch = deal["last_outgoing_touch_at"]
        is_breached = False
        
        delta = current_time - last_touch
        total_hours = delta.total_seconds() / 3600.0
        total_days = delta.total_seconds() / 86400.0
        
        if total_hours < 24: readable_time = f"{round(total_hours, 1)} раб. ч."
        else: readable_time = f"{round(total_days, 1)} дн."
            
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
            "Тип контакта": deal["last_touch_type"],
            "Время без связи": readable_time,
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
            st.error(f"Внимание! Обнаружено {len(df_red)} заброшенных сделок, требующих реакции РОПа.")
            st.dataframe(df_red, column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")}, use_container_width=True, hide_index=True)
        else:
            st.success("Все сделки ведутся вовремя!")
            
    with tab_all:
        st.dataframe(df_all, column_config={"Ссылка на CRM": st.column_config.LinkColumn("Открыть карточку сделки")}, use_container_width=True, hide_index=True)


# ==========================================
# ХРОНОЛОГИЯ КАСАНИЙ
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


# ==========================================
# 🔧 ТЕХНИЧЕСКИЙ РАЗДЕЛ (ОТЛАДКА)
# ==========================================
st.markdown("---")
with st.expander("🔧 Технический раздел: Отладка ответа Битрикс24 (Наблюдатели)"):
    st.write("Если поле 'Наблюдатель' по-прежнему отображает `—`, разверните структуру ниже, чтобы увидеть, как именно ваш портал отдает данные:")
    if debug_payload:
        st.json(debug_payload)
    else:
        st.info("Данные отладки пусты (возможно, кэш еще не обновлен. Нажмите кнопку 'Сбросить кэш и обновить' в боковой панели).")
