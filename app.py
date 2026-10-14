# -*- coding: utf-8 -*-
import os
import sqlite3
import datetime
import io
import base64
import json
import urllib.request
import urllib.error
import pandas as pd
import streamlit as st

# ==========================================
# 1. 页面基础配置与内置种子数据
# ==========================================
st.set_page_config(
    page_title="腰封出入库与发货核算管理系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_FILE = "waist_seal_wms.db"

DEFAULT_SKU_SPECS = [
    {"工厂": "和光", "材质": "胡桃木", "形状": "圆形", "规格": '16"', "腰封规格": None, "SKU": "MASTHTMRD16"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "圆形", "规格": '18"', "腰封规格": None, "SKU": "MASTHTMRD18"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "圆形", "规格": '20"', "腰封规格": None, "SKU": "MASTHTMRD20"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "圆形", "规格": '22"', "腰封规格": None, "SKU": "MASTHTMRD22"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "圆形", "规格": '24"', "腰封规格": None, "SKU": "MASTHTMRD24"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '14"', "腰封规格": None, "SKU": "MASTHTMRT2014"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTHTMRT2218"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTHTMRT2818"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTHTMRT3218"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTHTMRT3218-MH"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '12"', "腰封规格": "[784x150mm]", "SKU": "MASTHTMRT3612"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '12"', "腰封规格": "[784x150mm]", "SKU": "MASTHTMRT3612-MH"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '20"', "腰封规格": "[1194x150mm]", "SKU": "MASTHTMRT4020"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '22"', "腰封规格": "[1294x150mm]", "SKU": "MASTHTMS22"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '22"', "腰封规格": "[1294x150mm]", "SKU": "MASTHTMS22-MH"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "方形", "规格": '24"', "腰封规格": "[1394x150mm]", "SKU": "MASTHTMS24"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "矩形", "规格": '24"', "腰封规格": "[1394x150mm]", "SKU": "MASTHTMS24-MH"},
    {"工厂": "和光", "材质": "胡桃木", "形状": "方形", "规格": '30"', "腰封规格": None, "SKU": "MASTHTMS30"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTXSMRT2218"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "矩形", "规格": '18"', "腰封规格": "[1088x150mm]", "SKU": "MASTXSMRT3218"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "矩形", "规格": '12"', "腰封规格": "[784x150mm]", "SKU": "MASTXSMRT3612"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "矩形", "规格": '20"', "腰封规格": "[1194x150mm]", "SKU": "MASTXSMRT4020"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "方形", "规格": '22"', "腰封规格": "[1294x150mm]", "SKU": "MASTXSMS22"},
    {"工厂": "颖泰", "材质": "相思木", "形状": "方形", "规格": '24"', "腰封规格": "[1394x150mm]", "SKU": "MASTXSMS24"},
]

# ==========================================
# 2. GitHub 云端自动同步持久化模块（防休眠丢数据）
# ==========================================
def get_github_config():
    """读取 Streamlit Secrets 中的 GitHub 配置"""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        branch = st.secrets.get("GITHUB_BRANCH", "main")
        if token and repo:
            return {"token": str(token).strip(), "repo": str(repo).strip(), "branch": str(branch).strip()}
    except Exception:
        pass
    return None

def pull_db_from_github():
    """容器唤醒启动时，自动从 GitHub 拉取最新的 waist_seal_wms.db 文件"""
    cfg = get_github_config()
    if not cfg:
        return False
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{DB_FILE}?ref={cfg['branch']}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {cfg['token']}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Streamlit-WMS-App"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "content" in data:
                db_bytes = base64.b64decode(data["content"])
                with open(DB_FILE, "wb") as f:
                    f.write(db_bytes)
                return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
    except Exception:
        pass
    return False

def push_db_to_github(commit_msg="Update database from Streamlit"):
    """每次数据变动后，自动将最新的 waist_seal_wms.db 推送保存到 GitHub"""
    cfg = get_github_config()
    if not cfg or not os.path.exists(DB_FILE):
        return False, "未配置 GitHub 自动同步"
    
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{DB_FILE}"
    headers = {
        "Authorization": f"token {cfg['token']}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Streamlit-WMS-App"
    }
    
    sha = None
    try:
        get_req = urllib.request.Request(f"{url}?ref={cfg['branch']}", headers=headers)
        with urllib.request.urlopen(get_req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            sha = res_data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            return False, f"查询远端失败: {e}"
    except Exception as e:
        return False, f"网络异常: {e}"
        
    try:
        with open(DB_FILE, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")
            
        payload = {
            "message": f"[skip ci] {commit_msg} ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            "content": content_b64,
            "branch": cfg["branch"]
        }
        if sha:
            payload["sha"] = sha
            
        put_req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(put_req, timeout=15) as resp:
            return True, "已同步至 GitHub 云端"
    except Exception as e:
        return False, f"云端同步失败: {e}"


# ==========================================
# 3. SQLite 数据库底层逻辑与自动升级
# ==========================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def save_and_sync(conn, action_desc="更新数据"):
    """统一提交事务并触发 GitHub 云端同步"""
    conn.commit()
    conn.close()
    ok, msg = push_db_to_github(action_desc)
    if get_github_config() and not ok:
        st.toast(f"⚠️ 本地已保存，但{msg}", icon="⚠️")
    elif ok:
        st.toast("✅ 数据已永久同步至 GitHub 云端", icon="☁️")

def init_db():
    # 容器首次启动时先尝试从 GitHub 拉取最新数据库
    if "db_pulled" not in st.session_state:
        pull_db_from_github()
        st.session_state["db_pulled"] = True
        
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sku_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factory TEXT NOT NULL,
        material TEXT,
        shape TEXT,
        dimension TEXT,
        waist_spec TEXT,
        sku TEXT UNIQUE NOT NULL
    )
    ''')
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        factory TEXT NOT NULL,
        waist_spec TEXT NOT NULL,
        stock INTEGER DEFAULT 0,
        pre_ship_qty INTEGER DEFAULT 0,
        safety_stock INTEGER DEFAULT 100,
        updated_at TEXT,
        PRIMARY KEY (factory, waist_spec)
    )
    ''')
    
    cur.execute('PRAGMA table_info(inventory)')
    existing_cols = [r[1] for r in cur.fetchall()]
    if 'pre_ship_qty' not in existing_cols:
        try:
            cur.execute('ALTER TABLE inventory ADD COLUMN pre_ship_qty INTEGER DEFAULT 0')
            conn.commit()
        except Exception:
            pass
    
    cur.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        trans_type TEXT NOT NULL,
        factory TEXT NOT NULL,
        waist_spec TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        before_stock INTEGER NOT NULL,
        after_stock INTEGER NOT NULL,
        batch_no TEXT,
        sku_details TEXT,
        operator TEXT,
        remark TEXT
    )
    ''')
    
    cur.execute('SELECT COUNT(*) FROM sku_mapping')
    if cur.fetchone()[0] == 0:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in DEFAULT_SKU_SPECS:
            cur.execute('''
            INSERT INTO sku_mapping (factory, material, shape, dimension, waist_spec, sku)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (item["工厂"], item["材质"], item["形状"], item["规格"], item["腰封规格"], item["SKU"]))
            
            if item["腰封规格"]:
                cur.execute('''
                INSERT OR IGNORE INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at)
                VALUES (?, ?, 0, 0, 100, ?)
                ''', (item["工厂"], item["腰封规格"], now_str))
        conn.commit()
        conn.close()
        push_db_to_github("Initialize seed database")
    else:
        conn.commit()
        conn.close()

