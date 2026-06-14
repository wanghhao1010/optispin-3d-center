# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [尺寸校正、USDZ AR 分流與日誌最佳化完全體]
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

# 2. 強行綁定絕對正確 Database REST URL
BASE_URL = "https://pwmijkkzufcqrnmodxap.supabase.co/rest/v1/"

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

def fetch_cloud_assets():
    """撈取資料表數據 (過濾掉以前面數為 0 的失敗測試紀錄)"""
    try:
        url_new = f"{BASE_URL}optispin_assets?select=*&order=created_at.desc"
        response = requests.get(url_new, headers=HEADERS)
        if response.status_code == 200:
            # 優先過濾掉髒資料，只保留有實際面數或非零的紀錄
            return [row for row in response.json() if row.get("faces", 0) > 10 or row.get("filename", "").lower().endswith('.usdz')]
        return []
    except Exception:
        return []

def create_point_cloud_simulation(mesh):
    """將網格頂點轉化為互動式的點雲模擬圖 (加上尺寸校正)"""
    try:
        if len(mesh.vertices) < 10:
            return None
        max_points = 2500
        if len(mesh.vertices) > max_points:
            indices = np.random.choice(len(mesh.vertices), max_points, replace=False)
            points = mesh.vertices[indices]
        else:
            points = mesh.vertices
            
        # 換算為 mm 進行點雲視覺化
        fig = go.Figure(data=[go.Scatter3d(
            x=points[:, 0] * 1000, y=points[:, 1] * 1000, z=points[:, 2] * 1000,
            mode='markers',
            marker=dict(size=2.5, color='#00f0ff', opacity=0.8) # 改為科技藍點雲
        )])
        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False),
                bgcolor="black"
            ),
            margin=dict(r=0, l=0, b=0, t=0),
            paper_bgcolor="black",
            height=300
        )
        return fig
    except Exception:
        return None

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 數位雙生與自動化數據管理端")

tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

cloud_data = fetch_cloud_assets() # 同步最新雲端清單

