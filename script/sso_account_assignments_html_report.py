from datetime import datetime
import boto3
import time
import logging

def list_active_accounts():
    """
    Retrieves a list of active AWS accounts.
    """
    account_list = []
    organizations_client = boto3.client('organizations')
    paginator = organizations_client.get_paginator('list_accounts')
    page_iterator = paginator.paginate()

    for page in page_iterator:
        for acct in page['Accounts']:
            if acct['Status'] == 'ACTIVE':
                account_list.append({'name': acct['Name'], 'id': acct['Id']})

    return account_list

def list_existing_sso_instances():
    """
    Lists existing AWS SSO instances.
    """
    client = boto3.client('sso-admin')

    sso_instance_list = []
    response = client.list_instances()
    for sso_instance in response['Instances']:
        sso_instance_list.append({'instanceArn': sso_instance["InstanceArn"], 'identityStore': sso_instance["IdentityStoreId"]})

    return sso_instance_list

def get_sso_instance_name(sso_instance_arn):
    """
    Retrieves the name of an AWS SSO instance.
    """
    try:
        client = boto3.client('sso-admin')
        response = client.describe_instance(InstanceArn=sso_instance_arn)
        if 'Name' in response:
            return response['Name']
        else:
            return response['IdentityStoreId']
    except Exception as e:
        logging.exception("An error occurred while retrieving the name of the AWS SSO instance: %s", str(e))
        return response['OwnerAccountId']

def list_permission_sets(sso_instance_arn):
    """
    Lists permission sets in an AWS SSO instance.
    """
    client = boto3.client('sso-admin')
    perm_set_dict = {}

    response = client.list_permission_sets(InstanceArn=sso_instance_arn)

    results = response["PermissionSets"]
    while "NextToken" in response:
        response = client.list_permission_sets(InstanceArn=sso_instance_arn, NextToken=response["NextToken"])
        results.extend(response["PermissionSets"])

    for permission_set in results:
        perm_description = client.describe_permission_set(InstanceArn=sso_instance_arn,PermissionSetArn=permission_set)
        perm_set_dict[perm_description["PermissionSet"]["Name"]] = permission_set

    return perm_set_dict

def list_account_assignments(sso_instance_arn, account_id, permission_set_arn):
    """
    Lists account assignments for a specific permission set in an AWS SSO instance.
    """
    client = boto3.client('sso-admin')
    paginator = client.get_paginator("list_account_assignments")

    response_iterator = paginator.paginate(
        InstanceArn=sso_instance_arn,
        AccountId=account_id,
        PermissionSetArn=permission_set_arn
    )

    account_assignments = []
    for response in response_iterator:
        for row in response['AccountAssignments']:
            account_assignments.append({'PrincipalType': row['PrincipalType'], 'PrincipalId': row['PrincipalId']})

    return account_assignments

def describe_principal(principal_id, principal_type, identity_store_id):
    """
    Describes the user or group based on the principal ID and type.
    """
    client = boto3.client('identitystore')
    if principal_type == "USER":
        response = client.describe_user(IdentityStoreId=identity_store_id, UserId=principal_id)
        return response['UserName']
    elif principal_type == "GROUP":
        try:
            response = client.describe_group(IdentityStoreId=identity_store_id, GroupId=principal_id)
            return response['DisplayName']
        except client.exceptions.ResourceNotFoundException:
            return "DELETED-GROUP"
        except Exception as e:
            logging.exception("An error occurred while describing group: %s", str(e))
            return "ERROR"

def create_report(account_list, sso_instance, permission_sets_list, break_after=None):
    print("🔎 Gathering Data for Accounts:")
    """
    Creates a report of account assignments.
    """
    result = []
    total_accounts = len(account_list)

    for i, account in enumerate(account_list, start=1):
        for permission_set, permission_set_arn in permission_sets_list.items():
            account_assignments = list_account_assignments(sso_instance['instanceArn'], account['id'], permission_set_arn)

            for account_assignment in account_assignments:
                account_assignments_dict = {
                    'AccountID': account['id'],
                    'AccountName': account['name'],
                    'PermissionSet': permission_set,
                    'ObjectType': account_assignment['PrincipalType']
                }

                object_name = describe_principal(account_assignment['PrincipalId'], account_assignment['PrincipalType'], sso_instance['identityStore'])
                account_assignments_dict['ObjectName'] = object_name

                result.append(account_assignments_dict)

        print(f"✅ {i}/{total_accounts} Done")
        if break_after is not None and i >= break_after:
            break

    return result


