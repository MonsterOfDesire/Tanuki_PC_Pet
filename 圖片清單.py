import os
import pandas as pd


def generate_excel_with_logic(folder_path, output_excel):
    valid_extensions = ('.gif')
    files = [f for f in os.listdir(folder_path) if f.endswith(valid_extensions)]

    # 定義關鍵字映射
    severe_keys = ["scold", "hard-cry", "cry", "exhausted", "scared"]
    low_keys = ["sad", "angry", "awkward", "think", "hurry", "effort", "sleep"]
    normal_keys = ["happy", "smile", "confidence", "cool", "glance", "awkward", "think"]

    rows = []

    for filename in files:
        name_lower = filename.lower()

        # 1. 判斷 Band (根據優先順序或聯集)
        bands = []
        if any(k in name_lower for k in severe_keys):
            bands.append("severe")
        if any(k in name_lower for k in low_keys):
            bands.append("low")
        if any(k in name_lower for k in normal_keys):
            bands.append("normal")

        # 2. 判斷 Contexts
        if "interaction_move" in name_lower:
            context_val = "moving_interaction"
        elif "interaction" in name_lower:
            context_val = "interaction"
        else:
            context_val = "random"

        # 建立資料列
        rows.append({
            "filename": filename,
            "band": ", ".join(bands),  # 在 Excel 中以逗號分隔
            "contexts": context_val,
            "weight": 1.0,
            "release_offset": ""  # 預留空白
        })

    df = pd.DataFrame(rows)
    df.to_excel(output_excel, index=False)
    print(f"自動分類完成！Excel 檔案已生成：{output_excel}")

# 使用範例
folder_path = r"J:\TanukiProject\venv\assets_cropped\Tsurumaru Tsuyoshi"
generate_excel_with_logic(folder_path, "manifest_edit.xlsx")