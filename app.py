# -*- coding: utf-8 -*-
from flask import Flask, request, render_template_string, jsonify, redirect, url_for
import jwt
import datetime
import secrets
import os

app = Flask(__name__)
# 请务必将此密钥更改为一个强大且保密的随机字符串!!!
app.config['SECRET_KEY'] = secrets.token_urlsafe(32)

# 读取HTML文件
with open('test.html', 'r', encoding='utf-8') as f:
    TEST_HTML = f.read()
with open('report.html', 'r', encoding='utf-8') as f:
    REPORT_HTML = f.read()

def generate_test_token():
    """生成一个用于测试页的一次性令牌，有效期为36小时"""
    payload = {
        'type': 'test_access',
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=36)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def generate_report_token(data):
    """生成一个包含报告数据的永久令牌"""
    payload = {
        'type': 'report_data',
        'data': data,
        'iat': datetime.datetime.utcnow()
        # 不设置exp，使其永久有效
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    """解码并验证JWT令牌"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, '链接已过期'
    except jwt.InvalidTokenError:
        return None, '无效的链接'

@app.route('/')
def index():
    """首页，生成一个新的测试链接"""
    new_test_link = url_for('access_test', token=generate_test_token(), _external=True)
    return f'''
    <html>
    <head><title>马年开运 · 测试链接生成器</title></head>
    <body style="font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px;">
        <h1 style="color: #c44f4f;">✨ 马年开运 · 测试链接生成器</h1>
        <p>点击下方按钮生成一个新的一次性测试链接（36小时内有效）：</p>
        <a href="{new_test_link}" style="display: inline-block; background: #c44f4f; color: white; padding: 12px 24px; border-radius: 30px; text-decoration: none; margin-top: 20px;">生成新链接</a>
        <p style="margin-top: 30px; color: #666;">当前生成的链接：<br><a href="{new_test_link}">{new_test_link}</a></p>
    </body>
    </html>
    '''

@app.route('/test/<token>')
def access_test(token):
    """用户通过一次性链接访问测试页面"""
    payload, error = decode_token(token)
    if error:
        return f'<h1>错误</h1><p>{error}</p>'
    
    if payload.get('type') != 'test_access':
        return '<h1>错误</h1><p>无效的链接类型</p>'
    
    # 返回测试页面
    return TEST_HTML

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """接收前端提交的数据，生成报告链接并返回"""
    data = request.get_json()
    test_token = data.get('token')
    birth = data.get('birth')
    start = data.get('start')
    style = data.get('style')

    # 验证测试token的有效性
    payload, error = decode_token(test_token)
    if error:
        return jsonify({'error': f'测试链接无效或已过期: {error}'}), 400
    
    # 验证必填字段
    if not all([birth, start, style]):
        return jsonify({'error': '缺少必要参数'}), 400

    # 准备要存储在报告token中的数据
    report_data = {
        'birth': birth,
        'start': start,
        'style': style
    }
    
    # 生成永久的报告token
    report_token = generate_report_token(report_data)
    redirect_url = url_for('access_report', token=report_token, _external=True)
    
    return jsonify({'redirect_url': redirect_url})

@app.route('/report/<token>')
def access_report(token):
    """用户通过永久链接查看报告"""
    payload, error = decode_token(token)
    if error:
        return f'<h1>错误</h1><p>{error}</p>'
    
    if payload.get('type') != 'report_data':
        return '<h1>错误</h1><p>无效的报告链接</p>'
    
    report_data = payload.get('data', {})
    birth = report_data.get('birth', '1994-12-15')
    start = report_data.get('start', '')
    style = report_data.get('style', 'neutral')

    # 将数据注入到report.html模板中
    script_to_inject = f'''
    <script>
    var BIRTH_DATE = "{birth}";
    var START_DATE = "{start}";
    var STYLE_PREF = "{style}";
    </script>
    '''
    report_html_with_data = REPORT_HTML.replace('</head>', script_to_inject + '</head>')
    
    return report_html_with_data

if __name__ == '__main__':
    # 在生产环境中，请使用更健壮的服务器，如gunicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
