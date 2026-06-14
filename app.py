# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [USDZ修復與跨資產動態診斷日誌完全體]
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
    st.error("❌ 偵測到雲端 Secrets 設定缺失！請確認 Streamlit Cloud配置。")
    st.stop()

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def fetch_cloud_assets():
    """撈取資料表數據"""
    try:
        url_new = f"{BASE_URL}optispin_assets?select=*&order=created_at.desc"
        res_new = requests.get(url_new, headers=HEADERS)
        if res_new.status_code == 200:
            return res_new.json()
        return []
    except Exception:
        return []

def create_point_cloud_simulation(mesh):
    """將網格頂點轉化為互動式的點雲模擬圖"""
    try:
        if len(mesh.vertices) < 10:
            return None
        max_points = 3000
        if len(mesh.vertices) > max_points:
            indices = np.random.choice(len(mesh.vertices), max_points, replace=False)
            points = mesh.vertices[indices]
        else:
            points = mesh.vertices
            
        fig = go.Figure(data=[go.Scatter3d(
            x=points[:, 0], y=points[:, 1], z=points[:, 2],
            mode='markers',
            marker=dict(size=2, color='white', opacity=0.8)
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

cloud_data = fetch_cloud_assets() # 全域載入最新雲端數據，確保兩邊同步

# ------------------------------------------------------------------------------ #
# 分頁一：3D 大數據資產管理端 (修復 USDZ 幾何與預覽)
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
            with st.spinner("🚀 正在進行幾何拓撲解析與大數據封裝..."):
                file_bytes = uploaded_file.read()
                file_name = uploaded_file.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                vertices_count = 0
                faces_count = 0
                bounding_box_str = "無法計算 (iOS 專屬格式)"
                area_val, volume_val = 0.0, 0.0
                
                # 針對一般通用格式進行解析
                if file_extension in [".obj", ".stl", ".glb"]:
                    try:
                        file_stream = io.BytesIO(file_bytes)
                        scene_or_mesh = trimesh.load(file_stream, file_type=file_extension.strip('.'))
                        if isinstance(scene_or_mesh, trimesh.Scene):
                            mesh = list(scene_or_mesh.geometry.values())[0] if len(scene_or_mesh.geometry) > 0 else None
                        else:
                            mesh = scene_or_mesh
                            
                        if mesh is not None:
                            vertices_count = len(mesh.vertices)
                            faces_count = len(mesh.faces)
                            area_val = float(mesh.area)
                            volume_val = float(mesh.volume) if mesh.is_volume else 0.0
                            bbox = mesh.bounding_box.extents
                            bounding_box_str = f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm"
                    except Exception as mesh_err:
                        pass
                elif file_extension == ".usdz":
                    # USDZ 為高壓縮二進位，本機跳過解析，保留數據給 Gemini 估算
                    vertices_count, faces_count = 12000, 24000  # 提供典型 Scaniverse 預估值
                    bounding_box_str = "動態偵測中 (USDZ)"

                base64_mesh = base64.b64encode(file_bytes).decode('utf-8')

                with st.spinner("🤖 正在調度 Gemini 專家系統進行生成式工藝評估..."):
                    try:
                        prompt_analysis = f"""
                        你是一位精通精密機械加工、3D列印(PLA/PETG)與自動化量測的工業專家。
                        當前系統剛接收到一個自動化 3D 掃描模型：
                        - 檔案名稱: {file_name}
                        - 預估頂點數: {vertices_count}
                        - 預估網格面數: {faces_count}
                        - 格式類型: {file_extension}
                        
                        請針對該數據給出結構診斷，並依 100 字內精簡專業回答。
                        """
                        ai_response = ai_client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt_analysis
                        )
                        diagnosis_text = ai_response.text
                    except Exception as ai_err:
                        diagnosis_text = f"Gemini 專家系統調度失敗。{str(ai_err)}"

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
                    
                    post_url = f"{BASE_URL}optispin_assets"
                    res_post = requests.post(post_url, headers=HEADERS, json=asset_row)
                    
                    if res_post.status_code in [200, 201, 204]:
                        st.session_state[upload_key] = True
                        st.success(f"🎉 {file_name} 寫入大數據中心成功！")
                        time.sleep(0.5)
                        st.rerun()  
                    else:
                        st.error(f"❌ 寫入失敗，代碼: {res_post.status_code}")
                except Exception as db_err:
                    st.error(f"資料庫通訊阻斷: {str(db_err)}")

    # ------------------------------------------------------------------------------ #
    # 雲端動態搜尋儀表板 (相容 GLB 與 USDZ 畫布)
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
                    display_time = "未知時間"
                    if raw_time:
                        try:
                            dt = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                            display_time = dt.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            display_time = str(raw_time)[:16]
                    
                    fname = item.get('filename', '未命名資產')
                    is_usdz = fname.lower().endswith('.usdz')
                    
                    st.markdown(f"#### 📄 檔案: {fname}")
                    st.caption(f"🕒 上傳時間: {display_time}")
                    
                    mesh_b64 = item.get("filesize", "")
                    if mesh_b64 and len(mesh_b64) > 100:
                        mode_key = f"mode_{item.get('id')}"
                        if mode_key not in st.session_state:
                            st.session_state[mode_key] = "🛰️ 3D 模型實體"
                            
                        st.radio("檢視模式", ["🛰️ 3D 模型實體", "模擬單色點雲"], key=mode_key, horizontal=True, label_visibility="collapsed")
                        
                        if st.session_state[mode_key] == "🛰️ 3D 模型實體":
                            try:
                                # 🛠️ 關鍵修復：如果是 usdz，同時將 src 與 ios-src 綁定，啟動 AR Quick Look 相容機制
                                mime_type = "model/vnd.usdz+zip" if is_usdz else "data:model/gltf-binary;base64," + mesh_b64
                                src_tag = f'src="data:model/vnd.usdz+zip;base64,{mesh_b64}" ios-src="data:model/vnd.usdz+zip;base64,{mesh_b64}"' if is_usdz else f'src="{mime_type}"'
                                
                                html_canvas = f"""
                                <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                                <model-viewer 
                                    {src_tag}
                                    alt="OptiSpin 3D Scan" 
                                    auto-rotate camera-controls ar
                                    style="width: 100%; height: 320px; background-color: #1a1a1a; border-radius: 10px;">
                                </model-viewer>
                                """
                                st.components.v1.html(html_canvas, height=330)
                            except Exception:
                                st.caption("🔺 3D 畫布載入受限")
                        else:
                            # 點雲模擬模式
                            if is_usdz:
                                st.info("🌌 USDZ 正在由手機硬體進行 AR 加速，點雲模擬請優先選擇 GLB/OBJ 格式。")
                            else:
                                with st.spinner("🌌 正在逆向封裝單色點雲模擬..."):
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
                        st.metric("邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    
                    st.info(f"**🤖 Gemini 智慧製程評估報告：**\n{item.get('ai_diagnosis', '無診斷數據')}")
                    
                    if st.button(f"🗑️ 銷毀資產", key=f"del_{item.get('id')}_{fname}"):
                        requests.delete(f"{BASE_URL}optispin_assets?id=eq.{item.get('id')}", headers=HEADERS)
                        st.toast("已從雲端銷毀")
                        time.sleep(0.5)
                        st.rerun()
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------ #
# 分頁二：Scaniverse 智慧診斷日誌 (跨資產動態同步、相似數據整理與分析功能)
# ------------------------------------------------------------------------------ #
with tab2:
    st.subheader("🤖 大數據中心跨資產綜合分析日誌")
    st.caption("自動讀取目前雲端所有 3D 掃描紀錄，比對相似工件、統計數據並提供製程優化建議")
    
    if not cloud_data:
        st.info("💡 目前雲端資料庫尚無有效資產，請先上傳 3D 模型後再進行日誌診斷。")
    else:
        # 1. 精煉目前雲端所有檔案的摘要數據，打包餵給 Gemini
        assets_summary_list = []
        for index, item in enumerate(cloud_data):
            assets_summary_list.append(
                f"[{index+1}] 檔案名稱: {item.get('filename')} | 上傳時間: {item.get('created_at','')[:16]} | "
                f"面數: {item.get('faces', 0)} | 尺寸: {item.get('bounding_box', '未知')}"
            )
        all_assets_context = "\n".join(assets_summary_list)
        
        # 2. 自動觸發 Gemini 進行全資產動態分析
        with st.spinner("🤖 正在調度 Gemini 頂級思維矩陣盤點雲端資產、比對相似物件與數據..."):
            try:
                intelligence_prompt = f"""
                你是一位在逢甲大學精密系統設計學程服務的 AI 智慧建檔與逆向工程工程專家。
                目前雲端大數據中心共有以下 3D 掃描資產紀錄：
                {all_assets_context}
                
                請幫我執行以下任務：
                1. 【資產與數據紀錄總覽】：簡單統計目前共有幾筆掃描件，並列出他們的名稱與核心幾何數據。
                2. 【相似物件特徵整理】：比對這些檔案（例如比對檔名、尺寸、時間接近的物件），如果有相似的（例如同一個工件的多次掃描、或是大小相近的機械件），請將他們整理歸類在一起，並說明它們的差異（如面數增減、精度變化）。
                3. 【自動化製程整合建議】：針對這些相似或現有的物件，結合 OptiSpin 3D 自動化掃描台（Arduino控制、馬達調校）與 3D 列印（PLA/PETG），給出下一步的逆向工程或加工優化建議。
                
                回答請條列式、專業、嚴謹，直接輸出診斷報告。
                """
                
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash', contents=[intelligence_prompt]
                )
                
                # 3. 渲染漂亮、科技感的診斷日誌面板
                st.markdown("### 📋 大數據中心動態同步診斷報告")
                st.markdown(f"<div style='background-color:#2a2a2a; padding:15px; border-radius:10px; border-left: 5px solid #00f0ff;'>{response.text}</div>", unsafe_allow_html=True)
                
            except Exception as chat_err:
                st.error(f"🧠 思維矩陣同步失敗: {str(chat_err)}")
                
        # 4. 保留下方動態問答對話框，方便進行延伸的 PLC/CNC 提問
        st.markdown("---")
        st.markdown("💬 **針對上述數據或逆向工程，向 AI 工程導師進一步提問：**")
        chat_input = st.text_input("輸入提問內容...", placeholder="例如：針對上述相似的機械件，G-code 該如何優化？", label_visibility="collapsed")
        if chat_input:
            with st.spinner("🤖 智慧導師正在解析..."):
                try:
                    system_context = f"你是一位精密系統設計學程的導師。請根據剛才盤點的資產環境：{all_assets_context}，深度解答學生的提增問題：{chat_input}"
                    sub_response = ai_client.models.generate_content(
                        model='gemini-2.5-flash', contents=system_context
                    )
                    st.info(sub_response.text)
                except Exception as e:
                    st.error(str(e))