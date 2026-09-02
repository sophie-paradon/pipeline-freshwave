import pipeline

df = pipeline.fetch_weather_for_city("Paris", 48.8566, 2.3522)

print(df.shape)
print(df.head(3))
print(df.dtypes)
