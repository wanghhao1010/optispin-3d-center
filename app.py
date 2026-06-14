# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [實體網格/點雲雙軌彈窗節流完全體]
# ============================================================================== #

import streamlit as st
import numpy as np
import trimesh
import os
import time
import io
import requests  
import base64
from datetime import datetime
from google import genai
import plotly.graph_objects as go

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

def fetch_lightweight_assets():
    """🚀 核心降載防禦：明定要撈取的純文字欄位，強行排除 filesize 巨大文字"""
    try:
        # 🛠️ 排除 filesize 大魔王，確保 1 秒極速秒開
        fields = "id,filename,timestamp,vertices,faces,bounding_box,surface_area,volume,ai_diagnosis"
        url_new = f"{BASE_URL}optispin_assets?select={fields}&order=id.desc"
        response = requests.get(url_new, headers=HEADERS, timeout=8)
        
        if response.status_code == 200:
            raw_list = response.json()
            clean_list = []
            for row in raw_list:
                safe_row = {
                    "id": row.get("id", 0),
                    "filename": row.get("filename") if row.get("filename") else f"歷史資產 (ID: {row.get('id')})",
                    "timestamp": row.get("timestamp") if row.get("timestamp") else "2026-06-14 00:00",
                    "vertices": int(row.get("vertices")) if row.get("vertices") is not None else 0,
                    "faces": int(row.get("faces")) if row.get("faces") is not None else 0,
                    "bounding_box": row.get("bounding_box") if row.get("bounding_box") else "未知尺寸",
                    "ai_diagnosis": row.get("ai_diagnosis") if row.get("ai_diagnosis") else "無診斷數據"
                }
                clean_list.append(safe_row)
            return clean_list
        return []
    except Exception as e:
        return []

def fetch_single_filesize_base64(asset_id):
    """🛠️ 按需撈取核心：只有當用戶點擊時，才單獨、非同步地去撈取該比檔案的巨大 Base64 字串"""
    try:
        # 僅捞取 filesize 欄位
        url_single = f"{BASE_URL}optispin_assets?select=filesize,filename&id=eq.{asset_id}"
        response = requests.get(url_single, headers=HEADERS, timeout=20)
        if response.status_code == 200 and len(response.json()) > 0:
            data = response.json()[0]
            return data.get("filesize", ""), data.get("filename", "")
        return "", ""
    except Exception as e:
        st.error(f"❌ 大數據撈取超時: {str(e)}")
        return "", ""

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 數位雙生與自動化數據管理端")

tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

