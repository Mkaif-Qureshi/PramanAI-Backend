import spacy

# Load the model directly from the directory
nlp = spacy.load("D:\\Kaif\\Hackathon\\Suprem court\\Application\\pramanai-backend\\en_legal_ner_trf")

# Test the model with some text
doc = nlp("Some legal text to analyze")
for ent in doc.ents:
    print(ent.text, ent.label_)
