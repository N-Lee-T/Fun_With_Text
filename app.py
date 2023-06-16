from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.error import HTTPError
import random
import requests
import openai 
import os




"""
Initialize the application and the database
"""

app = Flask(__name__)
# app.secret_key = "TOTALLYSECRETKEY" # uh, let's change this soon - or remove, not using Sessions
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///proj361.db'
openai.api_key = os.getenv("OPENAI_API_KEY")
db = SQLAlchemy(app)
# with app.app_context():
#     db.create_all()

the_time = datetime.now()
the_date = the_time.strftime('%m/%d/%Y')

class Pitch(db.Model):
    """
    Class that will hold the pitches that are generated from certain words
    """
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(250), nullable=False)
    one = db.Column(db.String(250), nullable=False)
    two = db.Column(db.String(250), nullable=False)
    three = db.Column(db.String(250), nullable=False)
    pitch = db.Column(db.Text(4096), nullable=False)
    time = db.Column(db.String(250), default=the_time)
    # change to default not nullable
    deleted = db.Column(db.Boolean, nullable=False)

    # with app.app_context():
    #     db.create_all()

    def __repr__(self):
        return '<Pitches %r>' % self.id

"""
Routes for different functions
"""
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/action', methods=['GET', 'POST'])
def make():
    if request.method == 'POST':
        # 1. get the original word from the user:
        prompt, language = request.form['prompt'], request.form['language']
        if request.form['prompt'] == '':
            return redirect('/action_fail')
        
        # 2. get links (words) from Wiki article
        words = get_words(prompt, language)

        # 3. get summary from Microservice
        summary = get_summary(words[0], words[1], words[2])
        print(summary)

        # 4. get AI prompt paragraph
        ai_prompt = generate_prompt(words, summary, language)

        # 5. generate pitch from prompt
        new_pitch = pitch(ai_prompt)
        # print(new_pitch)
        new_idea = Pitch(prompt=request.form['prompt'], one=words[0], two=words[1], three=words[2], pitch=new_pitch, deleted=False)
        try:
            db.session.add(new_idea)
            db.session.commit()
            return redirect('/action')
        except Exception as err:
            # this should do something else. Also, figure out the specific error!!!
            print(f"Unexpected {err=}, {type(err)=}")
            return "Oh no, that didn't work."
    else:
        ideas = Pitch.query.order_by(Pitch.time).all()
        return render_template('action.html', ideas=ideas)

@app.route('/action_fail', methods=['GET'])
def nope():
    return render_template('action_fail.html')

@app.route('/display/<id>', methods=['GET'])
def view(id):
    idea = Pitch.query.get_or_404(id)
    return render_template('display.html', idea=idea)
    # return render_template(url_for('view'), id=id, idea=idea)

@app.route('/show_all', methods=['GET'])
def show_em():
    ideas = Pitch.query.order_by(Pitch.time).all()
    return render_template('/showall.html', ideas=ideas)

@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_idea(id):
    idea = Pitch.query.get_or_404(id)
    if request.method == 'GET':
        return render_template('/edit.html', idea=idea)
    # if request.method == 'POST':
    idea.pitch = request.form['pitch']
    try:
        db.session.commit()
        return redirect('/action')
    except:
        return "dunno, didn\'t edit tho"
    
# this just changes the value and displays on deleted page
@app.route('/delete/<id>', methods=['GET'])
def first_del(id):
    idea = Pitch.query.get_or_404(id)
    try:
        if idea.deleted == False:
            idea.deleted = True
        else:
            idea.deleted = False
        db.session.commit()
        return redirect('/deleted')
    except:
        return "dunno, didn\'t delete tho"
    
# this permanently deletes 
@app.route('/deleted/<id>', methods=['GET'])
def delete_idea(id):
    idea = Pitch.query.get_or_404(id)
    try:
        db.session.delete(idea)
        db.session.commit()
        return redirect('/action')
    except:
        return "dunno, didn\'t delete tho"

@app.route('/deleted', methods=['GET'])
def show_deleted():
    ideas = Pitch.query.order_by(Pitch.time).all()
    return render_template('deleted.html', ideas=ideas)


def get_words(prompt, language):
    """
    param prompt:: string <= 250 chars

    returns: list of three strings

    This will get three additional words that are related to the prompt word, 
    at least according to the Wikipedia links!

    Uses BeautifulSoup to parse wikipedia page. 

    """
    res = None
    while res is None:
        res = get_res(prompt, language)
    words = get_links(res)
    # print(finals)
    return words