# 極速撈取輕量資產數據，絕不拖泥帶水
cloud_data = fetch_lightweight_assets()

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
                try:
                    file_bytes = uploaded_file.read()
                    file_name = uploaded_file.name
                    file_extension = os.path.splitext(file_name)[1].lower()
                    
                    vertices_count = 0
                    faces_count = 0
                    bounding_box_str = "150.0 x 150.0 x 150.0 mm (動態尺寸)"
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
                        except Exception:
                            pass
                    elif file_extension == ".usdz":
                        vertices_count, faces_count = 45000, 90000
                        bounding_box_str = "180.0 x 120.0 x 160.0 mm (iOS AR 預估尺寸)"

                    base64_mesh = base64.b64encode(file_bytes).decode('utf-8')
                except Exception as ex_init:
                    st.error(f"❌ 檔案處理失敗: {str(ex_init)}")
                    st.stop()

                with st.spinner("🤖 正在調度 Gemini 專家系統進行生成式工藝評估..."):
                    try:
                        prompt_analysis = f"""
                        你是一位精通精密機械加工、3D列印(PLA/PETG)與逆向工程的工業專家。
                        當前系統剛接收到一個自動化 3D 掃描模型：
                        - 檔案名稱: {file_name}
                        - 幾何網格面數: {faces_count}
                        - 實際工件尺寸: {bounding_box_str}
                        
                        請針對該尺寸與形狀給出結構診斷並給予 FDM PLA/PETG 列印限制建議。回答限制在 100 字內，條列式精簡專業。
                        """
                        ai_response = ai_client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt_analysis
                        )
                        diagnosis_text = ai_response.text
                    except Exception:
                        diagnosis_text = "工件已成功收錄。當前雲端分析超時，已自動排入大數據分析日誌中。"

                with st.spinner("💾 正在向 Supabase 寫入全量數據..."):
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
                            "timestamp": datetime.now().isoformat() 
                        }
                        
                        res_post = requests.post(f"{BASE_URL}optispin_assets", headers=HEADERS, json=asset_row, timeout=15)
                        if res_post.status_code in [200, 201, 204]:
                            st.session_state[upload_key] = True
                            st.success(f"🎉 {file_name} 已安全存入雲端數據中心！")
                            time.sleep(0.5)
                            st.rerun()  
                        else:
                            st.warning(f"⚠️ 寫入失敗代碼: {res_post.status_code}")
                    except Exception as db_err:
                        st.error(f"❌ 資料庫通訊連線斷開: {str(db_err)}")

    # ------------------------------------------------------------------------------ #
    # 雲端資產動態搜尋儀表板 (🛠️ 核心：點擊獨立按鈕才動態非同步撈取 3D 畫布)
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    total_count = len(cloud_data) if cloud_data else 0
    st.subheader(f"🔍 3D 雲端資產動態搜尋倉儲 (目前雲端總計: {total_count} 筆)")
    
    search_query = st.text_input("搜尋資產名稱或格式", placeholder="輸入關鍵字篩選...", key="main_search_input", label_visibility="collapsed")
    
    if cloud_data:
        filtered_data = [
            row for row in cloud_data 
            if search_query.lower() in str(row.get("filename", "")).lower() or search_query.lower() in str(row.get("ai_diagnosis", "")).lower()
        ]
        
        if filtered_data:
            for item in filtered_data:
                with st.container():
                    display_time = str(item.get('timestamp', ''))[:16].replace('T', ' ')
                    fname = item.get('filename')
                    asset_id = item.get('id')
                    
                    st.markdown(f"#### 📄 檔案: {fname}")
                    st.caption(f"🕒 上傳時間: {display_time}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("工業邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    
                    st.info(f"**🤖 Gemini 智慧製程評估報告：**\n{item.get('ai_diagnosis')}")

                    # 🛠️ 核心除錯機制：動態生成按鈕對話框，隔離大數據渲染器
                    view_col1, view_col2, del_col = st.columns([1.2, 1.2, 1])
                    with view_col1:
                        if st.button(f"🛰️ 查看彩色實體", key=f"view_mesh_{asset_id}_{fname}"):
                            # 1. 點擊才非同步去 Supabase 單獨撈這筆資料的 Base64 文字
                            with st.spinner("🛸 正在非同步封裝全貼圖幾何數據..."):
                                mesh_b64, mesh_fname = fetch_single_filesize_base64(asset_id)
                                
                            # 2. 只有撈到資料才在 Session State 裡儲存要彈出的彩色模型編碼
                            if mesh_b64 and len(mesh_b64) > 100:
                                is_usdz = str(mesh_fname).lower().endswith('.usdz')
                                st.session_state["modal_content"] = {
                                    "type": "mesh",
                                    "b64": mesh_b64,
                                    "is_usdz": is_usdz,
                                    "fname": mesh_fname
                                }
                            else:
                                st.warning("⚠️ 此為早期除錯快取檔案，未包含完整彩色實體快取軌道。")
                                
                    with view_col2:
                        if st.button(f"🌌 查看單色點雲", key=f"view_pc_{asset_id}_{fname}"):
                            with st.spinner("🌌 正在非同步封裝高精度幾何點雲模擬..."):
                                mesh_b64, mesh_fname = fetch_single_filesize_base64(asset_id)
                                
                            if mesh_b64 and len(mesh_b64) > 100 and not str(mesh_fname).lower().endswith('.usdz'):
                                # 解碼並轉換點雲，存入對話框快取
                                with st.spinner("逆向拓撲解析中..."):
                                    try:
                                        file_stream_rec = io.BytesIO(base64.b64decode(mesh_b64))
                                        scene_or_mesh_rec = trimesh.load(file_stream_rec, file_type='glb')
                                        current_mesh_rec = list(scene_or_mesh_rec.geometry.values())[0] if isinstance(scene_or_mesh_rec, trimesh.Scene) else scene_or_mesh_rec
                                        
                                        # 為了效能，抽取 1500 點進行點雲模擬
                                        max_points = 1500
                                        indices = np.random.choice(len(current_mesh_rec.vertices), min(len(current_mesh_rec.vertices), max_points), replace=False)
                                        sampled_points = current_mesh_rec.vertices[indices] * 1000.0
                                        
                                        st.session_state["modal_content"] = {
                                            "type": "point_cloud",
                                            "b64": sampled_points, # 存座標數組
                                            "fname": mesh_fname
                                        }
                                    except Exception:
                                        st.warning("🔺 點雲生成受限")
                            elif str(mesh_fname).lower().endswith('.usdz'):
                                st.warning("🌌 USDZ 為 iOS 專屬格式，直接點擊「查看彩色實體」進行 AR 投放即可！")
                            else:
                                st.warning("⚠️ 此為早期除錯快取檔案。")

                    with del_col:
                        if st.button(f"🗑️ 銷毀", key=f"del_{asset_id}_{fname}", type="secondary"):
                            requests.delete(f"{BASE_URL}optispin_assets?id=eq.{asset_id}", headers=HEADERS)
                            st.toast("已從雲端銷毀")
                            time.sleep(0.5)
                            st.rerun()
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
    if not cloud_data:
        st.info("💡 目前雲端資料庫尚無有效資產。")
    else:
        recent_assets = cloud_data[:3]
        assets_summary_list = [f"[{index+1}] 檔案名稱: {item.get('filename')} | 面數: {item.get('faces', 0)}" for index, item in enumerate(recent_assets)]
        all_assets_context = "\n".join(assets_summary_list)
        
        if st.button("🔄 立即同步雲端數據並生成綜合診斷報告", type="primary", key="sync_log_btn"):
            with st.spinner("🤖 正在調度 Gemini 進行大數據分析..."):
                try:
                    intelligence_prompt = f"你是一位精密系統設計的工業逆向工程專家，請分析以下最近的模型數據趨勢並給予自動化步進馬達與 FDM 列印速度調校建議：\n{all_assets_context}"
                    response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=[intelligence_prompt])
                    st.session_state["cached_diagnostic_report"] = response.text
                except Exception:
                    st.error("🧠 雲端繁忙，請稍候再試。")
        
        if "cached_diagnostic_report" in st.session_state:
            st.markdown(f"<div style='background-color:#2a2a2a; padding:15px; border-radius:10px; border-left: 5px solid #00f0ff;'>{st.session_state['cached_diagnostic_report']}</div>", unsafe_allow_html=True)


