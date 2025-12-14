import time

from salesforce_api import Salesforce
from dotenv import load_dotenv
import os
import logging

from buildingblocks.salesforce_connector.salesforce_connector_deprecated import SalesforceConnector
import argparse


def integration_test_salesforce_write_read_delete(table_name: str):
    # 1. Connect
    connector = SalesforceConnector(table_name=table_name)

    # 2. Prepare test data
    test_email = f'integ_test_{int(time.time())}@example.com'
    test_record = {
        'name__c': 'Integration Tester',
        'email__c': test_email,
        'phone_number__c': '555-555-1212',
        'car_model__c': 'Testla',
        'preferred_date__c': '2024-07-01',
        'preferred_time__c': '12:00',
        'zip_code__c': '12345',
        'user_profile__c': 'QA',
        'consent_given__c': 'true',
        'conversation_summary__c': 'Test summary',
    }

    # 3. Write
    write_result = connector.write_user_details(test_record)
    print("Write Result:", write_result)
    assert write_result['success'], f"Write failed: {write_result['errors']}"
    salesforce_id = write_result['id']
    assert salesforce_id

    # 4. Read back (verify)
    found = connector.get_user_details(test_email, test_fields=list(test_record.keys()))
    print("Read Result:", found)
    assert any(rec.get('Email__c', '').lower() == test_email.lower() or  # API field case
               rec.get('email__c', '').lower() == test_email.lower() or
               rec.get('email', '').lower() == test_email.lower() or
               rec.get('Email', '').lower() == test_email.lower()
               for rec in found), f"Test record not found for {test_email}"


    delete_result = connector.delete_record(salesforce_id)
    print("Delete Result:", delete_result)
    # (Depending on library, might just not fail if OK, or might return status)
    assert delete_result['id'] == salesforce_id and delete_result['success'], "Delete failed"

    print('\nIntegration test completed successfully!')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Salesforce integration test.")
    parser.add_argument("--table_name", type=str, default="SalesAgentRecord__c", help="Salesforce table name to use for the test.")
    args = parser.parse_args()

    table_name = args.table_name
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting integration test...")
    integration_test_salesforce_write_read_delete(table_name=table_name)
    logging.info("Integration test finished.")