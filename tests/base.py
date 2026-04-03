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
import os

from tap_tester.base_suite_tests.base_case import BaseCase
from test_client import DeputyTestClient


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
    def name():
        return "tap_tester_tap_deputy"

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
        token = DeputyTestClient.get_token_information()
        return {
            'client_id': token['client_id'],
            'client_secret': token['client_secret'],
            'redirect_uri': token['redirect_uri'],
            'refresh_token': token['refresh_token'],
            'access_token': token['access_token'],
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

    # ------------------------------------------------------------------
    # Environment guard
    # ------------------------------------------------------------------

    @classmethod
    def setUpClass(cls, logging="Ensuring environment variables are sourced."):  # pylint: disable=invalid-name
        super().setUpClass(logging=logging)
        missing_envs = [v for v in _REQUIRED_ENV_VARS if os.getenv(v) is None]
        if missing_envs:
            raise ValueError(f"Missing environment variables: {missing_envs}")

