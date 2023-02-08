import json
from datetime import datetime
import re
import structlog
from sqlalchemy.exc import OperationalError, IntegrityError, ProgrammingError
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker

from log import configure_logging
from secret_manager import get_secret


def get_database_connection():
    return create_engine(get_secret("DATABASE_URL")).execution_options(isolation_level="AUTOCOMMIT")

"""
Table pg_stat_activity
 datid | datname | pid  | usesysid | usename | application_name |  client_addr   |          client_hostname          | client_port |         backend_start         |          xact_start           |          query_start          |         state_change          | wait_event_type | wait_event | state  | backend_xid | backend_xmin |                         query                          |  backend_type
-------+---------+------+----------+---------+------------------+----------------+-----------------------------------+-------------+-------------------------------+-------------------------------+-------------------------------+-------------------------------+-----------------+------------+--------+-------------+--------------+--------------------------------------------------------+----------------
 16391 | crm     | 6120 |    16389 | crm     | psql             | 169.150.204.34 | unn-169-150-204-34.datapacket.com |       29409 | 2023-02-04 16:58:35.635358+00 | 2023-02-04 18:26:49.557535+00 | 2023-02-04 18:26:49.557535+00 | 2023-02-04 18:26:49.557538+00 |                 |            | active |             |       467264 | SELECT * FROM pg_stat_activity WHERE state = 'active'; | client backend
"""


def configure_db(event=None, context=None):
    configure_logging()
    logger = structlog.get_logger()
    logger.info("Running")
    password = "XXXX1234"
    with sessionmaker(bind=get_database_connection())() as session:
        # Validate the wal level is logical
        query = text("show wal_level;")
        result = session.execute(query).first()
        assert result[0] == "logical"

        # FIXME: make publication and slot names flexible
        pub_exists = session.execute(text("SELECT pubname FROM pg_publication WHERE pubname = 'data_stream';")).first()
        logger.info(f"Pub exisits: {pub_exists}")
        if not pub_exists:
            session.execute(text("CREATE PUBLICATION data_stream FOR ALL TABLES;"))

        slot_exists = session.execute(text("SELECT slot_name from pg_replication_slots WHERE slot_name = 'data_stream_slot';")).first()
        logger.info(f"Slot exisits: {slot_exists}")
        if not slot_exists:
            session.execute(text("SELECT PG_CREATE_LOGICAL_REPLICATION_SLOT('data_stream_slot', 'pgoutput');"))

        cmds = [
        f"CREATE USER data_stream WITH ENCRYPTED PASSWORD '{password}';",
        "GRANT RDS_REPLICATION TO data_stream;",
        "GRANT SELECT ON ALL TABLES IN SCHEMA public TO data_stream;",
        "GRANT USAGE ON SCHEMA public TO data_stream;",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO data_stream;"

        # Only to use in crm public snapshot on AWS
        # "GRANT SELECT ON ALL TABLES IN SCHEMA iklin TO data_stream;",
        # "GRANT SELECT ON ALL TABLES IN SCHEMA gplus TO data_stream;",
        # "GRANT SELECT ON ALL TABLES IN SCHEMA test TO data_stream;",
        # "GRANT USAGE ON SCHEMA iklin TO data_stream;",
        # "GRANT USAGE ON SCHEMA gplus TO data_stream;",
        # "GRANT USAGE ON SCHEMA test TO data_stream;",
        ]

        for cmd in cmds:
            try:
                result = session.execute(text(f"{cmd} COMMIT;"))
                logger.info(result)
            except (IntegrityError, ProgrammingError) as ex:
                logger.error(ex)


def process(event=None, context=None):
    configure_logging()
    logger = structlog.get_logger()
    with sessionmaker(bind=get_database_connection())() as session:
        query = text("SELECT pid FROM pg_stat_activity WHERE state = 'active' AND usename = 'data_stream';")
        result = session.execute(query).first()
        if result:
            pid = result[0]
            print(f"Killing PID: {pid}")
            # starts" a request to terminate gracefully, which may be satisfied after some time
            cancel_session_query = text(f"select pg_cancel_backend(pid) from pg_stat_activity where pid = '{pid}';")
            # kill the proccess hardly
            kill_session_query = text(f"select pg_terminate_backend(pid) from pg_stat_activity where pid = '{pid}';")

            try:
                logger.info("drop session")
                kresult = session.execute(cancel_session_query)
                logger.info(kresult.all())
            except OperationalError as ex:
                logger.error(ex)
        else:
            logger.info("No process PID found, proceding")
            slot_exists = session.execute(text("SELECT slot_name from pg_replication_slots WHERE slot_name = 'data_stream_slot';")).first()
            if slot_exists:
                drop_slot_query = text("SELECT pg_drop_replication_slot('data_stream_slot');")
                logger.info("Droping slot")
                session.execute(drop_slot_query)
    print("ok")


def data_simulator(event=None, context=None):
    configure_logging()
    logger = structlog.get_logger()
    with sessionmaker(bind=get_database_connection())() as session:
        for schema in ['public', 'gplus', 'iklin']:
            for i in range(1000):
                # query = text(f"INSERT INTO {schema}.django_migrations (app, name, applied) VALUES('x-{schema}-{i}', 'name-{schema}-{i**2}', NOW()); COMMIT;")
                query = text(re.sub(r"\[|\]", "", f"INSERT INTO {schema}.django_migrations (app, name, applied) VALUES {[(f'x-{schema}-{i}', f'name-{schema}-{i**2}', datetime.now().isoformat()) for i in range(1000)]}; COMMIT;"))
                logger.info(f"schema: {schema}, i:{i}, query: {query}")
                result = session.execute(query)
    logger.info("All data inserted")


def run(event, context):
    body = {
        "message": "Function executed successfully!",
        "event": event
    }
    configure_logging()
    logger = structlog.get_logger()
    logger.info("Running")
    # configure_db()
    process()
    logger.info(json.dumps(body))
    return {"statusCode": 200, "body": json.dumps(body)}
