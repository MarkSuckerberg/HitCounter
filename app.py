from simple import app
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    load_dotenv(".env.example", override=False)
    app.run()
