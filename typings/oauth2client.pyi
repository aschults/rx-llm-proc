from google.auth import credentials

# Fake credentials type so pyright doesn't choke on `googleapiclient-stubs`
Credentials = credentials.Credentials
