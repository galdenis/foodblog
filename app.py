from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename
from flask_marshmallow import Marshmallow
from flask_restful import Api, Resource

with open('config.json', 'r') as c:
    params = json.load(c)['params']

app = Flask(__name__)
app.secret_key = 'secret-key'
marshmallow = Marshmallow(app)
api = Api(app)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

local = True
if local:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:12345678@127.0.0.1/blog'
else: 
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://bd76e9f60062ae:cd50826c@eu-cdbr-west-03.cleardb.net/heroku_eab3a7d732b7a56'

db = SQLAlchemy(app)


# database models


class Contact(db.Model):
    SerialNum = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Phone = db.Column(db.String(20), nullable=False)
    Msg = db.Column(db.String(100), nullable=False)
    Date = db.Column(db.String(12), nullable=False)


class Accounts(db.Model):
    Name = db.Column(db.String(50), nullable=False)
    Email = db.Column(db.String(50), nullable=False)
    Username = db.Column(db.String(20), nullable=False, primary_key=True)
    Password = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Integer, nullable=False)


class Posts(db.Model):
    SerialNum = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(50), nullable=False)
    SubTitle = db.Column(db.String(50), nullable=False)
    Content = db.Column(db.String(120), nullable=False)
    PostedBy = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(25), nullable=False)
    Approved = db.Column(db.Integer, nullable=False)
    Date = db.Column(db.String(12), nullable=False)
    img_path = db.Column(db.String(100), nullable=False)


# serializer for posts Api


class PostSchema(marshmallow.Schema):
    class Meta:
        fields = ("SerialNum", "Title", "SubTitle", "Content",
                  "PostedBy", "slug", "Date", "img_path")
        model = Posts


posts_schema = PostSchema(many=True)


# posts api endpoint


class PostListResource(Resource):
    def get(self):
        posts = Posts.query.filter_by(Approved=1).all()
        return posts_schema.dump(posts)


api.add_resource(PostListResource, '/posts_api')


# application endpoints


