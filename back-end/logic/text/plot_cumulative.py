import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('/Users/slimslavik/core/back-end/data/frequency.csv')

# Add cumulative probabilities if they don't exist
if 'prob' not in df.columns:
    df['prob'] = df['freq'] / df['freq'].sum()
    df['cumulative'] = df['prob'].cumsum()
else:
    df['prob'] = df['prob'] / 100
    df['cumulative'] = df['prob'].cumsum()

# Sort by count (already sorted from analysis.py)
plt.figure(figsize=(12, 8))
plt.plot(range(1, len(df)+1), df['cumulative'], linewidth=2)

# Add markers for key percentiles
percentiles = [0.5, 0.8, 0.9, 0.95, 0.98]
colors = ['red', 'orange', 'yellow', 'green', 'blue']

for i, percentile in enumerate(percentiles):
    # Find first rank where cumulative >= percentile
    mask = df['cumulative'] >= percentile
    if mask.any():
        rank_idx = df[mask].index[0]
        rank = rank_idx + 1  # 1-indexed ranking
        cum_prob = df.iloc[rank_idx]['cumulative']
        
        # Plot point and add label
        plt.plot(rank, cum_prob, 'o', color=colors[i], markersize=8)
        plt.annotate(f'Rank {rank}', 
                    (rank, cum_prob), 
                    xytext=(10, 10), 
                    textcoords='offset points',
                    fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=colors[i], alpha=0.7))

plt.xlabel('Word Rank')
plt.ylabel('Cumulative Probability')
plt.title('Cumulative Probability Distribution with Key Percentiles')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()