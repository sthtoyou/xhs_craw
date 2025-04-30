# Web Crawler with AI Analysis

一个强大的网页爬虫工具，支持多种网站的内容抓取，并使用大模型进行文本分析。

## 功能特点

- 支持多种网站的内容抓取：
  - 知乎文章（需要cookie）
  - 小红书笔记（需要cookie和x-s参数）
  - 抖音视频（需要cookie）
  - 今日头条文章（需要cookie）
  - 其他普通网页
- 支持大模型文本分析：
  - 通义千问（dashscope）
  - 文心一言（百度AI）
- 自动下载网页中的图片
- 将结果保存为Excel文件
- 支持批量处理多个URL
- 支持交互式单URL处理
- 支持环境变量配置

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/craw.git
cd craw
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 安装Playwright浏览器：
```bash
playwright install
```

## 配置

可以通过环境变量或命令行参数进行配置：

### 环境变量
创建 `.env` 文件并设置以下变量：
```
QWEN_API_KEY=your_qwen_api_key
WENXIN_API_KEY=your_wenxin_api_key
WENXIN_SECRET_KEY=your_wenxin_secret_key
ZHIHU_COOKIE=your_zhihu_cookie
XIAOHONGSHU_COOKIE=your_xiaohongshu_cookie
XIAOHONGSHU_X_S=your_xiaohongshu_x_s
DOUYIN_COOKIE=your_douyin_cookie
TOUTIAO_COOKIE=your_toutiao_cookie
```

### 命令行参数

```bash
python web_crawler.py --help
```

主要参数：
- `--urls`: 要处理的URL列表（空格分隔）
- `--model-type`: 大模型类型（'qwen' 或 'wenxin'）
- `--model-api-key`: 大模型API密钥
- `--base-image-dir`: 图片保存目录（默认：'downloads'）
- `--zhihu-cookie`: 知乎cookie（可选）
- `--xiaohongshu-cookie`: 小红书cookie（可选）
- `--xiaohongshu-x-s`: 小红书x-s参数（可选）
- `--douyin-cookie`: 抖音cookie（可选）
- `--toutiao-cookie`: 头条cookie（可选）
- `--no-download-images`: 不下载图片
- `--no-save-to-excel`: 不保存到Excel
- `--excel-file`: Excel文件名
- `--append`: 追加到现有文件

### 示例

1. 使用通义千问分析单个URL：
```bash
python web_crawler.py --model-type qwen --model-api-key YOUR_QWEN_API_KEY --urls https://example.com
```

2. 使用文心一言批量分析多个URL：
```bash
python web_crawler.py --model-type wenxin --model-api-key YOUR_WENXIN_API_KEY --urls https://example1.com https://example2.com
```

3. 交互式模式：
```bash
python web_crawler.py --model-type qwen --model-api-key YOUR_QWEN_API_KEY
```

## 输出结果

程序会生成以下输出：
1. 文本分析结果：
   - 原始文本
   - 核心内容摘要
   - 关键词列表
2. 下载的图片（如果启用）：
   - 图片按域名和时间戳分类存储
   - 自动处理图片格式和大小
3. Excel文件（如果启用），包含：
   - URL
   - 原始文本
   - 核心内容
   - 关键词
   - 图片路径

## 注意事项

1. 某些网站（如知乎、小红书、抖音、头条）需要提供cookie才能抓取内容
2. 使用大模型API需要相应的API密钥
3. 建议在使用前先测试单个URL的处理
4. 批量处理时注意API调用频率限制
5. 图片下载功能会自动处理图片格式和大小限制
6. 支持环境变量配置，方便批量处理

## 依赖项

- requests>=2.31.0
- beautifulsoup4>=4.12.0
- pandas>=2.0.0
- openpyxl>=3.1.0
- dashscope>=1.13.0
- tqdm>=4.66.0
- playwright>=1.40.0
- aiohttp>=3.9.0
- python-dotenv==1.0.1
- baidu-aip>=2.2.18

## 许可证

MIT License 