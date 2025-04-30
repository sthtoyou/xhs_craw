import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from urllib.parse import urljoin, urlparse
import dashscope
from datetime import datetime
import re
import random
import time
from tqdm import tqdm
import hashlib
import json
import base64
import asyncio
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import argparse
from typing import Tuple, List
from models import get_model

class WebCrawler:
    def __init__(self, model_type=None, model_api_key=None, base_image_dir=None, zhihu_cookie=None, xiaohongshu_cookie=None, xiaohongshu_x_s=None, douyin_cookie=None, toutiao_cookie=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        })
        self.base_image_dir = base_image_dir or os.path.abspath('downloads')
        self.model = get_model(model_type, model_api_key) if model_type and model_api_key else None
        self.zhihu_cookie = zhihu_cookie
        self.xiaohongshu_cookie = xiaohongshu_cookie
        self.xiaohongshu_x_s = xiaohongshu_x_s
        self.douyin_cookie = douyin_cookie
        self.toutiao_cookie = toutiao_cookie
        
        # 确保图片目录存在
        if not os.path.exists(self.base_image_dir):
            os.makedirs(self.base_image_dir)
            
        # 如果有认证信息，立即设置
        if zhihu_cookie:
            self.set_auth_info('zhihu', cookie=zhihu_cookie)
        if xiaohongshu_cookie:
            self.set_auth_info('xiaohongshu', cookie=xiaohongshu_cookie, x_s=xiaohongshu_x_s)
        if douyin_cookie:
            self.set_auth_info('douyin', cookie=douyin_cookie)
        if toutiao_cookie:
            self.set_auth_info('toutiao', cookie=toutiao_cookie)

    def set_qwen_api_key(self, api_key):
        """设置通义千问 API 密钥"""
        self.qwen_api_key = api_key
        dashscope.api_key = api_key

    async def get_xiaohongshu_content_playwright(self, url):
        """
        使用Playwright获取小红书笔记内容
        
        Args:
            url (str): 小红书笔记URL
            
        Returns:
            tuple: (文本内容, 图片URL列表)
        """
        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.session.headers['User-Agent']
                )
                page = await context.new_page()
                
                # 访问页面
                await page.goto(url, wait_until='networkidle')
                
                # 获取文本内容
                text = []
                
                # 获取标题
                try:
                    title = await page.locator('.title').text_content()
                    text.append(f"标题：{title}")
                except:
                    pass
                    
                # 获取正文
                try:
                    content = await page.locator('.content').text_content()
                    text.append(f"正文：{content}")
                except:
                    pass
                    
                # 获取标签
                try:
                    tags = await page.locator('.tag').all()
                    if tags:
                        tag_texts = [await tag.text_content() for tag in tags]
                        text.append(f"标签：{', '.join(tag_texts)}")
                except:
                    pass
                
                # 获取图片
                images = []
                try:
                    img_elements = await page.locator('img').all()
                    for img in img_elements:
                        src = await img.get_attribute('src')
                        if src and not src.startswith('data:image/svg'):  # 排除SVG图标
                            images.append(src)
                except:
                    pass
                
                # 关闭浏览器
                await browser.close()
                
                return '\n'.join(text), images
                
        except Exception as e:
            print(f"使用Playwright获取小红书内容时出错: {str(e)}")
            return None, None

    def set_auth_info(self, platform, cookie=None, x_s=None):
        """
        设置平台认证信息
        
        Args:
            platform (str): 平台名称 ('zhihu' 或 'xiaohongshu')
            cookie (str): cookie字符串
            x_s (str): x-s参数（仅小红书需要）
        """
        if platform == 'zhihu':
            self.zhihu_cookie = cookie
        elif platform == 'xiaohongshu':
            self.xiaohongshu_cookie = cookie
            self.xiaohongshu_x_s = x_s

    def create_image_directory(self, url):
        """
        为每个网页创建独立的图片目录
        
        Args:
            url (str): 网页URL
            
        Returns:
            str: 图片目录路径
        """
        # 使用域名和时间戳创建目录名
        domain = urlparse(url).netloc
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 使用URL的MD5作为子目录名，避免重复
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        dir_name = f"{domain}_{timestamp}_{url_hash}"
        
        # 创建完整路径
        image_dir = os.path.join(self.base_image_dir, dir_name)
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
            
        return image_dir

    def get_image_extension(self, response):
        """
        根据响应头和URL确定图片扩展名
        
        Args:
            response (Response): 请求响应对象
            
        Returns:
            str: 图片扩展名
        """
        # 从Content-Type获取
        content_type = response.headers.get('content-type', '').lower()
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        elif 'bmp' in content_type:
            return '.bmp'
        elif 'svg' in content_type:
            return '.svg'
        else:
            return '.jpg'  # 默认扩展名

    def is_valid_image(self, response):
        """
        检查响应是否为有效的图片
        
        Args:
            response (Response): 请求响应对象
            
        Returns:
            bool: 是否为有效图片
        """
        content_type = response.headers.get('content-type', '').lower()
        valid_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml']
        
        if not any(t in content_type for t in valid_types):
            return False
            
        # 检查文件大小
        content_length = int(response.headers.get('content-length', 0))
        if content_length > 10 * 1024 * 1024:  # 大于10MB的跳过
            return False
            
        return True

    def resolve_xiaohongshu_short_url(self, short_url):
        """
        解析小红书短链接，获取真实链接
        
        Args:
            short_url (str): 小红书短链接
            
        Returns:
            str: 真实的笔记链接
        """
        try:
            # 设置允许重定向
            response = self.session.get(short_url, allow_redirects=True, timeout=10)
            # 获取最终重定向的URL
            final_url = response.url
            print(f"短链接已解析: {final_url}")
            return final_url
        except Exception as e:
            print(f"解析短链接时出错: {str(e)}")
            return None

    def get_zhihu_content(self, url):
        """
        获取知乎文章内容
        
        Args:
            url (str): 知乎文章URL
            
        Returns:
            tuple: (文本内容, 图片URL列表)
        """
        try:
            # 构建知乎API URL
            article_id = url.split('/')[-1]
            api_url = f'https://www.zhihu.com/api/v4/articles/{article_id}'
            
            # 添加知乎特定的请求头
            headers = self.session.headers.copy()
            headers.update({
                'authority': 'www.zhihu.com',
                'referer': 'https://www.zhihu.com/',
                'x-requested-with': 'fetch',
                'x-zse-93': '101_3_3.0',
                'cookie': self.zhihu_cookie,
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'none',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1'
            })
            
            response = self.session.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            content = data.get('content', '')
            
            # 解析HTML内容
            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取文本
            text = soup.get_text()
            
            # 提取图片
            images = []
            for img in soup.find_all('img'):
                img_url = img.get('src') or img.get('data-original')
                if img_url:
                    images.append(img_url)
                    
            return text, images
            
        except Exception as e:
            print(f"获取知乎内容时出错: {str(e)}")
            return None, None

    def extract_content(self, url):
        """
        从网页提取文本和图片
        
        Args:
            url (str): 网页URL
            
        Returns:
            dict: 包含 'content' 和 'image_urls' 的字典
        """
        try:
            # 检查 URL 格式
            if not url.startswith(('http://', 'https://')):
                raise ValueError("Invalid URL format. URL must start with http:// or https://")
            
            domain = urlparse(url).netloc
            
            # 处理不同网站的内容
            if 'zhihu.com' in domain:
                if not self.zhihu_cookie:
                    print("需要知乎 cookie 才能抓取知乎文章。请登录知乎后从浏览器开发者工具中获取 cookie。")
                    return None
                text, images = self.get_zhihu_content(url)
                if text is None:
                    return None
                return {'content': text, 'image_urls': images or []}
            elif 'xiaohongshu.com' in domain:
                if not self.xiaohongshu_cookie:
                    print("需要小红书 cookie 才能抓取小红书笔记。请登录小红书后从浏览器开发者工具中获取 cookie。")
                    return None
                result = self.get_xiaohongshu_content(url)
                if result is None:
                    return None
                return {
                    'content': f"标题：{result.get('title', '')}\n\n正文：{result.get('content', '')}",
                    'image_urls': result.get('image_urls', [])
                }
            elif 'douyin.com' in domain:
                if not self.douyin_cookie:
                    print("需要抖音 cookie 才能抓取抖音内容。请登录抖音后从浏览器开发者工具中获取 cookie。")
                    return None
                result = self.get_douyin_content(url)
                if result is None:
                    return None
                return {
                    'content': f"标题：{result.get('title', '')}\n\n正文：{result.get('content', '')}",
                    'image_urls': result.get('image_urls', [])
                }
            elif 'toutiao.com' in domain:
                if not self.toutiao_cookie:
                    print("需要头条 cookie 才能抓取头条文章。请登录头条后从浏览器开发者工具中获取 cookie。")
                    return None
                result = self.get_toutiao_content(url)
                if result is None:
                    return None
                return {
                    'content': f"标题：{result.get('title', '')}\n\n正文：{result.get('content', '')}",
                    'image_urls': result.get('image_urls', [])
                }
            else:
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 提取文本
                text = soup.get_text()
                
                # 提取图片
                images = []
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src:
                        images.append(src)
                        
                return {
                    'content': text,
                    'image_urls': images
                }
            
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"状态码: {e.response.status_code}")
                print(f"响应头: {e.response.headers}")
            return None
        except Exception as e:
            print(f"提取内容时出错: {str(e)}")
            return None

    def download_images(self, images, url):
        """
        下载图片到本地
        
        Args:
            images (list): 图片URL列表
            url (str): 原始网页URL
            
        Returns:
            list: 下载的图片路径列表
        """
        if not images:
            print("没有找到需要下载的图片")
            return []
            
        # 创建图片保存目录
        image_dir = self.create_image_directory(url)
        print(f"\n图片将保存到: {image_dir}")
        
        downloaded_paths = []
        failed_downloads = []
        
        # 使用tqdm创建进度条
        for i, img_url in enumerate(tqdm(images, desc="下载图片", unit="张")):
            try:
                # 添加随机延迟
                time.sleep(random.uniform(0.5, 1.5))
                
                # 处理base64图片
                if img_url.startswith('data:image'):
                    # 从base64字符串中提取图片数据
                    img_data = img_url.split(',')[1]
                    img_bytes = base64.b64decode(img_data)
                    
                    # 从MIME类型中获取扩展名
                    mime_type = img_url.split(';')[0].split(':')[1]
                    ext = '.' + mime_type.split('/')[-1]
                    
                    # 创建文件名
                    img_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                    filename = f"image_{i+1}_{img_hash}{ext}"
                    filepath = os.path.join(image_dir, filename)
                    
                    # 保存图片
                    with open(filepath, 'wb') as f:
                        f.write(img_bytes)
                        
                    downloaded_paths.append(filepath)
                    continue
                
                # 处理普通URL图片
                response = requests.get(img_url, headers=self.session.headers, timeout=10, stream=True)
                if response.status_code == 200 and self.is_valid_image(response):
                    # 获取扩展名
                    ext = self.get_image_extension(response)
                    
                    # 创建文件名（使用URL的MD5值避免重复）
                    img_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                    filename = f"image_{i+1}_{img_hash}{ext}"
                    filepath = os.path.join(image_dir, filename)
                    
                    # 保存图片
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                
                    downloaded_paths.append(filepath)
                    
                else:
                    failed_downloads.append((img_url, "无效的响应或非图片内容"))
                    
            except Exception as e:
                failed_downloads.append((img_url, str(e)))
                
        # 打印下载结果统计
        total = len(images)
        success = len(downloaded_paths)
        failed = len(failed_downloads)
        
        print(f"\n下载完成！")
        print(f"总计: {total} 张图片")
        print(f"成功: {success} 张")
        print(f"失败: {failed} 张")
        
        # 如果有失败的下载，打印详细信息
        if failed_downloads:
            print("\n失败的下载:")
            for url, reason in failed_downloads:
                print(f"URL: {url}")
                print(f"原因: {reason}\n")
                
        return downloaded_paths

    def analyze_text(self, text):
        """
        使用配置的大模型分析文本
        
        Args:
            text (str): 要分析的文本
            
        Returns:
            tuple: (核心内容, 关键词)
        """
        if not self.model:
            print("错误：未设置大模型")
            return None, None
            
        try:
            return asyncio.run(self.model.analyze_text(text))
        except Exception as e:
            print(f"分析文本时出错: {str(e)}")
            return None, None

    def save_to_excel(self, url, text, summary, keywords, image_paths, excel_filename=None, append=False):
        """
        将结果保存到Excel文件
        
        Args:
            url (str): 网页URL
            text (str): 原始文本
            summary (str): 核心内容
            keywords (list): 关键词列表
            image_paths (list): 图片路径列表
            excel_filename (str, optional): Excel文件名，不指定则使用默认名称
            append (bool): 是否追加到现有文件
        """
        try:
            # 创建DataFrame
            data = {
                'URL': [url],
                '原始文本': [text],
                '核心内容': [summary],
                '关键词': [', '.join(keywords)],
                '图片路径': ['\n'.join(image_paths)]
            }
            
            df = pd.DataFrame(data)
            
            # 生成文件名
            if not excel_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                excel_filename = f'web_analysis_{timestamp}.xlsx'
            
            # 如果文件存在且需要追加
            if os.path.exists(excel_filename) and append:
                # 读取现有文件
                existing_df = pd.read_excel(excel_filename)
                # 合并数据
                df = pd.concat([existing_df, df], ignore_index=True)
                print(f"结果已追加到 {excel_filename}")
            else:
                print(f"结果已保存到 {excel_filename}")
            
            # 保存到Excel
            df.to_excel(excel_filename, index=False, engine='openpyxl')
            
        except Exception as e:
            print(f"保存Excel时出错: {str(e)}")

    def get_xiaohongshu_content(self, url):
        print("正在使用 Playwright 抓取小红书内容...")
        
        with sync_playwright() as p:
            # 启动浏览器，设置更宽松的超时时间
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            
            # 如果有 cookie，设置 cookie
            if self.xiaohongshu_cookie:
                for cookie_str in self.xiaohongshu_cookie.split(';'):
                    if '=' in cookie_str:
                        name, value = cookie_str.strip().split('=', 1)
                        context.add_cookies([{
                            'name': name,
                            'value': value,
                            'domain': '.xiaohongshu.com',
                            'path': '/'
                        }])
            
            # 创建新页面
            page = context.new_page()
            
            try:
                # 访问页面，设置较长的超时时间
                page.goto(url, wait_until='networkidle', timeout=60000)
                
                # 等待页面加载完成
                page.wait_for_load_state('networkidle', timeout=60000)
                
                # 等待内容出现
                selectors = [
                    'div[class*="content"]',  # 正文内容
                    'div[class*="title"]',    # 标题
                    'div[class*="desc"]',     # 描述
                    'img[class*="image"]',    # 图片
                ]
                
                # 等待任意一个选择器出现
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=20000)
                    except:
                        continue
                
                # 提取标题
                title = ''
                try:
                    title_elem = page.query_selector('div[class*="title"]')
                    if title_elem:
                        title = title_elem.inner_text()
                except:
                    pass
                
                # 提取正文内容
                content = ''
                try:
                    content_selectors = [
                        'div[class*="content"]',
                        'div[class*="desc"]',
                        'div[class*="note"]'
                    ]
                    for selector in content_selectors:
                        content_elem = page.query_selector(selector)
                        if content_elem:
                            text = content_elem.inner_text()
                            if text:
                                content += text + '\n'
                except:
                    pass
                
                # 提取图片 URL
                image_urls = []
                try:
                    img_selectors = [
                        'img[class*="image"]',
                        'div[class*="image"] img',
                        'div[class*="swiper"] img'
                    ]
                    for selector in img_selectors:
                        img_elements = page.query_selector_all(selector)
                        for img in img_elements:
                            src = img.get_attribute('src')
                            if src and not src.startswith('data:'):
                                image_urls.append(src)
                except:
                    pass
                
                if not title and not content and not image_urls:
                    print("警告：未能提取到任何内容，可能需要登录或cookie已过期")
                    return None
                
                return {
                    'title': title,
                    'content': content.strip(),
                    'image_urls': list(set(image_urls))  # 去重
                }
                
            except Exception as e:
                print(f"抓取小红书内容时出错: {str(e)}")
                return None
            
            finally:
                browser.close()

    def get_douyin_content(self, url):
        """
        获取抖音视频内容
        
        Args:
            url (str): 抖音视频URL
            
        Returns:
            dict: 包含 'title', 'content', 'image_urls' 的字典
        """
        print("正在使用 Playwright 抓取抖音内容...")
        
        with sync_playwright() as p:
            # 启动浏览器，设置更宽松的超时时间
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"macOS"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # 如果有 cookie，设置 cookie
            if self.douyin_cookie:
                for cookie_str in self.douyin_cookie.split(';'):
                    if '=' in cookie_str:
                        name, value = cookie_str.strip().split('=', 1)
                        context.add_cookies([{
                            'name': name,
                            'value': value,
                            'domain': '.douyin.com',
                            'path': '/'
                        }])
            
            # 创建新页面
            page = context.new_page()
            
            try:
                # 访问页面，设置更长的超时时间
                page.goto(url, wait_until='networkidle', timeout=120000)
                
                # 等待页面加载完成
                page.wait_for_load_state('networkidle', timeout=120000)
                
                # 等待内容出现
                selectors = [
                    'div[class*="title"]',    # 标题
                    'div[class*="desc"]',     # 描述
                    'div[class*="comment"]',  # 评论
                    'img[class*="image"]',    # 图片
                ]
                
                # 等待任意一个选择器出现
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=30000)
                    except:
                        continue
                
                # 提取标题
                title = ''
                try:
                    title_elem = page.query_selector('div[class*="title"]')
                    if title_elem:
                        title = title_elem.inner_text()
                except:
                    pass
                
                # 提取描述内容
                content = ''
                try:
                    content_selectors = [
                        'div[class*="desc"]',
                        'div[class*="comment"]',
                        'div[class*="text"]'
                    ]
                    for selector in content_selectors:
                        content_elem = page.query_selector(selector)
                        if content_elem:
                            text = content_elem.inner_text()
                            if text:
                                content += text + '\n'
                except:
                    pass
                
                # 提取图片 URL
                image_urls = []
                try:
                    img_selectors = [
                        'img[class*="image"]',
                        'div[class*="image"] img',
                        'div[class*="swiper"] img'
                    ]
                    for selector in img_selectors:
                        img_elements = page.query_selector_all(selector)
                        for img in img_elements:
                            src = img.get_attribute('src')
                            if src and not src.startswith('data:'):
                                image_urls.append(src)
                except:
                    pass
                
                if not title and not content and not image_urls:
                    print("警告：未能提取到任何内容，可能需要登录或cookie已过期")
                    return None
                
                return {
                    'title': title,
                    'content': content.strip(),
                    'image_urls': list(set(image_urls))  # 去重
                }
                
            except Exception as e:
                print(f"抓取抖音内容时出错: {str(e)}")
                return None
            
            finally:
                browser.close()

    def get_toutiao_content(self, url: str) -> Tuple[str, List[str]]:
        """使用 Playwright 抓取头条内容"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                )
                
                # 设置cookie
                if self.toutiao_cookie:
                    context.add_cookies([{
                        'name': 'tt_webid',
                        'value': self.toutiao_cookie,
                        'domain': '.toutiao.com',
                        'path': '/'
                    }])
                
                page = context.new_page()
                page.set_default_timeout(120000)  # 设置超时时间为120秒
                
                # 访问页面
                page.goto(url, wait_until='networkidle')
                
                # 等待文章主体加载
                article = page.wait_for_selector('article', timeout=30000)
                if not article:
                    print("未找到文章主体")
                    return "", []
                
                # 尝试点击"展开剩余"按钮
                try:
                    # 等待页面完全加载
                    page.wait_for_timeout(2000)
                    
                    # 尝试查找包含"展开剩余"文本的元素
                    expand_elements = page.query_selector_all('text="展开剩余"')
                    if expand_elements:
                        print(f"找到 {len(expand_elements)} 个展开按钮")
                        for element in expand_elements:
                            element.click()
                            page.wait_for_timeout(1000)
                    
                    # 尝试查找其他可能的展开按钮
                    for selector in ['button', 'div', 'span', 'a']:
                        elements = page.query_selector_all(selector)
                        for element in elements:
                            try:
                                text = element.text_content()
                                if text and '展开' in text and '剩余' in text:
                                    print(f"找到展开按钮: {text}")
                                    element.click()
                                    page.wait_for_timeout(1000)
                            except:
                                pass
                    
                    # 滚动页面以触发懒加载
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    page.wait_for_timeout(2000)
                    page.evaluate('window.scrollTo(0, 0)')
                    page.wait_for_timeout(2000)
                    
                except Exception as e:
                    print(f"点击展开按钮时出错: {str(e)}")
                
                # 提取文章主体中的图片URL
                image_urls = []
                
                # 获取文章主体中的所有图片元素
                img_elements = article.query_selector_all('img')
                for img in img_elements:
                    # 获取所有可能的图片URL属性
                    src = img.get_attribute('src')
                    data_src = img.get_attribute('data-src')
                    data_original = img.get_attribute('data-original')
                    
                    # 只添加文章主体中的图片，排除头像、图标等
                    if src and src.startswith('http') and not any(x in src.lower() for x in ['avatar', 'icon', 'logo']):
                        image_urls.append(src)
                    if data_src and data_src.startswith('http') and not any(x in data_src.lower() for x in ['avatar', 'icon', 'logo']):
                        image_urls.append(data_src)
                    if data_original and data_original.startswith('http') and not any(x in data_original.lower() for x in ['avatar', 'icon', 'logo']):
                        image_urls.append(data_original)
                
                # 去重
                image_urls = list(set(image_urls))
                
                # 提取文章文本
                # 移除侧边栏和推荐内容
                sidebars = article.query_selector_all('.sidebar, .recommend, .related-articles, .advertisement')
                for sidebar in sidebars:
                    sidebar.evaluate('node => node.remove()')
                
                # 获取文章主体文本
                text = article.text_content().strip()
                
                browser.close()
                return text, image_urls
                
        except Exception as e:
            print(f"抓取头条内容时出错: {str(e)}")
            return "", []

    def process_url(self, url, download_images=True, save_to_excel=True, excel_filename=None, append=False):
        """
        处理单个URL，提取内容，下载图片，分析文本，并保存结果
        
        Args:
            url (str): 要处理的URL
            download_images (bool): 是否下载图片
            save_to_excel (bool): 是否保存到Excel
            excel_filename (str, optional): Excel文件名，不指定则使用默认名称
            append (bool): 是否追加到现有文件
            
        Returns:
            dict: 处理结果，包含URL、内容、摘要、关键词和图片路径
        """
        result = {
            'url': url,
            'content': None,
            'summary': None,
            'keywords': None,
            'image_paths': [],
            'success': False,
            'error': None
        }
        
        try:
            # 判断URL类型
            if 'xiaohongshu.com' in url or 'xhslink.com' in url:
                content = self.get_xiaohongshu_content(url)
                if content:
                    text = content.get('content', '')
                    image_urls = content.get('image_urls', [])
                else:
                    result['error'] = "无法获取小红书内容"
                    return result
            elif 'zhihu.com' in url:
                text, image_urls = self.get_zhihu_content(url)
            elif 'douyin.com' in url:
                content = self.get_douyin_content(url)
                if content:
                    text = content.get('content', '')
                    image_urls = content.get('image_urls', [])
                else:
                    result['error'] = "无法获取抖音内容"
                    return result
            elif 'toutiao.com' in url:
                text, image_urls = self.get_toutiao_content(url)
            else:
                print(f"不支持的URL类型: {url}")
                return result
            
            # 下载图片
            if download_images and image_urls:
                result['image_paths'] = self.download_images(image_urls, url)
            else:
                print("已跳过图片下载")
            
            # 分析文本
            print("\n正在分析文本...")
            if not text:
                result['error'] = "没有提取到文本内容"
                return result
                
            summary, keywords = self.analyze_text(text)
            if not summary or not keywords:
                result['error'] = "文本分析失败"
                return result
            
            result['content'] = text
            result['summary'] = summary
            result['keywords'] = keywords
            
            # 保存结果
            if save_to_excel:
                print("正在保存结果...")
                self.save_to_excel(url, text, summary, keywords, result['image_paths'], excel_filename, append)
            
            result['success'] = True
            print("\n分析完成！")
            
        except Exception as e:
            result['error'] = f"处理过程中出错: {str(e)}"
            print(result['error'])
        
        return result

def batch_process(urls, model_type=None, model_api_key=None, base_image_dir=None, zhihu_cookie=None, xiaohongshu_cookie=None, xiaohongshu_x_s=None, douyin_cookie=None, toutiao_cookie=None, download_images=True, save_to_excel=True, excel_filename=None, append=False):
    """
    批量处理多个URL
    
    Args:
        urls (list): URL列表
        model_type (str, optional): 大模型类型 ('qwen' 或 'wenxin')
        model_api_key (str, optional): 大模型API密钥
        base_image_dir (str, optional): 图片保存目录
        zhihu_cookie (str, optional): 知乎cookie
        xiaohongshu_cookie (str, optional): 小红书cookie
        xiaohongshu_x_s (str, optional): 小红书x-s参数
        douyin_cookie (str, optional): 抖音cookie
        toutiao_cookie (str, optional): 头条cookie
        download_images (bool): 是否下载图片
        save_to_excel (bool): 是否保存到Excel
        excel_filename (str, optional): Excel文件名，不指定则使用默认名称
        append (bool): 是否追加到现有文件
        
    Returns:
        list: 处理结果列表
    """
    crawler = WebCrawler(
        model_type=model_type,
        model_api_key=model_api_key,
        base_image_dir=base_image_dir,
        zhihu_cookie=zhihu_cookie,
        xiaohongshu_cookie=xiaohongshu_cookie,
        xiaohongshu_x_s=xiaohongshu_x_s,
        douyin_cookie=douyin_cookie,
        toutiao_cookie=toutiao_cookie
    )
    
    results = []
    for i, url in enumerate(urls):
        print(f"\n处理URL {i+1}/{len(urls)}: {url}")
        # 对于第一个URL，如果append为True，则追加到现有文件；否则创建新文件
        # 对于后续URL，如果append为True，则追加到现有文件
        is_append = append or i > 0
        result = crawler.process_url(url, download_images, save_to_excel, excel_filename, is_append)
        results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Web Crawler')
    parser.add_argument('--urls', nargs='+', help='URLs to process')
    parser.add_argument('--model-type', choices=['qwen', 'wenxin'], help='大模型类型')
    parser.add_argument('--model-api-key', help='大模型API密钥')
    parser.add_argument('--base-image-dir', default='downloads', help='图片保存目录')
    parser.add_argument('--zhihu-cookie', help='知乎cookie')
    parser.add_argument('--xiaohongshu-cookie', help='小红书cookie')
    parser.add_argument('--xiaohongshu-x-s', help='小红书x-s参数')
    parser.add_argument('--douyin-cookie', help='抖音cookie')
    parser.add_argument('--toutiao-cookie', help='头条cookie')
    parser.add_argument('--no-download-images', action='store_true', help='不下载图片')
    parser.add_argument('--no-save-to-excel', action='store_true', help='不保存到Excel')
    parser.add_argument('--excel-file', help='Excel文件名')
    parser.add_argument('--append', action='store_true', help='追加到现有文件')
    
    args = parser.parse_args()
    
    if not args.model_type or not args.model_api_key:
        parser.error("必须提供大模型类型和API密钥（--model-type 和 --model-api-key）")
    
    if args.urls:
        # 批量处理模式
        results = batch_process(
            args.urls,
            args.model_type,
            args.model_api_key,
            args.base_image_dir,
            args.zhihu_cookie,
            args.xiaohongshu_cookie,
            args.xiaohongshu_x_s,
            args.douyin_cookie,
            args.toutiao_cookie,
            not args.no_download_images,
            not args.no_save_to_excel,
            args.excel_file,
            args.append
        )
        
        # 统计处理结果
        success_count = sum(1 for r in results if r['success'])
        print(f"\n处理完成: 成功 {success_count}/{len(results)} 个URL")
    else:
        # 交互模式
        crawler = WebCrawler(
            model_type=args.model_type,
            model_api_key=args.model_api_key,
            base_image_dir=args.base_image_dir,
            zhihu_cookie=args.zhihu_cookie,
            xiaohongshu_cookie=args.xiaohongshu_cookie,
            xiaohongshu_x_s=args.xiaohongshu_x_s,
            douyin_cookie=args.douyin_cookie,
            toutiao_cookie=args.toutiao_cookie
        )
        
        while True:
            url = input("\n请输入URL (输入q退出): ")
            if url.lower() == 'q':
                break
                
            crawler.process_url(
                url,
                not args.no_download_images,
                not args.no_save_to_excel,
                args.excel_file,
                args.append
            )

if __name__ == "__main__":
    main() 