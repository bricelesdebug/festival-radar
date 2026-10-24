#!/usr/bin/env python3
"""Live Supabase smoke test using disposable users; never sends auth emails.

Service-role credentials stay in memory. Only test-owned rows are touched.
Only inactive Free subscription fixtures are created, then deleted by user cascade.
No alert events, deliveries, paid subscriptions or billing records are created.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import functools
import http.server
import subprocess
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class Api:
    def __init__(self, base, public_key, service_key):
        self.base, self.public, self.service = base.rstrip('/'), public_key, service_key

    def call(self, method, path, body=None, token=None, admin=False, prefer=None):
        headers = {'apikey':self.service if admin else self.public, 'Content-Type':'application/json'}
        if admin or token:
            headers['Authorization'] = 'Bearer ' + (self.service if admin else token)
        if prefer:
            headers['Prefer'] = prefer
        request = urllib.request.Request(self.base + path, method=method, headers=headers,
            data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read())
            except ValueError:
                data = {}
            # Returned in memory only. Never print backend responses or credentials.
            return exc.code, data
        except (OSError, ValueError):
            raise RuntimeError('Supabase unreachable or invalid response') from None


def require(condition, label):
    if not condition:
        raise RuntimeError(label)


def browser_journey(email, password):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(['node', str(ROOT/'tests/live-browser.cjs')],
                input=json.dumps({'url':f'http://127.0.0.1:{server.server_port}',
                                  'email':email, 'password':password}),
                text=True, capture_output=True, timeout=180)
            if result.returncode != 0:
                safe = result.stderr.strip()
                if re.fullmatch(r'Browser journey failed at stage: [a-z]+', safe):
                    raise RuntimeError(safe)
                raise RuntimeError('browser_journey')
        finally:
            server.shutdown()


def run(api, browser=False, checks=None):
    if checks is None:
        checks = []
    users, tokens, credentials = [], [], []
    nonce = secrets.token_hex(12)
    try:
        # Admin createUser confirms the synthetic account without sending email.
        # Do not use signup, invite, recover, magic links or password email flows.
        for _ in range(2):
            email = 'radar-validation-' + secrets.token_hex(12) + '@example.com'
            password = secrets.token_urlsafe(32)
            status, user = api.call('POST', '/auth/v1/admin/users',
                {'email':email, 'password':password, 'email_confirm':True,
                 'app_metadata':{'festival_radar_validation':nonce}}, admin=True)
            require(status in (200, 201) and user.get('id'), 'temporary_user_creation')
            users.append(user['id'])
            credentials.append((email, password))
            status, session = api.call('POST', '/auth/v1/token?grant_type=password',
                                      {'email':email, 'password':password})
            require(status == 200 and session.get('access_token'), 'password_signin')
            tokens.append(session['access_token'])
        checks.append('admin_creation_without_email_and_password_signin')
        uid, other = users
        token, other_token = tokens
        fid = json.loads((ROOT/'data/festivals.json').read_text())['events'][0]['id']
        status, _ = api.call('POST', '/rest/v1/favorites',
                            {'user_id':uid, 'festival_id':fid}, token=token)
        require(status == 201, 'favorite_insert')
        for candidate_token, expected in ((token, 1), (other_token, 0), (None, 0)):
            status, rows = api.call('GET', '/rest/v1/favorites?select=festival_id&user_id=eq.'+uid,
                                   token=candidate_token)
            # Anonymous denial is also valid; authenticated cross-user reads must be empty.
            if candidate_token is None and status in (401, 403):
                continue
            require(status == 200 and len(rows) == expected, 'favorite_rls_isolation')
        checks.append('favorite_insert_read_and_cross_user_isolation')
        status, _ = api.call('POST', '/rest/v1/favorites',
                            {'user_id':other, 'festival_id':fid}, token=token)
        require(status in (401, 403), 'cross_user_favorite_insert_denied')
        status, _ = api.call('DELETE', '/rest/v1/favorites?user_id=eq.'+uid, token=other_token)
        require(status in (200, 204), 'cross_user_favorite_delete_request')
        status, rows = api.call('GET', '/rest/v1/favorites?select=festival_id&user_id=eq.'+uid, token=token)
        require(status == 200 and len(rows) == 1, 'cross_user_favorite_delete_denied')
        checks.append('cross_user_favorite_writes_denied')
        pref = {'user_id':uid, 'countries':['FR'], 'genres':['Techno'], 'email_enabled':False}
        status, _ = api.call('POST', '/rest/v1/alert_preferences?on_conflict=user_id',
                            pref, token=token, prefer='resolution=merge-duplicates,return=minimal')
        require(status in (200, 201, 204), 'preference_save')
        pref.update(countries=['BE'], genres=[])
        status, _ = api.call('POST', '/rest/v1/alert_preferences?on_conflict=user_id',
                            pref, token=token, prefer='resolution=merge-duplicates,return=minimal')
        require(status in (200, 201, 204), 'preference_update')
        status, rows = api.call('GET', '/rest/v1/alert_preferences?select=countries,genres,email_enabled&user_id=eq.'+uid, token=token)
        require(status == 200 and len(rows) == 1 and rows[0]['countries'] == ['BE']
                and rows[0]['email_enabled'] is False, 'preference_roundtrip')
        status, rows = api.call('GET', '/rest/v1/alert_preferences?select=countries&user_id=eq.'+uid, token=other_token)
        require(status == 200 and rows == [], 'preference_cross_user_isolation')
        checks.append('preference_upsert_read_and_cross_user_isolation_email_off')
        status, rows = api.call('GET', '/rest/v1/alert_deliveries?select=id,event_key,status,created_at,alert_events(event_type,payload,detected_at)&user_id=eq.'+uid, token=token)
        require(status == 200 and rows == [], 'inbox_join_empty_for_new_account')
        checks.append('inbox_relation_and_empty_state')
        status, rows = api.call('GET', '/rest/v1/subscriptions?select=plan,status,current_period_end&user_id=eq.'+uid, token=token)
        require(status == 200 and rows == [], 'premium_read')
        status, _ = api.call('POST', '/rest/v1/subscriptions',
            {'user_id':uid, 'plan':'free', 'status':'inactive',
             'provider_customer_id':'validation-'+nonce}, admin=True)
        require(status == 201, 'server_free_fixture')
        status, rows = api.call('GET', '/rest/v1/subscriptions?select=plan,status,current_period_end&user_id=eq.'+uid, token=token)
        require(status == 200 and len(rows) == 1 and rows[0]['plan'] == 'free', 'subscription_own_read')
        status, rows = api.call('GET', '/rest/v1/subscriptions?select=plan,status&user_id=eq.'+uid, token=other_token)
        require(status == 200 and rows == [], 'subscription_cross_user_read_denied')
        status, _ = api.call('GET', '/rest/v1/subscriptions?select=provider_customer_id&user_id=eq.'+uid, token=token)
        require(status in (401, 403), 'provider_identifier_hidden')
        status, _ = api.call('PATCH', '/rest/v1/subscriptions?user_id=eq.'+uid,
            {'plan':'premium', 'status':'active', 'current_period_end':'2099-01-01T00:00:00Z'}, token=token)
        require(status in (401, 403), 'client_cannot_grant_premium')
        checks.append('premium_rls_provider_fields_hidden_and_client_upgrade_denied')
        status, _ = api.call('DELETE', '/rest/v1/favorites?user_id=eq.'+uid+'&festival_id=eq.'+urllib.parse.quote(fid, safe=''), token=token)
        require(status in (200, 204), 'unfollow')
        status, rows = api.call('GET', '/rest/v1/favorites?select=festival_id&user_id=eq.'+uid, token=token)
        require(status == 200 and rows == [], 'unfollow_roundtrip')
        checks.append('unfollow_roundtrip')
        if browser:
            browser_journey(*credentials[0])
            checks.append('browser_signin_preferences_follow_persistence_inbox_premium_and_signout')
        status, _ = api.call('POST', '/auth/v1/logout?scope=local', token=token)
        require(status in (200, 204), 'signout')
        checks.append('signout')
        return checks
    finally:
        failed_cleanup = False
        for uid in users:
            cleaned = False
            for _ in range(3):
                try:
                    status, _ = api.call('DELETE', '/auth/v1/admin/users/'+uid, admin=True)
                    if status in (200, 204, 404):
                        cleaned = True
                        break
                except RuntimeError:
                    continue
            if not cleaned:
                failed_cleanup = True
        if failed_cleanup:
            raise RuntimeError('temporary_user_cleanup_failed')
        checks.append('temporary_accounts_and_free_fixtures_cleaned_up')
        print('Temporary accounts and inactive Free fixtures cleaned up; no alert, paid subscription or email created.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    source = (ROOT/'index.html').read_text()
    match = re.search(r'createClient\("(https://[^\"]+)","([^\"]+)"\)', source)
    if not match:
        raise SystemExit('Public Supabase configuration not found')
    configured_base, public_key = match.groups()
    base = os.environ.get('SUPABASE_URL', configured_base).rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    require(base == configured_base and key, 'configured_project_or_server_secret_missing')
    report = {'passed':False, 'email_sending':False, 'billing':False, 'checks':[]}
    try:
        run(Api(base, public_key, key), browser=args.browser, checks=report['checks'])
        report['passed'] = True
    except RuntimeError as exc:
        report['failure'] = str(exc)
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