@app.route("/")
def home():
    posts = Posts.query.filter_by(Approved=1).all()
    return render_template('index.html', params=params, posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contact(Name=name, Email=email, Phone=phone,
                        Msg=message, Date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        flash('Thanks for contacting. We will get back to you soon!', 'info')
    return render_template('contact.html', params=params)


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=post)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin_username']:
        posts = Posts.query.filter_by(Approved=1).all()
        non_approved_posts = Posts.query.filter_by(Approved=0).all()
        non_approved_users = Accounts.query.filter_by(status=0).all()
        return render_template('dashboard.html', params=params, posts=posts,
                               non_approved_posts=non_approved_posts, non_approved_users=non_approved_users)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == params['admin_username'] and password == params['admin_password']:
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
        else:
            flash('Incorrect Username or Password!', 'warning')
            return render_template('login.html', params=params)
    else:
        return render_template('login.html', params=params)


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/edit/<string:SerialNum>", methods=['GET', 'POST'])
def edit(SerialNum):
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            title = request.form.get('title')
            SubTitle = request.form.get('SubTitle')
            slug = request.form.get('slug')
            img_path = request.form.get('img_path')
            content = request.form.get('content')
            date = datetime.now()
            if SerialNum == '0':
                post = Posts(Title=title, SubTitle=SubTitle, Content=content,
                             slug=slug, img_path=img_path, Date=date, Approved=1, PostedBy='Admin')
                db.session.add(post)
                db.session.commit()
                return redirect('/')
            else:
                post = Posts.query.filter_by(SerialNum=SerialNum).first()
                post.Title = title
                post.SubTitle = SubTitle
                post.Content = content
                post.slug = slug
                post.img_path = img_path
                db.session.commit()
                return redirect(f"/edit/{SerialNum}")
        post = Posts.query.filter_by(SerialNum=SerialNum).first()
        return render_template('edit.html', params=params, post=post, SerialNum=SerialNum)


@app.route("/uploader", methods=['GET', 'POST'])
def upload():
    if "user" in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            f = request.files['post-bg']
            f.save(os.path.join(
                'static/assets/img', secure_filename(f.filename)))
            flash('Uploaded Successfully!', 'success')
            return redirect('/dashboard')


@app.route("/delete/<string:SerialNum>", methods=['GET', 'POST'])
def delete(SerialNum):
    if 'user' in session and session['user'] == params['admin_username']:
        post = Posts.query.filter_by(SerialNum=SerialNum).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/approve/<string:SerialNum>", methods=['GET', 'POST'])
def approve(SerialNum):
    if 'user' in session and session['user'] == params['admin_username']:
        post = Posts.query.filter_by(SerialNum=SerialNum).first()
        post.Approved = 1
        db.session.commit()
    return redirect('/dashboard')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        if name == '' or email == '' or username == '' or password == '':
            flash('Enter data in all fields!', 'warning')
            return render_template('user-signup.html', params=params)
        user = Accounts.query.filter_by(Username=username).first()
        user_2 = Accounts.query.filter_by(Email=email).first()
        if user:
            flash('Username already exists!', 'warning')
        elif user_2:
            flash('Email already exists!', 'warning')
        else:
            entry = Accounts(Name=name, Email=email, Username=username,
                             Password=password, status=0)
            db.session.add(entry)
            db.session.commit()
            flash('Information Submitted. You can login after admin approval!', 'success')
    return render_template('user-signup.html', params=params)


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if 'user-session' in session:
        return redirect('/profile')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Accounts.query.filter_by(Username=username).first()
        if user is None:
            flash('Username does not exists!', 'warning')
            return render_template('user-login.html', params=params)
        if user.Password != password:
            flash('Incorrect Password!', 'warning')
            return render_template('user-login.html', params=params)
        if user.status == 0:
            flash('Account under review!', 'warning')
            return render_template('user-login.html', params=params)
        if user.Username == username and user.Password == password:
            session['user-session'] = username
            return redirect('/profile')

    return render_template('user-login.html', params=params)


@app.route('/profile')
def user_profile():
    if 'user-session' in session:
        user = Accounts.query.filter_by(
            Username=session['user-session']).first()
        posts = Posts.query.filter_by(PostedBy=session['user-session']).all()
        return render_template('profile.html', params=params, user=user, posts=posts)
    else:
        return redirect('/')


@app.route('/logout-user')
def user_logout():
    session.pop('user-session')
    return redirect('/login')


@app.route("/edit/user/post/<string:SerialNum>", methods=['GET', 'POST'])
def edit_user_posts(SerialNum):
    if 'user-session' in session:
        if request.method == 'POST':
            title = request.form.get('title')
            SubTitle = request.form.get('SubTitle')
            slug = request.form.get('slug')
            img_path = request.form.get('img_path')
            content = request.form.get('content')
            date = datetime.now()
            if SerialNum == '0':
                post = Posts(Title=title, SubTitle=SubTitle, Content=content, slug=slug, img_path=img_path,
                             Date=date, PostedBy=session['user-session'], Approved=0)
                db.session.add(post)
                db.session.commit()
                return redirect('/')
            else:
                post = Posts.query.filter_by(SerialNum=SerialNum).first()
                post.Title = title
                post.SubTitle = SubTitle
                post.Content = content
                post.slug = slug
                post.img_path = img_path
                post.Approved = 0
                db.session.commit()
                return redirect(f"/edit/user/post/{SerialNum}")
        post = Posts.query.filter_by(SerialNum=SerialNum).first()
        return render_template('user-edit.html', params=params, post=post, SerialNum=SerialNum)


@app.route("/delete/user/post/<string:SerialNum>", methods=['GET', 'POST'])
def delete_user_post(SerialNum):
    if 'user-session' in session:
        post = Posts.query.filter_by(SerialNum=SerialNum).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/login')


@app.route("/user/upload", methods=['GET', 'POST'])
def user_upload():
    if "user-session" in session:
        if request.method == 'POST':
            f = request.files['post-bg']
            f.save(os.path.join(
                'static/assets/img', secure_filename(f.filename)))
            flash('Uploaded Successfully!', 'success')
            return redirect('/login')


@app.route("/approve/user/<string:Username>", methods=['GET', 'POST'])
def approve_user(Username):
    if 'user' in session and session['user'] == params['admin_username']:
        user = Accounts.query.filter_by(Username=Username).first()
        user.status = 1
        db.session.commit()
    return redirect('/dashboard')


if __name__ == '__main__':
    app.run()