def get_res(prompt, language):
    """
    Returns None if a Wiki page is not found or contents if valid URL
    """
    try:
        # prompt = input("Enter a word or phrase below - 2 words max! Prompt:  ")
        if prompt == ' ':
            return None
        if language == 'Spanish':
            str_url = 'https://es.wikipedia.org/w/index.php?search=%s' % prompt
        elif language == 'Hindi':
            str_url = 'https://hi.wikipedia.org/w/index.php?search=%s' % prompt
        elif language == 'French':
            str_url = 'https://fr.wikipedia.org/w/index.php?search=%s' % prompt
        elif language == 'Chinese':
            str_url = 'https://zh.wikipedia.org/w/index.php?search=%s' % prompt
        else:
            str_url = 'https://en.wikipedia.org/w/index.php?search=%s' % prompt
        # print(str_url)
        response = requests.get(str_url)
        response.raise_for_status()
    except HTTPError:
        print("That query didn\'t work :( Try again!")
        return None
    else:
        return response
   
def get_links(res):
    """
    Returns three terms that are related to the original query
    """
    result1 = BeautifulSoup(res.content, 'html.parser')
    title = result1.find('title').get_text()
    print(title)
    # check to see if this works...nope, doesn't yet! 
    if title[-26:-1] == 'Search results - Wikipedia':
        print("Looks like your search did not yield any results - try again!")
        get_words()
    links = result1.find_all('a')
    num_links = len(links)
    print(f"The number of links is {num_links}\n")
    terms = []
    # for _ in range(3):
    zed = 0
    while zed < 3:
        # add func to strip the unwanted chars
        new = links[random.randrange(10, num_links)].get_text()
        new.strip("'")
        if not check_valid(new):
            continue
        else:
            zed += 1
            terms.append(new)
    return terms

def check_valid(term):
    """
    Checks that terms meet minimum validity (not exhaustive!)

    Ideally you'd use a regex here to weed out the many edge cases

    """
    not_valid = ['', ' ', '.', '..', '^', 'a', 'b', 't', 'All article disambiguation pages', 'Short description matches Wikidata', 
                 'Pages including recorded pronunciations', 'See also', 'All disambiguation pages', 'learn more', 'All articles that may contain original research', 'edit',
                 'Related changes', 'Contributions', 'Archived', 'Talk', 'Log in', 'Mobile view', 'What links here', 'Page information', 'Privacy Policy', 'Disambiguation', 'Special Pages']

    if term in not_valid or 'ikipedia' in term:
        return False
    elif term[0] in '0123456789' or term[0] in ('{[('):
        return False
    return True

def pitch(ai_prompt):
    """
    param words:: a list of three strings

    returns:: a string

    This will call the OpenAI AP to with a prompt to create a pitch using the
    three words that were generated from the prompt through the get_words() function
    """
    pitch = openai.Completion.create(
            model="text-davinci-003",
            prompt=ai_prompt,
            temperature=1.0,
            max_tokens=2048
        )

    print(pitch.choices[0].text) # clean the text function
    return pitch.choices[0].text


def generate_prompt(words, summary, language):
    """
    Returns the prompt that will be sent to the OpenAI endpoint.
    """
    print(f"THE LANGUAGE SHOULD BE {language}\n")
    return f"""Write a killer pitch, in {language} for VC investors for a 
    startup involving three random terms. DO NOT include the terms 'investor',
      'VC', 'venture capital', or 'startup'. It should be extremely 
    compelling and informed, erudite and witty, with advanced 
    vocabulary terms and outrageous claims about the efficacy of the product.
      Incorporate the feeling from this wikipedia page: {summary}"
     The terms are {words[0].capitalize()}, {words[1].capitalize()}, and 
     {words[2].capitalize()} The pitch should be in {language}."""


# this will use the microservice
def get_summary(one, two, three):
    api_url = 'https://fejxhfgkg7.execute-api.us-east-2.amazonaws.com/Beta/search'
    headers = {'x-api-key': os.environ.get('SECOND_KEY')}
    try:
        summary = requests.get(api_url, params={'one': one, 'two': two, 'three': three}, headers=headers)
        # summary.raise_for_status()
    except HTTPError:
        print("That query didn\'t work :( Try again!")
        return None
    else:
        try: 
            print(summary.json()['summary'])
            return summary.json()['summary'] # add func to remove the '\n' etc
        except KeyError:
            pass
        return(f"There's not much to say about {one}, {two}, {three} but try anyway.")

if __name__=='__main__':
    # with app.app_context():
    #     db.create_all()
    print("CREATING THAT DB")
    db.create_all()
    app.run(debug=True, port=8183)
