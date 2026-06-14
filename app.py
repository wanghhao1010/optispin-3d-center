# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [最高權限工業 Storage + 實體防呆鈕完全體]
# ============================================================================== #

import streamlit as st
import numpy as np
import trimesh
import os
import time
import io
import requests  
import base64
import plotly.graph_objects as go
from datetime import datetime
from google import genai

# 1. 系統網頁頂層基礎配置
st.set_page_config(
    page_title="OptiSpin 3D 控制中心",
    page_icon="🛸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 初始化預覽快取空間 (存在手機網頁的 session 中，記住開啟過的 3D/點雲狀態)
if "preview_cache" not in st.session_state:
    st.session_state["preview_cache"] = {}

# 2. 強行綁定絕對正確 Database 與 Storage REST URL
PROJECT_REF = "pwmijkkzufcqrnmodxap"
BASE_URL = f"https://{PROJECT_REF}.supabase.co/rest/v1/"
STORAGE_URL = f"https://{PROJECT_REF}.supabase.co/storage/v1/object/public/models/"

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("❌ 偵測到雲端 Secrets 設定缺失！請確認 Streamlit Cloud 配置。")
    st.stop()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def fetch_lightweight_assets():
    """🚀 核心降載防禦：僅抓取輕量純文字元數據，徹底終結 Timeout"""
    try:
        fields = "id,filename,timestamp,vertices,faces,bounding_box,surface_area,volume,ai_diagnosis,filesize"
        url_new = f"{BASE_URL}optispin_assets?select={fields}&order=id.desc"
        response = requests.get(url_new, headers=HEADERS, timeout=8)
        
        if response.status_code == 200:
            raw_list = response.json()
            clean_list = []
            for row in raw_list:
                file_url = row.get("filesize", "")
                # 🛡️ 乾淨安全過濾：只放行全新 Storage 通道（http開頭）的新資料
                if str(file_url).startswith("http"):
                    safe_row = {
                        "id": row.get("id", 0),
                        "filename": row.get("filename", "未命名資產"),
                        "timestamp": row.get("timestamp", "2026-06-14 00:00"),
                        "vertices": int(row.get("vertices")) if row.get("vertices") is not None else 0,
                        "faces": int(row.get("faces")) if row.get("faces") is not None else 0,
                        "bounding_box": row.get("bounding_box", "未知尺寸"),
                        "ai_diagnosis": row.get("ai_diagnosis", "無診斷數據"),
                        "filesize": file_url
                    }
                    clean_list.append(safe_row)
            return clean_list
        return []
    except Exception:
        return []

def upload_to_supabase_storage(file_name, file_bytes):
    """📦 儲存桶發射器：將 3D 實體檔案直接推上 Supabase Storage models 儲存桶"""
    timestamp_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp_prefix}_{file_name}"
    
    upload_url = f"https://{PROJECT_REF}.supabase.co/storage/v1/object/models/{unique_filename}"
    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/octet-stream"
    }
    
    try:
        res = requests.post(upload_url, headers=storage_headers, data=file_bytes, timeout=30)
        if res.status_code in [200, 201]:
            return f"{STORAGE_URL}{unique_filename}"
        return ""
    except Exception:
        return ""

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 數位雙生管理端")

tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

# 瞬間加載全量 Storage 歷史紀錄
cloud_data = fetch_lightweight_assets()

