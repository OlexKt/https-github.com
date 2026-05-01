import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import json
import re

# Клас для конвертації формул у Unicode [1, 2]
class UnicodeMath:
    @staticmethod
    def to_unicode(text):
        supers = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
        subs = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
        text = re.sub(r'\^(\d|\+|\-|\=|\(|\)|n)', lambda m: m.group(1).translate(supers), text)
        text = re.sub(r'\_(\d|\+|\-|\=|\(|\)|[aeoxhklmnpst])', lambda m: m.group(1).translate(subs), text)
        return text

# Налаштування інтерфейсу
st.set_page_config(page_title="Gemini Teacher Assistant", layout="wide")
st.title("♊ Gemini AI: Перевірка домашніх завдань")

with st.sidebar:
    st.header("⚙️ Налаштування")
    gemini_key = st.text_input("Введіть Google API Key", type="password")
    system_scale = st.selectbox("Система оцінювання", ["12-бальна (Україна)", "5-бальна"])
    model_name = st.selectbox("Модель", ["gemini-1.5-flash", "gemini-1.5-pro"])
    st.info("Flash — швидша та економна. Pro — розумніша для складних задач.")

if gemini_key:
    genai.configure(api_key=gemini_key)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Матеріали")
    ref_file = st.file_uploader("Завантажте ЕТАЛОН (зразок)", type=['jpg', 'png', 'jpeg', 'pdf'])
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
    st.subheader("2. Результати аналізу")
    
    if (btn_strict or btn_flex) and gemini_key:
        if not ref_file:
            st.warning("Додайте зразок розв'язання!")
        else:
            mode = "strict" if btn_strict else "flexible"
            model = genai.GenerativeModel(model_name)
            
            # Підготовка еталона
            ref_img = Image.open(ref_file)
            
            for idx, s_file in enumerate(student_files or [google_doc]):
                with st.status(f"Аналіз роботи №{idx+1}...", expanded=True):
                    try:
                        # Промпт для Gemini
                        prompt = f"""Дій як професійний викладач. 
                        1. Перевір еталон (перше зображення) на помилки. Якщо вони є, вкажи в 'internal_comment'.
                        2. Порівняй роботу студента (друге зображення або посилання) з еталоном.
                        3. Оціни за системою {system_scale}.
                        4. Режим: {mode} (strict - карати за відхилення від методу, flexible - приймати інші вірні шляхи).
                        
                        Відповідь надай ВИКЛЮЧНО у форматі JSON:
                        {{
                            "grade": "бал",
                            "errors": "список помилок",
                            "internal_comment": "аналіз для вчителя",
                            "student_comment": "короткий коментар (використовуйте ^2 для степенів та _2 для індексів)"
                        }}"""

                        # Формування запиту залежно від типу вводу
                        inputs = [prompt, ref_img]
                        if isinstance(s_file, str):
                            inputs.append(f"Google Doc Link: {s_file}")
                        else:
                            inputs.append(Image.open(s_file))

                        response = model.generate_content(inputs)
                        
                        # Очищення тексту від можливих маркерів ```json
                        clean_json = re.sub(r'```json|```', '', response.text).strip()
                        res = json.loads(clean_json)
                        
                        # Відображення
                        st.success(f"Готово: {getattr(s_file, 'name', 'Google Doc')}")
                        st.metric("Оцінка", res['grade'])
                        
                        with st.expander("Для викладача (помилки та аналіз)"):
                            st.write(f"**Помилки:** {res['errors']}")
                            st.write(f"**Аналіз:** {res['internal_comment']}")
                        
                        # Коментар з Unicode формулами [3]
                        final_comment = UnicodeMath.to_unicode(res['student_comment'])
                        st.text_area("Коментар для Classroom:", final_comment, key=f"res_{idx}")
                        st.divider()
                        
                    except Exception as e:
                        st.error(f"Помилка: {str(e)}")
    elif (btn_strict or btn_flex) and not gemini_key:
        st.error("Будь ласка, введіть API Key у боковій панелі.")
