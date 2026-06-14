# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [3D 動態雲點模型畫布完全體]
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
    """撈取資料表數據"""
    try:
        url_new = f"{BASE_URL}optispin_assets?select=*&order=created_at.desc"
        res_new = requests.get(url_new, headers=HEADERS)
        if res_new.status_code == 200:
            return res_new.json()
        return []
    except Exception:
        return []

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 數位雙生與自動化數據管理端")

tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

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
            with st.spinner("🚀 正在進行幾何拓撲解析與大數據封裝..."):
                file_bytes = uploaded_file.read()
                file_name = uploaded_file.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                vertices_count = 0
                faces_count = 0
                bounding_box_str = "無法計算"
                area_val, volume_val = 0.0, 0.0
                
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
                        st.warning(f"⚠️ 幾何結構解析受限: {str(mesh_err)}")

                # 將 3D 檔案編碼成 Base64 字串存入資料庫，供前端 3D 畫布隨時調用
                base64_mesh = base64.b64encode(file_bytes).decode('utf-8')

                with st.spinner("🤖 正在調度 Gemini 專家系統進行生成式工藝評估..."):
                    try:
                        prompt_analysis = f"""
                        你是一位精通精密機械加工、3D列印(PLA/PETG)與自動化量測的工業專家。
                        當前系統剛接收到一個自動化 3D 掃描模型，特徵如下：
                        - 檔案名稱: {file_name}
                        - 幾何頂點數: {vertices_count}
                        - 網格面數: {faces_count}
                        - 邊界尺寸: {bounding_box_str}
                        
                        請針對該幾何數據給出結構診斷：
                        1. 推測該工件可能屬於哪類機械零組件？
                        2. 若此工件使用 3D列印 製作，有何結構限制建議？
                        回答請維持在 100 字內，條列式精簡專業。
                        """
                        ai_response = ai_client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_analysis
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
                        "filesize": base64_mesh,  # 🛠️ 把編碼好的 3D 資料大文字塞進 filesize 欄位當作快取
                        "created_at": datetime.now().isoformat()
                    }
                    
                    post_url = f"{BASE_URL}optispin_assets"
                    res_post = requests.post(post_url, headers=HEADERS, json=asset_row)
                    
                    if res_post.status_code in [200, 201, 204]:
                        st.session_state[upload_key] = True
                        st.success(f"🎉 檔案 {file_name} 寫入成功！正在刷新儀表板...")
                        time.sleep(0.8)
                        st.rerun()  
                    else:
                        st.error(f"❌ 寫入失敗，代碼: {res_post.status_code}")
                except Exception as db_err:
                    st.error(f"資料庫通訊阻斷: {str(db_err)}")

    # ------------------------------------------------------------------------------ #
    # 雲端動態搜尋與幾何資產儀表板
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("🔍 3D 雲端資產動態搜尋倉儲")
    search_query = st.text_input("搜尋資產名稱或格式", placeholder="輸入關鍵字進行動態搜尋篩選...", label_visibility="collapsed")
    
    cloud_data = fetch_cloud_assets()
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
                    
                    st.markdown(f"#### 📄 檔案: {item.get('filename', '未命名資產')}")
                    st.caption(f"🕒 上傳時間: {display_time}")
                    
                    # 🛸 核心：3D 實體動態雲點畫布渲染核心
                    mesh_b64 = item.get("filesize", "")
                    if mesh_b64 and len(mesh_b64) > 100:
                        try:
                            # 建立前端 HTML5 網格渲染視窗
                            html_canvas = f"""
                            <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                            <model-viewer 
                                src="data:model/gltf-binary;base64,{mesh_b64}" 
                                alt="OptiSpin 3D Scan" 
                                auto-rotate 
                                camera-controls 
                                background-color="#111111"
                                style="width: 100%; height: 280px; background-color: #1a1a1a; border-radius: 10px;">
                            </model-viewer>
                            """
                            st.components.v1.html(html_canvas, height=290)
                        except Exception as canvas_err:
                            st.caption("🔺 3D 畫布初始化受限")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    
                    st.info(f"**🤖 Gemini 智慧製程評估報告：**\n{item.get('ai_diagnosis', '無診斷數據')}")
                    
                    if st.button(f"🗑️ 銷毀資產", key=f"del_{item.get('id')}_{item.get('filename')}"):
                        try:
                            del_url_new = f"{BASE_URL}optispin_assets?id=eq.{item.get('id')}"
                            requests.delete(del_url_new, headers=HEADERS)
                            st.toast(f"已從雲端銷毀")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as del_err:
                            st.error(f"銷毀指令失敗: {str(del_err)}")
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)
        else:
            st.info("💡 沒有符合當前搜尋關鍵字的 3D 資產。")
    else:
        st.info("📦 當前雲端大數據倉儲尚無任何資產，請於上方上傳首個 3D 模型檔案。")

# ------------------------------------------------------------------------------ #
# 分頁二：Scaniverse 智慧診斷與多模態通訊日誌
# ------------------------------------------------------------------------------ #
with tab2:
    st.subheader("📸 全自動點雲最佳化與 AI 多模態互動")
    chat_input = st.text_input("📝 向大數據中心 AI 提問", placeholder="例如：如何提升 Scaniverse 機械件掃描清澈度？")
    if chat_input:
        with st.spinner("🤖 正在將多模態日誌交由 Gemini 頂級思維矩陣解析..."):
            try:
                system_context = "你是一位在逢甲大學精密系統設計學程服務的 AI 智慧工程導師。請針對逆向工程、Arduino步進馬達控制、PLC、CNC 程式碼給予專業解答。"
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[system_context, chat_input]
                )
                st.markdown("### 🤖 智慧導師診斷回覆：")
                st.write(response.text)
            except Exception as chat_err:
                st.error(f"🧠 思維矩陣連線超時: {str(chat_err)}")