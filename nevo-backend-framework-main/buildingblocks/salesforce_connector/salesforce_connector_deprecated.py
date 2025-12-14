from salesforce_api import Salesforce
from dotenv import load_dotenv
import os
import logging

class SalesforceConnector:
    def __init__(self, table_name: str):
        load_dotenv()

        self.client = Salesforce(
            username=os.getenv("SALESFORCE_SANDBOX_USERNAME"),
            password=os.getenv("SALESFORCE_SANDBOX_PASSWORD"),
            security_token=os.getenv("SALESFORCE_SANDBOX_TOKEN"),
            is_sandbox=True,
        )

        self.table_name = table_name

    def get_client(self):
        return self.client
    
    def run_general_query(self, query):
        """
        Run a SOQL query against Salesforce and return the results.
        """
        try:
            result = self.client.sobjects.query(query)
            return result
        except Exception as e:
            logging.error(f"Error running query: {e}")
            return None

    def get_user_details(self, user_email: str, test_fields: list[str]) -> dict[str, str]:
        """
        Get user details from Salesforce using the user's email.
        """
        fields = ', '.join(test_fields)
        query = f"SELECT {fields} FROM {self.table_name} WHERE email__c = '{user_email}'"
        result = self.run_general_query(query)
        if result:
            return result
        else:
            logging.error("No records found or error in query execution.")
            return [{"warning": "No records found"}]
    
    def write_user_details(self, new_record: dict[str, str]) -> dict[str, str]:
        """
        Write data that's been captured from a user into Salesforce, writing only to existing fields
        """

        try:
            result = getattr(self.client.sobjects, self.table_name).insert(new_record)
        except Exception as e:
            logging.error(f"Error writing user details: {e}")
            return {'success': False, 'errors': [str(e)]}   

        insert_result = result[0] if isinstance(result, list) else result

        return {
            'success': insert_result.get('success', False),
            'id': insert_result.get('id'),
            'errors': insert_result.get('errors', [])
        }
    
    def delete_record(self, record_id: str) -> dict:
        """Delete a Salesforce record and return a consistent result structure."""
        try:
            # Perform the delete
            getattr(self.client.sobjects, self.table_name).delete(record_id)
            return {
                'success': True,
                'id': record_id,
                'errors': []
            }
        except Exception as e:
            # Try to extract error details if available
            errors = []
            try:
                errors = e.content.get('errors', [{'message': str(e)}])
            except AttributeError:
                errors = [{'message': str(e)}]
            
            return {
                'success': False,
                'id': record_id,
                'errors': errors
            }
        
if __name__ == "__main__":
    # Example usage
    connector = SalesforceConnector()
    user_email = "example@example.com"
    user_details = connector.get_user_details(user_email)
    print(user_details)
        