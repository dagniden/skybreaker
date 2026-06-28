import sqlite3
from contextlib import closing
from datetime import datetime, timezone


STATUS_PENDING = 'pending'
STATUS_REGISTERED = 'registered'
STATUS_FAILED_TO_REGISTER = 'failed_to_register'


class DiscoveryCache:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self):
        with closing(self.connect()) as connection:
            connection.execute(
                '''
                create table if not exists discovered_files (
                    fingerprint text primary key,
                    file_path text not null,
                    file_name text not null,
                    file_size integer not null,
                    modified_at text not null,
                    django_job_id integer,
                    status text not null,
                    last_error text not null default '',
                    last_sent_at text,
                    created_at text not null,
                    updated_at text not null
                )
                '''
            )
            connection.commit()

    def get_status(self, fingerprint):
        with closing(self.connect()) as connection:
            row = connection.execute(
                'select status from discovered_files where fingerprint = ?',
                (fingerprint,),
            ).fetchone()
        return row['status'] if row else None

    def should_send(self, fingerprint):
        return self.get_status(fingerprint) != STATUS_REGISTERED

    def mark_pending(self, recording):
        now = utc_now_iso()
        with closing(self.connect()) as connection:
            connection.execute(
                '''
                insert into discovered_files (
                    fingerprint, file_path, file_name, file_size, modified_at,
                    status, last_sent_at, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(fingerprint) do update set
                    file_path = excluded.file_path,
                    file_name = excluded.file_name,
                    file_size = excluded.file_size,
                    modified_at = excluded.modified_at,
                    status = excluded.status,
                    last_sent_at = excluded.last_sent_at,
                    updated_at = excluded.updated_at
                ''',
                (
                    recording.fingerprint,
                    recording.file_path,
                    recording.file_name,
                    recording.file_size,
                    recording.modified_at.isoformat(),
                    STATUS_PENDING,
                    now,
                    now,
                    now,
                ),
            )
            connection.commit()

    def mark_registered(self, fingerprint, django_job_id):
        now = utc_now_iso()
        with closing(self.connect()) as connection:
            connection.execute(
                '''
                update discovered_files
                set status = ?, django_job_id = ?, last_error = '', updated_at = ?
                where fingerprint = ?
                ''',
                (STATUS_REGISTERED, django_job_id, now, fingerprint),
            )
            connection.commit()

    def mark_failed_to_register(self, fingerprint, error):
        now = utc_now_iso()
        with closing(self.connect()) as connection:
            connection.execute(
                '''
                update discovered_files
                set status = ?, last_error = ?, updated_at = ?
                where fingerprint = ?
                ''',
                (STATUS_FAILED_TO_REGISTER, str(error), now, fingerprint),
            )
            connection.commit()


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()
