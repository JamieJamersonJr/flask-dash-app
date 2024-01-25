from flask import *
import sqlite3 as sql3
import argon2 as ar2
from datetime import datetime, timedelta
import time
from functools import wraps
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO
import plotly as ply
# from dash import Dash, html, dcc, callback, Output, Input
# import plotly.express as px
# import pandas as pd
from dash_app import make_dash, make_layout, define_callbacks


# CONFIG
app = Flask(__name__)
app.secret_key = b'VerySecureSecretYes'
# app.config['TESSERACT_PATH'] = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
app.config['SESSION_DURATION'] = seconds=1800
app.config['sample_table'] = 'Samples'
DATABASE = 'database/database.db'

# DASH INTEGRATION
# dash_app = Dash(__name__, server = app,  url_base_pathname = '/dash/')
dash_app = make_dash(app, DATABASE)
dash_app.layout = make_layout()
define_callbacks()

# FUNCTION DEFINITIONS

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sql3.connect(DATABASE)
    db.row_factory = make_dicts
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def check_login(username, password):
    if " " in username:
        return {'message':f'Usernames may not contain spaces', 'success':False}
    
    cur = get_db().cursor()
    cur.execute(f'SELECT username, password_hash FROM Users WHERE username = "{username}"')
    user = [user for user in cur]
    if len(user) <= 0:
        return {'message':f'User {username} not found', 'success':False}
    
    ph = ar2.PasswordHasher()
    hash = user[0]['password_hash']
    try:
        if ph.verify(hash, password):
            if ph.check_needs_rehash(hash):
                cur.execute(f'REPLACE INTO Users (username, password_hash) VALUES ("{username}", "{ph.hash(password)}")')
            return {'message':f'Logged in as {username}', 'success':True}
        else:
            return {'message':'Incorrect username or password', 'success':False}
    except ar2.exceptions.VerifyMismatchError:
        return {'message':'Incorrect username or password', 'success':False}
    except:
        return {'message':'Login failed', 'success':False}

def add_login_log(username):
    login_timestamp =  time.time()
    ph = ar2.PasswordHasher()
    login_hash = ph.hash(f"{login_timestamp}{username}")
    cur = get_db().cursor()
    cur.execute(f'INSERT INTO Logins (login_hash, login_date, username) VALUES ("{login_hash}","{login_timestamp}","{username}")')
    get_db().commit()
    session['auth_token'] = login_hash

def validate_session():
    cur = get_db().cursor()
    token = session.get('auth_token')
    if token != None:
        cur.execute(f'SELECT login_date FROM Logins WHERE login_hash = "{session["auth_token"]}"')
        login_date = [row for row in cur]
        print(login_date)
        if len(login_date) == 1:
            print((time.time() - login_date[0]['login_date']))
            if (time.time() - login_date[0]['login_date']) < app.config['SESSION_DURATION']:
                return {'message':'Session Valid', 'response': True}
        return {'message':'Session Timed Out', 'response': False}
    else:
        return {'message':'User not logged in', 'response': False}

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if validate_session()['response']:
            print(f"Session message: {validate_session()['message']}")
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapper

def datestring_to_unix(date_string, format = "%d/%m/%Y"):
    date_format = format
    print(f"Converting datestring: {date_string} of format: {date_format} to datetime object")
    dt_object = datetime.strptime(date_string, date_format)
    print(f"datetime object: {dt_object}")
    unix_timestamp = int(dt_object.timestamp())
    return unix_timestamp

def unix_to_datestring(unix):
    return datetime.fromtimestamp(int(unix)).strftime('%d/%m/%Y')

def getSamples(from_date = None, to_date = None):
    cur = get_db().cursor()
    cur.execute(f'select date, p5_count, p05_count, location from {app.config["sample_table"]} ORDER BY date ASC')
    dataDict = {'data':[],'p5':[],'p05':[], 'posizione':[]}
    for row in cur:
        if from_date != None or to_date != None:
            if row['date'] < from_date or row['date'] > to_date:
                print('skipped')
                continue
        dataDict['data'].append(unix_to_datestring(row['date']))
        print(row['date'])
        dataDict['p5'].append(row['p5_count'])
        dataDict['p05'].append(row['p05_count'])
        dataDict['posizione'].append(row['location'])
    return pd.DataFrame(data = dataDict)
    

