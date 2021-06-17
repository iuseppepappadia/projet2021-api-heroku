from flask import Flask, render_template, url_for, request, flash,redirect
from flask_sqlalchemy import SQLAlchemy
import re
from sqlalchemy import create_engine
from sqlalchemy import text as txt
from nltk.corpus import stopwords                    
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sqlalchemy.dialects import registry

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hqhuebgborpypm:06e3f5f1cc916a9fa93250d2a5638845b168a555fd2702f316f0c8f913c572f7@ec2-34-193-101-0.compute-1.amazonaws.com:5432/de877rvmsp1n6m'
app.config['SQLALCHEMY_SECRET_KEY'] = 'secret-key-goes'
app.secret_key = 'super secret key'
db = SQLAlchemy(app)


registry.register('snowflake', 'snowflake.sqlalchemy', 'dialect')
eng = create_engine('postgresql://hqhuebgborpypm:06e3f5f1cc916a9fa93250d2a5638845b168a555fd2702f316f0c8f913c572f7@ec2-34-193-101-0.compute-1.amazonaws.com:5432/de877rvmsp1n6m')
connection = eng.connect()

stemmer= PorterStemmer()
stop_words = set(stopwords.words('french'))

class User(db.Model):
    __tablename__ = 'users'

    username = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, index=True)
    email = db.Column(db.String, index=True, unique=True)

    def __init__(self,username,password,email):
        self.username = username
        self.password = password
        self.email = email        

class Topic(db.Model):
    __tablename__ = 'topics'

    id_topic = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(64), index=True,unique=True)
    dictionary = db.Column(db.String, index=True)

    def __init__(self,id_topic,name,dictionary):
        self.id_topic = id_topic
        self.name = name
        self.dictionary = dictionary       



class Clean():

    def cleaning(document):
    # Remove all the special characters
        document = re.sub(r'\W', ' ', document)
        document = re.sub('\\xc3\\xa9', 'é', document)
    # remove all single characters
        document = re.sub(r'\s+[a-zA-Z]\s+', ' ', document)
    # Remove single characters from the start
        document = re.sub(r'\^[a-zA-Z]\s+', ' ', document) 
    # Substituting multiple spaces with single space
        document = re.sub(r'\s+', ' ', document, flags=re.I)
    # Converting to Lowercase
        document = document.lower() 
    # Stop Words
        tokens = word_tokenize(document)
        document = [i for i in tokens if not i in stop_words]
    # Stemming
        list1=[]
        for word in document:
            h = stemmer.stem(word)
            list1.append(h)
        list1 = list(set(list1))
        return list1
    
    def similarity(s0, s1):

      return (len(list(set(s0)&set(s1)))/len(s0) ) *100


class thematiseur():
   
     def thematiseur_gen(text,dictionary): #dictionary contiene l'id del topic e il
        args=[]
        for key in dictionary :           #valore di soglia, assegnato dall'utente
            x = thematiseur.thematiseur_spec(text,key,dictionary[key]) # richiama il classificatore specifico
            if x != None:    
                args.append(x)     
        return args
        
     def thematiseur_spec(text,index,threshold):
        sql_query = txt("SELECT name,dictionary FROM topics WHERE id_topic = :index ")
        result = connection.execute(sql_query,index=index)
        myresult = result.fetchall()
        #myresult = Topic.query.filter_by(id_topic=index).first()
            # nome del topic e lista di parole chiave            
        for res in myresult:
            z = res[0]
            y = res[1]
        text = Clean.cleaning(text) #pulizia del testo e del dizionario
        pured_dict = Clean.cleaning(y)
        m = Clean.similarity(text,pured_dict) #calcolo somiglianza tra i testi
        if m >= threshold: #stampa se la percentuale di somiglianza è maggiore del valore di soglia
            return z

@app.route('/')
def base():
    return render_template('base.html')

@app.route('/atform')
def atform():
    return render_template('form_out.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('sign_up.html')

@app.route('/signup', methods=['POST'])
def signup_post(): #registrazione
    email = request.form['email']
    username = request.form['name']
    password = request.form['password']
    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database
    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Please check your login details and try again.')
        return redirect(url_for('signup'))
    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, username=username, password=password)
    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('login'))
        
    
@app.route('/login', methods=['POST'])
def login_post():
    
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(username=name).first()
    db_psw = user.password
    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user: 
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))
    elif not db_psw!=password:
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))
    
    return redirect(url_for('base'))   

        

@app.route('/logout')
def logout():
    return render_template('base.html')

@app.route('/submitted', methods=['GET','POST'])
def apply():
    if request.method == 'POST':
        length = Topic.query.count()
        form_html = request.form
        file = request.files['myfile']
        if file:
            text=str(file.read())
            text = text.encode('latin-1').decode('utf-8')
        else:
            return render_template('form_out.html',message='Please, Insert A File',arg=[])
        thr = int(form_html['threshold'])
        dicts = {}
        for i in range(1,length+1):
            dicts[i]= thr
        args = thematiseur.thematiseur_gen(text,dicts)
        if len(args)>0:
            return render_template('form_out.html',args=args,message='')
        else :
            return render_template('form_out.html',message='No topics found,Try Again',arg=[])
    else:
        return render_template('form_out.html')
    
@app.route('/sub_dict', methods=['GET','POST'])
def add():
    if request.method == 'POST':
        form_html = request.form
        file = request.files['myfile_dict']
        if file:
            text =str(file.read())
            text = text.encode('latin-1').decode('utf-8')
            # do something with file contents
        else:
            return render_template('form_out.html',message='Please, Insert A File',arg=[])
        length = Topic.query.count()
        length = length + 1
        value = form_html['define']
        new_topic = Topic(id_topic=length,name=value,dictionary=text)
        db.session.add(new_topic)
        db.session.commit()
        return render_template('form_out.html',message='Dictionary Inserted',arg=[])
        
@app.route('/spec_rec', methods=['GET','POST'])
def specific():
    if request.method == 'POST':
        file = request.files['file_spec']
        if file:
            text =str(file.read())
            text = text.encode('latin-1').decode('utf-8')
            # do something with file contents
        else:
            return render_template('form_out.html',message='Please, Insert A File',arg=[])
        form_html = request.form
        thr = int(form_html['threshold2'])
        topics = form_html['mytext']
        topics = topics.split(',')        
        args = []
        #☺placeholders=[]
        #for value in topics:
         #   h = (value,)
          #  placeholders.append(h)
        
        #placeholders= ','.join("'"+str(topics[i])+"'" for i in range(len(topics)))
        if request.form.get("filter"):
            for item in topics:
                sql = txt("SELECT id_topic FROM topics WHERE name = :item")
                result = connection.execute(sql,item=item)
                myresult = result.first()
                for index in myresult: 
                    value = thematiseur.thematiseur_spec(text,index,thr)
                    #if value!=None:
                    args.append(value)
            return render_template('form_out.html',args=args,message='')
        elif request.form.get("subset") :
            
            sql = txt("SELECT id_topic FROM topics WHERE name NOT IN :topics")
            result = connection.execute(sql,topics=tuple(topics))
            myresult = result.fetchall()
            #res = Topic.query.filter_by(Topic.name.in_(topics)).all()
            for index in myresult:
                value = thematiseur.thematiseur_spec(text,index[0],thr)
                if value != None:
                    args.append(value)
            return render_template('form_out.html',args=args,message='')
        else :
            return render_template('form_out.html',args=[],message='')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)