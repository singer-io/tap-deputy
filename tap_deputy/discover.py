from singer.catalog import Catalog, CatalogEntry, Schema

"""
To specify the replication method, use the key replication-method, and for the replication key, 
use replication-key
in the RESOURCES. 
Example :  {'stream_name': 'addresses', 'replication-method', 'INCREMENTAL', 'replication-keys', 'Modified'}
"""
RESOURCES = {
    'Address': {'stream_name': 'addresses'},
    'Category': {'stream_name': 'categories'},
    'Comment': {'stream_name': 'comments'},
    'Company': {'stream_name': 'companies'},
    'CompanyPeriod': {'stream_name': 'company_periods'},
    'Contact': {'stream_name': 'contacts'},
    'Country': {'stream_name': 'countries'},
    'CustomAppData': {'stream_name': 'custom_app_data'},
    'CustomField': {'stream_name': 'custom_fields'},
    'CustomFieldData': {'stream_name': 'custom_field_data'},
    'Employee': {'stream_name': 'employees'},
    'EmployeeAgreement': {'stream_name': 'employee_agreements'},
    'EmployeeAgreementHistory': {'stream_name': 'employee_agreement_history'},
    'EmployeeAppraisal': {'stream_name': 'employee_appraisal'},
    'EmployeeAvailability': {'stream_name': 'employee_availability'},
    'EmployeeHistory': {'stream_name': 'employee_history'},
    'EmployeePaycycle': {'stream_name': 'employee_paycycles'},
    'EmployeePaycycleReturn': {'stream_name': 'employee_paycycle_returns'},
    'EmployeeRole': {'stream_name': 'employee_roles'},
    'EmployeeSalaryOpunitCosting': {'stream_name': 'employee_salary_opunit_costing'},
    'EmployeeWorkplace': {'stream_name': 'employee_workplaces'},
    'EmploymentCondition': {'stream_name': 'employment_conditions'},
    'EmploymentContract': {'stream_name': 'employee_contracts'},
    'EmploymentContractLeaveRules': {'stream_name': 'employee_contract_leave_rules'},
    'Event': {'stream_name': 'events'},
    'Geo': {'stream_name': 'geo'},
    'Journal': {'stream_name': 'journal'},
    'Kiosk': {'stream_name': 'kiosks'},
    'Leave': {'stream_name': 'leaves'},
    'LeaveAccrual': {'stream_name': 'leave_accruals'},
    'LeavePayLine': {'stream_name': 'leave_pay_lines'},
    'LeaveRules': {'stream_name': 'leave_rules'},
    'Memo': {'stream_name': 'memos'},
    'OperationalUnit': {'stream_name': 'operational_units'},
    'PayPeriod': {'stream_name': 'pay_periods'},
    'PayRules': {'stream_name': 'pay_rules'},
    'PublicHoliday': {'stream_name': 'public_holidays'},
    'Roster': {'stream_name': 'rosters'},
    'RosterOpen': {'stream_name': 'roster_opens'},
    'RosterSwap': {'stream_name': 'roster_swaps'},
    'SalesData': {'stream_name': 'sales_data'},
    'Schedule': {'stream_name': 'schedules'},
    'SmsLog': {'stream_name': 'sms_logs'},
    'State': {'stream_name': 'states'},
    'StressProfile': {'stream_name': 'stress_profiles'},
    'SystemUsageBalance': {'stream_name': 'system_usage_balances'},
    'SystemUsageTracking': {'stream_name': 'system_usage_tracking'},
    'Task': {'stream_name': 'tasks'},
    'TaskGroup': {'stream_name': 'task_groups'},
    'TaskGroupSetup': {'stream_name': 'task_group_setups'},
    'TaskOpunitConfig': {'stream_name': 'task_opunit_configs'},
    'TaskSetup': {'stream_name': 'task_setups'},
    'Team': {'stream_name': 'teams'},
    'Timesheet': {'stream_name': 'timesheets'},
    'TimesheetPayReturn': {'stream_name': 'timesheet_pay_returns'},
    'TrainingModule': {'stream_name': 'training_modules'},
    'TrainingRecord': {'stream_name': 'training_records'},
    'Webhook': {'stream_name': 'webhooks'}
}

TYPE_MAP = {
    'Integer': 'integer',
    'Float': 'number',
    'VarChar': 'string',
    'Blob': 'string',
    'Bit': 'boolean',
    'Time': 'string'
}

def get_schema(client, resource_name, resource_data):
    data = client.get(
        '/api/v1/resource/{}/INFO'.format(resource_name),
        endpoint='resource_info')

    properties = {}
    metadata = [
        {
            'breadcrumb': [],
            'metadata': {
                'tap-deputy.resource': resource_name,
                'forced-replication-method' : resource_data.get('replication-method', 'INCREMENTAL'),
                'valid-replication-keys' : resource_data.get('replication-keys', 'Modified'),
            }
        }
    ]

    for field_name, field_type in data['fields'].items():
        # Skipping all fields of type Json until we decide on how to handle "[]" as null response
        # Json data fields
        if field_type == "Json":
            continue
        if field_type in ['Date', 'DateTime']:
            json_schema = {
                'type': ['null', 'string'],
                'format': 'date-time'
            }
        else:
            json_schema = {
                'type': ['null', TYPE_MAP[field_type]]
            }

        properties[field_name] = json_schema

        metadata.append({
            'breadcrumb': ['properties', field_name],
            'metadata': {
                'inclusion': 'automatic' if field_name == 'Id' else 'available'
            }
        })

    schema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': properties
    }

    return schema, metadata

def discover(client):
    catalog = Catalog([])

    for resource_name, resource_meta_data in RESOURCES.items():
        schema_dict, metadata = get_schema(client, resource_name, resource_meta_data)
        schema = Schema.from_dict(schema_dict)

        stream_name = RESOURCES[resource_name]

        catalog.streams.append(CatalogEntry(
            stream=stream_name,
            tap_stream_id=stream_name,
            key_properties=['Id'],
            schema=schema,
            metadata=metadata
        ))

    return catalog
