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
from tap_tester import runner


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
        # _refresh_tokens_from_config updates env vars from the config file
        # written by the tap during a previous run, ensuring rotated tokens
        # survive across separate tap-tester process invocations.
        DeputyBase._refresh_tokens_from_config()
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
    def _load_env_script():
        """
        Parse /tmp/tap_deputy_env.sh (written by tearDownClass) and load any
        'export KEY="VALUE"' lines into the current process environment.
        Called at the very start of setUpClass so every test class begins with
        the most recently rotated tokens.
        """
        env_script = '/tmp/tap_deputy_env.sh'
        if not os.path.exists(env_script):
            return
        with open(env_script, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('export '):
                    continue
                # strip leading 'export '
                assignment = line[len('export '):]
                if '=' not in assignment:
                    continue
                key, _, value = assignment.partition('=')
                # strip surrounding quotes
                value = value.strip('"\'')
                os.environ[key] = value
                LOGGER.info("_load_env_script: loaded %s from %s", key, env_script)

    @staticmethod
    def _refresh_tokens_from_config():
        """
        Read rotated tokens the tap wrote back to /tmp/tap_tester_config.json
        and propagate them into the process environment variables so every
        subsequent get_credentials() / ensure_connection() call uses the
        latest tokens automatically.
        Returns the rotated dict (empty dict if file absent).
        """
        TAP_CONFIG_PATH = '/tmp/tap_tester_config.json'
        if not os.path.exists(TAP_CONFIG_PATH):
            return {}
        with open(TAP_CONFIG_PATH, 'r') as f:
            rotated = json.load(f)
        if rotated.get('refresh_token'):
            os.environ['TAP_DEPUTY_REFRESH_TOKEN'] = rotated['refresh_token']
            LOGGER.info("_refresh_tokens_from_config: updated TAP_DEPUTY_REFRESH_TOKEN")
        if rotated.get('access_token'):
            os.environ['TAP_DEPUTY_ACCESS_TOKEN'] = rotated['access_token']
            LOGGER.info("_refresh_tokens_from_config: updated TAP_DEPUTY_ACCESS_TOKEN")
        return rotated

    def run_sync_mode(self, conn_id):
        """
        Before syncing, refresh the connection's stored credentials with any
        tokens rotated by the tap during the preceding check/discovery run.
        Without this, run_sync_mode would overwrite the config file with the
        stale snapshot taken at ensure_connection time, causing a 400 on the
        next token-refresh attempt.
        """
        rotated = self._refresh_tokens_from_config()
        conn = runner.BACKEND.connections.get(conn_id)
        if conn and rotated:
            for key in ('refresh_token', 'access_token', 'expires_at'):
                if rotated.get(key):
                    conn['credentials'][key] = rotated[key]
            LOGGER.info("run_sync_mode: patched connection %s with rotated tokens", conn_id)
        return super().run_sync_mode(conn_id)

    # ------------------------------------------------------------------
    # Environment guard
    # ------------------------------------------------------------------

    @classmethod
    def setUpClass(cls, logging="Ensuring environment variables are sourced."):  # pylint: disable=invalid-name
        DeputyBase._load_env_script()
        super().setUpClass(logging=logging)
        missing_envs = [v for v in _REQUIRED_ENV_VARS if os.getenv(v) is None]
        if missing_envs:
            raise ValueError(f"Missing environment variables: {missing_envs}")

    @classmethod
    def tearDownClass(cls):  # pylint: disable=invalid-name
        """
        After all test methods in the class finish, write the latest rotated
        tokens to /tmp/tap_deputy_env.sh so the caller can source it to update
        their shell session:

            source /tmp/tap_deputy_env.sh
        """
        DeputyBase._refresh_tokens_from_config()
        env_script = '/tmp/tap_deputy_env.sh'
        lines = [
            '#!/usr/bin/env bash',
            '# Auto-generated by DeputyBase.tearDownClass — do not edit manually.',
        ]
        for var in ('TAP_DEPUTY_REFRESH_TOKEN', 'TAP_DEPUTY_ACCESS_TOKEN'):
            val = os.getenv(var, '')
            if val:
                lines.append(f'export {var}="{val}"')
        with open(env_script, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        LOGGER.info("tearDownClass: rotated tokens written to %s — run: source %s", env_script, env_script)
        super().tearDownClass()

    def tearDown(self, *args, logging="Propagating rotated tokens to env vars.", **kwargs):  # pylint: disable=invalid-name
        """
        After each test method, propagate any rotated tokens the tap wrote back
        to the config file into env vars so the next ensure_connection /
        get_credentials call picks them up automatically.
        """
        self._refresh_tokens_from_config()
        super().tearDown(*args, logging=logging, **kwargs)

