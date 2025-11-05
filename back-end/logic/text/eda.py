import pandas as pd
from analysis import coverage, save_freq, update_frequency

df = pd.read_csv('/Users/slimslavik/Desktop/vorp_extra/news_clean.txt', 
                 sep='\t', 
                 header=None)
df.columns = ['sentence']

local = save_freq(df)
user = pd.read_csv('/Users/slimslavik/core/back-end/data/frequency.csv')

ratio, unknown_pos = coverage(local, user)
print(ratio, unknown_pos)

update_frequency(local)