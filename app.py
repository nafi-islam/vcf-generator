# entry point. `flask run` finds a file named app.py automatically, and vercel looks
# for an object named `app` in app.py, so both local dev and deployment start here
from webapp import create_app

app = create_app()
