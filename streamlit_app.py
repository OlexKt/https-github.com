import streamlit as st
import base64
import json
import re
from openai import OpenAI
from PIL import Image
import io

# Ініціалізація OpenAI клієнта
def get_ai_client(api_key):
    return OpenAI(api_key=api_key)

# Клас для конвертації формул у Unicode [1, 2, 3]
class UnicodeMath:
    @staticmethod
    def to_unicode(text):
        supers = str.maketrans("0123456789+-=()n", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ")
        subs = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")
        # Перетворення ^2 та _2
        text = re.sub(r'\^(\d|\+|\-|\=|\(|\)|n)', lambda m: m.group(1).translate(supers), text)
        text = re.sub(r'\_(\d|\+|\-|\=|\(|\)|[aeoxhklmnpst])', lambda m: m.group(1).translate(subs), text)
        return text

# Функція для обробки зображень у Base64 [4, 5, 2]
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# Налаштування сторінки Streamlit
st.set_page_config(page_title="AI Перевірка ДЗ", layout="wide")

st.title("🍎 AI асистент вчителя: Перевірка завдань")

# Бокова панель налаштувань
with st.sidebar:
    st.header("⚙️ Налаштування")
    api_key = st.text_input("Введіть OpenAI API Key", type="password")
    system_scale = st.selectbox("Система оцінювання", ["12-бальна (Україна)", "5-бальна"])
    
    st.divider()
    st.info("Цей додаток використовує GPT-4o для аналізу фотографій та PDF-файлів робіт студентів.")

# Основний інтерфейс
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Завантаження матеріалів")
    
    # Завантаження еталона
    ref_file = st.file_uploader("Завантажте зразок (еталон) розв'язання", type=['jpg', 'png', 'pdf'])
    
    # Завантаження робіт студентів (Пакетне завантаження) 
    student_files = st.file_uploader("Завантажте роботи студентів (можна кілька відразу)", 
                                    type=['jpg', 'png', 'pdf'], 
                                    accept_multiple_files=True)
    
    google_doc_link = st.text_input("Або вставте посилання на Google Документ")

    # Кнопки вибору режиму [6, 5]
    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        strict_mode = st.button("📏 Прийняти правила зразка", use_container_width=True)
    with mode_col2:
        flex_mode = st.button("💡 Врахувати зміни у відповіді", use_container_width=True)

with col2:
    st.subheader("2. Результати перевірки")
    
    if (strict_mode or flex_mode) and api_key and ref_file and (student_files or google_doc_link):
        mode = "strict" if strict_mode else "flexible"
        client = get_ai_client(api_key)
        
        # Обробка кожного студента в пакеті 
        for idx, s_file in enumerate(student_files or [google_doc_link]):
            with st.status(f"Перевірка роботи №{idx+1}...", expanded=True) as status:
                try:
                    # Підготовка контенту для ШІ
                    ref_base64 = encode_image(ref_file)
                    
                    prompt = f"""Ви — професійний викладач. 
                    1. ПЕРЕВІРТЕ ЗРАЗОК: якщо в еталоні є помилка, вкажіть на неї в полі 'internal_comment'.
                    2. ПОРІВНЯЙТЕ: перевірте роботу студента відносно еталона.
                    3. ОЦІНІТЬ: за системою {system_scale}.
                    4. РЕЖИМ: {mode} (strict - лише як у зразку, flexible - приймати альтернативні логічні рішення).
                    
                    Результат ТІЛЬКИ у JSON:
                    {{
                        "grade": "бал",
                        "errors": "список помилок",
                        "internal_comment": "аналіз для вчителя (включаючи помилки в еталоні)",
                        "student_comment": "коментар для Classroom (використовуйте ^2 для степенів)"
                    }}"""

                    content = [{"type": "text", "text": prompt}]
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ref_base64}"}})
                    
                    if isinstance(s_file, str): # Посилання
                        content.append({"type": "text", "text": f"Google Doc: {s_file}"})
                    else: # Файл
                        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(s_file)}"}})

                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": content}],
                        response_format={"type": "json_object"}
                    )
                    
                    res = json.loads(response.choices.message.content)
                    
                    # Виведення результату
                    st.success(f"Робота {getattr(s_file, 'name', 'за посиланням')} перевірена!")
                    st.metric("Оцінка", res['grade'])
                    
                    with st.expander("Деталі для викладача"):
                        st.write("**Помилки:**", res['errors'])
                        st.write("**Внутрішній аналіз:**", res['internal_comment'])
                    
                    # Коментар для копіювання з Unicode формулами [1, 2]
                    clean_comment = UnicodeMath.to_unicode(res['student_comment'])
                    st.text_area("Коментар для студента (можна копіювати в Classroom):", 
                                clean_comment, key=f"comment_{idx}")
                    
                    st.divider()
                except Exception as e:
                    st.error(f"Помилка при обробці: {str(e)}")
    elif (strict_mode or flex_mode) and not api_key:
        st.warning("Будь ласка, введіть API Key у боковій панелі.")
