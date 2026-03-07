from PIL import Image, ImageChops


def process_image_to_icon(input_path, output_path):
    # 1. 開啟圖片並轉換為 RGBA (確保有 Alpha 信道)
    img = Image.open(input_path).convert("RGBA")

    # --- 步驟一：去背（將白色轉為透明） ---
    # 分離 R, G, B, A 四個信道
    r, g, b, a = img.split()

    # 我們的目標是讓「不是黑色」的地方變透明。
    # 利用黑色的特性 (RGB皆為0)，我們可以用 R, G, B 的和來當遮罩。
    # 這裡我們使用一個更直觀的方法：把白色 (R>240) 的地方設為 alpha 0。
    # 如果你的原圖背景是非常純的白色 (255)，這行會很有效。
    datas = img.getdata()
    new_data = []
    for item in datas:
        # 如果 RGB 都很接近 255 (白色)，將 A (第4個元素) 設為 0
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)  # 保持原樣
    img.putdata(new_data)

    # --- 步驟二：自動裁切（僅保留圖案部分，忽略文字） ---
    # 再次提取 Alpha 信道以找到實際的「可見區域」
    alpha = img.split()[-1]

    # 使用 ImageChops 的反色功能來找到非透明區域的邊界 (bbox)
    # bbox 返回 (left, top, right, bottom)
    bbox = alpha.getbbox()

    if bbox:
        # 計算頭部的粗略高度（忽略下方文字）
        # 觀察圖片，頭部圖案大約佔據高度的 70%
        image_height = img.height
        head_height_ratio = 0.7
        cropped_head_bottom = bbox[1] + int((bbox[3] - bbox[1]) * head_height_ratio)

        # 執行精確裁切 (left, top, right, bottom)
        cropped_img = img.crop((bbox[0], bbox[1], bbox[2], cropped_head_bottom))

        # 使其變成正方形 (Icon 需要)
        # 尋找裁切後圖片的最大邊長，並將其置中
        w, h = cropped_img.size
        max_dim = max(w, h)
        square_img = Image.new("RGBA", (max_dim, max_dim), (255, 255, 255, 0))
        offset = ((max_dim - w) // 2, (max_dim - h) // 2)
        square_img.paste(cropped_img, offset)
        final_img = square_img
        print(f"裁切完成。原始區域: {bbox}，裁切後區域: (..., {cropped_head_bottom})")
    else:
        final_img = img
        print("未偵測到有效圖案，使用原始圖片。")

    # --- 步驟三：儲存為高品質多尺寸 ICO ---
    # 定義標準的 Icon 尺寸
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    # 指定 bmp 格式封裝，能更精確地支援透明背景
    final_img.save(output_path, sizes=icon_sizes, bitmap_format="bmp")
    print(f"高品質透明 Icon 裁切版本已生成：{output_path}")


# --- 執行程式 ---
# 為了避免快取問題，我們使用一個全新的檔名
process_image_to_icon("luna.png", "luna_head_transparent_v4.ico")