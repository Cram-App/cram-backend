import flask
from flask import Flask
from nltk.corpus import wordnet as wn
from textblob import TextBlob
import click
import json
import re
import wikipedia

app = Flask(__name__)

class Article:
    """Retrieves and analyzes wikipedia articles"""

    def __init__(self, title):
        self.page = wikipedia.page(title)
        self.summary = TextBlob(self.page.summary)

    def generate_trivia_sentences(self):
        sentences = self.summary.sentences

        # Remove the first sentence - it's never a good one
        del sentences[0]

        trivia_sentences = []
        for sentence in sentences:
            trivia = self.evaluate_sentence(sentence)
            if trivia:
                trivia_sentences.append(trivia)

        return trivia_sentences

    def get_similar_words(self, word):
        # In the absence of a better method, take the first synset
        synsets = wn.synsets(word, pos='n')
        similar_words = []
        # If there aren't any synsets, return an empty list
        if len(synsets) == 0:
            return []
        else:
            synset = synsets[0]

        # Get the hypernym for this synset (again, take the first)
        if len(synset.hypernyms()) > 0:
            hypernym = synset.hypernyms()[0]

            # Get some hyponyms from this hypernym
            if len(hypernym.hyponyms()) > 0:
                hyponyms = hypernym.hyponyms()

            # Take the name of the first lemma for the first 8 hyponyms
            
            for hyponym in hyponyms:
                similar_word = hyponym.lemmas()[0].name().replace('_', ' ')
                
                if similar_word != word:
                    similar_words.append(similar_word)

                if len(similar_words) == 8:
                    break

        return similar_words

    def evaluate_sentence(self, sentence):
        if sentence.tags[0][1] == 'RB' or len(sentence.words) < 6:
            # This sentence starts with an adverb or is less than five words long
            # and probably won't be a good fit
            return None

        tag_map = {word.lower(): tag for word, tag in sentence.tags}

        replace_nouns = []
        for word, tag in sentence.tags:
            # For now, only blank out non-proper nouns that don't appear in the article title
            if tag == 'NN' and word not in self.page.title:
                # Is it in a noun phrase? If so, blank out the last two words in that phrase
                for phrase in sentence.noun_phrases:
                    if phrase[0] == '\'':
                        # If it starts with an apostrophe, ignore it
                        # (this is a weird error that should probably
                        # be handled elsewhere)
                        break

                    if word in phrase:
                        # Blank out the last two words in this phrase
                        [replace_nouns.append(phrase_word) for phrase_word in phrase.split()[-2:]]
                        break

                # If we couldn't find the word in any phrases,
                # replace it on its own
                if len(replace_nouns) == 0:
                    replace_nouns.append(word)
                break
        
        if len(replace_nouns) == 0:
            # Return none if we found no words to replace
            return None

        trivia = {
            'title': self.page.title,
            'url': self.page.url,
            'answer': ' '.join(replace_nouns)
        }

        if len(replace_nouns) == 1:
            # If we're only replacing one word, use WordNet to find similar words
            trivia['similar_words'] = self.get_similar_words(replace_nouns[0])
        else:
            # If we're replacing a phrase, don't bother - it's too unlikely to make sense
            trivia['similar_words'] = []

        # Blank out our replace words (only the first occurrence of the word in the sentence)
        replace_phrase = ' '.join(replace_nouns)
        blanks_phrase = ('__________ ' * len(replace_nouns)).strip()

        expression = re.compile(re.escape(replace_phrase), re.IGNORECASE)
        sentence = expression.sub(blanks_phrase, str(sentence), count=1)

        trivia['question'] = sentence
        return trivia


# For now, hard-code the titles of articles you want to scrape here
SAMPLE_ARTICLES = (
    'Climatology',
    # 'Tony Bennett',
    # 'Gauls',
    # 'Scabbling',
    # 'Henry V, Duke of Carinthia',
    # 'Ukrainian Women\'s Volleyball Super League'
)

# @click.command()
# @click.argument('titles', nargs=-1)
# @click.option('--output', type=click.File('w'), help='Output to JSON file')
@app.route("/")
def home():
    return "Hello World"

@app.route("/questions", methods=['GET'])
# def generate_trivia(titles, output):
def generate_trivia():
    """Generates trivia questions from wikipedia articles. If no
    titles are supplied, pulls from these sample articles:

    'Tony Bennett', 'Gauls', 'Scabbling', 'Henry V, Duke of Carinthia',
    'Ukrainian Women\'s Volleyball Super League'
    """
    topic = "blockchain"
    questions = {}
    if flask.request.method == "GET":
        if 'topic' in flask.request.args:
            topic = flask.request.args['topic']
            print(topic)
    # Use the sample articles if the user didn't supply any
    # if len(titles) == 0:
    #     titles = SAMPLE_ARTICLES

    # Retrieve the trivia sentences
            questions = []
            # for article in topics:
            click.echo('Analyzing \'{0}\''.format(topic))
            topic = Article(title=topic)
            questions = questions + topic.generate_trivia_sentences()

    # Output to stdout or JSON
    # if output:
    #     output_file = output.open()
    #     json.dump(questions, output_file, sort_keys=True, indent=4)
    #     click.echo('Output stored in {0}'.format(output.name))
    # else:
    #   click.echo(json.dumps(questions, sort_keys=True, indent=4))
    return json.dumps(questions)


if __name__ == '__main__':
    app.debug = True
    app.run('0.0.0.0', port=8000)
    # generate_trivia()
