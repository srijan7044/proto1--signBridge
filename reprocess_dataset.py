import pandas as pd
import numpy as np

# 1. Load the original raw dataset
df_raw = pd.read_csv("data/gestures_letters_1.csv")
labels = df_raw["label"].values
feature_matrix = df_raw.drop(columns=["label"]).values

print(f"Original dataset shape: {df_raw.shape}")

# 2. Re-slot single-hand gestures into Slot 0 (Primary)
new_rows = []
for idx, row in enumerate(feature_matrix):
    left_hand = row[0:63]
    right_hand = row[63:126]
    
    has_left = np.any(np.abs(left_hand) > 1e-4)
    has_right = np.any(np.abs(right_hand) > 1e-4)
    
    new_vector = np.zeros(126, dtype=np.float32)
    
    # If only one hand is populated (either left or right slot), force it into Slot 0
    if has_left and not has_right:
        new_vector[0:63] = left_hand
    elif has_right and not has_left:
        new_vector[0:63] = right_hand
    else:
        new_vector = row.copy()
        
    new_rows.append(new_vector)

# 3. Rebuild DataFrame and remove duplicates caused by slot alignment
df_aligned = pd.DataFrame(new_rows, columns=[f"f{i}" for i in range(126)])
df_aligned.insert(0, "label", labels)
df_clean = df_aligned.drop_duplicates().reset_index(drop=True)

# 4. Apply light Gaussian jitter augmentation to balance all classes to 1,000 samples
np.random.seed(42)
target_per_class = 1000
augmented_dfs = []

for label, group in df_clean.groupby("label"):
    feature_cols = [c for c in group.columns if c != "label"]
    current_len = len(group)
    n_needed = max(target_per_class, current_len)
    
    indices = np.random.choice(group.index, size=n_needed, replace=True)
    sampled = group.loc[indices, feature_cols].values
    
    noise = np.random.normal(0.0, 0.015, size=sampled.shape)
    mask = (sampled != 0.0)
    jittered = np.where(mask, sampled + noise, 0.0)
    
    df_synth = pd.DataFrame(jittered, columns=feature_cols)
    df_synth.insert(0, "label", label)
    augmented_dfs.append(df_synth)

df_enhanced = pd.concat(augmented_dfs, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)

# 5. Overwrite the enhanced CSV file
output_path = "data/gestures_letters_enhanced (1).csv"
df_enhanced.to_csv(output_path, index=False)
print(f"Successfully updated {output_path} with {len(df_enhanced)} aligned samples.")