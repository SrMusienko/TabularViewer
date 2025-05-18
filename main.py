import streamlit as st
import pandas as pd
import pyreadstat
import os
import re
from tkinter import Tk, filedialog

st.set_page_config(page_title="📑 Tabular Viewer", layout="wide")
def select_directory():
    root = Tk()
    root.withdraw()  # Скрыть основное окно
    root.attributes('-topmost', True)  # Окно поверх других
    folder_path = filedialog.askdirectory(title="Виберіть каталог з даними")
    root.destroy()
    return folder_path

DEFAULT_DIR = "data"
st.sidebar.header("🔧 Налаштування")
custom_dir = st.sidebar.text_input("Шлях до каталогу з даними:", value=DEFAULT_DIR)
DATA_DIR = custom_dir.strip()
if st.sidebar.button("📁 Виберіть каталог"):
    selected_dir = select_directory()
    if selected_dir:
        DATA_DIR = selected_dir
        st.sidebar.success(f"Вибрано каталог: {DATA_DIR}")
    else:
        DATA_DIR = "data"
else:
    DATA_DIR = "data"  # Значение по умолчанию

st.title("📑 Tabular Viewer")

if not os.path.exists(DATA_DIR):
    st.error(f"Папка '{DATA_DIR}' не знайдена. Створи папку і додай файли туди.")
    st.stop()

files = [f for f in os.listdir(DATA_DIR) if not f.startswith('.') and os.path.isfile(os.path.join(DATA_DIR, f))]

if not files:
    st.warning(f"Немає доступних файлів для перегляду у папці {DATA_DIR}/")
    st.stop()

selected = st.sidebar.selectbox("Оберіть таблицю для перегляду:", sorted(files))


@st.cache_data
def load_data_with_meta(file):
    ext = os.path.splitext(file)[1].lower()
    path = os.path.join(DATA_DIR, file)
    try:
        if ext == ".sas7bdat":
            df, meta = pyreadstat.read_sas7bdat(path)
            return df, meta
        elif ext == ".xpt":
            df, meta = pyreadstat.read_xport(path)
            return df, meta
        elif ext == ".csv":
            return pd.read_csv(path), None
        elif ext == ".xlsx":
            return pd.read_excel(path), None
        else:
            return None, None
    except Exception as e:
        st.error(f"Помилка при завантаженні файлу {file}: {e}")
        return None, None
@st.cache_data
def parse_sdtm_metadata(path):
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        parsed = []
        for line in lines:
            parts = line.strip().split("$")
            if len(parts) >= 5:
                parsed.append({
                    "Dataset": parts[2],
                    "Variable": parts[3],
                    "Label": parts[4],
                    "Type": parts[5] if len(parts) > 5 else ""
                })
        return pd.DataFrame(parsed)
    except Exception as e:
        return None
    
@st.cache_data
def load_all_metadata():
    metadata_files = [f for f in os.listdir(DATA_DIR) if f.endswith(('.csv', '.xlsx')) and not f.startswith('.')]
    specs = {}
    for file in metadata_files:
        path = os.path.join(DATA_DIR, file)
        try:
            if file == "SDTM_spec_Variables.csv":
                df = parse_sdtm_metadata(path)
            elif file.endswith(".csv"):
                df = pd.read_csv(path)
            elif file.endswith(".xlsx"):
                df = pd.read_excel(path)
            else:
                continue
            if df is not None and any(col.lower() in df.columns.str.lower().tolist() for col in ["variable", "label"]):
                specs[file] = df
        except: continue
    return specs

@st.cache_data
def find_matching_metadata(data_filename, df, specs):
    base_name = os.path.splitext(data_filename)[0].lower()
    candidates = []
    for spec_name, spec_df in specs.items():
        cols = spec_df.columns.str.lower()
        if any("variable" in col for col in cols):
            candidates.append((spec_name, spec_df))

    for name, df_spec in candidates:
        if re.search(base_name, name.lower()):
            return df_spec

    for name, df_spec in candidates:
        cols = df_spec.columns.str.lower()
        if "dataset" in cols:
            if df_spec["Dataset"].astype(str).str.lower().str.contains(base_name).any():
                return df_spec[df_spec["Dataset"].str.lower() == base_name]

    for name, df_spec in candidates:
        if "Variable" in df_spec.columns:
            common = set(df_spec["Variable"]).intersection(df.columns)
            if len(common) / len(df.columns) > 0.3:
                return df_spec

    return None

@st.cache_data
def describe_column(col, metadata_df, _meta):
    # Попытка найти описание из внешней таблицы спецификации
    if metadata_df is not None and "Variable" in metadata_df.columns:
        row = metadata_df[metadata_df["Variable"] == col]
        if not row.empty:
            return row.iloc[0].to_dict()

    # Если есть pyreadstat.meta — извлекаем оттуда
    desc = {}
    if _meta:
        if hasattr(_meta, "column_names_to_labels"):
            desc["Label"] = _meta.column_names_to_labels.get(col, "")
        if hasattr(_meta, "readstat_variable_types"):
            desc["Type"] = _meta.readstat_variable_types.get(col, "")
        if hasattr(_meta, "variable_storage_width"):
            desc["Length"] = _meta.variable_storage_width.get(col, "")
        # Проверка на возможное поле format в будущем (его пока нет в pyreadstat)
        if hasattr(_meta, "formats"):
            desc["Format"] = _meta.formats.get(col, "")
    return desc if desc else None



df, meta = load_data_with_meta(selected)
all_specs = load_all_metadata()
matched_metadata = find_matching_metadata(selected, df, all_specs) if df is not None else None




tab1, tab2 = st.tabs(["📋 Метаданi","📄 Данi"])

with tab2:
    st.dataframe(df, use_container_width=True)
    st.markdown(f"**Кількість рядків:** {len(df)} | **Кількість колонок:** {len(df.columns)}")

with tab1:
    if meta:
        meta_rows = []
        for idx, col in enumerate(meta.column_names):
            desc = describe_column(col, matched_metadata, _meta=meta) or {}
            meta_rows.append({
                "№": idx + 1,
                "Variable": col,
                "Label": desc.get("Label", ""),
                "Type": desc.get("Type", ""),
                "Length": desc.get("Length", ""),
                "Format": desc.get("Format", "")
            })
        meta_df = pd.DataFrame(meta_rows)
        st.dataframe(meta_df, use_container_width=True)
    else:
        st.info("Метадані SAS не знайдені.")