try:
    import MeCab as mecab
except ImportError:
    try:
        import mecab
    except ImportError:
        mecab = None
        print("Warning: MeCab not available. Text analysis features will be limited.", flush=True)
import pandas as pd
import os

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# CSV file is only needed for testing, not production
data_path = os.path.join(backend_root, 'database', 'data', 'kaist_sentences.csv')
data = None
if os.path.exists(data_path):
    try:
        data = pd.read_csv(data_path)
    except Exception:
        pass

def save_freq(data):
    if mecab is None:
        print("Error: MeCab is not available. Cannot analyze text.", flush=True)
        return pd.DataFrame(columns=['word', 'pos', 'count', 'prob'])
    #text = data['sentence'].to_string()
    # Use Korean dictionary explicitly
    # Try different possible paths for Korean dictionary
    korean_dict_paths = [
        '/usr/local/lib/mecab/dic/mecab-ko-dic',  # Intel Mac
        '/opt/homebrew/lib/mecab/dic/mecab-ko-dic',  # Apple Silicon Mac
        '/usr/lib/mecab/dic/mecab-ko-dic',  # Linux
    ]
    
    tagger = None
    for dict_path in korean_dict_paths:
        if os.path.exists(dict_path):
            try:
                tagger = mecab.Tagger(f'-d {dict_path}')
                break
            except:
                continue
    
    # Fallback to system default if Korean dictionary not found
    if tagger is None:
        try:
            tagger = mecab.Tagger()
        except:
            print("Error: Failed to initialize MeCab tagger", flush=True)
            return pd.DataFrame(columns=['word', 'pos', 'count', 'prob'])
    #parsed = tagger.parse(text)   #test
    parsed = tagger.parse(data)
    tokens = []
    for line in parsed.splitlines():
        if line == "EOS" or not line.strip():
            continue

        try:
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            surface, features = parts
            col = features.split(",")
            
            # MeCab output can have variable number of fields
            # Ensure we have at least the minimum required fields
            if len(col) < 4:
                continue
            
            # Safely extract fields with defaults
            token = {
                'pos': col[0] if len(col) > 0 else '',
                'semantic': col[1] if len(col) > 1 else '',
                'has_badchim': col[2] if len(col) > 2 else '',
                'word': col[3] if len(col) > 3 else surface,  # fallback to surface if word not available
                'type': col[4] if len(col) > 4 else '',
                'start': col[5] if len(col) > 5 else '',
                'end': col[6] if len(col) > 6 else '',
                'expression': col[7] if len(col) > 7 else '',
            }
            tokens.append(token)
            
            # Process token transformations only if we have tokens
            if len(tokens) == 0:
                continue
                
            if tokens[-1]['type'] == 'Inflect':
                new_tokens = []
                expression = tokens[-1]['expression']
                if expression:
                    expression = expression.split("/") 
                    if len(expression) >= 2:
                        new_tokens.append({
                            'new_base': expression[0],
                            'base_pos': expression[1],
                        })
                        tokens.append({
                            'pos': new_tokens[0]['base_pos'],
                            'word': new_tokens[0]['new_base'],
                        })
                        tokens.pop(-2)

            if len(tokens) > 0 and tokens[-1]['pos'] == 'XSV':
                if len(tokens) >= 2:
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
        except Exception as e:
            # Skip malformed lines
            print(f"Warning: Skipping malformed MeCab line: {line[:50]}... Error: {e}", flush=True)
            continue
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
    if data is not None:
        save_freq(data)
    else:
        print("kaist_sentences.csv not found. This script requires the CSV file for testing.", flush=True)