import pandas as pd
import json


def excel_to_manifest_json(input_excel, output_json):
    df = pd.read_excel(input_excel)
    manifest = {}

    for _, row in df.iterrows():
        filename = row['filename']
        item_data = {}

        # 處理清單類欄位 (自動過濾掉 NaN)
        for col in ['band', 'contexts']:
            val = str(row[col]) if pd.notna(row[col]) else ""
            if val.strip():
                # 將 "low, normal" 分解為 ["low", "normal"]
                item_data[col] = [i.strip() for i in val.split(',')]

        # 處理數值
        if pd.notna(row['weight']):
            item_data['weight'] = float(row['weight'])

        if pd.notna(row['release_offset']):
            try:
                item_data['release_offset'] = int(row['release_offset'])
            except:
                pass

        manifest[filename] = item_data

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"JSON 轉換成功：{output_json}")

input_excel = r"J:\TanukiProject\venv\assets_cropped\Air Groove\manifest_edit.xlsx"
output_json = r"J:\TanukiProject\venv\assets_cropped\Air Groove\manifest_edit.json"
excel_to_manifest_json(input_excel, output_json)