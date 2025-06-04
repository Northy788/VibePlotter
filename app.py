import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import re
import expression  # import expression.py
from datetime import datetime, timedelta

st.set_page_config(page_title="VibePlotter", layout="wide")
st.title("📊 VibePlotter")

def parse_simple_excel_formula(s):
    if not isinstance(s, str):
        return s
    if not s.startswith('='):
        return s

    # กรณี: =TEXT(unix/86400 + 25569, "...") & "." & number
    pattern_time = r'=TEXT\((\d+)(?:\/86400\s*\+\s*25569)\s*,\s*"([^"]+)"\)\s*&\s*"\."\s*&(\d+)'
    m_time = re.match(pattern_time, s)
    if m_time:
        unix_ts = int(m_time.group(1))
        fmt = m_time.group(2)
        suffix = m_time.group(3)

        # แปลง Excel timestamp เป็น datetime
        dt = datetime.utcfromtimestamp(unix_ts)
        # format string ใน Excel กับ Python ไม่ตรงกัน ต้องแปลง
        fmt = fmt.replace("ddd", "%a").replace("dd", "%d").replace("mmm", "%b").replace("yyyy", "%Y").replace("hh", "%H").replace("mm", "%M").replace("ss", "%S")
        formatted_dt = dt.strftime(fmt)
        return f"{formatted_dt}.{suffix}"

    # กรณี: =num1 & "." & TEXT(num2, "000000")
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

uploaded_files = st.file_uploader("📂 เลือกไฟล์ CSV", type="csv", accept_multiple_files=True)

if uploaded_files:
    with st.spinner("🔄 กำลังโหลดและประมวลผลไฟล์..."):
        dataframes = {}
        column_sets = []

        for file in uploaded_files:
            df = pd.read_csv(file, encoding='utf-8-sig')  # รองรับอักษรไทย
            # แปลงสูตร Excel แบบง่ายในทุก cell ของ df
            df = df.applymap(parse_simple_excel_formula)
            
            name = file.name
            dataframes[name] = df
            column_sets.append(set(df.columns))

        common_columns = sorted(set.intersection(*column_sets))
        if not common_columns:
            st.warning("❗ ไม่มี column ที่เหมือนกันในทุกไฟล์เพื่อใช้เป็นแกน X")
        else:
            st.markdown("### 🔢 เลือกแกน X (ต้องมีในทุกไฟล์) - เลือกได้มากกว่า 1 คอลัมน์")
            x_cols = st.multiselect("เลือกแกน X", common_columns, default=common_columns[0])

            fig = go.Figure()

            for name, df in dataframes.items():
                st.markdown(f"### 📄 การตั้งค่าสำหรับไฟล์: `{name}`")
                
                # แสดงตารางข้อมูลทั้งหมดของไฟล์
                st.markdown("#### ตารางข้อมูลทั้งหมด:")
                with st.expander(f"⚙️ ข้อมูลสถิติ", expanded=False):
                    st.dataframe(df.describe())
                st.dataframe(df)

                y_cols = st.multiselect(f"✅ เลือกคอลัมน์ Y ที่จะแสดง (ไฟล์: {name})", df.columns, key=f"ycol_{name}")

                for col in y_cols:
                    with st.expander(f"⚙️ การตั้งค่าสำหรับ `{col}`", expanded=False):
                        cols = st.columns([3, 3, 1, 2, 2])
                        with cols[0]:
                            preset = st.selectbox("🛠️ เลือก Expression สำเร็จรูป", list(expression.expressions.keys()), key=f"preset_{name}_{col}")
                        with cols[1]:
                            expr = st.text_input(f"✏️ หรือ กรอก Expression เอง (ใช้ 'x' แทนค่าดิบ)", value="x", key=f"expr_{name}_{col}")
                        with cols[2]:
                            scatter = st.checkbox("🔘 จุด scatter", value=True, key=f"scatter_{name}_{col}")
                        with cols[3]:
                            color = st.color_picker("🎨 สีเส้น", value="#0000FF", key=f"color_{name}_{col}")
                        with cols[4]:
                            display_name = st.text_input("📝 ชื่อที่แสดงบนกราฟ", value=f"{name}:{col}", key=f"name_{name}_{col}")

                    if preset != "None":
                        expr_func = expression.expressions[preset]
                    else:
                        expr_func = None

                    for x_col in x_cols:
                        if x_col not in df.columns or col not in df.columns:
                            st.error(f"❌ ไม่พบคอลัมน์ `{x_col}` หรือ `{col}` ในไฟล์ `{name}`")
                            continue
                        try:
                            x = df[x_col]
                            y_raw = df[col]

                            if expr_func:
                                y = expr_func(y_raw)
                            else:
                                y = eval(expr, {"np": __import__("numpy")}, {"x": y_raw})

                        except Exception as e:
                            st.error(f"❌ Expression ผิดพลาดใน `{col}`: {e}")
                            continue

                        trace_name = f"{display_name} (X: {x_col})"
                        fig.add_trace(go.Scattergl(
                            x=x,
                            y=y,
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
                    orientation="h",  # แนวนอน
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig, use_container_width=True)
