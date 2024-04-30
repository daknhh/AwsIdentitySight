# AWS Indentity Sight

This tools is designed to generate an HTML report of IAM Identity Center.

Currently we are just supporting account assignments. It retrieves information about account assignments from AWS Identity Center, including account IDs, account names, SSO instance names, object types (user or group), object names (usernames or group names), and permission sets assigned to each account. The report is saved as an HTML file for easy viewing.

|Releases |Author  | 
--- | --- |
| [Changelog](CHANGELOG.md) | David Krohn </br> [Linkedin](https://www.linkedin.com/in/daknhh/) - [Blog](https://globaldatanet.com/blog/author/david-krohn)|

## Prerequisites
Python 3.x installed on your system.
AWS CLI configured with necessary permissions to access AWS SSO and Identity Store services.

## Usage
1. Clone or download the script sso_account_assignments_html_report.py to your local machine.
2. Install the required Python libraries by running the following command:

```
pip install boto3
```

1. Open the script in a text editor and configure the AWS CLI credentials if they are not already configured on your system.
2. Run the script using the following command:

```
python sso_account_assignments_html_report.py
```

5. The script will generate an HTML report named sso_report_Account_Assignments_TIMESTAMP.html, where TIMESTAMP is the current date and time.

## Output

The generated HTML report contains a table with the following columns:

- AccountID: The AWS account ID.
- AccountName: The name of the AWS account.
- SSOInstanceName: The name of the AWS SSO instance.
- ObjectType: The type of object (USER or GROUP).
- ObjectName: The name of the user or group.
- PermissionSet: The permission set assigned to the user or group.
