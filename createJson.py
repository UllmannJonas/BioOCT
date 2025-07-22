import os
import json

base_path = os.path.dirname(os.path.abspath(__file__))
images_path = os.path.join(base_path, 'imagesTr')
labels_path = os.path.join(base_path, 'labelsTr')    

# Liste der Bilddateien (.nii.gz) im imagesTr Ordner
image_files = sorted([f for f in os.listdir(images_path) if f.endswith('.nii.gz')])
label_files = sorted([f for f in os.listdir(labels_path) if f.endswith('.nii.gz')])

# Sicherstellen, dass Bild- und Labeldateien übereinstimmen
if len(image_files) != len(label_files):
    raise ValueError("There must be an equal number of image and label files.")

# Aufbau der Trainingseinträge
training_entries = []
for img_file, lbl_file in zip(image_files, label_files):
    training_entries.append({
        "image": f"./imagesTr/{img_file}",
        "label": f"./labelsTr/{lbl_file}"
    })

# JSON-Struktur
data = {
    "modality": {
        "0": "CT"
    },
    "labels": {
        "background": 0
    },
    "numTraining": len(image_files),
    "file_ending": ".nii.gz",
    "dataset_name": "Mina",
    "release": "1.0",
    "training": training_entries
}

# JSON speichern
output_file = os.path.join(base_path, 'dataset.json')

if os.path.exists(output_file):
    user_input = input(f"File {output_file} already exists. Overwrite? (y/n): ")
    if user_input.lower() != 'y':
        exit()

with open(output_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"JSON Datei erfolgreich erstellt: {output_file}")