def createPlot(_from_date = None, _to_date = None):
    # db = pd.read_csv("static/temp_storage/prova_PW.csv",sep=';')
    if _from_date != None or _to_date != None:
        db = getSamples(datestring_to_unix(_from_date, "%Y-%m-%d"), datestring_to_unix(_to_date, "%Y-%m-%d"))
    else:
        db = getSamples()
    print(f"DEBUG: {db.dtypes}")
    # print([row for row in cur])
    pd.set_option('display.max_rows', 5)
    # Calcoli statistici
    mean_p5 = db['p5'].mean()
    # print(db['data'])
    mean_p5 = db['p5'].mean()
    mean_p05 = db['p05'].mean()
    stdDev_p5 = db['p5'].std()
    stdDev_p05 = db['p05'].std()
    ucl_p5 = mean_p5 + (3 * stdDev_p5)
    ucl_p05 = mean_p05 + (3 * stdDev_p05)
    limit_p5 = 29300
    limit_p05 = 3520000
    print(ucl_p5)
    # Conversione della colonna 'data' in formato datetime
    db['data'] = pd.to_datetime(db['data'], dayfirst=True)

    # Creazione del grafico a linee
    plt.figure(figsize=(12, 6))

    # Linea principalez
    sns.lineplot(x='data', y='p5', data=db, label='N° particelle di diametro ≥ 5 μm')
    # Linea orizzontali per il limite
    plt.axhline(y=limit_p5, color='g', linestyle='--',label='Action level', linewidth=2)
    plt.axhline(y=ucl_p5, color='r', linestyle='--',label='Alert level', linewidth=2)

    outlier = db['p5'] > ucl_p5
    
    # Evidenzia i punti che superano l'Alert level
    plt.scatter(x=db.loc[outlier & (db['p5'] > limit_p5), 'data'], y=db.loc[outlier & (db['p5'] > limit_p5), 'p5'],
            color='orange', marker='o', label='Action Level Exceeded')  # Aggiunto per evidenziare l'Action level

    plt.scatter(x=db.loc[outlier & (db['p5'] > ucl_p5), 'data'], y=db.loc[outlier & (db['p5'] > ucl_p5), 'p5'],
                color='red', marker='o', label='Alert Level Exceeded')
    for i, txt in enumerate(db.loc[outlier, 'p5']):
        posizione = db.loc[outlier, 'posizione'].iloc[i]  # Ottieni la posizione dell'outlier
        plt.annotate(f"Pos {posizione}\n{txt:.2f}", (db.loc[outlier, 'data'].iloc[i], txt),
                    textcoords="offset points", xytext=(0, 10), ha='center')
        

    # Regolazioni estetiche del grafico
    plt.title('Carta di Controllo per particelle di diametro ≥ 5 μm')
    plt.xlabel('Data')
    plt.ylabel('N° particelle di diametro ≥ 5 μm')
    plt.xticks(rotation=45)
    # Ottieni il buffer dell'immagine
    buffer = BytesIO()
    plt.savefig(buffer, format='png', transparent=True)
    buffer.seek(0)
    
    
    # Apri l'immagine con l'applicazione predefinita su Windows
    Image.open(buffer).save("static/temp_storage/5plot.png")

    # Conversione della colonna 'data' in formato datetime
    
    db['data'] = pd.to_datetime(db['data'])

    # Creazione del grafico a linee
    plt.figure(figsize=(12, 6))

    # Linea principale
    sns.lineplot(x='data', y='p05', data=db, label='N° particelle di diametro ≥ 0,5 μm')

    # Linea orizzontali per il limite
    plt.axhline(y=limit_p05, color='g', linestyle='--',label='Action level', linewidth=2)
    plt.axhline(y=ucl_p05, color='r', linestyle='--',label='Alert level', linewidth=2)

    outlier = db['p05'] > ucl_p05

    # Evidenzia i punti che superano l'Alert level
    plt.scatter(x=db.loc[outlier & (db['p05'] > limit_p05), 'data'], y=db.loc[outlier & (db['p05'] > limit_p05), 'p05'],
            color='orange', marker='o', label='Action Level Exceeded')  # Aggiunto per evidenziare l'Action level

    plt.scatter(x=db.loc[outlier & (db['p05'] > ucl_p05), 'data'], y=db.loc[outlier & (db['p05'] > ucl_p05), 'p05'],
                color='red', marker='o', label='Alert Level Exceeded')
    for i, txt in enumerate(db.loc[outlier, 'p05']):
        posizione = db.loc[outlier, 'posizione'].iloc[i]  # Ottieni la posizione dell'outlier
        plt.annotate(f"Pos {posizione}\n{txt:.2f}", (db.loc[outlier, 'data'].iloc[i], txt),
                    textcoords="offset points", xytext=(0, 10), ha='center')

    # Regolazioni estetiche del grafico
    plt.title('Carta di Controllo per particelle di diametro ≥ 0,5 μm')
    plt.xlabel('Data')
    plt.ylabel('N° particelle di diametro ≥ 0,5 μm')
    plt.xticks(rotation=45)
    # Ottieni il buffer dell'immagine
    buffer = BytesIO()
    plt.savefig(buffer, format='png', transparent = True)
    buffer.seek(0)

    # Apri l'immagine con l'applicazione predefinita su Windows
    Image.open(buffer).save("static/temp_storage/05plot.png")


# ROUTE DEFINITIONS

