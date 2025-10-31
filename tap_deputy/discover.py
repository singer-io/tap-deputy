from singer.catalog import Catalog, CatalogEntry, Schema

RESOURCES = {
    'Address': {"stream": 'addresses',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Category': {"stream": 'categories',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Comment': {"stream": 'comments',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Company': {"stream": 'companies',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'CompanyPeriod': {"stream": 'company_periods',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Contact': {"stream": 'contacts',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Country': {"stream": 'countries',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'CustomAppData': {"stream": 'custom_app_data',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'CustomField': {"stream": 'custom_fields',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'CustomFieldData': {"stream": 'custom_field_data',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Employee': {"stream": 'employees',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeAgreement': {"stream": 'employee_agreements',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeAgreementHistory': {"stream": 'employee_agreement_history',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeAppraisal': {"stream": 'employee_appraisal',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeAvailability': {"stream": 'employee_availability',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeHistory': {"stream": 'employee_history',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeePaycycle': {"stream": 'employee_paycycles',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeePaycycleReturn': {"stream": 'employee_paycycle_returns',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeRole': {"stream": 'employee_roles',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeSalaryOpunitCosting': {"stream": 'employee_salary_opunit_costing',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmployeeWorkplace': {"stream": 'employee_workplaces',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmploymentCondition': {"stream": 'employment_conditions',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmploymentContract': {"stream": 'employee_contracts',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'EmploymentContractLeaveRules': {"stream": 'employee_contract_leave_rules',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Event': {"stream": 'events',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Geo': {"stream": 'geo',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Journal': {"stream": 'journal',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Kiosk': {"stream": 'kiosks',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Leave': {"stream": 'leaves',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'LeaveAccrual': {"stream": 'leave_accruals',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'LeavePayLine': {"stream": 'leave_pay_lines',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'LeaveRules': {"stream": 'leave_rules',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Memo': {"stream": 'memos',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'OperationalUnit': {"stream": 'operational_units',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'PayPeriod': {"stream": 'pay_periods',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'PayRules': {"stream": 'pay_rules',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'PublicHoliday': {"stream": 'public_holidays',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Roster': {"stream": 'rosters',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'RosterOpen': {"stream": 'roster_opens',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'RosterSwap': {"stream": 'roster_swaps',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'SalesData': {"stream": 'sales_data',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Schedule': {"stream": 'schedules',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'SmsLog': {"stream": 'sms_logs',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'State': {"stream": 'states',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'StressProfile': {"stream": 'stress_profiles',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'SystemUsageBalance': {"stream": 'system_usage_balances',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'SystemUsageTracking': {"stream": 'system_usage_tracking',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Task': {"stream": 'tasks',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TaskGroup': {"stream": 'task_groups',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TaskGroupSetup': {"stream": 'task_group_setups',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TaskOpunitConfig': {"stream": 'task_opunit_configs',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TaskSetup': {"stream": 'task_setups',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Team': {"stream": 'teams',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Timesheet': {"stream": 'timesheets',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TimesheetPayReturn': {"stream": 'timesheet_pay_returns',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TrainingModule': {"stream": 'training_modules',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'TrainingRecord': {"stream": 'training_records',"forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]},
    'Webhook': {"stream": 'webhooks', "forced-replication-method":"INCREMENTAL", "valid-replication-keys": ["Modified"]}
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
                'forced-replication-method' : resource_data['forced-replication-method'],
                'valid-replication-keys' : resource_data['valid-replication-keys'],
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
