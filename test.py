import dropbox 
from secret import secret 
dbx = dropbox.Dropbox(secret['db-token'])

f = open('test_file.txt', 'rb')  
meta = dbx.files_upload(f.read(), '/NogginStats/test.txt', mode=dropbox.files.WriteMode("overwrite"))

meta, res = dbx.files_download('/NogginStats/test.txt')
print(res.content)