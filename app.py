# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [資料庫連線完全體]
# ============================================================================== #

import streamlit as st
import numpy as np
import trimesh
import os
import time
import io
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
from google import genai
from google.genai import types

# 1. 系統網頁頂層基礎配置 (徹底拔除會導致破圖的裝飾)
st.set_page_config(
    page_title="OptiSpin 3D 控制中心",
    page_icon="🛸",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 初始化刪除 Session 狀態
if "optimistic_deleted_ids" not in st.session_state:
    st.session_state.optimistic_deleted_ids = set()

# 2. 安全讀取雲端環境變數 (Secrets)
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    
    # 初始化雲端資料庫與 AI 客戶端
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error("❌ 偵測到雲端 Secrets 設定缺失！請確認 Streamlit Cloud 的 Advanced Settings 已正確配置。")
    st.stop()

# 雲端資料庫儲存桶 (Bucket) 名稱定義
BUCKET_MODELS = "saved-models"

# 3. 雲端資料庫與資料核心交互工人
def fetch_cloud_assets():
    """從 Supabase Database 撈取所有未被標記刪除的 3D 大數據資產"""
    try:
        # 修正表格名稱為正確的關聯表，並改用通用時間排序避開不存在的欄位
        response = supabase.table("optispin_assets").select("*").order("created_at", descending=True).execute()
        return [row for row in response.data if row["id"] not in st.session_state.optimistic_deleted_ids]
    except Exception as e:
        # 如果 optispin_assets 讀不到，自動切換至備用表格名稱
        try:
            response = supabase.table("models").select("*").execute()
            return response.data
        except:
            st.error(f"⚠️ 無法讀取資料庫資產，請確認 Supabase Table 名稱是否正確: {str(e)}")
            return []

def upload_to_supabase_storage(bucket_name: str, file_path: str, file_data: bytes):
    """將二進位檔案資料直接儲存至 Supabase Storage"""
    try:
        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_data,
            file_options={"cache-control": "3600", "upsert": "true"}
        )
        return True
    except Exception as e:
        st.error(f"💥 Storage 儲存失敗: {str(e)}")
        return False

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

# 頂部控制中心標題區塊 (乾淨俐落)
st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 數位雙生與自動化數據管理端")

# 功能主分頁切換介面
tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

# ------------------------------------------------------------------------------ #
# 分頁一：3D 大數據資產管理端 (上傳、網格解析、動態檢索)
# ------------------------------------------------------------------------------ #
with tab1:
    st.subheader("📥 點擊或拖曳上傳全新 3D 掃描模型")
    uploaded_file = st.file_uploader(
        "支援工業點雲與網格幾何格式", 
        type=["glb", "obj", "usdz", "stl"], 
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        with st.spinner("🚀 正在進行幾何拓撲解析與雲端備份..."):
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
                    st.warning(f"⚠️ 幾何核心成功備份檔案，但拓撲結構解析受限: {str(mesh_err)}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{file_name}"
            success = upload_to_supabase_storage(BUCKET_MODELS, unique_filename, file_bytes)
            
            if success:
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
                        diagnosis_text = f"Gemini 專家系統調度失敗。診斷代碼: {str(ai_err)}"

                try:
                    asset_row = {
                        "filename": file_name,
                        "storage_path": unique_filename,
                        "vertices": vertices_count,
                        "faces": faces_count,
                        "bounding_box": bounding_box_str,
                        "surface_area": area_val,
                        "volume": volume_val,
                        "ai_diagnosis": diagnosis_text,
                        "created_at": datetime.now().isoformat()
                    }
                    # 嘗試寫入，若表格名稱不對會自動捕捉
                    supabase.table("optispin_assets").insert(asset_row).execute()
                    st.success(f"🎉 檔案 {file_name} 雲端大數據資產配置成功！")
                    time.sleep(1)
                    st.rerun()
                except Exception as db_err:
                    st.error(f"資料庫寫入阻斷，請檢查 Supabase Table 名稱: {str(db_err)}")

    # ------------------------------------------------------------------------------ #
    # 雲端動態搜尋與幾何資產儀表板
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    st.subheader("🔍 3D 雲端資產動態搜尋倉儲")
    search_query = st.text_input("搜尋資產名稱或格式", placeholder="輸入關鍵字進行動態搜尋篩選...")
    
    cloud_data = fetch_cloud_assets()
    if cloud_data:
        filtered_data = [
            row for row in cloud_data 
            if search_query.lower() in row.get("filename", "").lower() or search_query.lower() in row.get("ai_diagnosis", "").lower()
        ]
        
        if filtered_data:
            for item in filtered_data:
                with st.container():
                    st.markdown(f"#### 📄 檔案: {item.get('filename', '未命名資產')}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    
                    st.info(f"**🤖 Gemini 智慧製程評估報告：**\n{item.get('ai_diagnosis', '無診斷數據')}")
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
    chat_input = st.text_input("📝 向大數據中心 AI 提問 (例如：如何提升 Scaniverse 機械件掃描清澈度？)")
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