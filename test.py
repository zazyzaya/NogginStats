import dropbox 
from secret import secret

dbx = dropbox.Dropbox(
    oauth2_refresh_token=secret['refresh-token'],
    app_key=secret['db-key'],
    app_secret=secret['db-secret']
)

dbx.files_download_to_file('/NogginStats/test.txt')