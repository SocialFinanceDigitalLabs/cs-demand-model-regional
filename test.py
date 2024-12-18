import pandas as pd

df = pd.read_csv("samples/v1/episodes.csv")

print(len(df["PLACE"].unique()))