def write_result_to_html(result, sso_instance_name):
    """
    Writes the report results to an HTML file.
    """

    
    awsaccount_icon = """
    <svg class="w-6 h-6" height="48" width="48" xmlns="http://www.w3.org/2000/svg"><path d="M35.642 43.223v-8.568l7.427-4.215v8.482l-7.427 4.3zm-9.41-12.773l7.41 4.205v8.436l-7.325-4.277-.085-8.364zM42.08 28.7l-7.438 4.223-7.295-4.14 7.455-4.323 7.278 4.24zm-7.276-6.552L24.21 28.29l.12 11.678 10.418 6.085 10.322-5.978v-11.95l-10.265-5.977zM12.955 10.737A6.744 6.744 0 0119.691 4c3.713 0 6.734 3.022 6.734 6.737a6.742 6.742 0 01-6.734 6.736 6.743 6.743 0 01-6.736-6.736zm2.697 7.739a8.686 8.686 0 008.172-.046c1.323.383 2.591.95 3.771 1.694a15.48 15.48 0 012.997 2.468l1.453-1.373a17.437 17.437 0 00-3.383-2.786 16.808 16.808 0 00-2.883-1.443 8.707 8.707 0 002.646-6.253C28.425 5.919 24.507 2 19.691 2c-4.818 0-8.736 3.919-8.736 8.737 0 2.488 1.05 4.73 2.724 6.322C7.231 19.695 3 26.298 3 34.019v1h19.638v-2H5.027c.366-6.932 4.54-12.684 10.625-14.543z" fill="#B0084D" fill-rule="evenodd"></path></svg>
    """

    identitycenter_icon = """
    <?xml version="1.0" encoding="UTF-8"?>
<svg width="80px" height="80px" viewBox="0 0 80 80" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <!-- Generator: Sketch 64 (93537) - https://sketch.com -->
    <title>Icon-Architecture/64/Arch_AWS-Single-Sign-On_64</title>
    <desc>Created with Sketch.</desc>
    <defs>
        <linearGradient x1="0%" y1="100%" x2="100%" y2="0%" id="linearGradient-1">
            <stop stop-color="#BD0816" offset="0%"></stop>
            <stop stop-color="#FF5252" offset="100%"></stop>
        </linearGradient>
    </defs>
    <g id="Icon-Architecture/64/Arch_AWS-Single-Sign-On_64" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
        <g id="Icon-Architecture-BG/64/Security-Identity-Compliance" fill="url(#linearGradient-1)">
            <rect id="Rectangle" x="0" y="0" width="80" height="80"></rect>
        </g>
        <path d="M67.438,62.3245478 L52.56,47.4465478 C52.251,47.1385478 52.178,46.6655478 52.379,46.2795478 C54.457,42.2765478 53.659,37.2315478 50.439,34.0115478 C48.143,31.7155478 44.972,30.6245478 41.748,31.0125478 C38.518,31.4035478 35.67,33.2675478 33.936,36.1285478 C31.898,39.4875478 31.989,43.7965478 34.166,47.1075478 C37.187,51.7025478 43.076,53.2915478 47.864,50.8085478 C48.251,50.6085478 48.722,50.6805478 49.032,50.9895478 L51.5,53.4575478 C51.687,53.6445478 51.792,53.8995478 51.792,54.1645478 L51.792,57.4075478 L55.035,57.4075478 C55.299,57.4075478 55.554,57.5125478 55.742,57.6995478 L57.157,59.1135478 C57.344,59.3015478 57.45,59.5555478 57.45,59.8215478 L57.45,63.0635478 L60.692,63.0635478 C60.958,63.0635478 61.211,63.1695478 61.399,63.3565478 L63.254,65.2125478 L67.196,65.4755478 L67.438,62.3245478 Z M69.467,62.0195478 L69.114,66.6155478 C69.074,67.1395478 68.636,67.5385478 68.118,67.5385478 C68.095,67.5385478 68.073,67.5385478 68.05,67.5365478 L62.747,67.1825478 C62.504,67.1665478 62.277,67.0635478 62.106,66.8925478 L60.278,65.0635478 L56.45,65.0635478 C55.897,65.0635478 55.45,64.6165478 55.45,64.0635478 L55.45,60.2355478 L54.621,59.4075478 L50.792,59.4075478 C50.24,59.4075478 49.792,58.9595478 49.792,58.4075478 L49.792,54.5785478 L48.12,52.9055478 C42.546,55.3915478 35.941,53.4495478 32.494,48.2065478 C29.896,44.2545478 29.791,39.1065478 32.225,35.0915478 C34.281,31.7015478 37.665,29.4915478 41.507,29.0275478 C45.349,28.5655478 49.12,29.8645478 51.853,32.5975478 C55.506,36.2505478 56.536,41.8835478 54.475,46.5335478 L69.177,61.2355478 C69.383,61.4425478 69.49,61.7285478 69.467,62.0195478 L69.467,62.0195478 Z M45.423,41.3455478 C45.423,40.6775478 45.163,40.0495478 44.69,39.5775478 C44.217,39.1045478 43.589,38.8445478 42.922,38.8445478 C42.255,38.8445478 41.627,39.1045478 41.155,39.5765478 C40.18,40.5515478 40.18,42.1375478 41.155,43.1125478 C42.129,44.0875478 43.715,44.0875478 44.69,43.1125478 L44.69,43.1125478 C45.163,42.6395478 45.423,42.0125478 45.423,41.3455478 L45.423,41.3455478 Z M46.104,38.1625478 C46.955,39.0125478 47.423,40.1425478 47.423,41.3455478 C47.423,42.5465478 46.955,43.6765478 46.104,44.5265478 L46.104,44.5275478 C45.227,45.4045478 44.075,45.8425478 42.922,45.8425478 C41.77,45.8425478 40.618,45.4045478 39.741,44.5265478 C37.987,42.7715478 37.987,39.9165478 39.741,38.1625478 C40.59,37.3125478 41.72,36.8445478 42.922,36.8445478 C44.125,36.8445478 45.254,37.3125478 46.104,38.1625478 L46.104,38.1625478 Z M22.001,44.9215478 L28,44.9215478 L28,46.9215478 L22,46.9215478 C16.146,46.9085478 11.326,42.7565478 11.024,37.4675478 C11.011,37.2175478 11,36.9865478 11,36.7545478 C11,30.2305478 15.627,27.8055478 18.351,26.9445478 C18.333,26.6565478 18.324,26.3655478 18.324,26.0695478 C18.324,20.7195478 22.081,15.1815478 27.063,13.1885478 C32.87,10.8445478 39.028,12.0105478 43.526,16.3065478 C44.713,17.4265478 46.231,19.1005478 47.295,21.1415478 C48.431,20.1435478 49.714,19.6545478 51.183,19.6545478 C54.086,19.6545478 57.34,21.9905478 57.931,27.0965478 C63.95,28.4715478 67,31.7745478 67,36.9215478 C67,42.3485478 63.778,45.9895478 58.161,46.9085478 L57.838,44.9345478 C61.105,44.4005478 65,42.5755478 65,36.9215478 C65,32.5405478 62.397,29.9925478 56.808,28.9035478 C56.361,28.8155478 56.029,28.4365478 56.001,27.9815478 C55.777,24.2565478 53.795,21.6545478 51.183,21.6545478 C49.848,21.6545478 48.801,22.2345478 47.789,23.5355478 C47.566,23.8215478 47.209,23.9635478 46.848,23.9105478 C46.491,23.8555478 46.19,23.6115478 46.063,23.2725478 C45.191,20.9425478 43.454,18.9875478 42.15,17.7575478 C38.231,14.0155478 32.872,13.0035478 27.808,15.0445478 C23.61,16.7235478 20.324,21.5665478 20.324,26.0695478 C20.324,26.5745478 20.354,27.0605478 20.417,27.5545478 C20.421,27.5915478 20.423,27.6295478 20.424,27.6675478 L20.424,27.6695478 L20.424,27.6715478 L20.424,27.6735478 L20.424,27.6755478 L20.424,27.6755478 L20.424,27.6775478 L20.424,27.6775478 L20.424,27.6785478 L20.424,27.6795478 L20.424,27.6815478 C20.424,28.1865478 20.05,28.6085478 19.564,28.6775478 C17.065,29.3115478 13,31.1975478 13,36.7545478 C13,36.9515478 13.01,37.1485478 13.02,37.3375478 C13.262,41.5865478 17.208,44.9115478 22.001,44.9215478 L22.001,44.9215478 Z" id="AWS-Single-Sign-On_Icon_64_Squid" fill="#FFFFFF"></path>
    </g>
</svg>
    """
    # Sort the result by account name in descending order
    result_sorted = sorted(result, key=lambda x: x['AccountName'], reverse=True)

    # Initialize HTML content with the main heading
    html_content = f"<html><head><title>AWS Identity Center Assignment Report</title></head><body>"
    html_content += f"<h1>{identitycenter_icon}AWS Identity Center Assignment Report - {sso_instance_name}</h1>"

    # Initialize table of contents
    toc_content = f"<h2>{awsaccount_icon} AWS Accounts</h2><ul>"

    # Initialize dictionary to store account tables
    account_tables = {}

    # Iterate through the sorted result to generate account tables and TOC entries
    for row in result_sorted:
        account_id = row['AccountID']
        account_name = row['AccountName']

        # If account table doesn't exist, create a new table
        if account_id not in account_tables:
            # Add TOC entry for the account
            toc_content += f"<li><a href='#account_{account_id}'>{account_name}</a></li>"
            # Initialize the table for the account
            account_tables[account_id] = f"<h2>{account_name}</h2><table border='1'><tr><th>Type</th><th>Name</th><th>PermissionSet</th></tr>"

        # Add row to the corresponding account table
        account_tables[account_id] += f"<tr><td>{row['ObjectType']}</td><td>{row['ObjectName']}</td><td>{row['PermissionSet']}</td></tr>"

    # Close table of contents
    toc_content += "</ul>"

    # Write table of contents to HTML content
    html_content += toc_content

    # Write account tables to HTML content
    for account_id, account_table in account_tables.items():
        # Write account table to HTML content
        html_content += f"<a name='account_{account_id}'></a>{account_table}</table>"

    # Close HTML content
    html_content += "</body></html>"

    # Write HTML content to file
    filename = 'sso_report_Account_Assignments_' + datetime.now().strftime("%Y-%m-%d_%H.%M.%S") + '.html'
    with open(filename, 'w', newline='') as html_file:
        html_file.write(html_content)

def print_time_taken(start_time, end_time):
    """
    Prints the time taken for the report generation.
    """
    elapsed_time = end_time - start_time
    elapsed_time_string = f"{int(elapsed_time/60)} minutes and {int(elapsed_time%60)} seconds"
    print(f"The report took {elapsed_time_string} to generate.")

def main():
    """
    Main function to generate the SSO report.
    """
    print("🗼 AWS Identity Sight 🗼\n\n")
    print("ℹ️  Generating AWS Identity Center Assignment Report...\n")
    start_time = time.time()
    account_list = list_active_accounts()
    sso_instance = list_existing_sso_instances()[0]
    sso_instance_name = get_sso_instance_name(sso_instance['instanceArn'])
    permission_sets_list = list_permission_sets(sso_instance['instanceArn'])
    result = create_report(account_list, sso_instance, permission_sets_list)
    print("📂  Writing the report to an HTML file...")
    write_result_to_html(result, sso_instance_name)
    end_time = time.time()
    print_time_taken(start_time, end_time)

if __name__ == "__main__":
    main()
