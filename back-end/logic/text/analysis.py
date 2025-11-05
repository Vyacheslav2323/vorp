import mecab
import pandas as pd
import os

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
data_path = os.path.join(backend_root, 'database', 'data', 'kaist_sentences.csv')
data = pd.read_csv(data_path)

def save_freq(data):
    #text = data['sentence'].to_string()
    tagger = mecab.Tagger()
    #parsed = tagger.parse(text)   #test
    parsed = tagger.parse(data)
    tokens = []
    for line in parsed.splitlines():
        if line == "EOS":
            continue

        surface, features = line.split("\t",1)
        col = features.split(",")
        tokens.append({
            'pos': col[0],
            'semantic': col[1],
            'has_badchim': col[2],
            'word': col[3],
            'type': col[4],
            'start': col[5],
            'end': col[6],
            'expression': col[7],
        })
        if tokens[-1]['type'] == 'Inflect':
            new_tokens = []
            expression = tokens[-1]['expression']
            expression = expression.split("/") 
            new_tokens.append({
                'new_base': expression[0],
                'base_pos': expression[1],
            })
            tokens.append({
                'pos': new_tokens[0]['base_pos'],
                'word': new_tokens[0]['new_base'],
            })
            tokens.pop(-2)

        if tokens[-1]['pos'] == 'XSV':
            new_tokens = tokens[-2]['word'] + tokens[-1]['word'] + '다'
            tokens.append({
                'word': new_tokens,
                'pos': 'V1',
            })
            tokens.pop(-3)
        if len(tokens) >= 2 and tokens[-2]['pos'] in ['XR']:
            new_tokens = tokens[-2]['word'] + tokens[-1]['word'] + '다'
            tokens.append({
                'word': new_tokens,
                'pos': 'V2',
            })
            tokens.pop(-3)
        if len(tokens) >= 2 and tokens[-2]['pos'] in ['XPN']:
            new_tokens = tokens[-2]['word'] + tokens[-1]['word']
            tokens.append({
                'word': new_tokens,
                'pos': 'NEW',
            })
            tokens.pop(-2)
    df = pd.DataFrame(tokens)
    df = df[df['pos'].isin(['NNG', 'VA', 'VV', 'V','MAG','MM','NP', 'NR', 'NEW', 'V1', 'V2'])]
    mask = df['pos'].isin(['VA','VV'])
    if mask.any():
        df.loc[mask, 'word'] = df.loc[mask, 'word'] + '다'

    df=df[['word','pos']]
    df=df.groupby(['word', 'pos']).size().reset_index(name='count')
    df = df[~df['word'].fillna('').str.contains('*', regex=False)]    
    df=df.sort_values(by='count', ascending=False)
    df['prob'] = df['count'] / df['count'].sum()
    return df

def coverage(local, user):
    local_words = set(local['word'])
    user_words = set(user['word'])
    overlap = local_words.intersection(user_words)
    ratio = sum(local[local['word'].isin(overlap)]['prob'])
    unknown = local_words - user_words
    unknown_pos = local[local['word'].isin(unknown)][['word', 'pos']]
    return ratio, unknown_pos

def update_frequency(local):
    local = local[['word','pos','count']].copy()
    freq_path = os.path.join(backend_root, 'database', 'data', 'frequency.csv')
    gf = pd.read_csv(freq_path).reindex(columns=['word','pos','description','freq'])
    def to_row(r):
        return pd.DataFrame([{'word': r['word'], 'pos': r['pos'], 'description': '', 'freq': int(r['count'])}])
    for _, r in local.iterrows():
        m = gf['word'].eq(r['word'])
        if m.any():
            gf.loc[m, 'freq'] += int(r['count'])
        else:
            gf = pd.concat([gf, to_row(r)], ignore_index=True)
    gf.to_csv(freq_path, index=False)
    return gf


if __name__ == "__main__":
    save_freq(data)