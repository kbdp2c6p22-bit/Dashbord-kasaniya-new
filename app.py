# --- ОБНОВЛЕННАЯ ЛОГИКА КЛАССИФИКАЦИИ И ПРОВАЙДЕРОВ ---

def classify_touch(row):
    """
    Разделяет касания строго на Телфин и Wazzup, 
    а также классифицирует тексты сообщений Wazzup.
    """
    raw_type = str(row['raw_type']).upper()
    text = str(row['text']).lower() if row['text'] else ""
    
    # 1. Проверка на звонок Телфин
    if "TELFIN" in raw_type or "CALL" in raw_type:
        return "Звонок (Телфин)"
    
    # 2. Проверка на сообщение Wazzup
    if "WAZZUP" in raw_type or "SMS" in raw_type:
        # Внутри Wazzup делаем классификацию по тексту сообщения
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

# Пример того, как теперь группируются данные в имитации API:
# touch_data = [
#     {"deal_id": 101, "touch_date": "2026-05-20", "raw_type": "TELFIN_CALL", "text": "Входящий звонок", "manager": "Иванов И.И."},
#     {"deal_id": 101, "touch_date": "2026-05-25", "raw_type": "WAZZUP_MESSAGE", "text": "Высылаю счет", "manager": "Иванов И.И."}
# ]