# 🌟 校园微心愿交换平台

面向学生小需求难以被看见的问题 —— 发布小心愿、他人认领、完成反馈和感谢墙。

## 功能

- **心愿广场** — 按分类和状态浏览所有心愿
- **发布心愿** — 发布你的小心愿，可配图
- **认领机制** — 认领他人的心愿并帮助实现
- **状态流转** — 待认领 → 已认领 → 待确认 → 已完成
- **图片反馈** — 完成心愿后上传图片作为凭证
- **感谢墙** — 展示所有已完成的暖心瞬间
- **信用机制** — 完成+10分，心愿被完成+5分，放弃-5分

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

打开 http://127.0.0.1:5000

## 技术栈

- **后端**: Python Flask
- **数据库**: SQLite
- **前端**: Bootstrap 5 + Jinja2 模板

## 项目结构

```
├── app.py              # Flask 主应用
├── models.py           # 数据库模型
├── requirements.txt    # Python 依赖
├── static/
│   ├── css/style.css   # 自定义样式
│   └── uploads/        # 图片上传目录
└── templates/          # Jinja2 模板
    ├── base.html       # 基础布局
    ├── index.html      # 心愿广场
    ├── login.html      # 登录页
    ├── post_wish.html  # 发布心愿
    ├── wish_detail.html # 心愿详情
    ├── my_page.html    # 个人中心
    └── gratitude_wall.html # 感谢墙
```
