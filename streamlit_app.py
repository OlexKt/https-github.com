import streamlit as st
import google.generativeai as genai
import json
import re

# Клас для конвертації формул у Unicode (для Classroom) [1, 2]
class UnicodeMath:
    @staticmethod
    def to_unicode(text):
        supers = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
        subs = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
        text = re.sub(r'\^(\d|\+|\-|\=|\(|\)|n)', lambda m: m.group(1).translate(supers), text)
        text = re.sub(r'\_(\d|\+|\-|\=|\(|\)|[aeoxhklmnpst])', lambda m: m.group(1).translate(subs), text)
        return text

# Функція для підготовки файлу (зображення або PDF) для Gemini 
def prepare_file(uploaded_file):
    if uploaded_file is None:
        return None
    mime_type = uploaded_file.type
    return {
        "mime_type": mime_type,
        "data": uploaded_file.getvalue()
    }

st.set_page_config(page_title="Gemini Teacher Assistant", layout="wide")
st.title("♊ Gemini AI: Перевірка завдань (PDF + Фото)")

with st.sidebar:
    st.header("⚙️ Налаштування")
    gemini_key = st.text_input("Введіть Google API Key", type="password")
    system_scale = st.selectbox("Система оцінювання", ["12-бальна (Україна)", "5-бальна"])
    model_name = st.selectbox("Модель", ["gemini-1.5-flash", "gemini-1.5-pro"])
    st.info("💡 **Порада:** Для складних формул краще використовувати **Gemini 1.5 Pro**.")

if gemini_key:
    genai.configure(api_key=gemini_key)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Завантаження")
    ref_file = st.file_uploader("Завантажте ЕТАЛОН (PDF або фото)", type=['jpg', 'png', 'jpeg', 'pdf'])
    student_files = st.file_uploader("Завантажте РОБОТИ СТУДЕНТІВ (пакетом)", 
                                    type=['jpg', 'png', 'jpeg', 'pdf'], 
                                    accept_multiple_files=True)
    google_doc = st.text_input("Або посилання на Google Doc")

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        btn_strict = st.button("📏 Суворо за зразком", use_container_width=True)
    with m_col2:
        btn_flex = st.button("💡 Врахувати зміни", use_container_width=True)

with col2:
    st.subheader("2. Результати")
    
    if (btn_strict or btn_flex) and gemini_key:
        if not ref_file:
            st.warning("Будь ласка, додайте еталон!")
        else:
            mode = "strict" if btn_strict else "flexible"
            model = genai.GenerativeModel(model_name)
            
            # Готуємо еталон один раз
            ref_data = prepare_file(ref_file)
            
            # Якщо завантажено файли, перевіряємо їх. Якщо ні - пробуємо посилання.
            works_to_check = student_files if student_files else ([google_doc] if google_doc else)
            
            for idx, s_item in enumerate(works_to_check):
                with st.status(f"Перевірка: {getattr(s_item, 'name', 'Google Doc')}...", expanded=True):
                    try:
                        prompt = f"""Дій як професійний викладач. 
                        1. Перевір еталон (перший файл) на наявність помилок.
                        2. Порівняй роботу студента (другий файл або посилання) з еталоном.
                        3. Оціни за системою {system_scale}.
                        4. Режим: {mode} (strict - карати за відхилення, flexible - приймати інші логічно вірні шляхи).
                        
                        Відповідь надай ВИКЛЮЧНО у форматі JSON:
                        {{
                            "grade": "бал",
                            "errors": "список помилок студента",
                            "internal_comment": "аналіз для вчителя (в т.ч. якщо є помилки в еталоні)",
                            "student_comment": "короткий коментар (використовуйте ^2 для степенів та _2 для індексів)"
                        }}"""

                        inputs = [prompt, ref_data]
                        
                        if isinstance(s_item, str): # Це посилання
                            inputs.append(f"Google Doc Link: {s_item}")
                        else: # Це завантажений файл
                            inputs.append(prepare_file(s_item))

                        # Запит до Gemini
                        response = model.generate_content(inputs)
                        
                        # Очищення та парсинг JSON
                        clean_json = re.sub(r'```json|```', '', response.text).strip()
                        res = json.loads(clean_json)
                        
                        # Виведення результатів
                        st.success(f"Перевірено: {getattr(s_item, 'name', 'Google Doc')}")
                        st.metric("Оцінка", res['grade'])
                        
                        with st.expander("Технічні деталі"):
                            st.write("**Помилки:**", res['errors'])
                            st.write("**Аналіз:**", res['internal_comment'])
                        
                        # Форматування коментаря для Classroom
                        classroom_text = UnicodeMath.to_unicode(res['student_comment'])
                        st.text_area("Скопіюйте коментар для студента:", classroom_text, key=f"res_{idx}")
                        st.divider()
                        
                    except Exception as e:
                        st.error(f"Помилка при перевірці '{getattr(s_item, 'name', 'посилання')}': {str(e)}")
    elif (btn_strict or btn_flex) and not gemini_key:
        st.error("Введіть Google API Key!")
