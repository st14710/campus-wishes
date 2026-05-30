# -*- coding: utf-8 -*-
"""校园微心愿交换平台"""

import os
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory
)
from werkzeug.utils import secure_filename
from models import get_db, init_db

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        name = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(UPLOAD_FOLDER, name))
        return name
    return ""


def current_user():
    if "user_id" in session:
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        db.close()
        return user
    return None


# ==================== 模板过滤器 ====================
@app.template_filter("status_label")
def status_label(s):
    m = {
        "pending": "待认领", "claimed": "已认领", "fulfilled": "待确认",
        "completed": "已完成", "cancelled": "已取消",
        "active": "进行中"
    }
    return m.get(s, s)


@app.template_filter("status_color")
def status_color(s):
    m = {
        "pending": "warning", "claimed": "info", "fulfilled": "primary",
        "completed": "success", "cancelled": "secondary",
        "active": "info"
    }
    return m.get(s, "secondary")



@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# ==================== 首页 ====================
@app.route("/")
def index():
    db = get_db()
    category = request.args.get("category", "")
    status = request.args.get("status", "pending")

    query = "SELECT w.*, u.name as poster_name FROM wishes w JOIN users u ON w.user_id=u.id WHERE 1=1"
    params = []

    if category:
        query += " AND w.category=?"
        params.append(category)
    if status:
        query += " AND w.status=?"
        params.append(status)

    query += " ORDER BY w.created_at DESC"

    wishes = db.execute(query, params).fetchall()

    # 统计
    stats = {
        "total": db.execute("SELECT COUNT(*) as c FROM wishes").fetchone()["c"],
        "completed": db.execute("SELECT COUNT(*) as c FROM wishes WHERE status='completed'").fetchone()["c"],
        "pending": db.execute("SELECT COUNT(*) as c FROM wishes WHERE status='pending'").fetchone()["c"],
    }

    db.close()
    return render_template("index.html", wishes=wishes, stats=stats,
                           category=category, status=status)