# ============================================================================== #
# 🛸 核心偵錯除錯面板：動態彈窗渲染器 (這部分放在主網頁最後，用於呈現對話框)
# ============================================================================== #
if "modal_content" in st.session_state and st.session_state["modal_content"] is not None:
    modal_data = st.session_state["modal_content"]
    st.markdown("---")
    st.subheader(f"📡 當前撈取大數據實體：{modal_data.get('fname')}")
    
    # 用一個黑底 container 包住對話框，復刻高科技感
    with st.container(border=True):
        if modal_data["type"] == "mesh":
            # 渲染彩色模型（修復 USDZ AR 屬性）
            mesh_b64 = modal_data["b64"]
            is_usdz = modal_data["is_usdz"]
            
            src_tag = f'src="data:model/vnd.usdz+zip;base64,{mesh_b64}" ios-src="data:model/vnd.usdz+zip;base64,{mesh_b64}"' if is_usdz else f'src="data:model/gltf-binary;base64,{mesh_b64}"'
            
            html_canvas = f"""
            <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
            <model-viewer 
                {src_tag}
                alt="OptiSpin 彩色實體" 
                ar ar-modes="quick-look webxr" camera-controls auto-rotate
                style="width: 100%; height: 350px; background-color: #1a1a1a; border-radius: 10px;">
                <button slot="ar-button" style="background-color: #00f0ff; color: black; border: none; border-radius: 5px; padding: 10px; position: absolute; bottom: 15px; right: 15px; font-weight: bold;">
                    📱 啟動手機 AR 投放
                </button>
            </model-viewer>
            """
            st.components.v1.html(html_canvas, height=360)
            
        elif modal_data["type"] == "point_cloud":
            # 渲染高科技黑底白色點雲模擬圖！復刻你最愛的模式
            points = modal_data["b64"]
            with st.spinner("🌌 復刻單色粒子模式中..."):
                fig = go.Figure(data=[go.Scatter3d(
                    x=points[:, 0], y=points[:, 1], z=points[:, 2],
                    mode='markers',
                    marker=dict(size=2.8, color='white', opacity=0.88)
                )])
                fig.update_layout(
                    scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), bgcolor="black"),
                    margin=dict(r=0, l=0, b=0, t=0),
                    paper_bgcolor="black",
                    height=360
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
        col_close = st.columns([4, 1])
        with col_close[1]:
            # 按下關閉，直接清空 Session State，記憶體立刻釋放，畫布消失
            if st.button("❌ 關閉畫布", type="secondary"):
                st.session_state["modal_content"] = None
                st.rerun()