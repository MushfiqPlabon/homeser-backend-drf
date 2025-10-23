import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Drops and re-creates the database."

    def handle(self, *args, **options):
        db_name = connection.settings_dict["NAME"]
        if connection.vendor == "sqlite":
            self.stdout.write(
                self.style.WARNING(f"Deleting SQLite database file: {db_name}")
            )
            if os.path.exists(db_name):
                os.remove(db_name)
            # Also clear media directory if exists
            media_path = Path(settings.BASE_DIR) / "media"
            if media_path.exists():
                import shutil

                shutil.rmtree(media_path)
        elif connection.vendor == "postgresql":
            # For PostgreSQL, we need to connect to a different database to drop the target database
            # Common practice is to connect to the 'postgres' database
            pass

            # Close the current connection
            connection.close()

            # Create a new connection to the 'postgres' database
            db_settings = connection.settings_dict.copy()
            db_settings["NAME"] = "postgres"

            try:
                # Try connecting to 'postgres' database
                from django.db import utils

                postgres_conn = utils.ConnectionHandler({"default": db_settings})[
                    "default"
                ]

                with postgres_conn.cursor() as cursor:
                    self.stdout.write(f"Dropping database {db_name}...")
                    cursor.execute(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
                    self.stdout.write(f"Creating database {db_name}...")
                    cursor.execute(f"CREATE DATABASE {db_name};")

                postgres_conn.close()
            except Exception as e:
                # If connecting to 'postgres' fails, fall back to dropping all tables individually
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not connect to 'postgres' database to drop {db_name}. "
                        f"Falling back to individual table dropping. Error: {e}"
                    )
                )

                # Reconnect to the target database
                connection.connect()

                # Get all table names
                table_names = connection.introspection.table_names()

                # Drop all tables one by one
                with connection.cursor() as cursor:
                    for table_name in table_names:
                        try:
                            cursor.execute(
                                f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'
                            )
                            self.stdout.write(f"Dropped table: {table_name}")
                        except Exception as table_e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Could not drop table {table_name}: {table_e}"
                                )
                            )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully dropped all tables in database {db_name}."
                    )
                )

        self.stdout.write(self.style.SUCCESS("Successfully erased the database."))