init_db()

def get_inventory_df():
    conn = get_db_connection()
    query = '''
    SELECT 
        i.factory AS 工厂, 
        i.waist_spec AS 腰封规格, 
        i.stock AS 在库库存, 
        COALESCE(i.pre_ship_qty, 0) AS 预发货数量,
        (i.stock - COALESCE(i.pre_ship_qty, 0)) AS 可用库存,
        i.safety_stock AS 安全库存预警值,
        COALESCE(GROUP_CONCAT(s.sku, ', '), '无关联SKU') AS 适配产品SKU,
        i.updated_at AS 最近更新时间
    FROM inventory i
    LEFT JOIN sku_mapping s ON i.factory = s.factory AND i.waist_spec = s.waist_spec
    GROUP BY i.factory, i.waist_spec
    ORDER BY i.factory, i.waist_spec
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        def calc_status(row):
            avail = row['可用库存']
            safety = row['安全库存预警值']
            if avail < 0:
                return f"🔴 预发超额缺货 (缺{-avail}件)"
            elif avail <= 0:
                return "🔴 无可用库存"
            elif avail <= safety:
                return "🟡 安全预警 (可用紧缺)"
            else:
                return "🟢 充足"
                
        df['库存状态'] = df.apply(calc_status, axis=1)
        df['建议采购补货量'] = df.apply(lambda r: max(0, r['安全库存预警值'] - r['可用库存']), axis=1)
        
    return df

def get_sku_mapping_df():
    conn = get_db_connection()
    df = pd.read_sql_query('''
    SELECT factory AS 工厂, material AS 材质, shape AS 形状, dimension AS 规格, waist_spec AS 腰封规格, sku AS SKU
    FROM sku_mapping
    ORDER BY factory, sku
    ''', conn)
    conn.close()
    return df

def get_transactions_df():
    conn = get_db_connection()
    df = pd.read_sql_query('''
    SELECT 
        id AS 流水号, 
        timestamp AS 操作时间, 
        trans_type AS 业务类型, 
        factory AS 工厂, 
        waist_spec AS 腰封规格,
        quantity AS 变动数量, 
        before_stock AS 变动前库存, 
        after_stock AS 变动后库存,
        batch_no AS 单号或批次, 
        sku_details AS 关联SKU明细, 
        operator AS 操作人, 
        remark AS 备注
    FROM transactions
    ORDER BY id DESC
    ''', conn)
    conn.close()
    return df

def to_excel_bytes(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()


# ==========================================
# 4. 页面布局与导航
# ==========================================
st.title("📦 腰封出入库与发货核算管理系统")
st.caption("适用工厂独立核算 · 智能发货计划核算 · 预发货占用管理 · 缺货智能侦测 · 云端防丢持久化")

with st.sidebar:
    st.header("📌 功能导航")
    menu = st.radio(
        "请选择操作模块：",
        [
            "📊 库存总览与预警看板",
            "🚚 发货与预发货计划核算",
            "📥 采购入库（一步式直接入库）",
            "📋 出入库明细流水账",
            "⚙️ 规格对照表管理 (纠错/更换/新增)"
        ]
    )
    
    st.markdown("---")
    st.subheader("☁️ 云端数据防丢状态")
    gh_cfg = get_github_config()
    if gh_cfg:
        st.success(f"✅ **GitHub 云同步已开启**\n\n绑定仓库: `{gh_cfg['repo']}`\n*(休眠唤醒后数据永久保留)*")
        if st.button("🔄 立即从云端强制刷新数据"):
            if pull_db_from_github():
                st.success("已拉取云端最新数据！")
                st.rerun()
    else:
        st.warning("⚠️ **当前为临时容器存储**\n\n未配置 GitHub Token，Streamlit 休眠重启后数据会重置。请配置 Secrets 或使用下方手动备份。")
        
    with st.expander("💾 数据库一键备份与恢复 (.db)"):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                st.download_button(
                    label="📥 下载完整数据库文件 (.db)",
                    data=f.read(),
                    file_name=f"waist_seal_wms_{datetime.date.today()}.db",
                    mime="application/octet-stream",
                    use_container_width=True
                )
        restore_file = st.file_uploader("📂 上传恢复 .db 备份文件：", type=["db", "sqlite", "sqlite3"])
        if restore_file is not None:
            if st.button("⚠️ 确认恢复该备份数据库", use_container_width=True):
                with open(DB_FILE, "wb") as f:
                    f.write(restore_file.getvalue())
                push_db_to_github("Restore database from backup")
                st.success("✅ 数据库恢复成功！")
                st.rerun()

# ==========================================
# 5. 模块一：库存总览与预警看板
# ==========================================
if menu == "📊 库存总览与预警看板":
    st.subheader("📊 腰封当前库存总览与预警看板")
    inv_df = get_inventory_df()
    
    col1, col2, col3, col4 = st.columns(4)
    total_physical = inv_df['在库库存'].sum() if not inv_df.empty else 0
    total_pre_ship = inv_df['预发货数量'].sum() if not inv_df.empty else 0
    total_available = inv_df['可用库存'].sum() if not inv_df.empty else 0
    warning_items = len(inv_df[inv_df['可用库存'] <= inv_df['安全库存预警值']]) if not inv_df.empty else 0
    
    col1.metric("腰封实物在库总量", f"{total_physical:,} 件")
    col2.metric("📌 预发货待发占用", f"{total_pre_ship:,} 件", delta=f"{total_pre_ship} 占用" if total_pre_ship>0 else None, delta_color="off")
    col3.metric("🟢 净可用库存", f"{total_available:,} 件", delta="净可用" if total_available>=0 else "超额预发", delta_color="normal" if total_available>=0 else "inverse")
    col4.metric("⚠️ 需预警/补货品项", f"{warning_items} 种", delta=f"{warning_items} 项紧缺" if warning_items>0 else "库存健康", delta_color="inverse")
    
    st.markdown("---")
    
    alert_df = inv_df[inv_df['可用库存'] <= inv_df['安全库存预警值']]
    if not alert_df.empty:
        st.error(f"⚠️ 当前有 **{len(alert_df)}** 项腰封可用库存低于安全预警线或已出现预发超额缺货，请及时安排采购补货！")
        with st.expander("查看【需补货订购清单 (已扣除预发占用)】", expanded=True):
            display_alert = alert_df[['工厂', '腰封规格', '在库库存', '预发货数量', '可用库存', '安全库存预警值', '建议采购补货量', '库存状态', '适配产品SKU']]
            st.dataframe(display_alert, use_container_width=True)
            st.download_button(
                label="📥 导出需补货清单 (Excel)",
                data=to_excel_bytes(display_alert),
                file_name=f"腰封补货订购建议表_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
    st.markdown("### 📋 全部库存明细列表")
    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        factory_filter = st.selectbox("按工厂筛选：", ["全部工厂"] + sorted(list(inv_df['工厂'].unique())))
    with fcol2:
        search_spec = st.text_input("按腰封规格/SKU模糊搜索：", placeholder="例如：1088 或 MASTHTMRT")
        
    filtered_df = inv_df.copy()
    if factory_filter != "全部工厂":
        filtered_df = filtered_df[filtered_df['工厂'] == factory_filter]
    if search_spec:
        filtered_df = filtered_df[
            filtered_df['腰封规格'].str.contains(search_spec, case=False, na=False) |
            filtered_df['适配产品SKU'].str.contains(search_spec, case=False, na=False)
        ]
        
    display_main_cols = ['工厂', '腰封规格', '在库库存', '预发货数量', '可用库存', '安全库存预警值', '库存状态', '建议采购补货量', '适配产品SKU', '最近更新时间']
    st.dataframe(filtered_df[display_main_cols], use_container_width=True)
    
    st.download_button(
        label="📥 导出当前完整库存表 (Excel)",
        data=to_excel_bytes(filtered_df[display_main_cols]),
        file_name=f"腰封库存总览_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    with st.expander("⚙️ 快捷调整：预发货数量 / 盘点在库库存 / 安全预警值"):
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            sel_factory = st.selectbox("选择目标工厂", sorted(list(inv_df['工厂'].unique())), key="adj_fac")
        with pcol2:
            specs_for_fac = sorted(list(inv_df[inv_df['工厂'] == sel_factory]['腰封规格'].unique()))
            sel_spec = st.selectbox("选择目标腰封规格", specs_for_fac, key="adj_spec")
        
        cur_row = inv_df[(inv_df['工厂'] == sel_factory) & (inv_df['腰封规格'] == sel_spec)].iloc[0]
        
        pcol3, pcol4, pcol5 = st.columns(3)
        with pcol3:
            new_stock = st.number_input("在库实物库存 (直接盘点覆盖)", min_value=0, value=int(cur_row['在库库存']), step=10)
        with pcol4:
            new_pre_ship = st.number_input("📌 预发货数量 (待发占用)", min_value=0, value=int(cur_row['预发货数量']), step=10)
        with pcol5:
            new_safety = st.number_input("安全库存预警值", min_value=0, value=int(cur_row['安全库存预警值']), step=10)
            
        adj_remark = st.text_input("调整备注：", value="日常预发微调或盘点更新")
        
        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("💾 保存调整", key="btn_save_adj", type="primary"):
                conn = get_db_connection()
                cur = conn.cursor()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                old_stk = int(cur_row['在库库存'])
                old_pre = int(cur_row['预发货数量'])
                
                cur.execute('''
                UPDATE inventory 
                SET stock = ?, pre_ship_qty = ?, safety_stock = ?, updated_at = ?
                WHERE factory = ? AND waist_spec = ?
                ''', (new_stock, new_pre_ship, new_safety, now_str, sel_factory, sel_spec))
                
                if new_stock != old_stk or new_pre_ship != old_pre:
                    cur.execute('''
                    INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (now_str, "库存/预发调整", sel_factory, sel_spec, new_stock - old_stk, old_stk, new_stock, "MANUAL-ADJ", f"预发: {old_pre}->{new_pre_ship}", "管理员", adj_remark))
                    
                save_and_sync(conn, f"Adjust inventory {sel_factory} {sel_spec}")
                st.success(f"✅ 【{sel_factory}】规格【{sel_spec}】已成功更新！当前可用库存为 {new_stock - new_pre_ship} 件。")
                st.rerun()
                
        with btn_c2:
            if st.button("🧹 一键清空该规格预发货数量 (归零)", key="btn_clear_pre"):
                conn = get_db_connection()
                cur = conn.cursor()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute('UPDATE inventory SET pre_ship_qty = 0, updated_at = ? WHERE factory = ? AND waist_spec = ?', (now_str, sel_factory, sel_spec))
                cur.execute('''
                INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (now_str, "清空预发货", sel_factory, sel_spec, 0, int(cur_row['在库库存']), int(cur_row['在库库存']), "CLEAR-PRE", "预发清零", "管理员", "发货完毕或计划取消"))
                save_and_sync(conn, f"Clear pre-ship {sel_factory} {sel_spec}")
                st.success("✅ 预发货数量已成功清零！")
                st.rerun()


# ==========================================
# 6. 模块二：发货与预发货计划核算
# ==========================================
elif menu == "🚚 发货与预发货计划核算":
    st.subheader("🚚 发货与预发货计划核算（支持锁定预发 & 正式出库）")
    st.write("上传发货计划表格，系统将自动核算腰封需求。您可以选择**【📌 登记为预发货 (提前锁定占用)】**，或**【🚀 确认正式发货出库 (扣减实物)】**。")
    
    uploaded_file = st.file_uploader("📂 请选择或拖入发货计划 Excel 文件：", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            plan_df = pd.read_excel(uploaded_file)
            st.success(f"成功读取发货计划文件，共包含 **{len(plan_df)}** 条发货明细行。")
            
            col_sku = next((c for c in plan_df.columns if str(c).strip().upper() in ["SKU", "MSKU"]), None)
            col_qty = next((c for c in plan_df.columns if "计划发货量" in str(c) or "发货数量" in str(c) or "数量" in str(c)), None)
            col_batch = next((c for c in plan_df.columns if "发货批次号" in str(c) or "批次号" in str(c) or "发货单号" in str(c)), None)
            col_name = next((c for c in plan_df.columns if "品名" in str(c)), None)
            
            if not col_sku or not col_qty:
                st.error("❌ 无法自动识别发货计划中的【SKU】或【计划发货量】列，请检查表格表头！")
                st.write("表格当前列名：", list(plan_df.columns))
            else:
                clean_plan = pd.DataFrame({
                    "发货批次号": plan_df[col_batch] if col_batch else "未注明批次",
                    "SKU": plan_df[col_sku].astype(str).str.strip(),
                    "品名": plan_df[col_name] if col_name else "-",
                    "计划发货量": pd.to_numeric(plan_df[col_qty], errors='coerce').fillna(0).astype(int)
                })
                
                sku_map_df = get_sku_mapping_df()
                existing_skus = set(sku_map_df['SKU'].unique())
                plan_skus = set(clean_plan['SKU'].unique())
                unknown_skus = plan_skus - existing_skus
                
                if unknown_skus:
                    st.warning(f"⚠️ **侦测到发货计划中包含 {len(unknown_skus)} 个尚未在系统登记的全新 SKU**：`{', '.join(unknown_skus)}`\n\n"
                               f"这些 SKU 暂未建立对照关系，建议前往【⚙️ 规格对照表管理】添加录入。当前系统将按【未订做规格 (0库存缺货)】临时核算。")
                
                merged = pd.merge(clean_plan, sku_map_df, on="SKU", how="left")
                inv_df = get_inventory_df()
                
                analysis_records = []
                for (factory, waist), group in merged.groupby(["工厂", "腰封规格"], dropna=False):
                    total_demand = group["计划发货量"].sum()
                    skus_detail = ", ".join([f"{r.SKU} ({r.计划发货量}件)" for _, r in group.iterrows()])
                    
                    if pd.isna(waist) or str(waist).strip() == "" or waist is None or str(waist).strip().lower() == "none":
                        fac_name = factory if pd.notna(factory) and factory else "未知工厂/新SKU"
                        analysis_records.append({
                            "工厂": fac_name,
                            "腰封规格": "【未订做规格/新规格】",
                            "本次需求量": total_demand,
                            "当前在库实物": 0,
                            "当前预发占用": 0,
                            "当前可用库存": 0,
                            "本次结存可用": -total_demand,
                            "缺货数量": total_demand,
                            "状态": "❌ 缺货 (未订做新规格)",
                            "涉及SKU及发货量": skus_detail,
                            "is_unmade": True
                        })
                    else:
                        cur_row_match = inv_df[(inv_df["工厂"] == factory) & (inv_df["腰封规格"] == waist)]
                        cur_phys = cur_row_match["在库库存"].iloc[0] if not cur_row_match.empty else 0
                        cur_pre = cur_row_match["预发货数量"].iloc[0] if not cur_row_match.empty else 0
                        cur_avail = cur_row_match["可用库存"].iloc[0] if not cur_row_match.empty else 0
                        
                        after_avail = cur_avail - total_demand
                        shortage = max(0, total_demand - cur_avail)
                        
                        if shortage == 0:
                            status = "🟢 可用库存充足"
                        elif cur_phys >= total_demand:
                            status = f"🟡 实物充足但预发占用紧缺 (差{shortage}件)"
                        else:
                            status = f"🔴 实物缺货 (缺{shortage}件)"
                            
                        analysis_records.append({
                            "工厂": factory,
                            "腰封规格": waist,
                            "本次需求量": total_demand,
                            "当前在库实物": cur_phys,
                            "当前预发占用": cur_pre,
                            "当前可用库存": cur_avail,
                            "本次结存可用": after_avail,
                            "缺货数量": shortage,
                            "状态": status,
                            "涉及SKU及发货量": skus_detail,
                            "is_unmade": False
                        })
                        
                analysis_df = pd.DataFrame(analysis_records)
                analysis_df.sort_values(by=["缺货数量"], ascending=False, inplace=True)
                
                st.markdown("### 📊 腰封需求核算明细")
                total_need = analysis_df["本次需求量"].sum()
                total_short = analysis_df["缺货数量"].sum()
                
                kcol1, kcol2, kcol3 = st.columns(3)
                kcol1.metric("本次计划总需求", f"{total_need} 件")
                kcol2.metric("当前满足可发量", f"{total_need - total_short} 件")
                kcol3.metric("需关注缺口量", f"{total_short} 件", delta=f"{total_short} 缺口" if total_short > 0 else "无缺口", delta_color="inverse")
                
                display_cols = ["工厂", "腰封规格", "本次需求量", "当前在库实物", "当前预发占用", "当前可用库存", "本次结存可用", "缺货数量", "状态", "涉及SKU及发货量"]
                st.dataframe(analysis_df[display_cols], use_container_width=True)
                
                st.download_button(
                    label="📥 导出本次发货腰封核算分析表 (Excel)",
                    data=to_excel_bytes(analysis_df[display_cols]),
                    file_name=f"发货腰封核算分析_{clean_plan['发货批次号'].iloc[0] if not clean_plan.empty else '批次'}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.markdown("---")
                st.markdown("### 🛠️ 选择执行操作")
                
                default_batch = str(clean_plan['发货批次号'].iloc[0]) if not clean_plan.empty else datetime.date.today().strftime("OUT-%Y%m%d")
                out_batch_no = st.text_input("关联发货批次号：", value=default_batch)
                out_operator = st.text_input("操作人：", value="发货仓管")
                out_remark = st.text_input("备注说明：", value="发货计划批次调度")
                
                action_col1, action_col2 = st.columns(2)
                
                with action_col1:
                    st.info("📌 **方案 A：登记为预发货（提前锁定腰封）**\n\n"
                            "货品正在备货/贴标/拣货阶段，**先不扣减实物库存**，而是将需求计入**【预发货数量】**锁定占用，减少“可用库存”，防止与其他批次撞车。")
                    if st.button("📌 确认登记为预发货 (锁定腰封)", type="secondary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for _, row in analysis_df.iterrows():
                            fac = row["工厂"]
                            spec = row["腰封规格"]
                            need_qty = int(row["本次需求量"])
                            skus_info = row["涉及SKU及发货量"]
                            
                            if not row["is_unmade"]:
                                cur.execute('''
                                UPDATE inventory 
                                SET pre_ship_qty = pre_ship_qty + ?, updated_at = ?
                                WHERE factory = ? AND waist_spec = ?
                                ''', (need_qty, now_str, fac, spec))
                                
                                cur.execute('''
                                INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (now_str, "预发货锁定", fac, spec, need_qty, int(row["当前在库实物"]), int(row["当前在库实物"]), out_batch_no, skus_info, out_operator, f"{out_remark} [锁定预发占用]"))
                                
                        save_and_sync(conn, f"Lock pre-ship batch {out_batch_no}")
                        st.success(f"🎉 批次【{out_batch_no}】已成功登记为预发货！相关腰封已提前锁定占用。")
                        st.balloons()
                        st.rerun()
                        
                with action_col2:
                    st.success("🚀 **方案 B：确认正式发货出库（扣减在库实物）**\n\n"
                               "货物已经打包完毕装车发出，**正式扣减在库实物库存**。")
                    auto_release_pre = st.checkbox("如果该批次之前已登记过预发货，发货时同步释放/扣减预发占用", value=True)
                    if st.button("🚀 确认正式发货出库", type="primary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for _, row in analysis_df.iterrows():
                            fac = row["工厂"]
                            spec = row["腰封规格"]
                            need_qty = int(row["本次需求量"])
                            cur_phys = int(row["当前在库实物"])
                            cur_pre = int(row["当前预发占用"])
                            skus_info = row["涉及SKU及发货量"]
                            
                            if row["is_unmade"]:
                                cur.execute('''
                                INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (now_str, "发货出库(未订做缺货)", fac, spec, -need_qty, 0, 0, out_batch_no, skus_info, out_operator, f"{out_remark} [新规格缺货直接放行]"))
                            else:
                                after_phys = cur_phys - need_qty
                                after_pre = max(0, cur_pre - need_qty) if auto_release_pre else cur_pre
                                
                                cur.execute('''
                                UPDATE inventory 
                                SET stock = ?, pre_ship_qty = ?, updated_at = ?
                                WHERE factory = ? AND waist_spec = ?
                                ''', (after_phys, after_pre, now_str, fac, spec))
                                
                                cur.execute('''
                                INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (now_str, "正式发货出库", fac, spec, -need_qty, cur_phys, after_phys, out_batch_no, skus_info, out_operator, f"{out_remark} (释放预发:{cur_pre}->{after_pre})"))
                                
                        save_and_sync(conn, f"Outbound batch {out_batch_no}")
                        st.success(f"🎉 批次【{out_batch_no}】正式发货出库完成！实物库存已完成扣减。")
                        st.balloons()
                        st.rerun()
                        
        except Exception as e:
            st.error(f"处理文件时发生错误：{e}")


# ==========================================
# 7. 模块三：采购入库（一步式直接入库）
# ==========================================
elif menu == "📥 采购入库（一步式直接入库）":
    st.subheader("📥 采购入库（一步式直接入库，各工厂独立）")
    st.write("向包材厂订购的腰封到货后，在此处直接一步录入，在库库存即时增加，并自动记入流水账。")
    
    inv_df = get_inventory_df()
    known_factories = sorted(list(inv_df['工厂'].unique())) if not inv_df.empty else ["和光", "颖泰"]
    
    tab_single, tab_batch = st.tabs(["📝 单规格快捷入库", "📑 批量导入入库"])
    
    with tab_single:
        with st.form("inbound_form", clear_on_submit=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                in_factory_choice = st.selectbox("入库目标工厂：", known_factories + ["➕ 新增工厂..."])
                if in_factory_choice == "➕ 新增工厂...":
                    in_factory = st.text_input("请输入新工厂名称：")
                else:
                    in_factory = in_factory_choice
                    
            with col_f2:
                existing_specs = sorted(list(inv_df[inv_df['工厂'] == in_factory]['腰封规格'].unique())) if not inv_df.empty and in_factory in known_factories else []
                spec_options = existing_specs + ["➕ 输入新制作的腰封规格..."]
                in_spec_choice = st.selectbox("入库腰封规格：", spec_options)
                
                if in_spec_choice == "➕ 输入新制作的腰封规格..." or not existing_specs:
                    in_spec = st.text_input("请输入腰封规格尺寸（例如：[1088x150mm]）：")
                else:
                    in_spec = in_spec_choice
                    
            col_f3, col_f4 = st.columns(2)
            with col_f3:
                in_qty = st.number_input("入库数量（件）：", min_value=1, value=500, step=50)
            with col_f4:
                default_in_batch = datetime.date.today().strftime("IN-%Y%m%d-01")
                in_batch = st.text_input("采购单号 / 入库批次：", value=default_in_batch)
                
            col_f5, col_f6 = st.columns(2)
            with col_f5:
                in_operator = st.text_input("操作人：", value="采购员")
            with col_f6:
                in_remark = st.text_input("入库备注：", value="常规采购补货到货入库")
                
            submit_in = st.form_submit_button("📥 确认一步式入库", type="primary")
            
            if submit_in:
                if not in_factory or not in_spec:
                    st.error("❌ 工厂名称和腰封规格不能为空！")
                else:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cur.execute('SELECT stock, safety_stock FROM inventory WHERE factory = ? AND waist_spec = ?', (in_factory, in_spec))
                    row = cur.fetchone()
                    if row:
                        cur_stock = row[0]
                        new_stock = cur_stock + in_qty
                        cur.execute('''
                        UPDATE inventory SET stock = ?, updated_at = ? WHERE factory = ? AND waist_spec = ?
                        ''', (new_stock, now_str, in_factory, in_spec))
                    else:
                        cur_stock = 0
                        new_stock = in_qty
                        cur.execute('''
                        INSERT INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at)
                        VALUES (?, ?, ?, 0, 100, ?)
                        ''', (in_factory, in_spec, new_stock, now_str))
                        
                    cur.execute('''
                    INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (now_str, "采购入库", in_factory, in_spec, in_qty, cur_stock, new_stock, in_batch, "", in_operator, in_remark))
                    
                    save_and_sync(conn, f"Inbound {in_factory} {in_spec} +{in_qty}")
                    st.success(f"🎉 入库成功！【{in_factory}】规格【{in_spec}】实物在库 +{in_qty} 件。原库存：{cur_stock} 件 ➔ 现库存：{new_stock} 件！")
                    st.balloons()
                    st.rerun()
                    
    with tab_batch:
        st.write("上传批量入库 Excel 表格进行一键批量入库（包含列：`工厂`、`腰封规格`、`入库数量`、`批次号`（可选）、`备注`（可选））。")
        batch_file = st.file_uploader("📂 选择批量入库 Excel 文件：", type=["xlsx", "xls"], key="batch_in_uploader")
        if batch_file:
            try:
                b_df = pd.read_excel(batch_file)
                st.write("预览导入数据：", b_df.head())
                if st.button("🚀 确认批量执行入库", key="btn_exec_batch"):
                    conn = get_db_connection()
                    cur = conn.cursor()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    count = 0
                    for _, row in b_df.iterrows():
                        bfac = str(row['工厂']).strip()
                        bspec = str(row['腰封规格']).strip()
                        bqty = int(row['入库数量'])
                        bbatch = str(row.get('批次号', 'BATCH-IN'))
                        bremark = str(row.get('备注', '批量导入入库'))
                        
                        cur.execute('SELECT stock FROM inventory WHERE factory = ? AND waist_spec = ?', (bfac, bspec))
                        erow = cur.fetchone()
                        c_stk = erow[0] if erow else 0
                        n_stk = c_stk + bqty
                        
                        if erow:
                            cur.execute('UPDATE inventory SET stock = ?, updated_at = ? WHERE factory = ? AND waist_spec = ?', (n_stk, now_str, bfac, bspec))
                        else:
                            cur.execute('INSERT INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at) VALUES (?, ?, ?, 0, 100, ?)', (bfac, bspec, n_stk, now_str))
                            
                        cur.execute('''
                        INSERT INTO transactions (timestamp, trans_type, factory, waist_spec, quantity, before_stock, after_stock, batch_no, sku_details, operator, remark)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (now_str, "采购入库", bfac, bspec, bqty, c_stk, n_stk, bbatch, "", "批量操作员", bremark))
                        count += 1
                        
                    save_and_sync(conn, f"Batch inbound {count} items")
                    st.success(f"✅ 成功完成 {count} 笔规格的批量入库！")
                    st.rerun()
            except Exception as e:
                st.error(f"批量入库失败：{e}")


# ==========================================
# 8. 模块四：出入库明细流水账
# ==========================================
elif menu == "📋 出入库明细流水账":
    st.subheader("📋 腰封出入库明细流水账")
    st.write("记录所有采购入库、预发货锁定、正式发货出库以及盘点调整的完整历史台账，支持溯源与审计。")
    
    tx_df = get_transactions_df()
    
    if tx_df.empty:
        st.info("💡 暂无出入库流水记录，进行采购入库或发货扣减后将在此处自动生成流水。")
    else:
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            type_options = ["全部类型"] + sorted(list(tx_df['业务类型'].unique()))
            sel_type = st.selectbox("业务类型过滤：", type_options)
        with col_t2:
            factory_options = ["全部工厂"] + sorted(list(tx_df['工厂'].unique()))
            sel_fac = st.selectbox("工厂过滤：", factory_options)
        with col_t3:
            kw = st.text_input("关键字搜索（批次/单号/SKU/规格）：", placeholder="例如：FPG260917 或 1088")
            
        filtered_tx = tx_df.copy()
        if sel_type != "全部类型":
            filtered_tx = filtered_tx[filtered_tx['业务类型'] == sel_type]
        if sel_fac != "全部工厂":
            filtered_tx = filtered_tx[filtered_tx['工厂'] == sel_fac]
        if kw:
            filtered_tx = filtered_tx[
                filtered_tx['单号或批次'].astype(str).str.contains(kw, case=False, na=False) |
                filtered_tx['腰封规格'].astype(str).str.contains(kw, case=False, na=False) |
                filtered_tx['关联SKU明细'].astype(str).str.contains(kw, case=False, na=False) |
                filtered_tx['备注'].astype(str).str.contains(kw, case=False, na=False)
            ]
            
        st.write(f"共筛选出 **{len(filtered_tx)}** 条流水记录：")
        st.dataframe(filtered_tx, use_container_width=True)
        
        st.download_button(
            label="📥 导出出入库流水账 (Excel)",
            data=to_excel_bytes(filtered_tx),
            file_name=f"腰封出入库流水台账_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ==========================================
# 9. 模块五：规格对照表管理 (纠错/更换/新增)
# ==========================================
elif menu == "⚙️ 规格对照表管理 (纠错/更换/新增)":
    st.subheader("⚙️ 腰封规格与 SKU 对照表管理")
    st.write("维护产品 SKU 的基础属性（形状、规格、材质、工厂）及腰封绑定关系。支持**在线纠错修改**、**录入新 SKU**、**Excel 批量维护**。")
    
    sku_df = get_sku_mapping_df()
    inv_df = get_inventory_df()
    known_factories = sorted(list(sku_df['工厂'].unique())) if not sku_df.empty else ["和光", "颖泰"]
    
    tab_modify, tab_add_new, tab_batch_upload = st.tabs([
        "✏️ 修改 / 纠错现有 SKU（改形状、规格、腰封）",
        "➕ 录入全新 SKU", 
        "📤 上传 Excel 批量更新/追加"
    ])
    
    with tab_modify:
        st.markdown("#### ✏️ 修改 / 纠错 SKU 属性或腰封规格")
        st.caption("例如：录入时误将【圆形】录成了【矩形】、尺寸写错、或者更换了新腰封规格，均可在此直接修改保存。")
        
        sku_options = []
        for _, row in sku_df.iterrows():
            current_waist = row['腰封规格'] if pd.notna(row['腰封规格']) and row['腰封规格'] and str(row['腰封规格']).strip() != 'None' else '未订做'
            sku_options.append(f"{row['SKU']}  |  【{row['工厂']}】  |  {row['材质']}  |  {row['形状']} {row['规格']}  |  腰封: {current_waist}")
            
        selected_option = st.selectbox("🔍 请搜索或选择要修改的目标 SKU：", sku_options, key="select_target_edit_sku")
        target_sku = selected_option.split("  |  ")[0].strip()
        sku_info = sku_df[sku_df['SKU'] == target_sku].iloc[0]
        
        st.markdown("---")
        st.markdown(f"##### 🛠️ 正在编辑 SKU：`{target_sku}`")
        
        with st.form("form_edit_sku_attributes", clear_on_submit=False):
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                edit_factory = st.text_input("归属工厂：", value=str(sku_info['工厂']))
            with col_e2:
                edit_material = st.text_input("产品材质：", value=str(sku_info['材质']) if pd.notna(sku_info['材质']) else "")
            with col_e3:
                standard_shapes = ["圆形", "矩形", "方形", "椭圆形", "其他"]
                cur_shape = str(sku_info['形状']).strip() if pd.notna(sku_info['形状']) else "矩形"
                shape_idx = standard_shapes.index(cur_shape) if cur_shape in standard_shapes else len(standard_shapes) - 1
                edit_shape = st.selectbox("产品形状 (纠错选择)：", standard_shapes, index=shape_idx)
                
            col_e4, col_e5 = st.columns(2)
            with col_e4:
                edit_dim = st.text_input("产品规格尺寸 (如 18\" 或 36*12\")：", value=str(sku_info['规格']) if pd.notna(sku_info['规格']) else "")
            with col_e5:
                cur_w_val = str(sku_info['腰封规格']).strip() if pd.notna(sku_info['腰封规格']) and sku_info['腰封规格'] and str(sku_info['腰封规格']).strip() != 'None' else ''
                edit_waist = st.text_input("腰封规格尺寸 (如 [1088x150mm]，留空表示暂未订做)：", value=cur_w_val)
                
            st.caption("💡 提示：修改形状或规格后，系统对照表立即更新；若输入了新的腰封规格，系统会自动在对应工厂库存表中添加该规格。")
            btn_save_edits = st.form_submit_button("💾 确认保存修改", type="primary")
            
            if btn_save_edits:
                clean_fac = str(edit_factory).strip()
                clean_mat = str(edit_material).strip()
                clean_shape = str(edit_shape).strip()
                clean_dim = str(edit_dim).strip()
                clean_waist = str(edit_waist).strip() if edit_waist and str(edit_waist).strip() != "" and str(edit_waist).strip().lower() != "none" else None
                
                if not clean_fac:
                    st.error("❌ 工厂名称不能为空！")
                else:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cur.execute('''
                    UPDATE sku_mapping
                    SET factory = ?, material = ?, shape = ?, dimension = ?, waist_spec = ?
                    WHERE sku = ?
                    ''', (clean_fac, clean_mat, clean_shape, clean_dim, clean_waist, target_sku))
                    
                    if clean_waist:
                        cur.execute('''
                        INSERT OR IGNORE INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at)
                        VALUES (?, ?, 0, 0, 100, ?)
                        ''', (clean_fac, clean_waist, now_str))
                        
                    save_and_sync(conn, f"Edit SKU {target_sku}")
                    st.success(f"🎉 SKU【{target_sku}】修改已成功保存！\n\n"
                               f"最新属性：工厂【{clean_fac}】· 材质【{clean_mat}】· **形状【{clean_shape}】** · 规格【{clean_dim}】· 腰封【{clean_waist or '暂未订做'}】")
                    st.balloons()
                    st.rerun()

        with st.expander("🗑️ 删除此 SKU (仅用于完全录错废弃的条目)"):
            st.warning(f"注意：删除操作将从系统中永久移除 SKU【{target_sku}】的对照关系。")
            del_confirm = st.checkbox(f"我确认要永久删除 SKU【{target_sku}】", key=f"del_chk_{target_sku}")
            if st.button("确认删除", type="secondary", key="btn_del_sku"):
                if del_confirm:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute('DELETE FROM sku_mapping WHERE sku = ?', (target_sku,))
                    save_and_sync(conn, f"Delete SKU {target_sku}")
                    st.success(f"SKU【{target_sku}】已被成功删除。")
                    st.rerun()
                else:
                    st.error("请先勾选确认复选框！")

    with tab_add_new:
        st.markdown("#### ➕ 录入单个新产品 SKU")
        st.caption("新产品上线时，在此填写产品属性与对应的腰封规格。如果腰封还未定做，腰封规格留空即可。")
        
        with st.form("form_add_new_sku", clear_on_submit=False):
            col_n1, col_n2, col_n3 = st.columns(3)
            with col_n1:
                new_sku_code = st.text_input("产品 SKU 编码 (必填)*", placeholder="例如：MASTHTMRD26")
            with col_n2:
                n_factory_choice = st.selectbox("归属工厂 (必选)*", known_factories + ["➕ 新增工厂..."])
                if n_factory_choice == "➕ 新增工厂...":
                    n_factory = st.text_input("输入新工厂名：", placeholder="例如：新辉")
                else:
                    n_factory = n_factory_choice
            with col_n3:
                n_material = st.text_input("材质", placeholder="例如：胡桃木 / 相思木")
                
            col_n4, col_n5, col_n6 = st.columns(3)
            with col_n4:
                n_shape = st.selectbox("形状", ["圆形", "矩形", "方形", "椭圆形", "其他"])
            with col_n5:
                n_dim = st.text_input("产品规格尺寸", placeholder="例如：26\" 或 36*12\"")
            with col_n6:
                exist_specs = sorted(list(inv_df[inv_df['工厂'] == n_factory]['腰封规格'].unique())) if not inv_df.empty and n_factory in known_factories else []
                n_spec_choice = st.selectbox("腰封规格选择：", ["【暂未订做 (留空)】"] + exist_specs + ["➕ 输入新订做尺寸..."])
                
                if n_spec_choice == "➕ 输入新订做尺寸...":
                    n_waist_val = st.text_input("请输入腰封规格：", placeholder="例如：[1088x150mm]")
                elif n_spec_choice == "【暂未订做 (留空)】":
                    n_waist_val = None
                else:
                    n_waist_val = n_spec_choice
                    
            btn_save_new_sku = st.form_submit_button("💾 保存并录入新 SKU", type="primary")
            
            if btn_save_new_sku:
                if not new_sku_code or not str(new_sku_code).strip():
                    st.error("❌ SKU 编码不能为空！")
                elif not n_factory or not str(n_factory).strip():
                    st.error("❌ 工厂不能为空！")
                else:
                    clean_sku = str(new_sku_code).strip()
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute('SELECT COUNT(*) FROM sku_mapping WHERE sku = ?', (clean_sku,))
                    if cur.fetchone()[0] > 0:
                        st.error(f"❌ SKU【{clean_sku}】已存在于系统中，请勿重复添加！如果需要纠错修改，请前往第一个标签页【✏️ 修改 / 纠错现有 SKU】。")
                        conn.close()
                    else:
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        clean_waist = str(n_waist_val).strip() if n_waist_val and str(n_waist_val).strip() != "" else None
                        
                        cur.execute('''
                        INSERT INTO sku_mapping (factory, material, shape, dimension, waist_spec, sku)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (n_factory.strip(), n_material.strip(), n_shape, n_dim.strip(), clean_waist, clean_sku))
                        
                        if clean_waist:
                            cur.execute('''
                            INSERT OR IGNORE INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at)
                            VALUES (?, ?, 0, 0, 100, ?)
                            ''', (n_factory.strip(), clean_waist, now_str))
                            
                        save_and_sync(conn, f"Add SKU {clean_sku}")
                        st.success(f"🎉 新 SKU【{clean_sku}】录入成功！归属工厂：{n_factory}，腰封规格：{clean_waist or '暂未订做(0库存)'}。")
                        st.balloons()
                        st.rerun()

    with tab_batch_upload:
        st.markdown("#### 📤 通过 Excel 表格批量导入 / 批量更新 SKU")
        st.caption("表格列名需包含：`工厂`、`材质`、`形状`、`规格`、`腰封规格`、`SKU`。")
        
        mode = st.radio("选择导入模式：", ["增量追加 / 更新（保留旧数据，已存在则更新形状/规格/腰封，新SKU则新增）", "⚠️ 完全覆盖（清空现有所有对照数据并重新建立）"])
        batch_spec_file = st.file_uploader("选择 Excel 对照表文件：", type=["xlsx", "xls"], key="batch_sku_uploader")
        
        if batch_spec_file and st.button("🚀 执行 Excel 导入", type="primary"):
            try:
                up_df = pd.read_excel(batch_spec_file)
                conn = get_db_connection()
                cur = conn.cursor()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if "完全覆盖" in mode:
                    cur.execute('DELETE FROM sku_mapping')
                    
                added_cnt = 0
                for _, r in up_df.iterrows():
                    sku_val = str(r['SKU']).strip()
                    fac_val = str(r['工厂']).strip()
                    w_val = str(r['腰封规格']).strip() if pd.notna(r['腰封规格']) and str(r['腰封规格']).strip() != '' else None
                    
                    cur.execute('''
                    INSERT INTO sku_mapping (factory, material, shape, dimension, waist_spec, sku)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sku) DO UPDATE SET
                        factory = excluded.factory,
                        material = excluded.material,
                        shape = excluded.shape,
                        dimension = excluded.dimension,
                        waist_spec = excluded.waist_spec
                    ''', (fac_val, str(r.get('材质', '')), str(r.get('形状', '')), str(r.get('规格', '')), w_val, sku_val))
                    
                    if w_val:
                        cur.execute('''
                        INSERT OR IGNORE INTO inventory (factory, waist_spec, stock, pre_ship_qty, safety_stock, updated_at)
                        VALUES (?, ?, 0, 0, 100, ?)
                        ''', (fac_val, w_val, now_str))
                    added_cnt += 1
                    
                save_and_sync(conn, f"Batch update {added_cnt} SKUs")
                st.success(f"✅ Excel 批量导入处理完成！共导入/更新了 {added_cnt} 个 SKU 的规格对应关系。")
                st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")

    st.markdown("---")
    st.markdown("### 📋 系统当前维护的全部 SKU 规格表")
    st.dataframe(sku_df, use_container_width=True)
    
    st.download_button(
        label="📥 导出当前全部 SKU 对照表 (Excel)",
        data=to_excel_bytes(sku_df),
        file_name=f"腰封规格对照表_全量_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
