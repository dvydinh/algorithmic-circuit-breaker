import pandas as pd
import re
from collections import Counter

# Standard English stopwords (minimal list to avoid downloading NLTK corpus)
STOPWORDS = set([
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "d", 
    "ll", "m", "o", "re", "ve", "y", "ain", "aren", "couldn", "didn", "doesn", "hadn", 
    "hasn", "haven", "isn", "ma", "mightn", "mustn", "needn", "shan", "shouldn", "wasn", 
    "weren", "won", "wouldn"
])

def extract_toxic_words():
    # Read the dataset
    df = pd.read_csv('doc/train.csv/train.csv')
    
    # Filter for severe_toxic == 1
    severe_toxic_df = df[df['severe_toxic'] == 1]
    
    # Tokenize and count
    word_counts = Counter()
    
    for text in severe_toxic_df['comment_text']:
        if not isinstance(text, str):
            continue
            
        # Lowercase, remove non-alphabetic chars
        clean_text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        
        # Tokenize by splitting on whitespace
        words = clean_text.split()
        
        # Remove stopwords and short words
        valid_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
        
        word_counts.update(valid_words)
        
    # Get top 150
    top_150 = [word for word, count in word_counts.most_common(150)]
    
    # Format and print the JS array output
    js_array = "const TOXICITY_DICTIONARY = " + str(top_150) + ";"
    print(js_array)
    
if __name__ == "__main__":
    extract_toxic_words()
