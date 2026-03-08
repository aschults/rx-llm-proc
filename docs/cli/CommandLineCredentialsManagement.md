# Command-Line Credentials Management

To use the tools that interact with Google Workspace APIs (like Gmail, Drive,
etc.), you must authorize the application to access your data via Google's
OAuth2 protocol.

## The Authentication Process

The process is designed to be straightforward and secure, leveraging the
standard Google Authentication Libraries.

1.  **Prerequisite**: You must first obtain a `client_secret.json` file for your
    project from the
    [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
    Place this file in your configuration directory.

2.  **First-Time Use**: The first time you run a command that requires Google
    API access, the tool will automatically initiate a one-time authorization
    process. It will prompt you to open a URL in your browser, where you will
    log in and grant the requested permissions.

3.  **Automatic Token Storage**: After you grant consent, a `credentials.json` file is
    automatically created in your configuration directory. This file securely
    stores the authorization token (including a refresh token), so you do not
    have to re-authenticate every time you run a command.

### Environment Variables

You can specify alternative locations for these files using environment
variables:

- `RX_LLM_PROC_GOOGLE_CLIENT_SECRET_FILE`: Overrides the default path for
  `client_secret.json`.
- `RX_LLM_PROC_GOOGLE_CREDENTIALS_FILE`: Overrides the default path for the
  generated `credentials.json`.

---

## Application Default Credentials (ADC)

If you have the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
installed, you can use Application Default Credentials to authenticate. This is
the recommended method for developers as it avoids manual management of secret
files.

1. **Authorize**: Run the following command in your terminal:

   ```bash
   # Define the scopes you need
   SCOPES=(
     "https://www.googleapis.com/auth/gmail.modify"
     "https://www.googleapis.com/auth/cloud-platform"
     "https://www.googleapis.com/auth/tasks"
     "https://www.googleapis.com/auth/drive"
     "https://www.googleapis.com/auth/spreadsheets"
   )

   # Login with the joined scopes
   gcloud auth application-default login --scopes="$(IFS=,; echo "${SCOPES[*]}")"
   ```

   _Note: Ensure you include all necessary scopes for the Workspace APIs you
   intend to use._

2. **Automatic Detection**: The tools will automatically detect and use these
   credentials if available, falling back to the `client_secret.json` method
   only if ADC is not configured.

---

## Detailed Documentation

For a complete explanation of the authentication flow, how access and refresh
tokens are handled, file storage locations, and **important security
considerations**, please see the canonical design document:

### **[[../design/CredentialStoreDesign]]**
