from decouple import config

# Print all database related environment variables
print("DB Name:", config("DB_NAME", default=None))
print("DB User:", config("DB_USER", default=None))
print("DB Password:", config("DB_PASSWORD", default=None))
print("DB Host:", config("DB_HOST", default=None))
print("DB Port:", config("DB_PORT", default=None))
