import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ================= 1. 数据库初始化 =================
def init_db():
    conn = sqlite3.connect('gym_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (name TEXT, course TEXT, total_times INTEGER, remaining_times INTEGER,
                  PRIMARY KEY (name, course))''')
    c.execute('''CREATE TABLE IF NOT EXISTS checkin_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, name TEXT, course TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, name TEXT, course TEXT, times INTEGER, cost REAL)''')
    
    c.execute("SELECT COUNT(*) FROM students")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO students VALUES ('lwt', '短棍', 24, 9)")
        c.execute("INSERT INTO students VALUES ('lwt', '拳击', 50, 38)")
        
        purchases = [
            ('2026-07-11', 'lwt', '短棍', 24, 2388.0),
            ('2026-08-23', 'lwt', '拳击', 50, 5999.0)
        ]
        c.executemany("INSERT INTO purchase_logs (date, name, course, times, cost) VALUES (?, ?, ?, ?, ?)", purchases)
        
        checkins = [
            ('2026-07-12', 'lwt', '短棍'), ('2026-07-18', 'lwt', '短棍'), ('2026-07-19', 'lwt', '短棍'),
            ('2026-07-25', 'lwt', '短棍'), ('2026-08-08', 'lwt', '短棍'), ('2026-08-15', 'lwt', '短棍'),
            ('2026-08-22', 'lwt', '短棍'), ('2026-08-25', 'lwt', '短棍'), ('2026-09-05', 'lwt', '短棍'),
            ('2026-09-10', 'lwt', '短棍'), ('2026-09-12', 'lwt', '短棍'), ('2026-09-29', 'lwt', '短棍'),
            ('2026-10-08', 'lwt', '短棍'), ('2026-10-15', 'lwt', '短棍'), ('2026-10-20', 'lwt', '短棍'),
            ('2026-08-23', 'lwt', '拳击'), ('2026-08-29', 'lwt', '拳击'), ('2026-09-06', 'lwt', '拳击'),
            ('2026-09-13', 'lwt', '拳击'), ('2026-09-15', 'lwt', '拳击'), ('2026-09-27', 'lwt', '拳击'),
            ('2026-10-03', 'lwt', '拳击'), ('2026-10-11', 'lwt', '拳击'), ('2026-10-18', 'lwt', '拳击'),
            ('2026-10-23', 'lwt', '拳击'), ('2026-10-25', 'lwt', '拳击'), ('2026-10-30', 'lwt', '拳击')
        ]
        c.executemany("INSERT INTO checkin_logs (date, name, course) VALUES (?, ?, ?)", checkins)
        conn.commit()
    conn.close()

init_db()

# 核心工具函数：重算剩余次数
def recalculate_remaining_times():
    conn = sqlite3.connect('gym_data.db')
    c = conn.cursor()
    c.execute("SELECT name, course, total_times FROM students")
    records = c.fetchall()
    
    for name, course, total_times in records:
        c.execute("SELECT COUNT(*) FROM checkin_logs WHERE name=? AND course=?", (name, course))
        checked_in = c.fetchone()[0]
        new_remain = total_times - checked_in
        c.execute("UPDATE students SET remaining_times=? WHERE name=? AND course=?", (new_remain, name, course))
    conn.commit()
    conn.close()

recalculate_remaining_times()

# ================= 2. 页面设置 =================
st.set_page_config(page_title="打卡系统", layout="wide")
st.title("🥊 课程管理系统")

conn = sqlite3.connect('gym_data.db')
c = conn.cursor()
c.execute("SELECT DISTINCT name FROM students")
existing_names = [row[0] for row in c.fetchall()]
c.execute("SELECT DISTINCT course FROM students")
existing_courses = [row[0] for row in c.fetchall()]
conn.close()

tab1, tab2, tab3 = st.tabs(["📅 日常打卡", "📝 课程录入与记录", "🔍 打卡记录管理"])

# ================= Tab 1: 日常打卡 & 统计分析 =================
with tab1:
    st.subheader("今日打卡")
    
    if not existing_names:
        st.info("目前没有学员记录，请先到【课程录入与记录】页面添加！")
    else:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            c_name = st.selectbox("选择学员姓名", existing_names, index=None, placeholder="请选择学员...")
        with col2:
            c_course = st.selectbox("选择打卡课程", existing_courses, index=None, placeholder="请选择课程...")
        with col3:
            st.write("")
            st.write("")
            if st.button("✅ 确认打卡", use_container_width=True, type="primary"):
                if c_name and c_course:
                    conn = sqlite3.connect('gym_data.db')
                    c = conn.cursor()
                    c.execute("SELECT remaining_times FROM students WHERE name=? AND course=?", (c_name, c_course))
                    res = c.fetchone()
                    
                    if res and res[0] > 0:
                        checkin_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        c.execute("INSERT INTO checkin_logs (date, name, course) VALUES (?, ?, ?)", 
                                  (checkin_time, c_name, c_course))
                        conn.commit()
                        recalculate_remaining_times()
                        conn.close()
                        st.success(f"打卡成功！")
                        st.rerun() 
                    else:
                        st.error(f"打卡失败！该课程次数已耗尽，请先续课。")
                        conn.close()
                else:
                    st.warning("请先选择学员和课程！")

    st.divider()
    st.subheader("📊 学员数据与进度统计")
    
    conn = sqlite3.connect('gym_data.db')
    query = """
    SELECT 
        s.name AS 姓名, 
        s.course AS 课程, 
        s.total_times AS 总次数, 
        s.remaining_times AS 剩余次数,
        IFNULL(p.total_cost, 0) AS 总费用,
        IFNULL(ck.checkin_count, 0) AS 已打卡次数
    FROM students s
    LEFT JOIN (SELECT name, course, SUM(cost) as total_cost FROM purchase_logs GROUP BY name, course) p 
        ON s.name = p.name AND s.course = p.course
    LEFT JOIN (SELECT name, course, COUNT(*) as checkin_count FROM checkin_logs GROUP BY name, course) ck 
        ON s.name = ck.name AND s.course = ck.course
    """
    df_stats = pd.read_sql_query(query, conn)
    conn.close()

    # 计算百分比（0-100之间）
    df_stats['课程进度'] = df_stats['已打卡次数'] / df_stats['总次数']
    df_stats['课程进度'] = (df_stats['课程进度'] * 100).clip(upper=100.0) 
    df_stats['课程进度'] = df_stats['课程进度'].fillna(0) 

    df_display = df_stats[['姓名', '课程', '总次数', '剩余次数', '总费用', '课程进度']]
    
    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "总费用": st.column_config.NumberColumn(format="¥%.2f"),
            "课程进度": st.column_config.ProgressColumn(
                "课程进度", 
                format="%.1f%%", 
                min_value=0, 
                max_value=100,
            )
        }
    )

# ================= Tab 2: 课程录入 =================
with tab2:
    st.subheader("📝 新增购课 / 续课")
    with st.form("purchase_form", clear_on_submit=True):
        col_date, col_name, col_course = st.columns(3)
        with col_date:
            p_date = st.date_input("购课日期", datetime.now())
        with col_name:
            p_name = st.selectbox("学员姓名", options=existing_names, accept_new_options=True, placeholder="选择或新建...")
        with col_course:
            p_course = st.selectbox("课程类型", options=existing_courses, accept_new_options=True, placeholder="选择或新建...")
            
        col_times, col_cost = st.columns(2)
        with col_times:
            p_times = st.number_input("增加次数", min_value=1, step=1)
        with col_cost:
            p_cost = st.number_input("费用 (元)", min_value=0.0, step=100.0)
            
        submit_purchase = st.form_submit_button("确认录入", type="primary")
        
        if submit_purchase:
            if p_name and p_course:
                p_name = p_name.strip()
                p_course = p_course.strip()
                conn = sqlite3.connect('gym_data.db')
                c = conn.cursor()
                c.execute("INSERT INTO purchase_logs (date, name, course, times, cost) VALUES (?, ?, ?, ?, ?)", 
                          (str(p_date), p_name, p_course, p_times, p_cost))
                
                c.execute("SELECT * FROM students WHERE name=? AND course=?", (p_name, p_course))
                res = c.fetchone()
                if res:
                    new_total = res[2] + p_times
                    c.execute("UPDATE students SET total_times=? WHERE name=? AND course=?", (new_total, p_name, p_course))
                else:
                    c.execute("INSERT INTO students (name, course, total_times, remaining_times) VALUES (?, ?, ?, ?)", (p_name, p_course, p_times, p_times))
                
                conn.commit()
                recalculate_remaining_times()
                conn.close()
                st.success(f"已成功为 {p_name} 录入【{p_course}】{p_times} 次，费用 {p_cost} 元！")
                st.rerun()
            else:
                st.warning("姓名和课程类型不能为空！")

    st.divider()
    st.subheader("📜 历史录入记录")
    conn = sqlite3.connect('gym_data.db')
    df_purchase = pd.read_sql_query("SELECT date AS 日期, name AS 姓名, course AS 课程, times AS 增加次数, cost AS 费用 FROM purchase_logs ORDER BY id DESC LIMIT 50", conn)
    st.dataframe(df_purchase, use_container_width=True, hide_index=True)
    conn.close()

# ================= Tab 3: 打卡记录管理 =================
with tab3:
    st.subheader("🔍 历史打卡记录管理")
    
    conn = sqlite3.connect('gym_data.db')
    df_checkins = pd.read_sql_query("SELECT id, date AS 日期, name AS 姓名, course AS 课程 FROM checkin_logs ORDER BY date DESC", conn)
    conn.close()
    
    if df_checkins.empty:
        st.info("目前没有任何打卡记录。")
    else:
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = False
            
        if not st.session_state.edit_mode:
            st.markdown("💡 **提示：** 当前为只读状态。若要修改日期或删除记录，请点击下方按钮。")
            st.dataframe(
                df_checkins.drop(columns=['id']), 
                use_container_width=True, 
                hide_index=True
            )
            if st.button("✏️ 点击开启修改模式", type="primary"):
                st.session_state.edit_mode = True
                st.rerun()
        else:
            st.markdown("💡 **提示：** 请在下方表格中直接修改日期，或选中行首点击 🗑️ 删除。")
            edited_df = st.data_editor(
                df_checkins,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic", 
                column_config={
                    "id": None,
                    "日期": st.column_config.TextColumn("日期 (可修改)", required=True)
                }
            )
            
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("💾 保存修改", type="primary", use_container_width=True):
                    conn = sqlite3.connect('gym_data.db')
                    c = conn.cursor()
                    
                    original_ids = set(df_checkins['id'])
                    new_ids = set(edited_df['id'].dropna().astype(int))
                    deleted_ids = original_ids - new_ids
                    
                    if deleted_ids:
                        for d_id in deleted_ids:
                            c.execute("DELETE FROM checkin_logs WHERE id=?", (d_id,))
                    
                    valid_edited = edited_df.dropna(subset=['id'])
                    for index, row in valid_edited.iterrows():
                        if int(row['id']) in original_ids:
                            c.execute("UPDATE checkin_logs SET date=? WHERE id=?", (row['日期'], int(row['id'])))
                    
                    conn.commit()
                    recalculate_remaining_times()
                    conn.close()
                    
                    st.session_state.edit_mode = False
                    st.success("记录已保存，剩余次数已自动同步！")
                    st.rerun()
                    
            with col_cancel:
                if st.button("❌ 取消修改", use_container_width=True):
                    st.session_state.edit_mode = False
                    st.rerun()