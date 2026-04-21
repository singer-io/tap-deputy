"""
Base class for tap-deputy integration tests.

Centralises tap connection config and stream expectations so individual test
classes stay DRY and comparable across the suite.

Authentication notes
--------------------
A fresh ``access_token`` is obtained at test-class setup time by exchanging the
``refresh_token`` via Deputy's OAuth endpoint.

The following environment variables must be set before running any test:

    TAP_DEPUTY_DOMAIN          – company subdomain, e.g. mycompany.ent-na.deputy.com
    TAP_DEPUTY_CLIENT_ID       – OAuth application client ID
    TAP_DEPUTY_CLIENT_SECRET   – OAuth application client secret
    TAP_DEPUTY_REDIRECT_URI    – registered redirect URI for the OAuth app
    TAP_DEPUTY_REFRESH_TOKEN   – long-lived refresh token
"""
import json
import os

from tap_tester.base_suite_tests.base_case import BaseCase
from tap_tester.logger import LOGGER
from tap_tester import runner, connections


# ---------------------------------------------------------------------------
# All Deputy API resource → stream-name mappings (mirrors tap_deputy/discover.py)
# ---------------------------------------------------------------------------
RESOURCES = {
    'Address': 'addresses',
    'Category': 'categories',
    'Comment': 'comments',
    'Company': 'companies',
    'CompanyPeriod': 'company_periods',
    'Contact': 'contacts',
    'Country': 'countries',
    'CustomAppData': 'custom_app_data',
    'CustomField': 'custom_fields',
    'CustomFieldData': 'custom_field_data',
    'Employee': 'employees',
    'EmployeeAgreement': 'employee_agreements',
    'EmployeeAgreementHistory': 'employee_agreement_history',
    'EmployeeAppraisal': 'employee_appraisal',
    'EmployeeAvailability': 'employee_availability',
    'EmployeeHistory': 'employee_history',
    'EmployeePaycycle': 'employee_paycycles',
    'EmployeePaycycleReturn': 'employee_paycycle_returns',
    'EmployeeRole': 'employee_roles',
    'EmployeeSalaryOpunitCosting': 'employee_salary_opunit_costing',
    'EmployeeWorkplace': 'employee_workplaces',
    'EmploymentCondition': 'employment_conditions',
    'EmploymentContract': 'employee_contracts',
    'EmploymentContractLeaveRules': 'employee_contract_leave_rules',
    'Event': 'events',
    'Geo': 'geo',
    'Journal': 'journal',
    'Kiosk': 'kiosks',
    'Leave': 'leaves',
    'LeaveAccrual': 'leave_accruals',
    'LeavePayLine': 'leave_pay_lines',
    'LeaveRules': 'leave_rules',
    'Memo': 'memos',
    'OperationalUnit': 'operational_units',
    'PayPeriod': 'pay_periods',
    'PayRules': 'pay_rules',
    'PublicHoliday': 'public_holidays',
    'Roster': 'rosters',
    'RosterOpen': 'roster_opens',
    'RosterSwap': 'roster_swaps',
    'SalesData': 'sales_data',
    'Schedule': 'schedules',
    'SmsLog': 'sms_logs',
    'State': 'states',
    'StressProfile': 'stress_profiles',
    'SystemUsageBalance': 'system_usage_balances',
    'SystemUsageTracking': 'system_usage_tracking',
    'Task': 'tasks',
    'TaskGroup': 'task_groups',
    'TaskGroupSetup': 'task_group_setups',
    'TaskOpunitConfig': 'task_opunit_configs',
    'TaskSetup': 'task_setups',
    'Team': 'teams',
    'Timesheet': 'timesheets',
    'TimesheetPayReturn': 'timesheet_pay_returns',
    'TrainingModule': 'training_modules',
    'TrainingRecord': 'training_records',
    'Webhook': 'webhooks',
}

ALL_STREAM_NAMES = set(RESOURCES.values())

_REQUIRED_ENV_VARS = [
    'TAP_DEPUTY_DOMAIN',
    'TAP_DEPUTY_CLIENT_ID',
    'TAP_DEPUTY_CLIENT_SECRET',
    'TAP_DEPUTY_REDIRECT_URI',
    'TAP_DEPUTY_REFRESH_TOKEN',
    'TAP_DEPUTY_ACCESS_TOKEN',  # used by the tap in --dev mode
]


