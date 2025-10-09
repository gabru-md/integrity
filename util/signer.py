import requests
from dotenv import load_dotenv
import os

load_dotenv()

APPLE_SIGNING_SERVER_URL = os.getenv("APPLE_SIGNING_SERVER_URL")


def sign_file_on_macbook(unsigned_filepath: str, signed_output_path: str) -> bool:
    """
    Sends an unsigned .shortcut file to the MacBook signing service and saves the signed result.

    :param unsigned_filepath: Path to the local unsigned .shortcut file.
    :param signed_output_path: Path where the returned signed file should be saved.
    :return: True if signing was successful, False otherwise.
    """
    if not os.path.exists(unsigned_filepath):
        print(f"Error: Unsigned file not found at {unsigned_filepath}")
        return False

    # 1. Prepare the file for the POST request
    # 'rb' opens the file in binary mode for reading
    try:
        with open(unsigned_filepath, 'rb') as f:
            files = {
                'file': (os.path.basename(unsigned_filepath), f, 'application/octet-stream')
            }

            print(f"Sending file to MacBook service at: {APPLE_SIGNING_SERVER_URL}")

            response = requests.post(APPLE_SIGNING_SERVER_URL, files=files, timeout=300)  # 5 min timeout

            if response.status_code == 200:
                print("Signing successful. Saving signed file...")

                # Save the binary content of the response (the signed file)
                with open(signed_output_path, 'wb') as out_f:
                    out_f.write(response.content)

                print(f"Signed file saved to: {signed_output_path}")
                return True
            else:
                # Signing service returned an error
                print(f"Signing failed. Status code: {response.status_code}")
                print(f"MacBook server response: {response.text}")
                return False

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to the MacBook signing service at {APPLE_SIGNING_SERVER_URL}.")
        print("Ensure the MacBook server is running and the IP address is correct.")
        return False
    except requests.exceptions.Timeout:
        print("Error: Request timed out. The signing process might have taken too long.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
