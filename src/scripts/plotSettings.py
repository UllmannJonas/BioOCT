import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

settings_folder = Path(".")

filter_sizes = {}
roi_sizes = {}
contrast_percetiles = {}
binarization_thresholds = {}
outlier_sizes = {}

for file in settings_folder.glob("*.json"):
    if file.name.startswith("settings_"):
        with open(file, "r") as f:
            data = json.load(f)
        user_handle = data.get("handle_input", {}).get("input_text", "")
        filter_sizes[user_handle] = data.get("median_filter", {}).get("filter_size")
        roi_sizes[user_handle] = data.get("roi_filter_2D", {}).get("roi_size")
        contrast_percetiles[user_handle] = data.get("increase_contrast", {}).get("percentile")
        binarization_thresholds[user_handle] = data.get("binarize", {}).get("threshold")
        outlier_sizes[user_handle] = data.get("remove_outliers", {}).get("outlier_size")

users = list(filter_sizes.keys())
labels = ["Filter Size", "ROI Size", "Contrast Percentile", "Binarization Threshold", "Outlier Size"]
data = []
for user in users:
    data.append([
        filter_sizes.get(user, 0),
        roi_sizes.get(user, 0),
        contrast_percetiles.get(user, 0),
        binarization_thresholds.get(user, 0),
        outlier_sizes.get(user, 0),
    ])

data = np.array(data)

x = np.arange(len(labels))
width = 0.5 / len(users)

fig, ax = plt.subplots(figsize=(12, 6))

for i, user in enumerate(users):
    ax.bar(x + i*width, data[i], width, label=user)

ax.set_xticks(x + width*(len(users)-1)/2)
ax.set_xticklabels(labels)
ax.set_ylabel('Setting Value')
ax.set_title('User setting comparison')
ax.legend(title="Users")
ax.grid(axis='y')

plt.tight_layout()
plt.show()