class DeputyBase(BaseCase):
    """
    Single source of truth for tap identity, credentials, and stream contracts.
    Keeping these here means a schema change only needs to be fixed in one place.
    """

    # Default start date; individual tests may override via self.start_date.
    start_date = '2020-01-01T00:00:00Z'

    @staticmethod
    def tap_name():
        return "tap-deputy"

    @staticmethod
    def get_type():
        return "platform.deputy"

    def get_properties(self):
        return {
            'start_date': self.start_date,
            'domain': os.getenv('TAP_DEPUTY_DOMAIN'),
        }

    @staticmethod
    def get_credentials():
        return {
            'client_id': os.getenv('TAP_DEPUTY_CLIENT_ID'),
            'client_secret': os.getenv('TAP_DEPUTY_CLIENT_SECRET'),
            'redirect_uri': os.getenv('TAP_DEPUTY_REDIRECT_URI'),
            'refresh_token': os.getenv('TAP_DEPUTY_REFRESH_TOKEN'),
            'access_token': os.getenv('TAP_DEPUTY_ACCESS_TOKEN'),
        }

    @staticmethod
    def expected_metadata():
        """
        All Deputy streams are INCREMENTAL, bookmarked on the ``Modified`` field.
        Every stream has a single primary key (``Id``).
        RESPECTS_START_DATE is True because the QUERY endpoint filters on
        ``Modified >= start_date``.
        """
        return {
            stream: {
                BaseCase.PRIMARY_KEYS: {'Id'},
                BaseCase.REPLICATION_METHOD: BaseCase.INCREMENTAL,
                BaseCase.REPLICATION_KEYS: {'Modified'},
                BaseCase.RESPECTS_START_DATE: True,
            }
            for stream in ALL_STREAM_NAMES
        }

    @staticmethod
    def _load_tokens_from_config():
        """
        Read /tmp/tap_tester_config.json (written by the tap subprocess on every
        run) and update env vars if it contains fresher tokens.  This is the
        cross-process persistence mechanism: when a new pytest invocation starts,
        the file still holds the tokens from the last tap run of the previous
        invocation.  No shell script needed.
        """
        TAP_CONFIG_PATH = '/tmp/tap_tester_config.json'
        if not os.path.exists(TAP_CONFIG_PATH):
            return
        try:
            with open(TAP_CONFIG_PATH, 'r') as f:
                saved = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        for key, env_var in (('refresh_token', 'TAP_DEPUTY_REFRESH_TOKEN'),
                             ('access_token', 'TAP_DEPUTY_ACCESS_TOKEN')):
            val = saved.get(key)
            if val:
                os.environ[env_var] = val
                LOGGER.info("_load_tokens_from_config: seeded %s from %s", env_var, TAP_CONFIG_PATH)

    @staticmethod
    def _sync_rotated_tokens_to_backend(conn_id):
        """
        After any tap subprocess exits it writes rotated OAuth tokens back to
        /tmp/tap_tester_config.json.  InMemoryBackend never reads that file
        again, so we do it here — once — and push the fresh tokens straight
        into the backend connection store and env vars.

        Doing it here (rather than in get_credentials / tearDown) means there
        is a single, explicit token-propagation point and no scattered file
        reads elsewhere.
        """
        TAP_CONFIG_PATH = '/tmp/tap_tester_config.json'
        if not os.path.exists(TAP_CONFIG_PATH):
            return
        with open(TAP_CONFIG_PATH, 'r') as f:
            rotated = json.load(f)
        conn = runner.BACKEND.connections.get(conn_id)
        if conn:
            for key in ('refresh_token', 'access_token', 'expires_at'):
                if rotated.get(key):
                    conn['credentials'][key] = rotated[key]
            LOGGER.info("_sync_rotated_tokens_to_backend: patched connection %s", conn_id)
        # Keep env vars in sync so get_credentials() is correct for the
        # very first ensure_connection call of the next test class.
        if rotated.get('refresh_token'):
            os.environ['TAP_DEPUTY_REFRESH_TOKEN'] = rotated['refresh_token']
        if rotated.get('access_token'):
            os.environ['TAP_DEPUTY_ACCESS_TOKEN'] = rotated['access_token']

    def run_sync_mode(self, conn_id):
        """
        Push tokens rotated by the preceding check/discover run into the backend
        BEFORE super() writes the config file so the sync tap never sees a stale token.
        After sync, push again for the next call in the chain.
        """
        self._sync_rotated_tokens_to_backend(conn_id)
        result = super().run_sync_mode(conn_id)
        self._sync_rotated_tokens_to_backend(conn_id)
        return result

    # ------------------------------------------------------------------
    # Token-chaining: preserve the live refresh_token across connection resets
    # ------------------------------------------------------------------
    # The base-suite tests (all_fields, bookmark, discovery, …) all call
    # connections.ensure_connection(self) directly — not self.ensure_connection()
    # — so an instance-method override is bypassed entirely.  Instead we
    # monkey-patch the module-level function in setUpClass and restore it in
    # tearDownClass so every call site automatically gets the hook.

    @staticmethod
    def _preserve_refresh_token_hook(existing_conns, payload):
        """
        payload_hook injected into every connections.ensure_connection call.

        Deputy tokens rotate on every use.  When tap-tester tears down and
        re-creates the connection it builds the payload from the env-var
        snapshot taken at class-setup time.  By the time a second test runs
        that snapshot is stale and Deputy rejects the token with 400
        invalid_grant.  This hook reads the *live* tokens from the existing
        connection's credentials and overwrites both payload locations:
          - payload['properties'] — used by StitchBackend (merges creds in)
          - payload['credentials'] — used by InMemoryBackend (keeps them separate)
        Both refresh_token and access_token are chained because both rotate
        and Deputy requires a valid access_token on tap startup.
        """
        if not existing_conns:
            return payload
        conn_with_creds = connections.fetch_existing_connection_with_creds(existing_conns[0]['id'])
        live_creds = conn_with_creds.get('credentials', {})
        for key in ('refresh_token', 'access_token'):
            live_val = live_creds.get(key)
            if not live_val:
                continue
            payload['properties'][key] = live_val
            if 'credentials' in payload:
                payload['credentials'][key] = live_val
        return payload

    # ------------------------------------------------------------------
    # Environment guard
    # ------------------------------------------------------------------

    @classmethod
    def setUpClass(cls, logging="Ensuring environment variables are sourced."):  # pylint: disable=invalid-name
        # Seed env vars from the config file left by a previous run's tap subprocess.
        # This is the cross-process persistence mechanism — no shell script needed.
        cls._load_tokens_from_config()
        super().setUpClass(logging=logging)
        missing_envs = [v for v in _REQUIRED_ENV_VARS if os.getenv(v) is None]
        if missing_envs:
            raise ValueError(f"Missing environment variables: {missing_envs}")
        # Patch the module-level ensure_connection so all base-suite call sites
        # automatically get the token-chaining hook without needing to be changed.
        cls._original_ensure_connection = connections.ensure_connection
        def _patched_ensure_connection(scenario, original_properties=True, original_credentials=True, payload_hook=None):
            effective_hook = payload_hook or DeputyBase._preserve_refresh_token_hook
            return cls._original_ensure_connection(
                scenario,
                original_properties=original_properties,
                original_credentials=original_credentials,
                payload_hook=effective_hook,
            )
        connections.ensure_connection = _patched_ensure_connection
        LOGGER.info("setUpClass: patched connections.ensure_connection with token-chaining hook")

        # Also patch runner.run_check_mode: every discover subprocess rotates tokens.
        # BaseCase.run_and_verify_check_mode calls runner.run_check_mode directly so
        # an instance-method override is bypassed, same as ensure_connection above.
        cls._original_run_check_mode = runner.run_check_mode
        def _patched_run_check_mode(scenario, conn_id):
            result = cls._original_run_check_mode(scenario, conn_id)
            DeputyBase._sync_rotated_tokens_to_backend(conn_id)
            return result
        runner.run_check_mode = _patched_run_check_mode
        LOGGER.info("setUpClass: patched runner.run_check_mode with token-sync hook")

    @classmethod
    def tearDownClass(cls):  # pylint: disable=invalid-name
        # Restore patched module-level functions so other tap test suites are unaffected.
        if hasattr(cls, '_original_ensure_connection'):
            connections.ensure_connection = cls._original_ensure_connection
            LOGGER.info("tearDownClass: restored original connections.ensure_connection")
        if hasattr(cls, '_original_run_check_mode'):
            runner.run_check_mode = cls._original_run_check_mode
            LOGGER.info("tearDownClass: restored original runner.run_check_mode")
        super().tearDownClass()

    def tearDown(self, *args, logging="Tokens kept in sync via run_check/sync_mode.", **kwargs):  # pylint: disable=invalid-name
        super().tearDown(*args, logging=logging, **kwargs)

