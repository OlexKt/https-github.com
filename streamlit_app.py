import streamlit as st
import google.generativeai as genai
import json
import re

# Клас для конвертації формул у Unicode (для Classroom)
class UnicodeMath:
    @staticmethod
    def to_unicode(text):
        # Мапи для верхніх та нижніх індексів
        supers = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
        subs = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
        # Пошук x^2 та x_2
        text = re.sub(r'\^(\d|\+|\-|\=|\(|\)|n)', lambda m: m.group(1).translate(supers), text)
        text = re.sub(r'\_(\d|\+|\-|\=|\(|\)|[aeoxhklmnpst])', lambda m: m.group(1).translate(subs), text)
        return text

# Конвертація посилань Google Docs у прямий PDF-експорт
def get_pdf_export_url(url):
    if "[docs.google.com/document/d/](https://docs.google.com/document/d/)" in url:
        # Заміна кінцівки /edit... на /export?format=pdf
        base_url = url.split("/edit")
        return f"{base_url}/export?format=pdf"
    return url

# Підготовка файлу для Gemini (PDF або Image)
def prepare_file(uploaded_file):
    if uploaded_file is None:
        return None
    return {
        "mime_type": uploaded_file.type,
        "data": uploaded_file.getvalue()
    }

st.set_page_config(page_title="AI Teacher Assistant", layout="wide")
st.title("♊ Gemini AI: Перевірка завдань (Версія 3.0)")

with st.sidebar:
    st.header("⚙️ Налаштування")
    gemini_key = st.text_input("Введіть Google API Key", type="password", help="Отримайте ключ на aistudio.google.com")
    system_scale = st.selectbox("Система оцінювання", ["12-бальна (Україна)", "5-бальна"])
    model_name = st.selectbox("Модель", ["gemini-1.5-flash", "gemini-1.5-pro"])
    st.info("💡 **Порада:** Для 12-бальної системи краще використовувати **Gemini 1.5 Pro**.")

if gemini_key:
    genai.configure(api_key=gemini_key)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Завантаження матеріалів")
    ref_file = st.file_uploader("Завантажте ЕТАЛОН (зразок)", type=['jpg', 'png', 'jpeg', 'pdf'])
    student_files = st.file_uploader("Завантажте РОБОТИ СТУДЕНТІВ (пакетом)", 
                                    type=['jpg', 'png', 'jpeg', 'pdf'], 
                                    accept_multiple_files=True)
    google_doc = st.text_input("Або вставте посилання на Google Документ")

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        btn_strict = st.button("📏 Суворо за зразком", use_container_width=True)
    with m_col2:
        btn_flex = st.button("💡 Врахувати зміни", use_container_width=True)

with col2:
    st.subheader("2. Результати аналізу")
    
    if (btn_strict or btn_flex) and gemini_key:
        if not ref_file:
            st.warning("Будь ласка, спочатку завантажте зразок розв'язання (еталон)!")
        else:
            mode = "strict" if btn_strict else "flexible"
            model = genai.GenerativeModel(model_name)
            ref_data = prepare_file(ref_file)
            
            # --- ФІКС СИНТАКСИСУ (РЯДКИ 69-75) ---
            works_to_check =
            if student_files:
                works_to_check = student_files
            elif google_doc:
                works_to_check = [google_doc]
            
            if not works_to_check:
                st.info("Додайте хоча б одну роботу студента (файл або посилання).")
            # ------------------------------------

            for idx, s_item in enumerate(works_to_check):
                student_name = getattr(s_item, 'name', 'Google Doc')
                with st.status(f"Аналіз: {student_name}...", expanded=True):
                    try:
                        # Промпт з урахуванням українських рівнів оцінювання
                        prompt = f"""Дій як професійний викладач.
                        1. Перевір еталон (перший файл) на помилки. Якщо вони є, вкажи в 'internal_comment'.
                        2. Порівняй роботу студента (другий файл) з еталоном.
                        3. Оціни за системою {system_scale}. (12-бальна система в Україні має 4 рівні: початковий, середній, достатній, високий).
                        4. Режим: {mode} (strict - карати за відхилення від методу, flexible - приймати альтернативні вірні шляхи).
                        
                        Відповідь надай ВИКЛЮЧНО у форматі JSON:
                        {{
                            "grade": "бал",
                            "errors": "список помилок",
                            "internal_comment": "аналіз для вчителя (в т.ч. помилки в самому еталоні)",
                            "student_comment": "короткий коментар (використовуйте ^2 для степенів та _2 для індексів)"
                        }}"""

                        inputs = [prompt, ref_data]
                        if isinstance(s_item, str): # Це посилання
                            final_url = get_pdf_export_url(s_item)
                            inputs.append(f"Завантаж та проаналізуй цей документ: {final_url}")
                        else: # Це файл
                            inputs.append(prepare_file(s_item))

                        response = model.generate_content(inputs)
                        
                        # Парсинг результату
                        clean_json = re.sub(r'```json|```', '', response.text).strip()
                        res = json.loads(clean_json)
                        
                        st.success(f"Робота {student_name} перевірена!")
                        st.metric("Оцінка", res['grade'])
                        
                        with st.expander("Подробиці для викладача"):
                            st.write("**Помилки:**", res['errors'])
                            st.write("**Технічний аналіз:**", res['internal_comment'])
                        
                        # Unicode-форматування для копіювання
                        comment = UnicodeMath.to_unicode(res['student_comment'])
                        st.text_area("Коментар для Classroom:", comment, key=f"res_area_{idx}")
                        st.divider()
                        
                    except Exception as e:
                        st.error(f"Помилка в роботі {idx+1}: {str(e)}")
    elif (btn_strict or btn_flex) and not gemini_key:
        st.error("Помилка: Не введено Google API Key у боковій панелі!")
