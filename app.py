#gemini

from flask import g, Flask, request,render_template, redirect, url_for, flash
import google.generativeai as genai
import os
import sqlite3
import datetime
import time
import requests
import json
import pandas as pd

#====================initialize app=====================================
app=Flask(__name__)
#for local testing only, when depoly to Render, remove those keys
app.config.from_mapping(
    # a default secret that should be overridden by instance config
    GEMINI_KEY="",
    TELEGRAM_KEY=""
)
currentuser=""
usersession={}

# =================== manage key =======================================
def getkey(key):
    #for local testing only
    api_key=app.config[key]
    if api_key=='':
        # get from environment variables
        api_key = os.getenv(key)
        if api_key is None or api_key=="":
            with open('config.json', 'r') as file:
                ret=json.load(file)
                api_key=ret[key]
    return api_key            
            

# ================================Initial Database============================
try:
    conn = sqlite3.connect('log.db')
    conn.execute('CREATE TABLE user (name text, timestamp timestamp)')
    conn.close()
except Exception as eex:
    print("tabble alrready crreated")



#==========================Initialize Telegram===============================
telegram_key=getkey('TELEGRAM_KEY')
BASE_URL = f'https://api.telegram.org/bot{telegram_key}/'

#==========================Initialize Diffusion Model========================
#import torch
#from diffusers import StableDiffusionPipeline

#diffusionmodel = StableDiffusionPipeline.from_pretrained("CompVis/stable-diffusion-v1-4", torch_dtype=torch.float16)
diffusionmodel = None
#diffusionmodel = diffusionmodel.to("cuda") #cuda, or cpu   gpu 
#pipe.save_pretrained("./stable_diffusion_cpu")

#=========================Initialize Gemini================================= 
# google api is from https://makersuite.google.com
# Run locally based on the configuration file, uncomment the following two lines
#app.config.from_pyfile("config.py", silent=True) 
gemini_key=getkey('GEMINI_KEY')
genai.configure(api_key=gemini_key)
model= genai.GenerativeModel("gemini-2.0-flash-001") #gemini-1.5-flash

#========================DBS data prediction===============================
dbs_df = pd.read_csv("data/DBS_SingDollar.csv")

#========================= page handlers ===================================
@app.route("/", methods=['GET', 'POST'])
def index():    
   return login()

@app.route("/main", methods=['GET', 'POST'])
def main():
    global usersession

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
            usersession={}
            return redirect(url_for("telegram"))
        elif bvalue=='Telegramimage':
            usersession={}
            return redirect(url_for("telegramimage"))
        elif bvalue=='Telegramwebhook':
            usersession={}
            return redirect(url_for("telegramwebhook"))
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

@app.route("/paynow", methods=["GET","POST"])
def paynow():
    return render_template("paynow.html")

def getlastmessages(rmsg, command):
    global usersession
    r1=rmsg.json()
    r1=r1["result"]
    print(f"message queue size={len(r1)}")
    if len(r1)==0:  
        return False
    
    # For loop to initalize the usersessions when setfirstid=True or find last message id
    for item in r1:
        keys=item.keys()
        
        if 'edited_message' in keys: # when previous prompt is modified to be the new prompt
            itm=item['edited_message']
        elif 'message' in keys:
            itm=item['message']
        else:
           raise Exception("Unknown message key!")

        chat_id=str(itm['chat']['id']) # convert chat id to string for dict type key 
        msg=itm['text']
        msg_id=itm['message_id']

        if chat_id in usersession: # for a user exists in the session list
            # find the last message id and set to user session lastmsgid attribute
            if msg_id>usersession[chat_id]['lastmsgid']:
                orfirstid=usersession[chat_id]['firstid'] #keep the original firstid at this moment for the usersession under this chat_id
                orstatus=usersession[chat_id]['status']
                usersession.update({chat_id:{'firstid':orfirstid, 'lastmsgid':msg_id, "msg":msg,'status':orstatus}})
                #print(f"update {chat_id} with {usersessions[chat_id]}")
        else: # for a user not in the session list
            usersession.update({chat_id:{'firstid':0,'msg':"", 'lastmsgid':0, 'status':'active'}})
            print(f"set first question to chat_id={chat_id}....")
            send_url = BASE_URL + f'sendMessage?chat_id={chat_id}&text={command}'
            requests.get(send_url)
    return True

