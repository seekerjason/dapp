#gemini

from flask import g, Flask, request,render_template, redirect, url_for, flash


import google.generativeai as genai
import os
import sqlite3
import datetime
try:
    conn = sqlite3.connect('log.db')
    conn.execute('CREATE TABLE user (name text, timestamp timestamp)')
    conn.close()
except Exception as eex:
    print("tabble alrready crreated")

import datetime

app=Flask(__name__)
app.config.from_mapping(
    # a default secret that should be overridden by instance config
    SECRET_KEY="AIzaSyC6IXrrGiBV9VMj-FYV-XsUun7FczKbAas",
)

currentuser=""

# google api is from https://makersuite.google.com

# Run locally based on the configuration file, uncomment the following two lines
app.config.from_pyfile("config.py", silent=True) 
api_key=app.config['SECRET_KEY']

# Run in colab, the uncomment the following two lines
#from google.colab import userdata
#api_key = userdata.get('makersuite')

# Run in render.com or locally based on the environment variable, then uncomment the following line. MAKESUITE_API_KEY need to add into Enviornment Variables
#api_key = os.getenv('MAKERSUITE_API_KEY')

genai.configure(api_key=api_key)
model= genai.GenerativeModel("gemini-2.0-flash-001") #gemini-1.5-flash

@app.route("/", methods=['GET', 'POST'])
def index():    
   return login()

@app.route("/main", methods=['GET', 'POST'])
def main():
    nextpage='main.html'
    if request.method=='POST':
        bvalue=request.form.get('instruction')
        print(f"bvalue={bvalue}")
        if bvalue=='Chatbot':
            return redirect(url_for("gemini"))
        elif bvalue=='Create':
            return redirect(url_for("create"))
        elif bvalue=='Delete':
            delete() #delete account and logout
            g.currentuser=""
            return redirect(url_for("index"))
        elif bvalue=='Logout':
            flash("Successfully Logout", "info")
            g.currentuser=""
            nextpage='index.html'
        elif bvalue=='Transfer':
            return redirect(url_for("paynow"))
        elif bvalue=='Telegram':
            nextpage='Telegram'
        else:
            flash(f"invalid Instruction ({bvalue})!",'error')
    
    return(render_template(nextpage))

def delete():
    global currentuser
    print(f"in delete, currentuser={currentuser} ")

    if currentuser == 'admin':
        flash("Admin user cannot be delete!")
    else:
        conn = sqlite3.connect('log.db')
        c = conn.cursor()
        sqlstr=f"delete from user where name='{currentuser}'"
        c.execute(sqlstr)
        conn.commit()
        c.close()
        conn.close()

@app.route("/create", methods=['GET', 'POST'])
def create():
    print("in create call!")
    users=[]
    nextpage='create.html'
    if request.method=='POST':
        instr=request.form.get("instruct")
        if instr=='back':
            nextpage='main.html'
        else:
            username=request.form.get('username')
            if username==None or username.strip()=='':
                flash("User Name cannot be empty!", 'error')
            else:
                print(f"username={username}")
                currentDateTime = datetime.datetime.now()
                conn = sqlite3.connect('log.db')
                c = conn.cursor()
                sqlstr=f"SELECT * FROM user WHERE name='{username}'"
                ret=c.execute(sqlstr)
                ret=ret.fetchone()
                if ret is None:      
                    c.execute('INSERT INTO user (name,timestamp) VALUES(?,?)',(username,currentDateTime))
                    conn.commit()
                    flash(f"User {username} have been created successfully!",'info')
                else:
                    flash(f"This username ({username}) has been created before! Please use different username!", "error")
                c.close()
                conn.close()
    if nextpage=='create.html':
        users=user_log()
    
    return (render_template(nextpage, users=users))

def login():
    global currentuser
    nextpage='index.html'
    if request.method=='POST':
        username=request.form.get('username')
        if username==None or username.strip()=='':
            flash("User Name cannot be empty!", 'error')
        else:
            print(f"username={username}")
            conn = sqlite3.connect('log.db')
            c = conn.cursor()
            sqlstr=f"SELECT * FROM user WHERE name='{username}'"
            ret=c.execute(sqlstr)
            ret=ret.fetchone()
            if ret is None:      
                currentuser=""
                flash(f"User {username} does not exist! Please login with an valid user name and create this user first!", "error")
            else:
                currentuser=username
                nextpage='main.html'
            c.close()
            conn.close()    
    print(f"After login, currentuser={currentuser} ")
    return render_template(nextpage)

def user_log():
    users=[]
    conn = sqlite3.connect('log.db')
    c = conn.cursor()
    sqlstr=f"select * from user where name <> 'admin' order by timestamp desc"
    c.execute(sqlstr)
    i=0
    for r in  c:
        users.append({'name':r[0],'timestamp':r[1]})
        i+=1
    c.close()
    conn.close()
    print(users)

    return users

 
@app.route("/gemini", methods=["GET", "POST"])
def gemini():
    return(render_template("gemini.html"))

@app.route("/gemini_reply", methods=["GET", "POST"])
def gemini_reply():
    r=None
    if request.method=='POST':
        if request.form.get("instruct") == 'back':
            return redirect(url_for('main'))
        else:
            q=request.form.get('q')
            print(f"{q}")
            r= model.generate_content(q)
            r=r.text
    return(render_template("gemini_reply.html", r=r))

if __name__=="__main__":
    app.run()

@app.route("/paynow", methods=["GET","POST"])
def paynow():
    return render_template("paynow.html")