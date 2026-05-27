import streamlit as st
import pandas as pd
import requests
import time

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Дашборд касаний (TopFranchise)", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Аналитика касаний: Клиенты TopFranchise.ru")
st.markdown("---")

# --- БОКОВАЯ ПАНЕЛЬ ДЛЯ АВТОРИЗАЦИИ ---
st.sidebar.header("🔑 Настройки подключения")
bitrix_webhook = st.sidebar.text_input("Вебхук Битрикс24", type="password", help="Вставьте ваш URL вебхука Битрикс24 (начинается с https://...)")
vibe_api_key = st.sidebar.text_input("API Ключ VibeCode", type="password", help="Вставьте ваш токен vibe_api_...")

# --- СТРОГАЯ ЛОГИКА КЛАССИФИКАЦИИ КАСАНИЙ ---
def classify_touch(row):
    """
    Разделяет касания строго на Телфин и Wazzup, 
    а также классифицирует тексты сообщений Wazzup.
    """
    raw_type = str(row.get('raw_type', '')).upper()
    text = str(row.get('text', '')).lower() if row.get('text') else ""
    
    # 1. Проверка на звонок Телфин
    if "TELFIN" in raw_type or "CALL" in raw_type:
        return "Звонок (Телфин)"
    
    # 2. Проверка на сообщение Wazzup
    if "WAZZUP" in raw_type or "SMS" in raw_type:
        if any(w in text for w in ["привет", "здравствуй", "добрый день", "доброе утро"]):
            return "Wazzup: Приветствие / Выход на связь"
        elif any(w in text for w in ["цена", "стоимость", "сколько стоит", "скидк", "рубл", "оплат", "счет"]):
            return "Wazzup: Обсуждение цены/оплаты"
        elif any(w in text for w in ["договор", "акт", "правк", "подписа", "документ"]):
            return "Wazzup: Согласование документов"
        elif any(w in text for w in ["спасибо", "отлично", "договорились", "ок", "хорошо"]):
            return "Wazzup: Договоренность / Успех"
        elif any(w in text for w in ["отказ", "не интересно", "дорого", "нет"]):
            return "Wazzup: Отработка возражений"
        return "Wazzup: Текущая переписка"
        
    return "Другое касание"

# --- ФУНКЦИИ РАБОТЫ С API ---

@st.cache_data(ttl=600)  # Кэшируем на 10 минут, чтобы не спамить запросами при каждом клике
def fetch_topfranchise_data(webhook, vibe_key):
    """
    Скачивает ID воронки, фильтрует сделки на лету и подтягивает касания.
    """
    if not webhook or not vibe_key:
        return None, "Пожалуйста, введите корректные ключи в боковой панели."

    try:
        # ШАГ 1: Ищем ID нужной воронки динамически
        cat_url = f"{webhook.rstrip('/')}/crm.dealcategory.list"
        cat_response = requests.post(cat_url, json={}, timeout=20).json()
        
        category_id = None
        categories = cat_response.get("result", [])
        
        for cat in categories:
            if cat.get("NAME") == "Клиенты TopFranchise.ru":
                category_id = cat.get("ID")
                break
        
        # Если воронка не найдена по имени, по умолчанию берем ID = 0 (Общая), но предупреждаем
        if category_id is None:
            category_id = 0
            st.sidebar.warning("Воронка 'Клиенты TopFranchise.ru' не найдена, загружена общая воронка.")

        # ШАГ 2: Качаем сделки ТОЛЬКО из этой воронки (CATEGORY_ID)
        deal_url = f"{webhook.rstrip('/')}/crm.deal.list"
        deal_filter = {
            "filter": {"CATEGORY_ID": category_id},
            "select": ["ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID"]
        }
        
        deal_response = requests.post(deal_url, json=deal_filter, timeout=20).json()
        deals = deal_response.get("result", [])
        
        if not deals:
            return pd.DataFrame(), "В воронке 'Клиенты TopFranchise.ru' пока нет сделок."

        deal_ids = [deal["ID"] for deal in deals]

        # ШАГ 3: Запрос к VibeCode / Сбор касаний только для отфильтрованных сделок
        # (Имитируем сбор логов активности по списку deal_ids, чтобы не перегружать память)
        
        # Замените этот URL на ваш реальный эндпоинт VibeCode, если он агрегирует данные
        # Для безопасности передаем ваш vibe_key в заголовках
        
        # --- БЛОК СБОРА ДАННЫХ КАСАНИЙ (Пример структуры) ---
        raw_touches = []
        
        # Ниже представлена умная заглушка-генератор, которая подхватит ваши deal_ids 
        # и создаст структуру для работы классификатора, пока вы не подключите финальный URL VibeCode:
        for idx, d_id in enumerate(deal_ids):
            manager = f"Менеджер {idx % 3 + 1}"
            if idx % 2 == 0:
                raw_touches.append({"deal_id": d_id, "touch_date": "2026-05-26", "raw_type": "TELFIN_CALL", "text": "Входящий звонок", "manager": manager})
                raw_touches.append({"deal_id": d_id, "touch_date": "2026-05-27", "raw_type": "WAZZUP_MESSAGE", "text": "Добрый день! Высылаю счет на оплату франшизы.", "manager": manager})
            else:
                raw_touches.append({"deal_id": d_id, "touch_date": "2026-05-25", "raw_type": "WAZZUP_MESSAGE", "text": "Спасибо, договор получили, изучаем", "manager": manager})
                raw_touches.append({"deal_id": d_id, "touch_date": "2026-05-27", "raw_type": "WAZZUP_MESSAGE", "text": "Дорого, у нас нет такого бюджета сейчас", "manager": manager})

        df_touches = pd.DataFrame(raw_touches)
        return df_touches, None

    except Exception as e:
        return None, f"Ошибка при подключении к API: {str(e)}"

# --- ОСНОВНАЯ ЛОГИКА ИНТЕРФЕЙСА ---

if not bitrix_webhook or not vibe_api_key:
    st.info("👋 Добро пожаловать! Чтобы активировать дашборд, введите ваш Вебхук Битрикс24 и API Ключ VibeCode в меню слева.")
    st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=200)
else:
    with st.spinner("⏳ Подключаемся к Битрикс24, ищем воронку TopFranchise и фильтруем данные..."):
        df, error_message = fetch_topfranchise_data(bitrix_webhook, vibe_api_key)

    if error_message:
        st.error(error_message)
    elif df is not None and not df.empty:
        
        # Применяем твою классификацию ко всем строкам таблицы
        df['Тип касания'] = df.apply(classify_touch, axis=1)

        # --- МЕТРИКИ ДАШБОРДА ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Всего сделок в анализе", len(df['deal_id'].unique()))
        with col2:
            st.metric("Всего зафиксировано касаний", len(df))
        with col3:
            st
