#!user/bin/env python3  
# -*- coding: utf8 -*- 

'''
Created on 2018年7月2日

该工具用于抓取静态页面，比如Gitbook站点等。
该工具会根据传入的首页页面，递归从页面内容中获取link方式CSS链接、JS链接、Html页面等下载至本地，
并自动组织其相对路径关系，直至全部下载完成
@author: Sunshine
'''

import io
import os
import re
import sys

from nt import link
from urllib import parse
from builtins import staticmethod

from bs4 import BeautifulSoup
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')  # 改变标准输出的默认编码
url_reg = re.compile(r'^(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]$', re.I)
img_reg_in_css = re.compile(r'url\([\'"]?([-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|])[\'"]?\)', re.I)  # url('abcd') or url("abcd")
url_param_reg = re.compile(r'(.+)\?(.+=.*&?)+', re.I)  # ?name=name01
css_type_reg = re.compile(r'\.css[l]?$', re.I)
html_type_reg = re.compile(r'\.htm[l]?$', re.I)

'''
Python基础之字符串为空或空格判断:
1、使用字符串长度判断 len(s) ==0  则字符串为空
2、判断是否字符串全部是空格 s.isspace() == True
3、字符串去空格及去指定字符。去掉空格后判断字符串长度 strip() 用于移除字符串头尾指定的字符（默认为空格或换行符）或字符序列。
去两边空格：str.strip()
去左空格：str.lstrip()
去右空格：str.rstrip()
去两边字符串：str.strip('d')，相应的也有lstrip，rstrip
'''


