from dotenv import load_dotenv

load_dotenv()  # the order is important here: load_dotenv MUST be called before framework import

from nevo_framework.api import api as framework_api

if __name__ == "__main__":
    framework_api.main()
