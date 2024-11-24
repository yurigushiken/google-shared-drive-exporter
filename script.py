import os
import io
import json
import pickle
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/drive']

# Define your base directory here
base_path = "E:/"  # Replace this with your SSD drive or main directory

# Define script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define subdirectories relative to the script directory
metadata_directory = os.path.join(script_dir, "metadata")
metadata_file_path = os.path.join(metadata_directory, "file_metadata.json")
reports_directory = os.path.join(script_dir, "reports")

# Define local backup path
local_path = os.path.join(base_path, "LCN shared drive export")

# Ensure the necessary directories exist
os.makedirs(local_path, exist_ok=True)
os.makedirs(metadata_directory, exist_ok=True)
os.makedirs(reports_directory, exist_ok=True)

def load_metadata():
    if os.path.exists(metadata_file_path):
        with open(metadata_file_path, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(metadata_file_path, 'w') as f:
        json.dump(metadata, f, indent=4)

def get_google_auth_user_info():
    creds = None
    token_path = os.path.join(script_dir, 'token.pickle')
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secrets_path = os.path.join(script_dir, CLIENT_SECRETS_FILE)
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    creds_json = creds.to_json()
    return json.loads(creds_json)

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    filename = filename.replace('(', '').replace(')', '').replace(',', '').replace('&', '').replace(';', '')
    filename = ' '.join(filename.split())  # Remove extra spaces
    return filename[:50]  # Limit to 50 characters

def ensure_path_length(path):
    if len(path) > 250:
        path_parts = path.split(os.sep)
        shortened_parts = [part[:30] if len(part) > 30 else part for part in path_parts]
        return os.sep.join(shortened_parts)
    return path

def get_extension_from_mime(mime_type):
    google_mime_map = {
        'application/vnd.google-apps.document': '.docx',
        'application/vnd.google-apps.spreadsheet': '.xlsx',
        'application/vnd.google-apps.presentation': '.pptx',
        'application/vnd.google-apps.drawing': '.png',
        'application/vnd.google-apps.script': '.json',
        'application/msword': '.doc',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.ms-powerpoint': '.ppt',
        'video/quicktime': '.mov',
        'application/pdf': '.pdf',
        'text/plain': '.txt',
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'application/zip': '.zip',
        'audio/mpeg': '.mp3',
        'video/mp4': '.mp4',
        'application/vnd.google-apps.shortcut': '',  # Shortcuts will be ignored
        'application/octet-stream': ''  # For unknown binary files
    }
    return google_mime_map.get(mime_type, '')

def download_file(drive_service, file_id, file_name, local_folder_path, mime_type, modified_time, report, existing_metadata):
    sanitized_name = sanitize_filename(file_name)
    file_path = os.path.join(local_folder_path, sanitized_name)
    file_path = ensure_path_length(file_path)

    try:
        print(f"Processing file: {file_name} | MIME Type: {mime_type}")

        # Get the proper extension for the MIME type
        expected_extension = get_extension_from_mime(mime_type)
        if expected_extension:
            base_name = os.path.basename(file_path)
            base, ext = os.path.splitext(base_name)
            if ext.lower() != expected_extension.lower():
                if base_name.lower().endswith(expected_extension.lower()):
                    base_name = base_name[:-len(expected_extension)]
                elif base_name.lower().endswith(expected_extension.lower().lstrip('.')):
                    base_name = base_name[:-len(expected_extension.lstrip('.'))]
                base_name += expected_extension
                file_path = os.path.join(os.path.dirname(file_path), base_name)

        # Check if file exists locally and is up-to-date
        if os.path.exists(file_path):
            local_modified_time = os.path.getmtime(file_path)
            drive_modified_time = datetime.datetime.strptime(modified_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
            if abs(local_modified_time - drive_modified_time) < 1:  # Allowing 1 second difference
                skip_message = f"File is up-to-date, skipping download: {file_name}"
                print(skip_message)
                # Do not add to report
                return
        else:
            drive_modified_time = datetime.datetime.strptime(modified_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()

        if mime_type.startswith('application/vnd.google-apps.'):
            # Map Google Workspace MIME types to export formats
            mime_type_export = {
                'application/vnd.google-apps.document': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.google-apps.drawing': 'image/png',
                'application/vnd.google-apps.script': 'application/vnd.google-apps.script+json',
                # Add more mappings if needed
            }.get(mime_type, 'application/pdf')  # Default to PDF if not found

            print(f"Exporting Google Workspace file to: {expected_extension}")
            request = drive_service.files().export_media(fileId=file_id, mimeType=mime_type_export)
        else:
            request = drive_service.files().get_media(fileId=file_id)

        file_data = io.BytesIO()
        downloader = MediaIoBaseDownload(file_data, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Save the file locally
        with open(file_path, 'wb') as f:
            f.write(file_data.getvalue())
        # Update the local file's modified time to match the drive file
        os.utime(file_path, (drive_modified_time, drive_modified_time))

        print(f"File saved: {file_path}")
        # Do not add successful downloads to report

        # Update existing_metadata after each file
        existing_metadata[file_id] = {
            "name": file_name,
            "mimeType": mime_type,
            "modifiedTime": modified_time,
            "size": int(os.path.getsize(file_path))
        }

    except HttpError as e:
        error_content = json.loads(e.content.decode('utf-8'))
        error_reason = error_content.get('error', {}).get('errors', [{}])[0].get('reason')
        if error_reason == 'exportSizeLimitExceeded':
            error_message = f"Cannot export file '{file_name}' because it exceeds the export size limit."
        elif error_reason == 'badRequest':
            error_message = f"Cannot export file '{file_name}' due to unsupported conversion."
        else:
            error_message = f"Failed to process '{file_name}' (MIME: {mime_type}). Error: {e}"
        print(error_message)
        report.append(error_message)
    except Exception as e:
        error_message = f"Failed to process '{file_name}' (MIME: {mime_type}). Error: {e}"
        print(error_message)
        report.append(error_message)

def download_files_in_folder(drive_service, folder_id, local_folder_path, shared_drive_id=None,
                             existing_metadata={}, aggregated_report=None, downloaded_files=None):
    if aggregated_report is None:
        aggregated_report = []
    if downloaded_files is None:
        downloaded_files = []

    query = f"'{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        corpora='drive',
        driveId=shared_drive_id,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)"
    ).execute()

    items = results.get('files', [])

    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        modified_time = item['modifiedTime']

        if mime_type == 'application/vnd.google-apps.folder':
            sanitized_folder_name = sanitize_filename(file_name)
            new_folder_path = os.path.join(local_folder_path, sanitized_folder_name)
            new_folder_path = ensure_path_length(new_folder_path)
            if not os.path.exists(new_folder_path):
                os.makedirs(new_folder_path)
            print(f"Recursing into folder: {file_name}")
            download_files_in_folder(
                drive_service, file_id, new_folder_path, shared_drive_id,
                existing_metadata=existing_metadata, aggregated_report=aggregated_report,
                downloaded_files=downloaded_files
            )
        elif mime_type == 'application/vnd.google-apps.shortcut':
            skip_message = f"Shortcut ignored: {file_name}"
            print(skip_message)
            # Do not add this message to aggregated_report
        else:
            if file_id not in existing_metadata or existing_metadata[file_id]['modifiedTime'] != modified_time:
                print(f"Downloading file: {file_name}")
                download_file(
                    drive_service, file_id, file_name, local_folder_path, mime_type,
                    modified_time, aggregated_report, existing_metadata
                )
                downloaded_files.append({
                    'id': file_id,
                    'name': file_name,
                    'size': int(item.get('size', 0))
                })
            else:
                # File has not changed, skipping download
                skip_message = f"File has not changed, skipping download: {file_name}"
                print(skip_message)
                # Do not add this message to aggregated_report

def get_total_files_and_size(drive_service, shared_drive_id):
    print("Calculating total number of files and total size on the shared drive. This may take a while...")
    total_files_on_drive = 0
    total_size_on_drive = 0
    page_token = None
    while True:
        response = drive_service.files().list(
            q="trashed=false",
            spaces='drive',
            corpora='drive',
            driveId=shared_drive_id,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageToken=page_token,
            pageSize=1000,
            fields="nextPageToken, files(size)"
        ).execute()
        for file in response.get('files', []):
            total_files_on_drive += 1
            total_size_on_drive += int(file.get('size', 0))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return total_files_on_drive, total_size_on_drive

if __name__ == "__main__":
    shared_drive_id = '0ANrqIuJZcnvTUk9PVA'  # Your Shared Drive ID

    creds = Credentials.from_authorized_user_info(info=get_google_auth_user_info())
    drive_service = build('drive', 'v3', credentials=creds)

    existing_metadata = load_metadata()
    aggregated_report = []
    downloaded_files = []

    # Start the download process
    print("Starting the download process...")
    download_files_in_folder(
        drive_service,
        shared_drive_id,
        local_path,
        shared_drive_id,
        existing_metadata,
        aggregated_report,
        downloaded_files
    )

    # Save metadata after all files are processed
    save_metadata(existing_metadata)

    # Calculate total files and size on the drive
    total_files_on_drive, total_size_on_drive = get_total_files_and_size(drive_service, shared_drive_id)
    print(f"Total files on shared drive: {total_files_on_drive}")
    print(f"Total size on shared drive: {total_size_on_drive / (1024 ** 3):.2f} GB")

    # Calculate total errors
    total_errors = len(aggregated_report)

    # Generate final report using downloaded_files and aggregated_report
    total_files_downloaded = len(downloaded_files)
    total_data_exported_gb = sum(file['size'] for file in downloaded_files) / (1024 ** 3)
    total_drive_size_gb = total_size_on_drive / (1024 ** 3)
    percentage_downloaded = (total_files_downloaded / total_files_on_drive) * 100 if total_files_on_drive else 0

    report_summary = [
        f"Backup Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total files on shared drive: {total_files_on_drive}",
        f"Total size on shared drive: {total_drive_size_gb:.2f} GB",
        f"Total files downloaded this run: {total_files_downloaded}",
        f"Total data downloaded this run: {total_data_exported_gb:.2f} GB",
        f"Percentage of drive downloaded this run: {percentage_downloaded:.2f}%",
        f"Total errors encountered during backup: {total_errors}",
        "",
        "List of files downloaded:"
    ]

    report_summary.extend(file['name'] for file in downloaded_files)

    # Add errors and warnings to the report
    if aggregated_report:
        report_summary.extend([
            "",
            "Errors and Warnings encountered during backup:"
        ])
        report_summary.extend(aggregated_report)

    # Generate a timestamped filename for the report
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f"backup_report_{timestamp}.txt"
    report_file_path = os.path.join(reports_directory, report_filename)

    # Write the aggregated report to the file
    with open(report_file_path, 'w', encoding='utf-8') as report_file:
        report_file.write("\n".join(report_summary))

    # Optionally, print the report to the terminal
    print("\n=== Final Backup Report Summary ===\n")
    print("\n".join(report_summary))