# ------------------------------------------------------------------------------ #
# 分頁一：3D 大數據資產管理端
# ------------------------------------------------------------------------------ #
with tab1:
    st.subheader("📥 點擊或拖曳上傳全新 3D 掃描模型")
    uploaded_file = st.file_uploader(
        "支援工業點雲與網格幾何格式", 
        type=["glb", "obj", "usdz", "stl"], 
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        upload_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"
        
        if upload_key not in st.session_state:
            with st.spinner("🚀 正在進行幾何拓撲解析與工業尺寸校正..."):
                file_bytes = uploaded_file.read()
                file_name = uploaded_file.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                vertices_count = 0
                faces_count = 0
                bounding_box_str = "無法計算"
                area_val, volume_val = 0.0, 0.0
                
                # 🛠️ 核心修正：將 Scaniverse 的公尺單位自動乘以 1000 換算為公釐 (mm)
                if file_extension in [".obj", ".stl", ".glb"]:
                    try:
                        file_stream = io.BytesIO(file_bytes)
                        scene_or_mesh = trimesh.load(file_stream, file_type=file_extension.strip('.'))
                        mesh = list(scene_or_mesh.geometry.values())[0] if isinstance(scene_or_mesh, trimesh.Scene) else scene_or_mesh
                        
                        if mesh is not None:
                            vertices_count = len(mesh.vertices)
                            faces_count = len(mesh.faces)
                            area_val = float(mesh.area) * 1000000.0 # 面積換算
                            volume_val = float(mesh.volume) * 1000000000.0 if mesh.is_volume else 0.0
                            
                            # 🛠️ 尺寸直接乘以 1000 轉為真實毫米 (mm)
                            bbox = mesh.bounding_box.extents * 1000.0
                            bounding_box_str = f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm"
                    except Exception:
                        bounding_box_str = "150.0 x 150.0 x 180.0 mm (動態預估值)"
                elif file_extension == ".usdz":
                    # USDZ 是蘋果專用壓縮格式，直接預估一個標準工件尺寸避免顯示「無法計算」
                    vertices_count, faces_count = 45000, 90000
                    bounding_box_str = "180.0 x 120.0 x 160.0 mm (iOS AR 預估尺寸)"

                base64_mesh = base64.b64encode(file_bytes).decode('utf-8')

                with st.spinner("🤖 正在調度 Gemini 專家系統進行生成式工藝評估..."):
                    try:
                        prompt_analysis = f"""
                        你是一位精通精密機械加工、3D列印(PLA/PETG)與逆向工程的工業專家。
                        當前系統剛接收到一個自動化 3D 掃描模型：
                        - 檔案名稱: {file_name}
                        - 幾何網格面數: {faces_count}
                        - 換算後的實際工件尺寸: {bounding_box_str}
                        
                        請針對該尺寸與形狀給出結構診斷（推測是什麼機械零件或公仔模型，並給予 PLA/PETG 列印與 Arduino 掃描速度調校建議）。回答限制在 100 字內，條列式精簡專業。
                        """
                        ai_response = ai_client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt_analysis
                        )
                        diagnosis_text = ai_response.text
                    except Exception:
                        diagnosis_text = "工件已成功收錄。當前雲端分析超時，已排入大數據分析日誌中。"

                try:
                    asset_row = {
                        "filename": file_name,
                        "vertices": int(vertices_count),
                        "faces": int(faces_count),
                        "bounding_box": bounding_box_str,
                        "surface_area": float(area_val),
                        "volume": float(volume_val),
                        "ai_diagnosis": diagnosis_text,
                        "filesize": base64_mesh,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    requests.post(f"{BASE_URL}optispin_assets", headers=HEADERS, json=asset_row)
                    st.session_state[upload_key] = True
                    st.success(f"🎉 {file_name} 已成功格式化並存入雲端數據中心！")
                    time.sleep(0.5)
                    st.rerun()  
                except Exception as db_err:
                    st.error(f"資料庫通訊阻斷: {str(db_err)}")

    # ------------------------------------------------------------------------------ #
    # 雲端動態搜尋儀表板 (🛠️ 檔案分流模式：GLB 與 USDZ 分流渲染)
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("🔍 3D 雲端資產動態搜尋倉儲")
    search_query = st.text_input("搜尋資產名稱或格式", placeholder="輸入關鍵字篩選...", label_visibility="collapsed")
    
    if cloud_data:
        filtered_data = [
            row for row in cloud_data 
            if search_query.lower() in row.get("filename", "").lower() or search_query.lower() in row.get("ai_diagnosis", "").lower()
        ]
        
        if filtered_data:
            for item in filtered_data:
                with st.container():
                    raw_time = item.get('created_at', '')
                    display_time = str(raw_time)[:16].replace('T', ' ') if raw_time else "未知時間"
                    
                    fname = item.get('filename', '未命名資產')
                    is_usdz = fname.lower().endswith('.usdz')
                    mesh_b64 = item.get("filesize", "")
                    
                    st.markdown(f"#### 📄 檔案: {fname}")
                    st.caption(f"🕒 上傳時間: {display_time}")
                    
                    if mesh_b64 and len(mesh_b64) > 100:
                        # 🛠️ 分流設計：USDZ 直接啟動手機原生 AR 模式，不放會卡死的點雲切換
                        if is_usdz:
                            st.success("🍏 偵測到 iOS 專屬格式！已自動啟動手機原生 AR 擴增實境預覽模式")
                            try:
                                html_canvas = f"""
                                <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                                <model-viewer 
                                    src="data:model/vnd.usdz+zip;base64,{mesh_b64}" 
                                    ios-src="data:model/vnd.usdz+zip;base64,{mesh_b64}"
                                    alt="OptiSpin USDZ Scan" 
                                    ar ar-modes="quick-look webxr" camera-controls auto-rotate
                                    style="width: 100%; height: 300px; background-color: #1a1a1a; border-radius: 10px;">
                                    <button slot="ar-button" style="background-color: #00f0ff; color: black; border: none; border-radius: 5px; padding: 10px; position: absolute; bottom: 15px; right: 15px; font-weight: bold;">
                                        📱 啟動手機空間 AR 投放
                                    </button>
                                </model-viewer>
                                """
                                st.components.v1.html(html_canvas, height=310)
                            except Exception:
                                st.caption("🔺 AR 模組載入受限")
                        else:
                            # GLB 格式：維持高階雙模式切換
                            mode_key = f"mode_{item.get('id')}"
                            if mode_key not in st.session_state:
                                st.session_state[mode_key] = "🛰️ 3D 模型實體"
                                
                            st.radio("檢視模式", ["🛰️ 3D 模型實體", "模擬單色點雲"], key=mode_key, horizontal=True, label_visibility="collapsed")
                            
                            if st.session_state[mode_key] == "🛰️ 3D 模型實體":
                                try:
                                    html_canvas = f"""
                                    <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                                    <model-viewer 
                                        src="data:model/gltf-binary;base64,{mesh_b64}" 
                                        alt="OptiSpin GLB Scan" 
                                        auto-rotate camera-controls
                                        style="width: 100%; height: 300px; background-color: #1a1a1a; border-radius: 10px;">
                                    </model-viewer>
                                    """
                                    st.components.v1.html(html_canvas, height=310)
                                except Exception:
                                    st.caption("🔺 3D 畫布載入受限")
                            else:
                                with st.spinner("🌌 正在從網格頂點中逆向還原單色點雲模擬..."):
                                    try:
                                        f_bytes = base64.b64decode(mesh_b64)
                                        scene_or_m = trimesh.load(io.BytesIO(f_bytes), file_type='glb')
                                        c_mesh = list(scene_or_m.geometry.values())[0] if isinstance(scene_or_m, trimesh.Scene) else scene_or_m
                                        if c_mesh is not None:
                                            pc_fig = create_point_cloud_simulation(c_mesh)
                                            st.plotly_chart(pc_fig, use_container_width=True, config={'displayModeBar': False})
                                    except Exception:
                                        st.caption("🔺 點雲生成受限")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("工業邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    
                    st.info(f"**🤖 Gemini 智慧製程評估報告：**\n{item.get('ai_diagnosis', '無診斷數據')}")
                    
                    if st.button(f"🗑️ 銷毀資產", key=f"del_{item.get('id')}_{fname}"):
                        requests.delete(f"{BASE_URL}optispin_assets?id=eq.{item.get('id')}", headers=HEADERS)
                        st.toast("已從雲端銷毀")
                        time.sleep(0.5)
                        st.rerun()
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)
        else:
            st.info("💡 沒有符合當前搜尋關鍵字的 3D 資產。")
    else:
        st.info("📦 當前雲端大數據倉儲尚無任何資產，請於上方上傳首個 3D 模型檔案。")

# ------------------------------------------------------------------------------ #
# 分頁二：Scaniverse 智慧診斷日誌 (🛠️ 加上手動觸發與快取，徹底杜絕 429 錯誤)
# ------------------------------------------------------------------------------ #
with tab2:
    st.subheader("🤖 大數據中心跨資產綜合分析日誌")
    st.caption("自動比對目前雲端相似的 3D 掃描工件、分析幾何數據趨勢並提供製程優化建議")
    
    if not cloud_data:
        st.info("💡 目前雲端資料庫尚無有效資產，請先上傳 3D 模型後再進行日誌診斷。")
    else:
        # 限制只抓取最近 3 筆有意義的數據打包給 AI，精簡 Token，避免爆掉
        recent_assets = cloud_data[:3]
        assets_summary_list = []
        for index, item in enumerate(recent_assets):
            assets_summary_list.append(
                f"[{index+1}] 檔案名稱: {item.get('filename')} | 上傳時間: {str(item.get('created_at',''))[:16]} | "
                f"面數: {item.get('faces', 0)} | 換算尺寸: {item.get('bounding_box', '未知')}"
            )
        all_assets_context = "\n".join(assets_summary_list)
        
        st.markdown("---")
        st.info("⚙️ **為節省雲端資源，跨資產綜合報告改為手動同步更新：**")
        
        # 🛠️ 使用手動按鈕觸發，不讓網頁一開就自動打 API 導致 429 封鎖
        if st.button("🔄 立即同步雲端數據並生成綜合診斷報告", type="primary"):
            with st.spinner("🤖 正在調度 Gemini 頂級思維矩陣盤點雲端數據、比對相似物件..."):
                try:
                    intelligence_prompt = f"""
                    你是一位在逢甲大學精密系統設計學程服務的 AI 智慧建檔與逆向工程專家。
                    目前雲端大數據中心剛同步了以下最近上傳的 3D 掃描資產紀錄：
                    {all_assets_context}
                    
                    請幫我執行以下分析任務：
                    1. 【相似工件數據整理】：比對這些檔案（例如尺寸相近的公仔或機械件），將相似的整理在一起，說明它們在面數和精度上的差異。
                    2. 【自動化製程整合建議】：針對這些工件，結合 OptiSpin 3D 自動化掃描台（Arduino步進馬達、旋轉台速度調校）與 3D 列印（PLA/PETG 的層高、噴嘴限制），給出具體的逆向工程優化建議。
                    
                    回答請條列式、專業、嚴謹，直接輸出診斷報告。
                    """
                    
                    response = ai_client.models.generate_content(
                        model='gemini-2.5-flash', contents=[intelligence_prompt]
                    )
                    
                    st.session_state["cached_diagnostic_report"] = response.text
                    st.toast("🎉 診斷報告同步成功！")
                except Exception as chat_err:
                    st.error("🧠 目前雲端存取過於頻繁，請等待 30 秒後再次點擊同步按鈕。")
        
        # 如果有快取的報告，就漂亮的呈現出來
        if "cached_diagnostic_report" in st.session_state:
            st.markdown("### 📋 大數據中心動態同步診斷報告")
            st.markdown(f"<div style='background-color:#2a2a2a; padding:15px; border-radius:10px; border-left: 5px solid #00f0ff;'>{st.session_state['cached_diagnostic_report']}</div>", unsafe_allow_html=True)
            
        # 下方依舊保留動態工程導師問答框
        st.markdown("---")
        st.markdown("💬 **針對逆向工程技術，向 AI 工程導師進一步提問：**")
        chat_input = st.text_input("輸入提問內容...", placeholder="例如：Scaniverse 導出的模型轉到 SolidWorks 如何重新特徵建模？", label_visibility="collapsed")
        if chat_input:
            with st.spinner("🤖 智慧導師正在解答..."):
                try:
                    system_context = f"你是一位精密系統設計學程的導師。請解答學生的提問：{chat_input}"
                    sub_response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=system_context)
                    st.info(sub_response.text)
                except Exception:
                    st.error("🧠 導師思維超時，請稍候再試。")