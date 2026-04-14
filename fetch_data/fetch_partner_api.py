import os
from graphql import print_ast
import requests
from dotenv import load_dotenv
from gql import gql

is_dev = False

def getenv_w_log(key):
    value = os.getenv(key)
    if value is None:
        print(f"Error: {key} is not set in the environment variables.")
    return value

def fetch_events(first_n=10):
    if is_dev:
        print(load_dotenv())

    org_id = getenv_w_log("SHOPIFY_PARTNER_ORG_ID")
    app_id = getenv_w_log("SHOPIFY_PARTNER_APP_ID")
    api_ver = getenv_w_log("SHOPIFY_PARTNER_API_VER")
    access_token = getenv_w_log("SHOPIFY_PARTNER_API_TOKEN")

    if not all([org_id, app_id, api_ver, access_token]):
        print("Error: Missing required environment variable(s)")
        return None

    global_app_id = f"gid://partners/App/{app_id}"
    api_url = f"https://partners.shopify.com/{org_id}/api/{api_ver}/graphql.json"

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    variables = {
        "appId": global_app_id,
        "first_n": first_n
    }

    graphql_query = gql("""
            query GetEvents($appId: ID!, $first_n: Int!) {
                app(id: $appId) {
                    id
                    name
                    events(first: $first_n) {
                        edges {
                            node {
                                occurredAt
                                shop {
                                    name
                                    myshopifyDomain
                                }
                                type

                                __typename
                
                                ... on RelationshipUninstalled {
                                    description
                                    reason
                                }
                        
                                ... on AppSubscriptionEvent {
                                    charge {
                                        amount {
                                            amount
                                            currencyCode
                                        }
                                        billingOn
                                        id
                                        name
                                        test
                                    }
                                }
                        
                                ... on AppPurchaseOneTimeEvent {
                                    charge {
                                        amount {
                                            amount
                                            currencyCode
                                        }
                                        id
                                        name
                                        test
                                    }
                                }
                        
                                ... on UsageChargeApplied {
                                    charge {
                                        amount {
                                            amount
                                            currencyCode
                                        }
                                        id
                                        name
                                        test
                                    }
                                }
                        
                                ... on AppCreditEvent {
                                    appCredit {
                                        amount {
                                            amount
                                            currencyCode
                                        }
                                        id
                                        name
                                        test
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)
    
    query_str = print_ast(graphql_query.document)
    response = requests.post(api_url, json={"query": query_str, "variables": variables}, headers=headers)

    if response.status_code == 200:
        print("GraphQL query successful!")
        return response.json()
    else:
        print(f"GraphQL query failed with status code {response.status_code}: {response.text}")
        return None




if __name__ == "__main__":
    is_dev = True
    result_json = fetch_events(50)
    if result_json is not None:
        os.makedirs("output", exist_ok=True)
        with open("output/events_data.json", "w", encoding="utf-16") as f:
            import json
            json.dump(result_json, f, indent=2)
            print("Data saved to output/events_data.json")
            exit(0)

        print("Failed to write data.")   
    print("Failed to fetch events data.")
    exit(1)
