# =========================================================================
# 🤖 OptiSpin 3D AI攝影棚 - 精密幾何量測與網格特徵診斷工具 [完全體]
# =========================================================================
import os
import numpy as np
import trimesh

print("\n==================================================")
print("🚀 [START] 獨立 AI 攝影棚量測探針正在強制啟動中...")
print("==================================================")

# 🎯 請確認這個 GLB 檔案有放在你的 saved_models 資料夾中
# (檔名請務必與你資料夾裡的檔案一模一樣)
target_filename = "Scaniverse 2026-05-25 182400.glb" 

file_path = os.path.join("saved_models", target_filename)
base_name = os.path.splitext(target_filename)[0]
output_dir = os.path.join("saved_images", f"{base_name}_dataset")

print(f"🔍 檢查實體檔案路徑: {file_path}")

if not os.path.exists(file_path):
    print(f"❌ 嚴重錯誤：目標資料夾內找不到指定測試檔案！")
    print(f"💡 目前 saved_models 資料夾內所有檔案列表為: {os.listdir('saved_models')}")
else:
    print(f"📂 檔案實體確認存在！開始嘗試載入 3D 結構...")
    try:
        loaded = trimesh.load(file_path)
        
        # 1. 執行複合場景（Scene）解構
        if isinstance(loaded, trimesh.Scene):
            print("💡 偵測到 Scaniverse 複合場景 (Scene)，正在解構層級節點並合併網格...")
            mesh = loaded.to_mesh()
        else:
            mesh = loaded
            
        print(f"✅ 成功將場景封裝解構為單一多邊形網格物件！")
        
        # 2. 幾何頂點矩陣有效性驗證
        vertices = np.array(mesh.vertices)
        print(f"📐 讀取幾何頂點矩陣成功！頂點總數: {len(vertices)} | 三角面總數: {len(mesh.faces)}")
        
        if len(vertices) == 0:
            raise ValueError("該模型檔案之頂點矩陣長度為 0 (幽靈網格)，不包含任何有效實體幾何數據。")
            
        # 3. 🌟 核心修正：將 Scaniverse 預設的「公尺」集體乘以 1000 放大為工業標準「公釐 (mm)」
        print("⚡ 啟動單位校正探針：公尺 (m) ➡️ 公釐 (mm)")
        vertices_scaled = vertices * 1000.0
        mesh.vertices = vertices_scaled
        
        # 4. 用 NumPy 矩陣降維極值操作，強行算出真實 Bounding Box 長寬高包絡尺寸
        min_bound = np.min(vertices_scaled, axis=0)
        max_bound = np.max(vertices_scaled, axis=0)
        extents = max_bound - min_bound
        print(f"衡量結果 📏 實體外觀尺寸: {extents[0]:.1f} x {extents[1]:.1f} x {extents[2]:.1f} mm")
        
        # 5. 幾何軸向置中校正，確保物體中心死死鎖定在絕對原點 (0,0,0)
        centroid = (max_bound + min_bound) / 2.0
        mesh.apply_translation(-centroid)
        print(f"📍 質心校正完成。模型幾何中心已成功校正對齊至旋轉軸原點")
        
        # 6. 架設虛擬渲染場景並動態調校觀測半徑
        scene = mesh.scene()
        max_dim = np.max(extents)
        
        # 相機安全半徑在毫米維度下拉開，徹底打通近裁剪面穿透地獄
        camera_distance = max_dim * 2.5
        print(f"🛰️ 虛擬相機最佳環繞拍攝半徑設定為: {camera_distance:.2f} mm")
        
        if not os.path.exists(output_dir): 
            os.makedirs(output_dir)
        
        # 7. 自動化 360 度環繞追蹤拍照快門
        print("📸 啟動自動攝影棚，開始進行環繞 360 度連續追蹤拍攝...")
        for i in range(10):
            angle = (2 * np.pi / 10) * i
            cam_x = camera_distance * np.cos(angle)
            cam_y = camera_distance * np.sin(angle)
            cam_z = camera_distance * 0.6  # 帶有完美的工業 3D 俯視夾角
            
            camera_transform = trimesh.transformations.look_at(
                eye=[cam_x, cam_y, cam_z], 
                target=[0, 0, 0], 
                up=[0, 0, 1]
            )
            scene.camera_transform = camera_transform
            
            # 渲染並存入檔案系統
            img_data = scene.save_image(resolution=[400, 400])
            save_filename = f"view_{i:02d}.png"
            with open(os.path.join(output_dir, save_filename), "wb") as f:
                f.write(img_data)
            print(f"  [視角 {i:02d}] 咔嚓！{save_filename} 渲染完成並成功存檔。")
            
        print("\n🎉 【史詩級重大突破】AI 攝影棚除錯診斷完畢，10 組環繞視角照片已全數噴出！")
        print(f"📂 請至這個資料夾查看實體相片：{output_dir}")
        
    except Exception as e:
        print("\n💥 [崩潰報錯] 後端網格幾何運算中斷，錯誤追蹤軌跡如下：")
        import traceback
        traceback.print_exc()

print("==================================================")
print("🏁 [END] 診斷腳本執行完畢。")
print("==================================================\n")