class DownloadUtil():
    
    loaded_pages = []  # 统计已加载页面，同时防止相同页面重复加载导致死循环
    
    # 初始化下载工具方法，index_url=传入开始解析的首页地址，disk_base_path=本地磁盘存储路径，request_header=浏览器拷贝的请求头
    def __init__(self, index_url, disk_base_path, request_header):
        self.index_url = index_url
        self.disk_base_path = disk_base_path
        self.request_header = request_header

    pass

    @staticmethod
    def url_encoder(url, encoding='utf-8'):
        if url is not None and '%' not in url:  # 未进行过编码字符串才执行编码，保证只编码一次
            url = parse.quote(url, encoding=encoding)
            
        return url

    pass

    @staticmethod
    def url_decoder(url, encoding='utf-8'):
        if url is not None and '%' in url:  # 进行过编码字符串才执行解码，保证只解码一次
            url = parse.unquote(url, encoding=encoding)
        
        return url

    pass

    # 通过urllib方式下载图片，亦可用于下载二进制文件，比如字体等
    @staticmethod
    def urllib_download_img(image_url, disk_addr):
        from urllib.request import urlretrieve
        urlretrieve(image_url, disk_addr)     

    pass
  
    # 通过requests方式下载图片，亦可用于下载二进制文件，比如字体等
    @staticmethod
    def request_download_img(image_url, disk_addr):
        with open(disk_addr, 'wb') as img:
            img.write(requests.get(image_url).content)                      

    pass
      
    # 通过requests并引入缓冲区方式下载图片，亦可用于下载二进制文件，比如字体等
    @staticmethod
    def chunk_download_img(image_url, disk_addr):
        get_request = requests.get(image_url, stream=True)    
        with open(disk_addr, 'wb') as img:
            for chunk in get_request.iter_content(chunk_size=32):
                img.write(chunk)

    pass
    
    # 解析传入的首页地址，若为资源，则转换为其父文件夹表示形式，比如http://baidu.com/a/b.html转换结果为http://baidu.com/a/
    @staticmethod
    def parse_index_url(index_url):
        index_base_url = index_url
        resource_file_name = os.path.basename(index_url);
        resource_file_path = os.path.dirname(index_url);
        if '.' in resource_file_name:
            index_base_url = resource_file_path
            
        return index_base_url

    pass
    
    # 将path解析N多文件夹形式保存至dirs列表中，比如a/b/c/d.html，则解析结果dirs=[a,b,c]
    @staticmethod
    def parse_path_to_dir(path, dirs):
        child_path = os.path.basename(path)
        parent_path = os.path.dirname(path)
        
        dirs.insert(0, child_path)
        
        # 字符长度不为0且不为空格，继续判断
        if len(parent_path) > 0 and not parent_path.isspace():
            DownloadUtil.parse_path_to_dir(parent_path, dirs)  # 递归解析
        
        return dirs

    pass

    # 将传入的地址url去除prefix后，解析N多文件夹存放至dirs列表，url比如http://www.baidu.com/a/b/c/d.html
    @staticmethod
    def parse_url_to_dir(url, prefix, dirs):
        full_path = os.path.dirname(url)
          
        # 去除URL前缀
        if full_path.startswith(prefix):
            full_path = full_path[len(prefix):len(full_path)]
        
        return DownloadUtil.parse_path_to_dir(full_path, dirs)    

    pass
    
    # 给出完整本地磁盘存储路径、完整资源链接路径、及资源请求头，下载资源并返回资源内容
    @staticmethod
    def download_resource_to_disk(full_disk_path, link_full_path, request_header):
        file_name = os.path.basename(link_full_path)
        if not full_disk_path.endswith(file_name):
            full_disk_path += file_name
        
        # 开启文件输出流
        full_disk_path = os.path.normpath(full_disk_path)
        data_file = open(full_disk_path, 'w', encoding='utf-8')
        
        # 下载资源
        file_data = requests.get(link_full_path, request_header)
        file_data.encoding = 'utf-8'
        
        # 写入磁盘
        data_file.write(file_data.text)
        data_file.close()  
        
        return file_data.text

    pass
 
    # 根据给定本地磁盘存储路径，将资源链接，可能为相对路径，以及资源首页访问地址，解析出资源应该存在至本地的绝对路径和资源绝对路径,
    # 比如disk_base_path=F://gitbook, href_link=a/b/c.html, url_prefix=http://www.baidu.com, 则结果为[F://gitbook/a/b/c.html,http://www.baidu.com/a/b/c.html]
    @staticmethod
    def resolve_one_link(disk_base_path, href_link, url_prefix):
        # 在路径后添加'/'
        if not disk_base_path.endswith('/'):
            disk_base_path += '/'
                
        # 非本站资源
        if url_reg.match(href_link) and not href_link.startswith(url_prefix):
            return print('third site resource, skip : {:s}'.format(href_link))

        # 本站全路径资源，不作处理
        elif href_link.startswith(url_prefix):
            pass
        
        # 非本站非全路径资源
        else:
            href_link = url_prefix + href_link
            
        # 拼接完整磁盘路径
        full_disk_path = disk_base_path + href_link[len(url_prefix):len(href_link)]
        
        # 如果文件已存在则跳过, 如果路径不存在则创建
        parent_disk_path = os.path.dirname(full_disk_path)
        if not os.path.exists(full_disk_path) and not os.path.exists(parent_disk_path):
            os.makedirs(parent_disk_path)
        
        return [full_disk_path, href_link]

    pass

    # 根据当前页面地址page_addr，解析得出link_path应有的路径。因为html中可能使用的是相对当前页面的相对路径，所以转换资源链接为绝对路径时需要考虑当前页面
    # 比如index_url=http://baidu.com, link_path=./a/b.html, page_addr=http://baidu.com/c/d.html,则解析结果link_path为:[http://baidu.com/c/a/b.html,....]
    @staticmethod
    def parse_relative_absolute_path(index_url, link_path, page_addr):
        origin_link_path = link_path
        origin_page_addr = page_addr
        
        # 已经是全链接路径的则不处理
        if not url_reg.match(link_path):
            # 处理当前页面与所处理链接的关系，得出最终链接地址
            if page_addr is not None and page_addr.startswith(index_url):
                page_addr = os.path.dirname(page_addr)
                page_addr = page_addr[len(index_url):len(page_addr)]
            if page_addr is not None and len(page_addr) > 0:
                link_path = os.path.normpath(page_addr + '/' + link_path)
                link_path = link_path.replace('\\', '/')
        
        # 去掉url参数
        if url_param_reg.search(link_path):
            print('before remove url param : {:s}'.format(link_path))
            link_path = url_param_reg.search(link_path).group(1)
        
        return [DownloadUtil.url_decoder(link_path), origin_link_path, origin_page_addr]

    pass

    # 下载图片、字体等类似二进制文件
    def download_img(self, img_path, page_addr=''):
        parse_infos = DownloadUtil.parse_relative_absolute_path(self.index_url, img_path, page_addr)   
        
        print('find link : {:s}, cur_page_addr : {:s}, resolved : {:s}'.format(parse_infos[1], parse_infos[2], parse_infos[0]))
        path_infos = DownloadUtil.resolve_one_link(self.disk_base_path, parse_infos[0], self.index_url)
        if path_infos is None:
            return print('skip...\n')
        
        full_disk_path = path_infos[0]
        
        if os.path.exists(full_disk_path):
            return print('existed resource : {:s}\n'.format(full_disk_path))        
        
        full_img_path = path_infos[1]
        if full_img_path in self.loaded_pages:
            return print('loaded img, skip : {:s}\n'.format(full_img_path))
        else:
            self.loaded_pages.append(full_img_path)
        
        # 一切准备完毕，准备正式下载
        print('begin download img : ' + path_infos[1])
        DownloadUtil.request_download_img(path_infos[1], path_infos[0])  # 下载图片
        print('save to {:s}, download finished ...\n'.format(path_infos[0]))
        
    pass
    
    # 下载文件文件至本地
    def download_pages(self, link_path, page_addr=''):
        parse_infos = DownloadUtil.parse_relative_absolute_path(self.index_url, link_path, page_addr)   
        
        print('find link : {:s}, cur_page_addr : {:s}, resolved : {:s}'.format(parse_infos[1], parse_infos[2], parse_infos[0]))
        path_infos = DownloadUtil.resolve_one_link(self.disk_base_path, parse_infos[0], self.index_url)
        if path_infos is None:
            return print('skip...\n')
        
        full_disk_path = path_infos[0]
        
        if os.path.exists(full_disk_path):
            return print('existed resource : {:s}\n'.format(full_disk_path))        
        
        full_link_path = path_infos[1]
        if full_link_path in self.loaded_pages:
            return print('loaded page, skip : {:s}\n'.format(full_link_path))
        else:
            self.loaded_pages.append(full_link_path)
        
        # 一切准备完毕，准备正式下载
        print('begin download file : ' + path_infos[1])
        child_page_data = DownloadUtil.download_resource_to_disk(path_infos[0], path_infos[1], self.request_header)
        print('save to {:s}, download finished ...\n'.format(path_infos[0]))
        
        # 如果为html页面，则解析该页面中所包含的资源
        if html_type_reg.search(link_path):
            DownloadUtil.download_and_resolve_one_page(self, child_page_data, page_addr=path_infos[1])
        
        # 如果为css页面，则提取页面中所包含的图片
        if css_type_reg.search(link_path):
            img_groups = img_reg_in_css.finditer(child_page_data)
            for match in img_groups:
                print('find img in css : {:s}'.format(match.group(0)))
                DownloadUtil.download_img(self, img_path=match.group(1), page_addr=path_infos[1])
        
    pass

    # 处理一个页面，此方法为入口
    def download_and_resolve_one_page(self, page_data, page_addr=''):
        # soup = BeautifulSoup(page_data,'html.parser')
        soup = BeautifulSoup(page_data, 'lxml')
        
        links = soup.find_all('link', attrs={'href':True})
        for link in links:
            self.download_pages(link['href'], page_addr)
        pass
                 
        scripts = soup.find_all('script', attrs={'src':True})
        for script in scripts:
            self.download_pages(script['src'], page_addr)
        pass
    
        htmls = soup.find_all('a', attrs={'href':True})
        for html in htmls:
            hrml_href = html['href']  # 非html链接页面，不处理
            if hrml_href.endswith('.html') or hrml_href.endswith('.htm'):
                self.download_pages(html['href'], page_addr)
        pass
    
        imgs = soup.find_all('img', attrs={'src':True})
        for img in imgs:
            self.download_img(img['src'], page_addr)
        pass

    pass


