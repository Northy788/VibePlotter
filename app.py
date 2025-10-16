import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import re
import expression  # import expression.py
from datetime import datetime, timedelta
from multiprocessing import Pool, cpu_count
import io
import numexpr as ne

st.set_page_config(page_title="VibePlotter", layout="wide")
st.title("📊 VibePlotter")

def parse_simple_excel_formula(s):
    if not isinstance(s, str):
        return s
    if not s.startswith('='):
        return s

    pattern_time = r'=TEXT\((\d+)(?:\/86400\s*\+\s*25569)\s*,\s*"([^"]+)"\)\s*&\s*"\."\s*&(\d+)'
    m_time = re.match(pattern_time, s)
    if m_time:
        unix_ts = int(m_time.group(1))
        fmt = m_time.group(2)
        suffix = m_time.group(3)
        dt = datetime.utcfromtimestamp(unix_ts)
        fmt = fmt.replace("ddd", "%a").replace("dd", "%d").replace("mmm", "%b").replace("yyyy", "%Y").replace("hh", "%H").replace("mm", "%M").replace("ss", "%S")
        formatted_dt = dt.strftime(fmt)
        return f"{formatted_dt}.{suffix}"

    pattern_concat = r'=(\d+)&"\."&TEXT\((\d+),"0+"\)'
    m = re.match(pattern_concat, s)
    if m:
        num1 = m.group(1)
        num2 = m.group(2)
        zero_format = re.search(r'"(0+)"', s)
        width = len(zero_format.group(1)) if zero_format else len(num2)
        num2_formatted = num2.zfill(width)
        return f"{num1}.{num2_formatted}"
    return s

def process_file(file):
    file_content = file.getvalue()
    df = pd.read_csv(io.BytesIO(file_content), encoding='utf-8-sig')
    df = df.applymap(parse_simple_excel_formula)
    name = file.name
    return name, df, set(df.columns)


uploaded_files = st.file_uploader("📂 เลือกไฟล์ CSV", type="csv", accept_multiple_files=True)

if uploaded_files:
    with st.spinner("🔄 กำลังโหลดและประมวลผลไฟล์..."):
        with Pool(processes=cpu_count()) as pool:
            results = pool.map(process_file, uploaded_files)

        dataframes = {name: df for name, df, _ in results}
        column_sets = [cols for _, _, cols in results]

        common_columns = sorted(set.intersection(*column_sets)) if column_sets else []

    if not common_columns:
        st.warning("❗ ไม่มี column ที่เหมือนกันในทุกไฟล์เพื่อใช้เป็นแกน X")
    else:
        st.markdown("### 🔢 เลือกแกน X (ต้องมีในทุกไฟล์) - เลือกได้มากกว่า 1 คอลัมน์")
        x_cols = st.multiselect("เลือกแกน X", common_columns, default=[common_columns[0]])

        fig = go.Figure()

        for name, df in dataframes.items():
            st.markdown(f"### 📄 การตั้งค่าสำหรับไฟล์: `{name}`")
            
            # <<< ส่วนที่แสดงตารางข้อมูลและสถิติถูกลบออกไปแล้ว
            
            y_cols = st.multiselect(f"✅ เลือกคอลัมน์ Y ที่จะแสดง (ไฟล์: {name})", list(df.columns), key=f"ycol_{name}")

            for col in y_cols:
                with st.expander(f"⚙️ การตั้งค่าสำหรับ `{col}`", expanded=False):
                    cols = st.columns([3, 3, 1, 2, 2])
                    with cols[0]:
                        preset = st.selectbox("🛠️ เลือก Expression สำเร็จรูป", list(expression.expressions.keys()), key=f"preset_{name}_{col}")
                    with cols[1]:
                        expr_text = st.text_input(f"✏️ หรือ กรอก Expression เอง (ใช้ 'x' แทนค่าดิบ)", value="x", key=f"expr_{name}_{col}")
                    with cols[2]:
                        scatter = st.checkbox("🔘 จุด scatter", value=True, key=f"scatter_{name}_{col}")
                    with cols[3]:
                        color = st.color_picker("🎨 สีเส้น", value="#0000FF", key=f"color_{name}_{col}")
                    with cols[4]:
                        display_name = st.text_input("📝 ชื่อที่แสดงบนกราฟ", value=f"{name}:{col}", key=f"name_{name}_{col}")

                for x_col in x_cols:
                    if x_col not in df.columns or col not in df.columns:
                        st.error(f"❌ ไม่พบคอลัมน์ `{x_col}` หรือ `{col}` ในไฟล์ `{name}`")
                        continue
                    try:
                        x_data = df[x_col]
                        y_raw = df[col]

                        if preset != "None":
                            expr_func = expression.expressions[preset]
                            y_data = expr_func(y_raw)
                        else:
                            local_dict = {'x': y_raw, 'np': __import__("numpy")}
                            y_data = ne.evaluate(expr_text, local_dict=local_dict)

                    except Exception as e:
                        st.error(f"❌ Expression ผิดพลาดใน `{col}`: {e}")
                        continue

                    trace_name = f"{display_name} (X: {x_col})"
                    fig.add_trace(go.Scattergl(
                        x=x_data,
                        y=y_data,
                        mode="lines+markers" if scatter else "lines",
                        name=trace_name,
                        line=dict(color=color),
                        marker=dict(size=6) if scatter else None,
                        hovertemplate="<b>X:</b> %{x:.6f}<br><b>Y:</b> %{y:.6f}<extra></extra>"
                    ))

        fig.update_layout(
            title="📈 กราฟข้อมูลจากไฟล์ CSV",
            xaxis_title="แกน X ที่เลือก",
            yaxis_title="ค่าที่แสดงผล",
            height=700,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            )
        )
        st.plotly_chart(fig, use_container_width=True)