# ==================== 登录/注册 ====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        if not student_id or not name:
            flash("请填写学号和姓名", "danger")
            return redirect(url_for("login"))

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE student_id=?", (student_id,)).fetchone()
        if not user:
            db.execute("INSERT INTO users (student_id, name) VALUES (?,?)", (student_id, name))
            db.commit()
            user = db.execute("SELECT * FROM users WHERE student_id=?", (student_id,)).fetchone()

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        db.close()
        flash(f"欢迎回来，{user['name']}！", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("已退出登录", "info")
    return redirect(url_for("index"))


# ==================== 发布心愿 ====================
@app.route("/wish/post", methods=["GET", "POST"])
def post_wish():
    user = current_user()
    if not user:
        flash("请先登录", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "其他")
        wish_image = save_upload(request.files.get("image"))

        if not title or not description:
            flash("标题和描述不能为空", "danger")
            return render_template("post_wish.html", user=user)

        db = get_db()
        db.execute(
            "INSERT INTO wishes (user_id, title, description, category, wish_image) VALUES (?,?,?,?,?)",
            (user["id"], title, description, category, wish_image)
        )
        db.commit()
        db.close()

        flash("心愿发布成功！", "success")
        return redirect(url_for("index"))

    return render_template("post_wish.html", user=user)


# ==================== 心愿详情 ====================
@app.route("/wish/<int:wish_id>")
def wish_detail(wish_id):
    user = current_user()
    db = get_db()

    wish = db.execute("""
        SELECT w.*, u.name as poster_name, u.student_id as poster_sid, u.credit_score as poster_credit
        FROM wishes w JOIN users u ON w.user_id=u.id WHERE w.id=?
    """, (wish_id,)).fetchone()

    if not wish:
        db.close()
        flash("心愿不存在", "danger")
        return redirect(url_for("index"))

    # 当前认领信息
    claim = None
    if user:
        claim = db.execute(
            "SELECT * FROM claims WHERE wish_id=? AND user_id=? AND status!='cancelled'",
            (wish_id, user["id"])
        ).fetchone()

    # 所有活跃认领
    active_claims = db.execute("""
        SELECT c.*, u.name as claimer_name, u.credit_score as claimer_credit
        FROM claims c JOIN users u ON c.user_id=u.id
        WHERE c.wish_id=? AND c.status!='cancelled'
        ORDER BY c.created_at DESC
    """, (wish_id,)).fetchall()

    # 反馈
    feedbacks = db.execute("""
        SELECT f.*, u.name as author_name
        FROM feedback f JOIN users u ON f.user_id=u.id
        WHERE f.wish_id=? ORDER BY f.created_at DESC
    """, (wish_id,)).fetchall()

    db.close()
    return render_template("wish_detail.html", wish=wish, claim=claim,
                           active_claims=active_claims, feedbacks=feedbacks, user=user)


# ==================== 认领心愿 ====================
@app.route("/wish/<int:wish_id>/claim", methods=["POST"])
def claim_wish(wish_id):
    user = current_user()
    if not user:
        flash("请先登录", "danger")
        return redirect(url_for("login"))

    db = get_db()
    wish = db.execute("SELECT * FROM wishes WHERE id=?", (wish_id,)).fetchone()

    if not wish:
        db.close()
        flash("心愿不存在", "danger")
        return redirect(url_for("index"))

    if wish["user_id"] == user["id"]:
        db.close()
        flash("不能认领自己的心愿", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    if wish["status"] != "pending":
        db.close()
        flash("该心愿已被认领", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    # 检查是否已有认领
    existing = db.execute(
        "SELECT * FROM claims WHERE wish_id=? AND user_id=? AND status!='cancelled'",
        (wish_id, user["id"])
    ).fetchone()
    if existing:
        db.close()
        flash("你已经认领过这个心愿了", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    db.execute("INSERT INTO claims (wish_id, user_id) VALUES (?,?)", (wish_id, user["id"]))
    db.execute("UPDATE wishes SET status='claimed', updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    db.close()

    flash("认领成功！请尽快完成心愿哦~", "success")
    return redirect(url_for("wish_detail", wish_id=wish_id))


# ==================== 放弃认领 ====================
@app.route("/claim/<int:claim_id>/cancel", methods=["POST"])
def cancel_claim(claim_id):
    user = current_user()
    if not user:
        flash("请先登录", "danger")
        return redirect(url_for("login"))

    db = get_db()
    claim = db.execute("SELECT * FROM claims WHERE id=? AND user_id=?", (claim_id, user["id"])).fetchone()
    if not claim:
        db.close()
        flash("认领记录不存在", "danger")
        return redirect(url_for("index"))

    if claim["status"] == "completed":
        db.close()
        flash("已完成的心愿无法放弃", "warning")
        return redirect(url_for("wish_detail", wish_id=claim["wish_id"]))

    db.execute("UPDATE claims SET status='cancelled', updated_at=datetime('now','localtime') WHERE id=?", (claim_id,))
    # 如果心愿状态还是claimed，恢复为pending
    db.execute(
        "UPDATE wishes SET status='pending', updated_at=datetime('now','localtime') WHERE id=? AND status='claimed'",
        (claim["wish_id"],)
    )
    # 扣除信用分
    db.execute("UPDATE users SET credit_score=MAX(0, credit_score-5) WHERE id=?", (user["id"],))
    db.commit()
    db.close()

    flash("已放弃认领，信用分 -5", "warning")
    return redirect(url_for("wish_detail", wish_id=claim["wish_id"]))


# ==================== 提交完成反馈 ====================
@app.route("/wish/<int:wish_id>/fulfill", methods=["POST"])
def fulfill_wish(wish_id):
    user = current_user()
    if not user:
        flash("请先登录", "danger")
        return redirect(url_for("login"))

    db = get_db()
    claim = db.execute(
        "SELECT * FROM claims WHERE wish_id=? AND user_id=? AND status='active'",
        (wish_id, user["id"])
    ).fetchone()

    if not claim:
        db.close()
        flash("你没有认领这个心愿，或认领已失效", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    content = request.form.get("content", "").strip()
    image = save_upload(request.files.get("image"))

    if not content and not image:
        flash("请填写反馈内容或上传图片", "danger")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    db.execute(
        "INSERT INTO feedback (wish_id, claim_id, user_id, content, image) VALUES (?,?,?,?,?)",
        (wish_id, claim["id"], user["id"], content, image)
    )
    db.execute("UPDATE claims SET status='fulfilled', updated_at=datetime('now','localtime') WHERE id=?", (claim["id"],))
    db.execute("UPDATE wishes SET status='fulfilled', updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    db.close()

    flash("完成反馈已提交，等待发布者确认~", "success")
    return redirect(url_for("wish_detail", wish_id=wish_id))


# ==================== 发布者确认完成 ====================
@app.route("/wish/<int:wish_id>/confirm", methods=["POST"])
def confirm_wish(wish_id):
    user = current_user()
    if not user:
        flash("请先登录", "danger")
        return redirect(url_for("login"))

    db = get_db()
    wish = db.execute("SELECT * FROM wishes WHERE id=? AND user_id=?", (wish_id, user["id"])).fetchone()

    if not wish:
        db.close()
        flash("无权操作", "danger")
        return redirect(url_for("index"))

    if wish["status"] != "fulfilled":
        db.close()
        flash("心愿尚未被标记为完成", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    rating = int(request.form.get("rating", 5))
    claim = db.execute(
        "SELECT * FROM claims WHERE wish_id=? AND status='fulfilled' ORDER BY updated_at DESC LIMIT 1",
        (wish_id,)
    ).fetchone()

    if claim:
        db.execute("UPDATE claims SET status='completed', updated_at=datetime('now','localtime') WHERE id=?", (claim["id"],))
        # 认领者 +10 信用分
        db.execute("UPDATE users SET credit_score=credit_score+10 WHERE id=?", (claim["user_id"],))
        # 发布者 +5 信用分
        db.execute("UPDATE users SET credit_score=credit_score+5 WHERE id=?", (user["id"],))

    db.execute("UPDATE wishes SET status='completed', updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    db.close()

    flash("心愿已确认完成！双方信用分已更新 ", "success")
    return redirect(url_for("wish_detail", wish_id=wish_id))


# ==================== 取消心愿 ====================
@app.route("/wish/<int:wish_id>/cancel", methods=["POST"])
def cancel_wish(wish_id):
    user = current_user()
    if not user:
        flash("请先登录", "danger")
        return redirect(url_for("login"))

    db = get_db()
    wish = db.execute("SELECT * FROM wishes WHERE id=? AND user_id=?", (wish_id, user["id"])).fetchone()
    if not wish:
        db.close()
        flash("无权操作", "danger")
        return redirect(url_for("index"))

    if wish["status"] not in ("pending",):
        db.close()
        flash("只能取消待认领的心愿", "warning")
        return redirect(url_for("wish_detail", wish_id=wish_id))

    db.execute("UPDATE wishes SET status='cancelled', updated_at=datetime('now','localtime') WHERE id=?", (wish_id,))
    db.commit()
    db.close()

    flash("心愿已取消", "info")
    return redirect(url_for("wish_detail", wish_id=wish_id))


# ==================== 感谢墙 ====================
@app.route("/gratitude")
def gratitude_wall():
    db = get_db()

    feedbacks = db.execute("""
        SELECT f.*, w.title as wish_title,
               u1.name as helper_name, u1.credit_score as helper_credit,
               u2.name as poster_name
        FROM feedback f
        JOIN wishes w ON f.wish_id = w.id
        JOIN users u1 ON f.user_id = u1.id
        JOIN users u2 ON w.user_id = u2.id
        WHERE w.status = 'completed'
        ORDER BY f.created_at DESC
    """).fetchall()

    # top helpers
    top_helpers = db.execute("""
        SELECT u.name, u.credit_score, u.student_id,
               COUNT(c.id) as completed_count
        FROM users u
        LEFT JOIN claims c ON u.id = c.user_id AND c.status = 'completed'
        GROUP BY u.id
        ORDER BY u.credit_score DESC
        LIMIT 10
    """).fetchall()

    db.close()
    return render_template("gratitude_wall.html", feedbacks=feedbacks, top_helpers=top_helpers)


# ==================== 我的页面 ====================
@app.route("/my")
def my_page():
    user = current_user()
    if not user:
        flash("请先登录", "warning")
        return redirect(url_for("login"))

    db = get_db()

    my_wishes = db.execute("""
        SELECT * FROM wishes WHERE user_id=? ORDER BY created_at DESC
    """, (user["id"],)).fetchall()

    my_claims = db.execute("""
        SELECT c.*, w.title as wish_title, w.status as wish_status
        FROM claims c JOIN wishes w ON c.wish_id = w.id
        WHERE c.user_id=? AND c.status!='cancelled'
        ORDER BY c.created_at DESC
    """, (user["id"],)).fetchall()

    db.close()
    return render_template("my_page.html", user=user, my_wishes=my_wishes, my_claims=my_claims)


# ==================== 启动 ====================
if __name__ == "__main__":
    init_db()
    print("[OK] 校园微心愿交换平台已启动 → http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
