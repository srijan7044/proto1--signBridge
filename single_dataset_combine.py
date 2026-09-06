import os
import pandas as pd

words_csv = os.path.join("data", "gestures.csv")
letters_csv = os.path.join("data", "gestures_letters.csv")
combined_csv = os.path.join("data", "gestures_combined.csv")

df_words = pd.read_csv(words_csv)
df_letters = pd.read_csv(letters_csv)

# Concatenate vertically
df_combined = pd.concat([df_words, df_letters], ignore_index=True)
df_combined.to_csv(combined_csv, index=False)

print(f"Combined dataset saved to '{combined_csv}' with {df_combined.shape[0]} total samples across {df_combined['label'].nunique()} classes.")