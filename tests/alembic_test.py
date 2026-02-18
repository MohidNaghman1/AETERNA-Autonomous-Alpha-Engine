import psycopg2
conn = psycopg2.connect(
    dbname="aeterna",
    user="postgres",
    password="mohid708@",
    host="127.0.0.1",
    port=5432
)
print("Connected!")