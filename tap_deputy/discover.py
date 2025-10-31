from singer.catalog import Catalog, CatalogEntry, Schema

"""
To specify the replication method, use the key replication-method, and for the replication key, use replication-key
in the RESOURCES. 
"""
RESOURCES = {
    'Address': {"stream": 'addresses'},
    'Category': {"stream": 'categories'},
    'Comment': {"stream": 'comments'},
    'Company': {"stream": 'companies'},
    'CompanyPeriod': {"stream": 'company_periods'},
    'Contact': {"stream": 'contacts'},
    'Country': {"stream": 'countries'},
    'CustomAppData': {"stream": 'custom_app_data'},
    'CustomField': {"stream": 'custom_fields'},
    'CustomFieldData': {"stream": 'custom_field_data'},
    'Employee': {"stream": 'employees'},
    'EmployeeAgreement': {"stream": 'employee_agreements'},
    'EmployeeAgreementHistory': {"stream": 'employee_agreement_history'},
    'EmployeeAppraisal': {"stream": 'employee_appraisal'},
    'EmployeeAvailability': {"stream": 'employee_availability'},
    'EmployeeHistory': {"stream": 'employee_history'},
    'EmployeePaycycle': {"stream": 'employee_paycycles'},
    'EmployeePaycycleReturn': {"stream": 'employee_paycycle_returns'},
    'EmployeeRole': {"stream": 'employee_roles'},
    'EmployeeSalaryOpunitCosting': {"stream": 'employee_salary_opunit_costing'},
    'EmployeeWorkplace': {"stream": 'employee_workplaces'},
    'EmploymentCondition': {"stream": 'employment_conditions'},
    'EmploymentContract': {"stream": 'employee_contracts'},
    'EmploymentContractLeaveRules': {"stream": 'employee_contract_leave_rules'},
    'Event': {"stream": 'events'},
    'Geo': {"stream": 'geo'},
    'Journal': {"stream": 'journal'},
    'Kiosk': {"stream": 'kiosks'},
    'Leave': {"stream": 'leaves'},
    'LeaveAccrual': {"stream": 'leave_accruals'},
    'LeavePayLine': {"stream": 'leave_pay_lines'},
    'LeaveRules': {"stream": 'leave_rules'},
    'Memo': {"stream": 'memos'},
    'OperationalUnit': {"stream": 'operational_units'},
    'PayPeriod': {"stream": 'pay_periods'},
    'PayRules': {"stream": 'pay_rules'},
    'PublicHoliday': {"stream": 'public_holidays'},
    'Roster': {"stream": 'rosters'},
    'RosterOpen': {"stream": 'roster_opens'},
    'RosterSwap': {"stream": 'roster_swaps'},
    'SalesData': {"stream": 'sales_data'},
    'Schedule': {"stream": 'schedules'},
    'SmsLog': {"stream": 'sms_logs'},
    'State': {"stream": 'states'},
    'StressProfile': {"stream": 'stress_profiles'},
    'SystemUsageBalance': {"stream": 'system_usage_balances'},
    'SystemUsageTracking': {"stream": 'system_usage_tracking'},
    'Task': {"stream": 'tasks'},
    'TaskGroup': {"stream": 'task_groups'},
    'TaskGroupSetup': {"stream": 'task_group_setups'},
    'TaskOpunitConfig': {"stream": 'task_opunit_configs'},
    'TaskSetup': {"stream": 'task_setups'},
    'Team': {"stream": 'teams'},
    'Timesheet': {"stream": 'timesheets'},
    'TimesheetPayReturn': {"stream": 'timesheet_pay_returns'},
    'TrainingModule': {"stream": 'training_modules'},
    'TrainingRecord': {"stream": 'training_records'},
    'Webhook': {"stream": 'webhooks'}
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

    for resource_name, resource_data in RESOURCES.items():
        schema_dict, metadata = get_schema(client, resource_name, resource_data)
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
