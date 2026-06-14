# ============================================================================== #
# 🛸 OptiSpin 3D 智慧圖檔大數據中心 - [通用網頁渲染與預覽快取完全體]
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

# 🛠️ 核心：初始化用戶 Session State 中的預覽快取 (如果不存在)
# 結構：{"asset_id_mode": "base64_string"}
if "preview_cache" not in st.session_state:
    st.session_state["preview_cache"] = {}

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
    """撈取純文字欄位"""
    try:
        fields = "id,filename,timestamp,vertices,faces,bounding_box,surface_area,volume,ai_diagnosis"
        url_new = f"{BASE_URL}optispin_assets?select={fields}&order=id.desc"
        response = requests.get(url_new, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

def fetch_single_filesize_base64(asset_id):
    """🛠️ 按需撈取：從快取或資料庫單獨撈取巨大 Base64 字串"""
    # 1. 檢查快取中是否已有 GLB 基礎數據 (用於點雲模式)
    cache_key_glb = f"{asset_id}_mesh"
    if cache_key_glb in st.session_state["preview_cache"]:
        return st.session_state["preview_cache"][cache_key_glb], "cached_file.glb"
    
    try:
        url_single = f"{BASE_URL}optispin_assets?select=filesize,filename&id=eq.{asset_id}"
        response = requests.get(url_single, headers=HEADERS, timeout=20)
        if response.status_code == 200 and len(response.json()) > 0:
            data = response.json()[0]
            mesh_b64 = data.get("filesize", "")
            mesh_fname = data.get("filename", "")
            
            # 2. 將撈到的數據存入 GLB 快取
            if mesh_b64 and not str(mesh_fname).lower().endswith('.usdz'):
                st.session_state["preview_cache"][cache_key_glb] = mesh_b64
                
            return mesh_b64, mesh_fname
        return "", ""
    except Exception:
        return "", ""

# ============================================================================== #
# 🛰️ 核心通用網頁渲染器 html 生成器 (Three.js 核心)
# ============================================================================== #
def generate_universal_renderer_html(asset_b64, filename, height=350):
    """
    🛠️ 替換原本的 model-viewer，建立一個基於 Three.js 的通用網頁渲染器。
    它能自動識別並原生渲染 GLB 和 USDZ 的 data URI。
    """
    is_usdz = str(filename).lower().endswith('.usdz')
    data_uri = f"data:model/vnd.usdz+zip;base64,{asset_b64}" if is_usdz else f"data:model/gltf-binary;base64,{asset_b64}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OptiSpin Universal Renderer</title>
        <style>
            body {{ margin: 0; padding: 0; background-color: #1a1a1a; overflow: hidden; }}
            #web_canvas {{ width: 100%; height: {height}px; }}
            button {{ 
                background-color: #00f0ff; color: black; border: none; border-radius: 5px; 
                padding: 10px; position: absolute; bottom: 15px; right: 15px; font-weight: bold; cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <canvas id="web_canvas"></canvas>
        <button id="ar_btn" style="display:none;">📱 iPhone 空間 AR 投放</button>
        
        <script src="https://cdn.jsdelivr.net/npm/three@0.149.0/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.149.0/examples/js/loaders/GLTFLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.149.0/examples/js/loaders/USDZLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.149.0/examples/js/controls/OrbitControls.js"></script>
        
        <script>
            const canvas = document.getElementById('web_canvas');
            const renderer = new THREE.WebGLRenderer({{canvas: canvas, antialias: true, alpha: true}});
            renderer.setSize(canvas.clientWidth, canvas.clientHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(75, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 0.5);
            
            const controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            
            // 環境與方向光，確保模型亮度
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
            directionalLight.position.set(1, 1, 1).normalize();
            scene.add(directionalLight);
            
            const ar_btn = document.getElementById('ar_btn');
            
            function renderModel(model) {{
                scene.add(model);
                // 自動縮放與置中模型
                const box = new THREE.Box3().setFromObject(model);
                const size = box.getSize(new THREE.Vector3());
                const center = box.getCenter(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 0.4 / maxDim;
                model.scale.set(scale, scale, scale);
                model.position.sub(center.multiplyScalar(scale));
            }}

            const data_uri = "{data_uri}";
            
            if ({'true' if is_usdz else 'false'}) {{
                const loader = new USDZLoader();
                loader.load(data_uri, function (usdz_scene) {{
                    renderModel(usdz_scene);
                    
                    // 特殊處理：如果在 iOS 端且為 USDZ，亮出 AR 按鈕
                    if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {{
                        ar_btn.style.display = 'block';
                        ar_btn.onclick = () => {{
                            const ar_url = data_uri.replace('data:model/vnd.usdz+zip;base64,', 'quicklook-usdz:');
                            window.location.href = ar_url;
                        }};
                    }}
                }});
            }} else {{
                const loader = new GLTFLoader();
                loader.load(data_uri, function (gltf) {{
                    renderModel(gltf.scene);
                }});
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();
            
            // 監聽畫布縮放
            window.addEventListener('resize', () => {{
                camera.aspect = canvas.clientWidth / canvas.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(canvas.clientWidth, canvas.clientHeight);
            }});
        </script>
    </body>
    </html>
    """
    return html_content

# ============================================================================== #
# 🎨 核心主網頁前端 UI 渲染
# ============================================================================== #

st.title("🛸 OptiSpin 3D 控制中心")
st.caption("逢甲大學 精密系統設計學位學程 - 3D 通用渲染與預覽快取完全體")

tab1, tab2 = st.tabs(["📊 3D 大數據資產區", "🤖 Scaniverse 診斷日誌"])

# 瞬間撈取純文字資產數據
cloud_data = fetch_lightweight_assets()

# ------------------------------------------------------------------------------ #
# 分頁一：3D 大數據資產管理端
# ------------------------------------------------------------------------------ #
with tab1:
    st.subheader("📥 點擊或拖曳上傳全新 3D 掃描模型")
    uploaded_file = st.file_uploader(
        "支援工業幾何格式 (GLB/USDZ/OBJ/STL)", 
        type=["glb", "obj", "usdz", "stl"], 
        label_visibility="collapsed"
    )
    
    # ... (上傳與 Gemini 分析邏輯與原本相同，省略以縮短代碼)
    if uploaded_file is not None:
        # ... 原本的 trimesh 解析、ai 分析、base64 編碼、supabase 寫入邏輯
        # 寫入成功後記得執行 st.rerun()
        pass

    # ------------------------------------------------------------------------------ #
    # 雲端資產動態搜尋儀表板 (🛠️ 核心：「所見即所得」與預覽快取整合)
    # ------------------------------------------------------------------------------ #
    st.markdown("---")
    total_count = len(cloud_data) if cloud_data else 0
    st.subheader(f"🔍 3D 雲端資產動態搜尋倉儲 (雲端總計: {total_count} 筆)")
    
    search_query = st.text_input("搜尋資產名稱或格式", placeholder="輸入關鍵字篩選...", key="main_search_input", label_visibility="collapsed")
    
    if cloud_data:
        # ... 原本的 filtered_data 邏輯
        filtered_data = [
            row for row in cloud_data 
            if search_query.lower() in str(row.get("filename", "")).lower() or search_query.lower() in str(row.get("ai_diagnosis", "")).lower()
        ]
        
        if filtered_data:
            for item in filtered_data:
                with st.container():
                    fname = item.get('filename')
                    asset_id = item.get('id')
                    raw_time = item.get('timestamp', '')
                    display_time = str(raw_time)[:16].replace('T', ' ')
                    
                    st.markdown(f"#### 📄 檔案: {fname}")
                    st.caption(f"🕒 上傳時間: {display_time}")
                    
                    # 💡 核心優化：所見即所得的預覽 Container
                    # 建立一個與檔案 ID 關聯的 container，確保預覽出現在這筆資產下方
                    preview_container = st.container()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("網格面數 (Faces)", f"{item.get('faces', 0):,}")
                    with col2:
                        st.metric("工業邊界包絡體 (Bounding Box)", item.get('bounding_box', '無法計算'))
                    st.info(f"🤖 Gemini 智慧製程評估：\n{item.get('ai_diagnosis')}")

                    # 雙軌按鈕發射器
                    view_col1, view_col2, del_col = st.columns([1.2, 1.2, 1])
                    with view_col1:
                        # 用於辨識快取模式的 Key
                        mesh_cache_key = f"{asset_id}_mesh"
                        if st.button(f"🛰️ 實體全貼圖預覽", key=f"view_mesh_{asset_id}_{fname}"):
                            with st.spinner("🛸 封裝全貼圖幾何數據... (快取檢查中)"):
                                mesh_b64, mesh_fname = fetch_single_filesize_base64(asset_id)
                                if mesh_b64:
                                    # 🛠️ 將成功的預覽 Base64 和文件名存入快取
                                    st.session_state["preview_cache"][mesh_cache_key] = mesh_b64
                                    st.success(f"🎉 快取已記住，下次開啟即秒開！")
                                else:
                                    st.warning("⚠️ 此為空殼資產。")
                    
                    with view_col2:
                        pc_cache_key = f"{asset_id}_point_cloud"
                        if st.button(f"🌌 高科技單色點雲", key=f"view_pc_{asset_id}_{fname}"):
                            with st.spinner("🌌 封裝幾何頂點數據..."):
                                # 點雲也需要從 GLB 快取中獲取頂點，或者從資料庫撈取 GLB 再解析
                                mesh_b64, mesh_fname = fetch_single_filesize_base64(asset_id)
                                if mesh_b64 and not str(mesh_fname).lower().endswith('.usdz'):
                                    try:
                                        # 解析頂點並降採樣 (原本邏輯)
                                        f_bytes = base64.b64decode(mesh_b64)
                                        scene_or_m = trimesh.load(io.BytesIO(f_bytes), file_type='glb')
                                        c_mesh = list(scene_or_m.geometry.values())[0] if isinstance(scene_or_m, trimesh.Scene) else scene_or_m
                                        max_points = 1500
                                        indices = np.random.choice(len(c_mesh.vertices), min(len(c_mesh.vertices), max_points), replace=False)
                                        sampled_points = c_mesh.vertices[indices] * 1000.0
                                        
                                        # 🛠️ 將點雲座標數據存入點雲快取
                                        st.session_state["preview_cache"][pc_cache_key] = sampled_points
                                    except Exception: pass
                    
                    with del_col:
                        # 原本的銷毀邏輯，省略
                        pass
                    
                    # 🛠️ 核心：在預覽 Container 中實施「所見即所得」與「快取讀取」
                    with preview_container:
                        # 1. 實體全貼圖渲染檢查
                        if mesh_cache_key in st.session_state["preview_cache"]:
                            mesh_data_b64 = st.session_state["preview_cache"][mesh_cache_key]
                            # 核心：生成 GLB/USDZ 通用渲染器
                            html_web_view = generate_universal_renderer_html(mesh_data_b64, fname, height=355)
                            st.components.v1.html(html_web_view, height=360)
                        
                        # 2. 點雲模擬渲染檢查
                        if pc_cache_key in st.session_state["preview_cache"]:
                            points = st.session_state["preview_cache"][pc_cache_key]
                            with st.container(border=True):
                                # 原本的 plotly 黑底點雲邏輯
                                fig = go.Figure(data=[go.Scatter3d(x=points[:, 0], y=points[:, 1], z=points[:, 2],mode='markers', marker=dict(size=2.5, color='#00f0ff', opacity=0.85))])
                                fig.update_layout(scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), bgcolor="black"), margin=dict(r=0,l=0,b=0,t=0), paper_bgcolor="black", height=280)
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #bbb;'>", unsafe_allow_html=True)

# ... (分頁二日誌邏輯，省略)