def setModelResponse(dtype, command, note, chat_id, text):
    if dtype=='image':
        #with torch.no_grad():
        image = diffusionmodel(text).images[0]
        image_path = "/content/image.png"
        image.save(image_path)
        image_caption = "stable-diffusion"
        data = {"chat_id": chat_id, "caption": image_caption}
        url = f"{BASE_URL}sendPhoto?chat_id={chat_id}"
        with open(image_path, "rb") as image_file:
            requests.post(url, data=data, files={"photo": image_file})
        send_url = BASE_URL + f'sendMessage?chat_id={chat_id}&text={command}'
        requests.get(send_url)
    else:
        if text.isnumeric():
            msg = str(float(text) * 0.2 + 100)
        else:
            msg = note
        send_url = BASE_URL + f'sendMessage?chat_id={chat_id}&text={msg}'
        requests.get(send_url)
        send_url = BASE_URL + f'sendMessage?chat_id={chat_id}&text={command}'
        requests.get(send_url)

def handleNewMessage(dtype, command, note):
    global usersession
    # update firstid with lastmsgid      

    nkeys=usersession.keys()
    keys=list(nkeys)
    for chat_id in keys:
        msg_id = usersession[chat_id]['lastmsgid']
        firstid= usersession[chat_id]['firstid']
        msg=usersession[chat_id]['msg']
        status=usersession[chat_id]['status']
        if msg_id>firstid : # update firstid with msg_id
            usersession[chat_id]={'firstid':msg_id,"msg":msg, 'lastmsgid':msg_id,'status':status}
            print(f"for {chat_id}, new masg_id={msg_id}, firstid={firstid}")
            if firstid==0:
                continue 
        else: # msg_id==firstid
            continue
        
        print(f"new message coming for chat_id ({chat_id}), lastmsgid= {msg_id}, firstid={firstid}, msg={msg}, status={status}")
        
        if status=='active':
            if str.lower(msg)=='quit':
                #usersessions.pop(chat_id, None) # remove usersession from the session list
                usersession[chat_id]={'firstid':msg_id,"msg":'quit','lastmsgid':msg_id,'status':'inactive'}
                print(f"quit case: {chat_id}={usersession[chat_id]}")
                requests.get(BASE_URL+f"sendMessage?chat_id={chat_id}&text={'Bye! If you want to rejoin, please type mjbot'}")
            else:
                setModelResponse(dtype, command, note, chat_id, msg)
        else: # status==inactive
            if str.lower(msg)=='mjbot':              
                usersession[chat_id]={'firstid':0,"msg":msg, 'lastmsgid':msg_id,'status':'active'}
                send_url = BASE_URL + f'sendMessage?chat_id={chat_id}&text={command}'
                requests.get(send_url)
    # ENd for Loop
    return True


def telegram_func(dtype, command, note, thepage):
    global usersession
    print(f"in telegram_func, command={command}......")
    if request.method=='POST':
        if request.form.get("instruct")=='back':
            for item in usersession.keys():
                send_url = BASE_URL + f'sendMessage?chat_id={int(item)}&text={"Host Exit from the bot. Bye!"}'
                requests.get(send_url)
            return redirect(url_for('main'))
        
    #grab id
    #time.sleep(5) #ensure telegram is activated
    response = requests.get(BASE_URL + 'getUpdates')
    data = response.json()
    if len(data['result'])==0:
        return render_template(thepage)
    
    if getlastmessages(response, command):
        handleNewMessage(dtype, command, note)
    return(render_template(thepage))

@app.route("/telegram", methods=["GET","POST"])
def telegram():
    print("in telegram......")
    return telegram_func("salary", "Welcome to prediction, please enter the salary or quit", "salary must be a number", 'telegram.html')

@app.route("/telegramimage", methods=["GET","POST"])
def telegramimage():
    print("in telegramimage......")
    return telegram_func("image", "Welcome to prediction image, please enter words for the image or quit", None, 'telegramimage.html')

@app.route("/telegramwebhook", methods=["POST"])
def telegramwebhook():
    if request.form.get("instruct")=='back':
        '''for item in usersession.keys():
            send_url = BASE_URL + f'sendMessage?chat_id={int(item)}&text={"Host Exit from the bot. Bye!"}'
            requests.get(send_url)'''
        return redirect(url_for('main'))
    data = request.json
    if 'message' in data:
        message_text = data['message']['text']
        print(f"New message: {message_text}")
    return "OK", 200

if __name__=="__main__":
    app.run()