@app.route("/", methods=['GET', 'POST'])
@login_required
def home():
    return redirect('dashboard')
    
@app.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == "POST":
        if request.form['submitButton'] == 'Refresh Graph':
            createPlot()
            return render_template('dashboard.html', message = session.get('message'))
        cur = get_db().cursor()
        tstamp = datestring_to_unix(request.form["date"], "%Y-%m-%d")
        cur.execute(f'INSERT INTO {app.config["sample_table"]} (date, p5_count, p05_count, location, user_hash) VALUES ({tstamp}, {request.form["newMean5"]}, {request.form["newMean05"]}, "PLACEHOLDER", "{session["auth_token"]}")')
        get_db().commit()
        createPlot()
        return render_template('dashboard.html', message = session.get('message'))
    else:

        return render_template('dashboard.html', message = session.get('message'))

@app.route("/graph", methods=['GET', 'POST'])
def graph():
    createPlot()
    return render_template('graph.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        check = check_login(username, password)
        if check['success']:
            add_login_log(username)
            session['message'] = check['message']
            res = redirect(url_for('dashboard'))
            return res
            # flash(check['message'])
            # response = make_response(render_template('login_landing.html', user = request.cookies.get('current_user')))
            # # response.set_cookie('current_user', username, expires = helper.createExpiryDate())
            # # response.set_cookie('logged_in', 'true', expires = helper.createExpiryDate())
        else:
            # response = make_response(render_template('login_landing.html'))
            return render_template('login_template.html', error = check['message'])
        
    return render_template('login_template.html')

@app.route("/logout")
def logout():
    session.pop('auth_token')
    return redirect('/login')

@app.route("/admin", methods=['GET', 'POST'], strict_slashes=False)
def admin():
    
    return 'TODO'

@app.route("/admin/register", methods=['GET', 'POST'])
def add_user():
    cur = get_db().cursor()
    users = []
    cur.execute('SELECT * FROM Users')
    for row in cur:
        users.append(row)

    if request.method == 'POST':
        if request.form['password'] != request.form['confirm_password']:
            return render_template('register_user.html', activeUsers = users, error = "Password and confermation do not match, please re-enter password")
        username = request.form['username']
        ph = ar2.PasswordHasher()
        hashed_password = ph.hash(request.form['password'])
        
        cur.execute(f"INSERT INTO Users (username, password_hash) VALUES (\"{username}\", \"{hashed_password}\")")
        get_db().commit()

    return render_template('register_user.html', activeUsers = users)



#DEBUG STUFF REMOVE WHEN DONE
@app.route("/DEBUG", methods=['GET', 'POST'])
def _debug_db_query():
    if request.method == 'POST':
        cur = get_db().cursor()
        result = cur.execute(request.form['query'])
        if request.form.get('commit'):
            get_db().commit()
        return f"<form method='post'> Query: <input type='text' name='query'> Commit: <input type='checkbox' name='commit'> <input type='submit'> </form> {[row for row in result]}"
    return """<form method="post"> Query: <input type="text" name="query"> Commit: <input type='checkbox' name='commit'> <input type="submit"> </form>"""

@app.route("/DEBUG2", methods=['GET', 'POST'])
def _debug_db_query2():

    import random
    import time
        
    def str_time_prop(start, end, time_format, prop):
        """Get a time at a proportion of a range of two formatted times.

        start and end should be strings specifying times formatted in the
        given format (strftime-style), giving an interval [start, end].
        prop specifies how a proportion of the interval to be taken after
        start.  The returned time will be in the specified format.
        """

        stime = time.mktime(time.strptime(start, time_format))
        etime = time.mktime(time.strptime(end, time_format))

        ptime = stime + prop * (etime - stime)

        return time.strftime(time_format, time.localtime(ptime))


    def random_date(start, end, prop):
        return str_time_prop(start, end, '%d/%m/%Y %I:%M %p', prop)
    
        
    if request.method == 'POST':
        cur = get_db().cursor()
        for i in range(int(request.form['count'])):
            cur.execute(f'insert into DebugSamples (date, p5_count, p05_count, location) VALUES ({datestring_to_unix(random_date("1/1/2008 1:30 PM", "1/1/2009 4:50 AM", random.random()), "%d/%m/%Y %I:%M %p")}, {500+random.randrange(-100,100)}, {500+random.randrange(-100,100)}, "PLACEHOLDER")')
        if request.form.get('commit'):
            get_db().commit()
        return [row for row in cur]
        return f"<form method='post'> Generate #: <input type='text' name='query'> <input type='number' name='count'> Commit: <input type='checkbox' name='commit'> <input type='submit'> </form> {[row for row in result]}"
    return """<form method="post"> Generate #: <input type="text" name="query"> <input type='number' name='count'> Commit: <input type='checkbox' name='commit'> <input type="submit"> </form>"""





# Run the app
if __name__ == '__main__':
    app.run(debug=True)