# ------------------------------------------------------------------------------ #
# 分頁一：3D 大數據資產管理端
# ------------------------------------------------------------------------------ #
with tab1:
    st.subheader("📥 點擊或拖曳上傳全新 3D 掃描模型")
    uploaded_file = st.file_uploader(
        "支援工業幾何格式 (GLB/USDZ/OBJ/STL)", type=["glb", "obj", "usdz", "stl"], label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        st.info(f"📦 檔案已就緒：{uploaded_file.name} ({uploaded_file.size/1024/1024:.2f} MB)")
        
        # 🛠️ 實體防呆同步按鈕：強制打破手機瀏覽器輸入法與網路訊號的凍結鎖
        if st.button("🚀 點擊確認：啟動雲端大數據同步", type="primary", use_container_width=True, key="force_upload_trigger_btn"):
            upload_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"
            
            with st.spinner("🚀 正在進行幾何拓撲解析與工業尺寸校正..."):
                try:
                    file_bytes = uploaded_file.read()
                    file_name = uploaded_file.name
                    file_extension = os.path.splitext(file_name)[1].lower()
                    
                    vertices_count, faces_count = 0, 0
                    bounding_box_str = "150.0 x 150.0 x 150.0 mm"
                    area_val, volume_val = 0.0, 0.0
                    
                    if file_extension in [".obj", ".stl", ".glb"]:
                        try:
                            file_stream = io.BytesIO(file_bytes)
                            scene_or_mesh = trimesh.load(file_stream, file_type=file_extension.strip('.'))
                            mesh = list(scene_or_mesh.geometry.values())[0] if isinstance(scene_or_mesh, trimesh.Scene) else scene_or_mesh
                            if mesh is not None:
                                vertices_count = len(mesh.vertices)
                                faces_count = len(mesh.faces)
                                area_val = float(mesh.area) * 1000000.0
                                volume_val = float(mesh.volume) * 1000000000.0 if mesh.is_volume else 0.0
                                bbox = mesh.bounding_box.extents * 1000.0
                                bounding_box_str = f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm"
                        except Exception: pass
                    elif file_extension == ".usdz":
                        vertices_count, faces_count = 45000, 90000
                        bounding_box_str = "180.0 x 120.0 x 160.0 mm (iOS AR 預估尺寸)"
                except Exception as ex_init:
                    st.error(f"❌ 幾何分析失敗: {str(ex_init)}")
                    st.stop()

            with st.spinner("📦 正在將 3D 圖檔高速分流至雲端儲存桶 (Storage)..."):
                model_url = upload_to_supabase_storage(file_name, file_bytes)
                if not model_url:
                    st.error("❌ 儲存桶寫入失敗！請確認 Supabase 中已建立 models 儲存桶並開通 Policy。")
                    st.stop()

            with st.spinner("🤖 正在調度 Gemini 專家系統進行生成式工藝評估..."):
                try:
                    prompt_analysis = f"你是一位精通 3D 列印與精密加工的專家。工件檔名 {file_name}，網格面數 {faces_count}，換算尺寸 {bounding_box_str}。請給予 100 字內 FDM PLA/PETG 列印建議。"
                    ai_response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=[prompt_analysis])
                    diagnosis_text = ai_response.text
                except Exception:
                    diagnosis_text = "工件收錄成功。"

            try:
                asset_row = {
                    "filename": file_name, "vertices": int(vertices_count), "faces": int(faces_count),
                    "bounding_box": bounding_box_str, "surface_area": float(area_val), "volume": float(volume_val),
                    "ai_diagnosis": diagnosis_text, "filesize": model_url, "timestamp": datetime.now().isoformat() 
                }
                requests.post(f"{BASE_URL}optispin_assets", headers=HEADERS, json=asset_row, timeout=15)
                st.success(f"🎉 {file_name} 已成功格式化並存入雲端中心！")
                time.sleep(0.5)
                st.rerun()  
            except Exception: pass

    # ------------------------------------------------------------------------------ #
    # 🔍 3D 雲端資產搜尋儀表板 (極速、不超時、按鈕下方原地嵌入、支援狀態快取)
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    total_count = len(cloud_data) if cloud_data else 0
    st.subheader(f"🔍 3D 雲端資產動態搜尋倉儲 (目前雲端總計: {total_count} 筆)")
    search_query = st.text_input("搜尋資產名稱", placeholder="輸入關鍵字篩選...", key="main_search_input", label_visibility="collapsed")
    
    if cloud_data:
        filtered_data = [r for r in cloud_data if search_query.lower() in str(r.get("filename", "")).lower() or search_query.lower() in str(r.get("ai_diagnosis", "")).lower()]
        
        if filtered_data:
            for item in filtered_data:
                with st.container():
                    fname = item.get('filename')
                    asset_id = item.get('id')
                    file_url = item.get('filesize', '')
                    is_usdz = str(fname).lower().endswith('.usdz')
                    
                    st.markdown(f"#### 📄 檔案: {fname}")
                    st.caption(f"🕒 上傳時間: {str(item.get('timestamp', ''))[:16].replace('T', ' ')}")
                    
                    # 🛠 *所見即所得「內嵌畫布容器槽」，完美卡在數據與按鈕的正中間！*
                    canvas_slot = st.container()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("工業邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    st.info(f"🤖 Gemini 智慧評估報告：\n{item.get('ai_diagnosis')}")

                    # 快取開關識別碼
                    mesh_toggle_key = f"toggle_mesh_{asset_id}"
                    pc_toggle_key = f"toggle_pc_{asset_id}"

                    # 雙軌分流按鈕
                    view_col1, view_col2, del_col = st.columns([1.2, 1.2, 1])
                    with view_col1:
                        if st.button(f"🛰️ 實體全貼圖預覽", key=f"btn_m_{asset_id}"):
                            st.session_state[mesh_toggle_key] = not st.session_state.get(mesh_toggle_key, False)
                            st.session_state[pc_toggle_key] = False
                            st.rerun()
                            
                    with view_col2:
                        if st.button(f"🌌 高科技單色點雲", key=f"btn_pc_{asset_id}"):
                            st.session_state[pc_toggle_key] = not st.session_state.get(pc_toggle_key, False)
                            st.session_state[mesh_toggle_key] = False
                            st.rerun()

                    with del_col:
                        if st.button(f"🗑️ 銷毀", key=f"del_{asset_id}"):
                            requests.delete(f"{BASE_URL}optispin_assets?id=eq.{asset_id}", headers=HEADERS)
                            st.toast("已從雲端銷毀")
                            time.sleep(0.5)
                            st.rerun()

                    # 🛠️ 記憶層快取渲染核心
                    with canvas_slot:
                        # 1. 實體全貼圖預覽被打開
                        if st.session_state.get(mesh_toggle_key, False):
                            if is_usdz:
                                # 🍏 iOS 原生高權限 AR 投放通路：跨越沙盒限制，秒開 iPhone 相機
                                st.success("🍏 iOS 原生 AR 靜態網址通路已就緒！")
                                st.link_button(
                                    "📱 點擊此處 → 立即啟動 iPhone 官方空間 AR 投放",
                                    url=file_url,
                                    use_container_width=True,
                                    type="primary"
                                )
                                st.caption("<div style='text-align:center; color:#888; font-size:11px;'>直連技術：點擊後瀏覽器會瞬間喚醒蘋果原廠 3D 快照鏡頭</div>", unsafe_allow_html=True)
                            else:
                                # 🛰️ GLB 通用格式穩定版：從儲存桶網址直接極速串流
                                html_canvas = f"""
                                <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                                <model-viewer 
                                    src="{file_url}"
                                    alt="OptiSpin GLB" camera-controls auto-rotate shadow-intensity="1" Environment-image="neutral"
                                    style="width: 100%; height: 320px; background-color: #1a1a1a; border-radius: 10px;">
                                </model-viewer>
                                """
                                st.components.v1.html(html_canvas, height=330)

                        # 2. 高科技點雲預覽被打開
                        if st.session_state.get(pc_toggle_key, False):
                            if is_usdz:
                                st.warning("🌌 點雲模擬目前專屬於工業 GLB 格式，USDZ 請直接啟用「實體全貼圖預覽」投放 AR！")
                            else:
                                with st.spinner("🌌 正在從儲存桶逆向還原高科技點雲..."):
                                    try:
                                        # 從雲端儲存桶高速下載二進位數據並用 trimesh 進行輕量點雲抽樣
                                        res_file = requests.get(file_url, timeout=15)
                                        scene_or_m = trimesh.load(io.BytesIO(res_file.content), file_type='glb')
                                        c_mesh = list(scene_or_m.geometry.values())[0] if isinstance(scene_or_m, trimesh.Scene) else scene_or_m
                                        
                                        max_points = 1500  # 架構升級後，點雲精度可以提高 1.5 倍而不卡頓
                                        indices = np.random.choice(len(c_mesh.vertices), min(len(c_mesh.vertices), max_points), replace=False)
                                        pts = c_mesh.vertices[indices] * 1000.0
                                        
                                        fig = go.Figure(data=[go.Scatter3d(
                                            x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
                                            mode='markers', marker=dict(size=2.5, color='#00f0ff', opacity=0.85)
                                        )])
                                        fig.update_layout(
                                            scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), bgcolor="black"),
                                            margin=dict(r=0, l=0, b=0, t=0), paper_bgcolor="black", height=320
                                        )
                                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                                    except Exception:
                                        st.error("🔺 點雲拓撲還原超時")
                                            
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)
        else:
            st.info("💡 沒有符合當前搜尋關鍵字的 3D 資產。")
    else:
        st.info("📦 當前雲端大數據倉儲尚無任何資產，請於上方上傳首個 3D 模型檔案。")

