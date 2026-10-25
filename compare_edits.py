import pandas as pd

qids = """Q104628357 Q6378448 Q5550287 Q48780757 Q3351954 Q106543278
Q10341918 Q21267058 Q16493032 Q10340893 Q16654024 Q16653562 Q10338898
Q16654213 Q2841824 Q3264097 Q5961258 Q3347777 Q3356884 Q9558817
Q3549132 Q3474995 Q16682813 Q10318904 Q9558784 Q3504961 Q3220460""".split()

def load(folder):
    parts = [pd.read_csv(f"{folder}/{c}_clean.csv") for c in ["belgium", "portugal"]]
    return pd.concat(parts).set_index("qid")

before = load("data")
after = load("data/after")
b = before.loc[qids, "has_english_label"]
a = after.loc[qids, "has_english_label"]
print("Labelled before:", b.sum(), "of", len(qids))
print("Labelled after: ", a.sum(), "of", len(qids))
print("Newly labelled: ", int((a & ~b).sum()))
