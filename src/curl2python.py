# coding=utf-8

import os
import re
import json
import argparse
import shlex
from urllib.parse import unquote

from yapf.yapflib.yapf_api import FormatCode

files = {
    "py_template": "py_template.py",
}


def clear_case(file_name):
    if os.path.exists(file_name):
        os.remove(file_name)


def write_to_file(file_name, data):
    with open(file_name, mode="w", encoding="utf-8") as f:
        f.write(data)


def parse_curl_cmd(curl_cmd):
    parser = argparse.ArgumentParser()
    parser.add_argument('command')
    parser.add_argument('url')
    parser.add_argument('-d', '--data', '--data-binary', '--data-raw', '--data-ascii', "--data-urlencode")
    parser.add_argument('-H', '--header', action='append', default=[])
    args, _ = parser.parse_known_args(shlex.split(curl_cmd.replace(" $", " ").replace(r'\u0021', '!')))
    method = "post" if args.data else "get"
    p = args.url.find("?")
    if p >= 0:
        url, query = args.url[:p], args.url[p + 1:]
    else:
        url, query = args.url, ""

    params = dict(re.findall(r'([^=&]+)=([^=&]*)', unquote(query)))
    headers = {}
    cookie_str = ""
    for header in args.header:
        try:
            k, v = map(str.strip, header.split(': ', 1))
        except ValueError:
            k = header.split(':', 1)[0].strip().strip(';')
            v = ''
        if k.lower() == "cookie":
            cookie_str = v
        else:
            headers[k] = v
    cookies = {}
    for i in cookie_str.split(';'):
        item = i.split('=')
        cookies[item[0]] = '='.join(item[1:])
    content_type = headers.get('Content-Type') or headers.get('content-type') or headers.get('Content-type')
    data = {}
    if args.data:
        if "application/json" in content_type.lower():
            data = json.loads(args.data)
        elif "application/x-www-form-urlencoded" in content_type.lower():
            data = dict(re.findall(r'([^=&]+)=([^=&]*)', unquote(args.data)))

    return dict(
        url=url,
        params=params,
        headers=headers,
        method=method,
        cookies=cookies,
        cookies_str=cookie_str,
        content_type=content_type,
        data=data
    )


def curl_to_python(in_path, out_path, name):
    try:
        f = open(in_path, 'r')
        curl_data = f.read()
        f.close()
        if out_path is None:
            out_path = os.path.dirname(in_path)
        if name is None:
            name = 'py_template.py'
        context = parse_curl_cmd(curl_data)
        py_template = """import requests

headers = {{headers}}
cookies = {{cookies}}
data = {{data}}
params = {{params}}
response = requests.{{method}}('{{url}}', headers=headers, params=params, cookies=cookies, data=data)
print(response.text)

            """
        if context['method'] == 'get':
            py_template = py_template.replace(', data=data', '').replace('data = {{data}}', '')
        else:
            py_template = py_template.replace('{{data}}', str(context['data']))
        py_template = py_template. \
            replace('{{headers}}', str(context['headers'])). \
            replace('{{cookies}}', str(context['cookies'])). \
            replace('{{params}}', str(context['params'])). \
            replace('{{method}}', str(context['method'])). \
            replace('{{url}}', str(context['url']))

        py_template = str(FormatCode(py_template)[0])
        space_re_expression = re.compile("(:\n\s*?)'", re.S)
        space_result_list = re.findall(space_re_expression, py_template)
        for space in space_result_list:
            py_template = py_template.replace(space, ": ")
        write_to_file(os.path.join(out_path, name), py_template)
    except Exception as e:
        raise e


def get_args():
    arg = argparse.ArgumentParser()
    arg.add_argument("input", help=r"指定保存curl命令的文件路径。例子：D:\curl.txt")
    arg.add_argument("-o", "--output", help="文件输出目录，不传则与源文件同目录")
    arg.add_argument("-n", "--name", default="py_template.py", help="输出的python文件名")
    # 解析参数
    args = arg.parse_args()
    return args


if __name__ == '__main__':
    args = get_args()
    curl_to_python(args.input, args.output, args.name)
