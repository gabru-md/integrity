import os
from flask import Flask, request, send_file
import subprocess
import tempfile

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

APPLE_SIGNING_SERVER_PORT = os.getenv("APPLE_SIGNING_SERVER_PORT", 9002)


@app.route('/sign-shortcut', methods=['POST'])
def sign_shortcut():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.shortcut') as tmp_input, \
                tempfile.NamedTemporaryFile(delete=False, suffix='.shortcut') as tmp_output:

            input_path = tmp_input.name
            output_path = tmp_output.name

            # Save the uploaded file to the temporary input path
            file.save(input_path)

            # Execute the 'shortcuts sign' command
            # Note: The 'shortcuts' command should be in the system PATH
            command = [
                'shortcuts', 'sign',
                '--mode', 'anyone',
                '--input', input_path,
                '--output', output_path
            ]

            result = subprocess.run(command, capture_output=True, text=True, check=True)

            # Check for successful signing (optional, but good practice)
            if result.returncode == 0 and os.path.exists(output_path):
                # Return the signed file
                return send_file(
                    output_path,
                    mimetype='application/octet-stream',
                    as_attachment=True,
                    download_name=f"signed_{file.filename}"
                )
            else:
                return f"Signing failed. Output: {result.stderr}", 500

    except subprocess.CalledProcessError as e:
        # Handle shell command execution errors
        return f"Error executing shortcuts command: {e.stderr}", 500
    except Exception as e:
        # Handle other errors
        return f"An error occurred: {str(e)}", 500
    finally:
        # Clean up temporary files (important!)
        if 'input_path' in locals() and os.path.exists(input_path):
            os.unlink(input_path)
        if 'output_path' in locals() and os.path.exists(output_path):
            os.unlink(output_path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APPLE_SIGNING_SERVER_PORT)  # Use a port like 5001 for the Mac service
