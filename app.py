from routes import app
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.example", override=False)

if __name__ == "__main__":
    app.run()
