ENV = "prod" 

def log(message):
    """Logs a message if in development environment."""
    if ENV == "dev":
        print(message)