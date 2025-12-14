from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from salesforce_api import Salesforce


class SalesforceConnector:
    """
    Generic helper around simple REST calls made with salesforce-api.
    By default the custom object that will be created/read/deleted is
    passed in through `table_name` (for example: 'Sales_Agent_Record__c').
    """

    CONTACT_OBJECT = "Contact"              # standard object
    CONTACT_LOOKUP_FIELD = "Contact__c"     # lookup field that exists on your custom object

    def __init__(self, table_name: str = "SalesAgentRecord__c") -> None:
        load_dotenv()

        self.client = Salesforce(
            username=os.getenv("SALESFORCE_SANDBOX_USERNAME"),
            password=os.getenv("SALESFORCE_SANDBOX_PASSWORD"),
            security_token=os.getenv("SALESFORCE_SANDBOX_TOKEN"),
            is_sandbox=True,
        )
        self.table_name: str = table_name

    # --------------------------------------------------------------------- #
    #  Generic helpers                                                      #
    # --------------------------------------------------------------------- #

    def _run_soql(self, query: str) -> List[Dict[str, Any]]:
        """
        Internal helper that executes SOQL and always returns a list.
        """
        try:
            result = self.client.sobjects.query(query)
            return result or []
        except Exception as exc:
            logging.error("SOQL error: %s", exc)
            return []

    # --------------------------------------------------------------------- #
    #  Contact helpers                                                      #
    # --------------------------------------------------------------------- #

    def _find_contact_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Return the most recently-created Contact that has the supplied e-mail.
        """
        email = email.replace("'", r"\'")  # quick SQL-injection guard
        soql = (
            f"SELECT Id, FirstName, LastName, Email, CreatedDate "
            f"FROM {self.CONTACT_OBJECT} "
            f"WHERE Email = '{email}' "
            f"ORDER BY CreatedDate DESC LIMIT 1"
        )
        rows = self._run_soql(soql)
        return rows[0] if rows else None

    def _get_or_create_contact(self, contact_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure a Contact exists. Return its Id and an indicator whether it was created.
        Expected keys in contact_fields: 'FirstName', 'LastName', 'Email' (others allowed).
        """
        email = contact_fields.get("Email")
        if not email:
            raise ValueError("contact_fields must include an 'Email' key")

        existing = self._find_contact_by_email(email)
        if existing:
            return {"id": existing["Id"], "was_created": False}

        # Create a new Contact
        try:
            res = getattr(self.client.sobjects, self.CONTACT_OBJECT).insert(contact_fields)
            res = res[0] if isinstance(res, list) else res
            if not res.get("success"):
                raise Exception(res.get("errors", "Unknown errors while creating Contact"))
            return {"id": res["id"], "was_created": True}
        except Exception as exc:
            logging.error("Unable to create Contact: %s", exc)
            raise


    def get_user_details(
        self, user_email: str, sales_agent_fields: List[str] | None = None
    ) -> Dict[str, Any]:
        """
        1) Locate Contact by e-mail.
        2) Retrieve latest Sales_Agent_Record__c linked via Contact__c lookup.
        """
        contact = self._find_contact_by_email(user_email)
        if not contact:
            return {
                "success": False,
                "warning": f"No Contact found with email {user_email}",
                "contact": None,
                "agent_record": None,
            }

        # Build SOQL for Sales_Agent_Record__c
        fields = ", ".join(sales_agent_fields) if sales_agent_fields else "Id, CreatedDate"
        soql = (
            f"SELECT {fields} "
            f"FROM {self.table_name} "
            f"WHERE {self.CONTACT_LOOKUP_FIELD} = '{contact['Id']}' "
            f"ORDER BY CreatedDate DESC LIMIT 1"
        )
        agent_rows = self._run_soql(soql)
        latest_record = agent_rows[0] if agent_rows else None

        return {
            "success": True,
            "contact": contact,
            "agent_record": latest_record,
        }

    def write_user_details(
        self,
        contact_fields: Dict[str, Any],
        agent_record_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Upsert pattern:
        • Make sure Contact exists (create if not).
        • Insert a new Sales_Agent_Record__c that links to that Contact.

        Returns a consistent result dict.
        """
        try:
            # 1. Ensure / create Contact
            if not contact_fields.get("LastName", False):
                contact_fields["LastName"] = "Unknown"
            contact_info = self._get_or_create_contact(contact_fields)
            contact_id = contact_info["id"]

            # 2. Insert Sales_Agent_Record__c
            record_to_insert = {**agent_record_fields, self.CONTACT_LOOKUP_FIELD: contact_id}
            insert_res = getattr(self.client.sobjects, self.table_name).insert(record_to_insert)
            insert_res = insert_res[0] if isinstance(insert_res, list) else insert_res

            success_flag = insert_res.get("success", False)
            errors = insert_res.get("errors", [])

            return {
                "success": success_flag,
                "contact_id": contact_id,
                "contact_was_created": contact_info["was_created"],
                "agent_record_id": insert_res.get("id"),
                "errors": errors,
            }

        except Exception as exc:
            logging.error("Error during write_user_details: %s", exc, exc_info=True)
            return {"success": False, "errors": [str(exc)]}

    # --------------------------------------------------------------------- #
    #  Delete                                                               #
    # --------------------------------------------------------------------- #

    def delete_record(self, record_id: str) -> Dict[str, Any]:
        """
        Delete *only* a Sales_Agent_Record__c (custom object) entry.
        Does not delete related Contact.
        """
        try:
            getattr(self.client.sobjects, self.table_name).delete(record_id)
            return {"success": True, "id": record_id, "errors": []}
        except Exception as exc:
            errors = []
            try:
                errors = exc.content.get("errors", [{"message": str(exc)}])
            except AttributeError:
                errors = [{"message": str(exc)}]
            return {"success": False, "id": record_id, "errors": errors}


# ------------------------------------------------------------------------- #
#  Example usage                                                            #
# ------------------------------------------------------------------------- #
if __name__ == "__main__":
    connector = SalesforceConnector("SalesAgentRecord__c")

    # ------------------------  READ  ------------------------------------ #
    email_to_lookup = "john@email.com"
    resp = connector.get_user_details(email_to_lookup, sales_agent_fields=[
                        "name__c",
                        "email__c",
                        "phone_number__c",
                        "car_model__c",
                        "preferred_date__c",
                        "preferred_time__c",
                        "zip_code__c",
                        "user_profile__c",
                    ])
    print("Lookup response:\n", resp)

    # ------------------------  WRITE  ----------------------------------- #
    contact_payload = {
        "FirstName": "Ada",
        "LastName": "Lovelace",
        "Email": "ada.lovelace@example.com",
    }

    agent_record_payload = {
        "preferred_date__c": "24-05-2025",
        "preferred_time__c": "10h00",
        "conversation_summary__c": "Test summary",
    }

    write_resp = connector.write_user_details(contact_payload, agent_record_payload)
    print("Write response:\n", write_resp)

    # if write_resp.get("success") and write_resp.get("agent_record_id"):
    #     delete_resp = connector.delete_record(write_resp["agent_record_id"])
    #     print("Delete response:\n", delete_resp)
    # else:
    #     print("No record to delete.")