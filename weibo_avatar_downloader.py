#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博用户头像下载器
功能：从微博个人主页下载用户头像，并记录头像昵称关系到CSV文件
支持配置随机停留时间和性别解析功能
"""

import requests
import os
import csv
import json
import time
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def load_config(config_file='config.json'):
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：配置文件 {config_file} 未找到")
        return None
    except json.JSONDecodeError:
        print(f"错误：配置文件 {config_file} 格式不正确")
        return None

def read_user_info(file_path):
    """读取用户信息列表文件（格式：用户ID 用户名）"""
    user_info_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 1:
                        user_id = parts[0].strip()
                        username = parts[1].strip() if len(parts) >= 2 else ""
                        user_info_list.append((user_id, username))
        print(f"成功读取 {len(user_info_list)} 条用户信息")
        return user_info_list
    except FileNotFoundError:
        print(f"错误：用户信息文件 {file_path} 未找到")
        return []

def get_last_processed_user(csv_file):
    """获取CSV文件中最后处理的用户ID，用于断点续传"""
    if not os.path.exists(csv_file):
        return None
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                last_row = rows[-1]
                return last_row['user_id']
        return None
    except Exception as e:
        print(f"警告：读取CSV文件时发生异常 - {e}")
        return None

def parse_gender(text):
    """从文本中解析性别信息"""
    if '男' in text:
        return '男'
    if '女' in text:
        return '女'
    return ''

def get_user_info_web(user_id, config):
    """通过微博.cn网页解析获取用户信息（优先方法）"""
    url = f"https://weibo.cn/{user_id}/profile"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://weibo.cn/",
    }
    
    if config.get('cookie'):
        headers["Cookie"] = config['cookie']
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        # 检查是否是访问控制/验证页面
        if "Sina Visitor System" in response.text or "验证页面" in response.text or "安全验证" in response.text:
            print(f"警告：用户 {user_id} 页面返回访问控制页面")
            return None, None, ""
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找头像URL（根据提供的HTML结构）
        avatar_url = None
        td_tags = soup.find_all('td', valign='top')
        for td in td_tags:
            a_tag = td.find('a', href=re.compile(r'\/avatar\?'))
            if a_tag:
                img_tag = a_tag.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    avatar_url = img_tag['src']
                    break
        
        if not avatar_url:
            for img in soup.find_all('img'):
                if img and 'src' in img.attrs:
                    src = img['src']
                    if 'sinaimg.cn' in src or 'avatar' in src.lower():
                        avatar_url = src
                        break
        
        # 查找昵称（根据提供的HTML结构）
        nickname = None
        ctt_tags = soup.find_all('span', class_='ctt')
        for span in ctt_tags:
            text = span.get_text(strip=True)
            if text:
                match = re.match(r'^([^\s]+)', text)
                if match:
                    nickname = match.group(1)
                    break
        
        if not nickname:
            for tag in ['h1', 'h2', 'h3', 'div', 'span']:
                elements = soup.find_all(tag)
                for el in elements:
                    text = el.get_text(strip=True)
                    if text and len(text) < 20 and not text.isdigit() and '微博' not in text and '加关注' not in text:
                        nickname = text
                        break
                if nickname:
                    break
        
        # 查找性别信息
        gender = ""
        for span in ctt_tags:
            text = span.get_text(strip=True)
            parsed_gender = parse_gender(text)
            if parsed_gender:
                gender = parsed_gender
                break
        
        if not avatar_url or not nickname:
            print(f"警告：用户 {user_id} 信息不完整，头像URL: {avatar_url}, 昵称: {nickname}")
        
        return avatar_url, nickname, gender
    
    except Exception as e:
        print(f"错误：网页解析时发生异常 - {e}")
        return None, None, ""

def get_user_info_api(user_id, config):
    """通过微博API获取用户信息（备用方法）"""
    api_url = f"https://weibo.com/ajax/profile/info?uid={user_id}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": f"https://weibo.com/u/{user_id}",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    }
    
    if config.get('cookie'):
        headers["Cookie"] = config['cookie']
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('ok') == 1 and data.get('data'):
                user = data.get('data', {})
                
                # 获取头像URL
                avatar_url = user.get('avatar_hd') or user.get('profile_image_url')
                
                # 获取昵称
                nickname = user.get('screen_name')
                
                # 获取性别
                gender = user.get('gender', '')
                if gender == 'm':
                    gender = '男'
                elif gender == 'f':
                    gender = '女'
                else:
                    gender = ''
                
                if avatar_url and nickname:
                    print(f"成功通过API获取用户 {user_id} 信息")
                    return avatar_url, nickname, gender
                else:
                    print(f"警告：API返回的用户 {user_id} 信息不完整")
            else:
                print(f"警告：API返回错误 - {data.get('msg')}")
        else:
            print(f"错误：API请求失败，状态码：{response.status_code}")
    
    except Exception as e:
        print(f"错误：API请求时发生异常 - {e}")
    
    return None, None, ""

def download_avatar(user_id, avatar_url, output_dir):
    """下载用户头像"""
    if not avatar_url:
        return None
    
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        extension = 'jpg'
        if avatar_url.endswith('.jpg') or avatar_url.endswith('.jpeg'):
            extension = 'jpg'
        elif avatar_url.endswith('.png'):
            extension = 'png'
        elif avatar_url.endswith('.gif'):
            extension = 'gif'
        
        filename = f"{user_id}.{extension}"
        file_path = os.path.join(output_dir, filename)

        # 检查文件是否已存在
        if os.path.exists(file_path):
            print(f"用户 {user_id} 的头像已存在，跳过下载")
            return file_path
        
        response = requests.get(avatar_url, timeout=10)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"成功下载用户 {user_id} 的头像")
            return file_path
        else:
            print(f"错误：下载用户 {user_id} 头像失败，状态码：{response.status_code}")
            return None
    
    except Exception as e:
        print(f"错误：下载用户 {user_id} 头像时发生异常 - {e}")
        return None

def save_to_csv(data_list, csv_file, append=False):
    """保存到CSV文件"""
    try:
        mode = 'a' if append and os.path.exists(csv_file) else 'w'
        with open(csv_file, mode, encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'username', 'nickname', 'avatar_file', 'gender'])
            
            if mode == 'w' or (mode == 'a' and os.path.getsize(csv_file) == 0):
                writer.writeheader()
            
            writer.writerows(data_list)
        
        print(f"成功保存 {len(data_list)} 条记录到 {csv_file}")
    except Exception as e:
        print(f"错误：保存CSV文件时发生异常 - {e}")

def random_pause(config, page_num):
    """根据配置随机暂停"""
    scrape_config = config.get('scrape_config', {})
    min_pause = scrape_config.get('min_pause', 2)
    max_pause = scrape_config.get('max_pause', 4)
    min_pages = scrape_config.get('min_pages', 1)
    max_pages = scrape_config.get('max_pages', 3)
    
    # 计算是否需要暂停（每 n 到 m 页暂停一次）
    if page_num > 0 and (page_num % random.randint(min_pages, max_pages)) == 0:
        delay = random.uniform(min_pause, max_pause)
        print(f"随机暂停 {delay:.2f} 秒")
        time.sleep(delay)

def main():
    """主函数"""
    print("=" * 50)
    print("微博用户头像下载器")
    print("=" * 50)
    
    config = load_config()
    if not config:
        return
    
    if not config.get('cookie'):
        print("警告：未配置Cookie，程序可能无法正常工作")
        print("建议配置Cookie以提高成功率")
        print()
    
    user_info_list = read_user_info(config['avatar_sync_file'])
    if not user_info_list:
        print("没有找到用户信息，程序结束")
        return
    
    last_processed_user = get_last_processed_user(config['csv_file'])
    start_index = 0
    
    if last_processed_user:
        for i, (user_id, _) in enumerate(user_info_list):
            if user_id == last_processed_user:
                start_index = i + 1
                print(f"发现上次处理的位置，将从索引 {start_index} 开始继续")
                break
        else:
            print(f"警告：未在用户信息列表中找到上次处理的用户ID {last_processed_user}，将从头开始")
    
    results = []
    for i in range(start_index, len(user_info_list)):
        user_id, username = user_info_list[i]
        print(f"\n处理用户 {i+1}/{len(user_info_list)}: {user_id} ({username})")
        
        # 优先通过网页解析获取用户信息
        avatar_url, nickname, gender = get_user_info_web(user_id, config)
        
        # 如果网页解析失败，尝试通过API获取
        if not avatar_url or not nickname:
            print("网页解析失败，尝试通过API获取")
            avatar_url, nickname, gender = get_user_info_api(user_id, config)
        
        # 下载头像
        avatar_file = None
        if avatar_url:
            avatar_file = download_avatar(user_id, avatar_url, config['output_dir'])
        
        # 只有在成功获取到头像和昵称时才保存到CSV
        if avatar_file and nickname:
            results.append({
                'user_id': user_id,
                'username': username,
                'nickname': nickname,
                'avatar_file': os.path.basename(avatar_file) if avatar_file else '',
                'gender': gender
            })
            
            save_to_csv(results, config['csv_file'], append=True)
            results.clear()
        else:
            print(f"用户 {user_id} 信息不完整（头像或昵称缺失），不保存到CSV")
        
        # 随机暂停
        random_pause(config, i + 1)
    
    print("\n" + "=" * 50)
    print("程序执行完成！")
    print("=" * 50)
    print(f"头像下载到目录: {config['output_dir']}")
    print(f"用户信息保存到: {config['csv_file']}")

if __name__ == "__main__":
    main()
