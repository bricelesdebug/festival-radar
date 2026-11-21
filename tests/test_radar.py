import copy
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import collect
import detect_alerts
import extract_official_events as structured
from preview_alerts import matches, preview

NOW = dt.datetime(2026, 10, 24, tzinfo=dt.timezone.utc)

def event(eid='a'):
    return {'id':eid, 'name':'Test Festival', 'url':'https://example.com/tickets',
            'classifications':[{'genre':{'name':'Electronic'}}],
            'dates':{'start':{'localDate':'2027-06-01'}}}

class CollectionTests(unittest.TestCase):
    def test_normalize_keeps_source_and_unverified_status(self):
        e = collect.normalize(event(), 'FR')
        self.assertEqual(e['festivalConfidence'], 'unverified')
        self.assertEqual(e['saleStatus'], 'unverified')
        self.assertEqual(e['countryCode'], 'FR')

    def test_rejects_unsafe_url(self):
        e = event(); e['url'] = 'javascript:alert(1)'
        self.assertIsNone(collect.normalize(e, 'FR'))

    def test_unknown_date_not_fabricated(self):
        e = event(); e['dates']['start']['dateTBA'] = True
        self.assertIsNone(collect.normalize(e, 'FR'))

    def test_non_electronic_not_admitted(self):
        e = event(); e['classifications'][0]['genre']['name'] = 'Rock'
        self.assertIsNone(collect.normalize(e, 'FR'))

    def test_manifest_is_not_festival(self):
        e = event(); e['name'] = 'Manifest party'
        self.assertIsNone(collect.normalize(e, 'FR'))

    def test_reads_third_page_and_deduplicates(self):
        calls = []
        def fetch(params):
            calls.append(params['page'])
            return {'_embedded':{'events':[event(str(params['page']))]*100},
                    'page':{'totalPages':3}}
        with patch.object(collect, 'COUNTRIES', {'FR':'France'}):
            records, report = collect.collect('not-a-key', NOW, fetch)
        self.assertEqual(calls, [0, 1, 2])
        self.assertEqual(len(records), 3)
        self.assertTrue(report['complete'])

    def test_failed_country_preserves_catalog(self):
        def fail(_): raise RuntimeError('secret-in-url')
        with patch.object(collect, 'COUNTRIES', {'FR':'France'}):
            records, report = collect.collect('not-a-key', NOW, fail)
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'catalog.json'; p.write_text('existing')
            with self.assertRaises(ValueError): collect.publish(records, report, p)
            self.assertEqual(p.read_text(), 'existing')
        self.assertNotIn('secret', json.dumps(report))

    def test_paging_cap_is_not_complete(self):
        def fetch(_):
            return {'_embedded':{'events':[event()]*100}, 'page':{'totalPages':11}}
        with patch.object(collect, 'COUNTRIES', {'FR':'France'}):
            _, report = collect.collect('not-a-key', NOW, fetch)
        self.assertFalse(report['complete'])

    def test_success_writes_parseable_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'data.json'
            collect.publish({'a':collect.normalize(event(), 'FR')},
                            {'complete':True, 'updatedAt':NOW.isoformat()}, p)
            self.assertEqual(json.loads(p.read_text())['events'][0]['id'], 'a')

    def test_empty_collection_preserves_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'data.json'; p.write_text('existing')
            with self.assertRaises(ValueError):
                collect.publish({}, {'complete':True}, p)
            self.assertEqual(p.read_text(), 'existing')

class AlertTests(unittest.TestCase):
    def test_empty_baseline_never_announces_catalog(self):
        self.assertEqual(detect_alerts.detect({}, {'a':event()}), [])

    def test_unchanged_catalog_has_no_changes(self):
        self.assertEqual(detect_alerts.detect({'a':event()}, {'a':event()}), [])

    def test_date_change_preserves_matching_context(self):
        old = {'id':'a','date':'2027-06-01'}
        new = dict(old, date='2027-06-02', countryCode='FR', genres=['Techno'])
        changes = detect_alerts.detect({'a':old}, {'a':new})
        self.assertEqual(changes[0]['payload']['countryCode'], 'FR')
        self.assertEqual(changes[0]['event_type'], 'event_date_changed')

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'data.json'; p.write_text(json.dumps({'events':[event(), event()]}))
            with self.assertRaises(ValueError): detect_alerts.read_events(p)

    def test_replayed_snapshot_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'data.json'
            p.write_text(json.dumps({'updatedAt':NOW.isoformat(), 'events':[event()]}))
            result = subprocess.run([sys.executable, 'scripts/detect_alerts.py', str(p), str(p)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'increasing', result.stderr)

    def test_staging_defaults_to_offline_preview(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'candidates.json'; p.write_text('{"changes":[]}')
            result = subprocess.run([sys.executable, 'scripts/stage_inbox.py', str(p)], capture_output=True, env={})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'No database writes', result.stdout)

    def test_apply_requires_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'candidates.json'; p.write_text('{"changes":[]}')
            result = subprocess.run([sys.executable, 'scripts/stage_inbox.py', str(p), '--apply'], capture_output=True, env={})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'explicit operator approval', result.stderr)

class PersonalizationTests(unittest.TestCase):
    def test_country_filter(self):
        self.assertFalse(matches({'countryCode':'BE'}, {'countries':['FR']}))

    def test_broad_electronic_does_not_imply_techno(self):
        self.assertFalse(matches({'genres':['Electronic']}, {'genres':['Techno']}))

    def test_case_insensitive_genre(self):
        self.assertTrue(matches({'genres':['TECHNO']}, {'genres':['Techno']}))

    def test_following_consent_and_deduplication(self):
        c = {'event_key':'a:date', 'festival_id':'a', 'payload':{'countryCode':'FR'}}
        users = [{'user_id':'u', 'favorites':['a'], 'countries':['FR'], 'email_enabled':False},
                 {'user_id':'other', 'favorites':[]}]
        rows = preview([c, c], users)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]['delivery_enabled'])
        self.assertFalse(rows[0]['email_consent'])
        self.assertTrue(rows[0]['review_required'])

class OfficialSourceTests(unittest.TestCase):
    def test_music_event_in_graph(self):
        data = {'@graph':[{'@type':['Thing','MusicEvent'], 'name':'Test'}]}
        self.assertEqual(len(list(structured.walk(data))), 1)

    def test_schema_url_and_nested_festival(self):
        data = {'mainEntity':{'@type':'https://schema.org/Festival', 'name':'Test'}}
        self.assertEqual(len(list(structured.walk(data))), 1)

    def test_invalid_type_is_ignored(self):
        self.assertEqual(list(structured.walk({'@type':42})), [])

    def test_candidates_remain_source_claims(self):
        result = structured.summarize({'@type':'MusicEvent', 'name':'Test', 'startDate':'2027-01-01'})
        self.assertNotIn('verified', result)
        self.assertEqual(result['startDate'], '2027-01-01')

if __name__ == '__main__':
    unittest.main()
