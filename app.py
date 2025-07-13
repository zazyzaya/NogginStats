from flask import Flask, render_template, session, url_for, request

app = Flask(__name__)
app.secret_key = "TODO make this a global"

@app.route('/login', methods=['POST'])
def login(): 
    usr = request.form['first']
    pwd = request.form['password']
    
    print(usr)
    print(pwd)
    
    session['username'] = usr 
    session['usr_token'] = hash(usr + pwd)

    # TODO include logic to validate login 
    return render_template('index.html')


@app.route('/')
def index():
    session.clear()
    if session.get('usr_token'):
        return render_template('index.html')
    else: 
        return render_template('login.html')

app.run(debug=True)