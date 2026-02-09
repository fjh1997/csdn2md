import os
import re
import requests
import base64
import time

# ================= 配置区 =================
GITHUB_TOKEN = "" # 你的github token
REPO = "fjh1997/CSDN"  # 例如: "zhangsan/blog-images"
BRANCH = "main"
TARGET_DIR = "source/images"  # 图片在 GitHub 仓库中的存放目录
LOCAL_FOLDER = r"./"  # 你本地存放 MD 文件的文件夹路径
# ==========================================

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# 匹配 CSDN 图片链接的正则列表
# 1. i-blog.csdnimg.cn (旧版或部分链接)
# 2. img-blog.csdnimg.cn (新版常见链接)
CSDN_IMG_PATTERNS = [
    r'(!\[.*?\]\((https://i-blog\.csdnimg\.cn/[^?)]+).*?\))',
    r'(!\[.*?\]\((https://img-blog\.csdnimg\.cn/[^?)]+).*?\))'
]

def upload_to_github(file_content, file_name):
    """将图片内容上传到 GitHub API"""
    url = f"https://api.github.com/repos/{REPO}/contents/{TARGET_DIR}/{file_name}"
    
    # 检查文件是否已存在（避免重复上传）
    try:
        check_res = requests.get(url, headers=HEADERS)
        if check_res.status_code == 200:
            print(f"  - 图片 {file_name} 已存在，跳过上传")
            return f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/{TARGET_DIR}/{file_name}"
    except Exception as e:
        print(f"  - 检查文件存在出错: {e}")

    content_base64 = base64.b64encode(file_content).decode("utf-8")
    data = {
        "message": f"Upload image {file_name} via script",
        "content": content_base64,
        "branch": BRANCH
    }
    
    try:
        res = requests.put(url, json=data, headers=HEADERS)
        if res.status_code in [200, 201]:
            # 返回 jsDelivr 加速链接
            return f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/{TARGET_DIR}/{file_name}"
        else:
            print(f"  - 上传失败: {res.status_code} {res.text}")
            return None
    except Exception as e:
        print(f"  - 上传请求出错: {e}")
        return None

def process_file(file_path):
    """处理单个 MD 文件"""
    print(f"正在处理: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    modified = False

    # 遍历正则列表，匹配不同域名的图片
    for pattern in CSDN_IMG_PATTERNS:
        matches = re.findall(pattern, new_content)
        
        if not matches:
            continue

        for full_match, img_url in matches:
            print(f"  - 发现图片: {img_url}")
            try:
                # 下载图片，增加 Referer 绕过防盗链
                img_res = requests.get(img_url, headers={'Referer': 'https://blog.csdn.net/'}, timeout=10)
                if img_res.status_code == 200:
                    # 提取文件名
                    img_name = img_url.split('/')[-1]
                    
                    # 处理可能没有后缀名的情况 (img-blog 有时URL里不带后缀，但内容是图片)
                    if '.' not in img_name:
                        # 简单判断一下 Content-Type，或者默认给个 .png
                        content_type = img_res.headers.get('Content-Type', '')
                        if 'jpeg' in content_type:
                            img_name += ".jpg"
                        elif 'gif' in content_type:
                            img_name += ".gif"
                        else:
                            img_name += ".png"
                    
                    # 上传
                    new_github_url = upload_to_github(img_res.content, img_name)
                    
                    if new_github_url:
                        # 替换旧的 URL
                        new_content = new_content.replace(img_url, new_github_url)
                        print(f"  - 替换成功")
                        modified = True
                else:
                    print(f"  - 下载失败: HTTP {img_res.status_code}")
            except Exception as e:
                print(f"  - 处理出错: {e}")
            
            # 稍微停顿
            time.sleep(0.5)

    # 只有内容发生变化才写入文件
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("  - 文件已更新保存")
    else:
        print("  - 无需修改")

def run():
    for root, dirs, files in os.walk(LOCAL_FOLDER):
        for file in files:
            if file.endswith(".md"):
                process_file(os.path.join(root, file))

if __name__ == "__main__":
    run()
