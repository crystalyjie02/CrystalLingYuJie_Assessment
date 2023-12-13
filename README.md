# Example setup commands
To install all the packages, run this command:
pip install -r requirements.txt

To start the server, run this command:
uvicorn main:app --reload

# Configure .env file
To generate a secret key, run this command:
openssl rand -hex 32

SECRET_KEY = "#"
ALGORITHM = "#"
ACCESS_TOKEN_EXPIRE_MINUTES = #

If you are using localhost db, then no need to provide the database port number (in my case, I am using MySQL):
DATABASE_HOST = #
DATABASE_PORT = #
DATABASE_USER = #
DATABASE_PASSWORD = #
DATABASE = #

# Endpoints
'/token' : Description of the login endpoint
'/register': Description of the registration endpoint
'/login': Description of the login page.