# ------------------------------------------------------------------------------ #
# 分頁二：Scaniverse 智慧診斷日誌
# ------------------------------------------------------------------------------ #
with tab2:
    st.subheader("🤖 大數據中心跨資產綜合分析日誌")
    if cloud_data:
        recent_assets = cloud_data[:3]
        assets_summary_list = [f"[{index+1}] 檔案名稱: {item.get('filename')} | 面數: {item.get('faces', 0)}" for index, item in enumerate(recent_assets)]
        all_assets_context = "\n".join(assets_summary_list)
        
        if st.button("🔄 同步雲端數據並生成綜合診斷報告", type="primary", key="sync_log_btn"):
            with st.spinner("🤖 正在調度 Gemini 進行大數據分析..."):
                try:
                    intelligence_prompt = f"你是一位精密系統設計的工業逆向工程專家，請分析以下最近的模型數據趨勢並給予自動化步進馬達與 FDM 列印速度調校建議：\n{all_assets_context}"
                    response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=[intelligence_prompt])
                    st.session_state["cached_diagnostic_report"] = response.text
                except Exception:
                    st.error("🧠 雲端繁忙，請稍候再試。")
        
        if "cached_diagnostic_report" in st.session_state:
            st.markdown(f"<div style='background-color:#2a2a2a; padding:15px; border-radius:10px;'>{st.session_state['cached_diagnostic_report']}</div>", unsafe_allow_html=True)
    else:
        st.info("💡 目前雲端資料庫尚無有效資產。")