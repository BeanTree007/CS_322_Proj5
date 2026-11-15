import os
import unittest
from unittest.mock import patch

from pymongo.errors import PyMongoError

with patch.dict(os.environ, {'MONGO_HOST': '127.0.0.1'}):
    import app as brevet_app


class SubmitTests(unittest.TestCase):
    def setUp(self):
        self.client = brevet_app.app.test_client()
        database_patch = patch.object(brevet_app, 'db')
        self.database = database_patch.start()
        self.addCleanup(database_patch.stop)
        self.payload = {
            'brevet_distance_km': '200',
            'start_time': '2024-01-01T06:00',
            'controls': [],
        }

    def test_submit_saves_recalculated_controls(self):
        self.payload['controls'] = [
            {'distance_km': '0', 'location': 'Start', 'open_time': 'forged'},
            {'distance_km': '60', 'location': ' Stop ', 'close_time': 'forged'},
            {'distance_km': '', 'location': ''},
        ]
        response = self.client.post('/submit', json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['message'], 'Submission saved successfully.')
        self.database.brevet_submissions.insert_one.assert_called_once_with({
            'brevet_distance_km': 200,
            'start_time': '2024-01-01T06:00:00',
            'controls': [
                {
                    'distance_km': 0.0,
                    'location': 'Start',
                    'open_time': '2024-01-01T06:00:00',
                    'close_time': '2024-01-01T07:00:00',
                },
                {
                    'distance_km': 60.0,
                    'location': 'Stop',
                    'open_time': '2024-01-01T07:46:00',
                    'close_time': '2024-01-01T10:00:00',
                },
            ],
        })

    def test_empty_and_incomplete_rows_are_rejected(self):
        for controls in ([], [{'distance_km': '', 'location': ''}],
                         [{'distance_km': '', 'location': 'Somewhere'}],
                         [{'distance_km': '', 'miles': '-1'}]):
            with self.subTest(controls=controls):
                self.payload['controls'] = controls
                response = self.client.post('/submit', json=self.payload)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.get_json()['error'])
        self.database.brevet_submissions.insert_one.assert_not_called()

    def test_invalid_inputs_are_rejected_without_partial_save(self):
        cases = [
            {'brevet_distance_km': '250'},
            {'brevet_distance_km': True},
            {'start_time': 'not a date'},
            {'start_time': '9999-12-31T23:59:59'},
            {'controls': [{'distance_km': '60'}, {'distance_km': '-1'}]},
            {'controls': [{'distance_km': 'NaN'}]},
            {'controls': [{'distance_km': True}]},
            {'controls': 'not a list'},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                payload = dict(self.payload, controls=[{'distance_km': '60'}])
                payload.update(changes)
                response = self.client.post('/submit', json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.get_json()['error'])
        self.database.brevet_submissions.insert_one.assert_not_called()

    def test_database_failure_returns_error(self):
        self.payload['controls'] = [{'distance_km': '60'}]
        self.database.brevet_submissions.insert_one.side_effect = PyMongoError('write failed')
        response = self.client.post('/submit', json=self.payload)
        self.assertEqual(response.status_code, 503)
        self.assertIn('Unable to save', response.get_json()['error'])

    def test_calculator_page_and_ajax_still_work(self):
        self.assertIn(b'id="submit_brevet"', self.client.get('/').data)
        response = self.client.get('/_calc_times', query_string={
            'km': '60', 'brevet_dist_km': '200', 'start_time': '2024-01-01T06:00',
        })
        self.assertEqual(response.get_json(), {'result': {
            'open': '2024-01-01T07:46:00',
            'close': '2024-01-01T10:00:00',
        }})
        self.database.brevet_submissions.insert_one.assert_not_called()


if __name__ == '__main__':
    unittest.main()
