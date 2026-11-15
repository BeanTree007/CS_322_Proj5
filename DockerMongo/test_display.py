import os
import unittest
from unittest.mock import patch

from pymongo.errors import PyMongoError

with patch.dict(os.environ, {'MONGO_HOST': '127.0.0.1'}):
    import app as brevet_app


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.client = brevet_app.app.test_client()
        database_patch = patch.object(brevet_app, 'db')
        self.database = database_patch.start()
        self.addCleanup(database_patch.stop)

    def test_display_renders_saved_submissions(self):
        self.database.brevet_submissions.find.return_value = iter([
            {
                'brevet_distance_km': 200,
                'start_time': '2024-01-01T06:00:00',
                'controls': [
                    {'distance_km': 0.0, 'location': 'Start',
                     'open_time': '2024-01-01T06:00:00',
                     'close_time': '2024-01-01T07:00:00'},
                    {'distance_km': 60.0, 'location': '<Stop>',
                     'open_time': '2024-01-01T07:46:00',
                     'close_time': '2024-01-01T10:00:00'},
                ],
            },
            {
                'brevet_distance_km': 300,
                'start_time': '2024-02-01T08:00:00',
                'controls': [
                    {'distance_km': 10.0, 'location': '',
                     'open_time': '2024-02-01T08:18:00',
                     'close_time': '2024-02-01T09:30:00'},
                ],
            },
        ])
        response = self.client.get('/display')

        self.assertEqual(response.status_code, 200)
        for value in (b'Brevet: 200 km', b'Brevet: 300 km',
                      b'2024-01-01T06:00:00', b'2024-02-01T08:00:00',
                      b'0.0', b'60.0', b'10.0', b'Start', b'&lt;Stop&gt;',
                      b'2024-01-01T07:46:00', b'2024-01-01T10:00:00',
                      b'2024-02-01T08:18:00', b'2024-02-01T09:30:00'):
            self.assertIn(value, response.data)
        self.assertNotIn(b'No brevet submissions found.', response.data)
        self.database.brevet_submissions.find.assert_called_once_with()

    def test_display_reports_empty_database(self):
        self.database.brevet_submissions.find.return_value = iter([])
        response = self.client.get('/display')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No brevet submissions found.', response.data)

    def test_display_reports_cursor_read_failure(self):
        def failing_cursor():
            raise PyMongoError('read failed')
            yield

        self.database.brevet_submissions.find.return_value = failing_cursor()
        response = self.client.get('/display')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'Unable to retrieve brevet submissions.', response.data)
        self.assertNotIn(b'No brevet submissions found.', response.data)

    def test_calculator_links_to_display(self):
        response = self.client.get('/')
        self.assertIn(b'action="/display"', response.data)
        self.assertIn(b'>Display</button>', response.data)


if __name__ == '__main__':
    unittest.main()