pass


# 抓取GitBook至本地
class Downloader():
    disk_base_path = 'I:\\DubboBook'  # 存储位置
    url = 'http://dubbo.apache.org/zh-cn/docs/user/quick-start.html'  # 首页地址
#     header = {
#     'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
#     'Accept-Encoding':'gzip, deflate, br',
#     'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8',
#     'Cache-Control':'no-cache',
#     'Connection':'keep-alive',
#     'Cookie':'BAIDUID=EAE828652413BFA5A1F456F7EC079999:FG=1; PSTM=1517375398; __cfduid=d30bb1b686a29402eaf778827ff047ae51521456533; BDUSS=I1NHIwdjR2QjYySW5FeTRHR3BwWFFZOUd6QkZFS3F-b21nZX54a2lzMld6bEZiQVFBQUFBJCQAAAAAAAAAAAEAAAAF6IEdYWliNjI4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJZBKluWQSpbMF; BD_UPN=12314353; BIDUPSID=EAE828652413BFA5A1F456F7EC079999; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; H_PS_PSSID=1455_21086; BD_CK_SAM=1; PSINO=7; BD_HOME=1; sugstore=0',
#     'Pragma':'no-cache',
#     'Upgrade-Insecure-Requests':'1',
#     'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
#     }
     
    header = {
        'Host':'dubbo.apache.org',
        'Connection':'keep-alive',
        'Pragma':'no-cache',
        'Cache-Control':'no-cache',
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        'Accept':'*/*',
        'Referer':'http://dubbo.apache.org/zh-cn/docs/user/quick-start.html',
        'Accept-Encoding':'gzip, deflate',
        'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8'
        }
     
    if __name__ == '__main__':
        
        index_base_url = DownloadUtil.parse_index_url(url)
        print('parsed index_url : {:s}'.format(index_base_url))
        
        # 初始化并配置下载器
        downloader = DownloadUtil(index_base_url, disk_base_path, header)
                    
        # 获取页面数据
        webdata = requests.get(url, header)
        webdata.encoding = 'utf-8'
                      
        # 下载入口页面
        downloader.download_and_resolve_one_page(webdata.text)
                      
        print('all finished,  {:d} loaded'.format(len(downloader.loaded_pages)))

    pass

        
pass    
